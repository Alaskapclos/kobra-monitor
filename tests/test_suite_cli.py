import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import suite_cli
import test_suite_packages


class SuiteCLITests(unittest.TestCase):
    def call(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = suite_cli.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_signed_package_check_has_no_install_side_effect(self):
        fixture = test_suite_packages.PackageTests()
        fixture.setUp()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive, key = root / 'release.zip', root / 'trusted.pub'
            archive.write_bytes(fixture.package().getvalue())
            key.write_bytes(fixture.trusted['fixture'])
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            code, out, err = self.call(['verify-package', str(archive), '--platform',
                'linux-x86_64', '--key-id', 'fixture', '--trusted-public-key', str(key)])
            self.assertEqual((code, err), (0, ''))
            proof = json.loads(out)
            self.assertTrue(proof['verified'])
            self.assertFalse(proof['installed'])
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_invalid_public_key_is_a_readable_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            key = Path(folder) / 'bad.pub'
            key.write_bytes(b'bad')
            code, out, err = self.call(['verify-package', 'missing.zip', '--platform',
                'linux-x86_64', '--key-id', 'fixture', '--trusted-public-key', str(key)])
            self.assertEqual((code, out), (2, ''))
            self.assertIn('32 Bytes', err)

    def test_missing_snapshot_is_a_failure_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            code, out, err = self.call(['verify-snapshot', str(Path(folder) / 'missing')])
            self.assertEqual((code, out), (2, ''))
            self.assertIn('Prüfung fehlgeschlagen', err)
