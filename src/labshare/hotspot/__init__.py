"""Platform dispatch for hotspot, Wi-Fi and firewall helpers.

Only the network set-up differs between operating systems; everything else in
LabShare is identical on Windows and Linux.
"""

from __future__ import annotations

import sys
from typing import Optional

from .base import HotspotError, HotspotInfo

__all__ = ["HotspotError", "HotspotInfo", "start", "stop", "status", "connect_wifi", "open_firewall"]


def _backend():
    if sys.platform.startswith("win"):
        from . import windows as backend
    elif sys.platform.startswith("linux"):
        from . import linux as backend
    else:
        raise HotspotError("Automatic hotspot set-up supports Windows and Linux only. Create the hotspot manually.")
    return backend


def start(ssid: str, password: str, interface: Optional[str] = None) -> HotspotInfo:
    return _backend().start(ssid, password, interface)


def stop(ssid: Optional[str] = None) -> None:
    _backend().stop(ssid)


def status() -> str:
    return _backend().status()


def connect_wifi(ssid: str, password: str) -> None:
    _backend().connect_wifi(ssid, password)


def open_firewall(port: int) -> str:
    return _backend().open_firewall(port)
