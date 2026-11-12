#!/bin/bash
set -euo pipefail
export WLR_BACKENDS=headless WLR_RENDERER=pixman WLR_LIBINPUT_NO_DEVICES=1
export SWAYSOCK=$XDG_RUNTIME_DIR/parent-test.sock
printf 'output * mode 1280x720@60Hz\n' >"$XDG_RUNTIME_DIR/parent-test.conf"
dbus-run-session -- sway --unsupported-gpu -c "$XDG_RUNTIME_DIR/parent-test.conf" >"$XDG_RUNTIME_DIR/parent-test.log" 2>&1 &
p=$!
trap 'kill "$p" 2>/dev/null || true' EXIT
for _ in $(seq 1 100); do [ -S "$SWAYSOCK" ] && break; sleep .1; done
export WAYLAND_DISPLAY=wayland-1
for mode in '1280 720 60' '1280 720 90' '1280 720 120' '1280 720 144' '3440 1440 100' '5120 1440 240'; do
    read -r GAMESCOPE_WIDTH GAMESCOPE_HEIGHT rate <<<"$mode"
    export GAMESCOPE_WIDTH GAMESCOPE_HEIGHT
    swaymsg output '*' mode "${GAMESCOPE_WIDTH}x${GAMESCOPE_HEIGHT}@${rate}Hz" >/dev/null
    export GAMESCOPE_REFRESH=$rate
    python3 -c 'import sys,os; sys.path.insert(0,"/opt/whale-steam"); import session; m=session.agree(session.requested(os.environ),session.read_parent(os.environ)); print("REAL_PARENT_AGREEMENT_PASS",m)'
done
export GAMESCOPE_REFRESH=60
set +e
python3 /opt/whale-steam/session.py /usr/bin/true >"$XDG_RUNTIME_DIR/mismatch.log" 2>&1
status=$?
set -e
cat "$XDG_RUNTIME_DIR/mismatch.log"
test "$status" -eq 1
grep -q 'disagrees with parent' "$XDG_RUNTIME_DIR/mismatch.log"
if grep -q '\[gamescope\]' "$XDG_RUNTIME_DIR/mismatch.log"; then exit 1; fi
printf 'REAL_PARENT_MISMATCH_REFUSED_BEFORE_COMPOSITOR_PASS\n'
