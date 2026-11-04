"""Job lifecycle controls: synthetic reports and sockets, no real printer IO."""
import asyncio,json,tempfile,time,uuid,unittest
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock
sys.path[:0]=[str(Path(__file__).resolve().parent.parent),str(Path(__file__).resolve().parent.parent/'vendor/kobra-bridge')]
from controls import LightControls,ControlRefused
from print_job_control import PrintJobState,PRINT_ACTIONS,PREPARING_PHASES
from light_transport import LightControlClient
from monitor import Monitor,Telemetry
from read_only_policy import ReadOnlyViolation
from test_light_transport import decode

class PrintIntentTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.data=dict(online=True,connection_id='epoch',light_on=1,light_revision=1,light_age_s=0,context='a'*64);self.sent=[]
  async def send(ip,control,epoch,context):
   self.sent.append((control,epoch,context));self.data.update(light_on=PRINT_ACTIONS[control][1],light_revision=self.data['light_revision']+1)
  self.c=LightControls(Path(self.tmp.name)/'db',lambda ip:None,lambda *args:None,enabled=True,print_snapshot=lambda ip:dict(self.data),print_sender=send,confirmation_timeout=.02);self.addCleanup(self.c.close)
 async def prepare(self,control='print_pause',request=None):return await self.c.prepare('owner','192.0.2.1',PRINT_ACTIONS[control][1],request or str(uuid.uuid4()),control)
 async def test_pause_resume_stop_exactly_once_with_context(self):
  for action,start in [('print_pause',1),('print_resume',2),('print_stop',1),('print_stop',2)]:
   self.data['light_on']=start;p=await self.prepare(action);self.assertEqual(p['context'],'a'*64);self.assertEqual(len(self.sent),0)
   result=await self.c.execute('owner',p['id'],p['token']);self.assertEqual(result['state'],'confirmed');self.assertEqual(self.sent[0],(action,'epoch','a'*64))
   await self.c.execute('owner',p['id'],p['token']);self.assertEqual(len(self.sent),1);self.sent.clear()
 async def test_invalid_source_phase_and_values_never_prepare(self):
  for action,phase in [('print_pause',2),('print_resume',1),('print_stop',3),('print_pause',4),('print_stop',0)]:
   self.data['light_on']=phase
   with self.assertRaises(ControlRefused):await self.prepare(action)
  self.data['light_on']=1
  for desired in (True,2.0,'2',0,4):
   with self.assertRaises(ControlRefused):await self.c.prepare('owner','192.0.2.1',desired,str(uuid.uuid4()),'print_pause')
  self.assertFalse(self.sent)
 async def test_cancel_and_duplicate_request_do_not_send(self):
  request=str(uuid.uuid4());p=await self.prepare(request=request);q=await self.prepare(request=request);self.assertEqual(p['id'],q['id'])
  await self.c.cancel('owner',p['id']);await self.c.execute('owner',p['id'],'expired');self.assertFalse(self.sent)
 async def test_changed_job_phase_connection_and_stale_state_before_execute(self):
  for change in ({'context':'b'*64},{'light_on':2},{'connection_id':'new'},{'online':False},{'light_age_s':16}):
   old=dict(self.data);p=await self.prepare();self.data.update(change)
   with self.assertRaises(ControlRefused):await self.c.execute('owner',p['id'],p['token'])
   self.data=old
  self.assertFalse(self.sent)
 async def test_another_job_reaching_target_state_never_confirms(self):
  async def send(*args):self.sent.append(args);self.data.update(context='b'*64,light_on=2,light_revision=2)
  self.c.print_sender=send;p=await self.prepare();self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'uncertain')
 async def test_free_or_finished_is_not_a_confirmed_stop(self):
  for phase in (0,4):
   self.data.update(light_on=1,light_revision=1)
   async def send(*args):self.data.update(light_on=phase,light_revision=2)
   self.c.print_sender=send;p=await self.prepare('print_stop');self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'uncertain')
 async def test_same_revision_and_reconnect_after_send_never_confirm(self):
  for change in ({'light_on':2},{'light_on':2,'light_revision':2,'connection_id':'new'}):
   self.data.update(light_on=1,light_revision=1,connection_id='epoch')
   async def send(*args):self.data.update(change)
   self.c.print_sender=send;p=await self.prepare();self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'uncertain')
 async def test_transition_waits_for_newer_final_state_without_resending(self):
  self.c.confirmation_timeout=.3
  async def finish():
   await asyncio.sleep(.01);self.data.update(light_on=2,light_revision=2)
  async def send(*args):
   self.sent.append(args);self.data['light_on']=0;asyncio.create_task(finish())
  self.c.print_sender=send;p=await self.prepare();self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'confirmed');self.assertEqual(len(self.sent),1)
 async def test_stop_during_preparation_confirms_but_pause_and_resume_are_refused(self):
  self.data['light_on']=5
  for action in ('print_pause','print_resume'):
   with self.assertRaises(ControlRefused):await self.prepare(action)
  p=await self.prepare('print_stop');self.assertEqual(p['previous'],5)
  self.assertEqual((await self.c.execute('owner',p['id'],p['token']))['state'],'confirmed');self.assertEqual(len(self.sent),1)
 async def pending_resume(self):
  self.sent.clear()
  self.data.update(light_on=2)
  self.c.print_transition_timeout=.4
  async def send(*args):
   self.sent.append(args);self.data.update(light_on=0,transition='resuming',transition_age_s=0)
  self.c.print_sender=send;p=await self.prepare('print_resume')
  result=await self.c.execute('owner',p['id'],p['token'])
  self.assertEqual(result['state'],'awaiting')
  await self.c.execute('owner',p['id'],p['token']);self.assertEqual(len(self.sent),1)
  return p
 async def test_late_resume_is_observed_once_and_requires_new_revision(self):
  p=await self.pending_resume()
  self.data.update(light_on=1,transition=None)
  await asyncio.sleep(.12);self.assertEqual(self.c._row(p['id'],'owner')['state'],'awaiting')
  self.data.update(light_revision=2)
  await asyncio.sleep(.12);self.assertEqual(self.c._row(p['id'],'owner')['state'],'confirmed');self.assertEqual(len(self.sent),1)
 async def test_pending_resume_rejects_disconnect_job_change_and_natural_end(self):
  for change in ({'online':False},{'context':'b'*64},{'connection_id':'other'},{'light_on':4,'light_revision':2}):
   self.data.update(online=True,context='a'*64,connection_id='epoch',light_on=2,light_revision=1)
   p=await self.pending_resume();self.data.update(change)
   await asyncio.sleep(.12);self.assertEqual(self.c._row(p['id'],'owner')['state'],'uncertain')
 async def test_pending_timeout_does_not_repeat_command(self):
  p=await self.pending_resume();await asyncio.sleep(.5)
  self.assertEqual(self.c._row(p['id'],'owner')['state'],'uncertain');self.assertEqual(len(self.sent),1)
 async def test_other_session_and_parallel_control_are_rejected(self):
  p=await self.prepare()
  with self.assertRaises(ControlRefused):await self.c.execute('other',p['id'],p['token'])
  with self.assertRaises(ControlRefused):await self.prepare('print_stop')

