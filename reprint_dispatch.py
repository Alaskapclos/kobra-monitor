# SPDX-License-Identifier: GPL-3.0-only
"""Persistent two-step archive dispatch, disabled unless explicitly configured.

Transport and snapshots are injected. Existing controls share the reservation
lock. Upload success does not authorize start, and a socket write is not proof
of a started print. Restart/cancellation never resumes either write operation.
"""
import asyncio
import hashlib
import json
import math
import secrets
import sqlite3
import time
import uuid

from file_archive import digest, object_path
from reprint_preflight import inspect
from reprint_launch import mapping_for, start_payload
from reprint_transfer import remote_name

ACTIVE = ('prepared','uploading','uploaded','starting','awaiting')


class ReprintDispatch:
    def __init__(self, archive, snapshot, refresh, upload, start, *, controls=None,
                 enabled=False, clock=time.time, monotonic=time.monotonic):
        if type(enabled) is not bool:raise ValueError('Explicit archive-start mode required')
        self.archive=archive;self.snapshot=snapshot;self.refresh=refresh
        self.upload=upload;self.start=start;self.controls=controls;self.enabled=enabled
        self.clock=clock;self.monotonic=monotonic;self.deadlines={};self.closed=False;self.inflight=set();self.authorizations={};self.observer=None
        self.lock=controls.lock if controls else asyncio.Lock()
        self.db=sqlite3.connect(str(archive.root/'history.sqlite3'),isolation_level=None)
        self.db.row_factory=sqlite3.Row;self.db.execute('PRAGMA busy_timeout=3000')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS archive_dispatches(
            id TEXT PRIMARY KEY, actor TEXT NOT NULL, request_id TEXT NOT NULL,
            ip TEXT NOT NULL, sha256 TEXT NOT NULL, assignments TEXT NOT NULL,
            context TEXT NOT NULL, metadata TEXT NOT NULL, state TEXT NOT NULL,
            token TEXT NOT NULL, expires REAL NOT NULL, created REAL NOT NULL,
            updated REAL NOT NULL, receipt TEXT, detail TEXT NOT NULL,
            UNIQUE(actor,request_id));
            CREATE UNIQUE INDEX IF NOT EXISTS one_archive_dispatch_per_printer
            ON archive_dispatches(ip) WHERE state IN ('prepared','uploading','uploaded','starting','awaiting');''')
        self.db.execute("UPDATE archive_dispatches SET state='uncertain',token='',detail='Dienst neu gestartet; kein automatischer Neuversuch.' WHERE state IN ('uploading','starting','awaiting')")
        self.db.execute("UPDATE archive_dispatches SET state='expired',token='',detail='Bestätigung nach Neustart verworfen.' WHERE state IN ('prepared','uploaded')")
        if controls:controls.external_busy=self.busy

    def close(self):
        if self.closed:return
        if self.inflight:raise RuntimeError('Await shutdown before closing an active dispatcher')
        if self.observer:self.observer.cancel()
        self.closed=True
        self.db.execute("UPDATE archive_dispatches SET state='uncertain',token='',detail='Dienst beendet; Ergebnis unbestätigt.' WHERE state IN ('uploading','starting','awaiting')")
        self.db.close()

    async def shutdown(self):
        self.enabled=False
        if self.observer:
            self.observer.cancel()
            await asyncio.gather(self.observer,return_exceptions=True)
        for task in list(self.inflight):task.cancel()
        await asyncio.gather(*list(self.inflight),return_exceptions=True)
        self.close()

    def _expire(self):
        for row in self.db.execute("SELECT * FROM archive_dispatches WHERE state IN ('prepared','uploaded','awaiting')").fetchall():
            if row['expires'] <= self.clock() or self.deadlines.get(row['id'],0) <= self.monotonic():
                self._state(row['id'],'uncertain' if row['state']=='awaiting' else 'expired','Frist abgelaufen; kein automatischer Neuversuch.')

    def busy(self,ip,control=None):
        if self.closed:return False
        # An explicitly requested stop must remain possible after a start.
        if control=='print_stop':return False
        self._expire()
        return self.db.execute("SELECT 1 FROM archive_dispatches WHERE ip=? AND state IN ('prepared','uploading','uploaded','starting','awaiting')",(ip,)).fetchone() is not None

    def _row(self,actor,operation):
        if not isinstance(operation,str):raise ValueError('Ungültiger Archivvorgang.')
        row=self.db.execute('SELECT * FROM archive_dispatches WHERE id=? AND actor=?',(operation,actor)).fetchone()
        if not row:raise ValueError('Archivvorgang gehört nicht zu dieser Anmeldung.')
        return row

    def _public(self,row):
        result={k:row[k] for k in ('id','ip','sha256','state','expires','detail')}
        result['remote_filename']=remote_name(row['id'])
        metadata=json.loads(row['metadata'])
        for key in ('source_job','source_filename','nozzle_mm','materials'):result[key]=metadata[key]
        result['assignments']=json.loads(row['assignments'])
        result['selected_slots']=metadata.get('selected_slots',[])
        if row['state']=='confirmed':result['job_id']=json.loads(row['receipt']).get('job_id')
        if row['state'] in ('prepared','uploaded'):result['token']=row['token']
        return result

    def _state(self,operation,state,detail,*,lifetime=0,receipt=None):
        token=secrets.token_urlsafe(32) if state in ('prepared','uploaded') else ''
        self.db.execute('UPDATE archive_dispatches SET state=?,token=?,expires=?,updated=?,detail=?,receipt=COALESCE(?,receipt) WHERE id=?',
            (state,token,self.clock()+lifetime,self.clock(),detail,json.dumps(receipt) if receipt is not None else None,operation))
        if lifetime:self.deadlines[operation]=self.monotonic()+lifetime
        else:self.deadlines.pop(operation,None)

    def _fresh(self,ip,data=None):
        if not self.enabled or self.closed:raise PermissionError('Archiv-Druckstart nicht freigegeben.')
        if data is None:data=self.snapshot(ip)
        if not isinstance(data,dict) or data.get('enabled') is not True or data.get('model_id') != '20025' or data.get('idle') is not True:
            raise ValueError('Freigegebener Kobra S1 mit eindeutigem Leerlauf erforderlich.')
        if not all(isinstance(data.get(k),str) and 0 < len(data[k]) <= 256 for k in ('connection_id','idle_context','material_context')):
            raise ValueError('Aktuelle Druckerverbindung fehlt.')
        if data.get('ace_connection_id')!=data['connection_id']:
            raise ValueError('ACE-Daten gehören nicht zur aktuellen Verbindung.')
        for key in ('idle_age_s','ace_age_s'):
            age=data.get(key)
            if type(age) not in (float,int) or not math.isfinite(age) or not 0 <= age <= 15:
                raise ValueError('Drucker- oder ACE-Daten sind nicht frisch genug.')
        return data

    def _permitted(self,ip):
        if not self.enabled or self.closed:raise PermissionError('Archiv-Druckstart nicht freigegeben.')
        data=self.snapshot(ip)
        if not isinstance(data,dict) or data.get('enabled') is not True or data.get('model_id')!='20025':
            raise PermissionError('Dieser Drucker ist nicht für Archivübertragung und Start freigegeben.')

    def _context(self,ip,metadata,assignments,data=None):
        data=self._fresh(ip,data)
        mapping=mapping_for(metadata['materials'],assignments,data.get('slots'))
        selected={a['slot'] for a in assignments}
        identity={'connection':data['connection_id'],'idle_context':data['idle_context'],'material_context':data['material_context'],
            'slots':[{k:s.get(k) for k in ('global_index','index','box_id','status','edit_status','type','color','sku')}
                     for s in sorted(data['slots'],key=lambda s:s['global_index']) if s['global_index'] in selected]}
        return hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest(),mapping,data

    def _guard(self,row):
        try:
            if row['id'] in self.authorizations and self.authorizations[row['id']]() is not True:return False
            self.eligible(json.loads(row['metadata'])['source_job'],row['sha256'])
            context,_,_=self._context(row['ip'],json.loads(row['metadata']),json.loads(row['assignments']))
            return context==row['context']
        except (ValueError,PermissionError,TypeError,KeyError):return False

    def matches_snapshot(self,row,data):
        """Final socket-lock guard: caller supplies telemetry without locking socket again."""
        try:
            if self.authorizations.get(row['id'],lambda:False)() is not True:return False
            context,_,_=self._context(row['ip'],json.loads(row['metadata']),json.loads(row['assignments']),data)
            return context==row['context']
        except (ValueError,PermissionError,TypeError,KeyError):return False

    def eligible(self,job,sha256):
        if not isinstance(job,str) or len(job)!=32:raise ValueError('Erfolgreich abgeschlossener Quellauftrag fehlt.')
        with self.archive.h.lock:
            source=self.archive.h.db.execute("SELECT * FROM jobs WHERE id=? AND state='completed' AND ended_at IS NOT NULL",(job,)).fetchone()
            linked=self.archive.linked(job)
        if not source or not linked or linked['sha256']!=sha256:
            raise ValueError('Nur erfolgreich abgeschlossene Aufträge mit zugeordnetem Original können wiederholt werden.')
        return dict(source)

    def _control_free(self,ip):
        if not self.controls:return
        self.controls._expire()
        if self.controls.motion_wait(ip)>0 or self.controls.db.execute("SELECT 1 FROM control_attempts WHERE ip=? AND state IN ('prepared','sending','awaiting')",(ip,)).fetchone():
            raise ValueError('Andere Druckeraktion oder Bewegung kann noch laufen.')

    async def prepare(self,actor,request_id,ip,sha256,assignments,*,source_job,authorized=lambda:True):
        self._permitted(ip)
        source=self.eligible(source_job,sha256)
        if not isinstance(actor,str) or not 1 <= len(actor) <= 128:raise ValueError('Besitzeranmeldung erforderlich.')
        if not isinstance(request_id,str) or str(uuid.UUID(request_id)) != request_id:raise ValueError('Ungültige Vorgangskennung.')
        path=object_path(self.archive.root,sha256)
        with self.archive.h.lock:
            exists=self.archive.h.db.execute('SELECT 1 FROM archived_print_files WHERE sha256=?',(sha256,)).fetchone()
        if not exists or path.is_symlink() or not path.is_file():raise ValueError('Archivoriginal fehlt.')
        # Worker is pure local reading; it cannot send even if HTTP is cancelled.
        def read():
            if digest(path)!=sha256:raise ValueError('Originalprüfsumme stimmt nicht.')
            metadata=inspect(path)
            if digest(path)!=sha256:raise ValueError('Original während der Vorprüfung geändert.')
            return metadata
        metadata=await asyncio.to_thread(read)
        metadata['prior_job_ids']=[j['id'] for j in self.archive.h.jobs(ip)]
        metadata['source_job']=source_job;metadata['source_filename']=source['filename']
        await self.refresh(ip)
        async with self.lock:
            if authorized() is not True:raise PermissionError('Anmeldung abgelaufen; neu anmelden.')
            self._expire();self._control_free(ip)
            context,_,target=self._context(ip,metadata,assignments)
            selected={a['slot'] for a in assignments}
            metadata['selected_slots']=[{k:s.get(k) for k in ('global_index','type','color','sku')}
                for s in target['slots'] if s['global_index'] in selected]
            canonical=json.dumps(assignments,sort_keys=True)
            old=self.db.execute('SELECT * FROM archive_dispatches WHERE actor=? AND request_id=?',(actor,request_id)).fetchone()
            if old:
                if ((old['ip'],old['sha256'],old['assignments']) != (ip,sha256,canonical) or
                        json.loads(old['metadata'])['source_job']!=source_job):raise ValueError('Vorgangskennung bereits anders verwendet.')
                return self._public(old)
            if self.busy(ip):raise ValueError('Für diesen Drucker läuft bereits ein Archivvorgang.')
            operation=uuid.uuid4().hex;now=self.clock()
            self.db.execute('INSERT INTO archive_dispatches VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (operation,actor,request_id,ip,sha256,canonical,context,json.dumps(metadata),'prepared','',now,now,now,None,''))
            self._state(operation,'prepared','Datei und ACE-Auswahl geprüft. Noch nicht übertragen.',lifetime=30)
            return self._public(self._row(actor,operation))

    async def transfer(self,actor,operation,token,*,authorized=lambda:True):
        async with self.lock:
            if authorized() is not True:raise PermissionError('Anmeldung abgelaufen; keine Übertragung.')
            self._expire();row=self._row(actor,operation)
            if row['state']!='prepared':return self._public(row)
            if not isinstance(token,str) or not secrets.compare_digest(token,row['token']):raise ValueError('Bestätigung ungültig.')
            self._control_free(row['ip'])
            if not self._guard(row):raise ValueError('Drucker oder Filamentzuordnung geändert; neu vorbereiten.')
            self._state(operation,'uploading','Übertragung läuft. Kein Druckstart ausgelöst.')
            self.authorizations[operation]=authorized
        task=asyncio.current_task();self.inflight.add(task)
        try:
            async with asyncio.timeout(125):receipt=await self.upload(row,lambda:self._guard(row))
            if (not isinstance(receipt,dict) or receipt.get('sha256') != row['sha256'] or
                    receipt.get('remote_filename') != remote_name(operation) or receipt.get('storage_acknowledged') is not True):
                raise ValueError('Übertragungsbeleg stimmt nicht.')
            # Validate all launch fields now, before offering the second confirmation.
            _,mapping,_=self._context(row['ip'],json.loads(row['metadata']),json.loads(row['assignments']))
            if not self._guard(row):raise ValueError('Druckerzustand während Übertragung geändert.')
            start_payload(operation,receipt.get('md5'),receipt.get('bytes'),mapping)
            self._state(operation,'uploaded','Speicherung bestätigt. Druckstart muss separat bestätigt werden.',lifetime=300,receipt=receipt)
        except asyncio.CancelledError:
            self._state(operation,'uncertain','Übertragung unterbrochen; nicht erneut gesendet.');raise
        except Exception:
            self._state(operation,'uncertain','Übertragung oder Zustand nicht eindeutig bestätigt; kein automatischer Neuversuch.')
        finally:self.inflight.discard(task);self.authorizations.pop(operation,None)
        return self._public(self._row(actor,operation))

    async def launch(self,actor,operation,token,*,bed_clear,nozzle_mm,material_ready,authorized=lambda:True):
        # This is a new deliberate confirmation after the transfer, not a token
        # inherited from prepare or an automatic consequence of successful upload.
        row=self._row(actor,operation)
        if row['state']!='uploaded':return self._public(row)
        if bed_clear is not True or material_ready is not True or type(nozzle_mm) not in (int,float) or nozzle_mm!=json.loads(row['metadata'])['nozzle_mm']:
            raise ValueError('Freies Druckbett, passende eingebaute Düse und bereitstehendes Material bestätigen.')
        self._permitted(row['ip'])
        await self.refresh(row['ip'])
        async with self.lock:
            if authorized() is not True:raise PermissionError('Anmeldung abgelaufen; kein Start.')
            self._expire();row=self._row(actor,operation)
            if row['state']!='uploaded':return self._public(row)
            if not isinstance(token,str) or not secrets.compare_digest(token,row['token']):raise ValueError('Startbestätigung ungültig.')
            self._control_free(row['ip'])
            if not self._guard(row):raise ValueError('Drucker oder Filamentzuordnung geändert; kein Start.')
            _,mapping,data=self._context(row['ip'],json.loads(row['metadata']),json.loads(row['assignments']))
            receipt=json.loads(row['receipt']);payload=start_payload(operation,receipt['md5'],receipt['bytes'],mapping)
            revision=data.get('job_revision')
            if type(revision) is not int or revision<0:raise ValueError('Aktuelle Auftragsrevision fehlt.')
            self._state(operation,'starting','Start wird einmalig gesendet. Noch keine Druckerbestätigung.')
            self.authorizations[operation]=authorized
        task=asyncio.current_task();self.inflight.add(task)
        try:
            async with asyncio.timeout(8):await self.start(row,receipt,mapping,data['connection_id'],lambda:self._guard(row))
            self._state(operation,'awaiting','Start gesendet; bestätigten Beginn abwarten.',lifetime=30,
                        receipt=dict(receipt,task_id=payload['taskid'],connection_id=data['connection_id'],before_job_revision=revision))
            if self.observer is None:self.observer=asyncio.create_task(self._observe())
        except asyncio.CancelledError:
            self._state(operation,'uncertain','Start unterbrochen; Ergebnis unbestätigt, kein Neuversuch.');raise
        except Exception:
            self._state(operation,'uncertain','Start nicht eindeutig bestätigt; Drucker prüfen, nicht automatisch wiederholen.')
        finally:self.inflight.discard(task);self.authorizations.pop(operation,None)
        return self._public(self._row(actor,operation))

    async def status(self,actor,operation):
        async with self.lock:
            self._expire();row=self._row(actor,operation)
            if row['state']=='awaiting':
                data=self.snapshot(row['ip']) or {};job=data.get('job') or {};receipt=json.loads(row['receipt'])
                age=job.get('age_s');revision=data.get('job_revision')
                fresh=(type(age) in (int,float) and math.isfinite(age) and 0<=age<=15 and
                       type(revision) is int and revision>receipt['before_job_revision'])
                if (fresh and data.get('connected') is True and data.get('connection_id')==receipt['connection_id'] and
                        job.get('filename')==remote_name(operation) and job.get('task_id')==receipt['task_id'] and
                        job.get('phase') in ('init','checking','preheating','auto_leveling','printing','paused') and
                        job.get('id') not in json.loads(row['metadata'])['prior_job_ids']):
                    with self.archive.h.lock:
                        observed=self.archive.h.db.execute('SELECT * FROM jobs WHERE id=? AND ip=? AND filename=? AND identity=? AND first_seen>=? AND ended_at IS NULL',
                            (job.get('id'),row['ip'],job['filename'],job['task_id'],row['created'])).fetchone()
                    if observed:
                        def associate():
                            self.archive.link(observed['id'],row['sha256'],method='reprint',source_job=json.loads(row['metadata'])['source_job'])
                            if self.archive.h.reports.job(observed['id'])['ended_at'] is not None:
                                self.archive.h.reports.freeze(observed['id'],reason='Original aus bestätigter Archivwiederholung zugeordnet')
                        try:
                            task=asyncio.create_task(asyncio.to_thread(associate))
                            try:await asyncio.shield(task)
                            except asyncio.CancelledError:await task;raise
                            detail='Neuer Druckauftrag bestätigt und Archivoriginal zugeordnet.'
                        except (OSError,ValueError):detail='Neuer Druckauftrag bestätigt. Archivzuordnung bitte prüfen.'
                        self._state(operation,'confirmed',detail,receipt=dict(receipt,job_id=observed['id']))
            return self._public(self._row(actor,operation))

    async def _observe(self):
        """Read feedback even after the phone tab closes. Never sends commands."""
        try:
            while not self.closed:
                rows=self.db.execute("SELECT actor,id FROM archive_dispatches WHERE state='awaiting'").fetchall()
                if not rows:return
                for row in rows:
                    try:await self.status(row['actor'],row['id'])
                    except (ValueError,OSError,sqlite3.Error):pass
                await asyncio.sleep(1)
        finally:self.observer=None

    async def cancel(self,actor,operation):
        async with self.lock:
            row=self._row(actor,operation)
            if row['state'] in ('prepared','uploaded'):
                self._state(operation,'cancelled','Weiterer Ablauf verworfen. Bereits übertragene Druckerdatei bleibt erhalten.')
            return self._public(self._row(actor,operation))
