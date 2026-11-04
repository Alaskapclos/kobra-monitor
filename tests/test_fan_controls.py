"""Fan routing, intent isolation, schema upgrade and real-report confirmation."""
import asyncio
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
import uuid
from unittest.mock import Mock
import sys
sys.path[:0]=[str(Path(__file__).resolve().parent.parent),str(Path(__file__).resolve().parent.parent/'vendor/kobra-bridge')]
from controls import LightControls, ControlRefused, FAN_FIELDS
from light_transport import LightControlClient
from test_light_transport import decode
from monitor import Monitor, Fleet
from types import SimpleNamespace

class FanControlsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.data={k:dict(online=True,connection_id='epoch',light_on=0,light_revision=1,light_age_s=0) for k in FAN_FIELDS}
        self.light=dict(online=True,connection_id='epoch',light_on=False,light_revision=1,light_age_s=0)
        self.sent=[]
        async def send(ip,fan,value,epoch):
            self.sent.append((ip,fan,value,epoch));self.data[fan].update(light_on=value,light_revision=2)
        self.c=LightControls(Path(self.tmp.name)/'history.sqlite3',lambda ip:self.light,lambda *a:None,
            enabled=True,fan_snapshot=lambda ip,fan:self.data[fan],fan_sender=send,confirmation_timeout=.03)
        self.addCleanup(self.c.close)
    async def prepare(self,fan='part_fan',value=40,rid=None):
        return await self.c.prepare('owner','192.0.2.1',value,rid or str(uuid.uuid4()),control=fan)
    async def test_each_fan_is_numeric_and_requires_execute_once(self):
        for fan in FAN_FIELDS:
            p=await self.prepare(fan);self.assertEqual(p['desired'],40);self.assertEqual(p['previous'],0)
            self.assertEqual(p['action'],fan);before=len(self.sent)
            self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'confirmed')
            await self.c.execute('owner',p['id'],p['token']);self.assertEqual(len(self.sent),before+1)
            self.assertEqual(self.sent[-1][1:3],(fan,40))
    async def test_cancel_and_unchanged_never_send(self):
        p=await self.prepare();await self.c.cancel('owner',p['id']);await self.c.execute('owner',p['id'],'old')
        p=await self.prepare(value=0);self.assertEqual(p['state'],'unchanged');self.assertFalse(self.sent)
    async def test_invalid_channel_and_level_rejected(self):
        for v in (True,False,None,'20',20.5,-1,101):
            with self.assertRaises(ControlRefused):await self.prepare(value=v)
        with self.assertRaises(ControlRefused):await self.prepare(fan='hotend_fan')
        self.assertFalse(self.sent)
    async def test_shared_light_fan_lock_and_request_identity(self):
        rid=str(uuid.uuid4());p=await self.prepare(rid=rid)
        for fan,v in [('aux_fan',40),('part_fan',41)]:
            with self.assertRaises(ControlRefused):await self.prepare(fan,v,rid)
        with self.assertRaises(ControlRefused):await self.c.prepare('owner','192.0.2.1',True,str(uuid.uuid4()))
        await self.c.cancel('owner',p['id']);self.assertFalse(self.sent)
    async def test_changed_value_reconnect_and_stale_reports_never_send(self):
        for mutation in ({'light_on':10},{'connection_id':'new'},{'light_age_s':16}):
            p=await self.prepare();self.data['part_fan'].update(mutation)
            with self.assertRaises(ControlRefused):await self.c.execute('owner',p['id'],p['token'])
            self.data['part_fan'].update(light_on=0,connection_id='epoch',light_age_s=0)
        self.assertFalse(self.sent)
    async def test_value_without_new_revision_is_not_confirmed(self):
        async def send(ip,fan,value,epoch):self.data[fan]['light_on']=value
        self.c.fan_sender=send;p=await self.prepare()
        self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'uncertain')
    async def test_old_light_rows_migrate_without_value_changes(self):
        path=Path(self.tmp.name)/'old.db'
        db=sqlite3.connect(path);schema=self.c.db.execute("SELECT sql FROM sqlite_master WHERE name='control_attempts'").fetchone()[0]
        schema=schema[:schema.rfind(', control TEXT')]+')' if ', control TEXT' in schema else schema
        # Use exact original schema, excluding newly appended column.
        schema=schema.replace(", control TEXT NOT NULL DEFAULT 'chamber_light'",'')
        db.execute(schema);db.close()
        old=LightControls(path,lambda ip:self.light);old.close()
        db=sqlite3.connect(path);self.assertIn('control',[r[1] for r in db.execute('pragma table_info(control_attempts)')]);db.close()

class FanTransportTests(unittest.TestCase):
    def client(self,enabled=True):
        c=LightControlClient('192.0.2.1','fake','fake','20025','fake',fan_control_enabled=enabled)
        c._sock=Mock();c._running=True;c._sock_gen=1;return c
    def test_exact_single_field_per_fan_and_no_light_permission_required(self):
        c=self.client()
        for fan,field in [('part_fan','fan_speed_pct'),('aux_fan','aux_fan_speed_pct'),('chamber_fan','box_fan_level')]:
            c.send_fan_once(fan,40,c.control_connection_id(),send_deadline=time.monotonic()+1)
            topic,body=decode(c._sock.sendall.call_args.args[0]);self.assertTrue(topic.endswith('/fan'))
            self.assertEqual(body['type'],'fan');self.assertEqual(body['action'],'setSpeed');self.assertEqual(body['data'],{field:40})
    def test_disable_invalid_level_and_expired_connection_never_send(self):
        c=self.client(False)
        with self.assertRaises(PermissionError):c.send_fan_once('part_fan',40,c.control_connection_id(),send_deadline=time.monotonic()+1)
        c.fan_control_enabled=True
        for fan,value in [('bogus',40),('part_fan',True),('aux_fan',101)]:
            with self.assertRaises(ValueError):c.send_fan_once(fan,value,c.control_connection_id(),send_deadline=time.monotonic()+1)
        with self.assertRaises(ConnectionError):c.send_fan_once('part_fan',40,'old',send_deadline=time.monotonic()+1)
        c._sock.sendall.assert_not_called()
    def test_partial_write_never_retry(self):
        c=self.client();c._sock.sendall.side_effect=OSError()
        with self.assertRaises(OSError):c.send_fan_once('part_fan',40,c.control_connection_id(),send_deadline=time.monotonic()+1)
        self.assertEqual(c._sock.sendall.call_count,1)

class FanTelemetryTests(unittest.TestCase):
    def test_channel_report_must_be_from_current_socket(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=Monitor('192.0.2.1',tmp,tmp,fan_control=True)
            m.client=SimpleNamespace(mode_id='20025',control_connection_id=lambda:'current')
            m.telemetry.link(True)
            m.telemetry.receive('fan',{'data':{'fan_speed_pct':40}},None,'old')
            self.assertFalse(m.fan_snapshot('part_fan')['online'])
            m.telemetry.receive('fan',{'data':{'aux_fan_speed_pct':50}},None,'current')
            self.assertFalse(m.fan_snapshot('part_fan')['online']);self.assertTrue(m.fan_snapshot('aux_fan')['online'])
