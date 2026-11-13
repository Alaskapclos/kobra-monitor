import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from monitor import Fleet,Monitor
from configuration import load_config
from types import SimpleNamespace
from access import Access
from accounts import write_account
from monitor import build_app
from aiohttp.test_utils import make_mocked_request

class FleetOrderTests(unittest.IsolatedAsyncioTestCase):
    async def test_order_persists_snapshot_matches_and_sessions_are_not_restarted(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp)/'data';data.mkdir();ips=['192.168.1.10','192.168.1.11'];fleet=Fleet(ips,tmp,data)
            original=dict(fleet.monitors)
            with patch.object(Monitor,'start',new=AsyncMock()) as start,patch.object(Monitor,'stop',new=AsyncMock()) as stop:
                await fleet.reorder(list(reversed(ips)))
                self.assertEqual(fleet.snapshot()['ips'],list(reversed(ips)))
                self.assertEqual([p['ip'] for p in fleet.snapshot()['printers']],list(reversed(ips)))
                self.assertEqual(load_config(data),list(reversed(ips)))
                for ip in ips:self.assertIs(fleet.monitors[ip],original[ip])
                start.assert_not_awaited();stop.assert_not_awaited()
            fleet.reprints.close();fleet.history.close()
            runtime=Path(tmp)/'next';runtime.mkdir()
            restarted=Fleet(load_config(data),runtime,data)
            self.assertEqual([p['ip'] for p in restarted.snapshot()['printers']],list(reversed(ips)))
            restarted.reprints.close();restarted.history.close()
    async def test_only_exact_current_permutation_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp)/'data';data.mkdir();fleet=Fleet(['192.168.1.10','192.168.1.11'],tmp,data)
            for ips in [[],None,['192.168.1.10'],['192.168.1.10','192.168.1.10'],['192.168.1.10','192.168.1.12'],[{},'192.168.1.11']]:
                with self.assertRaises(ValueError):await fleet.reorder(ips)
            self.assertFalse((data/'config.json').exists());fleet.reprints.close();fleet.history.close()

class OrderAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_order_requires_login_csrf_and_same_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_account(tmp,'Test','A long test password!')
            access=Access(tmp)
            service=SimpleNamespace(start=AsyncMock(),stop=AsyncMock(),reorder=AsyncMock(),ips=['192.168.1.11','192.168.1.10'])
            app=build_app(service,access)
            async def call(path,body,headers=None):
                request=make_mocked_request('POST',path,headers={'Host':'localhost','Content-Type':'application/json','Origin':'http://localhost',**(headers or {})})
                request.json=AsyncMock(return_value=body)
                match=await app.router.resolve(request)
                return await app.middlewares[0](request,match.handler)
            body={'printer_ips':service.ips}
            self.assertEqual((await call('/api/order',body)).status,401)
            login=await call('/api/session',{'username':'Test','password':'A long test password!'})
            headers={'Cookie':'kobra_session='+login.cookies['kobra_session'].value,'X-Kobra-CSRF':json.loads(login.text)['csrf']}
            bad=dict(headers);bad.pop('X-Kobra-CSRF')
            self.assertEqual((await call('/api/order',body,bad)).status,403)
            bad=dict(headers);bad['Origin']='https://evil.invalid'
            self.assertEqual((await call('/api/order',body,bad)).status,403)
            service.reorder.assert_not_awaited()
            self.assertEqual((await call('/api/order',body,headers)).status,200)
            service.reorder.assert_awaited_once_with(service.ips)

if __name__=='__main__':unittest.main()