class PrintTransportTests(unittest.TestCase):
 def client(self,enabled=True):
  c=LightControlClient('192.0.2.1','fake','fake','20025','fake',print_control_enabled=enabled);c._sock=Mock();c._running=True;c._sock_gen=1;return c
 def send(self,c,action='pause',task='-1',guard=lambda:True):c.send_print_once(action,task,c.control_connection_id(),send_deadline=time.monotonic()+1,job_guard=guard)
 def test_exact_three_packets_and_observed_task_only(self):
  c=self.client()
  for action in ('pause','resume','stop'):
   self.send(c,action);topic,body=decode(c._sock.sendall.call_args.args[0]);self.assertTrue(topic.endswith('/print'));self.assertEqual(body['action'],action);self.assertEqual(body['data'],{'taskid':'-1'})
 def test_allowlist_model_types_and_unknown_actions_blocked(self):
  c=self.client(False)
  with self.assertRaises(PermissionError):self.send(c)
  c.print_control_enabled=True
  for action in ('start','restart','cancel',None,True):
   with self.assertRaises(ValueError):self.send(c,action)
  for task in (None,False,1,'','0','-2','other/task'):
   with self.assertRaises(ValueError):self.send(c,task=task)
  c.mode_id='other'
  with self.assertRaises(ValueError):self.send(c)
  c._sock.sendall.assert_not_called()
 def test_guard_runs_inside_socket_lock_and_deadline_remains_bounded(self):
  c=self.client()
  def guard():self.assertTrue(c._lock.locked());return False
  with self.assertRaises(ConnectionError):self.send(c,guard=guard)
  def slow():time.sleep(.02);return True
  with self.assertRaises(TimeoutError):c.send_print_once('stop','-1',c.control_connection_id(),send_deadline=time.monotonic()+.01,job_guard=slow)
  c._sock.sendall.assert_not_called()
 def test_generic_methods_stay_read_only_and_partial_send_never_retries(self):
  c=self.client()
  with self.assertRaises(ReadOnlyViolation):c.pause_print('-1')
  with self.assertRaises(ReadOnlyViolation):c.publish_web('print','stop',{'taskid':'-1'})
  c._sock.sendall.side_effect=OSError()
  with self.assertRaises(OSError):self.send(c)
  self.assertEqual(c._sock.sendall.call_count,1)

