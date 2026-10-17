"""Exercise real D-Bus methods on the disposable image's system bus."""
import os
from pathlib import Path
import socket
import subprocess
import time

import dbus

runtime = Path(os.environ['XDG_RUNTIME_DIR'])
address = runtime / 'steam-control.sock'
with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as control:
    control.bind(str(address))
    control.settimeout(2)
    process = subprocess.Popen(['python3', '/opt/whale-steam/session-power.py'])
    try:
        bus = dbus.SystemBus()
        for _ in range(50):
            if bus.name_has_owner('org.freedesktop.login1'):
                break
            time.sleep(.1)
        power = dbus.Interface(bus.get_object('org.freedesktop.login1', '/org/freedesktop/login1'),
                               'org.freedesktop.login1.Manager')
        assert power.CanSuspend() == 'na'
        assert power.CanHibernate() == 'na'
        assert power.CanHybridSleep() == 'na'
        for method in (power.Suspend, power.Hibernate, power.HybridSleep):
            try:
                method(False)
                raise AssertionError('Sleep must not succeed')
            except dbus.DBusException as error:
                assert error.get_dbus_name() == 'org.freedesktop.DBus.Error.NotSupported'
        assert power.CanPowerOff() == 'yes'
        assert power.CanReboot() == 'yes'
        power.PowerOff(False)
        assert control.recv(32) == b'quit'
        power.Reboot(False)
        assert control.recv(32) == b'restart'
        desktop = dbus.Interface(bus.get_object('org.freedesktop.DisplayManager',
            '/org/freedesktop/DisplayManager/Seat0'), 'org.freedesktop.DisplayManager.Seat')
        desktop.SwitchToUser('steamuser', '')
        assert control.recv(32) == b'quit'
        subprocess.run(['/opt/whale-steam/steamos-session-select', 'desktop'], check=True)
        assert control.recv(32) == b'quit'
        print('CONTAINER_POWER_BUS_PASS')
    finally:
        process.terminate()
        process.wait(timeout=3)
        address.unlink(missing_ok=True)
