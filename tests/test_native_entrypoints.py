import io
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from suite.desktop import role_environment
from suite.native_entrypoints import MAC_ALEMBIC, windows_alembic


class NativeEntrypointTests(unittest.TestCase):
    def test_roles_prefer_their_own_console_tools_without_changing_parent(self):
        base={'PATH':'fixture-old-path'}
        mac=role_environment(Path('/fixture app'),'spoolman',base,system='darwin')
        self.assertTrue(mac['PATH'].startswith('/fixture app/runtime/spoolman/bin:'))
        windows=role_environment(Path('/fixture app'),'spoolman',base,system='win32')
        self.assertTrue(windows['PATH'].startswith('/fixture app/runtime/spoolman/Scripts;'))
        self.assertEqual(base,{'PATH':'fixture-old-path'})

    def test_portable_windows_launcher_contains_isolated_own_interpreter_and_console_main(self):
        body=windows_alembic(b'fixture-native-launcher')
        self.assertIn(b'#!"<launcher_dir>\\..\\python.exe" -B -X utf8\n',body)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            self.assertEqual(archive.namelist(),['__main__.py'])
            self.assertIn(b'from alembic.config import main',archive.read('__main__.py'))
        if sys.platform!='win32':
            self.assertEqual(subprocess.run(['/bin/sh','-n'],input=MAC_ALEMBIC.encode()).returncode,0)


if __name__=='__main__':unittest.main()
