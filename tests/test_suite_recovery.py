import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import test_suite_snapshots
from suite.deployment import contract, compose
from suite.recovery import restore_to_new_directory
from suite.snapshots import create_snapshot
from suite_service import run_due


class SuiteRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_suite_snapshots.SuiteSnapshotTests()
        self.fixture.setUp()
        self.config = contract('kobra-monitor:0.31.1-alpha.1')

    def tearDown(self):
        self.fixture.tearDown()

    def snapshot(self, deployment=None):
        f = self.fixture
        path = f.root / 'compose.json'
        path.write_text(json.dumps(deployment or compose(self.config)))
        return create_snapshot(f.monitor, f.spoolman, f.destination,
            monitor_image=self.config['monitor_image'], spoolman_image=self.config['spoolman_image'],
            deployment=path)

    def test_offline_restore_contains_both_databases_and_configuration_without_starting_services(self):
        f = self.fixture
        snapshot = self.snapshot()
        target = f.root / 'restored'
        restore_to_new_directory(snapshot, target)
        self.assertEqual((target / 'monitor-data/access-token').read_text().strip(), f.token)
        with sqlite3.connect(target / 'spoolman-data/spoolman.db') as db:
            self.assertEqual(db.execute('SELECT remaining FROM spool').fetchone(), (470,))
        self.assertEqual(json.loads((target / 'recorded-suite.json').read_text()), self.config)
        self.assertEqual(json.loads((target / 'recorded-compose.json').read_text()), compose(self.config))
        self.assertFalse((target / 'compose.yaml').exists())
        self.assertFalse((target / 'compose.json').exists())  # No accidental start against old project volumes.

    def test_restore_refuses_existing_target_and_changed_or_unsafe_deployment(self):
        f = self.fixture
        target = f.root / 'existing'
        target.mkdir()
        with self.assertRaises(ValueError):
            restore_to_new_directory(self.snapshot(), target)
        bad = compose(self.config)
        bad['services']['monitor']['volumes'].append('/:/host')
        with self.assertRaises(ValueError):
            restore_to_new_directory(self.snapshot(bad), f.root / 'bad-restore')
        self.assertFalse((f.root / 'bad-restore').exists())

    def test_scheduler_backs_up_full_configuration_and_does_not_duplicate_not_due_stand(self):
        f = self.fixture
        first = run_due(self.config, f.monitor, f.spoolman.parent, f.destination, clock=lambda: 100)
        self.assertIsNotNone(first)
        self.assertIsNone(run_due(self.config, f.monitor, f.spoolman.parent, f.destination, clock=lambda: 101))
        restore_to_new_directory(first, f.root / 'scheduled-restore')
        self.assertEqual(json.loads((f.root / 'scheduled-restore/recorded-suite.json').read_text()), self.config)
        second = run_due(self.config, f.monitor, f.spoolman.parent, f.destination, clock=lambda: 86501)
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)

    def test_watcher_does_not_restore_all_archives_every_minute(self):
        f = self.fixture
        state = {}
        first = run_due(self.config, f.monitor, f.spoolman.parent, f.destination, clock=lambda: 100, state=state)
        self.assertIsNotNone(first)
        with patch('suite_service.verify_snapshot') as verify:
            self.assertIsNone(run_due(self.config, f.monitor, f.spoolman.parent,
                f.destination, clock=lambda: 160, state=state))
            verify.assert_not_called()
