"""Pieces shared by the Windows and Linux hotspot back-ends."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import List, Sequence


class HotspotError(RuntimeError):
    """A hotspot / firewall / Wi-Fi command failed.  The message is meant for the user."""


@dataclass
class HotspotInfo:
    ssid: str
    ip: str
    notes: List[str] = field(default_factory=list)


def run(cmd: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(list(cmd), capture_output=True, text=True, errors="replace", timeout=60)
    except FileNotFoundError:
        raise HotspotError(f"Command not found: {cmd[0]}") from None
    except subprocess.TimeoutExpired:
        raise HotspotError(f"Command timed out: {' '.join(cmd)}") from None
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"exit code {result.returncode}"
        raise HotspotError(f"{' '.join(cmd[:3])} failed: {detail}")
    return result


def check_password(password: str) -> None:
    if not password or not (8 <= len(password) <= 63):
        raise HotspotError("The hotspot password must be 8 to 63 characters long.")
