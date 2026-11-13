"""Persisted one-shot archive flow with synthetic history, guards and senders."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import AsyncMock
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from history import History
from controls import LightControls,ControlRefused
from reprint_dispatch import ReprintDispatch
from reprint_launch import start_payload
from reprint_transfer import remote_name
from test_reprint_preflight import package,entries


class DispatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.now=100.;self.sent=[];self.transfers=[]
        self.history=History(Path(self.t.name)/'history.sqlite3');self.addCleanup(self.history.close)
        a=self.history.files;client=a.authenticate(a.new_client('synthetic'))
        self.raw=package(entries());self.sha=hashlib.sha256(self.raw).hexdigest()
        incoming=a.incoming/'test.part';incoming.write_bytes(self.raw)
        a.receive(incoming,'test.gcode.3mf',self.sha,len(self.raw),client)
        self.source='a'*32
        self.history.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (self.source,'192.0.2.1','old','test.gcode.3mf','completed',1,20,20,1,100,1,1,1));self.history.db.commit()
        a.link(self.source,self.sha)
        self.data={'enabled':True,'connected':True,'model_id':'20025','idle':True,'idle_age_s':0,'ace_age_s':0,
            'connection_id':'e','ace_connection_id':'e','idle_context':'idle-one','material_context':'material-one','job_revision':1,
            'slots':[{'index':2,'global_index':2,'box_id':0,'status':5,'type':'PLA','color':[1,2,3],'sku':'synthetic'}]}
        self.light={'online':True,'connection_id':'e','light_on':False,'light_revision':1,'light_age_s':0}
        self.controls=LightControls(Path(self.t.name)/'history.sqlite3',lambda ip:dict(self.light),AsyncMock(),enabled=True,monotonic=lambda:self.now)
        self.addCleanup(self.controls.close);self.refresh=AsyncMock()
        async def upload(row,guard):
            self.assertTrue(guard());self.transfers.append(row['id'])
            return {'sha256':row['sha256'],'remote_filename':remote_name(row['id']),'storage_acknowledged':True,
                    'md5':hashlib.md5(self.raw,usedforsecurity=False).hexdigest(),'bytes':len(self.raw)}
        async def start(row,receipt,mapping,epoch,guard):
            self.assertTrue(guard());self.sent.append((row['id'],epoch))
        self.upload=upload;self.start=start
        self.service=self.make_service();self.addCleanup(lambda:self.service.close() if not self.service.closed else None)
    def make_service(self,enabled=True):
        return ReprintDispatch(self.history.files,lambda ip:dict(self.data) if ip=='192.0.2.1' else None,
            self.refresh,self.upload,self.start,controls=self.controls,enabled=enabled,clock=lambda:self.now,monotonic=lambda:self.now)
    async def prepare(self,request_id=None):
        return await self.service.prepare('owner',request_id or str(uuid.uuid4()),'192.0.2.1',self.sha,[{'paint_index':1,'slot':2}],source_job=self.source)
    async def uploaded(self):
        p=await self.prepare();return await self.service.transfer('owner',p['id'],p['token'])
    async def launch(self,p,**changes):
        options={'bed_clear':True,'nozzle_mm':.4,'material_ready':True};options.update(changes)
        return await self.service.launch('owner',p['id'],p.get('token',''),**options)
    async def test_two_separate_tokens_duplicate_requests_and_no_automatic_start(self):
        key=str(uuid.uuid4());p=await self.prepare(key);same=await self.prepare(key)
        self.assertEqual(p['id'],same['id']);self.assertEqual(self.sent,[])
        u=await self.service.transfer('owner',p['id'],p['token']);self.assertEqual(u['state'],'uploaded')
        self.assertNotEqual(p['token'],u['token']);self.assertEqual(self.sent,[])
        await self.service.transfer('owner',p['id'],p['token']);self.assertEqual(len(self.transfers),1)
        with self.assertRaises(ValueError):await self.launch(p)
        started=await self.launch(u);self.assertEqual(started['state'],'awaiting')
        await self.launch(u);self.assertEqual(len(self.sent),1)
        self.assertNotIn('token',started)
    async def test_start_requires_fresh_second_confirmation_and_physical_checks(self):
        u=await self.uploaded()
        for changes in ({'bed_clear':False},{'material_ready':1},{'nozzle_mm':.6},{'nozzle_mm':True}):
            with self.assertRaises(ValueError):await self.launch(u,**changes)
        self.assertEqual(self.sent,[])
        self.data['idle']=False
        with self.assertRaises(ValueError):await self.launch(u)
        self.assertEqual(self.sent,[])
    async def test_owner_binding_and_unknown_or_disabled_printer(self):
        p=await self.prepare()
        for method in (self.service.status,self.service.cancel):
            with self.assertRaises(ValueError):await method('other-owner',p['id'])
        with self.assertRaises(ValueError):await self.service.transfer('other-owner',p['id'],p['token'])
        self.service.enabled=False
        with self.assertRaises(PermissionError):await self.prepare()
        self.assertEqual(self.transfers,[]);self.assertEqual(self.sent,[])
    async def test_connection_material_generation_age_or_ace_session_changes_revoke(self):
        for changes in ({'connection_id':'new'},{'material_context':'changed-back-to-same-spool'},
                        {'ace_connection_id':'old'},{'ace_age_s':16},{'idle_age_s':float('nan')}):
            before=dict(self.data);p=await self.prepare();self.data.update(changes)
            with self.assertRaises(ValueError):await self.service.transfer('owner',p['id'],p['token'])
            self.data=before;await self.service.cancel('owner',p['id'])
        self.assertEqual(self.transfers,[])
    async def test_shared_control_reservation_blocks_moves_but_not_print_abort(self):
        p=await self.prepare()
        with self.assertRaises(ControlRefused):await self.controls.prepare('owner','192.0.2.1',True,str(uuid.uuid4()))
        self.assertTrue(self.service.busy('192.0.2.1','axis_x'));self.assertFalse(self.service.busy('192.0.2.1','print_stop'))
        await self.service.cancel('owner',p['id'])
        manual=await self.controls.prepare('owner','192.0.2.1',True,str(uuid.uuid4()))
        with self.assertRaises(ValueError):await self.prepare()
        await self.controls.cancel('owner',manual['id'])
        self.controls.motion_deadlines['192.0.2.1']=self.now+30
        with self.assertRaises(ValueError):await self.prepare()
    async def test_interrupted_transfer_and_start_never_retry(self):
        p=await self.prepare()
        async def fail(*args):self.transfers.append('failed');raise OSError('synthetic partial upload')
        self.service.upload=fail
        bad=await self.service.transfer('owner',p['id'],p['token']);self.assertEqual(bad['state'],'uncertain')
        await self.service.transfer('owner',p['id'],p['token']);self.assertEqual(self.transfers,['failed'])
        self.service.upload=self.upload;u=await self.uploaded()
        async def fail_start(*args):self.sent.append('failed');raise OSError('synthetic partial socket write')
        self.service.start=fail_start
        bad=await self.launch(u);self.assertEqual(bad['state'],'uncertain')
        await self.launch(u);self.assertEqual(self.sent,['failed'])
    async def test_restart_does_not_resume_uploaded_or_uncertain_dispatch(self):
        u=await self.uploaded();self.service.close();self.service=self.make_service()
        r=await self.service.status('owner',u['id']);self.assertEqual(r['state'],'expired')
        await self.launch(u);self.assertEqual(self.sent,[]);self.assertEqual(len(self.transfers),1)
    async def test_confirmation_requires_new_exact_job_not_an_ack_or_unrelated_print(self):
        u=await self.uploaded();await self.launch(u)
        receipt=json.loads(self.service.db.execute('SELECT receipt FROM archive_dispatches WHERE id=?',(u['id'],)).fetchone()[0])
        self.data['idle']=False
        job={'id':'c'*32,'filename':remote_name(u['id']),'task_id':receipt['task_id'],'phase':'printing','age_s':0}
        self.data.update(job=job,job_revision=2)
        # Telemetry alone is not yet the new observed history job.
        self.assertEqual((await self.service.status('owner',u['id']))['state'],'awaiting')
        self.history.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (job['id'],'192.0.2.1',job['task_id'],job['filename'],'printing',self.now,self.now,None,1,0,1,1,0));self.history.db.commit()
        for changes in ({'filename':'unrelated.gcode.3mf'},{'task_id':'-1'},{'age_s':16},{'phase':'done'}):
            self.data['job']=dict(job,**changes)
            self.assertEqual((await self.service.status('owner',u['id']))['state'],'awaiting')
        self.data['job']=job
        self.assertEqual((await self.service.status('owner',u['id']))['state'],'confirmed')
        self.assertEqual(len(self.sent),1);self.assertEqual(len(self.history.jobs()),2)
        self.assertEqual(self.history.files.linked(job['id'])['link_method'],'reprint')
        self.assertEqual(self.history.files.linked(job['id'])['source_job'],self.source)
        self.assertEqual(self.history.files.linked(job['id'])['source_filename'],'test.gcode.3mf')
        self.assertNotIn('link_method',self.history.files.linked(self.source))
    async def test_unfinished_failed_unlinked_or_different_original_sources_are_not_eligible(self):
        for state,ended in [('printing',None),('canceled',20),('offline',20)]:
            self.history.db.execute('UPDATE jobs SET state=?,ended_at=? WHERE id=?',(state,ended,self.source));self.history.db.commit()
            with self.assertRaises(ValueError):await self.prepare()
        self.history.db.execute("UPDATE jobs SET state='completed',ended_at=20 WHERE id=?",(self.source,))
        self.history.db.execute('DELETE FROM file_job_links WHERE job_id=?',(self.source,));self.history.db.commit()
        with self.assertRaises(ValueError):await self.prepare()
        self.assertEqual(self.transfers,[]);self.assertEqual(self.sent,[])
    async def test_expiration_cancel_and_shutdown_do_not_send_again(self):
        p=await self.prepare();self.now+=31
        self.assertEqual((await self.service.transfer('owner',p['id'],p['token']))['state'],'expired')
        p=await self.prepare();await self.service.cancel('owner',p['id'])
        await self.service.transfer('owner',p['id'],p['token']);self.assertEqual(self.transfers,[])
        entered=asyncio.Event()
        async def block(*args):entered.set();await asyncio.Event().wait()
        self.service.upload=block;p=await self.prepare()
        task=asyncio.create_task(self.service.transfer('owner',p['id'],p['token']))
        await entered.wait();await self.service.shutdown()
        with self.assertRaises(asyncio.CancelledError):await task


if __name__=='__main__':unittest.main()
