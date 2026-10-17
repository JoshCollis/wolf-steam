import configparser
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HELPER = ROOT / 'scripts/network-status.sh'


class NetworkStatusTests(unittest.TestCase):
    def test_image_and_root_entrypoint_wire_real_network_status(self):
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertIn('network-manager', dockerfile)
        self.assertIn('/etc/NetworkManager/NetworkManager.conf', dockerfile)
        entrypoint = (ROOT / 'scripts/entrypoint.sh').read_text()
        self.assertIn('/opt/whale-steam/network-status.sh', entrypoint)
        self.assertLess(entrypoint.index('/opt/whale-steam/network-status.sh'),
                        entrypoint.index('exec gosu'))
        self.assertIn('if [ "${1:-}" = --probe ]; then', entrypoint)

    def test_config_adopts_docker_without_dns_or_new_connections(self):
        config = configparser.ConfigParser(interpolation=None)
        self.assertTrue(config.read(ROOT / 'scripts/NetworkManager.conf'))
        self.assertEqual(config['main']['dns'], 'none')
        self.assertEqual(config['main']['rc-manager'], 'unmanaged')
        self.assertEqual(config['main']['no-auto-default'], '*')
        self.assertEqual(config['keyfile']['unmanaged-devices'], 'none')
        self.assertEqual(config['device-container']['match-device'], 'interface-name:eth0')
        self.assertEqual(config['device-container']['managed'], '1')
        self.assertEqual(config['connectivity']['enabled'], 'true')
        self.assertEqual(config['connectivity']['uri'], 'http://steamconnecttest.com/204')
        self.assertEqual(config['connectivity']['response'], '')
        self.assertEqual(config['connectivity']['interval'], '60')

    def run_helper(self, mode):
        self.assertTrue(HELPER.exists(), 'network status startup helper missing')
        with tempfile.TemporaryDirectory() as directory:
            directory = pathlib.Path(directory)
            log = directory / 'calls'
            fake = directory / 'fake'
            fake.write_text('''#!/bin/bash
printf '%s %s\\n' "${0##*/}" "$*" >> "$CALL_LOG"
case "${0##*/}" in
  timeout) shift; shift; exec "$@" ;;
  dbus-send)
    [ "$MODE" != bus-failed ] || exit 1
    if [ ! -e "$CALL_LOG.bus" ]; then touch "$CALL_LOG.bus"; exit 1; fi ;;
  nmcli)
    [ "$MODE" != nm-failed ] || exit 1
    case "$*" in
      *connectivity*) echo "$MODE"; [ "$MODE" != offline ] ;;
      *) echo running ;;
    esac ;;
  setpriv)
    while [[ $1 = --* ]]; do shift; done
    exec "$@" ;;
esac
''')
            fake.chmod(0o755)
            for command in ('mkdir', 'dbus-uuidgen', 'dbus-daemon', 'dbus-send',
                            'setpriv', 'NetworkManager', 'nmcli', 'timeout', 'sleep'):
                (directory / command).symlink_to(fake)
            env = dict(os.environ, PATH=f'{directory}:/usr/bin:/bin',
                       CALL_LOG=str(log), MODE=mode,
                       DBUS_SYSTEM_BUS_ADDRESS='unix:path=/host/bus')
            result = subprocess.run(['bash', str(HELPER)], env=env,
                                    capture_output=True, text=True, timeout=5)
            return result, log.read_text()

    def test_startup_drops_network_control_and_uses_container_bus(self):
        result, calls = self.run_helper('full')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('dbus-daemon --system', calls)
        self.assertIn('--address=unix:path=/run/dbus/system_bus_socket', calls)
        self.assertIn('--bounding-set=-net_admin', calls)
        self.assertIn('--inh-caps=-net_admin', calls)
        self.assertIn('--ambient-caps=-net_admin', calls)
        self.assertIn('--no-new-privs NetworkManager --no-daemon', calls)
        self.assertIn('networking connectivity check', calls)
        self.assertNotIn('/host/bus', calls)
        self.assertNotIn('nmcli connection', calls)

    def test_real_offline_is_nonfatal(self):
        result, calls = self.run_helper('offline')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('networking connectivity check', calls)
        self.assertIn('offline', result.stderr)

    def test_unready_local_bus_is_bounded_and_nonfatal(self):
        result, calls = self.run_helper('bus-failed')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLessEqual(sum(line.startswith('dbus-send ') for line in calls.splitlines()), 21)
        self.assertNotIn('setpriv ', calls)
        self.assertIn('not ready', result.stderr)

    def test_unready_networkmanager_is_bounded_and_nonfatal(self):
        result, calls = self.run_helper('nm-failed')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLessEqual(sum(line.startswith('nmcli ') for line in calls.splitlines()), 20)
        self.assertNotIn('networking connectivity check', calls)
        self.assertIn('not ready', result.stderr)
