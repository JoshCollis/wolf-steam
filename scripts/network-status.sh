#!/bin/bash
# Container-local system services for Steam's libnm status, not network setup.
set -euo pipefail
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket

warn() { printf 'network-status: %s\n' "$*" >&2; }
bus_ready() {
    timeout --kill-after=1s 1s dbus-send --system --type=method_call --print-reply \
        --dest=org.freedesktop.DBus /org/freedesktop/DBus \
        org.freedesktop.DBus.GetId >/dev/null 2>&1
}
nm_ready() {
    [ "$(timeout --kill-after=1s 1s nmcli -t -f RUNNING general 2>/dev/null)" = running ]
}
# Only wait for local services. Offline egress must never prevent Steam starting.
wait_ready() {
    local attempt
    for attempt in {1..20}; do
        if "$@"; then return 0; fi
        sleep 0.1
    done
    return 1
}

mkdir -p /run/dbus
# Do not connect to a host bus, even if an inherited environment names one.
if ! bus_ready; then
    dbus-uuidgen --ensure
    timeout --kill-after=1s 3s dbus-daemon --system --fork --nopidfile \
        --address="$DBUS_SYSTEM_BUS_ADDRESS" || warn 'system D-Bus failed to start'
fi
if ! wait_ready bus_ready; then
    warn 'local system D-Bus not ready; continuing without network status'
    exit 0
fi

# Wolf runners may grant NET_ADMIN. Remove it from all capability sets for
# this daemon and its descendants: NM must not change Docker's interfaces/routes.
# Never fall back to launching an unrestricted NetworkManager on failure.
setpriv --bounding-set=-net_admin --inh-caps=-net_admin --ambient-caps=-net_admin \
    --no-new-privs NetworkManager --no-daemon \
    --config=/etc/NetworkManager/NetworkManager.conf &
if ! wait_ready nm_ready; then
    warn 'NetworkManager not ready; continuing without network status'
    exit 0
fi
# Trigger a genuine check, bounded independently of the periodic NM check.
# Failure/offline is informative, not a reason to block a user's offline session.
if ! status=$(timeout --kill-after=1s 5s nmcli --wait 4 networking connectivity check 2>&1); then
    warn "connectivity check unavailable/offline: $status"
else
    warn "connectivity: $status"
fi
