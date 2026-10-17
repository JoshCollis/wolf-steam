#!/bin/bash
# Disposable native Gamescope/Steam session: no Wolf socket or existing home.
set -euo pipefail
gamescope=/usr/games/gamescope
dbus-run-session -- "$gamescope" --backend headless -e -W 1280 -H 720 -- \
    python3 /opt/whale-steam/steam-session.py >"$XDG_RUNTIME_DIR/gamescope.log" 2>&1 &
compositor=$!
cleanup() {
    status=$?
    if [ "$status" -ne 0 ]; then
        tail -n 100 "$XDG_RUNTIME_DIR/gamescope.log" || true
        tail -n 60 "$HOME/.steam/root/logs/console-linux.txt" || true
    fi
    kill "$compositor" 2>/dev/null || true
}
trap cleanup EXIT
for _ in $(seq 1 300); do
    kill -0 "$compositor" || { echo 'Gamescope exited during startup' >&2; exit 1; }
    if pgrep -x steamwebhelper >/dev/null && [ -s "$HOME/.steam/steam.pid" ]; then break; fi
    if [ -e "$XDG_RUNTIME_DIR/steam-session.done" ]; then
        echo 'Steam session exited before UI startup' >&2; exit 1
    fi
    sleep 1
done
pgrep -x steamwebhelper >/dev/null
echo NATIVE_STEAM_UI_PROCESS_PASS
original_pid=$(cat "$HOME/.steam/steam.pid")
dbus-send --system --print-reply --dest=org.freedesktop.login1 \
    /org/freedesktop/login1 org.freedesktop.login1.Manager.Reboot boolean:false
for _ in $(seq 1 180); do
    current_pid=$(cat "$HOME/.steam/steam.pid" 2>/dev/null || true)
    if [ -n "$current_pid" ] && [ "$current_pid" != "$original_pid" ] && \
        pgrep -x steamwebhelper >/dev/null; then break; fi
    sleep 1
done
test -n "$current_pid"
test "$current_pid" != "$original_pid"
pgrep -x steamwebhelper >/dev/null
echo NATIVE_STEAM_RESTART_PASS
/opt/whale-steam/steamos-session-select desktop
for _ in $(seq 1 250); do
    [ ! -e "$XDG_RUNTIME_DIR/steam-session.done" ] || break
    sleep .2
done
test "$(cat "$XDG_RUNTIME_DIR/steam-session.done")" = 0
echo NATIVE_STEAM_DESKTOP_EXIT_PASS
