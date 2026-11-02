"""Real HTTP boundary + coordinator, with fake telemetry and a fake sender only."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from aiohttp.test_utils import make_mocked_request
from access import Access
from accounts import write_account
from controls import LightControls
from monitor import build_app, Fleet, Monitor

class ControlApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        write_account(self.tmp.name,'Owner','A synthetic long password!')
        self.access=Access(self.tmp.name)
        self.ip='192.168.250.10'
        self.data=dict(online=True,connection_id='fake-epoch',light_on=False,light_age_s=0,light_revision=1)
        self.writes=[]
        async def sender(ip,on,epoch):
            self.writes.append((ip,on,epoch));self.data.update(light_on=on,light_revision=self.data['light_revision']+1)
        self.controls=LightControls(Path(self.tmp.name)/'control.sqlite3',lambda ip:dict(self.data),sender,enabled=True)
        self.addCleanup(self.controls.close)
        self.item=SimpleNamespace(light_supported=lambda:True,refresh_light=AsyncMock())
        self.service=SimpleNamespace(start=AsyncMock(),stop=AsyncMock(),controls=self.controls,
                                     monitors={self.ip:self.item},read_only=False)
        self.app=build_app(self.service,self.access)
        login=await self.call('/api/session',{'username':'Owner','password':'A synthetic long password!'},headers={})
        self.headers={'Cookie':'kobra_session='+login.cookies['kobra_session'].value,
                      'X-Kobra-CSRF':json.loads(login.text)['csrf']}
    async def call(self,path,body,headers=None,method='POST'):
        request=make_mocked_request(method,path,headers={'Host':'localhost','Content-Type':'application/json',
            'Origin':'http://localhost',**(self.headers if headers is None else headers)})
        request.json=AsyncMock(return_value=body)
        match=await self.app.router.resolve(request)
        return await self.app.middlewares[0](request,match.handler)
    def prepare(self):return dict(action='prepare',ip=self.ip,desired=True,request_id=str(uuid.uuid4()))
    async def test_owner_csrf_origin_and_post_required_before_any_refresh_or_send(self):
        for headers,status in [({},401),({'Cookie':self.headers['Cookie']},403),
                                ({**self.headers,'Origin':'https://evil.invalid'},403)]:
            self.assertEqual((await self.call('/api/controls',self.prepare(),headers)).status,status)
        self.assertEqual((await self.call('/api/controls',{},method='GET')).status,403)
        self.item.refresh_light.assert_not_awaited();self.assertEqual(self.writes,[])
    async def test_complete_confirmed_flow_and_repeated_execute_write_once(self):
        response=await self.call('/api/controls',self.prepare());self.assertEqual(response.status,200)
        prepared=json.loads(response.text);self.assertEqual(self.writes,[])
        body=dict(action='execute',id=prepared['id'],token=prepared['token'])
        first=await self.call('/api/controls',body);second=await self.call('/api/controls',body)
        self.assertEqual(json.loads(first.text)['state'],'confirmed')
        self.assertEqual(json.loads(second.text)['state'],'confirmed');self.assertEqual(len(self.writes),1)
    async def test_unknown_printer_extra_fields_and_wrong_types_never_send(self):
        for body in [dict(self.prepare(),ip='192.168.250.99'),dict(self.prepare(),arbitrary='start'),
                     dict(self.prepare(),desired=1),[],{'action':{}},dict(action='execute',id=[],token='x')]:
            self.assertEqual((await self.call('/api/controls',body)).status,400)
        self.assertEqual(self.writes,[])
    async def test_another_session_cannot_execute_or_cancel_owner_intent(self):
        prepared=json.loads((await self.call('/api/controls',self.prepare())).text)
        login=await self.call('/api/session',{'username':'Owner','password':'A synthetic long password!'},headers={})
        other={'Cookie':'kobra_session='+login.cookies['kobra_session'].value,'X-Kobra-CSRF':json.loads(login.text)['csrf']}
        for body in [dict(action='execute',id=prepared['id'],token=prepared['token']),dict(action='cancel',id=prepared['id'])]:
            self.assertEqual((await self.call('/api/controls',body,other)).status,400)
        self.assertEqual(self.writes,[])
    async def test_disabled_and_bootstrap_installations_cannot_control(self):
        self.controls.enabled=False
        self.assertEqual((await self.call('/api/controls',self.prepare())).status,403)
        self.controls.enabled=True;self.access.account=None
        self.assertEqual((await self.call('/api/controls',self.prepare())).status,403)
        self.assertEqual(self.writes,[])
    async def test_light_assets_use_existing_security_headers_and_mode_is_accurate(self):
        response=await self.call('/api/session',{},method='GET')
        self.assertIs(json.loads(response.text)['read_only'],False)
        response=await self.call('/assets/controls.js',{},headers={},method='GET')
        self.assertEqual(response.status,200)
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertIn("script-src 'self'",response.headers['Content-Security-Policy'])

    async def test_fan_http_requires_owner_allowlist_and_explicit_confirmation(self):
        fan_data=dict(online=True,connection_id='fake-epoch',light_on=0,light_age_s=0,light_revision=1)
        async def send(ip,fan,value,epoch):
            self.writes.append((fan,value));fan_data.update(light_on=value,light_revision=2)
        self.controls.fan_snapshot=lambda ip,fan:dict(fan_data)
        self.controls.fan_sender=send
        self.item.fan_supported=lambda:True;self.item.refresh_fan=AsyncMock()
        body=dict(action='prepare_fan',ip=self.ip,fan='part_fan',desired=40,request_id=str(uuid.uuid4()))
        for headers in ({},{'Cookie':self.headers['Cookie']},{**self.headers,'Origin':'https://evil.invalid'}):
            self.assertNotEqual((await self.call('/api/controls',body,headers)).status,200)
        self.item.refresh_fan.assert_not_awaited()
        for change in ({'fan':'arbitrary'},{'desired':True},{'desired':101},{'ip':'192.0.2.99'}):
            self.assertEqual((await self.call('/api/controls',{**body,**change})).status,400)
        prepared=json.loads((await self.call('/api/controls',body)).text)
        self.assertFalse(self.writes)
        result=await self.call('/api/controls',dict(action='execute',id=prepared['id'],token=prepared['token']))
        self.assertEqual(json.loads(result.text)['state'],'confirmed');self.assertEqual(self.writes,[('part_fan',40)])

    async def test_speed_http_binds_current_job_context_and_requires_owner(self):
        data=dict(online=True,connection_id='fake-epoch',light_on=2,light_age_s=0,light_revision=1,context='a'*64)
        async def send(ip,mode,epoch,context):
            self.writes.append((mode,context));data.update(light_on=mode,light_revision=2)
        self.controls.speed_snapshot=lambda ip:dict(data);self.controls.speed_sender=send
        self.item.speed_supported=lambda:True;self.item.refresh_speed=AsyncMock();self.item.speed_snapshot=lambda:dict(data)
        body=dict(action='prepare_speed',ip=self.ip,desired=3,context='a'*64,request_id=str(uuid.uuid4()))
        for headers in ({},{'Cookie':self.headers['Cookie']},{**self.headers,'Origin':'https://evil.invalid'}):
            self.assertNotEqual((await self.call('/api/controls',body,headers)).status,200)
        self.item.refresh_speed.assert_not_awaited()
        for change in ({'desired':True},{'desired':4},{'context':'b'*64},{'ip':'192.0.2.99'},{'taskid':'-1'}):
            self.assertEqual((await self.call('/api/controls',{**body,**change})).status,400)
        prepared=json.loads((await self.call('/api/controls',body)).text);self.assertFalse(self.writes)
        result=await self.call('/api/controls',dict(action='execute',id=prepared['id'],token=prepared['token']))
        self.assertEqual(json.loads(result.text)['state'],'confirmed');self.assertEqual(self.writes,[(3,'a'*64)])

class ControlFleetTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_read_only_and_configured_printer_allowlist(self):
        for enabled in (None,['192.168.250.10']):
            with tempfile.TemporaryDirectory() as tmp:
                runtime=Path(tmp)/'run';runtime.mkdir();data=Path(tmp)/'data';data.mkdir()
                fleet=Fleet(['192.168.250.10','192.168.250.11'],runtime,data,light_control_ips=enabled)
                result=fleet.snapshot()
                self.assertEqual(result['read_only'],enabled is None)
                self.assertEqual([p['light_control']['enabled'] for p in result['printers']],
                                 [enabled is not None,False])
                if fleet.controls:fleet.controls.close()
                fleet.history.close()
    async def test_only_received_light_report_from_current_socket_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            item=Monitor('192.168.250.10',tmp,tmp,light_control=True)
            item.client=SimpleNamespace(mode_id='20025',control_connection_id=lambda:'epoch-2')
            item.telemetry.link(True)
            item.telemetry.receive('light',{'data':{'type':2,'status':1}},None,'epoch-1')
            self.assertFalse(item.light_snapshot()['online'])
            item.telemetry.receive('light',{'data':{'type':2,'status':0}},None,'epoch-2')
            self.assertTrue(item.light_snapshot()['online']);self.assertEqual(item.light_snapshot()['light_revision'],2)
            self.assertIs(item.light_snapshot()['light_on'],False)

    async def test_speed_only_allowlist_is_explicit_and_idle_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=Path(tmp)/'run';runtime.mkdir();data=Path(tmp)/'data';data.mkdir()
            fleet=Fleet(['192.168.250.10','192.168.250.11'],runtime,data,speed_control_ips=['192.168.250.10'])
            result=fleet.snapshot();self.assertFalse(result['read_only']);self.assertTrue(result['controls']['speed_mode'])
            self.assertEqual([p['speed_control']['enabled'] for p in result['printers']],[True,False])
            self.assertFalse(result['printers'][0]['speed_control']['available'])
            fleet.controls.close();fleet.history.close()
