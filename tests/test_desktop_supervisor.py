import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from suite.desktop import (InstallationLock, atomic_json, prepare_data, child_environment,
    create_control_server, controller_request, local_url, terminate_owned, FORMAT)


class DesktopDataTests(unittest.TestCase):
    def test_single_instance_lock_can_be_reacquired_after_release(self):
        with tempfile.TemporaryDirectory() as folder:
            a=InstallationLock(Path(folder)/'desktop.lock');b=InstallationLock(a.path)
            self.assertTrue(a.acquire())
            try:self.assertFalse(b.acquire())
            finally:a.close()
            self.assertTrue(b.acquire());b.close()

    def test_restart_preserves_account_and_mappings_and_only_rewrites_own_endpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder)/'data';old='http://127.0.0.1:17136/spoolman';new='http://127.0.0.1:17137/spoolman'
            identity=prepare_data(data,'0.33.0-alpha.1',old)
            (data/'monitor/account.json').write_text('fixture account hash')
            settings=data/'monitor/spoolman.json'
            state=json.loads(settings.read_text());state['mappings']={'192.168.1.20:0':1};atomic_json(settings,state)
            self.assertEqual(prepare_data(data,'0.33.0-alpha.1',new),identity)
            self.assertEqual(json.loads(settings.read_text())['mappings'],state['mappings'])
            self.assertEqual(json.loads(settings.read_text())['url'],new)
            self.assertEqual((data/'monitor/account.json').read_text(),'fixture account hash')
            state['url']='http://192.168.1.20:7912';atomic_json(settings,state)
            prepare_data(data,'0.33.0-alpha.1',old)
            self.assertEqual(json.loads(settings.read_text())['url'],state['url'])
            with self.assertRaises(ValueError):prepare_data(data,'0.34.0-alpha.1',old)

    def test_existing_foreign_data_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'spoolman.db').write_bytes(b'existing')
            with self.assertRaises(ValueError):prepare_data(path,'0.33.0-alpha.1','http://127.0.0.1:17136/spoolman')
            self.assertEqual((path/'spoolman.db').read_bytes(),b'existing')

    def test_child_environment_drops_inherited_controls_and_public_bindings(self):
        with patch.dict(os.environ,{'KOBRA_LIGHT_CONTROL_IPS':'192.168.1.20',
                 'KOBRA_LISTEN':'0.0.0.0','KOBRA_DATA_DIR':'old','SPOOLMAN_DB_PASSWORD':'private',
                 'DYLD_LIBRARY_PATH':'foreign libraries'}):
            env=child_environment(Path('fixture-data'),Path('fixture-ffmpeg'),
                'http://127.0.0.1:17136/spoolman','a'*64)
        self.assertNotIn('KOBRA_LIGHT_CONTROL_IPS',env)
        self.assertNotIn('SPOOLMAN_DB_PASSWORD',env)
        self.assertNotIn('DYLD_LIBRARY_PATH',env)
        self.assertEqual(env['KOBRA_LISTEN'],'127.0.0.1')
        self.assertEqual(env['SPOOLMAN_DIR_DATA'],str(Path('fixture-data/spoolman')))
        self.assertTrue(env['PATH'].startswith('fixture-ffmpeg'+os.pathsep))

    def test_only_owned_process_handles_are_terminated(self):
        class Process:
            def __init__(self,done=False):self.done=done;self.terminated=False;self.waited=False
            def poll(self):return 0 if self.done else None
            def terminate(self):self.terminated=True;self.done=True
            def wait(self,timeout):self.waited=True
        finished=Process(True);running=Process()
        terminate_owned([finished,running])
        self.assertFalse(finished.terminated);self.assertTrue(running.terminated)
        self.assertTrue(finished.waited and running.waited)

    def test_local_urls_never_accept_external_hosts_or_credentials(self):
        self.assertTrue(local_url('http://127.0.0.1:17135/'))
        self.assertTrue(local_url('http://127.0.0.1:17135/#access=fixture',fragment=True))
        for url in ['http://example.com:17135/','http://localhost:17135/',
                    'http://u:p@127.0.0.1:17135/','http://127.0.0.1:17135/stop','file:///secret']:
            self.assertFalse(local_url(url))


class DesktopControllerHTTPTests(unittest.TestCase):
    def test_authenticated_status_and_explicit_stop_are_bound_to_own_instance(self):
        stop=threading.Event();token='a'*64
        server=create_control_server(token,'fixture-instance','http://127.0.0.1:17135/',stop)
        server_thread=threading.Thread(target=server.serve_forever,daemon=True);server_thread.start()
        url='http://127.0.0.1:'+str(server.server_port)
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(url+'/status')
            self.assertEqual(error.exception.code,401)
            error.exception.close()
            self.assertFalse(stop.is_set())
            with tempfile.TemporaryDirectory() as folder:
                atomic_json(Path(folder)/'instance.json',{'format':FORMAT,'instance':'fixture-instance',
                    'control_url':url,'control_token':token})
                self.assertEqual(controller_request(folder)['monitor_url'],'http://127.0.0.1:17135/')
                self.assertFalse(stop.is_set())
                self.assertTrue(controller_request(folder,'stop')['stopping'])
                self.assertTrue(stop.is_set())
        finally:
            server.shutdown();server.server_close();server_thread.join(timeout=3)
