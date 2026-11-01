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


def printer(sku='TEST-UNIQUE-0001',slot=0,age=0,connection='online',empty=False,ip=IP):
    return {'ip':ip,'connection':connection,'section_age_s':{'ace':age},'data':{'ace_slots':[
        {'global_index':slot,'sku':sku,'edit_status':2 if empty else 0}]}}

class IdentityService(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = SpoolService.asyncSetUp
    asyncTearDown = SpoolService.asyncTearDown
    async def test_identity_link_blocks_fixed_assignment_and_preserves_move_recognition(self):
        await self.s.link_sku('TEST-UNIQUE-0001',42,[printer()])
        for slot in (0,3):
            with self.assertRaisesRegex(ValueError,'folgt bereits ihrer Kennung'):
                await self.s.assign(IP,slot,42,[IP],{slot})
        self.assertEqual(self.s.mappings,{})
        self.assertEqual(self.s.detections([printer(slot=3)])[0]['spool_id'],42)
        # Old conflicting configurations can still be repaired without inventory access.
        self.s.mappings={IP:{'0':42}};self.s.error='offline'
        await self.s.assign(IP,0,None,[IP],{0})
        self.assertEqual(self.s.sku_links,{'TEST-UNIQUE-0001':42})
        self.s.error=''
        self.assertEqual(self.s.detections([printer(slot=3)])[0]['status'],'recognized')
        await self.s.link_sku('TEST-UNIQUE-0001',None,[])
        await self.s.assign(IP,3,42,[IP],{3})
        self.assertEqual(self.s.mappings[IP],{'3':42})
    async def test_link_follows_spool_between_slots_and_survives_restart(self):
        await self.s.assign(IP,0,42,[IP],{0})
        await self.s.link_sku('TEST-UNIQUE-0001',42,[printer()])
        self.assertEqual(self.s.mappings[IP],{})
        restored=Spools(self.tmp.name,clock=lambda:self.now)
        self.assertEqual(restored.sku_links,{'TEST-UNIQUE-0001':42})
        self.assertEqual(restored.detections([printer(slot=2)])[0]['status'],'inventory_unavailable')
        restored.items=self.s.items;restored.checked=self.now
        found=restored.detections([printer(slot=2)])[0]
        self.assertEqual((found['slot'],found['spool_id'],found['status']),(2,42,'recognized'))
    async def test_duplicate_stale_offline_empty_and_invalid_skus_never_bind(self):
        for values in [[printer(),printer(slot=1)],[printer(age=61)],[printer(connection='offline')],[printer(empty=True)],[printer(sku='')]]:
            with self.subTest(values=values),self.assertRaises(ValueError):await self.s.link_sku('TEST-UNIQUE-0001',42,values)
        for sku in ['',None,'x'*97,'<script>','a\nb']:
            with self.assertRaises(ValueError):await self.s.link_sku(sku,42,[printer(sku=sku)])
    async def test_observed_duplicates_and_inventory_expiry_disable_recognition(self):
        await self.s.link_sku('TEST-UNIQUE-0001',42,[printer()])
        self.assertEqual([r['status'] for r in self.s.detections([printer(),printer(slot=1)])],['duplicate','duplicate'])
        self.assertEqual(self.s.detections([printer(empty=True)])[0]['status'],'empty')
        self.now+=61
        self.assertEqual(self.s.detections([printer()])[0]['status'],'inventory_unavailable')
        await self.s.link_sku('TEST-UNIQUE-0001',None,[])
        self.assertFalse(self.s.sku_links)
    async def test_server_switch_conflict_rebind_and_save_failure_are_safe(self):
        await self.s.link_sku('TEST-UNIQUE-0001',42,[printer()])
        with self.assertRaises(ValueError):await self.s.configure('http://192.168.1.50:7912')
        with self.assertRaises(ValueError):await self.s.link_sku('OTHER-0001',42,[printer(sku='OTHER-0001')])
        with patch.object(self.s,'save',side_effect=OSError()):
            with self.assertRaises(ValueError):await self.s.link_sku('TEST-UNIQUE-0001',None,[])
        self.assertEqual(self.s.sku_links,{'TEST-UNIQUE-0001':42})
        self.s.mappings={IP:{'2':42}}
        self.assertEqual(self.s.detections([printer()])[0]['status'],'conflict')
    async def test_unknown_product_sku_never_auto_creates_inventory_or_links(self):
        self.assertEqual(self.s.detections([printer(sku='PRODUCT-001')])[0]['status'],'unknown')
        self.assertEqual(self.s.sku_links,{})
        self.assertFalse(self.s.path.exists())

class IdentityAccess(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.AccessTests.asyncSetUp
    asyncTearDown = fixtures.AccessTests.asyncTearDown
    call = fixtures.AccessTests.call
    signin = fixtures.AccessTests.signin
    async def test_link_requires_explicit_identity_confirmation_and_live_report(self):
        self.service.spools=Spools(self.tmp.name)
        self.service.spools.url='http://127.0.0.1:8000'
        self.service.spools.items=normalize(SPOOLS);self.service.spools.checked=self.service.spools.clock()
        self.service.ips=[IP]
        self.service.monitors={IP:SimpleNamespace(telemetry=SimpleNamespace(snapshot=lambda:printer()))}
        headers=await self.signin()
        body={'action':'link_sku','ip':IP,'slot':0,'sku':'TEST-UNIQUE-0001','spool_id':42}
        self.assertEqual((await self.call('POST','/api/spools',body,headers)).status,400)
        body['unique_confirmed']=True
        body['slot']=1
        self.assertEqual((await self.call('POST','/api/spools',body,headers)).status,400)
        body['slot']=0
        response=await self.call('POST','/api/spools',body,headers)
        self.assertEqual(response.status,200)
        self.assertEqual(json.loads(response.text)['detections'][0]['status'],'recognized')
        self.service.monitors={}
        body['spool_id']=None
        self.assertEqual((await self.call('POST','/api/spools',body,headers)).status,200)
