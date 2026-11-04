import os
import asyncio
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE))
import monitor
from aiohttp import web
from aiohttp.test_utils import make_mocked_request


def fake_bridge():
    return SimpleNamespace(_state={'printer_name':'Test S1','firmware_version':'2.7.2.7',
        'nozzle_temp':257,'nozzle_target':257,'bed_temp':80,'bed_target':80,
        'print_state':'printing','progress':.42,'filename':'file.gcode'},
        _ams_slots=[{'index':0,'global_index':0,'type':'PETG','color':[33,39,33]}],
        _ams_loaded_slot=0,_ace_box_ids=[0],_store=SimpleNamespace(_conn=Mock()))


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.now=100
        self.state=monitor.Telemetry('192.168.1.101',clock=lambda:self.now)
        self.bridge=fake_bridge()

    def info(self):
        self.state.receive('info',{'code':200,'data':{'printerName':'Test','state':'busy',
            'temp':{'curr_nozzle_temp':257},'project':{'state':'printing'},
            'urls':{'fileUploadurl':'http://192.0.2.1/?s=SECRET'},'password':'SECRET'}},self.bridge)

    def test_no_fake_zero_readings_before_first_report(self):
        snap=self.state.snapshot()
        self.assertIsNone(snap['data'])
        self.assertIsNone(snap['age_s'])
        self.assertEqual(snap['connection'],'connecting')

    def test_stale_values_are_retained_but_never_look_live(self):
        self.info(); self.state.link(True)
        self.assertEqual(self.state.snapshot()['connection'],'online')
        self.now+=91
        snap=self.state.snapshot()
        self.assertEqual(snap['connection'],'stale')
        self.assertEqual(snap['data']['nozzle_temp'],257)
        self.assertEqual(snap['section_age_s']['temperature'],91)
        self.state.link(False)
        self.assertEqual(self.state.snapshot()['connection'],'offline')

    def test_section_freshness_is_independent_and_ack_is_ignored(self):
        self.info(); self.state.link(True); self.now+=91
        self.state.receive('tempature',{'data':{'curr_nozzle_temp':250}},self.bridge)
        snap=self.state.snapshot()
        self.assertEqual(snap['connection'],'online')
        self.assertEqual(snap['section_age_s']['print'],91)
        self.assertEqual(snap['section_age_s']['temperature'],0)
        self.now+=4
        self.state.receive('info',{'code':200,'data':{}},self.bridge)
        self.state.receive('tempature',{'code':500,'data':{'curr_nozzle_temp':0}},self.bridge)
        self.assertEqual(self.state.snapshot()['section_age_s']['temperature'],4)

    def test_snapshot_contains_no_credentials_upload_urls_or_original_references(self):
        self.info()
        self.state.receive('multiColorBox',{'code':200,'data':{'multi_color_box':[{'id':0}]}},self.bridge)
        snap=self.state.snapshot()
        self.assertNotIn('SECRET',json.dumps(snap))
        self.assertNotIn('fileUploadurl',json.dumps(snap))
        snap['data']['ace_slots'][0]['type']='Changed'
        self.assertEqual(self.state.snapshot()['data']['ace_slots'][0]['type'],'PETG')

    def test_reconnect_ace_report_does_not_replace_previous_temperature_with_zero(self):
        self.info()
        self.now+=100
        fresh_bridge=fake_bridge()
        fresh_bridge._state['nozzle_temp']=0
        self.state.receive('multiColorBox',{'code':200,'data':{'multi_color_box':[]}},fresh_bridge)
        snap=self.state.snapshot()
        self.assertEqual(snap['data']['nozzle_temp'],257)
        self.assertEqual(snap['section_age_s']['temperature'],100)
        self.assertEqual(snap['section_age_s']['ace'],0)

    def test_sku_is_bounded_and_full_suffix_preserved(self):
        self.bridge._ams_slots[0]['sku']='TEST-UNIQUE-0001'
        self.state.receive('multiColorBox',{'data':{'multi_color_box':[{'id':0}]}},self.bridge)
        self.assertEqual(self.state.snapshot()['data']['ace_slots'][0]['sku'],'TEST-UNIQUE-0001')
        self.bridge._ams_slots[0]['sku']='x'*500
        self.state.receive('multiColorBox',{'data':{'multi_color_box':[{'id':0}]}},self.bridge)
        self.assertIsNone(self.state.snapshot()['data']['ace_slots'][0]['sku'])

    def test_explicit_empty_ace_report_clears_cached_slots(self):
        self.state.receive('multiColorBox',{'code':200,'data':{'multi_color_box':[{'id':0}]}},self.bridge)
        self.assertEqual(len(self.state.snapshot()['data']['ace_slots']),1)
        self.state.receive('multiColorBox',{'code':200,'data':{'multi_color_box':[]}},self.bridge)
        snap=self.state.snapshot()
        self.assertEqual(snap['data']['ace_slots'],[])
        self.assertEqual(snap['data']['ace_units'],[])
        self.assertEqual(snap['data']['loaded_slot'],-1)


class ApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_assets_and_status_can_reach_a_handler(self):
        service=SimpleNamespace(ip='192.168.1.101',telemetry=monitor.Telemetry('192.168.1.101'),start=AsyncMock(),stop=AsyncMock())
        app=monitor.build_app(service)
        gate=app.middlewares[0]
        handler=AsyncMock(return_value=web.json_response({'ok':True}))
        for path in ('/','/assets/monitor.css','/assets/monitor.js','/api/status','/health'):
            r=await gate(make_mocked_request('GET',path),handler)
            self.assertEqual(r.status,200)
        self.assertIn("connect-src 'self'",r.headers['Content-Security-Policy'])
        count=handler.await_count
        for method,path in [('POST','/api/status'),('GET','/websocket'),('GET','/api/settings'),
                            ('POST','/printer/print/start'),('GET','/assets/../../monitor.py'),('POST','/')]:
            r=await gate(make_mocked_request(method,path),handler)
            self.assertEqual(r.status,403)
        self.assertEqual(count,handler.await_count)

    async def test_failed_login_retries_without_discarding_previous_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=monitor.Monitor('192.168.1.101',tmp,tmp)
            service.connect=AsyncMock(side_effect=OSError('failure'))
            service.disconnect=AsyncMock(side_effect=lambda:service.telemetry.link(False))
            sleeps=[]
            async def stop_sleep(delay):
                sleeps.append(delay)
                raise asyncio.CancelledError()
            with patch.object(monitor.asyncio,'sleep',new=stop_sleep):
                with self.assertRaises(asyncio.CancelledError): await service.run()
            self.assertEqual(sleeps,[monitor.RETRY_AFTER])
            self.assertGreaterEqual(service.disconnect.await_count,1)
            self.assertNotIn('failure',service.telemetry.snapshot()['message'])

    async def test_disconnect_removes_temporary_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=monitor.Monitor('192.168.1.101',tmp,tmp)
            for name in ('anycubic_slicer.crt','anycubic_slicer.key'):
                Path(tmp,name).write_text('test-only placeholder')
            service.client=SimpleNamespace(disconnect=Mock())
            service.bridge=fake_bridge()
            conn=service.bridge._store._conn
            await service.disconnect()
            self.assertFalse(list(Path(tmp).iterdir()))
            conn.close.assert_called_once()
            self.assertIsNone(service.client)

    async def test_login_recovers_automatically_after_a_network_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=monitor.Monitor('192.168.1.101',tmp,tmp)
            client=SimpleNamespace(_sock=object(),_running=True,publish=Mock(),query_info=Mock(),query_multicolor_box=Mock())
            attempts=[]
            async def connect():
                attempts.append(True)
                if len(attempts)==1: raise OSError('Temporary network failure')
                service.client=client
                service.bridge=fake_bridge()
                service.telemetry.receive('info',{'code':200,'data':{'state':'busy'}},service.bridge)
            async def disconnect():
                service.client=None
                service.telemetry.link(False)
            service.connect=connect
            service.disconnect=disconnect
            async def bounded_sleep(delay):
                if delay==monitor.RETRY_AFTER: return
                raise asyncio.CancelledError()
            with patch.object(monitor.asyncio,'sleep',new=bounded_sleep):
                with self.assertRaises(asyncio.CancelledError): await service.run()
            self.assertEqual(len(attempts),2)
            client.query_info.assert_called_once()
            client.query_multicolor_box.assert_called_once()
            self.assertEqual(service.telemetry.snapshot()['data']['print_state'],'printing')


