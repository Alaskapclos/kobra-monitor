"""Control intents must not become socket writes by retry, stale data or restart."""
import asyncio
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from controls import ControlRefused, LightControls


class LightControlTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'history.sqlite3'
        self.now = 1000
        self.elapsed = 0
        self.data = dict(online=True, connection_id='first-session', light_on=False,
                         light_revision=12, light_age_s=0)
        self.sent = []
        self.confirm = True
        self.fail_send = False

        def snapshot(ip):
            return dict(self.data) if ip == '192.0.2.1' else None

        self.snapshot = snapshot

        async def send(ip, desired, epoch):
            self.sent.append((ip, desired, epoch))
            if self.fail_send:
                raise OSError('Socket result unknown')
            if self.confirm:
                self.data.update(light_on=desired,
                                 light_revision=self.data['light_revision'] + 1)

        self.send = send
        self.service = self.open_service()

    def open_service(self, **kw):
        return LightControls(self.path, self.snapshot, self.send, enabled=True,
                             clock=lambda: self.now, monotonic=lambda: self.elapsed,
                             confirmation_timeout=.12, **kw)

    async def asyncTearDown(self):
        self.service.close()
        self.folder.cleanup()

    async def prepare(self, desired=True, actor='owner-session', ip='192.0.2.1', request_id=None):
        return await self.service.prepare(actor, ip, desired, request_id or str(uuid.uuid4()))

    async def execute(self, intent, actor='owner-session'):
        return await self.service.execute(actor, intent['id'], intent.get('token', ''))

    async def test_disabled_default_and_missing_sender_cannot_prepare(self):
        for enabled, sender in ((False, self.send), (True, None)):
            other = LightControls(':memory:', self.snapshot, sender, enabled=enabled)
            try:
                with self.assertRaises(ControlRefused):
                    await other.prepare('owner', '192.0.2.1', True, str(uuid.uuid4()))
            finally:
                other.close()
        self.assertEqual(self.sent, [])

    async def test_prepare_and_cancel_do_not_send(self):
        intent = await self.prepare()
        self.assertEqual(intent['state'], 'prepared')
        result = await self.service.cancel('owner-session', intent['id'])
        self.assertEqual(result['state'], 'cancelled')
        await self.execute(intent)
        self.assertEqual(self.sent, [])

    async def test_only_a_new_report_confirms_the_change(self):
        intent = await self.prepare()
        result = await self.execute(intent)
        self.assertEqual(result['state'], 'confirmed')
        self.assertEqual(self.sent, [('192.0.2.1', True, 'first-session')])
        self.assertNotIn('token', result)

    async def test_no_command_when_already_in_requested_state(self):
        intent = await self.prepare(False)
        self.assertEqual(intent['state'], 'unchanged')
        self.assertNotIn('token', intent)
        await self.execute(intent)
        self.assertEqual(self.sent, [])

    async def test_wrong_actor_token_or_device_cannot_send(self):
        with self.assertRaises(ControlRefused):
            await self.prepare(ip='192.0.2.2')
        intent = await self.prepare()
        with self.assertRaises(ControlRefused):
            await self.execute(intent, 'another-session')
        with self.assertRaises(ControlRefused):
            await self.service.execute('owner-session', intent['id'], 'bad-token')
        self.assertEqual(self.sent, [])

    async def test_offline_missing_invalid_and_old_fields_are_refused(self):
        baseline = dict(self.data)
        for changes in ({'online':False}, {'light_on':None}, {'light_on':0},
                        {'light_age_s':16}, {'light_age_s':float('nan')},
                        {'light_age_s':-1}, {'connection_id':''}, {'light_revision':True}):
            self.data = {**baseline, **changes}
            with self.assertRaises(ControlRefused, msg=str(changes)):
                await self.prepare()
        self.assertEqual(self.sent, [])

    async def test_boolean_intent_is_strict(self):
        for value in (1, 0, 'true', None, {}, []):
            with self.assertRaises(ControlRefused):
                await self.prepare(value)
        self.assertEqual(self.sent, [])

    async def test_expired_preparation_never_sends(self):
        intent = await self.prepare()
        self.now += 21
        self.elapsed += 21
        result = await self.execute(intent)
        self.assertEqual(result['state'], 'expired')
        self.assertEqual(self.sent, [])

    async def test_reconnect_or_intervening_change_invalidates_preparation(self):
        intent = await self.prepare()
        self.data['connection_id'] = 'new-session'
        with self.assertRaises(ControlRefused):
            await self.execute(intent)
        self.data['light_on'] = False
        intent = await self.prepare()
        self.data['light_on'] = True
        with self.assertRaises(ControlRefused):
            await self.execute(intent)
        self.assertEqual(self.sent, [])

    async def test_double_click_and_http_retry_send_only_once(self):
        request_id = str(uuid.uuid4())
        first = await self.prepare(request_id=request_id)
        again = await self.prepare(request_id=request_id)
        self.assertEqual(first, again)
        results = await asyncio.gather(self.execute(first), self.execute(first))
        self.assertTrue(all(r['state'] in ('sending', 'confirmed') for r in results))
        await self.execute(first)
        self.assertEqual(len(self.sent), 1)
        with self.assertRaises(ControlRefused):
            await self.prepare(False, request_id=request_id)

    async def test_two_browsers_cannot_prepare_overlapping_actions(self):
        await self.prepare()
        with self.assertRaises(ControlRefused):
            await self.prepare(actor='second-browser')
        self.assertEqual(self.sent, [])

    async def test_socket_error_is_uncertain_and_never_retried(self):
        self.fail_send = True
        intent = await self.prepare()
        self.assertEqual((await self.execute(intent))['state'], 'uncertain')
        await self.execute(intent)
        self.assertEqual(len(self.sent), 1)

    async def test_ack_without_new_telemetry_is_not_confirmation(self):
        self.confirm = False
        intent = await self.prepare()
        self.assertEqual((await self.execute(intent))['state'], 'uncertain')
        self.assertEqual(len(self.sent), 1)

    async def test_reconnect_after_send_stays_uncertain_even_if_light_matches(self):
        async def reconnecting_send(ip, desired, epoch):
            await self.send(ip, desired, epoch)
            self.data['connection_id'] = 'replacement-session'
        self.service.sender = reconnecting_send
        intent = await self.prepare()
        self.assertEqual((await self.execute(intent))['state'], 'uncertain')
        await self.execute(intent)
        self.assertEqual(len(self.sent), 1)

    async def test_restart_discards_preparation_and_never_replays_send(self):
        intent = await self.prepare()
        self.service.close()
        self.service = self.open_service()
        self.assertEqual((await self.execute(intent))['state'], 'expired')
        self.assertEqual(self.sent, [])
        intent = await self.prepare()
        self.service.db.execute("UPDATE control_attempts SET state='sending' WHERE id=?", (intent['id'],))
        self.service.close()
        self.service = self.open_service()
        self.assertEqual((await self.execute(intent))['state'], 'uncertain')
        self.assertEqual(self.sent, [])

    async def test_audit_failure_prevents_socket_write(self):
        intent = await self.prepare()
        self.service.db.execute('PRAGMA query_only=ON')
        with self.assertRaises(sqlite3.OperationalError):
            await self.execute(intent)
        self.assertEqual(self.sent, [])

    async def test_clock_rollback_does_not_extend_confirmation_window(self):
        intent = await self.prepare()
        self.now -= 3600
        self.elapsed += 21
        self.assertEqual((await self.execute(intent))['state'], 'expired')
        self.assertEqual(self.sent, [])
