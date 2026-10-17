#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
export IMAGE=${IMAGE:?Set IMAGE to the image to verify}
docker run --rm --cpus 2 --memory 2g --pids-limit 512 "$IMAGE" --probe python3 /opt/whale-steam/tests/power-bus.py
docker run --rm --cpus 2 --memory 2g --pids-limit 512 "$IMAGE" --probe bash /opt/whale-steam/tests/vulkan-device.sh
docker run --rm --cpus 2 --memory 2g --pids-limit 512 "$IMAGE" --probe bash /opt/whale-steam/tests/native-refusal.sh
docker run --rm --cpus 2 --memory 2g --pids-limit 512 "$IMAGE" --probe bash /opt/whale-steam/tests/parent-agreement.sh
bash tests/persistence.sh
# All homes above are container-private disposable homes. No live GPU or Wolf changes.
