"""Network client used by the terminal UI.  Plain request/response, no threads."""

from __future__ import annotations

import socket
import uuid
from typing import List, Optional

from .config import DEFAULT_PORT
from .protocol import Connection, ProtocolError


class LabShareError(Exception):
    """The host refused a request (bad username, wrong token, ...)."""


class LabShareClient:
    def __init__(self, username: str, host: str, port: int = DEFAULT_PORT, token: Optional[str] = None):
        self.username = username
        self.host = host
        self.port = port
        self.token = token
        self._conn: Optional[Connection] = None
        self.unread = 0

    # -- connection ------------------------------------------------------------
    def connect(self) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=8)
        sock.settimeout(30)
        conn = Connection(sock)
        try:
            conn.send({"action": "register", "username": self.username, "token": self.token or ""})
            reply = conn.receive()
        except (OSError, ProtocolError):
            conn.close()
            raise
        if reply is None:
            conn.close()
            raise ConnectionError("host closed the connection")
        if not reply.get("ok"):
            conn.close()
            raise LabShareError(reply.get("error", "registration failed"))
        self.username = reply.get("username", self.username)
        self.unread = reply.get("unread", 0)
        self._conn = conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def request(self, payload: dict) -> dict:
        """Send one request.  A dropped connection is re-established once automatically."""
        last_error: Optional[Exception] = None
        for _ in range(2):
            try:
                if self._conn is None:
                    self.connect()
                self._conn.send(payload)
                reply = self._conn.receive()
                if reply is None:
                    raise ConnectionError("host closed the connection")
                return reply
            except (OSError, ProtocolError) as exc:
                last_error = exc
                self.close()
        raise ConnectionError(str(last_error))

    # -- API -------------------------------------------------------------------
    def _checked(self, payload: dict) -> dict:
        reply = self.request(payload)
        if not reply.get("ok"):
            raise LabShareError(reply.get("error", "request failed"))
        return reply

    def list_users(self) -> List[dict]:
        return self._checked({"action": "list"})["users"]

    def unread_count(self) -> int:
        self.unread = self._checked({"action": "count"})["unread"]
        return self.unread

    def send(self, to: str, text: str, kind: str = "text", filename: Optional[str] = None) -> dict:
        # client_id lets the host ignore a duplicate if this request is retried
        return self._checked(
            {"action": "send", "to": to, "text": text, "kind": kind, "filename": filename,
             "client_id": uuid.uuid4().hex}
        )

    def inbox(self) -> List[dict]:
        return self._checked({"action": "inbox"})["messages"]

    def mark_read(self, message_id: int) -> None:
        self._checked({"action": "ack", "id": message_id})
