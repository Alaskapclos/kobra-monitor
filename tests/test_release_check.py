# SPDX-License-Identifier: GPL-3.0-only
"""Public source archives must not leak private state or misrepresent a frozen build."""
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile
from scripts.release_check import check_files, collect_zip, collect_source
from unittest.mock import patch


def public_files():
    return {'LICENSE': b'GPL-3.0-only', 'NOTICE.md': b'Copyright', 'SOURCES.json': b'{}',
            'README.md': b'**Entwicklungsstand: 0.38.0-alpha.1 - test**', 'SECURITY.md': b'Local',
            'VERSION': b'0.38.0-alpha.1\n', 'compose.yaml': b'image: kobra-monitor:0.38.0-alpha.1',
            '.github/workflows/ci.yml': b'image: kobra-monitor:0.38.0-alpha.1',
            'static/index.html': b'KOBRA MONITOR / 0.38 ALPHA'}


class ReleaseCheckTests(unittest.TestCase):
    def test_without_git_requires_complete_frozen_tree_and_hashes(self):
        files = public_files()
        files['BUILD.json'] = json.dumps({'version':'0.38.0-alpha.1',
            'source_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}).encode()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,body in files.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
            with patch('scripts.release_check.subprocess.run',side_effect=FileNotFoundError):
                actual,errors=collect_source(root)
                self.assertEqual(errors,[])
                self.assertEqual(actual,files)
                (root/'extra.txt').write_text('not catalogued')
                self.assertTrue(collect_source(root)[1])
                (root/'extra.txt').unlink()
                (root/'LICENSE').write_text('changed')
                self.assertTrue(collect_source(root)[1])
                (root/'.git').mkdir()
                with self.assertRaises(FileNotFoundError):collect_source(root)

    def archive(self, entries):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                for name, body in entries:
                    archive.writestr(name, body)
            return collect_zip(path)

    def test_public_source_zip_and_exact_frozen_manifest_pass(self):
        files = public_files()
        files['BUILD.json'] = json.dumps({'version': '0.38.0-alpha.1',
            'source_sha256': {name: hashlib.sha256(body).hexdigest() for name, body in files.items()}}).encode()
        actual, errors = self.archive([('Kobra-Monitor/' + n, b) for n, b in files.items()])
        self.assertEqual(errors + check_files(actual, check_build=True), [])

    def test_private_database_sidecars_originals_and_credentials_are_rejected(self):
        for name in ('account.json', 'history.sqlite3-wal', 'cache.db-shm', 'file-archive/model.3mf',
                     'spoolman.json', 'config.json', '.git/config', '.env', '.push-secret',
                     'access-token', 'customer.stl', 'certificate.pfx'):
            with self.subTest(name=name):
                errors = check_files({**public_files(), name: b'private'})
                self.assertIn('Runtime/private file: ' + name, errors)

    def test_private_key_formats_in_disguised_file_are_rejected(self):
        for kind in ('', 'OPENSSH ', 'ENCRYPTED ', 'RSA ', 'EC '):
            secret = ('-----BEGIN ' + kind + 'PRIVATE KEY-----').encode()
            self.assertIn('Private-key block: innocuous.txt',
                          check_files({**public_files(), 'innocuous.txt': secret}))

    def test_other_computer_personal_paths_are_rejected(self):
        for body in (b'/Users/' + b'Example/Documents/data', b'/home/' + b'example/data',
                     b'C:' + bytes([92]) + b'Users' + bytes([92]) + b'Example' + bytes([92]) + b'data'):
            self.assertIn('Personal absolute path: example.txt',
                          check_files({**public_files(), 'example.txt': body}))

    def test_version_claims_and_required_license_file_are_checked(self):
        files = public_files(); files.pop('LICENSE')
        files['compose.yaml'] = b'image: kobra-monitor:0.37.0-alpha.1'
        files['README.md'] = b'old'; files['static/index.html'] = b'KOBRA MONITOR / 0.37 ALPHA'
        errors = check_files(files)
        for expected in ('Missing LICENSE', 'Image version mismatch: compose.yaml',
                         'README version mismatch', 'UI version mismatch'):
            self.assertIn(expected, errors)

    def test_stale_missing_and_incomplete_manifest_fail_closed(self):
        files = public_files()
        self.assertIn('Missing or invalid BUILD source manifest', check_files(files, check_build=True))
        files['BUILD.json'] = json.dumps({'version': '0.38.0-alpha.1', 'source_sha256': {}}).encode()
        self.assertTrue(any('BUILD source manifest differs' in e for e in check_files(files, check_build=True)))
        self.assertEqual(check_files(files), [])  # Working-tree inspection does not claim a frozen build.

    def test_archive_paths_duplicates_and_links_are_rejected_without_extraction(self):
        for name in ('../outside', '/outside', 'Kobra-Monitor/../outside',
                     'Kobra-Monitor/a' + bytes([92]).decode() + 'b', 'other/root'):
            _, errors = self.archive([(name, b'data')]); self.assertTrue(errors, name)
        _, errors = self.archive([('Kobra-Monitor/A.md', b'a'), ('Kobra-Monitor/a.md', b'b')])
        self.assertTrue(any('Duplicate' in e for e in errors))
        link = zipfile.ZipInfo('Kobra-Monitor/link'); link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        _, errors = self.archive([(link, b'outside')]); self.assertTrue(any('Linked' in e for e in errors))

    def test_known_upstream_service_defaults_do_not_hide_other_personal_paths(self):
        name = 'vendor/kobra-bridge/kobrax_moonraker_bridge.py'
        body = b'"' + b'/home/' + b'pi/klipper' + b'"'
        self.assertEqual(check_files({**public_files(), name: body}), [])
        self.assertIn('Personal absolute path: ' + name,
                      check_files({**public_files(), name: body + b' /home/' + b'owner/private'}))
        self.assertIn('Personal absolute path: other.py',
                      check_files({**public_files(), 'other.py': body}))

    def test_root_directory_member_is_allowed(self):
        files, errors = self.archive([('Kobra-Monitor/', b''), ('Kobra-Monitor/README.md', b'public')])
        self.assertEqual(errors, [])
        self.assertEqual(files, {'README.md': b'public'})
        link = zipfile.ZipInfo('Kobra-Monitor/'); link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        _, errors = self.archive([(link, b'outside')])
        self.assertTrue(any('special ZIP root' in e for e in errors))

    def test_oversized_member_is_rejected_before_read(self):
        from unittest.mock import patch
        with patch('scripts.release_check.MAX_FILE', 2):
            files, errors = self.archive([('Kobra-Monitor/large.txt', b'large')])
        self.assertEqual(files, {}); self.assertTrue(any('size limit' in e for e in errors))
