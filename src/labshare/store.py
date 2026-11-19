"""SQLite message store used by the host."""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional, Set


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class MessageStore:
    """Users and messages.  Each call opens its own connection, so it is thread-safe."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _open(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.path), timeout=15)
        con.row_factory = sqlite3.Row
        return con

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        con = self._open()
        try:
            with con:  # commit / rollback
                yield con
        finally:
            con.close()

    def _init_db(self) -> None:
        with self._conn() as con:
            try:
                con.execute("PRAGMA journal_mode=WAL")
            except sqlite3.DatabaseError:
                pass
            con.execute(
                """CREATE TABLE IF NOT EXISTS users (
                       username TEXT PRIMARY KEY COLLATE NOCASE,
                       last_seen TEXT NOT NULL)"""
            )
            con.execute(
                """CREATE TABLE IF NOT EXISTS messages (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       sender TEXT NOT NULL,
                       recipient TEXT NOT NULL,
                       kind TEXT NOT NULL DEFAULT 'text',
                       filename TEXT,
                       body TEXT NOT NULL,
                       created_at TEXT NOT NULL,
                       is_read INTEGER NOT NULL DEFAULT 0,
                       client_id TEXT)"""
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_inbox ON messages(recipient COLLATE NOCASE, is_read)"
            )

    # -- users ---------------------------------------------------------------
    def register_user(self, username: str) -> str:
        """Create or refresh a user; returns the canonical spelling (first one seen)."""
        with self._conn() as con:
            con.execute("INSERT OR IGNORE INTO users(username,last_seen) VALUES(?,?)", (username, now()))
            con.execute("UPDATE users SET last_seen=? WHERE username=?", (now(), username))
            return con.execute("SELECT username FROM users WHERE username=?", (username,)).fetchone()[0]

    def canonical_name(self, username: str) -> Optional[str]:
        with self._conn() as con:
            row = con.execute("SELECT username FROM users WHERE username=?", (username,)).fetchone()
        return row[0] if row else None

    def list_users(self, online_names: Set[str]) -> List[dict]:
        online = {n.lower() for n in online_names}
        with self._conn() as con:
            rows = con.execute("SELECT username FROM users ORDER BY username COLLATE NOCASE").fetchall()
        return [{"username": r[0], "online": r[0].lower() in online} for r in rows]

    # -- messages ------------------------------------------------------------
    def save_message(self, sender, recipient, kind, filename, body, client_id=None) -> int:
        with self._conn() as con:
            if client_id:  # a retried request must not create a duplicate
                row = con.execute(
                    "SELECT id FROM messages WHERE sender=? AND client_id=?", (sender, client_id)
                ).fetchone()
                if row:
                    return row[0]
            cur = con.execute(
                "INSERT INTO messages(sender,recipient,kind,filename,body,created_at,client_id) "
                "VALUES(?,?,?,?,?,?,?)",
                (sender, recipient, kind, filename, body, now(), client_id),
            )
            return cur.lastrowid

    def inbox(self, recipient: str) -> List[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT id,sender,kind,filename,body,created_at FROM messages "
                "WHERE recipient=? COLLATE NOCASE AND is_read=0 ORDER BY id",
                (recipient,),
            ).fetchall()
        return [dict(r) for r in rows]

    def unread_count(self, recipient: str) -> int:
        with self._conn() as con:
            return con.execute(
                "SELECT COUNT(*) FROM messages WHERE recipient=? COLLATE NOCASE AND is_read=0",
                (recipient,),
            ).fetchone()[0]

    def mark_read(self, message_id: int, recipient: str) -> bool:
        with self._conn() as con:
            cur = con.execute(
                "UPDATE messages SET is_read=1 WHERE id=? AND recipient=? COLLATE NOCASE",
                (message_id, recipient),
            )
            return cur.rowcount > 0
