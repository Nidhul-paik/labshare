"""Find this computer's IPv4 addresses (so the host can tell students where to connect)."""

from __future__ import annotations

import re
import socket
import subprocess
import sys
from typing import List


def _command_output(cmd) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def local_ipv4_addresses() -> List[str]:
    found: List[str] = []

    def add(ip: str) -> None:
        if ip and not ip.startswith(("127.", "169.254.", "0.")) and ip not in found:
            found.append(ip)

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass
    try:  # no packet is sent; this only asks the OS which interface would be used
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("10.255.255.255", 1))
        add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    if sys.platform.startswith("win"):
        for match in re.finditer(r"IPv4[^:\r\n]*:\s*(\d+\.\d+\.\d+\.\d+)", _command_output(["ipconfig"])):
            add(match.group(1))
    else:
        for match in re.finditer(r"inet (\d+\.\d+\.\d+\.\d+)/", _command_output(["ip", "-4", "-o", "addr", "show"])):
            add(match.group(1))
    return found
