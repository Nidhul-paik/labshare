"""Shared constants and small helpers for locating per-user data."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

APP_NAME = "LabShare"

DEFAULT_PORT = 50555
DEFAULT_BIND = "0.0.0.0"
DEFAULT_SSID = "LabShare"

# Typical address of the machine that creates the hotspot.
LINUX_HOTSPOT_IP = "10.42.0.1"      # NetworkManager shared mode
WINDOWS_HOTSPOT_IP = "192.168.137.1"  # Windows hosted network / Mobile Hotspot

MAX_MESSAGE_BYTES = 1_000_000       # 1 MB of message text
MAX_LINE_BYTES = 8_000_000          # JSON escaping can inflate text, so allow headroom

KINDS = ("text", "code", "command")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,32}$")
USERNAME_HELP = "1-32 characters: letters, digits, underscore, dot or hyphen"


def data_dir() -> Path:
    """Folder for the database and saved settings (created on demand)."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        path = base / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        path = base / "labshare"
    return path


def default_db_path() -> Path:
    return Path(os.environ.get("LABSHARE_DB") or data_dir() / "labshare.db")


def _settings_path() -> Path:
    return data_dir() / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(values: dict) -> None:
    """Best-effort: remembering the last host/username must never break the app."""
    try:
        path = _settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        merged = {**load_settings(), **values}
        path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    except OSError:
        pass
