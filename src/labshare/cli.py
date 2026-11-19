"""Command-line entry point:  python -m labshare  <host|client|hotspot|firewall|info>"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import sys
from typing import List, Optional

from . import __version__, hotspot, netutil, ui
from .client import LabShareClient, LabShareError
from .config import (
    DEFAULT_PORT,
    DEFAULT_SSID,
    LINUX_HOTSPOT_IP,
    USERNAME_HELP,
    USERNAME_RE,
    WINDOWS_HOTSPOT_IP,
    default_db_path,
    load_settings,
    save_settings,
)
from .hotspot import HotspotError
from .server import LabShareServer

COMMANDS = ("host", "client", "hotspot", "firewall", "info")


def _utf8_console() -> None:
    """Avoid UnicodeEncodeError when printing code on legacy Windows code pages."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    return input(f"{label}{suffix}: ").strip() or default


def build_parser() -> argparse.ArgumentParser:
    env_pw = os.getenv("LABSHARE_PASSWORD", "")
    env_token = os.getenv("LABSHARE_TOKEN") or None
    parser = argparse.ArgumentParser(
        prog="labshare", description="LabShare - offline text/code messenger for computer labs."
    )
    parser.add_argument("--version", action="version", version=f"LabShare {__version__}")
    sub = parser.add_subparsers(dest="command")

    host = sub.add_parser("host", help="run the message relay (optionally creating the Wi-Fi hotspot)")
    host.add_argument("--bind", default="0.0.0.0", help="address to listen on (default: all)")
    host.add_argument("--port", type=int, default=int(os.getenv("LABSHARE_PORT", DEFAULT_PORT)))
    host.add_argument("--db", default=str(default_db_path()), help="SQLite database file")
    host.add_argument("--token", default=env_token, help="optional shared access token clients must know")
    host.add_argument("--hotspot", action="store_true", help="create the Wi-Fi hotspot before starting")
    host.add_argument("--wifi", default=os.getenv("LABSHARE_WIFI"), help="Wi-Fi interface (Linux), e.g. wlp2s0")
    host.add_argument("--ssid", default=os.getenv("LABSHARE_SSID", DEFAULT_SSID))
    host.add_argument("--password", default=env_pw, help="hotspot password, 8-63 characters")
    host.add_argument("--keep-hotspot", action="store_true", help="leave the hotspot running when the host exits")
    host.add_argument("--no-firewall", action="store_true", help="do not try to open the firewall port")

    client = sub.add_parser("client", help="open the messenger (default command)")
    client.add_argument("--name", help="your username")
    client.add_argument("--host", help="IP address of the LabShare host")
    client.add_argument("--port", type=int, default=int(os.getenv("LABSHARE_PORT", DEFAULT_PORT)))
    client.add_argument("--token", default=env_token, help="access token, if the host uses one")
    client.add_argument("--ssid", help="join this Wi-Fi network first")
    client.add_argument("--password", default=env_pw, help="Wi-Fi password for --ssid")

    hs = sub.add_parser("hotspot", help="start / stop / inspect the Wi-Fi hotspot only")
    hs.add_argument("action", choices=["start", "stop", "status"])
    hs.add_argument("--wifi", default=os.getenv("LABSHARE_WIFI"))
    hs.add_argument("--ssid", default=os.getenv("LABSHARE_SSID", DEFAULT_SSID))
    hs.add_argument("--password", default=env_pw)

    fw = sub.add_parser("firewall", help="allow the LabShare port through the host firewall")
    fw.add_argument("--port", type=int, default=DEFAULT_PORT)

    sub.add_parser("info", help="show version, addresses and file locations")
    return parser


