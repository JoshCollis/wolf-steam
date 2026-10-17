#!/bin/bash
# Test-only PulseAudio daemon and null sink. Never connect to the runner's server.
# Requires pulseaudio in a disposable test container, not in the runtime image.
set -euo pipefail
export PULSE_SERVER=unix:$XDG_RUNTIME_DIR/wolf-audio-test.sock
pulseaudio --daemonize --exit-idle-time=-1 --use-pid-file=no -n \
    --load="module-native-protocol-unix socket=$XDG_RUNTIME_DIR/wolf-audio-test.sock auth-anonymous=1" \
    --load='module-null-sink sink_name=wolf_audio_test' \
    --log-target=stderr
cleanup() { pactl exit || true; }
trap cleanup EXIT
pactl set-default-sink wolf_audio_test
/opt/whale-steam/audio-check volume 50%
pactl get-sink-volume @DEFAULT_SINK@ | grep -q '50%'
/opt/whale-steam/audio-check mute
pactl get-sink-mute @DEFAULT_SINK@ | grep -q 'yes'
/opt/whale-steam/audio-check unmute
pactl get-sink-mute @DEFAULT_SINK@ | grep -q 'no'
python3 - <<'PY'
import array
import math
import subprocess
samples = array.array('h', (int(4000 * math.sin(2 * math.pi * 440 * i / 48000))
                            for i in range(48000)))
subprocess.run(['pacat', '--playback', '--raw', '--format=s16le', '--rate=48000',
                '--channels=1', '--device=wolf_audio_test'], input=samples.tobytes(), check=True)
PY
echo ISOLATED_AUDIO_VOLUME_MUTE_PLAYBACK_PASS
