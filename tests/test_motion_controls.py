"""Manual motion safety: fake sockets and reports only; never move a real printer."""
import asyncio,json,tempfile,time,uuid,unittest
from pathlib import Path
import sys
from unittest.mock import Mock,AsyncMock
sys.path[:0]=[str(Path(__file__).resolve().parent.parent),str(Path(__file__).resolve().parent.parent/'vendor/kobra-bridge')]
from motion_control import MotionState,motion_payload,MOTION_ACTIONS
from controls import LightControls,ControlRefused
from light_transport import LightControlClient
from test_light_transport import decode
import test_control_api as api_tests

class MotionStateTests(unittest.TestCase):
 def test_only_explicit_current_idle_authorizes(self):
  m=MotionState(lambda:100)
  for state,project in [('busy',None),('free',{}),('error',None),('free',{'state':'paused'}),('free',{'state':'auto_leveling'})]:
   m.receive('info',{'data':{'state':state,'project':project}},'e');self.assertFalse(m.snapshot('e',True)['online'])
  m.receive('info',{'data':{'state':'free','project':None}},'e');a=m.snapshot('e',True);self.assertTrue(a['online'])
  self.assertFalse(m.snapshot('new',True)['online']);self.assertFalse(m.snapshot('e',False)['online'])
  m.receive('print',{'state':'printing','data':{}},'e');self.assertFalse(m.snapshot('e',True)['online'])
  m.receive('info',{'data':{'state':'free','project':None}},'e');self.assertNotEqual(a['context'],m.snapshot('e',True)['context'])
 def test_errors_and_partial_info_revoke_idle(self):
  m=MotionState(lambda:100)
  for report in [{'data':{}},{'code':500,'data':{'state':'free'}},{'data':{'state':'busy'}}]:
   m.receive('info',{'data':{'state':'free'}},'e');m.receive('info',report,'e');self.assertFalse(m.snapshot('e',True)['online'])
 def test_payload_directions_and_home_are_fixed(self):
  for action,axis in MOTION_ACTIONS.items():
   if action.startswith('home_'):self.assertEqual(motion_payload(action,1),{'axis':axis,'move_type':2,'distance':0})
   else:
    for step in [1,15,50]:
     for sign in [-1,1]:self.assertEqual(motion_payload(action,sign*step),{'axis':axis,'move_type':int(sign<0 if action=='axis_z' else sign>0),'distance':step})
  for action,value in [('axis_x',0),('axis_y',51),('axis_z',True),('axis_z',1.0),('home_xy',50),('motors_off',1),('gcode',1)]:
   with self.assertRaises(ValueError):motion_payload(action,value)

class MotionCycleTests(unittest.TestCase):
 def test_regular_print_preparation_revokes_manual_permission_cycle(self):
  m=MotionState(lambda:100);idle={'data':{'state':'free','project':None}}
  m.receive('info',idle,'e');before=m.print_cycle
  m.receive('axis',{'state':'done','data':{}},'e');m.receive('info',idle,'e');self.assertEqual(before,m.print_cycle)
  m.receive('info',{'data':{'state':'busy','project':{'state':'auto_leveling','filename':'part.3mf'}}},'e');new=m.print_cycle;self.assertNotEqual(before,new)
  m.receive('print',{'state':'printing','data':{}},'e');self.assertEqual(new,m.print_cycle)
  m.receive('info',idle,'e');self.assertEqual(new,m.print_cycle)

class MotionIntentTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.now=100
  self.data=dict(online=True,connection_id='e',light_on=0,light_revision=1,light_age_s=0,context='a'*64,print_cycle='cycle-a');self.sent=[]
  async def send(*args):self.sent.append(args)
  self.c=LightControls(Path(self.tmp.name)/'db',lambda ip:None,send,enabled=True,motion_snapshot=lambda ip:dict(self.data),motion_sender=send,monotonic=lambda:self.now);self.addCleanup(self.c.close)
 async def prepare(self,action='axis_x',value=1):return await self.c.prepare('owner','192.0.2.1',value,str(uuid.uuid4()),control=action)
 async def test_single_send_is_not_false_physical_confirmation_and_cooldown(self):
  p=await self.prepare();r=await self.c.execute('owner',p['id'],p['token']);self.assertEqual(r['state'],'sent')
  await self.c.execute('owner',p['id'],p['token']);self.assertEqual(len(self.sent),1)
  with self.assertRaises(ControlRefused):await self.prepare()
  self.now+=5;self.assertEqual((await self.prepare())['state'],'prepared')
 async def test_home_has_longer_wait(self):
  p=await self.prepare('home_z');await self.c.execute('owner',p['id'],p['token']);self.assertEqual(self.c.motion_wait('192.0.2.1'),30)
 async def test_changed_state_context_epoch_and_cancel_never_send(self):
  for update in [dict(online=False),dict(context='b'*64),dict(connection_id='new'),dict(light_age_s=16)]:
   self.data.update(online=True,context='a'*64,connection_id='e',light_age_s=0);p=await self.prepare();self.data.update(update)
   with self.assertRaises(ControlRefused):await self.c.execute('owner',p['id'],p['token'])
  self.data.update(online=True,context='a'*64,connection_id='e',light_age_s=0);p=await self.prepare();await self.c.cancel('owner',p['id']);await self.c.execute('owner',p['id'],p['token']);self.assertEqual(self.sent,[])
 async def test_partial_send_timeout_is_uncertain_and_not_retried(self):
  async def fail(*args):self.sent.append(args);raise OSError('partial')
  self.c.motion_sender=fail;p=await self.prepare();r=await self.c.execute('owner',p['id'],p['token']);self.assertEqual(r['state'],'uncertain');self.assertGreater(self.c.motion_wait('192.0.2.1'),0);self.assertEqual(len(self.sent),1)

 async def test_motion_wait_never_blocks_print_abort(self):
  from print_job_control import PRINT_ACTIONS
  async def send(*args):pass
  self.c.print_sender=send
  self.c.print_snapshot=lambda ip:dict(self.data,light_on=1)
  self.c.motion_deadlines['192.0.2.1']=self.now+60
  p=await self.c.prepare('owner','192.0.2.1',3,str(uuid.uuid4()),control='print_stop')
  self.assertEqual(p['state'],'prepared')

