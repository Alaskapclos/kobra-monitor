"""Durable local observation history. No printer-control operations.
SPDX-License-Identifier: GPL-3.0-only
"""
import json
from pathlib import Path
import sqlite3
import threading
import time
import uuid

ACTIVE={'printing','busy','paused','pause','pausing','resuming','preheating','auto_leveling','checking','init'}
PREPARING={'preheating','auto_leveling','checking','init'}
TERMINAL={'finished','finish','complete','completed','canceled','cancelled','stoped','stopped'}


class History:
    def __init__(self,path,clock=time.time):
        Path(path).parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.clock=clock
        self.lock=threading.RLock()
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.create_function('casefold',1,lambda value:str(value or '').casefold(),deterministic=True)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,ip TEXT,identity TEXT,filename TEXT,
            state TEXT,first_seen REAL,last_seen REAL,ended_at REAL,observed_start INTEGER,
            progress REAL,layer INTEGER,total_layers INTEGER,elapsed_minutes REAL);
          CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ip TEXT,job_id TEXT,at REAL,kind TEXT,details TEXT);
          CREATE TABLE IF NOT EXISTS samples(id INTEGER PRIMARY KEY,ip TEXT,job_id TEXT,at REAL,data TEXT);
        ''')
        # Only live idle observations establish start coverage, never cached
        # samples from before a restart or a disconnected session.
        self.links={}; self.idle={}; self.idle_seen={}; self.last_sample={}

    def link(self,ip,connected):
        with self.lock:
            if self.links.get(ip)==connected:return
            self.links[ip]=connected
            if not connected:
                self.idle[ip]=False
                self.idle_seen.pop(ip,None)
            self._event(ip,None,'connected' if connected else 'disconnected',{})
            self.db.commit()

    def _event(self,ip,job_id,kind,details):
        self.db.execute('INSERT INTO events(ip,job_id,at,kind,details) VALUES(?,?,?,?,?)',
                        (ip,job_id,self.clock(),kind,json.dumps(details,ensure_ascii=False)))

    def observe(self,ip,kind,payload,snapshot):
        if payload.get('code') not in (None,200):
            if kind in ('info','print') and payload.get('state') in ('pause','paused','error','fault'):
                with self.lock:
                    current=self.db.execute('SELECT id FROM jobs WHERE ip=? AND ended_at IS NULL ORDER BY first_seen DESC LIMIT 1',(ip,)).fetchone()
                    state='paused' if payload.get('state') in ('pause','paused') else 'error'
                    if current:self.db.execute('UPDATE jobs SET state=?,last_seen=? WHERE id=?',(state,self.clock(),current['id']))
                    self._event(ip,current['id'] if current else None,'printer_error',{'code':payload.get('code'),'state':state,'message':str(payload.get('msg',''))[:500]})
                    self.db.commit()
            return
        data=payload.get('data')
        if not isinstance(data,dict):return
        with self.lock:
            current=self.db.execute("SELECT * FROM jobs WHERE ip=? AND ended_at IS NULL ORDER BY first_seen DESC LIMIT 1",(ip,)).fetchone()
            project=None;previous=False
            if kind=='info':
                project=data.get('project')
                if not isinstance(project,dict):
                    project=data.get('last_project');previous=True
                    if data.get('state')=='free':
                        self.idle[ip]=True
                        self.idle_seen[ip]=self.clock()
                    else:project=None
            elif kind=='print':
                project=dict(data)
                project['state']=payload.get('state')
            if isinstance(project,dict):
                state=project.get('state','')
                if state in ('printing','busy') and project.get('pause')==1:state='paused'
                identity=str(project.get('task_id') or project.get('taskid') or '')
                if identity in ('-1','0'):identity=''
                filename=project.get('filename') or (current['filename'] if current else '')
                if state in ACTIVE and not previous:
                    if current and identity and current['identity'] not in ('','-1','0') and identity!=current['identity']:
                        self.db.execute('UPDATE jobs SET state=?,ended_at=? WHERE id=?',('unknown_end',self.clock(),current['id']))
                        self._event(ip,current['id'],'unobserved_end',{})
                        current=None
                    now=self.clock()
                    if current is None:
                        job_id=uuid.uuid4().hex
                        recent_idle=(self.idle.get(ip) and
                                     0<=now-self.idle_seen.get(ip,float('-inf'))<=90)
                        # Preparation may carry the previous job's elapsed time
                        # and progress. Its explicit state establishes the start.
                        observed=bool(recent_idle and (state in PREPARING or
                                      (not project.get('print_time') and project.get('progress',0)<=1)))
                        self.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (job_id,ip,identity,filename,state,now,now,None,int(observed),project.get('progress',0),project.get('curr_layer',0),project.get('total_layers',0),project.get('print_time',0)))
                        self._event(ip,job_id,'start_observed' if observed else 'active_job_discovered',{'filename':filename,'state':state})
                    else:
                        job_id=current['id']
                        if current['state']!=state:self._event(ip,job_id,'state',{'from':current['state'],'to':state})
                        self.db.execute('UPDATE jobs SET identity=?,filename=?,state=?,last_seen=?,progress=?,layer=?,total_layers=?,elapsed_minutes=? WHERE id=?',
                            (identity or current['identity'],filename,state,now,project.get('progress',current['progress']),project.get('curr_layer',current['layer']),project.get('total_layers',current['total_layers']),project.get('print_time',current['elapsed_minutes']),job_id))
                    self.idle[ip]=False
                    current=self.db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
                elif state in TERMINAL and current:
                    same=(identity==current['identity']) if identity and current['identity'] not in ('','-1','0') else Path(filename).name==Path(current['filename']).name
                    if same:
                        result='completed' if state in ('finished','finish','complete','completed') else 'cancelled'
                        self.db.execute('UPDATE jobs SET state=?,last_seen=?,ended_at=?,progress=?,layer=?,total_layers=? WHERE id=?',
                            (result,self.clock(),self.clock(),project.get('progress',current['progress']),project.get('curr_layer',current['layer']),project.get('total_layers',current['total_layers']),current['id']))
                        self._event(ip,current['id'],result,{})
                        self.idle[ip]=True
                        self.idle_seen[ip]=self.clock()
            if snapshot.get('data') and self.clock()-self.last_sample.get(ip,0)>=15:
                self.last_sample[ip]=self.clock()
                self.db.execute('INSERT INTO samples(ip,job_id,at,data) VALUES(?,?,?,?)',
                    (ip,current['id'] if current else None,self.clock(),json.dumps(snapshot,ensure_ascii=False)))
            self.db.commit()

    def jobs(self,ip=None):
        with self.lock:
            rows=self.db.execute('SELECT * FROM jobs '+('WHERE ip=? ' if ip else '')+'ORDER BY first_seen DESC LIMIT 50',(ip,) if ip else ()).fetchall()
            return [dict(row) for row in rows]

    def events(self,limit=50):
        with self.lock:
            return [dict(row) for row in self.db.execute('SELECT * FROM events ORDER BY id DESC LIMIT ?',(limit,)).fetchall()]

    def archive(self,ip,search='',state='all',page=0):
        if state not in ('all','active','completed','cancelled','unknown_end'):
            raise ValueError('Unknown archive filter')
        if not isinstance(page,int) or page<0 or page>1000000 or len(search)>200:
            raise ValueError('Invalid archive query')
        with self.lock:
            where=['ip=?'];params=[ip]
            if search:
                where.append('instr(casefold(filename),casefold(?))>0');params.append(search)
            if state=='active':where.append('ended_at IS NULL')
            elif state!='all':where.append('state=?');params.append(state)
            clause=' AND '.join(where)
            total=self.db.execute('SELECT count(*) FROM jobs WHERE '+clause,params).fetchone()[0]
            size=10;pages=max(1,(total+size-1)//size);page=min(page,pages-1)
            rows=self.db.execute('SELECT * FROM jobs WHERE '+clause+' ORDER BY first_seen DESC,id DESC LIMIT ? OFFSET ?',
                                 (*params,size,page*size)).fetchall()
            summary=dict(self.db.execute('''SELECT count(*) AS total,
                coalesce(sum(state='completed'),0) AS completed,
                coalesce(sum(state='cancelled'),0) AS cancelled,
                coalesce(sum(ended_at IS NULL),0) AS active
                FROM jobs WHERE ip=?''',(ip,)).fetchone())
            return {'read_only':True,'ip':ip,'jobs':[dict(row) for row in rows],
                    'total':total,'page':page,'pages':pages,'page_size':size,'summary':summary}

    def report(self,job_id):
        from print_report import render_report
        with self.lock:
            row=self.db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
            if row is None:return None
            job=dict(row)
            end=job['ended_at'] if job['ended_at'] is not None else job['last_seen']
            # Include the terminal sample, written just after ended_at.
            samples=[{'at':r['at'],'data':json.loads(r['data'])} for r in self.db.execute(
                'SELECT at,data FROM samples WHERE ip=? AND job_id=? AND at>=? AND at<=? ORDER BY at',
                (job['ip'],job_id,job['first_seen'],end+1))]
            events=[{**dict(r),'details':json.loads(r['details'])} for r in self.db.execute(
                'SELECT * FROM events WHERE ip=? AND at>=? AND at<=? AND (job_id=? OR job_id IS NULL) ORDER BY at',
                (job['ip'],job['first_seen'],end+1,job_id))]
            return render_report(job,samples,events)

    def timeline(self,job_id):
        import math
        with self.lock:
            row=self.db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
            if row is None:return None
            job=dict(row)
            end=job['ended_at'] if job['ended_at'] is not None else job['last_seen']
            points=[]
            for row in self.db.execute(
                    'SELECT at,data FROM samples WHERE ip=? AND job_id=? AND at>=? AND at<=? ORDER BY at',
                    (job['ip'],job_id,job['first_seen'],end+1)):
                snap=json.loads(row['data']);data=snap.get('data') or {}
                age=(snap.get('section_age_s') or {}).get('temperature')
                valid=(snap.get('connection') not in ('offline','stale') and
                       (age is None or age<=90))
                point={'at':row['at']}
                for key in ('nozzle_temp','bed_temp','nozzle_target','bed_target'):
                    value=data.get(key)
                    point[key]=value if valid and isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else None
                points.append(point)
            events=[]
            for row in self.db.execute(
                    'SELECT at,kind,details FROM events WHERE ip=? AND at>=? AND at<=? AND (job_id=? OR job_id IS NULL) ORDER BY at',
                    (job['ip'],job['first_seen'],end+1,job_id)):
                details=json.loads(row['details'])
                events.append({'at':row['at'],'kind':row['kind'],
                    'state':details.get('state'),'from':details.get('from'),'to':details.get('to')})
            return {'read_only':True,'job':job,'points':points,'events':events}

    def close(self):
        with self.lock:self.db.close()
