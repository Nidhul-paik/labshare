"""The host: a threaded TCP relay that stores messages in SQLite."""

from __future__ import annotations

import hmac
import logging
import re
import socket
import threading
import time
from typing import Dict, Optional, Set, Tuple

from .config import (
    DEFAULT_BIND,
    DEFAULT_PORT,
    KINDS,
    MAX_MESSAGE_BYTES,
    USERNAME_HELP,
    USERNAME_RE,
    default_db_path,
)
from .protocol import Connection, ProtocolError
from .store import MessageStore

log = logging.getLogger("labshare.server")


def _err(message: str) -> dict:
    return {"ok": False, "error": message}


def _clean_filename(value) -> Optional[str]:
    if not isinstance(value, str):
        return None
    name = re.split(r"[\\/]", value.strip())[-1].strip()
    return name[:100] or None


class LabShareServer:
    def __init__(self, host: str = DEFAULT_BIND, port: int = DEFAULT_PORT, db_path=None, token: Optional[str] = None):
        self.host = host
        self.port = port
        self.token = token or None
        self.store = MessageStore(db_path or default_db_path())
        self._sock: Optional[socket.socket] = None
        self._online: Dict[str, Tuple[str, Connection]] = {}  # lower-name -> (name, connection)
        self._lock = threading.Lock()
        self._stop = threading.Event()

    # -- lifecycle -------------------------------------------------------------
    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(64)
        sock.settimeout(0.5)  # lets serve_forever notice shutdown() on every OS
        self._sock = sock
        self.port = sock.getsockname()[1]  # resolves port 0
        log.info("LabShare relay listening on %s:%s", self.host, self.port)

    def serve_forever(self) -> None:
        if self._sock is None:
            self.start()
        while not self._stop.is_set():
            try:
                client, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(client, addr), daemon=True).start()

    def shutdown(self) -> None:
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        with self._lock:
            conns = [c for _, c in self._online.values()]
            self._online.clear()
        for conn in conns:
            conn.close()

    def online_names(self) -> Set[str]:
        with self._lock:
            return {name for name, _ in self._online.values()}

    # -- per-connection handling -----------------------------------------------
    def _handle_client(self, sock: socket.socket, addr) -> None:
        conn = Connection(sock)
        username: Optional[str] = None
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            first = conn.receive()
            if first is None:
                return
            username = self._register(conn, first, addr)
            if username is None:
                return
            while not self._stop.is_set():
                request = conn.receive()
                if request is None:
                    break
                conn.send(self._dispatch(username, request))
        except ProtocolError as exc:
            try:
                conn.send(_err(str(exc)))
            except OSError:
                pass
        except OSError:
            pass
        finally:
            if username:
                self._unregister(username, conn)
                log.info("%s disconnected (%s)", username, addr[0])
            conn.close()

    def _register(self, conn: Connection, request: dict, addr) -> Optional[str]:
        if request.get("action") != "register":
            conn.send(_err("First message must be a register request"))
            return None
        name = str(request.get("username", "")).strip()
        if not USERNAME_RE.match(name):
            conn.send(_err(f"Invalid username ({USERNAME_HELP})"))
            return None
        if self.token is not None:
            given = str(request.get("token", "")).encode("utf-8")
            if not hmac.compare_digest(given, self.token.encode("utf-8")):
                log.warning("Rejected %s from %s: wrong token", name, addr[0])
                conn.send(_err("Wrong access token"))
                return None
        canonical = self.store.register_user(name)
        with self._lock:
            previous = self._online.get(canonical.lower())
            self._online[canonical.lower()] = (canonical, conn)
        if previous:  # same user reconnecting (e.g. after a crash): the new session wins
            previous[1].close()
        log.info("%s connected from %s", canonical, addr[0])
        conn.send({"ok": True, "username": canonical, "unread": self.store.unread_count(canonical)})
        return canonical

    def _unregister(self, username: str, conn: Connection) -> None:
        with self._lock:
            current = self._online.get(username.lower())
            if current and current[1] is conn:
                del self._online[username.lower()]

    # -- request handlers -----------------------------------------------------
    def _dispatch(self, username: str, request: dict) -> dict:
        action = request.get("action")
        try:
            if action == "list":
                return {"ok": True, "users": self.store.list_users(self.online_names())}
            if action == "send":
                return self._send(username, request)
            if action == "inbox":
                return {"ok": True, "messages": self.store.inbox(username)}
            if action == "count":
                return {"ok": True, "unread": self.store.unread_count(username)}
            if action == "ack":
                changed = self.store.mark_read(int(request.get("id", 0)), username)
                return {"ok": changed, **({} if changed else {"error": "No such unread message"})}
            if action == "ping":
                return {"ok": True, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
            return _err("Unknown action")
        except (ValueError, TypeError):
            return _err("Invalid request")
        except Exception:  # keep the connection alive on unexpected failures
            log.exception("Unexpected error handling %r from %s", action, username)
            return _err("Server error")

    def _send(self, sender: str, request: dict) -> dict:
        kind = request.get("kind", "text")
        if kind not in KINDS:
            return _err(f"Unknown message type (use one of: {', '.join(KINDS)})")
        text = request.get("text")
        if not isinstance(text, str) or not text.strip():
            return _err("Message is empty")
        if len(text.encode("utf-8")) > MAX_MESSAGE_BYTES:
            return _err("Message exceeds 1 MB")
        recipient = self.store.canonical_name(str(request.get("to", "")).strip())
        if recipient is None:
            return _err("Username not found. Ask the recipient to run LabShare once.")
        client_id = request.get("client_id")
        if not isinstance(client_id, str) or len(client_id) > 64:
            client_id = None
        message_id = self.store.save_message(
            sender, recipient, kind, _clean_filename(request.get("filename")), text, client_id
        )
        online = recipient.lower() in {n.lower() for n in self.online_names()}
        log.info("%s -> %s: %s #%s (%d bytes)", sender, recipient, kind, message_id, len(text))
        return {"ok": True, "id": message_id, "to": recipient, "recipient_online": online}
