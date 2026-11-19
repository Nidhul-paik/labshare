# Changelog

## 1.0.0
- Rewrote the single-file Ubuntu prototype as a package that runs on **Windows and Linux** (cmd, PowerShell, any terminal).
- New: Windows hotspot (netsh), Windows Firewall rule, Wi-Fi join on both systems.
- New: message types (text / code / command), suggested file names, case-insensitive usernames.
- New: optional shared access token; `--token` / `LABSHARE_TOKEN`.
- Fixed: the prototype host dropped idle clients after 15 s. Idle clients now stay connected and reconnect automatically.
- Fixed: retried sends can no longer create duplicate messages.
- Default database is now `labshare.db` (the old `messages.db` schema is not reused).
- CLI changed: `--role host-service` is now `host --hotspot`.
