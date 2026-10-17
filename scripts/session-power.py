#!/usr/bin/env python3
"""Minimal container-only power endpoints. Never forwards to host services."""
import os
import socket

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

LOGIN = 'org.freedesktop.login1.Manager'


def request(action):
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
        client.connect(os.path.join(os.environ['XDG_RUNTIME_DIR'], 'steam-control.sock'))
        client.send(action.encode())


class Power(dbus.service.Object):
    @dbus.service.method(LOGIN, in_signature='', out_signature='s')
    def CanPowerOff(self):
        return 'yes'

    @dbus.service.method(LOGIN, in_signature='', out_signature='s')
    def CanReboot(self):
        return 'yes'

    @dbus.service.method(LOGIN, in_signature='', out_signature='s')
    def CanSuspend(self):
        return 'na'

    @dbus.service.method(LOGIN, in_signature='', out_signature='s')
    def CanHibernate(self):
        return 'na'

    @dbus.service.method(LOGIN, in_signature='', out_signature='s')
    def CanHybridSleep(self):
        return 'na'

    @dbus.service.method(LOGIN, in_signature='b', out_signature='')
    def PowerOff(self, interactive):
        request('quit')

    @dbus.service.method(LOGIN, in_signature='b', out_signature='')
    def Reboot(self, interactive):
        request('restart')

    @dbus.service.method(LOGIN, in_signature='b', out_signature='')
    def Suspend(self, interactive):
        raise dbus.exceptions.DBusException('Suspend is unavailable in a streaming container',
                                            name='org.freedesktop.DBus.Error.NotSupported')

    @dbus.service.method(LOGIN, in_signature='b', out_signature='')
    def Hibernate(self, interactive):
        self.Suspend(interactive)

    @dbus.service.method(LOGIN, in_signature='b', out_signature='')
    def HybridSleep(self, interactive):
        self.Suspend(interactive)


class Desktop(dbus.service.Object):
    @dbus.service.method('org.freedesktop.DisplayManager.Seat', in_signature='ss', out_signature='')
    def SwitchToUser(self, username, session):
        request('quit')


if __name__ == '__main__':
    DBusGMainLoop(set_as_default=True)
    # Ignore inherited bus addresses: only use the container-local socket.
    bus = dbus.bus.BusConnection('unix:path=/run/dbus/system_bus_socket')
    names = [dbus.service.BusName(name, bus, do_not_queue=True) for name in
             ('org.freedesktop.login1', 'org.freedesktop.DisplayManager')]
    power = Power(names[0], '/org/freedesktop/login1')
    desktop = Desktop(names[1], '/org/freedesktop/DisplayManager/Seat0')
    GLib.MainLoop().run()
