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

class SpeedIntentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.data=dict(online=True,connection_id='epoch',light_on=2,light_revision=1,light_age_s=0,context='a'*64)
        self.sent=[]
        async def send(ip,mode,epoch,context):
            self.sent.append((ip,mode,epoch,context));self.data.update(light_on=mode,light_revision=self.data['light_revision']+1)
        self.c=LightControls(Path(self.tmp.name)/'db',lambda ip:None,lambda *a:None,enabled=True,
            speed_snapshot=lambda ip:dict(self.data),speed_sender=send,confirmation_timeout=.02)
        self.addCleanup(self.c.close)
    async def prepare(self,mode=3):return await self.c.prepare('owner','192.0.2.1',mode,str(uuid.uuid4()),control='speed_mode')
    async def test_prepare_never_sends_execute_once_and_exact_job_context(self):
        p=await self.prepare();self.assertEqual(p['context'],'a'*64);self.assertEqual(p['previous'],2);self.assertEqual(self.sent,[])
        result=await self.c.execute('owner',p['id'],p['token']);self.assertEqual(result['state'],'confirmed')
        await self.c.execute('owner',p['id'],p['token']);self.assertEqual(len(self.sent),1);self.assertEqual(self.sent[0][1:],(3,'epoch','a'*64))
    async def test_cancel_and_same_mode_never_send(self):
        p=await self.prepare();await self.c.cancel('owner',p['id']);await self.c.execute('owner',p['id'],'old')
        self.assertEqual((await self.prepare(2))['state'],'unchanged');self.assertEqual(self.sent,[])
    async def test_invalid_mode_missing_context_and_stale_state_are_rejected(self):
        for mode in (True,False,0,4,2.0,'2',None):
            with self.assertRaises(ControlRefused):await self.prepare(mode)
        for change in ({'context':''},{'context':None},{'online':False},{'light_age_s':16},{'light_on':99}):
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
        async def send(*args):self.sent.append(args);self.data.update(context='b'*64,light_on=3,light_revision=2)
        self.c.speed_sender=send;p=await self.prepare()
        self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'uncertain');self.assertEqual(len(self.sent),1)
    async def test_old_revision_does_not_confirm(self):
        async def send(*args):self.data['light_on']=3
        self.c.speed_sender=send;p=await self.prepare()
        self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'uncertain')
    async def test_other_session_and_parallel_printer_control_are_rejected(self):
        p=await self.prepare()
        with self.assertRaises(ControlRefused):await self.c.execute('other',p['id'],p['token'])
        with self.assertRaises(ControlRefused):await self.prepare(1)
        self.assertFalse(self.sent)

class SpeedTransportTests(unittest.TestCase):
    def client(self,enabled=True):
        c=LightControlClient('192.0.2.1','fake','fake','20025','fake',speed_control_enabled=enabled)
        c._sock=Mock();c._running=True;c._sock_gen=1;return c
    def send(self,c,mode=3,task='-1',guard=lambda:True):
        c.send_speed_once(mode,task,c.control_connection_id(),send_deadline=time.monotonic()+1,job_guard=guard)
    def test_exact_packet_only_speed_setting_with_observed_local_task(self):
        c=self.client()
        for mode in (1,2,3):
            self.send(c,mode);topic,body=decode(c._sock.sendall.call_args.args[0]);self.assertTrue(topic.endswith('/print'))
            self.assertEqual((body['type'],body['action']),('print','update'))
            self.assertEqual(body['data'],{'taskid':'-1','settings':{'print_speed_mode':mode}})
    def test_disabled_unknown_mode_and_invalid_task_never_send(self):
        c=self.client(False)
        with self.assertRaises(PermissionError):self.send(c)
        c.speed_control_enabled=True
        for mode in (True,0,4,'2',2.0):
            with self.assertRaises(ValueError):self.send(c,mode)
        for task in ('','0','-2','other/task',None,False,1):
            with self.assertRaises(ValueError):self.send(c,task=task)
        with self.assertRaises(ValueError):self.send(c,guard=None)
        c._sock.sendall.assert_not_called()
    def test_changed_job_checked_inside_socket_lock(self):
        c=self.client()
        def guard():
            self.assertTrue(c._lock.locked());return False
        with self.assertRaises(ConnectionError):self.send(c,guard=guard)
        c._sock.sendall.assert_not_called()
    def test_slow_guard_cannot_extend_deadline(self):
        c=self.client()
        def guard():time.sleep(.02);return True
        with self.assertRaises(TimeoutError):
            c.send_speed_once(3,'-1',c.control_connection_id(),send_deadline=time.monotonic()+.01,job_guard=guard)
        c._sock.sendall.assert_not_called()
    def test_partial_write_not_retried_and_generic_publish_stays_blocked(self):
        c=self.client()
        with self.assertRaises(ReadOnlyViolation):c.publish_web('print','update',{'taskid':'-1','settings':{'print_speed_mode':3}})
        c._sock.sendall.side_effect=OSError()
        with self.assertRaises(OSError):self.send(c)
        self.assertEqual(c._sock.sendall.call_count,1)

class SpeedTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.job={'id':'monitor-job-a','filename':'part.3mf','state':'printing','ended_at':None}
        self.m=Monitor('192.0.2.1',self.tmp.name,self.tmp.name,SimpleNamespace(jobs=lambda ip:[dict(self.job)]),speed_control=True)
        self.m.client=SimpleNamespace(mode_id='20025',control_connection_id=lambda:'current')
        self.m.telemetry.link(True);self.clock=100;self.m.telemetry.clock=lambda:self.clock
        self.bridge=SimpleNamespace(_state={'filename':'part.3mf','print_state':'printing'})
    def info(self,task=-1,file='part.3mf',phase='printing',epoch='current'):
        self.m.telemetry.receive('info',{'data':{'project':{'task_id':task,'filename':file,'state':phase},'print_speed_mode':2}},self.bridge,epoch)
    def test_received_minus_one_is_bound_to_monitor_job_not_default(self):
        self.assertIsNone(self.m.speed_snapshot());self.info();a=self.m.speed_snapshot()
        self.assertTrue(a['online']);self.assertEqual(a['task_id'],'-1')
        self.info();self.assertEqual(a['context'],self.m.speed_snapshot()['context'])
        self.job['id']='monitor-job-b';self.assertNotEqual(a['context'],self.m.speed_snapshot()['context'])
    def test_idle_pause_and_job_replacement_invalidate_context(self):
        self.info();a=self.m.speed_snapshot()['context'];self.info(phase='paused');self.assertFalse(self.m.speed_snapshot()['online'])
        self.info();self.assertNotEqual(a,self.m.speed_snapshot()['context'])
        self.info(file='other.3mf');self.assertIsNone(self.m.speed_snapshot())
        self.m.telemetry.receive('info',{'data':{'state':'free','project':None}},self.bridge,'current');self.assertFalse(self.m.speed_snapshot()['online'] if self.m.speed_snapshot() else False)
    def test_old_connection_and_stale_job_not_usable(self):
        self.info(epoch='old');self.assertFalse(self.m.speed_snapshot()['online'])
        self.info();self.clock+=16;self.assertGreater(self.m.speed_snapshot()['light_age_s'],15)
    def test_partial_ack_cannot_refresh_task_authority(self):
        self.info();self.clock+=16
        self.m.telemetry.receive('print',{'state':'done','data':{'settings':{'print_speed_mode':3}}},self.bridge,'current')
        self.assertGreater(self.m.speed_snapshot()['light_age_s'],15)
    def test_partial_report_from_other_job_blocks_until_full_info(self):
        self.info();self.m.telemetry.receive('print',{'state':'printing','data':{'taskid':'123','settings':{'print_speed_mode':3}}},self.bridge,'current')
        self.assertGreater(self.m.speed_snapshot()['light_age_s'],15)

    def test_same_filename_and_local_task_elapsed_reset_changes_context(self):
        def report(elapsed):
            self.m.telemetry.receive('info',{'data':{'project':{'task_id':-1,'filename':'part.3mf','state':'printing','print_time':elapsed},'print_speed_mode':2}},self.bridge,'current')
        report(30);before=self.m.speed_snapshot()['context'];report(31)
        self.assertEqual(before,self.m.speed_snapshot()['context']);report(0)
        self.assertNotEqual(before,self.m.speed_snapshot()['context'])