class MotionTransportTests(unittest.TestCase):
 def client(self,enabled=True):
  c=LightControlClient('127.0.0.1',1,'test-device','20025','u','p',motion_control_enabled=enabled);c._running=True;c._sock=Mock();return c
 def test_narrow_frame_and_guard(self):
  c=self.client();c.send_motion_once('axis_x',-15,c.control_connection_id(),send_deadline=time.monotonic()+2,job_guard=lambda:True)
  topic,frame=decode(c._sock.sendall.call_args[0][0]);self.assertEqual(frame['type'],'axis');self.assertEqual(frame['action'],'move');self.assertEqual(frame['data'],{'axis':1,'move_type':0,'distance':15})
 def test_disabled_or_revoked_guard_never_writes(self):
  for enabled in [False,True]:
   c=self.client(enabled)
   with self.assertRaises((PermissionError,ConnectionError)):c.send_motion_once('home_xy',1,c.control_connection_id(),send_deadline=time.monotonic()+2,job_guard=lambda:False)
   c._sock.sendall.assert_not_called()

class MotionAPITests(unittest.IsolatedAsyncioTestCase):
 call=api_tests.ControlApiTests.call
 async def asyncSetUp(self):
  await api_tests.ControlApiTests.asyncSetUp(self);self.item.motion_supported=lambda:True;self.item.refresh_motion=AsyncMock();self.motion=dict(online=True,connection_id='e',light_on=0,light_revision=1,light_age_s=0,context='a'*64,print_cycle='cycle-a')
  self.item.motion_snapshot=lambda:dict(self.motion);self.controls.motion_snapshot=lambda ip:dict(self.motion)
  async def send(*args):self.writes.append(args)
  self.controls.motion_sender=send
 def motion_body(self):return dict(action='prepare_motion',ip=self.ip,operation='axis_x',desired=1,context='a'*64,present=True,request_id=str(uuid.uuid4()))
 async def test_motion_presence_and_exact_fields_required(self):
  for b in [dict(self.motion_body(),present=False),dict(self.motion_body(),present='yes'),dict(self.motion_body(),desired=500),dict(self.motion_body(),gcode='G1 X10')]:self.assertEqual((await self.call('/api/controls',b)).status,400)
  self.assertEqual(self.writes,[])
 async def test_motion_live_refresh_and_actual_idle_recheck(self):
  b=self.motion_body();p=json.loads((await self.call('/api/controls',b)).text);self.item.refresh_motion.assert_awaited();self.assertEqual(p['state'],'prepared')
  self.motion['online']=False;self.assertEqual((await self.call('/api/controls',dict(action='execute',id=p['id'],token=p['token']))).status,400);self.assertEqual(self.writes,[])
 async def test_motion_full_api_flow_never_claims_completed(self):
  p=json.loads((await self.call('/api/controls',self.motion_body())).text)
  b=dict(action='execute',id=p['id'],token=p['token']);r=json.loads((await self.call('/api/controls',b)).text)
  self.assertEqual(r['state'],'sent');await self.call('/api/controls',b);self.assertEqual(len(self.writes),1)
 async def test_motion_asset_is_public_but_motion_endpoint_is_protected(self):
  self.assertEqual((await self.call('/assets/motion-controls.js',{},headers={},method='GET')).status,200)
  self.assertEqual((await self.call('/api/controls',self.motion_body(),headers={})).status,401)

 async def test_first_confirmed_axis_grants_only_same_actor_printer_and_print_cycle(self):
  p=json.loads((await self.call('/api/controls',self.motion_body())).text)
  r=json.loads((await self.call('/api/controls',dict(action='execute',id=p['id'],token=p['token']))).text)
  self.assertTrue(r['motion_confirmed']);self.controls.motion_deadlines.clear()
  next_body=dict(self.motion_body(),present=False)
  p=json.loads((await self.call('/api/controls',next_body)).text);self.assertEqual(p['state'],'prepared');await self.call('/api/controls',dict(action='cancel',id=p['id']))
  self.motion['context']='b'*64;self.motion['print_cycle']='cycle-b'
  self.assertEqual((await self.call('/api/controls',dict(self.motion_body(),present=False,context='b'*64))).status,400)
  self.motion.update(context='a'*64,print_cycle='cycle-a')
  self.assertEqual((await self.call('/api/controls',dict(self.motion_body(),operation='home_xy',present=False))).status,400)
 async def test_new_login_requires_new_presence_confirmation(self):
  p=json.loads((await self.call('/api/controls',self.motion_body())).text);await self.call('/api/controls',dict(action='execute',id=p['id'],token=p['token']));self.controls.motion_deadlines.clear()
  login=await self.call('/api/session',{'username':'Owner','password':'A synthetic long password!'},headers={})
  other={'Cookie':'kobra_session='+login.cookies['kobra_session'].value,'X-Kobra-CSRF':json.loads(login.text)['csrf']}
  self.assertEqual((await self.call('/api/controls',dict(self.motion_body(),present=False),headers=other)).status,400)
