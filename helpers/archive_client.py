#!/usr/bin/env python3
"""Anycubic Slicer Next send-cache collector; never changes or starts a printer.
SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import base64
import contextlib
try:
    import fcntl
except ImportError:
    fcntl = None
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from file_archive import MAX_FILE, MAX_TOTAL, RESERVE, digest, filename, validate_package


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Weiterleitung verweigert; Monitor-Adresse prüfen.')


def read_config(path):
    value = json.loads(Path(path).read_text())
    url = urllib.parse.urlsplit(value.get('base_url',''))
    if value.get('format') != 'kobra-archive-client-v1' or url.username or url.password or url.path not in ('','/') or url.query or url.fragment or not url.hostname or url.scheme not in ('http','https'): raise ValueError('Ungültige Monitor-Konfiguration.')
    if url.scheme == 'http':
        try: addr = ipaddress.ip_address(url.hostname)
        except ValueError as exc: raise ValueError('Unverschlüsseltes HTTP nur mit lokaler IP-Adresse.') from exc
        if not (addr.is_private or addr.is_loopback): raise ValueError('Für diese Adresse ist HTTPS erforderlich.')
    token = value.get('token')
    if not isinstance(token,str) or not 40 <= len(token) <= 64 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in token): raise ValueError('Ungültiger Computerzugang.')
    return value['base_url'].rstrip('/'), token


class Collector:
    def __init__(self, source, queue, include_existing=False):
        self.source = Path(source).absolute(); self.queue = Path(queue).absolute()
        self.queue.mkdir(parents=True, exist_ok=True, mode=0o700); self.queue.chmod(0o700)
        self.db = sqlite3.connect(self.queue/'queue.sqlite3', check_same_thread=False)
        (self.queue/'queue.sqlite3').chmod(0o600)
        self.db.executescript('''PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
          CREATE TABLE IF NOT EXISTS sources(path TEXT PRIMARY KEY,signature TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS pending(sha TEXT NOT NULL,name TEXT NOT NULL,size INTEGER NOT NULL,sent INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(sha,name));
          CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        ''')
        self.lock = threading.RLock(); self.observed = {}; self.blocked = False; self.upload_blocked = False
        if not self.db.execute("SELECT 1 FROM settings WHERE key='initialized'").fetchone():
            if not include_existing:
                for path in self.candidates():
                    self.db.execute('INSERT OR REPLACE INTO sources VALUES(?,?)', (str(path), self.signature(path)))
            self.db.execute("INSERT INTO settings VALUES('initialized','1')"); self.db.commit()

    def candidates(self):
        if not self.source.is_dir() or self.source.is_symlink(): return []
        # Only the known cache root and one Slicer-created numeric subdirectory.
        return sorted(p for p in [*self.source.glob('*.gcode.3mf'), *self.source.glob('*/*.gcode.3mf')] if p.is_file() and not p.is_symlink() and not p.parent.is_symlink())

    @staticmethod
    def signature(path):
        value = path.stat(); return f'{value.st_dev}:{value.st_ino}:{value.st_size}:{value.st_mtime_ns}'

    def scan(self):
        self.blocked = False
        for path in self.candidates():
            try:
                signature = self.signature(path)
                with self.lock: old = self.db.execute('SELECT signature FROM sources WHERE path=?', (str(path),)).fetchone()
                if old and old[0] == signature: continue
                if self.observed.get(str(path)) != signature:
                    self.observed[str(path)] = signature; continue
                self.capture(path, signature)
            except (OSError, ValueError, sqlite3.Error): self.blocked = True

    def capture(self, path, signature):
        name = filename(path.name); size = path.stat().st_size
        if not 0 < size <= MAX_FILE: raise ValueError('Dateigröße außerhalb des Limits.')
        used = sum(p.stat().st_size for p in self.queue.glob('*.gcode.3mf'))
        if used + size > MAX_TOTAL or shutil.disk_usage(self.queue).free < size + RESERVE: raise ValueError('Lokale Warteschlange voll.')
        sourcefd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        fd, temporary = tempfile.mkstemp(suffix='.part', dir=self.queue)
        try:
            # O_NOFOLLOW rejects a source replaced with a symlink after scanning.
            with os.fdopen(sourcefd,'rb') as src, os.fdopen(fd,'wb') as out:
                shutil.copyfileobj(src, out, 1024*1024); out.flush(); os.fsync(out.fileno())
            if self.signature(path) != signature: raise ValueError('Datei wird noch geschrieben.')
            validate_package(temporary); sha = digest(temporary); target = self.queue/(sha+'.gcode.3mf')
            if target.exists():
                if digest(target) != sha: raise ValueError('Lokales Original beschädigt.')
            else:
                os.replace(temporary,target)
                directory = os.open(self.queue,os.O_RDONLY) if os.name != 'nt' else None
                try: os.fsync(directory) if directory is not None else None
                finally:
                    if directory is not None: os.close(directory)
            with self.lock:
                self.db.execute('INSERT OR IGNORE INTO pending(sha,name,size) VALUES(?,?,?)', (sha,name,size))
                self.db.execute('INSERT OR REPLACE INTO sources VALUES(?,?)', (str(path),signature)); self.db.commit()
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def send_one(self, opener, base, token):
        with self.lock: row = self.db.execute('SELECT sha,name,size FROM pending WHERE sent=0 ORDER BY rowid LIMIT 1').fetchone()
        if not row: return False
        sha,name,size = row; path = self.queue/(sha+'.gcode.3mf')
        if not path.is_file() or digest(path) != sha: raise ValueError('Lokale Warteschlange beschädigt.')
        with path.open('rb') as stream:
            request = urllib.request.Request(base+'/api/archive/ingest', data=stream, method='POST', headers={
                'Authorization':'Bearer '+token, 'Content-Type':'application/octet-stream', 'Content-Length':str(size),
                'X-Kobra-Size':str(size), 'X-Kobra-SHA256':sha, 'X-Kobra-Filename':base64.urlsafe_b64encode(name.encode()).decode()})
            with opener.open(request,timeout=60) as response: result = json.loads(response.read(8192))
        if result.get('sha256') != sha or result.get('size') != size or result.get('verified') is not True: raise ValueError('NAS hat Original nicht bestätigt.')
        # Keep the local original, including after acknowledgement. No last-copy deletion.
        with self.lock: self.db.execute('UPDATE pending SET sent=1 WHERE sha=? AND name=?', (sha,name)); self.db.commit()
        return True

    def status(self):
        with self.lock:
            pending = self.db.execute('SELECT count(*) FROM pending WHERE sent=0').fetchone()[0]
            sent = self.db.execute('SELECT count(*) FROM pending WHERE sent=1').fetchone()[0]
        return {'pending':pending, 'confirmed':sent, 'state':'blocked' if self.blocked or self.upload_blocked else 'pending' if pending else 'ready', 'checked_at':time.time()}


def run(config, source, queue, include_existing=False):
    if fcntl is None: raise ValueError('Der automatische Cache-Helfer unterstützt zunächst macOS und Linux.')
    base, token = read_config(config)
    queue = Path(queue); queue.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (queue/'client.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        collector = Collector(source, queue, include_existing)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        stop = threading.Event()
        def upload():
            while not stop.is_set():
                try:
                    collector.upload_blocked = False
                    for _ in range(20):
                        if not collector.send_one(opener,base,token): break
                    data = json.dumps({'state':collector.status()['state']}).encode()
                    request = urllib.request.Request(base+'/api/archive/heartbeat',data=data,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
                    with opener.open(request,timeout=15) as response: response.read(8192)
                except urllib.error.HTTPError as exc:
                    collector.upload_blocked = exc.code in (400,401,403,507)
                    if collector.upload_blocked:
                        try:
                            request = urllib.request.Request(base+'/api/archive/heartbeat',data=b'{"state":"blocked"}',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
                            with opener.open(request,timeout=15) as response: response.read(8192)
                        except (OSError,ValueError): pass
                except (OSError, ValueError, urllib.error.URLError): pass
                stop.wait(30)
        worker = threading.Thread(target=upload,daemon=True); worker.start()
        try:
            while True:
                collector.scan()
                status = queue/'status.json'; temporary = queue/'status.tmp'
                fd = os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
                with os.fdopen(fd,'w') as stream: json.dump(collector.status(),stream)
                os.replace(temporary,status); time.sleep(2)
        finally: stop.set()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Originaldateien aus dem Anycubic-Sendecache privat archivieren.')
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--source',type=Path,default=Path(tempfile.gettempdir())/'ACGcode3mf')
    parser.add_argument('--queue',type=Path,default=Path.home()/'Library/Application Support/Kobra Monitor Archive/queue')
    parser.add_argument('--include-existing',action='store_true',help='Auch bereits vorhandene Cache-Dateien übernehmen.')
    args = parser.parse_args()
    run(args.config,args.source,args.queue,args.include_existing)
