#!/bin/bash
set -euo pipefail
glxinfo -B >"$XDG_RUNTIME_DIR/glx.log" 2>&1
exec stdbuf -oL glxgears >"$XDG_RUNTIME_DIR/gears.log" 2>&1
