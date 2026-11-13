"""Only synthetic sockets: these tests never construct a printer connection."""
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/kobra-bridge')]
from light_transport import LightControlClient
from kobrax_client import _build_publish
from read_only_policy import ReadOnlyViolation


def decode(frame):
    pos=1
    while frame[pos] & 128:pos+=1
    pos+=1
    size=int.from_bytes(frame[pos:pos+2], 'big');pos+=2
    return frame[pos:pos+size].decode(), json.loads(frame[pos+size:])


class LightTransportTests(unittest.TestCase):
    def client(self, enabled=True, model='20025'):
        client=LightControlClient('192.0.2.1','synthetic-user','synthetic-password',
                                  model,'synthetic-device',control_enabled=enabled)
        client._sock=Mock();client._running=True;client._sock_gen=7
        client._ensure_reader=Mock();client._reconnect=Mock()
        return client

    def test_exact_s1_light_packet_and_both_boolean_states(self):
        client=self.client()
        for on in (True,False):
            client.send_light_once(on,client.control_connection_id(),send_deadline=time.monotonic()+1)
            frame=client._sock.sendall.call_args.args[0]
            topic,body=decode(frame)
            self.assertEqual(topic,'anycubic/anycubicCloud/v1/web/printer/20025/synthetic-device/light')
            self.assertEqual(body['type'],'light');self.assertEqual(body['action'],'control')
            self.assertEqual(body['data'],{'type':2,'status':int(on),'brightness':100 if on else 0})
        self.assertEqual(client._sock.sendall.call_count,2)
        client._reconnect.assert_not_called()

    def test_disabled_and_wrong_model_never_write(self):
        for client in (self.client(False),self.client(model='20030')):
            with self.assertRaises((PermissionError,ValueError)):
                client.send_light_once(True,client.control_connection_id(),send_deadline=time.monotonic()+1)
            client._sock.sendall.assert_not_called()

    def test_untyped_boolean_and_topic_injection_are_refused(self):
        client=self.client()
        for value in (0,1,'true',None,{},[]):
            with self.assertRaises(ValueError):
                client.send_light_once(value,client.control_connection_id(),send_deadline=time.monotonic()+1)
        client.device_id='other/device/light'
        with self.assertRaises(ValueError):
            client.send_light_once(True,client.control_connection_id(),send_deadline=time.monotonic()+1)
        client._sock.sendall.assert_not_called()

    def test_epoch_change_disconnect_and_wrong_target_are_refused(self):
        client=self.client();old=client.control_connection_id();client._sock_gen+=1
        for identity in (old,'another-client:7',None):
            with self.assertRaises(ConnectionError):client.send_light_once(True,identity,send_deadline=time.monotonic()+1)
        client._running=False
        with self.assertRaises(ConnectionError):client.send_light_once(True,old,send_deadline=time.monotonic()+1)
        client._sock.sendall.assert_not_called()

    def test_failed_write_is_not_reconnected_or_retried(self):
        client=self.client();client._sock.sendall.side_effect=OSError('synthetic partial write')
        with self.assertRaises(OSError):
            client.send_light_once(True,client.control_connection_id(),send_deadline=time.monotonic()+1)
        self.assertEqual(client._sock.sendall.call_count,1)
        client._reconnect.assert_not_called()

    def test_generic_publish_cannot_bypass_the_narrow_entrypoint(self):
        client=self.client()
        for msg,action,data in [('light','control',{'type':2,'status':1,'brightness':100}),
                                ('print','start',{}),('axis','move',{}),
                                ('fan','setSpeed',{'fan_speed_pct':100})]:
            with self.assertRaises(ReadOnlyViolation):client.publish(msg,action,data,timeout=0)
        client._sock.sendall.assert_not_called();client._reconnect.assert_not_called()

    def test_status_queries_still_pass_the_original_frame_policy(self):
        client=self.client()
        client.publish('light','query',None,timeout=0)
        self.assertEqual(client._sock.sendall.call_count,1)
        with self.assertRaises(ReadOnlyViolation):
            client._send(_build_publish(client._web_topic('light'),'{"type":"light","action":"control","data":{}}'))
        self.assertEqual(client._sock.sendall.call_count,1)

    def test_expired_or_invalid_worker_deadline_never_writes(self):
        client=self.client();identity=client.control_connection_id()
        for deadline in (time.monotonic()-1,float('nan'),float('inf'),True,None,time.monotonic()+60):
            with self.assertRaises(TimeoutError):
                client.send_light_once(True,identity,send_deadline=deadline)
        client._sock.sendall.assert_not_called()

    def test_busy_socket_lock_cannot_delay_dispatch_past_deadline(self):
        client=self.client();identity=client.control_connection_id()
        client._lock.acquire()
        try:
            with self.assertRaises(TimeoutError):
                client.send_light_once(True,identity,send_deadline=time.monotonic()+.01)
        finally:client._lock.release()
        client._sock.sendall.assert_not_called()

    def test_periodic_fan_query_passes_policy_but_fan_control_does_not(self):
        client=self.client()
        client.publish('fan','query',None,timeout=0)
        self.assertEqual(client._sock.sendall.call_count,1)
        with self.assertRaises(ReadOnlyViolation):
            client.publish('fan','query',{'fan_speed_pct':40},timeout=0)
        with self.assertRaises(ReadOnlyViolation):
            client.publish('fan','setSpeed',{'fan_speed_pct':40},timeout=0)
        self.assertEqual(client._sock.sendall.call_count,1)
