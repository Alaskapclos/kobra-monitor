# SPDX-License-Identifier: GPL-3.0-only
"""Pair a Monitor backup and a read-only SQLite snapshot of Spoolman.

Each database is consistent separately; this is not a distributed transaction.
Verification restores data into temporary directories and starts no services.
"""
from datetime import datetime, timezone
from contextlib import closing
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
import uuid

import backup
from suite.packages import unique_object

FORMAT = 'kobra-suite-snapshot-v1'
FILES = frozenset({'monitor.zip', 'spoolman.sqlite3'})
MAX_METADATA = 1024 * 1024


def _database(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=15)


def _spoolman_summary(path):
    with closing(_database(path)) as db:
        if db.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise ValueError('Die Spoolman-Datenbank ist beschädigt.')
        if db.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise ValueError('Die Spoolman-Datenbeziehungen sind beschädigt.')
        schema = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master "
                            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
        tables = [row[1] for row in schema if row[0] == 'table']
        if not {'spool', 'filament', 'vendor'} <= set(tables):
            raise ValueError('Die erwarteten Spoolman-Tabellen fehlen.')
        counts = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            counts[table] = db.execute('SELECT count(*) FROM ' + quoted).fetchone()[0]
        return {'schema_sha256': hashlib.sha256(json.dumps(schema).encode()).hexdigest(),
                'table_counts': counts}


def _copy_spoolman(source, target):
    started = time.monotonic()

    def progress(*_):
        if time.monotonic() - started > 120:
            raise TimeoutError('Die Spoolman-Sicherung dauert zu lange.')

    with closing(_database(source)) as incoming, closing(sqlite3.connect(target)) as outgoing:
        incoming.backup(outgoing, pages=256, progress=progress, sleep=.01)
        outgoing.execute('PRAGMA journal_mode=DELETE')
    target.chmod(0o600)
    return _spoolman_summary(target)


def _description(path):
    return {'size': path.stat().st_size, 'sha256': backup.digest(path)}


def verify_snapshot(directory):
    """Validate both archives, then actually restore into isolated temporary paths."""
    directory = Path(directory).absolute()
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Die Komplettsicherung muss ein echtes Verzeichnis sein.')
    metadata = directory / 'snapshot.json'
    if metadata.is_symlink() or metadata.stat().st_size > MAX_METADATA:
        raise ValueError('Ungültiges Sicherungsverzeichnis.')
    data = json.loads(metadata.read_text(), object_pairs_hook=unique_object)
    if (not isinstance(data, dict) or data.get('format') != FORMAT or
            set(data.get('files', {})) != FILES or
            set(data.get('images', {})) != {'monitor', 'spoolman'} or
            any(not isinstance(v, str) or not v for v in data['images'].values()) or
            type(data.get('created_at')) not in (int, float) or
            not math.isfinite(data['created_at'])):
        raise ValueError('Keine vollständige Monitor-/Spoolman-Sicherung.')
    if {p.name for p in directory.iterdir()} != FILES | {'snapshot.json'}:
        raise ValueError('Unerwartete Dateien in der Komplettsicherung.')
    for name in FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file() or _description(path) != data['files'][name]:
            raise ValueError('Eine Sicherungsdatei fehlt oder wurde verändert.')
    monitor = backup.inspect(directory / 'monitor.zip')
    if monitor['restore_image'] != data['images']['monitor']:
        raise ValueError('Das passende Monitor-Image ist nicht eindeutig.')
    # No restore into live paths; validate_data performs no device/network I/O.
    with tempfile.TemporaryDirectory(prefix='kobra-suite-restore-') as temporary:
        stage = Path(temporary)
        backup.restore(directory / 'monitor.zip', stage / 'monitor')
        spoolman = stage / 'spoolman.sqlite3'
        shutil.copyfile(directory / 'spoolman.sqlite3', spoolman)
        spoolman.chmod(0o600)
        if _description(spoolman) != data['files']['spoolman.sqlite3']:
            raise ValueError('Die Spoolman-Datei änderte sich beim Prüfen.')
        if _spoolman_summary(spoolman) != data['spoolman']:
            raise ValueError('Die Spoolman-Wiederherstellung stimmt nicht überein.')
        restored_monitor = stage / 'monitor' / 'history.sqlite3'
        with closing(_database(restored_monitor)) as db:
            jobs = db.execute('SELECT count(*) FROM jobs').fetchone()[0]
    return {'verified': True, 'monitor_jobs': jobs,
            'spoolman_tables': data['spoolman']['table_counts'],
            'images': data['images'], 'created_at': data['created_at']}


def create_snapshot(monitor_data, spoolman_database, destination, *,
                    monitor_image, spoolman_image, deployment=None, clock=time.time):
    """Publish only after a complete isolated restore succeeded. Never prune data."""
    if any(not isinstance(image, str) or not image.strip() or len(image) > 512
           for image in (monitor_image, spoolman_image)):
        raise ValueError('Beide passenden Programm-/Imageversionen angeben.')
    monitor = Path(monitor_data).absolute()
    spoolman = Path(spoolman_database).absolute()
    target = Path(destination).absolute()
    if (monitor.is_symlink() or spoolman.is_symlink() or not monitor.is_dir() or
            not spoolman.is_file() or target.is_symlink()):
        raise ValueError('Echte, vorhandene Datenpfade verwenden.')
    # Resolve parents too: a symlinked destination must not bypass separation.
    monitor, spoolman, target = monitor.resolve(), spoolman.resolve(), target.resolve()
    if monitor == spoolman.parent or monitor in spoolman.parents or spoolman.parent in monitor.parents:
        raise ValueError('Monitor und Spoolman benötigen getrennte Datenordner.')
    for source in (monitor, spoolman.parent):
        if target == source or source in target.parents or target in source.parents:
            raise ValueError('Die Sicherung benötigt einen getrennten Datenordner.')
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    now = clock()
    stamp = datetime.fromtimestamp(now, timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    final = target / ('kobra-suite-' + stamp + '-' + uuid.uuid4().hex)
    with tempfile.TemporaryDirectory(prefix='.kobra-suite-', dir=target) as temporary:
        stage = Path(temporary)
        payload = stage / 'payload'
        payload.mkdir(mode=0o700)
        monitor_archive = backup.create(monitor, stage / 'monitor-stage',
                                        monitor_image, deployment, clock)
        os.replace(monitor_archive, payload / 'monitor.zip')
        started_spoolman = clock()
        summary = _copy_spoolman(spoolman, payload / 'spoolman.sqlite3')
        data = {'format': FORMAT, 'created_at': now,
                'images': {'monitor': monitor_image, 'spoolman': spoolman_image},
                'spoolman_snapshot_started_at': started_spoolman,
                'consistency': 'Each database is consistent; no cross-service transaction.',
                'contains_private_data': True, 'spoolman': summary,
                'files': {name: _description(payload / name) for name in sorted(FILES)}}
        metadata = payload / 'snapshot.json'
        metadata.write_text(json.dumps(data, indent=2) + '\n')
        metadata.chmod(0o600)
        verify_snapshot(payload)
        if final.exists() or final.is_symlink():
            raise ValueError('Das Sicherungsziel existiert bereits.')
        os.rename(payload, final)
    return final
