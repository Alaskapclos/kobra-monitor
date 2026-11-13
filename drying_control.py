# SPDX-License-Identifier: GPL-3.0-only
"""Single-use, connection/ACE-bound drying intents; no optimistic device state."""
import asyncio
import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from ace_climate import drying_options


class DryingAdapter:
    def __init__(self,monitor,enabled=False,maximum=55):
        if type(enabled) is not bool or type(maximum) is not int or maximum not in (55,65):raise ValueError('Explicit drying capability required')
        self.monitor=monitor;self.enabled=enabled;self.maximum=maximum

    def snapshot(self,box,*,epoch=None,client=None):
        m=self.monitor;c=m.client
        if not self.enabled or not c or str(c.mode_id)!='20025' or (client is not None and c is not client):return None
        if client is None:epoch=c.control_connection_id()
        t=m.telemetry
        with t.lock:
            units=t.climate.public(epoch,t.connected)
            u=next((u for u in units if u['id']==box),None)
            if not u:return None
            context=hashlib.sha256((t.climate.generation+t.material_context+t.job_token).encode()).hexdigest()
            return dict(u,max_temperature=self.maximum,online=bool(t.connected and epoch),connection=epoch,context=context)

    async def send(self,row,guard):
        m=self.monitor;c=m.client;epoch=row['connection'];before=json.loads(row['before_value'])
        def locked_guard():
            state=self.snapshot(row['box'],epoch=epoch,client=c)
            return guard() and state is not None and state['context']==row['context'] and state['online'] and state['current'].get('status') and state['ages'].get('status',999)<=15 and state.get('status')==before['status'] and all(state.get(k)==v for k,v in before.items())
        if c is None:raise ValueError('Druckerverbindung fehlt.')
        await asyncio.to_thread(c.send_drying_once,row['box'],json.loads(row['options']),epoch,
                               send_deadline=time.monotonic()+4,job_guard=locked_guard)
        # This is read-only and cannot replay the write.
        await asyncio.to_thread(c.publish,'multiColorBox','getInfo',None,.5)


