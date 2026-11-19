"""Linux back-end: NetworkManager (nmcli) and ufw."""

from __future__ import annotations

import shutil
import time
from typing import List, Optional

from ..config import LINUX_HOTSPOT_IP
from .base import HotspotError, HotspotInfo, check_password, run


def _unescape(value: str) -> str:
    return value.replace("\\:", ":")


def _wifi_interface() -> Optional[str]:
    for line in run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"]).stdout.splitlines():
        device, _, kind = line.rpartition(":")
        if kind == "wifi":
            return _unescape(device)
    return None


def _connection_names() -> List[str]:
    return [_unescape(n) for n in run(["nmcli", "-t", "-f", "NAME", "connection", "show"]).stdout.splitlines()]


def _interface_ip(interface: str) -> Optional[str]:
    for _ in range(6):
        out = run(["nmcli", "-g", "IP4.ADDRESS", "device", "show", interface], check=False).stdout.strip()
        if out:
            return out.splitlines()[0].split("/")[0]
        time.sleep(1)
    return None


def start(ssid: str, password: str, interface: Optional[str] = None) -> HotspotInfo:
    check_password(password)
    iface = interface or _wifi_interface()
    if not iface:
        raise HotspotError("No Wi-Fi interface found. Check `nmcli device status` or pass --wifi NAME.")
    notes = []
    if ssid in _connection_names():
        run(["nmcli", "connection", "up", ssid, "ifname", iface])
        notes.append(f"Reused the saved NetworkManager profile '{ssid}' (its stored password is kept).")
    else:
        run(["nmcli", "device", "wifi", "hotspot", "ifname", iface, "con-name", ssid, "ssid", ssid, "password", password])
    ip = _interface_ip(iface)
    if not ip:
        ip = LINUX_HOTSPOT_IP
        notes.append(f"Could not read the interface address; assuming the usual {LINUX_HOTSPOT_IP}.")
    return HotspotInfo(ssid=ssid, ip=ip, notes=notes)


def stop(ssid: Optional[str] = None) -> None:
    run(["nmcli", "connection", "down", ssid or "LabShare"])


def status() -> str:
    return run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"]).stdout.strip() or "No active connections."


def connect_wifi(ssid: str, password: str) -> None:
    run(["nmcli", "device", "wifi", "connect", ssid, "password", password])


def open_firewall(port: int) -> str:
    if not shutil.which("ufw"):
        return "ufw not installed - no firewall change made (add a rule yourself if you use iptables/nftables)."
    run(["ufw", "allow", f"{port}/tcp"])
    return f"ufw: allowed {port}/tcp"
