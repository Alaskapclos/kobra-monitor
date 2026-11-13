# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from aiohttp.test_utils import make_mocked_request
from access import Access
from diagnostics import summary
from monitor import Fleet, build_app


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.fleet=Fleet(['192.168.250.10'],self.tmp.name,str(Path(self.tmp.name)/'data'))
        self.fleet.started=100
        self.fleet.cameras.available=Mock(return_value=True)
        self.fleet.notifications.task=SimpleNamespace(done=lambda:False)
        self.telemetry=self.fleet.monitors[self.fleet.ips[0]].telemetry
        self.snapshot={'ip':'192.168.250.10','connection':'online','age_s':2.5,
                       'data':{'printer_name':'Private printer','filename':'Private job.gcode'},
                       'section_age_s':{'temperature':4}}
        self.telemetry.snapshot=Mock(side_effect=lambda:self.snapshot)
    def tearDown(self):self.fleet.reprints.close();self.fleet.history.close();self.tmp.cleanup()
    def test_report_has_only_allowlisted_operational_values(self):
        report=summary(self.fleet,clock=lambda:160)
        self.assertEqual(report['uptime_seconds'],60)
        self.assertEqual(report['printers'],[{'number':1,'state':'online','age_seconds':2.5,'temperature_current':True}])
        for secret in ('192.168','Private printer','Private job','filename','endpoint','password',self.tmp.name):self.assertNotIn(secret,json.dumps(report))
        self.assertTrue(report['notifications']['worker_running'])
        self.assertTrue(report['camera_decoder_ready'])
    def test_temperature_freshness_requires_online_and_valid_recent_measurement(self):
        for state,age in [('stale',3),('offline',3),('online',91),('online',None),('online',float('nan')),('online',True)]:
            self.snapshot.update(connection=state,section_age_s={'temperature':age})
            self.assertFalse(summary(self.fleet)['printers'][0]['temperature_current'])
    def test_unknown_nonfinite_or_negative_ages_do_not_escape(self):
        for age in (float('inf'),float('nan'),-1,True,'private value'):
            self.snapshot.update(connection='private state',age_s=age)
            item=summary(self.fleet)['printers'][0]
            self.assertEqual(item['state'],'connecting');self.assertIsNone(item['age_seconds'])
    def test_device_errors_pending_counts_and_completed_history_are_read_only(self):
        db=self.fleet.history.db
        db.execute("INSERT INTO push_devices(id,last_status,label,subscription) VALUES('fixture','failed','Private device','Private endpoint')")
        db.execute("INSERT INTO push_queue(device_id,event_key,payload,created_at,next_at,status) VALUES('fixture','fixture','Private body',0,0,'pending')")
        db.commit();before=db.total_changes
        report=summary(self.fleet)
        self.assertEqual(report['notifications']['devices'],1)
        self.assertEqual(report['notifications']['devices_with_errors'],1)
        self.assertEqual(report['notifications']['pending'],1)
        self.assertEqual(before,db.total_changes)
        self.assertNotIn('Private',json.dumps(report))
    def test_empty_fleet_and_inactive_worker_report_honestly(self):
        self.fleet.ips=[];self.fleet.notifications.task=None;self.fleet.cameras.available.return_value=False
        report=summary(self.fleet)
        self.assertEqual(report['printers'],[]);self.assertFalse(report['notifications']['worker_running']);self.assertFalse(report['camera_decoder_ready'])
    def test_printer_order_uses_numbers_not_device_identifiers(self):
        self.fleet.ips=['192.168.250.99','192.168.250.10']
        items=summary(self.fleet)['printers']
        self.assertEqual([v['number'] for v in items],[1,2]);self.assertEqual(items[0]['state'],'connecting')


class DiagnosticAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_access_without_account_no_write_route_and_owner_can_read(self):
        with tempfile.TemporaryDirectory() as folder:
            access=Access(folder);fleet=SimpleNamespace(start=AsyncMock(),stop=AsyncMock())
            app=build_app(fleet,access)
            async def call(method,path,headers=None):
                req=make_mocked_request(method,path,headers={'Host':'localhost',**(headers or {})})
                match=await app.router.resolve(req);return await app.middlewares[0](req,match.handler)
            self.assertEqual((await call('GET','/api/diagnostics')).status,401)
            self.assertEqual((await call('POST','/api/diagnostics')).status,403)
            access.sessions['fixture']={'expires':access.clock()+10,'csrf':'fixture'}
            headers={'Cookie':'kobra_session=fixture'}
            self.assertEqual((await call('GET','/api/diagnostics',headers)).status,403)
            access.account={'username':'Fixture'}
            from unittest.mock import patch
            with patch('monitor.diagnostic_summary',return_value={'read_only':True}) as check:
                response=await call('GET','/api/diagnostics',headers)
            self.assertEqual(response.status,200);check.assert_called_once_with(fleet)
            self.assertEqual(response.headers['Cache-Control'],'no-store')


if __name__=='__main__':unittest.main()
