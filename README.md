# wolf-steam

Steam container for [Games-on-Whales Wolf](https://github.com/games-on-whales/wolf),
using Ubuntu 26.04 LTS, gamescope, and native amd64/i386 Mesa packages.

## Image

```sh
docker pull ghcr.io/joshcollis/wolf-steam:latest
```

Pushes to `main` build and test the image, then publish `latest`, `main`, and
`sha-<full commit SHA>` tags to GHCR. Pull requests run the same tests without
publishing. For reproducible deployments, use an image digest instead of `latest`.
GHCR package visibility is managed separately from repository visibility; the
package must be public to allow anonymous pulls.

## Wolf configuration

See [`examples/wolf.config.toml`](examples/wolf.config.toml). Add the app to a
separate profile first and check Wolf's generated device, audio, input, and home mounts.
The example uses unconfined seccomp/AppArmor for Steam Runtime compatibility;
review those permissions before deploying.

- Mount a persistent, per-profile/app home at `/home/retro` before startup.
  Steam, libraries, Proton prefixes, shader caches, and login state live there.
- `PUID` and `PGID` default to `1000`. Existing files must already have the intended
  ownership; startup does not recursively change home ownership.
- Pass the required `/dev/dri` and `/dev/input` devices. Supplementary groups are
  derived from the mounted devices rather than fixed host group IDs.
- Wolf must supply `WAYLAND_DISPLAY`, `GAMESCOPE_WIDTH`, `GAMESCOPE_HEIGHT`, and
  `GAMESCOPE_REFRESH`. Supported refresh rates are 60, 90, 120, and 144 Hz.
- Keep `RUN_SWAY=false` and `RUN_GAMESCOPE=true`. The parent Wayland output must
  match the negotiated dimensions and refresh rate or startup fails.

The supervisor checks the parent mode every second. A changed supported mode
stops the session with exit code 75; recreate the lobby with the new negotiation
and the same persistent home. Same-mode reconnects keep the session running.
Missing or invalid parent modes stop the session rather than using a fallback.

Steam is downloaded from Valve on first use and updates in the persistent home.
Only the installer's download confirmation is automated; login and terms are not.

## Development

Requires Docker and Python 3:

```sh
bash tests/run-local.sh
```

Tests cover mode negotiation, reconnect policy, 32/64-bit software Vulkan device
creation, Xwayland software rendering, Steam bootstrap/webhelper startup, and
persistence across container recreation. Steam tests require network access.
Test containers and their temporary volume are removed afterward.

These software tests do not establish native GPU compatibility, Proton game
support, audio/input operation, or end-to-end stream cadence. Verify those on
your Wolf host. Native Vulkan probes are available as:

```sh
/opt/whale-steam/vulkan-device-64 --native
/opt/whale-steam/vulkan-device-32 --native
```

Only linux/amd64 is supported. Proprietary NVIDIA driver injection is not included.

## License

Project source is MIT licensed. See [`NOTICE.md`](NOTICE.md) for upstream attribution
and third-party licensing. This is not an official Valve, Ubuntu, Wolf, or GoW product.
