#!/bin/bash
set -euo pipefail
export WLR_BACKENDS=headless WLR_RENDERER=pixman WLR_LIBINPUT_NO_DEVICES=1
export GSK_RENDERER=cairo LIBGL_ALWAYS_SOFTWARE=1
export SWAYSOCK=$XDG_RUNTIME_DIR/smoke.sock
printf 'xwayland force
output * mode 1280x720@60Hz
' >"$XDG_RUNTIME_DIR/smoke.conf"
dbus-run-session -- sway --unsupported-gpu -c "$XDG_RUNTIME_DIR/smoke.conf" >"$XDG_RUNTIME_DIR/sway.log" 2>&1 &
p=$!
cleanup() {
    status=$?
    if [ "$status" -ne 0 ]; then
        ps -eo pid,ppid,args
        tail -n 80 "$XDG_RUNTIME_DIR/steam.log" 2>/dev/null || true
    fi
    kill "$p" 2>/dev/null || true
}
trap cleanup EXIT
for _ in $(seq 1 100); do [ -S "$SWAYSOCK" ] && break; sleep .1; done
for rate in 60 90 120 144; do
    swaymsg output '*' mode "1280x720@${rate}Hz" >/dev/null
    swaymsg -t get_outputs -r | jq -e ".[0].current_mode.refresh == $((rate*1000))" >/dev/null
    echo "HEADLESS_CONTROL_MODE_PASS=$rate (not a nested cadence certification)"
done
swaymsg exec /opt/whale-steam/render-probe.sh >/dev/null
sleep 8
cat "$XDG_RUNTIME_DIR/glx.log"
grep -q 'OpenGL renderer string:' "$XDG_RUNTIME_DIR/glx.log"
for _ in $(seq 1 30); do
    swaymsg -t get_tree -r | jq -e '[.. | objects | select(.name? == "glxgears")] | length > 0' >/dev/null && break
    sleep 1
done
swaymsg -t get_tree -r | jq -e '[.. | objects | select(.name? == "glxgears")] | length > 0' >/dev/null
cat "$XDG_RUNTIME_DIR/gears.log"
grep -q 'frames in' "$XDG_RUNTIME_DIR/gears.log"
swaymsg exec /opt/whale-steam/bootstrap-probe.sh >/dev/null
for _ in $(seq 1 120); do
    if pgrep -f 'steamwebhelper.*steamwebhelper' >/dev/null && [ -s "$HOME/.steam/root/ubuntu12_32/steam" ]; then break; fi
    sleep 2
done
cat "$XDG_RUNTIME_DIR/steam.log"
[ -s "$HOME/.steam/root/ubuntu12_32/steam" ]
pgrep -a steamwebhelper
printf 'STEAM_DOWNLOADED_AND_WEBHELPER_RUNNING
'
