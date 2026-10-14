#!/bin/bash
set -euo pipefail
volume=$(docker volume create whale-steam-test-$(date +%s)-$$)
trap 'docker volume rm "$volume" >/dev/null' EXIT
docker run --rm -v "$volume:/home/retro" whale-steam:local-test --probe bash -c '
    mkdir -p "$HOME/.steam/test-library/steamapps/compatdata/123" "$HOME/.config"
    printf prefix-sentinel >"$HOME/.steam/test-library/steamapps/compatdata/123/sentinel"
    printf user-preference >"$HOME/.config/whale-test-preference"
'
docker run --rm --security-opt seccomp=unconfined --security-opt apparmor=unconfined \
    -v "$volume:/home/retro" whale-steam:local-test --probe /opt/whale-steam/smoke.sh
docker run --rm -v "$volume:/home/retro" whale-steam:local-test --probe bash -c '
    test "$(cat "$HOME/.steam/test-library/steamapps/compatdata/123/sentinel")" = prefix-sentinel
    test "$(cat "$HOME/.config/whale-test-preference")" = user-preference
    test -x "$HOME/.steam/root/ubuntu12_32/steam"
    test -x "$HOME/.steam/root/ubuntu12_64/steamwebhelper"
    test -s "$HOME/.steam/root/deb-installer/version"
    echo PERSISTENCE_RECREATION_PASS
'
docker run --rm -e PUID=1234 -e PGID=1234 -v "$volume:/home/retro" whale-steam:local-test --probe bash -c '
    test "$(id -u)" = 1234
    test "$(stat -c %u "$HOME")" = 1234
    test "$(stat -c %u "$HOME/.config/whale-test-preference")" = 1000
    echo UID_REMAP_WITHOUT_RECURSIVE_HOME_CHOWN_PASS
'
