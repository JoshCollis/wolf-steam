# Third-party notices

Integration references under `vendor/gow/` come from
[Games-on-Whales GoW](https://github.com/games-on-whales/gow/tree/bc4bb677e3376e17265317f23d887ecf42de8972)
at commit `bc4bb677e3376e17265317f23d887ecf42de8972`.
Their original MIT copyright and license are preserved in `vendor/gow/LICENSE`.

The image uses the official Ubuntu 26.04 base. Ubuntu packages retain their own
licenses in `/usr/share/doc/*/copyright`. The project's MIT license and OCI license
label apply to project source, not every component in the image.

The Ubuntu Steam installer downloads the proprietary Steam client from Valve at
runtime. Steam binaries are not included in this repository or baked into the
image. Steam use is subject to the
[Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/).

The base image digest is pinned; apt packages receive updates during builds and
Steam updates itself at runtime, so package versions may vary between builds.
