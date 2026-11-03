# syntax=docker/dockerfile:1
ARG BASE_IMAGE=ubuntu:26.04@sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7
FROM ${BASE_IMAGE} AS probe-builder
ARG DEBIAN_FRONTEND=noninteractive
COPY build/check-support.sh /tmp/check-support.sh
RUN bash /tmp/check-support.sh && test "$(dpkg --print-architecture)" = amd64 && \
    dpkg --add-architecture i386 && apt-get -o APT::Update::Error-Mode=any update && \
    apt-get -o APT::Get::Always-Include-Phased-Updates=true upgrade -y --with-new-pkgs && \
    apt-get install -y --no-install-recommends gcc-multilib libvulkan-dev:amd64 libvulkan-dev:i386
COPY tests/vulkan-device.c /src/vulkan-device.c
RUN gcc -Wall -Wextra -Werror /src/vulkan-device.c -lvulkan -o /vulkan-device-64 && \
    gcc -m32 -Wall -Wextra -Werror /src/vulkan-device.c -lvulkan -o /vulkan-device-32
FROM ${BASE_IMAGE} AS runtime
ARG DEBIAN_FRONTEND=noninteractive
ARG IMAGE_SOURCE=""
ARG IMAGE_REVISION=local
ARG BASE_IMAGE
ARG BASE_DIGEST=sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7
LABEL org.opencontainers.image.title="wolf-steam" \
       org.opencontainers.image.source=$IMAGE_SOURCE \
       org.opencontainers.image.revision=$IMAGE_REVISION \
       org.opencontainers.image.base.name=$BASE_IMAGE \
       org.opencontainers.image.base.digest=$BASE_DIGEST \
       io.github.joshcollis.wolf-steam.support-end="2031-05-31" \
       org.opencontainers.image.licenses="MIT"
COPY build/check-support.sh build/package-evidence.py /tmp/
RUN bash /tmp/check-support.sh && test "$(dpkg --print-architecture)" = amd64 && \
    dpkg --add-architecture i386 && apt-get -o APT::Update::Error-Mode=any update && \
    apt-get -o APT::Get::Always-Include-Phased-Updates=true upgrade -y --with-new-pkgs && \
    apt-get install -y --no-install-recommends \
      ca-certificates curl python3 python3-dbus python3-gi gosu util-linux dbus-daemon dbus-bin network-manager \
      ibus zenity pulseaudio-utils locales pciutils \
      sway gamescope xwayland wayland-utils x11-utils x11-apps mesa-utils \
      steam-installer steam-libs:amd64 steam-libs:i386 \
      mesa-vulkan-drivers:amd64 mesa-vulkan-drivers:i386 \
      libgl1-mesa-dri:amd64 libgl1-mesa-dri:i386 \
      libvulkan1:amd64 libvulkan1:i386 vulkan-tools \
      fonts-dejavu-core xdg-utils bubblewrap procps jq && \
    userdel -r ubuntu && groupadd -g 1000 retro && useradd -m -u 1000 -g retro -s /bin/bash retro && \
    localedef -i en_US -f UTF-8 en_US.UTF-8 && \
    mkdir -p /usr/share/wolf-steam && \
    cp /etc/os-release /usr/share/wolf-steam/base-os-release && \
    printf '%s\n' "$BASE_IMAGE" > /usr/share/wolf-steam/base-image.txt && \
    python3 /tmp/package-evidence.py /usr/share/wolf-steam && \
    rm -rf /var/lib/apt/lists/* /tmp/check-support.sh /tmp/package-evidence.py
COPY --from=probe-builder /vulkan-device-64 /vulkan-device-32 /opt/whale-steam/
COPY --chmod=755 scripts/ /opt/whale-steam/
COPY --chmod=644 scripts/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf
COPY --chmod=644 scripts/session-power.conf /etc/dbus-1/system.d/wolf-steam.conf
RUN ln -s /opt/whale-steam/steamos-session-select /usr/bin/steamos-session-select
COPY LICENSE NOTICE.md /usr/share/doc/wolf-steam/
COPY vendor/gow/LICENSE /usr/share/doc/wolf-steam/gow-LICENSE
COPY tests/ /opt/whale-steam/tests/
ENV HOME=/home/retro PUID=1000 PGID=1000 RUN_SWAY=false RUN_GAMESCOPE=true LANG=en_US.UTF-8
ENTRYPOINT ["/opt/whale-steam/entrypoint.sh"]
