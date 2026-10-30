import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from history import History
from monitor import build_app
from aiohttp.test_utils import make_mocked_request


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.now=1000
        self.history=History(Path(self.tmp.name)/'test.db',clock=lambda:self.now)
        self.ip='192.168.1.102'
    def tearDown(self):
        self.history.close();self.tmp.cleanup()
    def observe(self,state='printing',progress=10,ip=None):
        self.history.observe(ip or self.ip,'info',{'code':200,'data':{'project':{
            'state':state,'filename':'handle.gcode','progress':progress,'print_time':206}}},
            {'connection':'online','data':{'print_state':state,'nozzle_temp':230,'bed_temp':75}})
    def test_completed_report_uses_observation_time_and_keeps_job(self):
        self.observe();job=self.history.jobs()[0]
        self.now+=60;self.observe('finished',100)
        before=self.history.jobs()
        result=self.history.report(job['id'])
        self.assertIn('Abgeschlossen',result)
        self.assertIn('0 h 1 min 0 s',result)
        self.assertIn('230–230 °C',result)
        self.assertEqual(self.history.jobs(),before)
    def test_disconnect_does_not_claim_completion_and_other_printer_is_excluded(self):
        self.observe();job=self.history.jobs()[0]
        self.now+=30;self.history.link('192.168.1.101',False)
        self.now+=10;self.history.link(self.ip,False)
        self.now+=150;self.observe()
        result=self.history.report(job['id'])
        self.assertIn('vorläufig',result)
        self.assertIn('Verbindungsunterbrechungen: 1',result)
        self.assertIn('nicht vollständig rekonstruierbar',result)
        self.assertNotIn('192.168.1.101',result)
    def test_missing_job_and_sql_input_cannot_select_another_job(self):
        self.observe()
        self.assertIsNone(self.history.report("' OR 1=1 --"))
    def test_legacy_leveling_is_explained_without_claiming_full_start(self):
        self.observe('auto_leveling')
        result=self.history.report(self.history.jobs()[0]['id'])
        self.assertIn('auto_leveling',result)
        self.assertIn('bestätigt keinen beobachteten Beginn',result)


class ReportEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_download_unknown_and_invalid_ids_without_printer_calls(self):
        history=SimpleNamespace(report=Mock(return_value='# Druckbericht\n'))
        service=SimpleNamespace(history=history,start=AsyncMock(),stop=AsyncMock())
        app=build_app(service)
        async def call(method,path):
            request=make_mocked_request(method,path)
            match=await app.router.resolve(request)
            return await app.middlewares[0](request,match.handler)
        valid='a'*32
        result=await call('GET','/api/report?job='+valid)
        self.assertEqual(result.status,200)
        self.assertIn('attachment;',result.headers['Content-Disposition'])
        self.assertEqual(result.content_type,'text/markdown')
        history.report.assert_called_once_with(valid)
        history.report.return_value=None
        self.assertEqual((await call('GET','/api/report?job='+valid)).status,404)
        history.report.reset_mock()
        self.assertEqual((await call('GET','/api/report?job=../secrets')).status,400)
        self.assertEqual((await call('POST','/api/report?job='+valid)).status,403)
        history.report.assert_not_called()

if __name__=='__main__':unittest.main()
