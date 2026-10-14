# syntax=docker/dockerfile:1
FROM ubuntu:26.04@sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7 AS probe-builder
ARG DEBIAN_FRONTEND=noninteractive
RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y --no-install-recommends gcc-multilib libvulkan-dev:amd64 libvulkan-dev:i386
COPY tests/vulkan-device.c /src/vulkan-device.c
RUN gcc -Wall -Wextra -Werror /src/vulkan-device.c -lvulkan -o /vulkan-device-64 && \
    gcc -m32 -Wall -Wextra -Werror /src/vulkan-device.c -lvulkan -o /vulkan-device-32
FROM ubuntu:26.04@sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7
ARG DEBIAN_FRONTEND=noninteractive
ARG IMAGE_SOURCE=""
LABEL org.opencontainers.image.title="wolf-steam" \
      org.opencontainers.image.source=$IMAGE_SOURCE \
      org.opencontainers.image.licenses="MIT"
RUN dpkg --add-architecture i386 && apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates curl python3 gosu util-linux dbus-daemon \
      sway gamescope xwayland wayland-utils x11-utils x11-apps mesa-utils \
      steam-installer steam-libs:amd64 steam-libs:i386 \
      mesa-vulkan-drivers:amd64 mesa-vulkan-drivers:i386 \
      libgl1-mesa-dri:amd64 libgl1-mesa-dri:i386 \
      libvulkan1:amd64 libvulkan1:i386 vulkan-tools \
      fonts-dejavu-core xdg-utils bubblewrap procps jq && \
    rm -rf /var/lib/apt/lists/* && \
    userdel -r ubuntu && groupadd -g 1000 retro && useradd -m -u 1000 -g retro -s /bin/bash retro
COPY --from=probe-builder /vulkan-device-64 /vulkan-device-32 /opt/whale-steam/
COPY --chmod=755 scripts/ /opt/whale-steam/
COPY LICENSE NOTICE.md /usr/share/doc/wolf-steam/
COPY vendor/gow/LICENSE /usr/share/doc/wolf-steam/gow-LICENSE
COPY tests/ /opt/whale-steam/tests/
ENV HOME=/home/retro PUID=1000 PGID=1000 RUN_SWAY=false RUN_GAMESCOPE=true
ENTRYPOINT ["/opt/whale-steam/entrypoint.sh"]
