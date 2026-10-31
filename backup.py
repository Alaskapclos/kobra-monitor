# SPDX-License-Identifier: GPL-3.0-only
"""Consistent installation backups. No network or printer-control operations."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import tempfile
import time
import uuid
import zipfile

FORMAT = 'kobra-monitor-installation-v1'
ARCHIVE = re.compile(r'kobra-backup-\d{8}T\d{6}Z-[a-f0-9]{8}\.zip\Z')
MAX_BYTES = 4 * 1024 ** 3
EXCLUDED = {'backups', '.backups', '__pycache__'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate_data(directory):
    from configuration import load_config
    from accounts import read_account
    if not (directory / 'config.json').is_file() or not load_config(directory):
        raise ValueError('Die Druckereinrichtung fehlt oder ist ungültig.')
    token = (directory / 'access-token').read_text().strip()
    if len(token) < 24:
        raise ValueError('Der Zugangscode fehlt oder ist ungültig.')
    read_account(directory) # Optional for old installations; malformed accounts fail closed.
    db = sqlite3.connect((directory / 'history.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Die Verlaufsdatenbank ist beschädigt.')
        for table in ('jobs', 'events', 'samples'):
            db.execute('SELECT 1 FROM ' + table + ' LIMIT 1').fetchall()
        devices=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='push_devices'").fetchone()
        key_path=directory/'push-vapid.pem'
        if devices and db.execute('SELECT count(*) FROM push_devices').fetchone()[0] and not key_path.is_file():
            raise ValueError('Der Benachrichtigungsschlüssel fehlt in der Sicherung.')
        if key_path.exists():
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import ec
            key=serialization.load_pem_private_key(key_path.read_bytes(),password=None)
            if not isinstance(key,ec.EllipticCurvePrivateKey) or not isinstance(key.curve,ec.SECP256R1):
                raise ValueError('Ungültiger Benachrichtigungsschlüssel in der Sicherung.')
    finally:
        db.close()


def create(data_dir, destination, image, deployment=None, clock=time.time):
    source = Path(data_dir).resolve()
    destination = Path(destination).resolve()
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError('Sicherungen brauchen einen getrennten Datenordner bzw. ein eigenes Volume.')
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    now = clock()
    stamp = datetime.fromtimestamp(now, timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name = 'kobra-backup-' + stamp + '-' + uuid.uuid4().hex[:8] + '.zip'
    # Stage into the destination: rename and creation are on the same filesystem.
    with tempfile.TemporaryDirectory(prefix='.kobra-backup-', dir=destination) as temporary:
        stage = Path(temporary)
        data = stage / 'data'
        data.mkdir(mode=0o700)
        before = (source / 'config.json').read_bytes()
        token_before = (source / 'access-token').read_bytes()
        account_path = source / 'account.json'
        account_before = account_path.read_bytes() if account_path.exists() else None
        for path in source.rglob('*'):
            relative = path.relative_to(source)
            if path.name.startswith('.push-') or any(part in EXCLUDED for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError('Symbolische Verknüpfungen im Datenordner werden nicht gesichert.')
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError('Unbekannter Dateityp im Datenordner.')
            if path.name in ('history.sqlite3', 'history.sqlite3-wal', 'history.sqlite3-shm'):
                continue
            target = data / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(path, target)
            target.chmod(0o600)
        db = sqlite3.connect((source / 'history.sqlite3').as_uri() + '?mode=ro', uri=True, timeout=15)
        snapshot = sqlite3.connect(data / 'history.sqlite3')
        try:
            db.backup(snapshot)
            snapshot.execute('PRAGMA journal_mode=DELETE')
        finally:
            snapshot.close()
            db.close()
        if before != (source / 'config.json').read_bytes() or token_before != (source / 'access-token').read_bytes():
            raise ValueError('Die Einrichtung wurde während der Sicherung geändert. Bitte wiederholen.')
        if (data / 'config.json').read_bytes() != before or (data / 'access-token').read_bytes() != token_before:
            raise ValueError('Die Einrichtung änderte sich während der Sicherung.')
        account_after = account_path.read_bytes() if account_path.exists() else None
        snapshot_account = (data / 'account.json').read_bytes() if (data / 'account.json').exists() else None
        if account_before != account_after or account_before != snapshot_account:
            raise ValueError('Das Benutzerkonto wurde während der Sicherung geändert. Bitte wiederholen.')
        validate_data(data)
        if deployment:
            shutil.copyfile(deployment, stage / 'compose.yaml')
        files = {p.relative_to(stage).as_posix(): {'sha256': digest(p), 'size': p.stat().st_size}
                 for p in stage.rglob('*') if p.is_file()}
        manifest = {'format': FORMAT, 'created_at': now, 'created_utc': stamp,
                    'restore_image': image, 'contains_access_code': True,
                    'contains_account': account_before is not None,
                    'tls_note': 'Temporary handshake certificates are regenerated on connection.',
                    'files': files}
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        archive = stage / 'archive.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as out:
            for relative in [*files, 'manifest.json']:
                out.write(stage / relative, relative)
        archive.chmod(0o600)
        inspect(archive)
        os.replace(archive, destination / name)
    return destination / name


def inspect(archive):
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)) or len(names) > 10000:
            raise ValueError('Doppelte oder zu viele Dateien im Archiv.')
        if sum(member.file_size for member in members) > MAX_BYTES:
            raise ValueError('Das Archiv ist zu groß.')
        for member in members:
            path = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or '\\' in member.filename
                    or ':' in member.filename or path.as_posix() != member.filename
                    or member.is_dir() or (mode & 0o170000) not in (0, 0o100000)):
                raise ValueError('Unsicherer Archivpfad oder Dateityp.')
            if member.filename not in ('manifest.json', 'compose.yaml') and not member.filename.startswith('data/'):
                raise ValueError('Unerwartete Datei im Archiv.')
        if source.getinfo('manifest.json').file_size > 1024 * 1024:
            raise ValueError('Das Sicherungsverzeichnis ist zu groß.')
        manifest = json.loads(source.read('manifest.json'))
        if manifest.get('format') != FORMAT or set(names) != set(manifest['files']) | {'manifest.json'}:
            raise ValueError('Das Archiv ist keine vollständige Kobra-Sicherung.')
        for name, expected in manifest['files'].items():
            h = hashlib.sha256()
            count = 0
            with source.open(name) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    count += len(block)
                    h.update(block)
            if count != expected['size'] or h.hexdigest() != expected['sha256']:
                raise ValueError('Die Prüfsumme einer Sicherungsdatei stimmt nicht.')
    return manifest


def restore(archive, target):
    manifest = inspect(archive)
    target = Path(target).absolute()
    if target.exists() or target.is_symlink():
        raise ValueError('Das Wiederherstellungsziel muss neu sein. Bestehende Daten werden nicht überschrieben.')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.kobra-restore-', dir=target.parent) as temporary:
        stage = Path(temporary)
        with zipfile.ZipFile(archive) as source:
            for name in manifest['files']:
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with source.open(name) as incoming, path.open('xb') as out:
                    shutil.copyfileobj(incoming, out)
                path.chmod(0o600)
        validate_data(stage / 'data')
        # Restores data only; deployment remains available inside the ZIP.
        if target.exists() or target.is_symlink():
            raise ValueError('Das Wiederherstellungsziel wurde zwischenzeitlich angelegt.')
        os.rename(stage / 'data', target)
    return manifest


def archives(destination):
    result = []
    for path in Path(destination).glob('kobra-backup-*.zip'):
        if path.is_symlink() or not ARCHIVE.fullmatch(path.name):
            continue
        try:
            manifest = inspect(path)
            result.append((float(manifest['created_at']), path))
        except (OSError, ValueError, KeyError, zipfile.BadZipFile):
            continue  # Never prune an unrelated or damaged file.
    return sorted(result, key=lambda item: (item[0], item[1].name))


def run_due(data_dir, destination, image, deployment=None, interval=86400, keep=7, clock=time.time):
    if interval < 60 or not 1 <= keep <= 365:
        raise ValueError('Ungültiger Sicherungsrhythmus oder Aufbewahrung.')
    prior = archives(destination)
    if prior and 0 <= clock() - prior[-1][0] < interval:
        return None
    result = create(data_dir, destination, image, deployment, clock)
    # Prune only after the new archive has passed all checks.
    for _, old in archives(destination)[:-keep]:
        old.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('create', 'watch'):
        command = sub.add_parser(name)
        command.add_argument('--data-dir', required=True)
        command.add_argument('--destination', required=True)
        command.add_argument('--image', required=True)
        command.add_argument('--deployment')
        if name == 'watch':
            command.add_argument('--interval', type=int, default=86400)
            command.add_argument('--keep', type=int, default=7)
    command = sub.add_parser('inspect')
    command.add_argument('archive')
    command = sub.add_parser('restore')
    command.add_argument('archive')
    command.add_argument('--target', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if args.command == 'inspect':
        metadata = inspect(args.archive)
        print(json.dumps({'valid': True, 'created_utc': metadata['created_utc'],
                          'restore_image': metadata['restore_image'], 'files': len(metadata['files'])}))
    elif args.command == 'restore':
        restore(args.archive, args.target)
        print('Wiederherstellung im neuen Datenordner geprüft und abgeschlossen.')
    elif args.command == 'create':
        print(create(args.data_dir, args.destination, args.image, args.deployment))
    else:
        if args.interval < 60 or not 1 <= args.keep <= 365:
            parser.error('Ungültiger Sicherungsrhythmus oder Aufbewahrung.')
        while True:
            delay = 300
            try:
                archive = run_due(args.data_dir, args.destination, args.image, args.deployment,
                                  args.interval, args.keep)
                if archive:
                    print('Sicherung geprüft: ' + archive.name, flush=True)
                    delay = args.interval
                else:
                    latest = archives(args.destination)[-1][0]
                    delay = max(1, args.interval - (time.time() - latest))
            except Exception:
                # Avoid credentials or filenames from arbitrary source errors in logs.
                print('Sicherung fehlgeschlagen; vorhandene Sicherungen bleiben erhalten. Neuer Versuch in 5 Minuten.', flush=True)
            time.sleep(delay)


if __name__ == '__main__':
    main()
