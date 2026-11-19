# LabShare

An offline text / code / command messenger for computer labs. One computer creates a Wi-Fi
hotspot and runs the relay; everyone else joins and chats from a terminal. **No internet, no
extra hardware, no third-party Python packages.** Works on **Windows (cmd, PowerShell)** and
**Linux (any terminal)**, and the two can talk to each other.

```
 Student PC (Windows)          Host PC (Linux or Windows)          Student PC (Linux)
 python -m labshare client --->  hotspot + relay + SQLite  <--- python -m labshare client
                  \_____________ Wi-Fi hotspot "LabShare" ____________/
```

## Features
- Send **text, code or commands**, including multi-line content, to any user.
- Messages to offline users are stored in SQLite and appear when they next connect.
- Read, **copy to clipboard**, **save as a file**, or mark as read.
- Optional shared **access token**, 1 MB message limit, automatic reconnect.
- Menu-driven UI with plain `print`/`input`: no colours or curses, so it works in `cmd.exe`.

## Requirements
- Python 3.8 or newer (on Windows tick *Add Python to PATH* when installing).
- Host: a Wi-Fi adapter that can act as an access point. Linux needs NetworkManager (`nmcli`).
- Clients: any Wi-Fi adapter.

## Quick start (no installation)
Run these from the project folder. `python` can be `py -3` on Windows, `python3` on Linux.

**1. Host computer** (Windows: open *Command Prompt as Administrator*; Linux: use `sudo`)
```
python run_labshare.py host --hotspot --ssid LabShare --password LabShare123
```
Linux needs the Wi-Fi interface if it is not auto-detected: `--wifi wlp2s0`.
The host prints the address students must use (Linux usually `10.42.0.1`, Windows `192.168.137.1`).

**2. Everyone else** (normal user is fine): join the `LabShare` Wi-Fi, then
```
python run_labshare.py client
```
It asks for your username and the host IP (and remembers them next time). Or in one line:
```
python run_labshare.py client --name arun --host 10.42.0.1
```
The host user can also chat: open a second terminal and run
`python run_labshare.py client --host 127.0.0.1`.

Helper scripts do the same thing: `scripts\host.bat`, `scripts\client.bat` (Windows) and
`scripts/host.sh`, `scripts/client.sh` (Linux).

Optional install: `pip install .` then use `labshare host ...` / `labshare client ...`.

## Using the menu
```
1. Show users          who is registered, and who is ONLINE
2. Send                pick a user, choose text/code/command, paste, finish with .END
3. Inbox (N unread)    open a message -> copy / save / mark as read
4. Exit
```
Finish multi-line input with `.END` on its own line (Ctrl+D on Linux, Ctrl+Z then Enter on Windows also work).
Saved files go to a `received/` folder next to where you started LabShare.

## Commands
| Command | Purpose |
|---|---|
| `host [--hotspot] [--token T] [--port N] [--db FILE]` | run the relay, optionally creating the hotspot |
| `client [--name N] [--host IP] [--token T] [--ssid S --password P]` | open the messenger |
| `hotspot start\|stop\|status` | hotspot only |
| `firewall [--port N]` | allow the port through ufw / Windows Firewall |
| `info` | show version, this computer's addresses, database path |

Settings can also come from environment variables: `LABSHARE_PORT`, `LABSHARE_SSID`, `LABSHARE_PASSWORD`,
`LABSHARE_WIFI`, `LABSHARE_TOKEN`, `LABSHARE_DB`.

## Troubleshooting
- **Cannot reach host**: confirm you joined the hotspot, run `python run_labshare.py info` on the host to see
  its address, then `ping <host-ip>` from the client. Allow the port with `firewall` (needs admin/sudo).
- **Windows: "hosted network not supported"**: many newer drivers removed it. Use *Settings > Network &
  Internet > Mobile hotspot* (or a phone/router hotspot) and run the host without `--hotspot`.
  See [docs/windows-setup.md](docs/windows-setup.md).
- **Linux: hotspot fails**: check `nmcli device status` and AP support (`iw list`). See [docs/linux-setup.md](docs/linux-setup.md).
- **Linux clipboard**: install `xclip` or `wl-clipboard`; otherwise use *Save to file*.

## Security
Traffic is **not encrypted** and usernames are not passwords. Use a hotspot password, the optional
`--token`, and a trusted lab only. Do not share secrets through LabShare.

## Project layout
```
src/labshare/   config, protocol, store (SQLite), server, client, ui, cli, clipboard, netutil, hotspot/
tests/          28 unit + integration tests (python -m unittest discover -v)
docs/           architecture, Windows and Linux setup, git workflow
scripts/        host/client launchers for .bat and .sh
systemd/        optional Linux auto-start service for the host
```
More in [docs/architecture.md](docs/architecture.md). Licensed under MIT.
