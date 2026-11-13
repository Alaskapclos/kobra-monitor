"""Current-session ACE state and a non-reentrant socket-lock regression test."""
import asyncio
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from monitor import Monitor
from light_transport import LightControlClient


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.m=Monitor('192.0.2.1',self.t.name,self.t.name,archive_start=True)
        self.client=LightControlClient('192.0.2.1','u','p','20025','synthetic',archive_start_enabled=True)
        self.client._running=True;self.client._sock=Mock();self.m.client=self.client
        self.epoch=self.client.control_connection_id();self.now=100.
        self.m.telemetry.clock=lambda:self.now;self.m.telemetry.motion.clock=lambda:self.now
        self.m.telemetry.link(True)
        self.bridge=SimpleNamespace(_state={},_ams_slots=[{'index':2,'global_index':2,'box_id':0,'status':5,
            'type':'PLA','color':[1,2,3],'sku':'synthetic','consumables_percent':100}],_ams_loaded_slot=2,_ace_box_ids=[0])
        self.m.telemetry.receive('info',{'data':{'state':'free','project':None,
            'urls':{'fileUploadurl':'http://192.0.2.1:18910/gcode_upload?s=PRIVATE'}}},self.bridge,self.epoch)
        self.ace()
    def ace(self):self.m.telemetry.receive('multiColorBox',{'data':{'multi_color_box':[{'id':0}]}},self.bridge,self.epoch)
    async def test_only_current_session_freshness_and_material_changes_invalidate(self):
        a=self.m.archive_repeat.snapshot();self.assertTrue(a['idle']);self.assertEqual(a['ace_connection_id'],self.epoch)
        self.bridge._ams_slots[0]['consumables_percent']=99;self.ace()
        self.assertEqual(self.m.archive_repeat.snapshot()['material_context'],a['material_context'])
        self.bridge._ams_slots[0]['sku']='changed';self.ace();b=self.m.archive_repeat.snapshot()
        self.bridge._ams_slots[0]['sku']='synthetic';self.ace();c=self.m.archive_repeat.snapshot()
        self.assertNotEqual(a['material_context'],b['material_context']);self.assertNotEqual(a['material_context'],c['material_context'])
        self.assertNotIn('PRIVATE',json.dumps(self.m.telemetry.snapshot()))
        self.assertNotIn('PRIVATE',json.dumps(c))
        self.client._sock_gen+=1
        self.assertFalse(self.m.archive_repeat.snapshot()['idle'])
    async def test_disabled_adapter_does_not_allow_status_as_start_permission(self):
        self.m.archive_repeat.enabled=False;self.assertIsNone(self.m.archive_repeat.snapshot())
        with self.assertRaises(ValueError):await self.m.archive_repeat.refresh()
        self.client._sock.sendall.assert_not_called()
    async def test_final_guard_does_not_acquire_socket_lock_again_or_look_up_history(self):
        # send_archive_start_once holds the same non-reentrant threading.Lock.
        self.m.history=Mock();self.m.history.jobs.side_effect=AssertionError('history lookup inside socket lock')
        mapping=[{'paint_index':0,'ams_index':2,'paint_color':[1,2,3,255],'ams_color':[1,2,3,255],'material_type':'PLA'}]
        receipt={'md5':'b'*32,'bytes':123}
        def matches(row,snapshot):return snapshot['idle'] and snapshot['connection_id']==self.epoch
        dispatch=SimpleNamespace(matches_snapshot=matches)
        await asyncio.wait_for(self.m.archive_repeat.start(dispatch,{'id':'a'*32},receipt,mapping,self.epoch,lambda:True),1)
        self.assertEqual(self.client._sock.sendall.call_count,1)
        self.m.history.jobs.assert_not_called()


if __name__=='__main__':unittest.main()