class FleetTests(unittest.IsolatedAsyncioTestCase):
    async def test_tls_loads_each_clients_own_certificate_not_module_defaults(self):
        import kobrax_client
        with tempfile.TemporaryDirectory() as tmp:
            for index in (1,2):
                cert=Path(tmp,f'{index}.crt');key=Path(tmp,f'{index}.key')
                cert.write_text('fixture');key.write_text('fixture')
                client=kobrax_client.KobraXClient('192.0.2.1','user','pass','20025','device',
                    read_only=True,cert_file=str(cert),key_file=str(key))
                tls=Mock();tls.recv.return_value=b'\x20\x02\x00\x00';tls.cipher.return_value=('fixture','TLSv1.3',256)
                context=Mock();context.wrap_socket.return_value=tls
                client._subscribe=Mock()
                with patch.object(kobrax_client.ssl,'SSLContext',return_value=context), \
                     patch.object(kobrax_client.socket,'getaddrinfo',return_value=[(None,None,None,None,('192.0.2.1',9883))]), \
                     patch.object(kobrax_client.socket,'create_connection',return_value=Mock()):
                    client._do_connect()
                context.load_cert_chain.assert_called_once_with(str(cert),str(key))
                client.disconnect()

    async def test_states_and_certificate_files_are_isolated_across_reconnects(self):
        from kobrax_client import KobraXClient
        with tempfile.TemporaryDirectory() as tmp:
            fleet=monitor.Fleet(['192.168.1.101','192.168.1.102'],tmp,str(Path(tmp)/'data'))
            first,second=fleet.monitors.values()
            def handshake(ip):
                return SimpleNamespace(broker_host=ip,broker_port=9883,device_cert='cert-'+ip,
                    device_key='key-'+ip,username='user-'+ip,password='pass-'+ip,model_id='20025',device_id='id-'+ip)
            with patch.object(monitor,'do_handshake',side_effect=handshake), patch.object(KobraXClient,'connect',new=Mock()):
                await asyncio.gather(first.connect(),second.connect())
                try:
                    self.assertNotEqual(first.client.cert_file,second.client.cert_file)
                    self.assertNotEqual(first.client.key_file,second.client.key_file)
                    self.assertNotEqual(first.client.client_id,second.client.client_id)
                    self.assertEqual(Path(first.client.cert_file).read_text(),'cert-'+first.ip)
                    self.assertEqual(Path(second.client.key_file).read_text(),'key-'+second.ip)
                    if os.name!='nt':self.assertEqual(Path(first.client.key_file).stat().st_mode & 0o777,0o600)
                    b1,b2=fake_bridge(),fake_bridge()
                    b2._state['nozzle_temp']=215
                    b2._state['printer_name']='Second S1'
                    for service,bridge in [(first,b1),(second,b2)]:
                        service.telemetry.receive('info',{'code':200,'data':{'printerName':'Test','state':'busy','temp':{'curr_nozzle_temp':1}}},bridge)
                    snapshots=fleet.snapshot()['printers']
                    self.assertEqual([x['data']['nozzle_temp'] for x in snapshots],[257,215])
                    second_key=Path(second.client.key_file)
                    await first.disconnect()
                    self.assertTrue(second_key.exists())
                    self.assertEqual(fleet.snapshot()['printers'][1]['connection'],'online')
                    await first.connect()
                    self.assertEqual(Path(first.client.key_file).read_text(),'key-'+first.ip)
                    self.assertTrue(second_key.exists())
                    self.assertTrue(all(x.client.read_only for x in (first,second)))
                finally:
                    await asyncio.gather(first.disconnect(),second.disconnect())
                    fleet.history.close()

    async def test_failing_printer_does_not_block_other_session_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            fleet=monitor.Fleet(['192.168.1.101','192.168.1.102'],tmp,str(Path(tmp)/'data'))
            first,second=fleet.monitors.values()
            first.run=AsyncMock(side_effect=OSError('only first session fails'))
            second.run=AsyncMock()
            await fleet.start(None)
            await asyncio.sleep(0)
            first.run.assert_awaited_once()
            second.run.assert_awaited_once()
            self.assertTrue(first.task.done())
            self.assertIsInstance(first.task.exception(),OSError)
            await second.stop(None)
            fleet.history.close()

    async def test_reconnected_session_gets_time_to_refresh_old_telemetry(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=monitor.Monitor('192.168.1.101',tmp,tmp)
            service.telemetry.seen['print']=time.monotonic()-120
            client=SimpleNamespace(_sock=object(),_running=True,publish=Mock(),query_info=Mock(),query_multicolor_box=Mock())
            async def connect():
                service.client=client
                service.bridge=fake_bridge()
            service.connect=connect
            service.disconnect=AsyncMock()
            async def finish(delay): raise asyncio.CancelledError()
            with patch.object(monitor.asyncio,'sleep',new=finish):
                with self.assertRaises(asyncio.CancelledError): await service.run()
            client.query_info.assert_called_once()
            client.query_multicolor_box.assert_called_once()


if __name__=='__main__': unittest.main()
