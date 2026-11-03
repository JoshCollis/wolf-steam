#!/bin/bash
# Ubuntu publishes standard support by month: May 2031 is inclusive.
# Source: https://ubuntu.com/about/release-cycle (verified 2026-11-03).
set -euo pipefail
# shellcheck disable=SC1090
source "${1:-/etc/os-release}"
today=${2-$(date -u +%F)}
if [[ ${ID:-} != ubuntu || ${VERSION_ID:-} != 26.04 ||
      ! $today =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ || $today > 2031-05-31 ]]; then
    echo 'Unsupported base/date: require Ubuntu 26.04 LTS through May 2031; review release policy.' >&2
    exit 1
fi
