"""Authenticated API integration; imported fixture owns fake transports only."""
import hashlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
import uuid

from aiohttp.test_utils import make_mocked_request
from access import Access
from monitor import build_app
import test_reprint_dispatch as fixture_module


class ReprintApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.f=fixture_module.DispatchTests();await self.f.asyncSetUp();self.addCleanup(self.f.doCleanups)
        self.access=Access(self.f.t.name);self.access.account={'username':'fixture'}
        self.access.sessions['owner']={'expires':self.access.clock()+100,'csrf':'fixture-csrf'}
        self.headers={'Cookie':'kobra_session=owner','X-Kobra-CSRF':'fixture-csrf'}
        item=SimpleNamespace(telemetry=SimpleNamespace(snapshot=lambda:{'data':{'printer_name':'Synthetic S1'}}),
                             archive_repeat=SimpleNamespace(enabled=True))
        self.app=build_app(SimpleNamespace(history=self.f.history,reprints=self.f.service,
            monitors={'192.0.2.1':item},start=AsyncMock(),stop=AsyncMock(),read_only=False),self.access)
    async def call(self,body=None,*,headers=None,method='POST',path='/api/reprints'):
        request=make_mocked_request(method,path,headers={'Host':'localhost','Origin':'http://localhost',
            'Content-Type':'application/json',**(self.headers if headers is None else headers)})
        request.json=AsyncMock(return_value=body)
        match=await self.app.router.resolve(request)
        return await self.app.middlewares[0](request,match.handler)
    def prepare(self):return {'action':'prepare','job':self.f.source,'sha256':self.f.sha,'ip':'192.0.2.1',
        'assignments':[{'paint_index':1,'slot':2}],'request_id':str(uuid.uuid4())}
    async def test_owner_csrf_origin_and_machine_scope_before_refresh_or_send(self):
        helper=self.f.history.files.new_client('machine')
        for headers,status in [({},401),({'Authorization':'Bearer '+helper},401),
                ({'Cookie':self.headers['Cookie']},403),({**self.headers,'Origin':'https://evil.invalid'},403)]:
            self.assertEqual((await self.call(self.prepare(),headers=headers)).status,status)
        self.assertEqual((await self.call(method='GET',headers={})).status,401)
        self.f.refresh.assert_not_awaited();self.assertEqual(self.f.transfers,[]);self.assertEqual(self.f.sent,[])
    async def test_catalog_and_preflight_are_reading_only(self):
        result=await self.call(method='GET');self.assertEqual(result.status,200)
        self.assertEqual(result.headers['Cache-Control'],'no-store')
        catalog=json.loads(result.text);self.assertEqual(catalog['jobs'][0]['id'],self.f.source)
        self.assertNotIn('connection_id',result.text);self.assertNotIn('upload_url',result.text)
        result=await self.call({'action':'check','job':self.f.source,'sha256':self.f.sha})
        self.assertEqual(result.status,200);self.assertFalse(json.loads(result.text)['start_authorized'])
        self.assertEqual(self.f.transfers,[]);self.assertEqual(self.f.sent,[])
    async def test_full_confirmed_intent_flow_and_repeated_post_sends_once(self):
        p=json.loads((await self.call(self.prepare())).text)
        u=json.loads((await self.call({'action':'transfer','id':p['id'],'token':p['token']})).text)
        self.assertEqual(u['state'],'uploaded');self.assertEqual(self.f.sent,[])
        body={'action':'start','id':u['id'],'token':u['token'],'bed_clear':True,'material_ready':True,'nozzle_mm':.4}
        result=await self.call(body);self.assertEqual(result.status,200);self.assertEqual(json.loads(result.text)['state'],'awaiting')
        await self.call(body);self.assertEqual(len(self.f.sent),1);self.assertEqual(len(self.f.transfers),1)
    async def test_another_session_disabled_permission_and_extra_fields_never_send(self):
        p=json.loads((await self.call(self.prepare())).text)
        self.access.sessions['other']={'expires':self.access.clock()+100,'csrf':'other'}
        response=await self.call({'action':'transfer','id':p['id'],'token':p['token']},
            headers={'Cookie':'kobra_session=other','X-Kobra-CSRF':'other'})
        self.assertEqual(response.status,400)
        for body in [[],{'action':{}},dict(self.prepare(),url='http://evil.invalid'),dict(self.prepare(),ip='192.0.2.99')]:
            self.assertIn((await self.call(body)).status,(400,403))
        self.f.service.enabled=False
        self.assertEqual((await self.call(self.prepare())).status,403)
        self.assertEqual(self.f.transfers,[]);self.assertEqual(self.f.sent,[])
    async def test_session_revocation_while_waiting_for_refresh_prevents_intent(self):
        async def revoke(ip):self.access.sessions.clear()
        self.f.service.refresh=revoke
        self.assertEqual((await self.call(self.prepare())).status,403)
        self.assertEqual(self.f.service.db.execute('SELECT count(*) FROM archive_dispatches').fetchone()[0],0)


if __name__=='__main__':unittest.main()
