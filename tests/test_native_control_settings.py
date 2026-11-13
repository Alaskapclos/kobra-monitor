import asyncio,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from native_control_settings import NativeControlSettings,validate,PATH
from suite.desktop import child_environment
from access import Access
from accounts import write_account
from monitor import build_app
from aiohttp.test_utils import make_mocked_request

IP='192.168.254.254'
GRANTS={IP:{'controls':['light','motion','drying'],'drying_limit':55}}

class GrantStoreTests(unittest.TestCase):
    def test_empty_default_and_fresh_process_retains_only_explicit_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=NativeControlSettings(tmp);self.assertEqual(store.read(),{})
            store.write(GRANTS);env=NativeControlSettings(tmp).environment([IP])
            self.assertEqual(env['KOBRA_LIGHT_CONTROL_IPS'],IP)
            self.assertEqual(env['KOBRA_FAN_CONTROL_IPS'],'')
            self.assertEqual(json.loads(env['KOBRA_DRYING_TEMPERATURE_LIMITS']),{IP:55})
            self.assertEqual(NativeControlSettings(tmp).environment([])['KOBRA_LIGHT_CONTROL_IPS'],'')
            if os.name!='nt':self.assertEqual(store.path.stat().st_mode&0o777,0o600)

    def test_invalid_rights_and_addresses_are_rejected(self):
        for value in [{IP:{'controls':['all'],'drying_limit':55}}, {IP:{'controls':['light','light'],'drying_limit':55}},
                      {'127.0.0.1':GRANTS[IP]}, {IP:{'controls':['drying'],'drying_limit':100}},
                      {IP:{'controls':['drying'],'drying_limit':True}}]:
            with self.assertRaises(ValueError):validate(value)

    def test_pruning_removes_permissions_before_readding_printer(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=NativeControlSettings(tmp);store.write(GRANTS);store.prune([])
            self.assertEqual(store.environment([IP])['KOBRA_MOTION_CONTROL_IPS'],'')

    def test_failed_write_keeps_previous_rights(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=NativeControlSettings(tmp);store.write(GRANTS);old=store.path.read_bytes()
            with patch('native_control_settings.os.replace',side_effect=OSError('fixture')):
                with self.assertRaises(OSError):store.write({})
            self.assertEqual(store.path.read_bytes(),old)

    def test_corrupt_and_linked_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=NativeControlSettings(tmp);store.path.write_text('bad')
            with self.assertRaises(ValueError):store.environment([IP])
            store.path.unlink();other=Path(tmp)/'other';other.write_text('{}');store.path.symlink_to(other)
            with self.assertRaises(ValueError):store.read()

    def test_supervisor_enables_only_native_settings_gate_and_strips_external_grants(self):
        with patch.dict(os.environ,{'KOBRA_LIGHT_CONTROL_IPS':IP}):
            env=child_environment(Path('fixture'),Path('ffmpeg'),'http://127.0.0.1:19999/spoolman','fixture-token')
        self.assertNotIn('KOBRA_LIGHT_CONTROL_IPS',env)
        self.assertEqual(env['KOBRA_NATIVE_CONTROL_SETTINGS'],'1')

class GrantHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();write_account(Path(self.tmp.name),'Fixture Owner','A synthetic fixture password only!')
        self.access=Access(self.tmp.name);self.store=NativeControlSettings(self.tmp.name)
        self.fleet=SimpleNamespace(start=AsyncMock(),stop=AsyncMock(),ips=[IP],native_control_settings=self.store,config_lock=asyncio.Lock())
        self.app=build_app(self.fleet,self.access)
        response=await self.call('POST','/api/session',{'username':'Fixture Owner','password':'A synthetic fixture password only!'},{'Content-Type':'application/json','Origin':'http://localhost'})
        self.assertEqual(response.status,200)
        self.headers={'Cookie':'kobra_session='+response.cookies['kobra_session'].value,'X-Kobra-CSRF':json.loads(response.text)['csrf'],'Content-Type':'application/json','Origin':'http://localhost'}

    async def asyncTearDown(self):self.tmp.cleanup()
    async def call(self,method,path,body=None,headers=None):
        request=make_mocked_request(method,path,headers={'Host':'localhost',**(headers or {})});request.json=AsyncMock(return_value=body)
        match=await self.app.router.resolve(request)
        return await self.app.middlewares[0](request,match.handler)
    def body(self):return {'grants':GRANTS,'printer_ips':[IP],'revision':self.store.revision(),'confirmed':True}

    async def test_owner_can_save_and_reopen_without_sending_commands(self):
        response=await self.call('POST',PATH,self.body(),self.headers);self.assertEqual(response.status,200)
        self.assertTrue(json.loads(response.text)['restart_required'])
        response=await self.call('GET',PATH,headers=self.headers);self.assertEqual(json.loads(response.text)['grants'],validate(GRANTS))
        self.fleet.start.assert_not_called();self.fleet.stop.assert_not_called()

    async def test_missing_login_csrf_and_cross_origin_cannot_grant(self):
        for headers,status in [({},401),({k:v for k,v in self.headers.items() if k!='X-Kobra-CSRF'},403),({**self.headers,'Origin':'http://other.invalid'},403)]:
            response=await self.call('POST',PATH,self.body(),headers);self.assertEqual(response.status,status)
        self.assertFalse(self.store.path.exists())

    async def test_confirmation_unknown_printer_and_stale_revision_cannot_grant(self):
        for edit,status in [({'confirmed':False},400),({'revision':'stale'},409),({'printer_ips':[]},409),({'grants':{'192.168.254.253':GRANTS[IP]}},400)]:
            response=await self.call('POST',PATH,{**self.body(),**edit},self.headers);self.assertEqual(response.status,status)
        self.assertFalse(self.store.path.exists())

    async def test_non_native_installation_cannot_enable_permissions(self):
        self.fleet.native_control_settings=None
        response=await self.call('GET',PATH,headers=self.headers);self.assertEqual(json.loads(response.text),{'available':False})
        response=await self.call('POST',PATH,self.body(),self.headers);self.assertEqual(response.status,403)
        self.assertFalse(self.store.path.exists())
