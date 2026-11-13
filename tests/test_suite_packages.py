import base64
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import unittest
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from suite.packages import COMPONENTS, FORMAT, verify_package


class PackageTests(unittest.TestCase):
    def setUp(self):
        # Ephemeral test key, never a publishing credential.
        self.key = Ed25519PrivateKey.generate()
        self.trusted = {'fixture': self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)}
        self.files, components = {}, {}
        for name in COMPONENTS:
            payload = 'components/' + name + '/program.bin'
            license_file, sources = 'licenses/' + name + '.txt', 'sources/' + name + '.zip'
            self.files.update({payload: b'fixture payload', license_file: b'fixture license',
                               sources: b'fixture source, not a distributed binary'})
            components[name] = {'version': '1.2.3', 'license': 'fixture-only',
                                'license_file': license_file, 'source_file': sources,
                                'payload_files': [payload]}
        self.manifest = {'format': FORMAT, 'version': '1.2.3', 'platform': 'linux-x86_64',
                         'key_id': 'fixture', 'components': components, 'files': {}}

    def package(self, *, metadata=None, data=None, edit=None):
        files = dict(self.files if data is None else data)
        manifest = json.loads(json.dumps(self.manifest if metadata is None else metadata))
        manifest['files'] = {n: {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
                             for n, b in files.items()}
        if edit:
            edit(manifest, files)
        body = json.dumps(manifest, separators=(',', ':')).encode()
        return self.raw_package(files, body)

    def raw_package(self, files, body):
        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
            archive.writestr('release.json', body)
            archive.writestr('release.sig', base64.b64encode(self.key.sign(body)))
        result.seek(0)
        return result

    def verify(self, package):
        return verify_package(package, self.trusted, 'linux-x86_64')

    def rewrite(self, package, edit):
        with zipfile.ZipFile(package) as archive:
            files = {n: archive.read(n) for n in archive.namelist()}
        edit(files)
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as archive:
            for n, data in files.items():
                archive.writestr(n, data)
        out.seek(0)
        return out

    def test_complete_signed_package_is_verified_without_extracting_or_running(self):
        proof = self.verify(self.package())
        self.assertEqual((proof.version, proof.files), ('1.2.3', 12))
        self.assertGreater(proof.expanded_bytes, 0)

    def test_unknown_or_replaced_publisher_key_is_not_trusted(self):
        with self.assertRaises(ValueError):
            verify_package(self.package(), {}, 'linux-x86_64')
        other = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        with self.assertRaises(ValueError):
            verify_package(self.package(), {'fixture': other}, 'linux-x86_64')

    def test_unsigned_or_modified_manifest_is_rejected(self):
        for change in [lambda f: f.pop('release.sig'),
                       lambda f: f.update({'release.sig': b'not-a-signature'}),
                       lambda f: f.update({'release.json': f['release.json'] + b' '})]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(self.rewrite(self.package(), change))

    def test_signed_wrong_platform_and_floating_versions_are_rejected(self):
        with self.assertRaises(ValueError):
            verify_package(self.package(), self.trusted, 'windows-x86_64')
        for field in ['version', 'components']:
            metadata = json.loads(json.dumps(self.manifest))
            if field == 'version':
                metadata[field] = 'latest'
            else:
                metadata[field]['spoolman']['version'] = 'latest'
            with self.assertRaises(ValueError):
                self.verify(self.package(metadata=metadata))

    def test_missing_components_licenses_sources_and_payloads_are_rejected(self):
        for name in ['components/spoolman/program.bin', 'licenses/python.txt', 'sources/ffmpeg.zip']:
            files = dict(self.files)
            del files[name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.verify(self.package(data=files))
        self.manifest['components'].pop('spoolman')
        with self.assertRaises(ValueError):
            self.verify(self.package())

    def test_corrupt_file_extra_file_and_unowned_program_are_rejected(self):
        for change in [lambda f: f.update({'components/monitor/program.bin': b'corrupt'}),
                       lambda f: f.update({'unexpected.exe': b'extra'})]:
            with self.assertRaises(ValueError):
                self.verify(self.rewrite(self.package(), change))
        files = {**self.files, 'components/monitor/undeclared.exe': b'not assigned'}
        with self.assertRaises(ValueError):
            self.verify(self.package(data=files))

    def test_hostile_paths_case_collisions_and_file_directory_conflicts(self):
        for name in ['../outside', '/outside', 'a/../outside', 'a\\outside', 'C:/outside',
                     'components/monitor/AUX.txt', 'components/monitor/x.',
                     'components/monitor/PROGRAM.bin', 'components/monitor/program.bin/file']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.verify(self.package(data={**self.files, name: b'hostile'}))

    def test_symlink_and_duplicate_zip_entry_are_rejected(self):
        original = self.package().getvalue()
        for symbolic in [False, True]:
            out = io.BytesIO(original)
            with zipfile.ZipFile(out, 'a') as archive, warnings.catch_warnings():
                warnings.simplefilter('ignore')
                item = zipfile.ZipInfo('components/monitor/program.bin')
                if symbolic:
                    item.filename = 'components/monitor/link'
                    item.create_system = 3
                    item.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(item, b'../outside')
            out.seek(0)
            with self.assertRaises(ValueError):
                self.verify(out)

    def test_signed_duplicate_json_field_and_oversized_claim_are_rejected(self):
        body = json.dumps(self.manifest).encode()[:-1] + b',"key_id":"fixture"}'
        with self.assertRaises(ValueError):
            self.verify(self.raw_package(self.files, body))
        def enlarge(manifest, _):
            manifest['files']['components/monitor/program.bin']['bytes'] = 20 * 1024**3
        with self.assertRaises(ValueError):
            self.verify(self.package(edit=enlarge))


if __name__ == '__main__':
    unittest.main()
