import asyncio,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from spools import Spools,local_url,normalize
import test_setup_access as fixtures

IP='192.168.1.20'
SPOOLS=[{'id':42,'remaining_weight':0,'filament':{'name':'Test','material':'PETG','vendor':{'name':'Hersteller'}}}]

class SpoolValidation(unittest.TestCase):
    def test_addresses_are_explicit_local_targets_without_credentials_or_paths(self):
        for value in ['http://192.168.1.20:7912','https://10.0.0.2','http://spoolman:8000','http://127.0.0.1:8000','']:
            self.assertEqual(local_url(value),value)
        for value in ['http://example.org','http://8.8.8.8','http://169.254.169.254','http://[::1]','file:///etc/passwd','http://u:p@192.168.1.2','http://192.168.1.2/api','http://192.168.1.2?key=x','http://192.168.1.2#x','http://192.168.1.2:99999',None]:
            with self.subTest(value=value),self.assertRaises(ValueError):local_url(value)
    def test_zero_weight_and_missing_weight_are_distinct_and_private_fields_dropped(self):
        items=normalize(SPOOLS+[{'id':43,'comment':'private','remaining_weight':float('nan'),'filament':{}},{'id':44,'archived':True}])
        self.assertEqual(items[0]['remaining_weight'],0);self.assertIsNone(items[1]['remaining_weight']);self.assertNotIn('comment',items[1]);self.assertEqual(len(items),2)
    def test_malformed_inventory_and_duplicate_ids_rejected(self):
        for value in [{},[None],[{'id':True}],[{'id':1,'filament':[]}],SPOOLS+SPOOLS]:
            with self.subTest(value=value),self.assertRaises(ValueError):normalize(value)
    def test_bad_mappings_and_one_spool_in_two_slots_rejected(self):
        for value in [{IP:{'0':True}},{IP:{'16':42}},{IP:{'0':42,'1':42}},{'8.8.8.8':{'0':42}}]:
            with self.subTest(value=value),self.assertRaises(ValueError):Spools.validate_mappings(value)

class SpoolService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.now=1000;self.s=Spools(self.tmp.name,clock=lambda:self.now)
        self.s.url='http://127.0.0.1:8000';self.s.items=normalize(SPOOLS);self.s.checked=self.now
    async def asyncTearDown(self):self.tmp.cleanup()
    async def test_assignment_persists_privately_and_loads_without_request(self):
        await self.s.assign(IP,0,42,[IP],{0})
        loaded=Spools(self.tmp.name);self.assertEqual(loaded.mappings,{IP:{'0':42}});self.assertIsNone(loaded.items)
        if os.name!='nt':self.assertEqual(self.s.path.stat().st_mode&0o777,0o600)
    async def test_invalid_target_stale_and_unknown_spool_rejected(self):
        for args in [(IP,0,99,[IP],{0}),(IP,1,42,[IP],{0}),(IP,True,42,[IP],{0}),('192.168.1.99',0,42,[IP],{0})]:
            with self.assertRaises(ValueError):await self.s.assign(*args)
        self.now+=61
        with self.assertRaises(ValueError):await self.s.assign(IP,0,42,[IP],{0})
    async def test_duplicate_assignment_rejected_but_clearing_offline_is_allowed(self):
        await self.s.assign(IP,0,42,[IP],{0})
        with self.assertRaises(ValueError):await self.s.assign(IP,1,42,[IP],{1})
        self.s.error='offline';await self.s.assign(IP,0,None,[IP],{0});self.assertEqual(self.s.mappings[IP],{})
    async def test_server_switch_cannot_rebind_existing_ids(self):
        await self.s.assign(IP,0,42,[IP],{0})
        with self.assertRaises(ValueError):await self.s.configure('http://192.168.1.50:7912')
        self.assertEqual(self.s.url,'http://127.0.0.1:8000')
    async def test_failed_save_rolls_back_memory(self):
        with patch.object(self.s,'save',side_effect=OSError()):
            with self.assertRaises(ValueError):await self.s.assign(IP,0,42,[IP],{0})
        self.assertEqual(self.s.mappings,{})
    async def test_refresh_uses_only_fixed_get_no_redirect_and_preserves_stale_data(self):
        class Content:
            async def iter_chunked(self,n):yield json.dumps(SPOOLS).encode()
        response=SimpleNamespace(status=200,content=Content())
        context=AsyncMock();context.__aenter__.return_value=response
        client=SimpleNamespace(get=lambda *a,**kw:context)
        factory=AsyncMock();factory.__aenter__.return_value=client
        calls=[]
        def get(*a,**kw):calls.append((a,kw));return context
        client.get=get
        with patch('spools.aiohttp.ClientSession',return_value=factory):
            self.assertTrue((await self.s.refresh())['inventory_current']);response.status=302
            result=await self.s.refresh();self.assertFalse(result['inventory_current']);self.assertEqual(len(result['spools']),1)
        self.assertTrue(all(a==('http://127.0.0.1:8000/api/v1/spool',) and kw['allow_redirects'] is False for a,kw in calls))

class SpoolAccess(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AccessTests.asyncSetUp
    asyncTearDown = fixtures.AccessTests.asyncTearDown
    call = fixtures.AccessTests.call
    signin = fixtures.AccessTests.signin
    async def test_spool_api_requires_account_csrf_origin_and_never_proxies_writes(self):
        self.service.spools=Spools(self.tmp.name)
        self.assertEqual((await self.call('GET','/api/spools')).status,401)
        h=await self.signin()
        self.assertEqual((await self.call('GET','/api/spools',headers=h)).status,200)
        self.assertEqual((await self.call('POST','/api/spools',{'action':'refresh'},h)).status,200)
        no=dict(h);no.pop('X-Kobra-CSRF')
        self.assertEqual((await self.call('POST','/api/spools',{'action':'refresh'},no)).status,403)
        bad=dict(h);bad['Origin']='https://evil.invalid'
        self.assertEqual((await self.call('POST','/api/spools',{'action':'refresh'},bad)).status,403)
        for action in ['consume','delete','measure','print','upload']:
            self.assertEqual((await self.call('POST','/api/spools',{'action':action},h)).status,400)
        self.assertEqual((await self.call('PATCH','/api/spools',{},h)).status,403)
