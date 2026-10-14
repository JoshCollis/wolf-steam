#!/bin/bash
set -euo pipefail
# Isolated local CPU-only test: native-only probes must not report lavapipe as GPU success.
for bits in 32 64; do
    if /opt/whale-steam/vulkan-device-$bits --native; then
        printf 'Native-only probe unexpectedly accepted CPU-only renderer\n' >&2
        exit 1
    fi
done
printf 'NATIVE_ONLY_CPU_REFUSAL_PASS\n'
