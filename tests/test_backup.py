import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backup import create, inspect, restore, run_due
from configuration import save_config, load_config
from access import Access
from history import History


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / 'source'
        self.data.mkdir()
        self.destination = self.root / 'backups'
        save_config(self.data, ['192.168.1.20'])
        self.token = Access(self.data).token
        self.history = History(self.data / 'history.sqlite3')
        self.history.db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ('a' * 32, '192.168.1.20', '', 'fixture.gcode', 'printing', 10, 20, None, 1, 20, 2, 10, 5))
        self.history.db.commit()
        self.image = 'kobra-monitor:fixture'

    def tearDown(self):
        self.history.close()
        self.temp.cleanup()

    def make(self, **kw):
        return create(self.data, self.destination, self.image, **kw)

    def test_full_roundtrip_includes_live_wal_config_code_and_extra_state(self):
        (self.data / 'extra.json').write_text('{"setting":true}')
        deployment = self.root / 'compose.yaml'
        deployment.write_text('services: {}\n')
        archive = self.make(deployment=deployment)
        metadata = inspect(archive)
        self.assertEqual(metadata['restore_image'], self.image)
        self.assertIn('compose.yaml', metadata['files'])
        self.assertNotIn('data/history.sqlite3-wal', metadata['files'])
        target = self.root / 'restored'
        restore(archive, target)
        self.assertEqual(load_config(target), ['192.168.1.20'])
        self.assertEqual(Access(target).token, self.token)
        self.assertEqual((target / 'extra.json').read_text(), '{"setting":true}')
        db = sqlite3.connect(target / 'history.sqlite3')
        self.assertEqual(db.execute('SELECT state FROM jobs').fetchone()[0], 'printing')
        db.close()
        if os.name != 'nt':
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
            self.assertEqual((target / 'access-token').stat().st_mode & 0o777, 0o600)

    def test_account_hash_survives_backup_and_restore_without_plaintext(self):
        from accounts import write_account, read_account, matches
        secret='Ein langes Sicherungs-Passwort!'
        write_account(self.data,'Besitzer',secret)
        archive=self.make();target=self.root/'with-account';restore(archive,target)
        self.assertTrue(matches(read_account(target),'Besitzer',secret))
        self.assertNotIn(secret,json.dumps(inspect(archive)))
        (self.data/'account.json').write_text('{}')
        with self.assertRaises(ValueError):self.make()

    def test_nested_backup_and_symlinks_are_not_silently_copied(self):
        (self.data / 'backups').mkdir()
        (self.data / 'backups' / 'old.zip').write_bytes(b'old')
        self.assertNotIn('data/backups/old.zip', inspect(self.make())['files'])
        if os.name != 'nt':
            (self.data / 'outside').symlink_to(self.root)
            with self.assertRaises(ValueError): self.make()

    def test_backup_cannot_recurse_into_source_or_its_parent(self):
        for path in (self.data, self.data / 'nested', self.root):
            with self.assertRaises(ValueError): create(self.data, path, self.image)

    def test_restore_refuses_existing_data(self):
        archive = self.make()
        marker = self.data / 'do-not-overwrite'
        marker.write_text('original')
        with self.assertRaises(ValueError): restore(archive, self.data)
        self.assertEqual(marker.read_text(), 'original')

    def rewrite(self, archive, change):
        with zipfile.ZipFile(archive) as source:
            files = {n: source.read(n) for n in source.namelist()}
        change(files)
        modified = self.root / 'modified.zip'
        with zipfile.ZipFile(modified, 'w') as out:
            for name, data in files.items(): out.writestr(name, data)
        return modified

    def test_corrupt_payload_is_rejected_before_any_restore(self):
        archive = self.rewrite(self.make(), lambda files: files.update({'data/config.json': b'corrupt'}))
        target = self.root / 'bad-restore'
        with self.assertRaises(ValueError): restore(archive, target)
        self.assertFalse(target.exists())

    def test_path_traversal_and_unexpected_files_are_rejected(self):
        for name in ('../outside', '/absolute', 'data/../../outside', 'data\\outside', 'C:/outside', 'unexpected'):
            archive = self.rewrite(self.make(), lambda files: files.update({name: b'x'}))
            with self.assertRaises(ValueError): inspect(archive)

    def test_duplicate_archive_members_are_rejected(self):
        archive = self.make()
        with zipfile.ZipFile(archive, 'a') as out:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                out.writestr('data/config.json', '{}')
        with self.assertRaises(ValueError): inspect(archive)

    def test_first_backup_immediate_restart_skips_and_due_backup_rotates(self):
        clock = [1793350000.0]
        def run():
            return run_due(self.data, self.destination, self.image, interval=86400, keep=7, clock=lambda: clock[0])
        self.assertIsNotNone(run())
        self.assertIsNone(run())
        unrelated = self.destination / 'kobra-backup-unrelated.zip'
        unrelated.write_text('keep')
        for _ in range(9):
            clock[0] += 86400
            self.assertIsNotNone(run())
        self.assertEqual(len(list(self.destination.glob('kobra-backup-*.zip'))), 8)
        self.assertEqual(unrelated.read_text(), 'keep')

    def test_failed_backup_does_not_prune_last_good_archive(self):
        archive = self.make(clock=lambda: 1000)
        (self.data / 'config.json').write_text('broken')
        with self.assertRaises((ValueError, KeyError)):
            run_due(self.data, self.destination, self.image, keep=1, clock=lambda: 100000)
        self.assertTrue(archive.exists())
        self.assertTrue(inspect(archive))

    def test_secrets_are_required_but_not_returned_in_inspection_metadata(self):
        archive = self.make()
        self.assertNotIn(self.token, json.dumps(inspect(archive)))
        (self.data / 'access-token').unlink()
        with self.assertRaises(FileNotFoundError): self.make()


if __name__ == '__main__':
    unittest.main()