# -- commands --------------------------------------------------------------------
def cmd_host(args) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    hotspot_ip: Optional[str] = None
    started_hotspot = False
    if args.hotspot:
        info = hotspot.start(args.ssid, args.password, args.wifi)
        started_hotspot = True
        hotspot_ip = info.ip
        print(f"[LabShare] Hotspot '{info.ssid}' is up. Host address: {info.ip}")
        for note in info.notes:
            print(f"[LabShare] Note: {note}")
    if not args.no_firewall:
        try:
            print(f"[LabShare] {hotspot.open_firewall(args.port)}")
        except HotspotError as exc:
            print(f"[LabShare] Firewall not changed: {exc}")
    server = LabShareServer(args.bind, args.port, args.db, args.token)
    try:
        server.start()
    except OSError as exc:
        print(f"[LabShare] Cannot listen on port {args.port}: {exc}", file=sys.stderr)
        return 1
    addresses = ([hotspot_ip] if hotspot_ip else []) + [a for a in netutil.local_ipv4_addresses() if a != hotspot_ip]
    print(f"[LabShare] Database: {args.db}")
    print("[LabShare] Clients should connect to one of: " + (", ".join(addresses) or "(no address found)"))
    if args.token:
        print("[LabShare] Access token is required (tell your students the token).")
    print("[LabShare] To chat from this computer, open another terminal:  python -m labshare client --host 127.0.0.1")
    print("[LabShare] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[LabShare] Stopping...")
    finally:
        server.shutdown()
        if started_hotspot and not args.keep_hotspot:
            try:
                hotspot.stop(args.ssid)
            except HotspotError as exc:
                print(f"[LabShare] Could not stop hotspot: {exc}")
    return 0


def cmd_client(args) -> int:
    settings = load_settings()
    try:
        name = args.name or _prompt(f"Your username ({USERNAME_HELP})", settings.get("name", ""))
        if not USERNAME_RE.match(name):
            print(f"[LabShare] Invalid username. Use {USERNAME_HELP}.", file=sys.stderr)
            return 2
        guess = settings.get("host") or (WINDOWS_HOTSPOT_IP if sys.platform.startswith("win") else LINUX_HOTSPOT_IP)
        host = args.host or _prompt("LabShare host IP", guess)
    except (EOFError, KeyboardInterrupt):
        print()
        return 1
    if args.ssid:
        try:
            print(f"[LabShare] Joining Wi-Fi '{args.ssid}' ...")
            hotspot.connect_wifi(args.ssid, args.password)
        except HotspotError as exc:
            print(f"[LabShare] Could not join Wi-Fi automatically: {exc}\n"
                  f"           Connect to '{args.ssid}' from the system Wi-Fi menu, then continue.")
    client = LabShareClient(name, host, args.port, args.token)
    try:
        client.connect()
    except LabShareError as exc:
        print(f"[LabShare] Host refused the connection: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[LabShare] Cannot reach {host}:{args.port} - {exc}", file=sys.stderr)
        print("           Check that you are on the LabShare Wi-Fi, the host is running, and the IP is right.", file=sys.stderr)
        return 1
    save_settings({"name": client.username, "host": host})
    print(f"[LabShare] Connected as {client.username}" + (f" - {client.unread} unread message(s)" if client.unread else ""))
    ui.run(client)
    return 0


def cmd_hotspot(args) -> int:
    if args.action == "start":
        info = hotspot.start(args.ssid, args.password, args.wifi)
        print(f"Hotspot '{info.ssid}' started. Host address: {info.ip}")
        for note in info.notes:
            print(f"Note: {note}")
    elif args.action == "stop":
        hotspot.stop(args.ssid)
        print("Hotspot stopped.")
    else:
        print(hotspot.status())
    return 0


def cmd_firewall(args) -> int:
    print(hotspot.open_firewall(args.port))
    return 0


def cmd_info(_args) -> int:
    print(f"LabShare {__version__}  |  Python {platform.python_version()}  |  {platform.system()} {platform.release()}")
    print(f"Default port     : {DEFAULT_PORT}")
    print(f"Default database : {default_db_path()}")
    print(f"This computer    : {', '.join(netutil.local_ipv4_addresses()) or '(no network address found)'}")
    print(f"Usual hotspot IP : {WINDOWS_HOTSPOT_IP if sys.platform.startswith('win') else LINUX_HOTSPOT_IP}")
    return 0


HANDLERS = {"host": cmd_host, "client": cmd_client, "hotspot": cmd_hotspot, "firewall": cmd_firewall, "info": cmd_info}


def main(argv: Optional[List[str]] = None) -> int:
    _utf8_console()
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help", "--version")):
        argv.insert(0, "client")  # `labshare --name x` behaves like `labshare client --name x`
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.command](args)
    except HotspotError as exc:
        print(f"[LabShare] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print()
        return 130
