#!/bin/bash
# Software bootstrap only. The managed session is exercised by steam-gpu.sh
# under native Gamescope, rather than pretending Sway is a SteamOS session.
exec /usr/games/steam -silent >"$XDG_RUNTIME_DIR/steam.log" 2>&1
