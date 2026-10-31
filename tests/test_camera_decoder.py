"""Real decoder smoke test against a local synthetic FLV, never a printer."""
import asyncio,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent.parent),str(Path(__file__).resolve().parent.parent/"vendor/kobra-bridge")]
from aiohttp import web
from camera_view import CameraViews

@unittest.skipUnless(CameraViews().available(),'Optional FFmpeg with redirect protection is unavailable on this runner')
class DecoderTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_flv_becomes_fresh_jpeg_and_worker_exits(self):
        producer=await asyncio.create_subprocess_exec('ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=green:s=128x96:r=12','-t','15','-an','-c:v','flv1','-f','flv','pipe:1',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        flv,errors=await producer.communicate();self.assertEqual(producer.returncode,0,errors.decode())
        calls=[]
        async def source(request):
            calls.append(request.method);response=web.StreamResponse(headers={'Content-Type':'video/x-flv'});await response.prepare(request)
            try:
                for offset in range(0,len(flv),256):
                    await response.write(flv[offset:offset+256]);await asyncio.sleep(.06)
            except (ConnectionResetError,asyncio.CancelledError):pass
            return response
        app=web.Application();app.router.add_get('/flv',source);runner=web.AppRunner(app);await runner.setup()
        site=web.TCPSite(runner,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1]
        views=CameraViews();create=views._reader
        def fixture_reader(ip):
            reader=create(ip);reader.set_url(f'http://127.0.0.1:{port}/flv');return reader
        views._reader=fixture_reader
        try:
            response=await views.frame('192.168.1.20',['192.168.1.20'])
            self.assertEqual(response.status,200,response.text if response.status!=200 else '')
            self.assertTrue(response.body.startswith(b'\xff\xd8'));self.assertTrue(response.body.endswith(b'\xff\xd9'))
            task=views.readers['192.168.1.20']._task_jpeg
            await views.stop(None);self.assertTrue(task.done());self.assertTrue(calls);self.assertEqual(set(calls),{'GET'})
        finally:await views.stop(None);await runner.cleanup()
    async def test_http_redirect_cannot_send_decoder_to_other_target(self):
        followed=[]
        async def redirect(request):raise web.HTTPFound('/forbidden')
        async def forbidden(request):followed.append(True);return web.Response(body=b'not a video')
        app=web.Application();app.router.add_get('/flv',redirect);app.router.add_get('/forbidden',forbidden)
        runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1]
        views=CameraViews();create=views._reader
        def fixture_reader(ip):
            reader=create(ip);reader.set_url(f'http://127.0.0.1:{port}/flv');return reader
        views._reader=fixture_reader
        try:
            response=await views.frame('192.168.1.20',['192.168.1.20'])
            self.assertEqual(response.status,503);self.assertFalse(followed)
        finally:await views.stop(None);await runner.cleanup()
