# wolf-steam

Steam Big Picture container for [Games-on-Whales Wolf](https://github.com/games-on-whales/wolf).
Ubuntu 26.04, gamescope, and amd64/i386 Mesa. AMD/Intel graphics only;
proprietary NVIDIA driver injection is not included.

```sh
docker pull ghcr.io/joshcollis/wolf-steam:latest
```

Pushes to `main` test and publish `latest`, `main`, and `sha-<commit>` to GHCR.
Use a digest to pin a deployment.

## Scheduled dependency refresh

Every Monday at **05:43 UTC**, and on push/manual runs, CI resolves the current
official `ubuntu:26.04` base to an immutable digest for both build stages. It
builds explicitly for `linux/amd64` with `--pull --no-cache`, updates APT indexes
with errors fatal, upgrades within 26.04, and installs the amd64/i386 dependencies.
It does not track `latest` Ubuntu or migrate to 26.10. The Dockerfile's local
default remains digest-pinned; overriding `BASE_IMAGE` also requires the matching
`BASE_DIGEST` label argument. Use CI's uncached build flags for a local refresh.

[Ubuntu 26.04 LTS has standard support through May 2031](https://ubuntu.com/about/release-cycle)
(verified November 2026). Builds reject another release or a date after that
month. Package coverage varies by component: LTS support does not guarantee
every Universe/Multiverse Steam or gaming package receives every security fix;
no Ubuntu Pro/ESM entitlement is assumed. Updates follow the available 26.04
repositories, not arbitrary upstream releases.

Each image contains `/usr/share/wolf-steam/{base-image.txt,base-os-release,packages.json,apt-policy.txt}`;
CI retains these as a run-specific package-evidence artifact. The build compares
every installed package version (including both architectures) with its freshly
indexed APT candidate and fails on a mismatch. This is timestamped repository
snapshot evidence, not proof from a moving container tag or a perpetual security
guarantee. Only after software acceptance does `main` publish that exact image
as `latest`, `main`, `sha-<commit>` and unique `run-<id>-<attempt>`; scheduled
same-commit builds can change packages, so use the run tag or digest for identity.
PRs and non-main manual runs never publish.

Steam self-updates inside persisted HOME; the container tag is **not** the Steam
client version. Refreshes preserve HOME, libraries and existing game/Proton
prefixes: no mass prefix migration or forced Proton updates. Publishing/pulling
does not adopt an image in a live session. There is no Watchtower or automatic
restart; choose a maintenance window to recreate the app after saving games.

## Configuration

Start with [`examples/wolf.config.toml`](examples/wolf.config.toml) in a separate
profile. Review its unconfined seccomp/AppArmor settings before deployment.

- Persist `/home/retro` per profile/app. Steam, login state, Proton prefixes,
  and shader caches live there. External libraries also need persistent mounts.
- `PUID`/`PGID` default to `1000`. Existing files must have matching ownership;
  startup does not recursively change it.
- Pass GPU/input devices and Wolf's audio socket. Device groups are detected
  from the mounted devices. No host D-Bus socket is needed.
- Wolf must supply `WAYLAND_DISPLAY`, `GAMESCOPE_WIDTH`, `GAMESCOPE_HEIGHT`, and
  `GAMESCOPE_REFRESH` (60, 90, 120, or 144 Hz).
- Keep `RUN_SWAY=false` and `RUN_GAMESCOPE=true`. A mismatched parent mode fails
  startup. A changed mode exits with code 75; recreate the lobby with the same home.

Steam downloads from Valve on first launch and updates in the persistent home.
NetworkManager provides container-local connectivity status without controlling
Docker's interfaces or DNS. Offline status does not block startup.

## Session controls

Desktop and Power Off end this app. Restart restarts Steam. These actions never
control host power. Suspend/hibernate are unavailable; Steam decides whether to
hide their menu items. Save games before ending a session.

Steam runs with `-steamos3` for session hooks. This may select its SteamOS client
channel and expose unsupported OS settings. Set `STEAM_OS_SESSION_HOOKS=0` to
disable it if an overlay/client regression occurs; Desktop switching may then
stop working. This image does not provide SteamOS updates or a desktop environment.

Allow at least 55 seconds for container shutdown so Steam can save state.
IBus supports text entry; Steam volume controls use Wolf's PulseAudio server.
`/opt/whale-steam/audio-check` reports the current sink; it also accepts
`volume 50%`, `mute`, and `unmute`.

## Verification

CI runs software tests against the built image. On a GPU test host, run
`IMAGE=<candidate-tag> bash tests/run-gpu.sh` for native Vulkan, focus, and Steam
restart/exit checks. Tests use disposable containers, not Wolf profiles.

Before rollout, check controller keyboard entry, in-game overlays, audio, menu
actions, and reconnects in a separate Wolf profile. Headless tests do not verify
Moonlight playback or end-to-end frame cadence.

## License

MIT. See [`NOTICE.md`](NOTICE.md) for third-party attribution and licensing.
Not an official Valve, Ubuntu, Wolf, or GoW product.
