import asyncio,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from aiohttp import web
from aiohttp.test_utils import TestClient,TestServer,make_mocked_request
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import test_setup_access as fixtures
from monitor import build_app
from spoolman_view import safe_path,allowed_browser_write
from spools import local_url

class GatewayPaths(unittest.TestCase):
    def test_fixed_prefix_and_native_base_path(self):
        self.assertEqual(local_url('http://127.0.0.1:7912/spoolman'),'http://127.0.0.1:7912/spoolman')
        for p in ['/spoolman/','/spoolman/api/v1/spool?limit=5','/spoolman/_app/main.js']:
            self.assertTrue(safe_path(p))
        for p in ['/spoolman-other/','/spoolman/../api/status','/spoolman/%2e%2e/api','/spoolman/%252e%252e/api','/spoolman/x%5cy','//evil.invalid/']:
            self.assertFalse(safe_path(p),p)
    def test_writes_need_explicit_matching_origin(self):
        for headers in [{},{'Origin':'https://evil.invalid'},{'Origin':'http://localhost','Sec-Fetch-Site':'cross-site'}]:
            self.assertFalse(allowed_browser_write(make_mocked_request('POST','/spoolman/api/v1/spool',headers={'Host':'localhost',**headers})))
        self.assertTrue(allowed_browser_write(make_mocked_request('PATCH','/spoolman/api/v1/spool/1',headers={'Host':'localhost','Origin':'https://localhost'})))

class GatewayIntegration(unittest.IsolatedAsyncioTestCase):
    call=fixtures.AccessTests.call
    signin=fixtures.AccessTests.signin
    async def asyncSetUp(self):
        await fixtures.AccessTests.asyncSetUp(self)
        self.seen=[]
        async def upstream(request):
            self.seen.append((request.method,request.path,dict(request.headers),await request.read()))
            if request.path.endswith('/outside'):return web.Response(status=302,headers={'Location':'https://evil.invalid/'})
            if request.path.endswith('/inside'):return web.Response(status=307,headers={'Location':'/spoolman/filament'})
            if request.path.endswith('/ws'):
                socket=web.WebSocketResponse();await socket.prepare(request)
                async for m in socket:await socket.send_str('reply:'+m.data)
                return socket
            return web.Response(text='native',headers={'Content-Type':'text/html','Set-Cookie':'secret=upstream','X-Total-Count':'2'})
        app=web.Application();app.router.add_route('*','/{path:.*}',upstream)
        self.upstream=TestServer(app);await self.upstream.start_server()
        self.service.spools=SimpleNamespace(url=str(self.upstream.make_url('/spoolman')))
        self.client=TestClient(TestServer(self.app));await self.client.start_server()
        self.headers={'Host':'localhost',**await self.signin()}
    async def asyncTearDown(self):
        await self.client.close();await self.upstream.close();await fixtures.AccessTests.asyncTearDown(self)
    async def test_original_content_protected_and_credentials_not_forwarded(self):
        self.assertEqual((await self.client.get('/spoolman/')).status,401)
        response=await self.client.get('/spoolman/',headers={**self.headers,'Authorization':'private'})
        self.assertEqual(await response.text(),'native');self.assertNotIn('Set-Cookie',response.headers)
        self.assertEqual(response.headers['X-Total-Count'],'2')
        self.assertIn("frame-ancestors 'self'",response.headers['Content-Security-Policy'])
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertNotIn('Cookie',self.seen[-1][2]);self.assertNotIn('Authorization',self.seen[-1][2])
    async def test_native_api_writes_require_owner_and_matching_origin(self):
        for method in ['POST','PUT','PATCH','DELETE']:
            for h in [{}, {'Host':'localhost','Cookie':self.headers['Cookie']}, {**self.headers,'Origin':'https://evil.invalid'}]:
                r=await self.client.request(method,'/spoolman/api/v1/spool/1',headers=h,data=b'{}')
                self.assertIn(r.status,[401,403])
            r=await self.client.request(method,'/spoolman/api/v1/spool/1',headers=self.headers,data=b'{}')
            self.assertEqual(r.status,200)
            self.assertEqual(self.seen[-1][3],b'{}')
            self.assertEqual(self.seen[-1][2]['Origin'],str(self.upstream.make_url('')).rstrip('/'))
        self.assertEqual((await self.client.post('/spoolman/config.js',headers=self.headers)).status,403)
        self.assertEqual((await self.client.post('/api/print',headers=self.headers)).status,403)
    async def test_redirects_and_unconfigured_gateway_are_bounded(self):
        r=await self.client.get('/spoolman/outside',headers=self.headers);self.assertEqual(r.status,502)
        r=await self.client.get('/spoolman/inside',headers=self.headers,allow_redirects=False)
        self.assertEqual(r.status,307);self.assertEqual(r.headers['Location'],'/spoolman/filament')
        self.service.spools.url=str(self.upstream.make_url('')).rstrip('/')
        self.assertEqual((await self.client.get('/spoolman/',headers=self.headers)).status,503)
    async def test_original_websocket_and_session_expiry(self):
        async with self.client.ws_connect('/spoolman/api/v1/ws',headers=self.headers) as socket:
            await socket.send_str('stock');self.assertEqual((await socket.receive(timeout=2)).data,'reply:stock')
        self.access.sessions.clear()
        self.assertEqual((await self.client.get('/spoolman/api/v1/spool',headers=self.headers)).status,401)
