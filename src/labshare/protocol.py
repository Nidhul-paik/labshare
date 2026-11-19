"""Wire protocol: one JSON object per line over a TCP connection.

Every request has an ``action``; every reply has ``ok`` (bool) and either the
result fields or an ``error`` string.  JSON escapes newlines inside strings, so
multi-line code travels safely inside a single line.
"""

from __future__ import annotations

import json
import socket
import threading
from typing import Optional

from .config import MAX_LINE_BYTES


class ProtocolError(Exception):
    """The peer sent something that is not valid protocol data."""


class Connection:
    """Line-delimited JSON on top of a connected socket."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self._reader = sock.makefile("rb")
        self._send_lock = threading.Lock()

    def send(self, payload: dict) -> None:
        data = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with self._send_lock:
            self.sock.sendall(data)

    def receive(self) -> Optional[dict]:
        """Return the next message, or ``None`` when the peer closed the connection."""
        line = self._reader.readline(MAX_LINE_BYTES + 1)
        if not line:
            return None
        if len(line) > MAX_LINE_BYTES and not line.endswith(b"\n"):
            raise ProtocolError("message too large")
        try:
            obj = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ProtocolError(f"malformed message: {exc}") from exc
        if not isinstance(obj, dict):
            raise ProtocolError("message must be a JSON object")
        return obj

    def close(self) -> None:
        for step in (lambda: self.sock.shutdown(socket.SHUT_RDWR), self.sock.close):
            try:
                step()
            except OSError:
                pass
