#!/bin/bash
set -euo pipefail
if [ "$(id -u)" = 0 ]; then
    [[ ${PUID} =~ ^[0-9]+$ && ${PGID} =~ ^[0-9]+$ ]] || exit 64
    [ "$PUID" -gt 0 ] && [ "$PGID" -gt 0 ] || exit 64
    groupmod -o -g "$PGID" retro
    # usermod -u otherwise recursively changes ownership inside an existing HOME.
    usermod -d /nonexistent retro
    usermod -o -u "$PUID" -g "$PGID" retro
    usermod -d /home/retro retro
    mkdir -p /home/retro /tmp/.X11-unix
    chmod 1777 /tmp/.X11-unix
    # Only the mount root, never recursively mutate existing personal data.
    chown "$PUID:$PGID" /home/retro
    groups=()
    for dev in /dev/dri/* /dev/input/*; do
        [ -e "$dev" ] || continue
        gid=$(stat -c %g "$dev")
        name=$(getent group "$gid" | cut -d: -f1)
        if [ -z "$name" ]; then name="device-$gid"; groupadd -g "$gid" "$name"; fi
        groups+=("$name")
    done
    for group in "${groups[@]}"; do usermod -aG "$group" retro; done
    # Wolf may supply an absolute socket rather than a runtime directory.
    parent=${WAYLAND_DISPLAY:-}
    if [[ -n $parent && $parent != /* ]]; then
        parent=${XDG_RUNTIME_DIR:?Relative WAYLAND_DISPLAY requires parent XDG_RUNTIME_DIR}/$parent
        export WAYLAND_DISPLAY=$parent
    fi
    if [[ $parent = /* && -S $parent ]]; then
        chown "$PUID:$PGID" "$parent"
    fi
    export XDG_RUNTIME_DIR=/run/whale-steam
    install -d -m 700 -o "$PUID" -g "$PGID" "$XDG_RUNTIME_DIR"
    export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
    /opt/whale-steam/network-status.sh || echo 'network-status: startup failed; continuing' >&2
    exec gosu retro "$0" "$@"
fi
export HOME=/home/retro
export PATH=/opt/whale-steam/bootstrap-bin:$PATH
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/whale-steam}
umask 022
mkdir -p "$HOME/.steam/ubuntu12_32/steam-runtime" "$HOME/.local/share/whale-steam"
# Keep all downloads, games, compatdata, shader caches and auth under mounted HOME.
# No first-run sentinel suppresses retries after a failed download.
if [ "${1:-}" = --probe ]; then
    shift
    exec "$@"
fi
exec dbus-run-session -- python3 /opt/whale-steam/session.py "$@"
