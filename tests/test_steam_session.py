import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('steam_session', ROOT / 'scripts/steam-session.py')
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)


class SteamSessionTests(unittest.TestCase):
    def test_gamescope_helpers_are_on_path(self):
        entrypoint = (ROOT / 'scripts/entrypoint.sh').read_text()
        self.assertIn('bootstrap-bin:/usr/games:$PATH', entrypoint)

    def test_os_session_hooks_have_explicit_opt_out(self):
        self.assertEqual(session.steam_command({}),
                         ['/usr/games/steam', '-gamepadui', '-steamos3'])
        self.assertEqual(session.steam_command({'STEAM_OS_SESSION_HOOKS': '0'}),
                         ['/usr/games/steam', '-gamepadui'])

    def test_socket_requests_and_invalid_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
                address = str(Path(directory) / 'control')
                server.bind(address)
                server.setblocking(False)
                self.assertIsNone(session.receive(server))
                with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
                    client.connect(address)
                    for action in ('quit', 'restart', 'suspend', 'anything'):
                        client.send(action.encode())
                        self.assertEqual(session.receive(server), action if action in ('quit', 'restart') else None)

    def test_shutdown_sentinel_wins_over_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            for name in ('steam-shutdown', 'steam-reboot'):
                (runtime / name).touch()
            self.assertEqual(session.pending_action(None, runtime), 'quit')
            self.assertEqual(session.pending_action(None, runtime), 'restart')

    def test_missing_stale_or_foreign_pid_is_not_steam(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertIsNone(session.steam_pid(home))
            (home / '.steam').mkdir()
            for value in ('invalid', '999999999', '1'):
                (home / '.steam/steam.pid').write_text(value)
                self.assertIsNone(session.steam_pid(home))

    @patch.object(session, 'steam_pid', return_value=None)
    @patch.object(session.subprocess, 'run')
    def test_exited_steam_does_not_start_shutdown_client(self, run, pid):
        process = Mock()
        process.poll.return_value = 0
        session.shutdown(process, Path('/unused'))
        run.assert_not_called()

    @patch.object(session.time, 'sleep')
    @patch.object(session.os, 'killpg')
    @patch.object(session, 'steam_pid', return_value=None)
    @patch.object(session.subprocess, 'run')
    def test_hung_shutdown_targets_only_owned_process_group(self, run, pid, killpg, sleep):
        process = Mock(pid=456)
        process.poll.return_value = None
        session.shutdown(process, Path('/unused'), grace=0)
        self.assertEqual(run.call_args.args[0], ['/usr/games/steam', '-shutdown'])
        self.assertEqual(killpg.call_args.args[0], 456)
