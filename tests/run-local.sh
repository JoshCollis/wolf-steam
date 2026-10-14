#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
docker build --pull=false --build-arg IMAGE_SOURCE="${IMAGE_SOURCE:-}" -t whale-steam:local-test .
docker run --rm whale-steam:local-test --probe bash /opt/whale-steam/tests/vulkan-device.sh
docker run --rm whale-steam:local-test --probe bash /opt/whale-steam/tests/native-refusal.sh
docker run --rm whale-steam:local-test --probe bash /opt/whale-steam/tests/parent-agreement.sh
bash tests/persistence.sh
# All homes above are container-private disposable homes. No live GPU or Wolf changes.