class PrintTelemetryTests(unittest.TestCase):
 def setUp(self):
  self.clock=100;self.p=PrintJobState(lambda:self.clock)
 def report(self,phase='printing',task=-1,file='part.3mf',elapsed=30,epoch='epoch'):
  self.p.receive('info',{'data':{'project':{'state':phase,'task_id':task,'filename':file,'print_time':elapsed}}},epoch)
 def test_pause_resume_keep_identity_but_new_job_and_elapsed_reset_change_it(self):
  self.report();before=self.p.token;self.report('paused');self.assertEqual(self.p.phase,2);self.assertEqual(before,self.p.token)
  self.report();self.assertEqual(before,self.p.token);self.report(elapsed=0);self.assertNotEqual(before,self.p.token)
  before=self.p.token;self.report(task=123);self.assertNotEqual(before,self.p.token)
 def test_missing_task_partial_state_and_ack_do_not_authorize(self):
  self.report(task=None);self.assertEqual(self.p.seen,float('-inf'))
  self.report();seen=self.p.seen;self.clock+=16
  self.p.receive('print',{'state':'done','data':{}},'epoch');self.assertEqual(self.p.seen,seen)
  self.p.receive('print',{'state':'paused','data':{}},'epoch');self.assertEqual(self.p.seen,float('-inf'))
 def test_free_and_natural_end_never_count_as_cancelled(self):
  self.report();self.p.receive('info',{'data':{'state':'free','project':None}},'epoch');self.assertEqual(self.p.phase,0)
  self.report('finished');self.assertEqual(self.p.phase,4)
 def test_matching_explicit_stop_preserves_identity_and_new_print_rotates_it(self):
  self.report();before=self.p.token;self.p.receive('print',{'state':'stoped','data':{'taskid':-1,'filename':'part.3mf','print_time':30}},'epoch');self.assertEqual(self.p.phase,3);self.assertEqual(self.p.token,before)
  self.report();self.assertNotEqual(before,self.p.token)
 def test_idle_boundary_rotates_identity_even_when_next_local_job_looks_identical(self):
  self.report();before=self.p.signature();self.p.receive('info',{'data':{'state':'free','project':None}},'epoch')
  self.report(elapsed=31);self.assertNotEqual(before,self.p.signature())
 def test_transition_preserves_identity_without_refreshing_authority(self):
  self.report();before=self.p.signature();seen=self.p.seen;rev=self.p.revision;self.clock+=1
  self.p.receive('print',{'state':'pausing','data':{}},'epoch');self.assertEqual(self.p.phase,0);self.assertEqual(before,self.p.signature());self.assertEqual(seen,self.p.seen);self.assertEqual(rev,self.p.revision)
  self.report('paused');self.assertEqual(before,self.p.signature());self.assertEqual(self.p.phase,2)
 def test_ack_does_not_erase_received_transition(self):
  self.report();self.p.receive('print',{'state':'resuming','data':{}},'epoch')
  self.p.receive('print',{'state':'done','data':{}},'epoch')
  self.assertEqual(self.p.transition,'resuming');self.assertEqual(self.p.phase,0)
 def test_new_connection_never_reuses_old_context(self):
  self.report();before=self.p.token;self.report(epoch='new');self.assertNotEqual(before,self.p.token)
 def test_all_known_preparation_stages_authorize_only_received_identity(self):
  self.report('init',elapsed=2316);token=self.p.token
  for state in PREPARING_PHASES:
   self.report(state,elapsed=2316);self.assertEqual(self.p.phase,5);self.assertEqual(self.p.token,token);self.assertEqual(self.p.seen,self.clock)
  self.report('printing',elapsed=0);self.assertEqual(self.p.token,token)
 def test_unknown_phase_still_disarms(self):
  self.report();self.report('unknown');self.assertEqual(self.p.phase,0);self.assertEqual(self.p.seen,float('-inf'))
 def test_preparation_and_unknown_states_disarm(self):
  self.report();self.p.receive('print',{'state':'auto_leveling','data':{}},'epoch');self.assertEqual(self.p.seen,float('-inf'));self.assertEqual(self.p.phase,5)

