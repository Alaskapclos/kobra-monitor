import json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from accounts import read_account,write_account,matches
from access import Access
from monitor import build_app
from aiohttp.test_utils import make_mocked_request

SECRET='Mein langes Passwort für Tests!'
class AccountTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.now=1000
        self.access=Access(self.tmp.name,clock=lambda:self.now)
        self.service=SimpleNamespace(start=AsyncMock(),stop=AsyncMock(),configure=AsyncMock(),ip=None)
        self.app=build_app(self.service,self.access)
    async def asyncTearDown(self):self.tmp.cleanup()
    async def call(self,path,body=None,headers=None,method='POST'):
        req=make_mocked_request(method,path,headers={'Host':'localhost','Origin':'http://localhost','Content-Type':'application/json',**(headers or {})})
        req.json=AsyncMock(return_value=body)
        match=await self.app.router.resolve(req)
        return await self.app.middlewares[0](req,match.handler)
    def headers(self,result):
        return {'Cookie':'kobra_session='+result.cookies['kobra_session'].value,'X-Kobra-CSRF':json.loads(result.text)['csrf']}
    async def bootstrap(self):
        response=await self.call('/api/session',{'code':self.access.token});self.assertEqual(response.status,200)
        return self.headers(response)
    async def create(self):
        headers=await self.bootstrap()
        response=await self.call('/api/account',{'username':'Mein Benutzer','password':SECRET,'password_confirmation':SECRET},headers)
        self.assertEqual(response.status,200);return self.headers(response)
    async def signin(self,name='Mein Benutzer',secret=SECRET):return await self.call('/api/session',{'username':name,'password':secret})
    async def test_account_creation_requires_trusted_setup_session_and_csrf(self):
        body={'username':'Test','password':SECRET,'password_confirmation':SECRET}
        self.assertEqual((await self.call('/api/account',body)).status,401)
        headers=await self.bootstrap();headers.pop('X-Kobra-CSRF')
        self.assertEqual((await self.call('/api/account',body,headers)).status,403)
        self.assertIsNone(read_account(self.tmp.name))
    async def test_bootstrap_cannot_read_printer_data_or_change_printers_before_account(self):
        headers=await self.bootstrap()
        self.assertEqual((await self.call('/api/status',headers=headers,method='GET')).status,403)
        self.assertEqual((await self.call('/api/setup',{'printer_ips':['192.168.1.1']},headers)).status,403)
        self.service.configure.assert_not_awaited()
    async def test_password_is_hashed_salted_private_and_survives_restart(self):
        await self.create();p=Path(self.tmp.name)/'account.json';data=p.read_text()
        self.assertNotIn(SECRET,data);a=read_account(self.tmp.name)
        self.assertTrue(matches(a,'mein benutzer',SECRET));self.assertIsNotNone(Access(self.tmp.name).account)
        other=Path(self.tmp.name)/'other';other.mkdir();b=write_account(other,'Mein Benutzer',SECRET)
        self.assertNotEqual(a['salt'],b['salt']);self.assertNotEqual(a['password_hash'],b['password_hash'])
        if os.name!='nt':self.assertEqual(p.stat().st_mode&0o777,0o600)
    async def test_old_code_is_disabled_after_migration(self):
        await self.create()
        self.assertEqual((await self.call('/api/session',{'code':self.access.token})).status,401)
        self.assertEqual((await self.signin()).status,200)
    async def test_validation_unicode_and_password_confirmation(self):
        headers=await self.bootstrap()
        for name,secret,confirm in [('xy',SECRET,SECRET),('Test','short','short'),('Test',SECRET,SECRET+'x'),('Test','a'*129,'a'*129)]:
            r=await self.call('/api/account',{'username':name,'password':secret,'password_confirmation':confirm},headers)
            self.assertEqual(r.status,400)
        r=await self.call('/api/account',{'username':'Jürgen','password':SECRET,'password_confirmation':SECRET},headers)
        self.assertEqual(r.status,200);self.assertEqual((await self.signin('JÜRGEN')).status,200)
    async def test_incorrect_login_is_generic_and_rate_limited(self):
        await self.create()
        unknown=await self.signin('unknown');wrong=await self.signin(secret='wrong')
        self.assertEqual(unknown.text,wrong.text)
        for _ in range(3):self.assertEqual((await self.signin(secret='wrong')).status,401)
        self.assertEqual((await self.signin()).status,429);self.now+=61
        self.assertEqual((await self.signin()).status,200)
    async def test_password_change_requires_old_password_and_revokes_other_sessions(self):
        headers=await self.create();other=self.headers(await self.signin())
        body={'username':'Neu','password':SECRET+'neu','password_confirmation':SECRET+'neu'}
        self.assertEqual((await self.call('/api/account',body,headers)).status,401)
        body['current_password']=SECRET
        result=await self.call('/api/account',body,headers);self.assertEqual(result.status,200)
        self.assertEqual((await self.call('/api/session',headers=other,method='GET')).status,200)
        self.assertFalse(json.loads((await self.call('/api/session',headers=other,method='GET')).text)['authenticated'])
        self.assertEqual((await self.signin()).status,401)
        self.assertEqual((await self.signin('Neu',SECRET+'neu')).status,200)
    async def test_logout_revokes_cookie_and_requires_csrf(self):
        headers=await self.create();missing=dict(headers);missing.pop('X-Kobra-CSRF')
        self.assertEqual((await self.call('/api/logout',headers=missing)).status,403)
        self.assertEqual((await self.call('/api/logout',headers=headers)).status,200)
        self.assertFalse(json.loads((await self.call('/api/session',headers=headers,method='GET')).text)['authenticated'])
    async def test_cross_site_account_write_is_rejected(self):
        headers=await self.bootstrap();headers['Origin']='https://evil.invalid'
        r=await self.call('/api/account',{'username':'Test','password':SECRET,'password_confirmation':SECRET},headers)
        self.assertEqual(r.status,403)
    async def test_corrupt_account_fails_closed_instead_of_enabling_code_login(self):
        await self.create();(Path(self.tmp.name)/'account.json').write_text('{}')
        with self.assertRaises(ValueError):Access(self.tmp.name)
    async def test_session_endpoint_never_returns_hash_salt_or_password(self):
        headers=await self.create();r=await self.call('/api/session',headers=headers,method='GET');s=json.loads(r.text)
        self.assertEqual(s['username'],'Mein Benutzer')
        self.assertNotIn('password_hash',s);self.assertNotIn('salt',s);self.assertNotIn(SECRET,r.text)
    async def test_account_login_still_cannot_control_printers(self):
        headers=await self.create()
        for path in ['/api/upload','/printer/print/start','/api/temperature']:
            self.assertEqual((await self.call(path,{},headers)).status,403)

if __name__=='__main__':unittest.main()
