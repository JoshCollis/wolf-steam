#!/bin/bash
exec /usr/games/steam -silent >"$XDG_RUNTIME_DIR/steam.log" 2>&1
