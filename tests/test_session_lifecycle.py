"""Real subprocess cleanup with stand-ins for Steam, IBus, and the UI."""
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('steam_session_lifecycle', ROOT / 'scripts/steam-session.py')
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)


class LifecycleTests(unittest.TestCase):
    def exercise(self, actions):
        real_popen = subprocess.Popen
        steam = []
        children = []
        errors = []
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)

            def spawn(argv, **kwargs):
                is_steam = argv[0] == '/usr/games/steam'
                duration = '.1' if is_steam and not actions else '30'
                child = real_popen([sys.executable, '-c', f'import time; time.sleep({duration})'],
                                   **kwargs)
                children.append(child)
                if is_steam:
                    steam.append(child)
                return child

            def run(argv, **kwargs):
                if argv == ['/usr/games/steam', '-shutdown']:
                    steam[-1].terminate()
                    steam[-1].wait(timeout=2)
                return subprocess.CompletedProcess(argv, 1 if argv[0] == 'pgrep' else 0)

            def send_actions():
                try:
                    for index, action in enumerate(actions):
                        deadline = time.monotonic() + 10
                        while len(steam) <= index:
                            if time.monotonic() > deadline:
                                raise AssertionError('Steam failed to launch/restart')
                            time.sleep(.02)
                        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
                            client.connect(str(runtime / 'steam-control.sock'))
                            client.send(action.encode())
                except Exception as error:
                    errors.append(error)

            thread = threading.Thread(target=send_actions, daemon=True)
            with patch.dict(os.environ, HOME=directory, XDG_RUNTIME_DIR=directory), \
                 patch.object(session.subprocess, 'Popen', side_effect=spawn), \
                 patch.object(session.subprocess, 'run', side_effect=run), \
                 patch.object(session.signal, 'signal'):
                thread.start()
                try:
                    self.assertEqual(session.main(), 0)
                finally:
                    for child in children:
                        if child.poll() is None:
                            child.kill()
                            child.wait()
                thread.join(timeout=2)
            self.assertFalse(errors, errors)
            self.assertEqual((runtime / 'steam-session.done').read_text(), '0')
            self.assertFalse((runtime / 'steam-control.sock').exists())
            self.assertTrue(all(child.poll() is not None for child in children))
            self.assertEqual(len(steam), max(1, len(actions)))

    def test_quit_stops_steam_and_services(self):
        self.exercise(['quit'])

    def test_restart_launches_new_steam_then_quits(self):
        self.exercise(['restart', 'quit'])

    def test_natural_steam_exit_finishes_session(self):
        self.exercise([])
