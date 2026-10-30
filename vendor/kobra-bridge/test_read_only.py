#!/usr/bin/env python3
"""Device-control boundary regression tests; never opens a printer connection."""
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock, patch

from aiohttp import web
from aiohttp.test_utils import make_mocked_request
import kobrax_client as client_module
import kobrax_moonraker_bridge as bridge_module
import config_loader
from kobrax_client import KobraXClient
from kobrax_moonraker_bridge import KobraXBridge, build_app
from read_only_policy import (
    READ_ONLY_GET_PATHS, ReadOnlyViolation, parse_read_only,
    validate_read_only_frame,
)


class ReadOnlyClientTests(unittest.TestCase):
    def setUp(self):
        self.client = KobraXClient('192.0.2.1', 'test', 'test', '20025', 'test-device', read_only=True)
        self.sock = Mock()
        self.client._sock = self.sock
        self.prefix = 'anycubic/anycubicCloud/v1/slicer/printer/20025/test-device/'

    def packet(self, kind, action, data=None, topic=None):
        return client_module._build_publish(topic or self.prefix+kind, json.dumps({
            'type':kind, 'action':action, 'data':data,
        }))

    def test_status_queries_reach_only_the_fake_socket(self):
        for kind, action in [('info','query'),('tempature','query'),('print','query'),('multiColorBox','getInfo')]:
            self.assertTrue(self.client._send(self.packet(kind, action)))
        self.assertTrue(self.client._send(client_module._build_subscribe(
            'anycubic/anycubicCloud/v1/printer/public/20025/test-device/#', 1)))
        self.assertTrue(self.client._send(client_module._build_pingreq()))
        self.assertEqual(self.sock.sendall.call_count, 6)

    def test_controls_wrong_target_and_query_with_settings_never_reach_socket(self):
        packets=[self.packet(kind,action) for kind,action in [
            ('print','start'),('print','pause'),('print','resume'),('print','stop'),
            ('tempature','set'),('fan','set'),('light','control'),
            ('multiColorBox','feedFilament'),('multiColorBox','setDry'),('multiColorBox','setAutoFeed'),
            ('unknown','query')]]
        packets += [self.packet('info','query',{'settings':{'target_nozzle_temp':300}}),
                    self.packet('info','query',topic=self.prefix.replace('test-device','other')+'info')]
        for packet in packets:
            with self.subTest(packet=packet), self.assertRaises(ReadOnlyViolation):
                self.client._send(packet)
        self.sock.sendall.assert_not_called()

    def test_malformed_retained_qos_and_concatenated_packets_never_reach_socket(self):
        good=self.packet('info','query')
        for packet in [b'',b'\x30',b'\x30\xff\xff\xff\xff\x00',good[:-1],good+good,
                       b'\x31'+good[1:],b'\x32'+good[1:],b'\xc0\x00'+good,
                       client_module._build_publish(self.prefix+'info','[]'),
                       client_module._build_subscribe('other-device/#',1)]:
            with self.subTest(packet=packet), self.assertRaises(ReadOnlyViolation):
                self.client._send(packet)
        self.sock.sendall.assert_not_called()

    def test_public_controls_and_upload_stop_before_readers_files_or_network(self):
        self.client._ensure_reader=Mock(side_effect=AssertionError('Reader must not start'))
        with self.assertRaises(ReadOnlyViolation): self.client.publish('print','pause')
        with self.assertRaises(ReadOnlyViolation): self.client.publish_web('print','update',{})
        with self.assertRaises(ReadOnlyViolation): self.client.upload_gcode('/nonexistent/file.gcode')
        self.client._ensure_reader.assert_not_called()
        self.sock.sendall.assert_not_called()
        self.assertEqual(self.client._pending_msgid,{})

    def test_duplicate_and_unexpected_fields_cannot_hide_control_payloads(self):
        for payload in [
            '{"type":"info","action":"pause","action":"query","data":null}',
            '{"type":"info","action":"query","data":null,"settings":{"target":300}}',
            '{"type":["info"],"action":"query","data":null}',
        ]:
            with self.assertRaises(ReadOnlyViolation):
                self.client._send(client_module._build_publish(self.prefix+'info',payload))
        self.sock.sendall.assert_not_called()

    def test_explicit_disabled_mode_preserves_existing_transport(self):
        c=KobraXClient('192.0.2.1','test','test','20025','test-device')
        c._sock=self.sock
        self.assertTrue(c._send(self.packet('print','pause')))
        self.sock.sendall.assert_called_once()

    def test_setting_rejects_typos_and_runtime_public_flag_assignment(self):
        for value in ['1','true','yes','on',True]: self.assertTrue(parse_read_only(value))
        for value in ['0','false','no','off',False]: self.assertFalse(parse_read_only(value))
        for value in ['tru','',None,'2']:
            with self.assertRaises(ValueError): parse_read_only(value)
        with self.assertRaises(AttributeError): self.client.read_only=False


class ReadOnlyBridgeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.client=KobraXClient('192.0.2.1','test','test','20025','test-device',read_only=True)
        self.args=SimpleNamespace(read_only=True,model_id='20025',data_dir=self.directory.name,
            camera_on_print=1,spoolman_server='http://should-never-be-contacted.invalid')
        with patch('kobrax_moonraker_bridge.SpoolmanClient',side_effect=AssertionError('No Spoolman in read-only mode')):
            self.bridge=KobraXBridge(self.client,args=self.args)
        self.app=build_app(self.bridge)

    def tearDown(self):
        self.bridge._store._conn.close()
        self.directory.cleanup()

    async def test_http_allowlist_denies_controls_websocket_settings_and_unknown_gets(self):
        gate=self.app.middlewares[0]
        reached=[]
        async def handler(request):
            reached.append(request.path)
            return web.json_response({'ok':True})
        for path in sorted(READ_ONLY_GET_PATHS):
            response=await gate(make_mocked_request('GET',path),handler)
            self.assertEqual(response.status,200)
        before=len(reached)
        forbidden=['/websocket','/printer/gcode/script?script=M104%20S300',
            '/printer/print/start','/printer/print/pause','/printer/print/resume','/printer/print/cancel',
            '/server/files/upload','/api/settings','/api/ace/dry','/api/ams/feed','/api/update/apply',
            '/kx/printers','/unknown']
        for method in ['GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS']:
            for path in forbidden:
                response=await gate(make_mocked_request(method,path),handler)
                self.assertEqual(response.status,403,(method,path))
        for path in READ_ONLY_GET_PATHS:
            response=await gate(make_mocked_request('POST',path),handler)
            self.assertEqual(response.status,403)
        self.assertEqual(len(reached),before)
        response=await gate(make_mocked_request('GET','/'),handler)
        self.assertTrue(json.loads(response.text)['read_only'])

    async def test_state_reports_mode_and_telemetry(self):
        self.bridge._state.update(nozzle_temp=257,bed_temp=80,progress=.82,print_state='printing')
        response=await self.bridge.handle_api_state(make_mocked_request('GET','/api/state'))
        body=json.loads(response.text)
        self.assertTrue(body['read_only'])
        self.assertEqual(body['nozzle_temp'],257)
        self.assertEqual(body['print_state'],'printing')
        self.assertEqual(body['camera_enabled'],0)

    async def test_camera_feed_and_spoolman_automations_are_disabled(self):
        self.assertIsNone(self.bridge._spoolman)
        self.client.start_camera=Mock(side_effect=AssertionError('No camera command'))
        self.bridge.camera_cache.set_url=Mock(side_effect=AssertionError('No camera stream'))
        self.bridge._last_feed_status={0:(5,0)}
        boxes=[{'id':0,'feed_status':{'type':1,'current_status':10,'slot_index':0}}]
        self.assertEqual(self.bridge._new_tip_form_events(boxes),[])
        payload={'data':{'printerName':'Test','model':'Anycubic Kobra S1','state':'busy',
            'project':{'state':'printing','filename':'active.gcode'},'urls':{'rtspUrl':'http://192.0.2.1/flv'}}}
        self.bridge._on_info(payload)
        self.bridge._on_print({'state':'printing','data':{'filename':'active.gcode'}})
        self.client.start_camera.assert_not_called()
        self.bridge.camera_cache.set_url.assert_not_called()
        self.assertEqual(self.bridge._state['print_state'],'printing')

    async def test_cannot_create_read_only_bridge_with_mutable_client(self):
        c=KobraXClient('192.0.2.1','test','test','20025','test-device')
        with self.assertRaises(ValueError): KobraXBridge(c,args=self.args)


class ReadOnlyStartupTests(unittest.TestCase):
    def parse_startup(self, argv):
        captured=[]
        with patch('sys.argv',['bridge',*argv]), \
             patch.object(bridge_module,'run_bridge',new=Mock(side_effect=lambda args:captured.append(args))), \
             patch.object(bridge_module.asyncio,'run'):
            bridge_module.main()
        return captured[0]

    def test_cli_and_environment_enable_mode(self):
        with patch.dict(os.environ,{'READ_ONLY':'0'}):
            self.assertTrue(self.parse_startup(['--read-only']).read_only)
            self.assertFalse(self.parse_startup([]).read_only)
        with patch.dict(os.environ,{'READ_ONLY':'1'}):
            self.assertTrue(self.parse_startup([]).read_only)
        with patch.dict(os.environ,{'READ_ONLY':'treu'}), self.assertRaises(ValueError):
            self.parse_startup([])

    def test_config_file_enables_mode_without_cli_flag(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            os.environ.pop('READ_ONLY',None)
            config=Path(directory,'config.ini')
            config.write_text('[bridge]\nread_only = 1\n')
            config_loader._load_config_file(config)
            self.assertTrue(self.parse_startup([]).read_only)

    def test_printer_entry_cannot_downgrade_process_mode(self):
        base=SimpleNamespace(read_only=True,printer_ip='192.0.2.1',mqtt_port=9883,
            username='test',password='test',mode_id='20025',device_id='device',port=7125)
        args=bridge_module._build_per_printer_args(base,{'read_only':'0','printer_ip':'192.0.2.2'})
        self.assertTrue(args.read_only)


if __name__=='__main__': unittest.main()
