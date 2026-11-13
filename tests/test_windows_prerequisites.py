import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import desktop_entry


class WindowsPrerequisiteTests(unittest.TestCase):
    def test_working_spoolman_import_requires_no_installer_or_network(self):
        result=SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
        with patch.object(desktop_entry.subprocess,'CREATE_NO_WINDOW',0,create=True), \
             patch.object(desktop_entry.subprocess,'run',return_value=result), \
             patch.object(desktop_entry,'message') as message:
            self.assertTrue(desktop_entry.ensure_runtime(Path('fixture'),Path('data')))
            message.assert_not_called()

    def test_declining_runtime_install_never_downloads_or_starts_application(self):
        result=SimpleNamespace(returncode=1,stdout=b'',stderr=b'DLL load failed')
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(desktop_entry.subprocess,'CREATE_NO_WINDOW',0,create=True), \
             patch.object(desktop_entry.subprocess,'run',return_value=result), \
             patch.object(desktop_entry,'message',return_value=False), \
             patch('urllib.request.urlopen') as download:
            self.assertFalse(desktop_entry.ensure_runtime(Path('fixture'),Path(folder)/'data'))
            download.assert_not_called()
            self.assertEqual((Path(folder)/'Startprotokolle/laufzeitpruefung.log').read_bytes(),result.stderr)

    def test_runtime_installer_matches_running_interpreter(self):
        for architecture, suffix in [('arm64', 'arm64'), ('x86_64', 'x64')]:
            with patch.object(desktop_entry, 'runtime_architecture', return_value=architecture):
                self.assertTrue(desktop_entry.cpp_runtime_download().endswith('/vc_redist.' + suffix + '.exe'))
                self.assertEqual(desktop_entry.windows_target().platform, 'windows-' + architecture)


    def test_download_requires_valid_exact_microsoft_publisher(self):
        for status,subject,accepted in [
            ('Valid','CN=Microsoft Corporation, O=Microsoft Corporation, C=US',True),
            ('NotTrusted','CN=Microsoft Corporation',False),
            ('Valid','CN=Microsoft Corporation Fake, O=Other',False)]:
            result=SimpleNamespace(returncode=0,stdout=json.dumps({'status':status,'subject':subject}).encode())
            with patch.object(desktop_entry.subprocess,'CREATE_NO_WINDOW',0,create=True), \
                 patch.object(desktop_entry.subprocess,'run',return_value=result):
                if accepted:desktop_entry.microsoft_signature(Path('fixture.exe'))
                else:
                    with self.assertRaises(ValueError):desktop_entry.microsoft_signature(Path('fixture.exe'))


if __name__=='__main__':unittest.main()
