from pathlib import Path
import os
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'scripts/audio-check'


class AudioControlsTests(unittest.TestCase):
    def test_explicit_actions_only_use_runner_default_sink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / 'calls'
            pactl = root / 'pactl'
            pactl.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n')
            pactl.chmod(0o755)
            env = dict(os.environ, PATH=f'{directory}:/usr/bin:/bin', CALL_LOG=str(log))
            for args, expected in (
                (['volume', '50%'], 'set-sink-volume @DEFAULT_SINK@ 50%'),
                (['mute'], 'set-sink-mute @DEFAULT_SINK@ 1'),
                (['unmute'], 'set-sink-mute @DEFAULT_SINK@ 0'),
            ):
                subprocess.run(['bash', str(HELPER), *args], env=env, check=True)
                self.assertEqual(log.read_text().splitlines()[-1], expected)
            before = log.read_text()
            for volume in ('101%', '-1%', '50; reboot', ''):
                result = subprocess.run(['bash', str(HELPER), 'volume', volume],
                                        env=env, capture_output=True)
                self.assertEqual(result.returncode, 64)
            self.assertEqual(log.read_text(), before)
            subprocess.run(['bash', str(HELPER)], env=env, check=True)
            self.assertEqual(log.read_text().splitlines()[-3:],
                ['info', 'get-sink-volume @DEFAULT_SINK@', 'get-sink-mute @DEFAULT_SINK@'])
