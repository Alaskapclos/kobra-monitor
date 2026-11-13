"""Speed intents are tied to the observed job; only synthetic sockets are used."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid
sys.path[:0]=[str(Path(__file__).resolve().parent.parent),str(Path(__file__).resolve().parent.parent/'vendor/kobra-bridge')]
from controls import LightControls, ControlRefused
from light_transport import LightControlClient
from read_only_policy import ReadOnlyViolation
from monitor import Monitor
from test_light_transport import decode

class TemperatureIntentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.data=dict(online=True,connection_id='epoch',light_on=0,light_revision=1,light_age_s=0,context='a'*64)
        self.sent=[]
        async def send(ip,control,mode,epoch,context):
            self.sent.append((ip,mode,epoch,context));self.data.update(light_on=mode,light_revision=self.data['light_revision']+1)
        self.c=LightControls(Path(self.tmp.name)/'db',lambda ip:None,lambda *a:None,enabled=True,
            temperature_snapshot=lambda ip,control:dict(self.data),temperature_sender=send,confirmation_timeout=.02)
        self.addCleanup(self.c.close)
    async def prepare(self,mode=60):return await self.c.prepare('owner','192.0.2.1',mode,str(uuid.uuid4()),control='bed_target')
    async def test_prepare_never_sends_execute_once_and_exact_job_context(self):
        p=await self.prepare();self.assertEqual(p['context'],'a'*64);self.assertEqual(p['previous'],0);self.assertEqual(self.sent,[])
        result=await self.c.execute('owner',p['id'],p['token']);self.assertEqual(result['state'],'confirmed')
        await self.c.execute('owner',p['id'],p['token']);self.assertEqual(len(self.sent),1);self.assertEqual(self.sent[0][1:],(60,'epoch','a'*64))
    async def test_cancel_and_same_mode_never_send(self):
        p=await self.prepare();await self.c.cancel('owner',p['id']);await self.c.execute('owner',p['id'],'old')
        self.assertEqual((await self.prepare(0))['state'],'unchanged');self.assertEqual(self.sent,[])
    async def test_invalid_mode_missing_context_and_stale_state_are_rejected(self):
        for mode in (True,False,-1,121,2.0,'2',None):
            with self.assertRaises(ControlRefused):await self.prepare(mode)
        for change in ({'context':''},{'context':None},{'online':False},{'light_age_s':16},{'light_on':999}):
            previous=dict(self.data);self.data.update(change)
            with self.assertRaises(ControlRefused):await self.prepare()
            self.data=previous
        self.assertEqual(self.sent,[])
    async def test_changed_job_reconnect_or_mode_before_execute_never_send(self):
        for change in ({'context':'b'*64},{'connection_id':'another'},{'light_on':1}):
            p=await self.prepare();old=dict(self.data);self.data.update(change)
            with self.assertRaises(ControlRefused):await self.c.execute('owner',p['id'],p['token'])
            self.data=old
        self.assertEqual(self.sent,[])
    async def test_changed_job_after_send_cannot_be_confirmed(self):
        async def send(*args):self.sent.append(args);self.data.update(context='b'*64,light_on=60,light_revision=2)
        self.c.temperature_sender=send;p=await self.prepare()
        self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'uncertain');self.assertEqual(len(self.sent),1)
    async def test_old_revision_does_not_confirm(self):
        async def send(*args):self.data['light_on']=60
        self.c.temperature_sender=send;p=await self.prepare()
        self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'uncertain')
    async def test_other_session_and_parallel_printer_control_are_rejected(self):
        p=await self.prepare()
        with self.assertRaises(ControlRefused):await self.c.execute('other',p['id'],p['token'])
        with self.assertRaises(ControlRefused):await self.prepare(1)
        self.assertFalse(self.sent)

class TemperatureTransportTests(unittest.TestCase):
    def client(self,enabled=True):
        c=LightControlClient('192.0.2.1','fake','fake','20025','fake',temperature_control_enabled=enabled)
        c._sock=Mock();c._running=True;c._sock_gen=1;return c
    def send(self,c,heater='nozzle_target',value=200,guard=lambda:True):
        c.send_temperature_once(heater,value,c.control_connection_id(),send_deadline=time.monotonic()+1,job_guard=guard)
    def test_each_heater_exact_packet_and_off(self):
        c=self.client()
        for heater,maxval in [('nozzle_target',320),('bed_target',120)]:
            for value in (0,maxval):
                self.send(c,heater,value);topic,body=decode(c._sock.sendall.call_args.args[0])
                self.assertTrue(topic.endswith('/tempature'));self.assertEqual(body['action'],'set')
                self.assertEqual(body['data'],{'type':0 if heater=='nozzle_target' else 1,'target_nozzle_temp':value if heater=='nozzle_target' else 0,'target_hotbed_temp':value if heater=='bed_target' else 0})
    def test_limits_types_allowlist_and_context_guard(self):
        c=self.client(False)
        with self.assertRaises(PermissionError):self.send(c)
        c.temperature_control_enabled=True
        for heater,value in [('other',0),('nozzle_target',321),('bed_target',121),('bed_target',True),('bed_target',60.0),('bed_target','60'),('bed_target',-1)]:
            with self.assertRaises(ValueError):self.send(c,heater,value)
        with self.assertRaises(ConnectionError):self.send(c,guard=lambda:False)
        c._sock.sendall.assert_not_called()
    def test_generic_writes_stay_blocked_and_partial_send_not_retried(self):
        c=self.client()
        with self.assertRaises(ReadOnlyViolation):c.publish_web('tempature','set',{'type':0,'target_nozzle_temp':200,'target_hotbed_temp':0})
        c._sock.sendall.side_effect=OSError()
        with self.assertRaises(OSError):self.send(c)
        self.assertEqual(c._sock.sendall.call_count,1)
    def test_slow_guard_cannot_extend_deadline(self):
        c=self.client()
        def guard():self.assertTrue(c._lock.locked());time.sleep(.02);return True
        with self.assertRaises(TimeoutError):c.send_temperature_once('bed_target',60,c.control_connection_id(),send_deadline=time.monotonic()+.01,job_guard=guard)
        c._sock.sendall.assert_not_called()

class TemperatureTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.m=Monitor('192.0.2.1',self.tmp.name,self.tmp.name,temperature_control=True)
        self.m.client=SimpleNamespace(mode_id='20025',control_connection_id=lambda:'current')
        self.m.telemetry.link(True);self.clock=100;self.m.telemetry.clock=lambda:self.clock
        self.bridge=SimpleNamespace(_state={})
    def info(self,project=None,epoch='current',state='free',temp=None):
        self.m.telemetry.receive('info',{'data':{'state':state,'project':project,'temp':temp or {'curr_nozzle_temp':24,'target_nozzle_temp':0,'target_hotbed_temp':0}}},self.bridge,epoch)
    def test_idle_context_stable_across_refresh_and_heater_confirmation_independent_of_actual(self):
        self.info();a=self.m.temperature_snapshot('nozzle_target');self.assertTrue(a['online']);self.info()
        self.assertEqual(a['context'],self.m.temperature_snapshot('nozzle_target')['context'])
        self.info(temp={'curr_nozzle_temp':24,'target_nozzle_temp':200,'target_hotbed_temp':0})
        b=self.m.temperature_snapshot('nozzle_target');self.assertEqual(b['light_on'],200);self.assertGreater(b['light_revision'],a['light_revision'])
    def test_print_start_pause_resume_and_end_invalidate_previous_context(self):
        self.info();a=self.m.temperature_snapshot('bed_target')['context']
        job={'task_id':-1,'filename':'part.3mf','state':'printing'}
        self.info(job,state='busy');b=self.m.temperature_snapshot('bed_target');self.assertTrue(b['online']);self.assertNotEqual(a,b['context'])
        self.info({**job,'pause':1},state='busy');self.assertGreater(self.m.temperature_snapshot('bed_target')['light_age_s'],15)
        self.info(job,state='busy');self.assertNotEqual(b['context'],self.m.temperature_snapshot('bed_target')['context'])
        self.m.telemetry.receive('print',{'state':'finished','data':{}},self.bridge,'current')
        self.assertFalse(self.m.temperature_snapshot('bed_target')['online'])
    def test_missing_raw_targets_no_defaults_and_old_socket_or_stale_are_blocked(self):
        self.info(temp={'curr_nozzle_temp':24});self.assertIsNone(self.m.temperature_snapshot('bed_target')['light_on'])
        self.info(epoch='old');self.assertFalse(self.m.temperature_snapshot('bed_target')['online'])
        self.info();self.clock+=16;self.assertGreater(self.m.temperature_snapshot('bed_target')['light_age_s'],15)
    def test_partial_temperature_ack_does_not_refresh_job_authority(self):
        self.info();self.clock+=16
        self.m.telemetry.receive('tempature',{'data':{'target_nozzle_temp':200}},None,'current')
        self.assertGreater(self.m.temperature_snapshot('nozzle_target')['light_age_s'],15)
    def test_unknown_busy_phase_never_authorizes_heating(self):
        self.info(state='busy');self.assertGreater(self.m.temperature_snapshot('bed_target')['light_age_s'],15)
        self.info({'state':'auto_leveling'},state='busy');self.assertGreater(self.m.temperature_snapshot('bed_target')['light_age_s'],15)

    def test_preparation_report_without_filename_immediately_invalidates_idle_intent(self):
        self.info();self.assertTrue(self.m.temperature_snapshot('bed_target')['online'])
        self.m.telemetry.receive('print',{'state':'auto_leveling','data':{}},self.bridge,'current')
        self.assertGreater(self.m.temperature_snapshot('bed_target')['light_age_s'],15)
