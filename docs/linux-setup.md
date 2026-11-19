# Linux setup

Needs Python 3.8+, NetworkManager (`nmcli`) and, on the host, a Wi-Fi adapter that supports AP mode.

```bash
nmcli device status                       # find the Wi-Fi interface (e.g. wlp2s0)
iw list | grep -A 15 "Supported interface modes"   # look for "AP"
sudo python3 run_labshare.py host --hotspot --wifi wlp2s0 --ssid LabShare --password LabShare123
```
Clients: join `LabShare`, then `python3 run_labshare.py client --host 10.42.0.1`.

## Firewall
`host` tries `ufw allow 50555/tcp` automatically (needs root). Without ufw, open the port in your own firewall.

## Auto-start the host at boot (optional)
```bash
sudo mkdir -p /opt/labshare && sudo cp -r src /opt/labshare/
sudo cp systemd/labshare.service /etc/systemd/system/
sudo cp systemd/labshare.env.example /etc/default/labshare
sudo nano /etc/default/labshare && sudo chmod 600 /etc/default/labshare
sudo systemctl daemon-reload && sudo systemctl enable --now labshare
sudo journalctl -u labshare -f
```
Clipboard support: `sudo apt install xclip` (X11) or `wl-clipboard` (Wayland).
