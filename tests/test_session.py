import importlib.util
import pathlib
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]

class SessionTests(unittest.TestCase):
    def test_finished_steam_stops_lingering_compositor(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            env = {'XDG_RUNTIME_DIR': directory, 'GAMESCOPE_WIDTH': '1280',
                   'GAMESCOPE_HEIGHT': '720', 'GAMESCOPE_REFRESH': '60'}
            compositor = Mock(pid=456)
            compositor.poll.return_value = None

            def finish(_):
                (pathlib.Path(directory) / 'steam-session.done').write_text('0')

            with patch.dict(m.os.environ, env), patch.object(m.sys, 'argv', ['session.py']), \
                 patch.object(m, 'read_parent', return_value=(1280, 720, 60000)), \
                 patch.object(m.subprocess, 'Popen', return_value=compositor), \
                 patch.object(m.time, 'sleep', side_effect=finish), \
                 patch.object(m.signal, 'signal'), \
                 patch.object(m.os, 'killpg') as killpg:
                self.assertEqual(m.main(), 0)
                killpg.assert_called_once_with(456, m.signal.SIGTERM)
                compositor.wait.assert_called_once_with(timeout=8)

    def module(self):
        self.assertTrue((ROOT / 'scripts/session.py').exists(), 'session implementation missing')
        spec = importlib.util.spec_from_file_location('session', ROOT / 'scripts/session.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_requested_rates(self):
        m = self.module()
        for rate in (60, 90, 120, 144):
            self.assertEqual(m.requested({'GAMESCOPE_WIDTH':'1920', 'GAMESCOPE_HEIGHT':'1080', 'GAMESCOPE_REFRESH':str(rate)}), (1920,1080,rate*1000))

    def test_invalid_and_missing_requests_fail(self):
        m = self.module()
        for rate in ('', '0', '145', '144; true', '60.5'):
            with self.assertRaises(ValueError):
                m.requested({'GAMESCOPE_WIDTH':'1920', 'GAMESCOPE_HEIGHT':'1080', 'GAMESCOPE_REFRESH':rate})
        with self.assertRaises(ValueError):
            m.requested({})

    def test_parent_mode_parser(self):
        m = self.module()
        text = "interface: 'wl_output', version: 4, name: 7\n\tmode:\n\t\twidth: 1920 px, height: 1080 px, refresh: 144000 mHz\n\t\tflags: current preferred\n"
        self.assertEqual(m.parent_mode(text), (1920,1080,144000))
        with self.assertRaises(ValueError):
            m.parent_mode(text.replace('current preferred','preferred'))

    def test_actual_wayland_info_hz_format(self):
        m = self.module()
        text = "width: 1920 px, height: 1080 px, refresh: 144.000 Hz,\n\t\tflags: current"
        self.assertEqual(m.parent_mode(text), (1920,1080,144000))

    def test_gamescope_refresh_is_real_launch_argument(self):
        m = self.module()
        for r in (60,90,120,144):
            args = m.launch_args((1920,1080,r*1000), ['steam','-bigpicture'])
            self.assertEqual(args[0], '/usr/games/gamescope')
            self.assertEqual(args[args.index('-r')+1], str(r))
            self.assertEqual(args[-3:], ['--','steam','-bigpicture'])

    def test_gamescope_steam_integration_precedes_command_separator(self):
        m = self.module()
        command = ['/usr/games/steam', '-bigpicture']
        for rate in (60, 90, 120, 144):
            with self.subTest(rate=rate):
                args = m.launch_args((1920, 1200, rate * 1000), command)
                separator = args.index('--')
                self.assertIn('-e', args[:separator],
                              'Steam IDs/focus control require Gamescope Steam integration')
                self.assertEqual(args[separator + 1:], command)
                self.assertEqual(args[args.index('-r') + 1], str(rate))
                self.assertEqual(args[args.index('-W') + 1], '1920')
                self.assertEqual(args[args.index('-H') + 1], '1200')

    def test_changed_reconnect_requires_recreation(self):
        m = self.module()
        self.assertFalse(m.requires_recreation((1920,1080,60000),(1920,1080,60000)))
        self.assertTrue(m.requires_recreation((1920,1080,60000),(1920,1080,144000)))

    def test_parent_disagreement_fails(self):
        m = self.module()
        for rate in (60,90,120,144):
            mode = (1920,1080,rate*1000)
            self.assertEqual(m.agree(mode, mode), mode)
            with self.assertRaises(ValueError):
                m.agree(mode, (1920,1080,59000))

    def test_reconnect_never_keeps_stale_refresh(self):
        m = self.module()
        for rate in (60,90,120,144):
            self.assertEqual(m.reconnect((1920,1080,60000), (2560,1440,rate*1000)), (2560,1440,rate*1000))
        with self.assertRaises(ValueError):
            m.reconnect((1920,1080,60000), (1920,1080,75000))

    def test_runtime_config_not_persistent_home(self):
        m = self.module()
        for rate in (60,90,120,144):
            self.assertIn(f'1920x1080@{rate}Hz', m.config((1920,1080,rate*1000)))
        self.assertNotIn('/home/', m.config((1920,1080,60000)))

if __name__ == '__main__':
    unittest.main()
