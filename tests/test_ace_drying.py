"""Climate evidence, exact heater packets and persisted no-retry intent tests."""
import asyncio
import copy
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock,AsyncMock
import sys
sys.path[:0]=[str(Path(__file__).resolve().parent.parent),str(Path(__file__).resolve().parent.parent/'vendor/kobra-bridge')]
from ace_climate import AceClimate,drying_options
from controls import LightControls
from drying_control import DryingControls,DryingAdapter
from light_transport import LightControlClient
from test_light_transport import decode
from monitor import Fleet,Telemetry,build_app
from access import Access
from aiohttp.test_utils import make_mocked_request


class ClimateTests(unittest.TestCase):
    def setUp(self):self.now=100;self.c=AceClimate(lambda:self.now)
    def receive(self,boxes,**extra):self.c.receive(dict(multi_color_box=boxes,**extra),'epoch')
    def units(self,epoch='epoch',online=True):return self.c.public(epoch,online)
    def test_absence_is_not_off_and_zero_is_measured(self):
        self.receive([{'id':0,'temperature':0,'humidity':0}]);u=self.units()[0]
        self.assertEqual(u['current_temp'],0);self.assertEqual(u['humidity'],0);self.assertNotIn('status',u)
        self.receive([{'id':0,'drying_status':{'status':0}}]);self.assertEqual(self.units()[0]['status'],0)
    def test_fields_have_independent_ages_and_invalid_does_not_restore_previous(self):
        self.receive([{'id':0,'temperature':32,'drying_status':{'status':1}}]);self.now+=30
        self.receive([{'id':0,'humidity':40}]);u=self.units()[0]
        self.assertEqual(u['ages']['current_temp'],30);self.assertEqual(u['ages']['humidity'],0)
        self.receive([{'id':0,'temperature':float('nan'),'drying_status':{'status':True}}]);u=self.units()[0]
        self.assertIsNone(u['current_temp']);self.assertIsNone(u['status'])
    def test_each_box_is_independent_and_ambiguous_top_level_not_guessed(self):
        self.receive([{'id':0,'temperature':31},{'id':1,'temperature':42,'humidity':22}],drying_status={'status':1})
        a,b=self.units();self.assertEqual((a['current_temp'],b['current_temp']),(31,42));self.assertNotIn('humidity',a);self.assertNotIn('status',a)
    def test_removal_duplicate_reconnect_and_change_back_invalidate_identity(self):
        self.receive([{'id':0,'drying_status':{'status':0}}]);first=self.units()[0]['configuration']
        for state in (1,0):self.receive([{'id':0,'drying_status':{'status':state}}])
        self.assertNotEqual(first,self.units()[0]['configuration']);self.assertFalse(self.units('new')[0]['current']['status'])
        self.assertFalse(self.units(online=False)[0]['current']['status'])
        self.receive([{'id':0},{'id':0}]);self.assertEqual(self.units(),[])
        self.receive([]);self.assertEqual(self.units(),[])
    def test_bounds_are_explicit_no_implicit_preset(self):
        for args in [(1,45,240),(True,None,240),(True,56,240),(True,45,9),(True,45,1441),(False,45,240)]:
            with self.assertRaises(ValueError):drying_options(*args)
        self.assertEqual(drying_options(False),{'status':0})
        self.assertEqual(drying_options(True,65,60,maximum=65)['target_temp'],65)
        with self.assertRaises(ValueError):drying_options(True,66,60,maximum=65)


class DryingTransportTests(unittest.TestCase):
    def client(self,enabled=True,model='20025'):
        c=LightControlClient('192.0.2.1','synthetic','synthetic',model,'fixture',drying_control_enabled=enabled)
        c._sock=Mock();c._running=True;c._sock_gen=7;return c
    def send(self,c,options=None,epoch=None,guard=lambda:True):
        return c.send_drying_once(1,options or drying_options(True,45,240),epoch or c.control_connection_id(),send_deadline=time.monotonic()+1,job_guard=guard)
    def test_exact_ace_only_slicer_packet_and_no_other_heaters(self):
        c=self.client();self.send(c);topic,p=decode(c._sock.sendall.call_args.args[0])
        self.assertEqual(topic,'anycubic/anycubicCloud/v1/slicer/printer/20025/fixture/multiColorBox')
        self.assertEqual(p['action'],'setDry');self.assertEqual(p['data'],{'multi_color_box':[{'id':1,'drying_status':drying_options(True,45,240)}]})
        self.send(c,{'status':0});self.assertEqual(c._sock.sendall.call_count,2)
    def test_permission_model_epoch_guard_options_and_generic_write_blocked(self):
        for c in (self.client(False),self.client(model='20030')):
            with self.assertRaises((ValueError,PermissionError)):self.send(c)
            c._sock.sendall.assert_not_called()
        c=self.client()
        for opts in ({'status':True},{'status':0,'target_temp':45},{'status':1,'target_temp':65,'duration':10,'remain_time':10}):
            with self.assertRaises(ValueError):self.send(c,opts)
        with self.assertRaises(ConnectionError):self.send(c,epoch='changed')
        with self.assertRaises(ConnectionError):self.send(c,guard=lambda:False)
        with self.assertRaises(PermissionError):c.publish('multiColorBox','setDry',{'status':1},0)
        c._sock.sendall.assert_not_called()
    def test_higher_limit_requires_explicit_device_capability(self):
        c=self.client();opts=drying_options(True,65,60,maximum=65)
        with self.assertRaises(ValueError):self.send(c,opts)
        c.drying_max_temperature=65;self.send(c,opts)
        self.assertEqual(decode(c._sock.sendall.call_args.args[0])[1]['data']['multi_color_box'][0]['drying_status']['target_temp'],65)
    def test_partial_write_is_not_retried(self):
        c=self.client();c._sock.sendall.side_effect=OSError('synthetic partial write')
        with self.assertRaises(OSError):self.send(c)
        self.assertEqual(c._sock.sendall.call_count,1)


class DryingIntentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.now=100;self.sent=[]
        self.controls=LightControls(Path(self.t.name)/'history.sqlite3',lambda ip:None,AsyncMock(),enabled=True);self.addCleanup(self.controls.close)
        self.archive=SimpleNamespace(busy=lambda ip,control=None:False)
        self.state={'id':0,'status':0,'target_temp':0,'duration':0,'configuration':'first','ages':{'status':0,'target_temp':0,'duration':0},'current':{'status':True,'target_temp':True,'duration':True},'revision':1,'connection':'epoch','context':'material-job','online':True}
        async def sender(row,guard):
            self.assertTrue(guard());self.sent.append(row['id']);self.state.update(json.loads(row['options']),revision=self.state['revision']+1,configuration='reported-new')
        self.sender=sender
        self.service=DryingControls(Path(self.t.name)/'history.sqlite3',lambda ip,box:copy.deepcopy(self.state) if ip=='192.0.2.1' and box==0 else None,sender,self.controls,self.archive,monotonic=lambda:self.now,confirmation_timeout=.02)
        self.addCleanup(self.service.close)
    async def prepare(self,**changes):
        args=dict(actor='owner',ip='192.0.2.1',box=0,on=True,temperature=45,duration=240,request_id=str(uuid.uuid4()));args.update(changes);return await self.service.prepare(**args)
    async def execute(self,p,**kwargs):return await self.service.action('owner',p['id'],'execute',p['token'],**kwargs)
    async def test_prepare_cancel_and_duplicate_execute_never_replay(self):
        p=await self.prepare();self.assertEqual(self.sent,[]);r=await self.execute(p);self.assertEqual(r['state'],'confirmed');await self.execute(p);self.assertEqual(len(self.sent),1)
        p=await self.prepare(on=False,temperature=None,duration=None);await self.service.action('owner',p['id'],'cancel');await self.execute(p);self.assertEqual(len(self.sent),1)
    async def test_expiry_auth_actor_or_changed_context_never_send(self):
        p=await self.prepare()
        with self.assertRaises(ValueError):await self.service.action('other',p['id'],'execute',p['token'])
        with self.assertRaises(PermissionError):await self.execute(p,authorized=lambda:False)
        self.state['configuration']='changed-back'
        with self.assertRaises(ValueError):await self.execute(p)
        p=await self.prepare();self.now+=21;self.assertEqual((await self.execute(p))['state'],'expired');self.assertEqual(self.sent,[])
    async def test_unknown_old_or_offline_cannot_prepare(self):
        for key,value in [('status',None),('online',False),('ages',{'status':16}),('current',{'status':False})]:
            before=self.state[key];self.state[key]=value
            with self.assertRaises(ValueError):await self.prepare()
            self.state[key]=before
        with self.assertRaises(ValueError):await self.prepare(ip='192.0.2.99')
    async def test_drying_reservation_blocks_archive_and_controls_but_not_stop(self):
        await self.prepare();self.assertTrue(self.archive.busy('192.0.2.1'));self.assertTrue(self.controls.external_busy('192.0.2.1','part_fan'));self.assertFalse(self.controls.external_busy('192.0.2.1','print_stop'))
    async def test_configured_ace2_limit_cannot_be_overridden_by_request(self):
        with self.assertRaises(ValueError):await self.prepare(temperature=65)
        self.state['max_temperature']=65;p=await self.prepare(temperature=65)
        self.assertEqual((await self.execute(p))['state'],'confirmed')
        with self.assertRaises(ValueError):await self.prepare(temperature=66)
    async def test_same_state_and_late_or_missing_confirmation_never_claim_success(self):
        p=await self.prepare(on=False,temperature=None,duration=None);self.assertEqual(p['state'],'unchanged')
        async def sender(row,guard):self.sent.append(row['id'])
        self.service.sender=sender;p=await self.prepare();r=await self.execute(p);self.assertEqual(r['state'],'uncertain');await self.execute(p);self.assertEqual(len(self.sent),1)


class DryingApiTests(DryingIntentTests):
    async def asyncSetUp(self):
        await super().asyncSetUp();self.access=Access(self.t.name);self.access.account={'username':'fixture'}
        self.access.sessions['owner']={'expires':self.access.clock()+100,'csrf':'fixture'}
        self.app=build_app(SimpleNamespace(drying=self.service,start=AsyncMock(),stop=AsyncMock(),read_only=False),self.access)
    async def call(self,body,headers):
        r=make_mocked_request('POST','/api/drying',headers={'Host':'localhost','Origin':'http://localhost','Content-Type':'application/json',**headers});r.json=AsyncMock(return_value=body)
        match=await self.app.router.resolve(r);return await self.app.middlewares[0](r,match.handler)
    async def test_origin_csrf_owner_and_strict_fields_before_send(self):
        b={'action':'prepare','ip':'192.0.2.1','box':0,'on':True,'temperature':45,'duration':240,'request_id':str(uuid.uuid4())}
        for headers,code in [({},401),({'Cookie':'kobra_session=owner'},403),({'Cookie':'kobra_session=owner','X-Kobra-CSRF':'fixture','Origin':'https://evil.invalid'},403)]:self.assertEqual((await self.call(b,headers)).status,code)
        headers={'Cookie':'kobra_session=owner','X-Kobra-CSRF':'fixture'}
        self.assertEqual((await self.call(dict(b,arbitrary_command='anything'),headers)).status,400)
        self.assertEqual((await self.call(b,headers)).status,200);self.assertEqual(self.sent,[])


if __name__=='__main__':unittest.main()
