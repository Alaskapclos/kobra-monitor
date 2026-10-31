import asyncio,json,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from camera_view import CameraViews
from access import Access
from accounts import write_account
from monitor import build_app
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

class Reader:
    def __init__(self):
        self.latest_jpeg=b'\xff\xd8fixture\xff\xd9';self.latest_jpeg_ts=time.time();self._task_jpeg=None;self.starts=0;self.stopped=False
    async def _run_jpeg_loop(self):
        self.starts+=1
        try:await asyncio.Event().wait()
        finally:self.stopped=True

class CameraViewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now=100;self.views=CameraViews(clock=lambda:self.now)
        self.views.available=lambda:True;self.views._reader=lambda ip:Reader()
    async def asyncTearDown(self):await self.views.stop(None)
    async def test_only_configured_printers_can_be_read(self):
        for ip in ('','http://evil.invalid','192.168.1.99'):
            self.assertEqual((await self.views.frame(ip,['192.168.1.20'])).status,400)
        self.assertFalse(self.views.readers)
    async def test_clients_share_one_decoder_and_idle_reader_is_reaped(self):
        configured=['192.168.1.20'];a,b=await asyncio.gather(self.views.frame(configured[0],configured),self.views.frame(configured[0],configured))
        self.assertEqual(a.status,200);self.assertEqual(b.body,a.body);self.assertEqual(a.headers['Cache-Control'],'no-store')
        reader=self.views.readers[configured[0]];await asyncio.sleep(0);self.assertEqual(reader.starts,1)
        self.now+=16;await self.views.prune();self.assertTrue(reader.stopped);self.assertFalse(self.views.readers)
    async def test_stale_image_is_never_reported_as_live(self):
        reader=Reader();reader.latest_jpeg_ts=time.time()-11;self.views._reader=lambda ip:reader
        self.assertEqual((await self.views.frame('192.168.1.20',['192.168.1.20'])).status,503)
    async def test_limit_and_removed_printer_cleanup(self):
        ips=['192.168.1.20','192.168.1.21','192.168.1.22']
        for ip in ips[:2]:self.assertEqual((await self.views.frame(ip,ips)).status,200)
        self.assertEqual((await self.views.frame(ips[2],ips)).status,503)
        await self.views.prune(ips[1:]);self.assertNotIn(ips[0],self.views.readers)
        self.assertEqual((await self.views.frame(ips[2],ips[1:])).status,200)
    async def test_missing_decoder_returns_actionable_error(self):
        self.views.available=lambda:False
        response=await self.views.frame('192.168.1.20',['192.168.1.20'])
        self.assertEqual(response.status,503);self.assertIn('FFmpeg',response.text);self.assertFalse(self.views.readers)
    async def test_reader_is_fixed_to_stock_stream_and_disallows_redirects(self):
        reader=CameraViews()._reader('192.168.1.20')
        self.assertEqual(reader._url,'http://192.168.1.20:18088/flv')
        args=reader._input_args(reader._url)
        self.assertEqual(args[args.index('-max_redirects')+1],'0')
        self.assertEqual(args[args.index('-protocol_whitelist')+1],'http,tcp')
        self.assertEqual(args[args.index('-f')+1],'flv')

class CameraAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_camera_requires_owner_session_and_cannot_be_started_by_post(self):
        with tempfile.TemporaryDirectory() as directory:
            write_account(directory,'Fixture','Camera fixture passphrase!');access=Access(directory)
            cameras=SimpleNamespace(frame=AsyncMock(return_value=web.Response(body=b'jpeg',content_type='image/jpeg')),start=AsyncMock(),stop=AsyncMock())
            service=SimpleNamespace(cameras=cameras,start=AsyncMock(),stop=AsyncMock(),ips=['192.168.1.20'])
            app=build_app(service,access)
            async def call(method,path,headers=None,body=None):
                request=make_mocked_request(method,path,headers={'Host':'localhost','Content-Type':'application/json',**(headers or {})});request.json=AsyncMock(return_value=body)
                match=await app.router.resolve(request);return await app.middlewares[0](request,match.handler)
            self.assertEqual((await call('GET','/api/camera/frame?ip=192.168.1.20')).status,401);cameras.frame.assert_not_awaited()
            login=await call('POST','/api/session',{'Origin':'https://localhost'},{'username':'Fixture','password':'Camera fixture passphrase!'})
            self.assertTrue(login.cookies['kobra_session']['secure'])
            headers={'Cookie':'kobra_session='+login.cookies['kobra_session'].value}
            self.assertEqual((await call('GET','/api/camera/frame?ip=192.168.1.20',headers)).status,200)
            cameras.frame.assert_awaited_once_with('192.168.1.20',['192.168.1.20'])
            for path in ('/api/camera/start','/api/camera/stop','/api/camera/frame','/printer/print/start'):
                self.assertEqual((await call('POST',path,headers)).status,403)
