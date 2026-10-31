# SPDX-License-Identifier: GPL-3.0-only
import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from aiohttp.test_utils import make_mocked_request
from history import History
from notifications import Notifications, preferences, subscription, deliver
from monitor import build_app
from access import Access


def info(endpoint='https://web.push.apple.com/Qfixture'):
    key=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    b64=lambda data:base64.urlsafe_b64encode(data).decode().rstrip('=')
    return {'endpoint':endpoint,'keys':{'p256dh':b64(key),'auth':b64(b'0123456789abcdef')}}


PREFS={'completed':True,'errors':True,'disconnect':True,'delay_seconds':180}


class NotificationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.now=10000
        self.history=History(Path(self.tmp.name)/'history.sqlite3',clock=lambda:self.now)
        self.sender=Mock(return_value=201)
        self.service=Notifications(self.history,self.tmp.name,lambda:{'192.168.1.10':'Drucker Eins'},lambda:self.now,self.sender)
        self.id=self.service.subscribe(info(),'Fixture-Handy',PREFS,'https://monitor.example.test')

    def tearDown(self):self.history.close();self.tmp.cleanup()

    def event(self,kind,ip='192.168.1.10',details=None,at=None):
        with self.history.lock:
            self.history.db.execute('INSERT INTO events(ip,job_id,at,kind,details) VALUES(?,?,?,?,?)',(ip,'a'*32,self.now if at is None else at,kind,json.dumps(details or {})))
            self.history.db.commit()

    async def test_only_confirmed_terminal_events_notify_and_never_include_file_or_ip(self):
        for kind in ('active_job_discovered','state','unobserved_end'):self.event(kind,details={'filename':'private.gcode'})
        self.service.collect();await self.service.flush();self.sender.assert_not_called()
        self.event('completed');self.service.collect();await self.service.flush()
        self.sender.assert_called_once();payload=self.sender.call_args.args[1]
        self.assertEqual(payload['title'],'Druck abgeschlossen')
        self.assertIn('Drucker Eins',payload['body']);self.assertNotIn('192.168',json.dumps(payload));self.assertNotIn('private',json.dumps(payload))
        self.service.collect();await self.service.flush();self.assertEqual(self.sender.call_count,1)

    async def test_cancelled_is_distinct_from_success(self):
        self.event('cancelled');self.service.collect();await self.service.flush()
        self.assertEqual(self.sender.call_args.args[1]['title'],'Druck abgebrochen')

    async def test_short_disconnect_suppressed_and_long_disconnect_once(self):
        self.event('disconnected');self.service.collect();self.now+=179;self.service.collect();await self.service.flush();self.sender.assert_not_called()
        self.event('connected');self.service.collect();self.now+=1;self.event('disconnected');self.service.collect();self.now+=181;self.service.collect();await self.service.flush()
        self.assertEqual(self.sender.call_count,1);self.assertIn('unbekannt',self.sender.call_args.args[1]['body'])
        self.now+=8*86400;self.service.collect();await self.service.flush();self.service.collect();await self.service.flush();self.assertEqual(self.sender.call_count,1)

    async def test_reconnected_cancels_pending_retry(self):
        self.sender.return_value=503;self.event('disconnected');self.service.collect();self.now+=181;self.service.collect();await self.service.flush()
        self.event('connected');self.service.collect();self.now+=60;await self.service.flush();self.assertEqual(self.sender.call_count,1)

    async def test_errors_deduplicate_but_new_error_or_later_incident_not_lost(self):
        for _ in range(5):self.event('printer_error',details={'code':42,'state':'paused','message':'secret'})
        self.event('printer_error',details={'code':43,'state':'error'});self.service.collect();await self.service.flush();self.assertEqual(self.sender.call_count,2)
        self.now+=901;self.event('printer_error',details={'code':42,'state':'paused'});self.service.collect();await self.service.flush();self.assertEqual(self.sender.call_count,3)

    async def test_restart_preserves_cursor_queue_and_outage_grace(self):
        self.event('disconnected');self.service.collect();key=self.service.public_key();self.now+=181
        self.service=Notifications(self.history,self.tmp.name,lambda:{'192.168.1.10':'Drucker Eins'},lambda:self.now,self.sender)
        self.assertEqual(key,self.service.public_key());self.service.collect();await self.service.flush();self.assertEqual(self.sender.call_count,1)
        self.service.collect();await self.service.flush();self.assertEqual(self.sender.call_count,1)

    async def test_old_events_and_other_printers_do_not_notify(self):
        self.event('completed',at=self.now-3601);self.event('completed',ip='192.168.1.99');self.service.collect();await self.service.flush();self.sender.assert_not_called()

    async def test_preferences_are_per_device(self):
        self.service.remove(self.id)
        self.service.subscribe(info(),'No finishes',{**PREFS,'completed':False},'https://monitor.example.test')
        self.event('completed');self.service.collect();await self.service.flush();self.sender.assert_not_called()
        self.event('printer_error');self.service.collect();await self.service.flush();self.sender.assert_called_once()

    async def test_retry_limited_and_gone_subscription_removed(self):
        self.sender.return_value=503;self.event('completed');self.service.collect()
        for delay in (0,31,121):self.now+=delay;await self.service.flush()
        self.assertEqual(self.sender.call_count,3);self.now+=1000;await self.service.flush();self.assertEqual(self.sender.call_count,3)
        self.sender.return_value=410;self.event('cancelled');self.service.collect();await self.service.flush();self.assertEqual(self.service.state()['devices'],[])

    async def test_expired_pending_message_not_sent(self):
        self.event('completed');self.service.collect();self.now+=3601;self.service.collect();await self.service.flush();self.sender.assert_not_called()

    async def test_explicit_test_is_rate_limited_and_remove_cancels_queue(self):
        self.service.test(self.id)
        with self.assertRaises(ValueError):self.service.test(self.id)
        self.service.remove(self.id);await self.service.flush();self.sender.assert_not_called()

    def test_public_state_has_no_subscriptions_or_private_keys(self):
        value=json.dumps(self.service.state());self.assertNotIn('endpoint',value);self.assertNotIn('p256dh',value);self.assertNotIn('pem',value)
        if os.name!='nt':self.assertEqual(self.service.key_path.stat().st_mode&0o777,0o600)

    def test_missing_key_with_registered_devices_fails_closed(self):
        self.service.key_path.unlink()
        with self.assertRaises(ValueError):self.service.public_key()

    def test_subscription_reenrollment_does_not_duplicate_device(self):
        self.assertEqual(self.service.subscribe(info(),'Renamed',PREFS,'https://monitor.example.test'),self.id)
        self.assertEqual(len(self.service.state()['devices']),1)

    def test_provider_boundary_blocks_private_hosts_lookalikes_and_bad_keys(self):
        for url in ('http://web.push.apple.com/p','https://127.0.0.1/p','https://192.168.1.10/p','https://web.push.apple.com.evil.test/p','https://fcm.googleapis.com:444/p','https://user:pw@fcm.googleapis.com/p','https://fcm.googleapis.com/p#frag'):
            with self.subTest(url=url),self.assertRaises(ValueError):subscription(info(url))
        value=info();value['keys']['auth']='wrong'
        with self.assertRaises(ValueError):subscription(value)
        with self.assertRaises(ValueError):preferences({**PREFS,'delay_seconds':True})

    def test_real_encryption_and_transport_does_not_follow_redirects(self):
        captured={}
        client_key=ec.generate_private_key(ec.SECP256R1());data=info()
        data['keys']['p256dh']=base64.urlsafe_b64encode(client_key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)).decode().rstrip('=')
        def request(session,method,url,**kwargs):
            captured.update(kwargs);captured['body']=kwargs['data'];return SimpleNamespace(status_code=201,text="",headers={})
        with patch('requests.Session.request',new=request):
            status=deliver(data,{'title':'Fixture encrypted'},self.service.key_path,'https://monitor.example.test')
        self.assertEqual(status,201);self.assertFalse(captured['allow_redirects']);self.assertNotIn(b'Fixture encrypted',captured['body'])
        self.assertEqual(captured['headers']['content-encoding'],'aes128gcm')
        import http_ece
        decoded=http_ece.decrypt(captured['body'],private_key=client_key,auth_secret=b'0123456789abcdef',version='aes128gcm')
        self.assertEqual(json.loads(decoded),{'title':'Fixture encrypted'})


class NotificationBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_account_csrf_and_origin_are_required_before_device_enrollment(self):
        with tempfile.TemporaryDirectory() as directory:
            access=Access(directory);service=SimpleNamespace(start=AsyncMock(),stop=AsyncMock(),notifications=SimpleNamespace(subscribe=Mock(return_value="c"*32),start=AsyncMock(),stop=AsyncMock()))
            app=build_app(service,access)
            async def call(method,path,headers=None,body=None):
                request=make_mocked_request(method,path,headers={'Host':'localhost',**(headers or {})});request.json=AsyncMock(return_value=body)
                match=await app.router.resolve(request);return await app.middlewares[0](request,match.handler)
            self.assertEqual((await call('GET','/api/notifications')).status,401)
            login=await call('POST','/api/session',{'Content-Type':'application/json'}, {'code':access.token})
            key=login.cookies['kobra_session'].value;csrf=json.loads(login.text)['csrf'];headers={'Cookie':'kobra_session='+key,'Content-Type':'application/json','X-Kobra-CSRF':csrf,'Origin':'https://localhost'}
            self.assertEqual((await call('POST','/api/notifications',headers,{})).status,403)
            access.account={'username':'Fixture'}
            self.assertEqual((await call('POST','/api/notifications',{**headers,'X-Kobra-CSRF':''},{})).status,403)
            self.assertEqual((await call('POST','/api/notifications',{**headers,'Origin':'https://evil.invalid'},{})).status,403)
            self.assertEqual((await call('POST','/api/notifications',headers,{'action':'subscribe','subscription':{},'label':'Fixture','preferences':PREFS})).status,200)
            service.notifications.subscribe.assert_called_once()


if __name__=='__main__':unittest.main()
