import json
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from access import Access
from accounts import write_account
from configuration import save_config
from history import History
from suite.desktop import FORMAT, InstallationLock, prepare_data
from suite.native_upgrade import (TARGET, choose_profile, upgrade_profile, target_path,
    existing_target, verify_backup, _inventory, _publish)


class NativeUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve();self.source = self.base/'Daten'
        monitor = self.source/'monitor';monitor.mkdir(parents=True)
        save_config(monitor, ['192.168.254.254'])
        Access(monitor)
        write_account(monitor, 'Fixture Owner', 'Only a synthetic fixture password!')
        history = History(monitor/'history.sqlite3')
        history.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            ('f'*32, '192.168.254.254', '', 'fixture.gcode', 'completed', 1, 2, 2, 1, 100, 20, 20, 3))
        history.db.commit();history.close()
        folder = self.source/'spoolman';folder.mkdir()
        with closing(sqlite3.connect(folder/'spoolman.db')) as db:
            db.executescript('CREATE TABLE vendor(id INTEGER PRIMARY KEY);'
                'CREATE TABLE filament(id INTEGER PRIMARY KEY,vendor_id REFERENCES vendor(id));'
                'CREATE TABLE spool(id INTEGER PRIMARY KEY,filament_id REFERENCES filament(id),remaining REAL);'
                'INSERT INTO vendor VALUES(1);INSERT INTO filament VALUES(1,1);INSERT INTO spool VALUES(1,1,470);')
        self.profile = {'format': FORMAT, 'version': '0.34.0-alpha.1',
            'identity': 'a'*32, 'backend_url': 'http://127.0.0.1:17136/spoolman'}
        (self.source/'desktop.json').write_text(json.dumps(self.profile))
        (monitor/'spoolman.json').write_text(json.dumps({'url': self.profile['backend_url'],
            'mappings': {'192.168.254.254': {'0': 1}}, 'sku_links': {}}))
        (self.source/'owner-note.txt').write_text('Fixture data remains intact.')
        self.target = target_path(self.source, TARGET)
        self.backups = self.source.with_name('Daten-Uebernahmesicherungen')

    def tearDown(self):
        self.temp.cleanup()

    def test_042_profile_is_copied_to_new_version_with_original_data_intact(self):
        self.profile['version'] = '0.42.0-alpha.1'
        (self.source/'desktop.json').write_text(json.dumps(self.profile))
        before = _inventory(self.source)
        target = upgrade_profile(self.source, TARGET)
        self.assertEqual(_inventory(self.source), before)
        self.assertEqual(json.loads((target/'desktop.json').read_text())['version'], TARGET)
        self.assertEqual(verify_backup(next(self.backups.iterdir()))['spools'], 1)

    def test_stopped_profile_restores_in_separate_directory_and_backup_is_verifiable(self):
        before = _inventory(self.source)
        result = upgrade_profile(self.source, TARGET)
        self.assertEqual(result, self.target)
        self.assertEqual(_inventory(self.source), before)
        self.assertEqual((self.target/'monitor/account.json').read_bytes(),
                         (self.source/'monitor/account.json').read_bytes())
        self.assertEqual((self.target/'monitor/spoolman.json').read_bytes(),
                         (self.source/'monitor/spoolman.json').read_bytes())
        with closing(sqlite3.connect(self.target/'spoolman/spoolman.db')) as db:
            self.assertEqual(db.execute('SELECT remaining FROM spool').fetchone(), (470,))
        self.assertEqual(json.loads((self.target/'desktop.json').read_text())['version'], TARGET)
        self.assertEqual(existing_target(self.source, TARGET), self.target)
        backups = list(self.backups.iterdir());self.assertEqual(len(backups), 1)
        self.assertEqual(verify_backup(backups[0]),
            {'verified': True, 'version': '0.34.0-alpha.1', 'jobs': 1, 'spools': 1})
        # Normal endpoint refresh still applies, only to the new profile.
        prepare_data(self.target, TARGET, 'http://127.0.0.1:19998/spoolman')
        self.assertEqual(_inventory(self.source), before)
        self.assertEqual(choose_profile(self.source, TARGET), self.target)
        self.assertEqual(len(list(self.backups.iterdir())), 1)
        (backups[0]/'owner-note.txt').write_text('changed')
        with self.assertRaises(ValueError):verify_backup(backups[0])

    def test_040_profile_is_backed_up_and_restored_without_touching_source(self):
        self.profile['version'] = '0.40.0-alpha.1'
        (self.source/'desktop.json').write_text(json.dumps(self.profile))
        before = _inventory(self.source)
        self.assertEqual(upgrade_profile(self.source, TARGET), self.target)
        self.assertEqual(_inventory(self.source), before)
        self.assertEqual(verify_backup(next(self.backups.iterdir())),
                         {'verified': True, 'version': '0.40.0-alpha.1', 'jobs': 1, 'spools': 1})

    def test_041_grants_and_data_survive_separate_verified_upgrade(self):
        from native_control_settings import NativeControlSettings
        self.profile['version']='0.41.0-alpha.1'
        (self.source/'desktop.json').write_text(json.dumps(self.profile))
        grants={'192.168.254.254':{'controls':['light'],'drying_limit':55}}
        NativeControlSettings(self.source/'monitor').write(grants)
        before=_inventory(self.source)
        upgrade_profile(self.source,TARGET)
        self.assertEqual(_inventory(self.source),before)
        self.assertEqual(NativeControlSettings(self.target/'monitor').read(),grants)
        self.assertEqual(verify_backup(next(self.backups.iterdir()))['version'],'0.41.0-alpha.1')

    def test_explicit_consent_is_required_and_cancellation_writes_nothing(self):
        before = _inventory(self.source)
        self.assertIsNone(choose_profile(self.source, TARGET, confirm=lambda _: False))
        self.assertIsNone(choose_profile(self.source, TARGET))
        self.assertEqual(_inventory(self.source), before)
        self.assertFalse(self.backups.exists());self.assertFalse(self.target.exists())
        self.assertEqual(choose_profile(self.source, TARGET, stopping=True), self.target)
        self.assertFalse(self.target.exists())
        self.assertEqual(choose_profile(self.source, TARGET, confirm=lambda _: True), self.target)

    def test_unknown_versions_and_foreign_profiles_are_rejected(self):
        with self.assertRaises(ValueError):upgrade_profile(self.source, '0.43.0-alpha.1')
        self.profile['version'] = '0.33.0-alpha.1'
        (self.source/'desktop.json').write_text(json.dumps(self.profile))
        with self.assertRaises(ValueError):upgrade_profile(self.source, TARGET)
        self.assertFalse(self.target.exists())
        self.profile['version'] = '0.39.0-alpha.1'
        (self.source/'desktop.json').write_text(json.dumps(self.profile))
        self.assertEqual(upgrade_profile(self.source, TARGET), self.target)

    def test_running_or_uncleanly_stopped_app_cannot_be_copied(self):
        lock = InstallationLock(self.source/'desktop.lock');self.assertTrue(lock.acquire())
        try:
            with self.assertRaises(ValueError):upgrade_profile(self.source, TARGET)
        finally:lock.close()
        (self.source/'instance.json').write_text('{}')
        with self.assertRaises(ValueError):upgrade_profile(self.source, TARGET)
        self.assertFalse(self.target.exists());self.assertFalse(self.backups.exists())

    def test_external_inventory_and_corrupt_database_preserve_source(self):
        settings = self.source/'monitor/spoolman.json';original = settings.read_bytes()
        settings.write_text(json.dumps({'url': 'http://192.168.254.253:7912'}))
        before = _inventory(self.source)
        with self.assertRaises(ValueError):upgrade_profile(self.source, TARGET)
        self.assertEqual(_inventory(self.source), before)
        settings.write_bytes(original)
        db = self.source/'spoolman/spoolman.db';db.write_bytes(b'bad database')
        before = _inventory(self.source)
        with self.assertRaises((ValueError, sqlite3.DatabaseError)):upgrade_profile(self.source, TARGET)
        self.assertEqual(_inventory(self.source), before);self.assertFalse(self.target.exists())

    def test_existing_target_is_not_replaced_even_if_it_is_empty(self):
        self.target.mkdir()
        before = _inventory(self.source)
        with self.assertRaises(FileExistsError):upgrade_profile(self.source, TARGET)
        with self.assertRaises((ValueError, OSError)):existing_target(self.source, TARGET)
        self.assertEqual(list(self.target.iterdir()), []);self.assertEqual(_inventory(self.source), before)
        incoming = self.base/'incoming';incoming.mkdir();(incoming/'file').write_text('new')
        with self.assertRaises(OSError):_publish(incoming, self.target)
        self.assertTrue((incoming/'file').exists());self.assertEqual(list(self.target.iterdir()), [])

    def test_symlinks_and_hard_links_do_not_escape_profile(self):
        if os.name == 'nt':self.skipTest('Windows symbolic link privileges differ')
        outside = self.base/'outside';outside.mkdir();(outside/'file').write_text('private fixture')
        link = self.source/'link';link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):upgrade_profile(self.source, TARGET)
        link.unlink()
        self.target.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):existing_target(self.source, TARGET)
        self.target.unlink()
        os.link(outside/'file', self.source/'linked-file')
        with self.assertRaises(ValueError):upgrade_profile(self.source, TARGET)
        self.assertEqual((outside/'file').read_text(), 'private fixture');self.assertFalse(self.target.exists())

    def test_failed_restore_never_publishes_target_or_changes_original(self):
        import suite.native_upgrade as module
        original = module._copy;calls = 0;before = _inventory(self.source)
        def fail_restore(*args):
            nonlocal calls
            calls += 1
            if calls == 2:raise OSError('Synthetic restore failure')
            return original(*args)
        with patch.object(module, '_copy', side_effect=fail_restore):
            with self.assertRaises(OSError):upgrade_profile(self.source, TARGET)
        self.assertFalse(self.target.exists());self.assertEqual(_inventory(self.source), before)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_failed_target_publication_keeps_verified_backup(self):
        import suite.native_upgrade as module
        original = module._publish;calls = 0;before = _inventory(self.source)
        def fail_target(*args):
            nonlocal calls
            calls += 1
            if calls == 2:raise OSError('Synthetic publication failure')
            return original(*args)
        with patch.object(module, '_publish', side_effect=fail_target):
            with self.assertRaises(OSError):upgrade_profile(self.source, TARGET)
        self.assertFalse(self.target.exists());self.assertEqual(_inventory(self.source), before)
        saved = list(self.backups.iterdir());self.assertEqual(len(saved), 1)
        self.assertTrue(verify_backup(saved[0])['verified'])

    def test_schema_migration_cannot_silently_change_existing_rows(self):
        before = _inventory(self.source)
        def changed(path):
            history = History(path)
            history.db.execute('UPDATE jobs SET progress=7');history.db.commit()
            return history
        with patch('history.History', side_effect=changed):
            with self.assertRaises(ValueError):upgrade_profile(self.source, TARGET)
        self.assertEqual(_inventory(self.source), before);self.assertFalse(self.target.exists())

    def test_missing_printer_configuration_is_allowed_without_inventing_one(self):
        (self.source/'monitor/config.json').unlink()
        result = upgrade_profile(self.source, TARGET)
        self.assertFalse((result/'monitor/config.json').exists())

    def test_committed_wal_rows_are_copied_without_opening_original_database(self):
        path = self.source/'spoolman/spoolman.db'
        with closing(sqlite3.connect(path)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('INSERT INTO spool VALUES(2,1,123)');db.commit()
            self.assertGreater(path.with_name(path.name+'-wal').stat().st_size, 0)
            before = _inventory(self.source)
            result = upgrade_profile(self.source, TARGET)
            self.assertEqual(_inventory(self.source), before)
            with closing(sqlite3.connect(result/'spoolman/spoolman.db')) as restored:
                self.assertEqual(restored.execute('SELECT remaining FROM spool ORDER BY id').fetchall(),
                                 [(470,), (123,)])

    def test_insufficient_space_leaves_existing_files_and_targets_untouched(self):
        from types import SimpleNamespace
        before = _inventory(self.source)
        with patch('suite.native_upgrade.shutil.disk_usage', return_value=SimpleNamespace(free=0)):
            with self.assertRaises(ValueError):upgrade_profile(self.source, TARGET)
        self.assertEqual(_inventory(self.source), before)
        self.assertFalse(self.target.exists());self.assertFalse(self.backups.exists())

    def test_copy_and_backup_verification_never_open_network_sockets(self):
        with patch('socket.socket', side_effect=AssertionError('Network access during data transfer')):
            result = upgrade_profile(self.source, TARGET)
            self.assertEqual(result, self.target)
            self.assertTrue(verify_backup(next(self.backups.iterdir()))['verified'])

    def test_push_registration_without_its_private_key_is_not_a_complete_backup(self):
        with closing(sqlite3.connect(self.source/'monitor/history.sqlite3')) as db:
            db.execute('CREATE TABLE push_devices(id TEXT)')
            db.execute("INSERT INTO push_devices VALUES('synthetic-device')");db.commit()
        before = _inventory(self.source)
        with self.assertRaises(ValueError):upgrade_profile(self.source, TARGET)
        self.assertEqual(_inventory(self.source), before);self.assertFalse(self.target.exists())

    def test_private_notification_key_is_preserved_byte_for_byte(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        key = ec.generate_private_key(ec.SECP256R1()).private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        (self.source/'monitor/push-vapid.pem').write_bytes(key)
        result = upgrade_profile(self.source, TARGET)
        self.assertEqual((result/'monitor/push-vapid.pem').read_bytes(), key)


if __name__ == '__main__':unittest.main()
