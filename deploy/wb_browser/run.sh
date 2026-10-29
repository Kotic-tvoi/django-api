#!/usr/bin/env bash
# One-shot VPS browser pilot; run as dedicated unprivileged user.
set -Eeuo pipefail
umask 077

if (( EUID == 0 )); then
  echo "ERROR: Do not run the browser as root." >&2
  exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${WB_BROWSER_PYTHON:-$HOME/.venvs/wb-browser/bin/python}"
PASSFILE="$HOME/.config/wb-browser/vnc.pass"
NOVNC_WEB="/usr/share/novnc"
CACHE="$HOME/.cache/wb-vps-browser"
DISPLAY_NUMBER="${WB_DISPLAY_NUMBER:-92}"
VNC_PORT="${WB_VNC_PORT:-5922}"
NOVNC_PORT="${WB_NOVNC_PORT:-6081}"

[[ "$DISPLAY_NUMBER" =~ ^[0-9]+$ && "$VNC_PORT" =~ ^[0-9]+$ && "$NOVNC_PORT" =~ ^[0-9]+$ ]] || {
  echo "ERROR: display and port values must be numeric." >&2
  exit 2
}
for bin in Xvfb xauth xdpyinfo openbox x11vnc websockify openssl curl; do
  command -v "$bin" >/dev/null || { echo "ERROR: $bin is not installed." >&2; exit 2; }
done
[[ -x "$PYTHON" ]] || { echo "ERROR: missing Python virtualenv $PYTHON" >&2; exit 2; }
[[ -f "$PASSFILE" ]] || {
  echo "ERROR: create the VNC password interactively: x11vnc -storepasswd $PASSFILE" >&2
  exit 2
}
[[ -f "$NOVNC_WEB/vnc.html" ]] || { echo "ERROR: noVNC static files not found in $NOVNC_WEB." >&2; exit 2; }

mkdir -p "$CACHE" "$HOME/.local/share/wb-vps-browser"
WORKDIR="$(mktemp -d "$CACHE/pilot.XXXXXXXX")"
export DISPLAY=":$DISPLAY_NUMBER"
export XAUTHORITY="$WORKDIR/Xauthority"
touch "$XAUTHORITY"
xauth -f "$XAUTHORITY" add "$DISPLAY" . "$(openssl rand -hex 16)" >/dev/null

pids=()
cleanup() {
  echo "Stopping pilot processes and closing browser..." >&2
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
  rm -rf -- "$WORKDIR"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

Xvfb "$DISPLAY" -screen 0 1366x768x24 -auth "$XAUTHORITY" -nolisten tcp >"$WORKDIR/xvfb.log" 2>&1 &
pids+=("$!")
ready=0
for _ in $(seq 1 40); do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then ready=1; break; fi
  sleep 0.25
done
[[ "$ready" == 1 ]] || { echo "ERROR: Xvfb did not start. See $WORKDIR/xvfb.log" >&2; exit 1; }

openbox >"$WORKDIR/openbox.log" 2>&1 &
pids+=("$!")
x11vnc -norc -display "$DISPLAY" -no6 -localhost -rfbport "$VNC_PORT" \
  -rfbauth "$PASSFILE" -forever -shared -noxdamage -quiet -nofilexfer \
  >"$WORKDIR/x11vnc.log" 2>&1 &
pids+=("$!")

websockify --web "$NOVNC_WEB" "127.0.0.1:$NOVNC_PORT" "127.0.0.1:$VNC_PORT" \
  >"$WORKDIR/websockify.log" 2>&1 &
pids+=("$!")
ready=0
for _ in $(seq 1 40); do
  if curl -fsS --max-time 1 "http://127.0.0.1:$NOVNC_PORT/vnc.html" -o /dev/null; then
    ready=1; break
  fi
  sleep 0.25
done
[[ "$ready" == 1 ]] || { echo "ERROR: local noVNC failed to start." >&2; exit 1; }

echo "noVNC ready on localhost:$NOVNC_PORT; access only through HTTPS/Nginx with authentication."
echo "VNC on localhost:$VNC_PORT; not intended for direct public exposure."
echo "Press Ctrl+C to stop. Logins and browser data remain in the private profile."
"$PYTHON" "$SCRIPT_DIR/browser.py"
