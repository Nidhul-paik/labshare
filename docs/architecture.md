# Architecture

## Components
| Module | Role |
|---|---|
| `server.py` | Threaded TCP relay. One thread per client; tracks who is online; validates and stores messages. |
| `store.py` | SQLite (`users`, `messages`). One short-lived connection per call, so it is thread-safe. |
| `protocol.py` | `Connection`: one JSON object per line over TCP. |
| `client.py` | Request/response client with one automatic reconnect. No background threads. |
| `ui.py` | Menu UI (`print`/`input` only). |
| `hotspot/` | The only OS-specific code: `linux.py` (nmcli, ufw) and `windows.py` (netsh). |
| `cli.py` | `host`, `client`, `hotspot`, `firewall`, `info`. |

## Message flow
1. Client connects and sends `register` (username, optional token). The host replies with the unread count.
2. `send` stores the message in SQLite (the host never loses it) and replies with the id and whether the recipient is online.
3. The recipient opens the inbox (`inbox`), then `ack` marks a message read. Unread messages survive reconnects and host restarts.

## Protocol (JSON lines)
| Request `action` | Fields | Reply |
|---|---|---|
| `register` | `username`, `token` | `ok`, `username`, `unread` |
| `list` | | `users: [{username, online}]` |
| `send` | `to`, `text`, `kind` (text/code/command), `filename`, `client_id` | `id`, `to`, `recipient_online` |
| `inbox` | | `messages: [{id, sender, kind, filename, body, created_at}]` |
| `count` | | `unread` |
| `ack` | `id` | `ok` |
| `ping` | | `time` |

Errors reply `{"ok": false, "error": "..."}`. `client_id` makes a retried `send` idempotent.

## Design decisions
- **Pull-based inbox**: no push threads, so the UI is simple and identical in cmd.exe and Linux terminals.
- **Standard library only**: nothing to install on lab machines.
- **Case-insensitive usernames**: `Alice` and `alice` are the same person; the first spelling wins.
- **Same username reconnects**: the newest session replaces the old one, which helps after a crash.
- **Limits**: 1 MB per message; messages are text only (no binary files).

## Known limitations
No encryption, no real authentication, one host per lab, no failover, and hotspot capacity depends on the host's Wi-Fi hardware.
The Windows hotspot path could not be tested in the development environment (Linux); see docs/windows-setup.md.
