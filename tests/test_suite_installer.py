import copy
import io
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from suite.bundle import render_installer
from suite.deployment import contract, prepare, compose
from suite_installer import inspect_project


class SuiteInstallerTests(unittest.TestCase):
    def test_renderer_refuses_shell_code_and_has_valid_portable_syntax(self):
        for image, image_id, name, digest in [
            ('kobra-monitor:0.32.0-alpha.1', 'sha256:'+'a'*64, 'monitor.tar', 'b'*64),
        ]:
            rendered = render_installer(image, image_id, name, digest)
            self.assertNotIn('@IMAGE', rendered)
            self.assertIn('--no-recreate', rendered)
            self.assertNotIn('docker.sock', rendered)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'Installieren.sh';path.write_text(rendered)
                if shutil.which('sh'):
                    result=subprocess.run(['sh','-n',str(path)],capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
        for field, value in [('image','kobra-monitor:latest;touch /tmp/oops'),
                             ('name','$(touch oops).tar'),('image_id','other'),('digest','b'*63)]:
            args={'image':'kobra-monitor:0.32.0-alpha.1','image_id':'sha256:'+'a'*64,
                  'archive_name':'monitor.tar','archive_sha256':'b'*64}
            args[{'name':'archive_name','digest':'archive_sha256'}.get(field,field)]=value
            with self.assertRaises(ValueError):render_installer(**args)

    def test_resume_accepts_only_the_exact_saved_project_and_version(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'installation'
            image='kobra-monitor:0.32.0-alpha.1'
            prepare(path,image,address='192.168.1.50',port=17126)
            before={p.name:p.read_bytes() for p in path.iterdir()}
            result=inspect_project(path,image)
            self.assertEqual(result['bind_address'],'192.168.1.50')
            self.assertEqual(result['port'],17126)
            with self.assertRaises(ValueError):inspect_project(path,'kobra-monitor:0.31.1-alpha.1')
            self.assertEqual(before,{p.name:p.read_bytes() for p in path.iterdir()})
            data=json.loads((path/'compose.json').read_text())
            data['services']['monitor']['volumes'].append('/:/host')
            (path/'compose.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):inspect_project(path,image)

    def test_lan_choice_is_saved_and_tampering_remains_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'installation'
            image='kobra-monitor:0.43.0-alpha.1'
            prepare(path,image,network='lan')
            self.assertEqual(inspect_project(path,image)['network'],'lan')
            changed=json.loads((path/'compose.json').read_text())
            changed['services']['spoolman']['networks'].append('printers')
            (path/'compose.json').write_text(json.dumps(changed))
            with self.assertRaises(ValueError):inspect_project(path,image)

    def test_endpoint_requires_explicit_private_address_and_never_wildcard(self):
        base=contract('kobra-monitor:0.32.0-alpha.1')
        self.assertNotIn('bind_address',base)  # Existing loopback contracts remain compatible.
        for address in ['192.168.1.50','10.0.0.2','172.16.1.2']:
            c=contract(base['monitor_image'],address=address)
            self.assertEqual(compose(c)['services']['monitor']['ports'],[address+':17125:7125'])
        for address in ['0.0.0.0','8.8.8.8','::','localhost','127.0.0.1;echo oops']:
            with self.assertRaises(ValueError):contract(base['monitor_image'],address=address)

    @unittest.skipIf(sys.platform=='win32','POSIX test-installer script; native Windows package is separate')
    def test_existing_target_is_refused_before_image_load_or_container_start(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);existing=root/'already-used';existing.mkdir()
            (existing/'keep.txt').write_text('preserve')
            trace=root/'docker-calls'
            script=root/'Installieren.sh'
            script.write_text(render_installer('kobra-monitor:0.32.0-alpha.1','sha256:'+'a'*64,'monitor.tar','b'*64))
            import os
            env={**os.environ,'TRACE':str(trace),'DOCKER_HOST':''}
            # The hardened Linux test container mounts /tmp noexec. Model the
            # external commands as shell functions, without executing files from
            # that directory or weakening the container's filesystem settings.
            fixture='uname() { echo Linux; }; docker() { printf "%s\\n" "$*" >> "$TRACE"; case "$1" in info) echo linux/amd64;; context) echo unix:///var/run/docker.sock;; compose) return 0;; *) return 99;; esac; }; . "$0"'
            result=subprocess.run(['sh','-c',fixture,str(script),'--yes','--directory',str(existing)],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            if 'existiert bereits' not in result.stderr:
                diagnostic=subprocess.run(['sh','-x','-c',fixture,str(script),'--yes','--directory',str(existing)],env=env,capture_output=True,text=True)
                self.fail(diagnostic.stderr+'\nFake Docker trace:\n'+trace.read_text())
            self.assertEqual((existing/'keep.txt').read_text(),'preserve')
            calls=trace.read_text()
            self.assertNotIn('image load',calls)
            self.assertNotIn(' run ',calls)
