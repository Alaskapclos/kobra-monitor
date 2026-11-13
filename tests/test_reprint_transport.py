"""Fake HTTP responses and MQTT sockets only; no real printer or LAN access."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock
sys.path[:0]=[str(Path(__file__).resolve().parent.parent),str(Path(__file__).resolve().parent.parent/'vendor/kobra-bridge')]
from reprint_transfer import upload_original,upload_endpoint,remote_name,TransferUncertain
from reprint_launch import mapping_for,start_payload
from light_transport import LightControlClient
from read_only_policy import ReadOnlyViolation
from test_light_transport import decode

OP='a'*32
SLOT={'index':2,'global_index':2,'box_id':0,'status':5,'type':'PLA+','color':[1,2,3]}
MATERIAL={'paint_index':1,'type':'PLA','color':'#112233'}


class FakeHTTP:
    def __init__(self):
        self.calls=[];self.options=None;self.raw=None;self.status=200;self.consume=True;self.after_chunk=None
        self.receipt={'code':200,'data':{'gcode':remote_name(OP)}};self.block=None;self.entered=asyncio.Event()
    def session(self,**options):
        self.options=options;owner=self
        class Session:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            def post(self,url,**options):
                owner.calls.append((url,options));self.raw=bytearray()
                class Response:
                    status=owner.status
                    async def __aenter__(inner):
                        if owner.consume:
                            async for chunk in options['data']:
                                self.raw.extend(chunk)
                                if owner.after_chunk:owner.after_chunk(len(self.raw))
                        owner.raw=bytes(self.raw);owner.entered.set()
                        if owner.block:await owner.block.wait()
                        return inner
                    async def __aexit__(self,*args):pass
                    @property
                    def content(self):
                        class Content:
                            async def iter_chunked(self,size):
                                raw=owner.receipt if isinstance(owner.receipt,bytes) else json.dumps(owner.receipt).encode()
                                for i in range(0,len(raw),size):yield raw[i:i+size]
                        return Content()
                return Response()
        return Session()


class UploadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.path=Path(self.t.name)/'original.gcode.3mf';self.raw=b'original archive bytes'*30000;self.path.write_bytes(self.raw)
        self.sha=hashlib.sha256(self.raw).hexdigest();self.http=FakeHTTP();self.valid=True
    async def send(self,**changes):
        options=dict(ip='192.0.2.1',reported_url='http://192.0.2.1:18910/gcode_upload?s=synthetic',
                     guard=lambda:self.valid,enabled=True,session_factory=self.http.session)
        options.update(changes)
        return await upload_original(self.path,self.sha,OP,**options)
    async def test_exact_original_bounded_request_and_storage_is_not_start(self):
        result=await self.send();self.assertEqual(len(self.http.calls),1)
        url,options=self.http.calls[0]
        self.assertEqual(url,'http://192.0.2.1:18910/gcode_upload?s=synthetic')
        self.assertFalse(self.http.options['trust_env']);self.assertFalse(options['allow_redirects'])
        self.assertEqual(self.http.options['timeout'].total,120)
        self.assertEqual(int(options['headers']['Content-Length']),len(self.http.raw))
        self.assertEqual(int(options['headers']['X-File-Length']),len(self.raw))
        self.assertIn(b'\r\n\r\n'+self.raw+b'\r\n--',self.http.raw)
        self.assertEqual(self.path.read_bytes(),self.raw)
        self.assertFalse(result['remote_hash_verified']);self.assertFalse(result['print_started'])
        self.assertEqual(result['md5'],hashlib.md5(self.raw,usedforsecurity=False).hexdigest())
    async def test_default_disabled_stale_guard_and_corrupt_source_never_post(self):
        with self.assertRaises(PermissionError):await self.send(enabled=False)
        with self.assertRaises(PermissionError):await self.send(enabled=1)
        self.valid=False
        with self.assertRaises(ValueError):await self.send()
        self.valid=True;self.path.write_bytes(b'changed')
        with self.assertRaises(ValueError):await self.send()
        self.assertEqual(self.http.calls,[])
    async def test_cross_host_redirect_path_and_token_injection_never_post(self):
        for value in ['http://192.0.2.2:18910/gcode_upload?s=a','https://192.0.2.1:18910/gcode_upload?s=a',
                      'http://192.0.2.1:18910/other?s=a','http://192.0.2.1:18910/gcode_upload?s=a&s=b',
                      'http://192.0.2.1:18910/gcode_upload?s=a%0d%0aX:x',
                      'http://user:pass@192.0.2.1:18910/gcode_upload?s=a','http://192.0.2.1:18910/gcode_upload?s=a#x']:
            with self.subTest(value=value),self.assertRaises(ValueError):await self.send(reported_url=value)
        self.assertEqual(self.http.calls,[])
    async def test_bad_response_early_response_and_redirect_are_uncertain_without_retry(self):
        cases=[(200,b'not json',True),(200,{'code':200,'data':{'gcode':'another.gcode.3mf'}},True),
               (200,{'code':True,'data':{'gcode':remote_name(OP)}},True),
               (200,b'{"code":0,"code":200,"data":{"gcode":"'+remote_name(OP).encode()+b'"}}',True),
               (200,b'x'*65537,True),(302,{},True),(200,self.http.receipt,False)]
        for status,receipt,consume in cases:
            self.http=FakeHTTP();self.http.status=status;self.http.receipt=receipt;self.http.consume=consume
            with self.subTest(status=status,consume=consume),self.assertRaises(TransferUncertain):await self.send()
            self.assertEqual(len(self.http.calls),1)
    async def test_guard_or_source_change_during_streaming_stops_transfer(self):
        self.http.after_chunk=lambda size:setattr(self,'valid',False)
        with self.assertRaises(TransferUncertain):await self.send()
        self.assertEqual(len(self.http.calls),1)
        self.http=FakeHTTP();self.valid=True
        def mutate(sent,total):self.path.write_bytes(self.raw+b'changed')
        with self.assertRaises(TransferUncertain):await self.send(progress=mutate)
        self.assertEqual(len(self.http.calls),1)
    async def test_cancellation_never_reconnects_or_retries(self):
        self.http.block=asyncio.Event();task=asyncio.create_task(self.send())
        await self.http.entered.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(len(self.http.calls),1)


class LaunchTests(unittest.TestCase):
    def mapping(self):return mapping_for([MATERIAL],[{'paint_index':1,'slot':2}],[SLOT])
    def client(self,enabled=True):
        c=LightControlClient('192.0.2.1','u','p','20025','synthetic',archive_start_enabled=enabled)
        c._running=True;c._sock=Mock();c._reconnect=Mock();return c
    def test_explicit_sparse_tool_mapping_and_fixed_start_packet(self):
        mapping=self.mapping();self.assertEqual([m['paint_index'] for m in mapping],[0,1])
        self.assertEqual([m['ams_index'] for m in mapping],[2,2])
        self.assertEqual(mapping[1]['paint_color'],[17,34,51,255])
        payload=start_payload(OP,'b'*32,123,mapping)
        self.assertEqual(payload['filename'],remote_name(OP));self.assertEqual(payload['filepath'],'/')
        self.assertTrue(payload['ams_settings']['use_ams']);self.assertEqual(payload['task_settings']['auto_leveling'],1)
    def test_missing_duplicate_empty_cross_material_and_hub_selections_blocked(self):
        for choices,slots in [([],[SLOT]),([{'paint_index':0,'slot':2}],[SLOT]),
            ([{'paint_index':1,'slot':2}]*2,[SLOT]),([{'paint_index':1,'slot':2}],[dict(SLOT,status=0)]),
            ([{'paint_index':1,'slot':2}],[dict(SLOT,type='PETG')]),
            ([{'paint_index':1,'slot':2}],[dict(SLOT,box_id=1)]),
            ([{'paint_index':1,'slot':2}],[dict(SLOT,color=[True,2,3])])]:
            with self.subTest(choices=choices,slots=slots),self.assertRaises(ValueError):mapping_for([MATERIAL],choices,slots)
    def test_start_uses_slicer_topic_once_and_never_confirms_printing(self):
        c=self.client();self.assertIsNone(c.send_archive_start_once(OP,'b'*32,123,self.mapping(),c.control_connection_id(),
                     send_deadline=time.monotonic()+1,job_guard=lambda:True))
        topic,payload=decode(c._sock.sendall.call_args.args[0])
        self.assertEqual(topic,'anycubic/anycubicCloud/v1/slicer/printer/20025/synthetic/print')
        self.assertEqual(payload['action'],'start');self.assertEqual(payload['data']['filename'],remote_name(OP))
        self.assertEqual(c._sock.sendall.call_count,1);c._reconnect.assert_not_called()
    def test_separate_permission_connection_guard_deadline_and_generic_read_only(self):
        for enabled,guard,epoch,deadline in [(False,True,True,True),(True,False,True,True),
                                          (True,True,False,True),(True,True,True,False)]:
            c=self.client(enabled)
            with self.assertRaises((PermissionError,ConnectionError,TimeoutError)):
                c.send_archive_start_once(OP,'b'*32,123,self.mapping(),c.control_connection_id() if epoch else 'old',
                   send_deadline=time.monotonic()+(1 if deadline else -1),job_guard=lambda:guard)
            c._sock.sendall.assert_not_called();c._reconnect.assert_not_called()
        c=self.client()
        with self.assertRaises(ReadOnlyViolation):c.publish('print','start',start_payload(OP,'b'*32,123,self.mapping()),timeout=0)
        c._sock.sendall.assert_not_called()
    def test_partial_start_write_is_not_retried(self):
        c=self.client();c._sock.sendall.side_effect=OSError('synthetic partial write')
        with self.assertRaises(OSError):c.send_archive_start_once(OP,'b'*32,123,self.mapping(),c.control_connection_id(),
            send_deadline=time.monotonic()+1,job_guard=lambda:True)
        self.assertEqual(c._sock.sendall.call_count,1);c._reconnect.assert_not_called()


if __name__=='__main__':unittest.main()
