import subprocess,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from types import SimpleNamespace
from unittest.mock import patch
from camera_view import DecoderAvailability

class DecoderAvailabilityTests(unittest.TestCase):
    def setUp(self):self.now=100;self.probe=DecoderAvailability(clock=lambda:self.now)
    def test_timeout_is_retried_and_recovers_without_service_restart(self):
        with patch('camera_view.shutil.which',return_value='/usr/bin/ffmpeg'),patch('camera_view.subprocess.run',side_effect=[subprocess.TimeoutExpired('ffmpeg',3),SimpleNamespace(returncode=0,stdout=b'max_redirects')]) as run:
            self.assertFalse(self.probe());self.assertEqual(self.probe.reason,'retrying')
            self.assertFalse(self.probe());self.assertEqual(run.call_count,1)
            self.now+=5;self.assertTrue(self.probe());self.assertEqual(run.call_count,2)
            self.now+=3600;self.assertTrue(self.probe());self.assertEqual(run.call_count,2)
    def test_missing_program_is_rechecked_after_it_becomes_available(self):
        with patch('camera_view.shutil.which',side_effect=[None,'/usr/bin/ffmpeg']),patch('camera_view.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=b'max_redirects')):
            self.assertFalse(self.probe());self.assertIn('Monitor-Server',self.probe.message())
            self.now+=5;self.assertTrue(self.probe());self.assertEqual(self.probe.message(),'')
    def test_failed_or_unsupported_program_does_not_become_ready(self):
        with patch('camera_view.shutil.which',return_value='/usr/bin/ffmpeg'),patch('camera_view.subprocess.run',side_effect=[SimpleNamespace(returncode=1,stdout=b'max_redirects'),SimpleNamespace(returncode=0,stdout=b'old help'),SimpleNamespace(returncode=0,stdout=b'max_redirects')]):
            self.assertFalse(self.probe());self.now+=5;self.assertFalse(self.probe());self.now+=5;self.assertTrue(self.probe())
    def test_os_error_is_temporary_and_message_identifies_server(self):
        with patch('camera_view.shutil.which',return_value='/usr/bin/ffmpeg'),patch('camera_view.subprocess.run',side_effect=OSError('temporary')):
            self.assertFalse(self.probe());self.assertIn('Monitor-Server',self.probe.message());self.assertIn('keine Installation',self.probe.message())

class RuntimeAvailabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_running_service_reports_recovered_camera_after_timeout(self):
        import json
        from unittest.mock import AsyncMock
        from aiohttp.test_utils import make_mocked_request
        from monitor import build_app
        now=[100];probe=DecoderAvailability(clock=lambda:now[0])
        service=SimpleNamespace(ip='192.168.1.20',ips=['192.168.1.20'],cameras=SimpleNamespace(available=probe,start=AsyncMock(),stop=AsyncMock()),start=AsyncMock(),stop=AsyncMock())
        app=build_app(service)
        async def health():
            request=make_mocked_request('GET','/health');match=await app.router.resolve(request)
            return json.loads((await app.middlewares[0](request,match.handler)).text)
        with patch('camera_view.shutil.which',return_value='/usr/bin/ffmpeg'),patch('camera_view.subprocess.run',side_effect=[subprocess.TimeoutExpired('ffmpeg',3),SimpleNamespace(returncode=0,stdout=b'max_redirects')]):
            self.assertFalse((await health())['camera_available']);now[0]+=5
            self.assertTrue((await health())['camera_available'])
