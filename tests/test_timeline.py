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


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.now=1000
        self.h=History(Path(self.tmp.name)/'test.db',clock=lambda:self.now)
        self.ip='192.168.1.102'
    def tearDown(self):self.h.close();self.tmp.cleanup()
    def observe(self,ip=None,age=0,connection='online',state='printing'):
        self.h.observe(ip or self.ip,'info',{'code':200,'data':{'project':{'state':state,'filename':'test.gcode'}}},
            {'connection':connection,'section_age_s':{'temperature':age},'data':{
                'nozzle_temp':230,'bed_temp':75,'nozzle_target':230,'bed_target':75,
                'password':'MUST NOT EXPORT','upload':'http://not-exported'}})
    def test_stale_and_disconnected_temperatures_are_missing_not_real_values(self):
        self.observe();job=self.h.jobs()[0]
        self.now+=30;self.observe(age=91)
        self.now+=30;self.observe(connection='offline')
        points=self.h.timeline(job['id'])['points']
        self.assertEqual(points[0]['nozzle_temp'],230)
        self.assertIsNone(points[1]['nozzle_temp']);self.assertIsNone(points[2]['nozzle_temp'])
        self.assertEqual(len(points),3)
    def test_other_devices_and_jobs_are_excluded_and_no_secrets_exported(self):
        self.observe();job=self.h.jobs()[0];self.now+=30
        self.observe(ip='192.168.1.101');self.h.link('192.168.1.101',False)
        self.h.link(self.ip,False);self.now+=30;self.observe(state='finished')
        self.now+=30;self.observe()
        data=self.h.timeline(job['id'])
        self.assertEqual(len(data['points']),2)
        self.assertEqual([e['kind'] for e in data['events']].count('disconnected'),1)
        self.assertEqual(data['job']['state'],'completed')
        self.assertNotIn('MUST NOT EXPORT',json.dumps(data))
        self.assertNotIn('192.168.1.101',json.dumps(data))
    def test_reading_timeline_keeps_history_unchanged_and_unknown_id_is_missing(self):
        self.observe();before=self.h.jobs();self.h.timeline(before[0]['id'])
        self.assertEqual(self.h.jobs(),before)
        self.assertIsNone(self.h.timeline("' OR 1=1 --"))


class TimelineEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_valid_read_requests_reach_stored_history(self):
        history=SimpleNamespace(timeline=Mock(return_value={'read_only':True,'points':[]}))
        service=SimpleNamespace(history=history,start=AsyncMock(),stop=AsyncMock())
        app=build_app(service)
        async def call(method,path):
            r=make_mocked_request(method,path);match=await app.router.resolve(r)
            return await app.middlewares[0](r,match.handler)
        job='b'*32
        self.assertEqual((await call('GET','/api/timeline?job='+job)).status,200)
        history.timeline.assert_called_once_with(job)
        history.timeline.return_value=None
        self.assertEqual((await call('GET','/api/timeline?job='+job)).status,404)
        history.timeline.reset_mock()
        self.assertEqual((await call('GET','/api/timeline?job=../file')).status,400)
        self.assertEqual((await call('POST','/api/timeline?job='+job)).status,403)
        history.timeline.assert_not_called()

if __name__=='__main__':unittest.main()
