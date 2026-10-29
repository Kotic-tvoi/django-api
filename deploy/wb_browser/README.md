# WB server-side browser pilot — manual login over noVNC

This is **stage 1 only**: test if WB works from the VPS IP and whether its catalog returns 200. Do not assume cookies from a VPS browser can be replayed with Python requests. Existing Django endpoints, Google Apps Script and Huckster are unchanged.

Security: Chrome runs as a **dedicated, non-root system user**, with a persistent profile. Xvfb and VNC expose no public TCP listener; websockify binds to 127.0.0.1:6081. Nginx must enforce HTTPS + Basic Auth; VNC itself has a separate password. Grant access only to designated administrators. Do not use other production accounts in this browser.

## Preparation on Ubuntu VPS

Run as administrator over SSH (adapt the repo path if needed):

```bash
sudo apt-get update
sudo apt-get install -y xvfb xauth x11-utils openbox x11vnc novnc websockify apache2-utils python3-venv python3-pip curl openssl
sudo useradd --create-home --shell /bin/bash wb-browser
sudo -u wb-browser -H bash -lc 'python3 -m venv ~/.venvs/wb-browser && ~/.venvs/wb-browser/bin/python -m pip install playwright && ~/.venvs/wb-browser/bin/python -m playwright install chromium'
```

Some Ubuntu installations require additional Chromium system packages. If Playwright reports missing libraries, run this once as root: `/home/wb-browser/.venvs/wb-browser/bin/python -m playwright install-deps chromium`. This changes OS packages but not Django or Nginx.

Create a VNC password **interactively** under the dedicated account:

```bash
sudo -u wb-browser -H bash -lc 'mkdir -p ~/.config/wb-browser && chmod 700 ~/.config/wb-browser && x11vnc -storepasswd ~/.config/wb-browser/vnc.pass && chmod 600 ~/.config/wb-browser/vnc.pass'
```

Check that ports are not already in use and no publicly exposed services are configured:

```bash
sudo ss -lntp | grep -E ':(5922|6081)\b' || true
```

## Test locally before changing Nginx

Start **inside a dedicated SSH session** (this process stays attached while testing):

```bash
sudo -u wb-browser -H bash -lc 'cd /opt/django-app/django-api && bash deploy/wb_browser/run.sh'
```

In another SSH session:

```bash
curl -I http://127.0.0.1:6081/vnc.html
sudo ss -lntp | grep -E ':(5922|6081)\b'
```

Both ports must be bound to 127.0.0.1 only. Never open port 5922 or 6081 in the firewall. Do not configure public noVNC until this check passes.

## Protect the web interface

1. Create a Basic Auth file: `sudo htpasswd -c /etc/nginx/wb-browser.htpasswd wb-operator`. Set a long, unique password.
2. Restrict file permissions for nginx (e.g. root:www-data mode 640, verify your actual worker group).
3. Copy the **contents** of `nginx-location.example.conf` into the currently active HTTPS `server { }` for your real domain. Do not replace the existing vhost or certificate settings.
4. Run `sudo nginx -t`, then `sudo systemctl reload nginx`.
5. Open `https://YOUR-DOMAIN/wb-browser/`. Enter the HTTP password, then the *separate* VNC password. Confirm the live browser view works, then log in to WB manually if allowed.

The browser logs catalog HTTP status codes and partner/destination IDs **only**, without cookies, tokens, URLs or response bodies. If WB blocks the VPS IP/automation, stop here; do not try to bypass security controls.

## Rollback

Stop the pilot with Ctrl+C in its SSH session. Remove only the added Nginx `location` blocks, `nginx -t`, reload Nginx. Existing Django will continue working unchanged. The stored browser profile remains under `/home/wb-browser/.local/share/wb-vps-browser/profile` until deliberately deleted.

## Not yet implemented

No automatic session transfer, scheduled browser restart, HTTPS API to synchronize headers, automatic Django retrieval, or Google Apps Script integration. This is intentional: first validate login and successful catalog responses from the VPS. Do not install a persistent systemd service or share VNC with all spreadsheet users yet.
