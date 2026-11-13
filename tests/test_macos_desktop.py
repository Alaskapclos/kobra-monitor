import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from suite.desktop import child_command, POSIX_BOOTSTRAP
from macos_entry import install_application, load_manifest
from suite.native_targets import native_target, runtime_architecture


class MacCommandTests(unittest.TestCase):
    def test_isolated_mac_command_keeps_paths_and_arguments_separate(self):
        command=child_command(Path('/fixture app'), 'spoolman',Path('/fixture app/app/spoolman'),
                              ['-m','uvicorn','fixture:app','--port','12345'],system='darwin',parent_fd=7)
        self.assertEqual(command[0],'/fixture app/runtime/spoolman/bin/python3.14')
        self.assertEqual(command[1:6],['-I','-B','-X','utf8','-c'])
        self.assertEqual(command[-6:],['7','module','uvicorn','fixture:app','--port','12345'])
        windows=child_command(Path('fixture'), 'monitor',Path('fixture/app/monitor'),['monitor.py'],system='win32')
        self.assertEqual(windows[1:],['-X','utf8','monitor.py'])

    def test_posix_child_exits_when_its_own_parent_pipe_closes(self):
        if os.name=='nt':self.skipTest('POSIX inherited descriptors')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);script=root/'child.py';ready=root/'ready'
            script.write_text('from pathlib import Path\nimport time\nPath('+repr(str(ready))+').touch()\ntime.sleep(30)\n')
            reader,writer=os.pipe()
            process=subprocess.Popen([sys.executable,'-I','-B','-c',POSIX_BOOTSTRAP,
                folder,folder,str(reader),'script',str(script)],pass_fds=(reader,))
            os.close(reader)
            try:
                end=time.monotonic()+5
                while not ready.exists() and time.monotonic()<end:time.sleep(.02)
                self.assertTrue(ready.exists())
                os.close(writer);writer=None
                self.assertEqual(process.wait(timeout=5),-signal.SIGTERM)
            finally:
                if writer is not None:os.close(writer)
                if process.poll() is None:process.terminate();process.wait(timeout=5)


class MacInstallTests(unittest.TestCase):
    def fixture(self,root):
        app=root/'Original Test.app';bundle=app/'Contents/Resources/payload';bundle.mkdir(parents=True)
        files={}
        for n in range(12):
            name=f'app/{n}.py';path=bundle/name;path.parent.mkdir(exist_ok=True)
            path.write_bytes(b'fixture');files[name]=hashlib.sha256(b'fixture').hexdigest()
        manifest={'format':'kobra-macos-test-bundle-v1','platform':native_target('macos',runtime_architecture()).platform,
                  'version':'0.34.0-alpha.1','bundle_id':'a'*64,'files':files}
        (bundle/'native-bundle.json').write_text(json.dumps(manifest))
        return app,manifest

    def test_new_app_is_verified_and_repeat_does_not_replace_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);app,manifest=self.fixture(root);target=root/'Programs/Test.app'
            self.assertEqual(install_application(app,target,manifest),target)
            self.assertEqual(load_manifest(target/'Contents/Resources/payload',verify=True)['bundle_id'],'a'*64)
            self.assertEqual(install_application(app,target,manifest),target)
            changed=dict(manifest,bundle_id='b'*64)
            with self.assertRaises(ValueError):install_application(app,target,changed)
            self.assertEqual(load_manifest(target/'Contents/Resources/payload')['bundle_id'],'a'*64)

    def test_changed_program_file_never_publishes_an_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);app,manifest=self.fixture(root);target=root/'Programs/Test.app'
            (app/'Contents/Resources/payload/app/0.py').write_bytes(b'changed')
            with self.assertRaises(ValueError):install_application(app,target,manifest)
            self.assertFalse(target.exists())
            self.assertEqual(list(target.parent.iterdir()),[])


if __name__=='__main__':unittest.main()
