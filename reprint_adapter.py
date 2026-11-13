# SPDX-License-Identifier: GPL-3.0-only
"""Server-only bindings between archive dispatch and one independently guarded S1."""
import asyncio
import copy
import time

from file_archive import object_path
from reprint_transfer import upload_original


class ReprintAdapter:
    def __init__(self,monitor,enabled=False):
        if type(enabled) is not bool:raise ValueError('Explicit archive-start permission required')
        self.monitor=monitor;self.enabled=enabled

    def snapshot(self,*,epoch=None,locked_client=None):
        m=self.monitor;client=m.client
        supported=bool(self.enabled and client and str(client.mode_id)=='20025')
        if not supported or (locked_client is not None and client is not locked_client):return None
        # locked_client means the caller ALREADY holds this client's socket lock.
        # No socket-lock acquisition or History lookup is permitted in that path.
        if locked_client is None:epoch=client.control_connection_id()
        t=m.telemetry
        with t.lock:
            motion=t.motion.snapshot(epoch,t.connected)
            p=t.print_job
            result={'enabled':True,'connected':bool(t.connected and epoch),'model_id':'20025','connection_id':epoch,
                'idle':motion['online'],'idle_context':motion['context'],'idle_age_s':motion['light_age_s'],
                'ace_connection_id':t.ace_connection,'ace_age_s':max(0,t.clock()-t.seen.get('ace',float('-inf'))),
                'material_context':t.material_context,'slots':copy.deepcopy(t.data.get('ace_slots',[])),
                'job_revision':p.revision,'job':None}
            job=(p.task,p.filename,p.phase,p.connection,max(0,p.clock()-p.seen))
        if locked_client is None and result['connected'] and job[2] in (1,2,5) and job[3]==epoch and m.history:
            matches=[j for j in m.history.jobs(m.ip) if j['ended_at'] is None and j['identity']==job[0] and j['filename']==job[1]]
            if len(matches)==1:
                result['job']={'id':matches[0]['id'],'task_id':job[0],'filename':job[1],
                    'phase':'printing' if job[2]==1 else 'paused' if job[2]==2 else 'auto_leveling','age_s':job[4]}
        return result

    async def refresh(self):
        m=self.monitor;client=m.client
        if not self.enabled or not client or str(client.mode_id)!='20025' or not client.control_connection_id():
            raise ValueError('Archiv-Druckstart für diesen Drucker nicht verfügbar.')
        for kind,action in (('info','query'),('multiColorBox','getInfo')):
            await asyncio.wait_for(asyncio.to_thread(client.publish,kind,action,None,1),2)

    async def upload(self,row,guard):
        m=self.monitor;client=m.client
        if not self.enabled or not client or str(client.mode_id)!='20025':raise PermissionError('Archivübertragung nicht freigegeben.')
        epoch=client.control_connection_id();t=m.telemetry
        with t.lock:url=t.archive_upload_url
        def current():
            if m.client is not client or client.control_connection_id()!=epoch or not guard():return False
            with t.lock:
                return (t.archive_upload_url==url and t.upload_connection==epoch and
                        0<=t.clock()-t.upload_seen<=15)
        return await upload_original(object_path(m.history.files.root,row['sha256']),row['sha256'],row['id'],
            ip=m.ip,reported_url=url,guard=current,enabled=self.enabled)

    async def start(self,dispatch,row,receipt,mapping,epoch,guard):
        m=self.monitor;client=m.client
        if not self.enabled or not client or not guard():raise ValueError('Druckerzustand geändert; kein Start.')
        def locked_guard():
            data=self.snapshot(epoch=epoch,locked_client=client)
            return data is not None and dispatch.matches_snapshot(row,data)
        await asyncio.to_thread(client.send_archive_start_once,row['id'],receipt['md5'],receipt['bytes'],mapping,epoch,
            send_deadline=time.monotonic()+4,job_guard=locked_guard)
