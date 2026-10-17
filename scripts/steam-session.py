#!/usr/bin/env python3
"""Run Steam and desktop integrations inside Gamescope's display environment."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parent


def steam_command(env):
    command = ['/usr/games/steam', '-gamepadui']
    if env.get('STEAM_OS_SESSION_HOOKS', '1') == '1':
        command.append('-steamos3')
    return command


def steam_pid(home):
    try:
        pid = int((home / '.steam/steam.pid').read_text().strip())
        # Do not trust a stale pidfile or an unrelated process after PID reuse.
        exe = Path(f'/proc/{pid}/exe').resolve(strict=True)
        if exe.name == 'steam' and exe.is_relative_to(home.resolve()):
            return pid
    except (OSError, ValueError):
        pass
    return None


def receive(control):
    try:
        action = control.recv(32).decode('ascii')
        return action if action in ('quit', 'restart') else None
    except (BlockingIOError, UnicodeError):
        return None


def pending_action(control, runtime):
    # Steam can exit before issuing a D-Bus power request. Its sentinels retain
    # the requested action across that exit (and distinguish it from an update).
    for filename, action in (('steam-shutdown', 'quit'), ('steam-reboot', 'restart')):
        marker = runtime / filename
        if marker.exists():
            marker.unlink()
            return action
    return receive(control)


def shutdown(process, home, grace=35):
    if process.poll() is None or steam_pid(home):
        try:
            subprocess.run(['/usr/games/steam', '-shutdown'], timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            if process.poll() is not None and not steam_pid(home):
                return
            time.sleep(.2)
        # Only the process group created for this Steam launch, never global pkill.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        else:
            time.sleep(3)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()


def main():
    runtime = Path(os.environ['XDG_RUNTIME_DIR'])
    home = Path(os.environ['HOME'])
    done = runtime / 'steam-session.done'
    done.unlink(missing_ok=True)
    address = runtime / 'steam-control.sock'
    address.unlink(missing_ok=True)
    action = None

    def stop(signum, frame):
        nonlocal action
        action = 'quit'

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    services = []
    process = None
    progress = None
    result = 1
    client_result = 0
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as control:
        control.bind(str(address))
        control.setblocking(False)
        try:
            services.append(subprocess.Popen(['python3', str(ROOT / 'session-power.py')]))
            services.append(subprocess.Popen(['ibus-daemon', '--replace', '--panel=disable',
                                              '--emoji-extension=disable']))
            env = os.environ.copy()
            env.update(STEAM_ENABLE_VOLUME_HANDLER='1', QT_IM_MODULE='ibus', GTK_IM_MODULE='ibus',
                       XMODIFIERS='@im=ibus',
                       XDG_CURRENT_DESKTOP='gamescope', XDG_SESSION_TYPE='wayland',
                       SRT_URLOPEN_PREFER_STEAM='1',
                       STEAMOS_STEAM_SHUTDOWN_SENTINEL=str(runtime / 'steam-shutdown'),
                       STEAMOS_STEAM_REBOOT_SENTINEL=str(runtime / 'steam-reboot'))
            for filename in ('steam-shutdown', 'steam-reboot'):
                (runtime / filename).unlink(missing_ok=True)
            # Power endpoints must exist before Steam caches their capabilities.
            for attempt in range(50):
                ready = subprocess.run(['dbus-send', '--system', '--print-reply',
                    '--dest=org.freedesktop.login1', '/org/freedesktop/login1',
                    'org.freedesktop.login1.Manager.CanPowerOff'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                if ready.returncode == 0:
                    break
                if services[0].poll() is not None:
                    raise RuntimeError('Container power service failed to start')
                time.sleep(.1)
            else:
                raise RuntimeError('Container power service did not become ready')
            while action != 'quit':
                progress = subprocess.Popen(['zenity', '--progress', '--pulsate', '--no-cancel',
                    '--title=Steam', '--text=Starting Steam. Downloads and updates may take a few minutes.'],
                    stdin=subprocess.PIPE)
                started = time.monotonic()
                # -steamos3 enables the session-select hook; no Steam Deck hardware spoofing.
                process = subprocess.Popen(steam_command(env),
                                           env=env, start_new_session=True)
                print('Steam starting; first launch and client updates require network access', flush=True)
                missing_since = None
                while action is None:
                    action = pending_action(control, runtime)
                    # The client owns its update UI. Remove our startup indicator
                    # once its web UI starts, or after a bounded startup interval.
                    if progress and (subprocess.run(['pgrep', '-x', 'steamwebhelper'],
                            stdout=subprocess.DEVNULL).returncode == 0 or
                            time.monotonic() - started > 300):
                        progress.terminate()
                        progress.wait(timeout=3)
                        progress.stdin.close()
                        progress = None
                    if process.poll() is not None and not steam_pid(home):
                        missing_since = missing_since or time.monotonic()
                        if time.monotonic() - missing_since >= 5:
                            client_result = max(0, process.returncode or 0)
                            if process.returncode and process.returncode < 0:
                                client_result = 1
                            print(f'Steam launcher exited with status {process.returncode}', flush=True)
                            action = 'quit'
                    else:
                        missing_since = None
                    time.sleep(.2)
                shutdown(process, home)
                if progress:
                    progress.terminate()
                    progress.wait(timeout=3)
                    progress.stdin.close()
                    progress = None
                if action == 'restart':
                    print('Restarting Steam', flush=True)
                    # A single menu selection can produce both a sentinel and
                    # a D-Bus call. Do not restart the new client a second time.
                    while (pending := pending_action(control, runtime)) is not None:
                        if pending == 'quit':
                            action = 'quit'
                    if action == 'restart':
                        action = None
            result = client_result
        finally:
            if progress:
                progress.terminate()
                progress.wait(timeout=3)
                progress.stdin.close()
            if process:
                shutdown(process, home, grace=0)
            for service in services:
                service.terminate()
                try:
                    service.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    service.kill()
                    service.wait()
            temporary = done.with_suffix('.tmp')
            temporary.write_text(str(result))
            temporary.replace(done)
            address.unlink(missing_ok=True)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
