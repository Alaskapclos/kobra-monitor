import json
from pathlib import Path
import sys
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import test_suite_snapshots as fixtures
from suite.desktop import FORMAT
from suite.native_backup import run_due
from suite.snapshots import verify_snapshot


class NativeBackupTests(unittest.TestCase):
    def test_paired_native_backup_restores_both_databases_and_records_profile(self):
        fixture=fixtures.SuiteSnapshotTests();fixture.setUp()
        try:
            profile={'format':FORMAT,'identity':'fixture','version':'0.33.0-alpha.1',
                     'backend_url':'http://127.0.0.1:17136/spoolman'}
            (fixture.root/'desktop.json').write_text(json.dumps(profile))
            (fixture.monitor/'spoolman.json').write_text(json.dumps({'url':profile['backend_url']}))
            state={};result=run_due(fixture.root,profile['version'],clock=lambda:100000,state=state)
            self.assertTrue(verify_snapshot(result)['verified'])
            self.assertEqual(verify_snapshot(result)['monitor_jobs'],1)
            with zipfile.ZipFile(result/'monitor.zip') as archive:
                names=[n for n in archive.namelist() if n.endswith('compose.yaml')]
                self.assertEqual(len(names),1)
                self.assertEqual(json.loads(archive.read(names[0])),profile)
            self.assertIsNone(run_due(fixture.root,profile['version'],clock=lambda:100001,state=state))
            self.assertIsNone(run_due(fixture.root,profile['version'],clock=lambda:100001,state={}))
            self.assertEqual(len(list((fixture.root/'backups').iterdir())),1)
            (fixture.monitor/'spoolman.json').write_text(json.dumps({'url':'http://192.168.1.20:7912'}))
            with self.assertRaises(ValueError):
                run_due(fixture.root,profile['version'],clock=lambda:100002,state=state)
            self.assertEqual(len(list((fixture.root/'backups').iterdir())),1)
        finally:fixture.tearDown()

    def test_waits_until_both_services_have_data(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(run_due(folder,'0.33.0-alpha.1'))
            self.assertFalse((Path(folder)/'backups').exists())


if __name__=='__main__':unittest.main()