class DryingControls:
    def __init__(self,database,snapshot,sender,controls,archive,clock=time.time,monotonic=time.monotonic,confirmation_timeout=12):
        self.snapshot=snapshot;self.sender=sender;self.controls=controls;self.archive=archive
        self.clock=clock;self.monotonic=monotonic;self.timeout=confirmation_timeout;self.deadlines={};self.inflight=set();self.closed=False
        self.lock=controls.lock
        self.db=sqlite3.connect(str(database),isolation_level=None);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=3000')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS ace_drying_attempts(
          id TEXT PRIMARY KEY,actor TEXT NOT NULL,request_id TEXT NOT NULL,ip TEXT NOT NULL,box INTEGER NOT NULL,
          options TEXT NOT NULL,before_value TEXT NOT NULL,connection TEXT NOT NULL,context TEXT NOT NULL,
          revision INTEGER NOT NULL,state TEXT NOT NULL,token TEXT NOT NULL,created REAL NOT NULL,detail TEXT NOT NULL,
          UNIQUE(actor,request_id));
          CREATE UNIQUE INDEX IF NOT EXISTS one_active_drying ON ace_drying_attempts(ip) WHERE state IN ('prepared','sending','awaiting');''')
        self.db.execute("UPDATE ace_drying_attempts SET state='uncertain',token='',detail='Dienst neu gestartet; kein automatischer Neuversuch.' WHERE state IN ('prepared','sending','awaiting')")
        controls.external_busy=lambda ip,control:False if control=='print_stop' else self.busy(ip) or archive.busy(ip,control)
        self.previous_archive_busy=archive.busy
        # Archive starts also honor drying reservations through the shared guard.
        archive.busy=lambda ip,control=None:False if control=='print_stop' else self.busy(ip) or self.previous_archive_busy(ip,control)

    def close(self):
        if self.closed:return
        if self.inflight:raise RuntimeError('Drying shutdown must await active operations')
        self.closed=True;self.db.execute("UPDATE ace_drying_attempts SET state='uncertain',token='',detail='Dienst beendet; Ergebnis unbestätigt.' WHERE state IN ('prepared','sending','awaiting')");self.db.close()

    async def shutdown(self):
        for task in list(self.inflight):task.cancel()
        await asyncio.gather(*list(self.inflight),return_exceptions=True);self.close()

    def busy(self,ip):
        if self.closed:return False
        for row in self.db.execute("SELECT id FROM ace_drying_attempts WHERE state='prepared'").fetchall():
            if self.monotonic()>=self.deadlines.get(row['id'],float('-inf')):self._state(row['id'],'expired','Bestätigung abgelaufen.')
        return self.db.execute("SELECT 1 FROM ace_drying_attempts WHERE ip=? AND state IN ('prepared','sending','awaiting')",(ip,)).fetchone() is not None

    def _row(self,actor,id):
        if not isinstance(id,str):raise ValueError('Ungültiger Vorgang.')
        row=self.db.execute('SELECT * FROM ace_drying_attempts WHERE id=? AND actor=?',(id,actor)).fetchone()
        if row is None:raise ValueError('Dieser Vorgang gehört nicht zu deiner Anmeldung.')
        return row

    def _public(self,row):
        out={k:row[k] for k in ('id','ip','box','state','detail')};out['options']=json.loads(row['options'])
        if row['state']=='prepared':out['token']=row['token']
        return out

    def _state(self,id,state,detail):
        self.db.execute('UPDATE ace_drying_attempts SET state=?,detail=?,token=\'\' WHERE id=?',(state,detail,id));self.deadlines.pop(id,None)

    def fresh(self,ip,box):
        if type(box) is not int or not 0<=box<=3:raise ValueError('Ungültiges ACE-Gerät.')
        s=self.snapshot(ip,box)
        if not s or not s.get('online') or not s.get('connection') or not s.get('context') or type(s.get('status')) is not int or s['status'] not in (0,1) or not s.get('current',{}).get('status') or not 0<=s.get('ages',{}).get('status',999)<=15:
            raise ValueError('Aktuelle bestätigte ACE-Daten fehlen oder Trocknung ist nicht freigegeben.')
        return s

    async def prepare(self,actor,ip,box,on,temperature,duration,request_id,authorized=lambda:True):
        if not isinstance(ip,str) or not isinstance(request_id,str) or str(uuid.UUID(request_id))!=request_id:raise ValueError('Ungültiger Steuerauftrag.')
        async with self.lock:
            if self.closed or not authorized():raise PermissionError('Bitte erneut anmelden.')
            s=self.fresh(ip,box);opts=drying_options(on,temperature,duration,maximum=s.get('max_temperature',55))
            old=self.db.execute('SELECT * FROM ace_drying_attempts WHERE actor=? AND request_id=?',(actor,request_id)).fetchone()
            if old:
                if old['ip']!=ip or old['box']!=box or json.loads(old['options'])!=opts:raise ValueError('Vorgangskennung bereits anders verwendet.')
                self.busy(ip);return self._public(self._row(actor,old['id']))
            self.controls._expire()
            if self.busy(ip) or self.previous_archive_busy(ip) or self.controls.db.execute("SELECT 1 FROM control_attempts WHERE ip=? AND state IN ('prepared','sending','awaiting')",(ip,)).fetchone():raise ValueError('Für diesen Drucker läuft bereits ein Steuervorgang.')
            s=self.fresh(ip,box)
            before={k:s.get(k) for k in ('status','target_temp','duration','configuration')}
            same=all(s.get(k)==v for k,v in opts.items() if k!='remain_time')
            id=uuid.uuid4().hex;state='unchanged' if same else 'prepared';token=secrets.token_urlsafe(32) if not same else ''
            self.db.execute('INSERT INTO ace_drying_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(id,actor,request_id,ip,box,json.dumps(opts),json.dumps(before),s['connection'],s['context'],s['revision'],state,token,self.clock(),'Bereits so gemeldet; kein Befehl.' if same else 'Vorbereitet; noch nicht gesendet.'))
            self.deadlines[id]=self.monotonic()+20
            return self._public(self._row(actor,id))

    async def action(self,actor,id,action,token=None,authorized=lambda:True):
        async with self.lock:
            row=self._row(actor,id);self.busy(row['ip']);row=self._row(actor,id)
            if action=='cancel' and row['state']=='prepared':self._state(id,'cancelled','Ohne Versand verworfen.')
            if action!='execute' or row['state']!='prepared':return self._public(self._row(actor,id))
            if self.closed or not authorized():raise PermissionError('Bitte erneut anmelden.')
            if not isinstance(token,str) or not secrets.compare_digest(token,row['token']):raise ValueError('Ungültige Bestätigung.')
            if self.previous_archive_busy(row['ip']):raise ValueError('Archivvorgang läuft; nicht gesendet.')
            s=self.fresh(row['ip'],row['box']);before=json.loads(row['before_value'])
            if s['connection']!=row['connection'] or s['context']!=row['context'] or any(s.get(k)!=v for k,v in before.items()):
                self._state(id,'rejected','ACE, Druckauftrag oder Zustand gewechselt.');raise ValueError('ACE-Zustand geändert; bitte erneut öffnen.')
            self.db.execute("UPDATE ace_drying_attempts SET state='sending',token='',revision=?,detail='Einmaliger Versand angefordert.' WHERE id=?",(s['revision'],id));row=self._row(actor,id)
            task=asyncio.current_task();self.inflight.add(task)
        try:
            await asyncio.wait_for(self.sender(row,authorized),5)
            self._state(id,'awaiting','Befehl gesendet; Rückmeldung wird geprüft.')
            deadline=asyncio.get_running_loop().time()+self.timeout;opts=json.loads(row['options'])
            while asyncio.get_running_loop().time()<deadline:
                s=self.fresh(row['ip'],row['box'])
                if s['connection']!=row['connection'] or s['context']!=row['context']:raise ValueError('ACE oder Verbindung gewechselt.')
                fields=['status','target_temp','duration'] if opts['status'] else ['status']
                if s['revision']>row['revision'] and all(s.get(k)==opts[k] and s['current'].get(k) and 0<=s['ages'].get(k,999)<=15 for k in fields):
                    self._state(id,'confirmed','Trocknung vom Drucker bestätigt.');break
                await asyncio.sleep(.1)
            else:self._state(id,'uncertain','Ausgang nicht bestätigt. Kein automatischer Neuversuch.')
        except asyncio.CancelledError:
            self._state(id,'uncertain','Prüfung unterbrochen; kein automatischer Neuversuch.');raise
        except Exception:
            self._state(id,'uncertain','Ausgang unklar; Drucker prüfen. Kein automatischer Neuversuch.')
        finally:self.inflight.discard(task)
        return self._public(self._row(actor,id))
