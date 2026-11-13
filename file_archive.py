"""Verified immutable print originals; no printer operations.
SPDX-License-Identifier: GPL-3.0-only
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import stat
import time
import unicodedata
import uuid
import zipfile

MAX_FILE = 256 * 1024**2
MAX_TOTAL = 2 * 1024**3
MAX_EXPANDED = 1024**3
RESERVE = 256 * 1024**2
SHA = re.compile(r'^[a-f0-9]{64}$')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def filename(value):
    if not isinstance(value, str): raise ValueError('Dateiname fehlt.')
    value = unicodedata.normalize('NFC', value)
    if not 1 <= len(value.encode('utf-8')) <= 240 or any(ord(c) < 32 or ord(c) == 127 for c in value) or '/' in value or '\\' in value or not value.lower().endswith('.gcode.3mf'):
        raise ValueError('Eine fertige .gcode.3mf-Druckdatei wird benötigt.')
    return value


def validate_package(path):
    """Read and CRC-check without extracting or interpreting executable contents."""
    if not 0 < Path(path).stat().st_size <= MAX_FILE: raise ValueError('Dateigröße außerhalb des Archivlimits.')
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if not 1 <= len(entries) <= 2048: raise ValueError('Zu viele Paketeinträge.')
            names = set(); total = 0; gcode = False
            for item in entries:
                name = item.filename
                parts = PurePosixPath(name).parts
                mode = item.external_attr >> 16
                if name in names or name.startswith('/') or '\\' in name or '..' in parts or ':' in name or item.flag_bits & 1 or stat.S_ISLNK(mode):
                    raise ValueError('Unsicherer Paketeintrag.')
                names.add(name); total += item.file_size
                if total > MAX_EXPANDED: raise ValueError('Entpacktes Paket überschreitet das Limit.')
                if name.lower().endswith('.gcode') and item.file_size: gcode = True
            if not gcode or '[Content_Types].xml' not in names: raise ValueError('Das Paket enthält keinen geslicten G-Code.')
            if archive.testzip() is not None: raise ValueError('Beschädigte Druckdatei.')
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as exc:
        raise ValueError('Druckdatei kann nicht vollständig geprüft werden.') from exc


def object_path(root, sha):
    if not isinstance(sha, str) or not SHA.fullmatch(sha): raise ValueError('Ungültige Prüfsumme.')
    return Path(root) / 'file-archive' / 'objects' / sha[:2] / (sha + '.gcode.3mf')


def verify_catalog(db, root):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='archived_print_files' AND type='table'").fetchone(): return
    for sha, size in db.execute('SELECT sha256,size FROM archived_print_files'):
        path = object_path(root, sha)
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size or digest(path) != sha:
            raise ValueError('Eine Originaldatei fehlt oder ihre Prüfsumme stimmt nicht.')


class FileArchive:
    def __init__(self, history, max_total=MAX_TOTAL):
        self.h = history
        self.root = Path(history.db.execute('PRAGMA database_list').fetchone()[2]).parent
        self.max_total = max_total
        self.incoming = self.root / '.archive-incoming'
        self.incoming.mkdir(mode=0o700, exist_ok=True)
        self.h.db.executescript('''
          CREATE TABLE IF NOT EXISTS archived_print_files(sha256 TEXT PRIMARY KEY,size INTEGER NOT NULL,created_at REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS file_archive_names(sha256 TEXT NOT NULL,name TEXT NOT NULL,first_seen REAL NOT NULL,last_seen REAL NOT NULL,PRIMARY KEY(sha256,name));
          CREATE TABLE IF NOT EXISTS file_archive_clients(id TEXT PRIMARY KEY,name TEXT NOT NULL,key_hash TEXT NOT NULL UNIQUE,created_at REAL NOT NULL,last_seen REAL,disabled INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT '');
          CREATE TABLE IF NOT EXISTS file_job_links(job_id TEXT PRIMARY KEY,sha256 TEXT NOT NULL,linked_at REAL NOT NULL);
        ''')
        if 'link_method' not in {r[1] for r in self.h.db.execute('PRAGMA table_info(file_job_links)')}:
            self.h.db.execute("ALTER TABLE file_job_links ADD COLUMN link_method TEXT NOT NULL DEFAULT 'manual'")
            self.h.db.commit()
        if 'source_job' not in {r[1] for r in self.h.db.execute('PRAGMA table_info(file_job_links)')}:
            self.h.db.execute('ALTER TABLE file_job_links ADD COLUMN source_job TEXT')
            self.h.db.commit()
        # A server restart never promotes an interrupted upload to an original.
        for path in self.incoming.glob('*.part'):
            if path.is_file() and not path.is_symlink(): path.unlink()

    def new_client(self, name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80: raise ValueError('Bitte einen Computernamen angeben.')
        token = secrets.token_urlsafe(32); now = self.h.clock(); client = uuid.uuid4().hex
        with self.h.lock:
            if self.h.db.execute('SELECT count(*) FROM file_archive_clients WHERE disabled=0').fetchone()[0] >= 20: raise ValueError('Bitte zuerst alte Computerzugänge widerrufen.')
            self.h.db.execute('INSERT INTO file_archive_clients(id,name,key_hash,created_at) VALUES(?,?,?,?)', (client, name.strip(), hashlib.sha256(token.encode()).hexdigest(), now))
            self.h.db.commit()
        return token

    def authenticate(self, token):
        if not isinstance(token, str) or not 40 <= len(token) <= 64: return None
        hashed = hashlib.sha256(token.encode()).hexdigest()
        with self.h.lock:
            row = self.h.db.execute('SELECT id FROM file_archive_clients WHERE key_hash=? AND disabled=0', (hashed,)).fetchone()
            return row['id'] if row else None

    def heartbeat(self, client, state):
        # Never store client paths, credentials or arbitrary diagnostic text.
        if state not in ('ready','pending','blocked'): raise ValueError('Ungültiger Helferstatus.')
        with self.h.lock:
            self.h.db.execute('UPDATE file_archive_clients SET last_seen=?,status=? WHERE id=? AND disabled=0', (self.h.clock(), state, client)); self.h.db.commit()

    def receive(self, temporary, name, expected, size, client):
        name = filename(name)
        if not isinstance(expected, str) or not SHA.fullmatch(expected) or type(size) is not int or not 0 < size <= MAX_FILE: raise ValueError('Ungültige Dateiangaben.')
        temporary = Path(temporary)
        if temporary.stat().st_size != size or digest(temporary) != expected: raise ValueError('Übertragung unvollständig oder Prüfsumme falsch.')
        validate_package(temporary)
        with self.h.lock:
            if not self.h.db.execute('SELECT 1 FROM file_archive_clients WHERE id=? AND disabled=0', (client,)).fetchone(): raise ValueError('Computerzugang widerrufen.')
            row = self.h.db.execute('SELECT size FROM archived_print_files WHERE sha256=?', (expected,)).fetchone()
            target = object_path(self.root, expected)
            if row:
                if row['size'] != size or not target.is_file() or target.is_symlink() or digest(target) != expected: raise ValueError('Vorhandenes Original ist nicht mehr intakt.')
            else:
                used = self.h.db.execute('SELECT coalesce(sum(size),0) FROM archived_print_files').fetchone()[0]
                if used + size > self.max_total or shutil.disk_usage(self.root).free < size + RESERVE: raise ValueError('Archiv voll. Original bleibt in der lokalen Warteschlange.')
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                os.chmod(temporary, 0o600)
                with temporary.open('r+b') as stream: os.fsync(stream.fileno())
                os.replace(temporary, target)
                fd = os.open(target.parent, os.O_RDONLY) if os.name != 'nt' else None
                try: os.fsync(fd) if fd is not None else None
                finally:
                    if fd is not None: os.close(fd)
                self.h.db.execute('INSERT INTO archived_print_files VALUES(?,?,?)', (expected, size, self.h.clock()))
            now = self.h.clock()
            self.h.db.execute('INSERT INTO file_archive_names VALUES(?,?,?,?) ON CONFLICT(sha256,name) DO UPDATE SET last_seen=excluded.last_seen', (expected, name, now, now))
            self.h.db.execute('UPDATE file_archive_clients SET last_seen=?,status=? WHERE id=?', (now, 'ready', client))
            self.h.db.commit()
            return {'sha256':expected, 'size':size, 'verified':True}

    def listing(self):
        with self.h.lock:
            files = []
            for row in self.h.db.execute('SELECT * FROM archived_print_files ORDER BY created_at DESC LIMIT 1000'):
                item = dict(row); item['names'] = [r[0] for r in self.h.db.execute('SELECT name FROM file_archive_names WHERE sha256=? ORDER BY name', (row['sha256'],))]; files.append(item)
            clients = [dict(r) for r in self.h.db.execute('SELECT id,name,created_at,last_seen,status,disabled FROM file_archive_clients ORDER BY created_at DESC')]
            return {'files':files, 'clients':clients, 'max_bytes':self.max_total, 'used_bytes':self.h.db.execute('SELECT coalesce(sum(size),0) FROM archived_print_files').fetchone()[0]}

    def revoke(self, client):
        if not isinstance(client, str) or not re.fullmatch('[a-f0-9]{32}', client): raise ValueError('Ungültiger Computerzugang.')
        with self.h.lock:
            self.h.db.execute('UPDATE file_archive_clients SET disabled=1 WHERE id=?', (client,)); self.h.db.commit()

    def linked(self, job):
        with self.h.lock:
            row = self.h.db.execute('SELECT f.sha256,f.size,l.linked_at,l.link_method,l.source_job,s.filename AS source_filename FROM file_job_links l JOIN archived_print_files f ON f.sha256=l.sha256 LEFT JOIN jobs s ON l.source_job=s.id WHERE l.job_id=?', (job,)).fetchone()
            # Preserve the existing shape for old manual report snapshots.
            if not row:return None
            result=dict(row)
            if result['link_method']=='manual':
                for key in ('link_method','source_job','source_filename'):result.pop(key)
            return result

    def link(self, job, sha, *, method='manual', source_job=None):
        if method not in ('manual','reprint'):raise ValueError('Unbekannte Herkunft der Dateizuordnung.')
        with self.h.lock:
            if method=='reprint':
                if (not isinstance(source_job,str) or source_job==job or
                    not self.h.db.execute("SELECT 1 FROM jobs j JOIN file_job_links l ON j.id=l.job_id WHERE j.id=? AND j.state='completed' AND j.ended_at IS NOT NULL AND l.sha256=?",(source_job,sha)).fetchone()):
                    raise ValueError('Erfolgreicher Quellauftrag mit demselben Original fehlt.')
            elif source_job is not None:raise ValueError('Manuelle Zuordnung hat keinen automatischen Quellauftrag.')
            if not self.h.db.execute('SELECT 1 FROM jobs WHERE id=?', (job,)).fetchone(): raise ValueError('Auftrag nicht gefunden.')
            path = object_path(self.root, sha)
            previous = self.linked(job)
            if previous and previous['sha256'] == sha: return
            if previous and method=='reprint':raise ValueError('Vorhandene Dateizuordnung wird nicht automatisch überschrieben.')
            if not self.h.db.execute('SELECT 1 FROM archived_print_files WHERE sha256=?', (sha,)).fetchone() or not path.is_file() or digest(path) != sha: raise ValueError('Geprüftes Original fehlt.')
            self.h.db.execute('INSERT INTO file_job_links(job_id,sha256,linked_at,link_method,source_job) VALUES(?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET sha256=excluded.sha256,linked_at=excluded.linked_at,link_method=excluded.link_method,source_job=excluded.source_job', (job, sha, self.h.clock(),method,source_job)); self.h.db.commit()
