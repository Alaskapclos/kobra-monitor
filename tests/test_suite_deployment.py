import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from suite.deployment import contract, compose, prepare, validate, SPOOLMAN_IMAGE
from suite_service import initialize, volume_identity, MARKER, run_due, write_heartbeat, heartbeat_healthy


class SuiteDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.config = contract('kobra-monitor:0.31.1-alpha.1')

    def test_only_monitor_has_loopback_port_no_existing_external_volumes(self):
        data = compose(self.config)
        services = data['services']
        self.assertEqual(services['monitor']['ports'], ['127.0.0.1:17125:7125'])
        for name in ('spoolman', 'backups', 'initialize'):
            self.assertNotIn('ports', services[name])
        for volume in data['volumes'].values():
            self.assertEqual(volume, {})
        for name in ('backups', 'initialize'):
            self.assertEqual(services[name]['network_mode'], 'none')
        self.assertTrue(all(services[n]['read_only'] for n in services))
        self.assertIn('@sha256:', services['spoolman']['image'])
        self.assertEqual(services['spoolman']['image'], SPOOLMAN_IMAGE)
        self.assertNotIn('environment', services['monitor'])  # No printer control grants.
        self.assertIn('test', services['backups']['healthcheck'])
        self.assertTrue(all('docker.sock' not in v for s in services.values() for v in s['volumes']))

    def test_explicit_lan_only_connects_monitor_and_grants_no_controls(self):
        config = contract('kobra-monitor:0.43.0-alpha.1', network='lan')
        self.assertEqual(validate(config), config)
        data = compose(config)
        self.assertTrue(data['networks']['suite']['internal'])
        self.assertEqual(data['networks']['printers'], {})
        self.assertEqual(data['services']['monitor']['networks'], ['suite', 'printers'])
        self.assertEqual(data['services']['spoolman']['networks'], ['suite'])
        env = data['services']['monitor']['environment']
        self.assertEqual(env, {'KOBRA_NATIVE_CONTROL_SETTINGS': '1'})
        for name in ('initialize', 'backups'):
            self.assertEqual(data['services'][name]['network_mode'], 'none')
        for service in data['services'].values():
            self.assertNotIn('privileged', service)
            self.assertNotIn('docker.sock', str(service))
        self.assertNotIn('ports', data['services']['spoolman'])

    def test_unknown_network_and_explicit_isolated_field_are_rejected(self):
        for network in ('host', 'bridge', '', True, None):
            with self.assertRaises(ValueError):
                contract('kobra-monitor:0.43.0-alpha.1', network=network)
        with self.assertRaises(ValueError):
            validate({**self.config, 'network': 'isolated'})
        self.assertNotIn('network', self.config)
        self.assertEqual(compose(self.config)['networks'], {'suite': {'internal': True}})

    def test_contract_rejects_foreign_projects_floating_images_and_production_ports(self):
        for changes in [{'project': 'kobra-monitor'}, {'project': '../../escape'},
                        {'port': 7125}, {'port': 7912}, {'port': True}, {'monitor_image': 'kobra-monitor:latest'}]:
            args = {'monitor_image': 'kobra-monitor:0.31.1-alpha.1', **changes}
            with self.assertRaises(ValueError):
                contract(**args)
        for field, value in [('spoolman_image', 'attacker/image:latest'), ('platform', 'linux/arm64')]:
            changed = {**self.config, field: value}
            with self.assertRaises(ValueError):
                validate(changed)

    def test_prepare_never_overwrites_existing_project(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'suite'
            prepare(path, self.config['monitor_image'])
            before = (path / 'suite.json').read_bytes()
            self.assertEqual(json.loads((path / 'compose.json').read_text())['name'],
                             json.loads(before)['project'])
            with self.assertRaises(FileExistsError):
                prepare(path, self.config['monitor_image'])
            self.assertEqual((path / 'suite.json').read_bytes(), before)

    def test_volume_initialization_is_idempotent_and_preserves_user_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / n for n in ('monitor', 'spoolman', 'backups')]
            for p in paths:
                p.mkdir()
            initialize(self.config, *paths)
            for role, path in zip(('monitor', 'spoolman', 'backups'), paths):
                self.assertEqual(json.loads((path / MARKER).read_text()), volume_identity(self.config, role))
            settings = paths[0] / 'spoolman.json'
            self.assertEqual(json.loads(settings.read_text())['url'], 'http://spoolman:8000/spoolman')
            custom = b'{"url":"http://spoolman:8000/spoolman","mappings":{"fixture":12}}'
            settings.write_bytes(custom)
            initialize(self.config, *paths)
            self.assertEqual(settings.read_bytes(), custom)

    def test_unknown_or_foreign_data_is_not_adopted_or_partially_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / n for n in ('monitor', 'spoolman', 'backups')]
            for p in paths:
                p.mkdir()
            (paths[1] / 'spoolman.db').write_bytes(b'pre-existing')
            with self.assertRaises(ValueError):
                initialize(self.config, *paths)
            self.assertEqual(list(paths[0].iterdir()), [])
            (paths[1] / 'spoolman.db').unlink()
            initialize(self.config, *paths)
            with self.assertRaises(ValueError):
                initialize(contract(self.config['monitor_image']), *paths)

    def test_nested_or_symlinked_volumes_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [root / n for n in ('monitor', 'spoolman', 'backups')]
            for p in paths:
                p.mkdir()
            with self.assertRaises(ValueError):
                initialize(self.config, paths[0], paths[0], paths[2])
            nested = paths[0] / 'nested'
            nested.mkdir()
            with self.assertRaises(ValueError):
                initialize(self.config, paths[0], nested, paths[2])
            self.assertIsNone(run_due(self.config, paths[0], paths[1], paths[2]))

    def test_backup_readiness_distinguishes_waiting_failure_and_stale_process(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'heartbeat.json'
            self.assertFalse(heartbeat_healthy(path))
            for status in ('waiting_or_not_due', 'verified'):
                write_heartbeat(status, path, clock=lambda: 100)
                self.assertTrue(heartbeat_healthy(path, clock=lambda: 101))
                self.assertFalse(heartbeat_healthy(path, clock=lambda: 281))
                self.assertFalse(heartbeat_healthy(path, clock=lambda: 99))
            write_heartbeat('failed', path, clock=lambda: 100)
            self.assertFalse(heartbeat_healthy(path, clock=lambda: 101))
