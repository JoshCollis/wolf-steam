#!/bin/bash
# Run on a GPU host. No Wolf socket, configuration, profile or display is mounted.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${IMAGE:?Set IMAGE to the isolated candidate image tag}"
render=${RENDER_DEVICE:-/dev/dri/renderD128}
card=${CARD_DEVICE:-/dev/dri/card0}
test -c "$render"
test -c "$card"
docker run --rm --network none --cpus 1 --memory 1g --pids-limit 128 \
    --device "$render" --entrypoint /bin/bash "$IMAGE" -c '
        /opt/whale-steam/vulkan-device-64 --native
        /opt/whale-steam/vulkan-device-32 --native
    '
python3 tests/gamescope_focus.py --image "$IMAGE" --card "$card" --render "$render"
docker run --rm --cpus 2 --memory 3g --memory-swap 3g --shm-size 256m --pids-limit 512 \
    --device "$render" --device "$card" \
    --security-opt seccomp=unconfined --security-opt apparmor=unconfined \
    "$IMAGE" --probe bash /opt/whale-steam/tests/steam-gpu.sh
