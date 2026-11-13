import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from access import Access
from configuration import save_config
from history import History
from suite.snapshots import create_snapshot, verify_snapshot


class SuiteSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.monitor = self.root / 'monitor'
        self.monitor.mkdir()
        save_config(self.monitor, ['192.168.1.20'])
        self.token = Access(self.monitor).token
        self.history = History(self.monitor / 'history.sqlite3')
        self.history.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            ('a' * 32, '192.168.1.20', '', 'fixture.gcode', 'printing', 10, 20, None, 1, 20, 2, 10, 5))
        self.history.db.commit()
        folder = self.root / 'spoolman'
        folder.mkdir()
        self.spoolman = folder / 'spoolman.db'
        self.db = sqlite3.connect(self.spoolman)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('CREATE TABLE vendor(id INTEGER PRIMARY KEY); '
                             'CREATE TABLE filament(id INTEGER PRIMARY KEY, vendor_id REFERENCES vendor(id)); '
                             'CREATE TABLE spool(id INTEGER PRIMARY KEY, filament_id REFERENCES filament(id), remaining REAL); '
                             'INSERT INTO vendor VALUES(1); INSERT INTO filament VALUES(1,1); '
                             'INSERT INTO spool VALUES(1,1,470);')
        self.db.commit()
        self.destination = self.root / 'snapshots'

    def tearDown(self):
        self.db.close()
        self.history.close()
        self.temp.cleanup()

    def make(self, **kwargs):
        return create_snapshot(self.monitor, self.spoolman, self.destination,
                               monitor_image='kobra-monitor:fixture',
                               spoolman_image='spoolman:fixture', **kwargs)

    def test_live_wal_databases_restore_together_without_changing_sources(self):
        before = self.spoolman.read_bytes()
        snapshot = self.make()
        result = verify_snapshot(snapshot)
        self.assertTrue(result['verified'])
        self.assertEqual(result['monitor_jobs'], 1)
        self.assertEqual(result['spoolman_tables'], {'filament': 1, 'spool': 1, 'vendor': 1})
        self.assertEqual(self.db.execute('SELECT remaining FROM spool').fetchone(), (470,))
        self.assertEqual(self.spoolman.read_bytes(), before)
        self.assertEqual((self.monitor / 'access-token').read_text().strip(), self.token)
        if os.name != 'nt':
            self.assertEqual(snapshot.stat().st_mode & 0o777, 0o700)
            for path in snapshot.iterdir():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_missing_or_wrong_spoolman_database_never_publishes_partial_success(self):
        self.db.execute('DROP TABLE spool')
        self.db.commit()
        with self.assertRaises(ValueError):
            self.make()
        self.assertEqual(list(self.destination.iterdir()), [])
        self.db.close()
        self.spoolman.unlink()
        with self.assertRaises(ValueError):
            self.make()
        self.assertFalse(self.spoolman.exists())  # No empty source created.

    def test_broken_relationship_is_not_a_valid_restore(self):
        self.db.execute('UPDATE spool SET filament_id=42')
        self.db.commit()
        with self.assertRaises(ValueError):
            self.make()
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_failed_restore_prevents_publishing_and_preserves_old_snapshots(self):
        old = self.make()
        before = {p.name: p.read_bytes() for p in old.iterdir()}
        with patch('suite.snapshots.backup.restore', side_effect=ValueError('test failure')):
            with self.assertRaises(ValueError):
                self.make()
        self.assertEqual([p.resolve() for p in self.destination.iterdir()], [old])
        self.assertEqual({p.name: p.read_bytes() for p in old.iterdir()}, before)

    def test_modified_or_missing_part_and_wrong_image_are_rejected(self):
        snapshot = self.make()
        path = snapshot / 'spoolman.sqlite3'
        original = path.read_bytes()
        path.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            verify_snapshot(snapshot)
        path.write_bytes(original)
        metadata = snapshot / 'snapshot.json'
        data = json.loads(metadata.read_text())
        data['images']['monitor'] = 'wrong-image'
        metadata.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            verify_snapshot(snapshot)

    def test_source_destination_overlap_and_symlinks_are_blocked(self):
        for destination in [self.root, self.monitor, self.monitor / 'backup', self.spoolman.parent]:
            with self.assertRaises(ValueError):
                create_snapshot(self.monitor, self.spoolman, destination,
                                monitor_image='monitor', spoolman_image='spoolman')
        if os.name != 'nt':
            link = self.root / 'link.db'
            link.symlink_to(self.spoolman)
            with self.assertRaises(ValueError):
                create_snapshot(self.monitor, link, self.destination,
                                monitor_image='monitor', spoolman_image='spoolman')

    def test_suspect_backup_member_is_not_followed(self):
        if os.name == 'nt':
            self.skipTest('symlink privileges differ on Windows')
        snapshot = self.make()
        member = snapshot / 'spoolman.sqlite3'
        member.unlink()
        member.symlink_to(self.spoolman)
        with self.assertRaises(ValueError):
            verify_snapshot(snapshot)


if __name__ == '__main__':
    unittest.main()