class PrintMonitorTests(unittest.TestCase):
 def test_monitor_history_identity_and_current_epoch_are_required(self):
  with tempfile.TemporaryDirectory() as tmp:
   jobs=[dict(id='job-a',filename='part.3mf',ended_at=None,state='printing')]
   m=Monitor('192.0.2.1',tmp,tmp,SimpleNamespace(jobs=lambda ip:jobs),print_control=True);m.client=SimpleNamespace(mode_id='20025',control_connection_id=lambda:'epoch');m.telemetry.link(True)
   m.telemetry.print_job.receive('info',{'data':{'project':{'task_id':-1,'filename':'part.3mf','state':'printing'}}},'epoch');a=m.print_snapshot();self.assertTrue(a['online']);jobs[0]['id']='job-b';self.assertNotEqual(a['context'],m.print_snapshot()['context'])
   jobs[0]['filename']='other';self.assertIsNone(m.print_snapshot())

 def test_real_s1_leveling_report_is_bound_to_active_history_job(self):
  import json
  fixture={'task_id':-1,'state':'auto_leveling','filename':'test.3mf','print_time':2316,'pause':0}
  with tempfile.TemporaryDirectory() as tmp:
   jobs=[dict(id='new-job',filename='test.3mf',ended_at=None,state='auto_leveling')]
   m=Monitor('192.0.2.1',tmp,tmp,SimpleNamespace(jobs=lambda ip:jobs),print_control=True);m.client=SimpleNamespace(mode_id='20025',control_connection_id=lambda:'epoch');m.telemetry.link(True)
   m.telemetry.print_job.receive('info',{'data':{'state':'busy','project':fixture}},'epoch')
   a=m.print_snapshot();self.assertTrue(a['online']);self.assertEqual(a['light_on'],5);self.assertEqual(a['task_id'],'-1')
   jobs[0]['filename']='old.3mf';self.assertIsNone(m.print_snapshot())

class PrintVisiblePhaseTests(unittest.TestCase):
 def test_explicit_phase_overrides_bridge_printing_without_guessing_from_zero(self):
  t=Telemetry('192.0.2.1');bridge=SimpleNamespace(_state={'print_state':'printing','progress':0})
  for phase,expected in [('auto_leveling','auto_leveling'),('busy','preparing'),('resuming','resuming'),('pausing','pausing'),('stopping','stopping'),('printing','printing')]:
   t.receive('info',{'data':{'project':{'state':phase,'task_id':-1,'filename':'part.3mf'}}},bridge,'epoch')
   self.assertEqual(t.data['print_state'],expected)
  t.receive('print',{'state':'resuming','data':{}},bridge,'epoch')
  self.assertEqual(t.data['print_state'],'resuming')
