import json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from access import Access
from configuration import printer_ips,save_config,load_config
from monitor import build_app,Fleet,Monitor
from bootstrap import ensure_runtime
from aiohttp.test_utils import make_mocked_request

class ConfigurationTests(unittest.TestCase):
    def test_only_private_ipv4_addresses_are_allowed_and_duplicates_removed(self):
        self.assertEqual(printer_ips(['192.168.1.10','192.168.1.10']),['192.168.1.10'])
        for value in ([],['127.0.0.1'],['8.8.8.8'],['::1'],['169.254.1.2'],['bad']):
            with self.assertRaises(ValueError):printer_ips(value)
    def test_installation_starts_unconfigured_and_persists_config_privately(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_config(tmp),[])
            save_config(tmp,['192.168.1.10'])
            self.assertEqual(load_config(tmp),['192.168.1.10'])
            if os.name!='nt':self.assertEqual((Path(tmp)/'config.json').stat().st_mode&0o777,0o600)
    def test_broken_config_does_not_silently_connect_to_other_devices(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'config.json').write_text('invalid')
            with self.assertRaises(ValueError):load_config(tmp)

class InstallerTests(unittest.TestCase):
    def test_changed_lock_installs_versions_but_unchanged_lock_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);py=root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python');py.parent.mkdir(parents=True);py.touch()
            lock=root/'requirements-lock.txt';lock.write_text('first')
            with patch('bootstrap.subprocess.check_call') as install:
                ensure_runtime(root);ensure_runtime(root);self.assertEqual(install.call_count,1)
                lock.write_text('second');ensure_runtime(root);self.assertEqual(install.call_count,2)
    def test_failed_install_does_not_mark_lock_as_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);py=root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python');py.parent.mkdir(parents=True);py.touch()
            (root/'requirements-lock.txt').write_text('first')
            with patch('bootstrap.subprocess.check_call',side_effect=OSError('fixture')):
                with self.assertRaises(OSError):ensure_runtime(root)
            self.assertFalse((root/'.venv/installed-lock.sha256').exists())

class AccessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.now=1000
        self.access=Access(self.tmp.name,clock=lambda:self.now)
        self.service=SimpleNamespace(start=AsyncMock(),stop=AsyncMock(),configure=AsyncMock(),ip=None)
        self.app=build_app(self.service,self.access)
    async def asyncTearDown(self):self.tmp.cleanup()
    async def call(self,method,path,body=None,headers=None):
        request=make_mocked_request(method,path,headers={'Host':'localhost',**(headers or {})})
        request.json=AsyncMock(return_value=body)
        match=await self.app.router.resolve(request)
        return await self.app.middlewares[0](request,match.handler)
    async def signin(self):
        result=await self.call('POST','/api/session',{'code':self.access.token},{'Content-Type':'application/json','Origin':'http://localhost'})
        self.assertEqual(result.status,200)
        self.assertTrue(result.cookies['kobra_session']['httponly'])
        self.assertEqual(result.cookies['kobra_session']['samesite'],'Strict')
        return {'Cookie':'kobra_session='+result.cookies['kobra_session'].value,'X-Kobra-CSRF':json.loads(result.text)['csrf'],'Content-Type':'application/json','Origin':'http://localhost'}
    async def test_unauthenticated_browser_cannot_read_status_or_configure(self):
        self.assertEqual((await self.call('GET','/api/status')).status,401)
        self.assertEqual((await self.call('POST','/api/setup',{'printer_ips':['192.168.1.10']})).status,401)
        self.service.configure.assert_not_awaited()
    async def test_session_cookie_is_private_and_valid_session_can_configure(self):
        headers=await self.signin()
        r=await self.call('POST','/api/setup',{'printer_ips':['192.168.1.10']},headers)
        self.assertEqual(r.status,200);self.service.configure.assert_awaited_once_with(['192.168.1.10'])
        session=await self.call('GET','/api/session',headers=headers)
        self.assertTrue(json.loads(session.text)['authenticated'])
    async def test_cross_origin_and_missing_csrf_setup_are_rejected(self):
        headers=await self.signin();headers['Origin']='https://evil.invalid'
        self.assertEqual((await self.call('POST','/api/setup',{},headers)).status,403)
        headers['Origin']='http://localhost';headers.pop('X-Kobra-CSRF')
        self.assertEqual((await self.call('POST','/api/setup',{},headers)).status,403)
        self.service.configure.assert_not_awaited()
    async def test_https_proxy_login_sets_secure_cookie(self):
        result=await self.call('POST','/api/session',{'code':self.access.token},{'Content-Type':'application/json','Origin':'https://localhost'})
        self.assertEqual(result.status,200)
        self.assertTrue(result.cookies['kobra_session']['secure'])
    async def test_expired_session_is_not_authorized(self):
        headers=await self.signin();self.now+=43201
        self.assertEqual((await self.call('GET','/api/status',headers=headers)).status,401)
    async def test_login_is_throttled_after_five_bad_codes(self):
        for _ in range(5):self.assertEqual((await self.call('POST','/api/session',{'code':'ä'},{'Content-Type':'application/json'})).status,401)
        self.assertEqual((await self.call('POST','/api/session',{'code':self.access.token},{'Content-Type':'application/json'})).status,429)
        self.now+=61;await self.signin()
    async def test_even_authenticated_browser_cannot_send_printer_commands(self):
        headers=await self.signin()
        for path in ('/printer/print/start','/printer/print/pause','/api/temperature','/api/upload'):
            self.assertEqual((await self.call('POST',path,{},headers)).status,403)
    async def test_malformed_origin_and_cross_site_login_are_rejected(self):
        for origin in ('https://evil.invalid','http://['):
            r=await self.call('POST','/api/session',{'code':self.access.token},{'Content-Type':'application/json','Origin':origin})
            self.assertEqual(r.status,403)
    async def test_persistent_access_code_is_not_changed_on_restart(self):
        self.assertEqual(Access(self.tmp.name).token,self.access.token)

class SetupFleetTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_fleet_and_reconfiguration_preserve_existing_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            fleet=Fleet([],tmp,str(Path(tmp)/'data'))
            self.assertFalse(fleet.snapshot()['configured'])
            with patch.object(Monitor,'start',new=AsyncMock()),patch.object(Monitor,'stop',new=AsyncMock()):
                await fleet.configure(['192.168.1.10']);first=fleet.monitors['192.168.1.10']
                await fleet.configure(['192.168.1.10','192.168.1.11'])
                self.assertIs(fleet.monitors['192.168.1.10'],first)
                self.assertEqual(load_config(Path(tmp)/'data'),['192.168.1.10','192.168.1.11'])
            fleet.history.close()

if __name__=='__main__':unittest.main()
