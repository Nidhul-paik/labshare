# Windows setup

Install Python 3.8+ from python.org with **Add Python to PATH** ticked. Everything works in `cmd.exe` and PowerShell.

> The Windows hotspot code was written to Microsoft's documented `netsh` commands but could not be run in the
> development environment (Linux). Test it on one machine first; the fallbacks below always work.

## Host
Open **Command Prompt as Administrator** in the project folder:
```
py -3 run_labshare.py host --hotspot --ssid LabShare --password LabShare123
```
This uses `netsh wlan set/start hostednetwork`, adds a Windows Firewall rule for port 50555, and prints the host
address (normally `192.168.137.1`).

### If the hosted network is not supported
Many recent Wi-Fi drivers dropped it (`netsh wlan show drivers` shows "Hosted network supported : No").
Alternatives, any of which works with LabShare:
1. **Mobile hotspot**: Settings > Network & Internet > Mobile hotspot, set name/password, turn on. Then run
   `py -3 run_labshare.py host` (without `--hotspot`). Some Windows versions insist on an internet connection to start it.
2. A **phone hotspot or Wi-Fi router** that everyone joins; run `host` on one PC and give out its IP (`run_labshare.py info`).
3. Make a **Linux** machine the host.

## Clients
```
py -3 run_labshare.py client --name arun --host 192.168.137.1
```
Join the Wi-Fi first (or add `--ssid LabShare --password LabShare123` to join from the command line).
If the connection fails, run on the host as Administrator: `py -3 run_labshare.py firewall`.
