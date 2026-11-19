"""Windows back-end: netsh hosted network, Windows Firewall and WLAN profiles."""

from __future__ import annotations

import ctypes
import os
import re
import tempfile
from typing import Optional
from xml.sax.saxutils import escape

from ..config import WINDOWS_HOTSPOT_IP
from .base import HotspotError, HotspotInfo, check_password, run

MOBILE_HOTSPOT_HELP = (
    "Alternative: open Settings > Network & Internet > Mobile hotspot, set the network name and "
    "password, switch it on, then run the host without --hotspot. Windows usually gives the host "
    f"the address {WINDOWS_HOTSPOT_IP}. If Windows refuses to start the hotspot without internet, "
    "use a phone hotspot or router instead - LabShare works on any shared Wi-Fi/LAN."
)


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _require_admin() -> None:
    if not is_admin():
        raise HotspotError("This needs an Administrator command prompt (right-click Command Prompt > Run as administrator).")


def start(ssid: str, password: str, interface: Optional[str] = None) -> HotspotInfo:
    check_password(password)
    _require_admin()
    drivers = run(["netsh", "wlan", "show", "drivers"], check=False).stdout
    match = re.search(r"Hosted network supported\s*:\s*(\w+)", drivers, re.IGNORECASE)
    if match and match.group(1).lower() != "yes":
        raise HotspotError("This Wi-Fi adapter/driver does not support the hosted network. " + MOBILE_HOTSPOT_HELP)
    run(["netsh", "wlan", "set", "hostednetwork", "mode=allow", f"ssid={ssid}", f"key={password}"])
    try:
        run(["netsh", "wlan", "start", "hostednetwork"])
    except HotspotError as exc:
        raise HotspotError(f"{exc}\n{MOBILE_HOTSPOT_HELP}") from None
    return HotspotInfo(ssid=ssid, ip=WINDOWS_HOTSPOT_IP, notes=[])


def stop(ssid: Optional[str] = None) -> None:
    run(["netsh", "wlan", "stop", "hostednetwork"])


def status() -> str:
    return run(["netsh", "wlan", "show", "hostednetwork"]).stdout.strip()


_PROFILE = """<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{ssid}</name>
  <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>auto</connectionMode>
  <MSM><security>
    <authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption>
    <sharedKey><keyType>passphrase</keyType><protected>false</protected><keyMaterial>{key}</keyMaterial></sharedKey>
  </security></MSM>
</WLANProfile>
"""


def connect_wifi(ssid: str, password: str) -> None:
    handle, path = tempfile.mkstemp(suffix=".xml")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            fh.write(_PROFILE.format(ssid=escape(ssid), key=escape(password)))
        run(["netsh", "wlan", "add", "profile", f"filename={path}"])
    finally:
        try:
            os.remove(path)  # the file contains the Wi-Fi password
        except OSError:
            pass
    run(["netsh", "wlan", "connect", f"name={ssid}"])


def open_firewall(port: int) -> str:
    _require_admin()
    rule = f"LabShare TCP {port}"
    run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule}"], check=False)
    run(["netsh", "advfirewall", "firewall", "add", "rule", f"name={rule}", "dir=in", "action=allow",
         "protocol=TCP", f"localport={port}"])
    return f"Windows Firewall: allowed inbound TCP {port}"
