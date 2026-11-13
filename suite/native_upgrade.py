# SPDX-License-Identifier: GPL-3.0-only
"""Explicit, stopped-profile upgrade by verified backup and separate restore.

Never upgrades the old profile in place, starts services or contacts printers.
"""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import sys
import tempfile
import time
import uuid

from suite.desktop import FORMAT, InstallationLock, atomic_json, local_url
from suite.packages import unique_object

TARGET = '0.43.0-alpha.4'
SOURCES = frozenset({'0.34.0-alpha.1', '0.39.0-alpha.1', '0.40.0-alpha.1', '0.41.0-alpha.1', '0.42.0-alpha.1'})
RECEIPT = 'kobra-native-profile-upgrade-v1'
MAX_FILES = 50000


def _publish(source, target):
    """Atomic directory publication with no replacement, including empty targets."""
    if os.name == 'nt':
        os.rename(source, target)
        return
    import ctypes as c
    libc = c.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        rename = libc.renamex_np
        rename.argtypes = [c.c_char_p, c.c_char_p, c.c_uint]
        result = rename(os.fsencode(source), os.fsencode(target), 4)  # RENAME_EXCL
    else:
        rename = libc.renameat2
        rename.argtypes = [c.c_int, c.c_char_p, c.c_int, c.c_char_p, c.c_uint]
        result = rename(-100, os.fsencode(source), -100, os.fsencode(target), 1)
    if result:
        raise OSError(c.get_errno(), 'Das Datenziel konnte nicht exklusiv angelegt werden.')


def _link(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


def _path(path):
    path = Path(path).expanduser().absolute()
    if any(_link(p) for p in (path, *path.parents)):
        raise ValueError('Verknüpfte Datenpfade werden nicht übernommen.')
    return path


def _json(path):
    if _link(path) or not path.is_file() or path.stat().st_size > 8*1024*1024:
        raise ValueError('Eine Datei der Testinstallation ist ungültig.')
    data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    if not isinstance(data, dict):
        raise ValueError('Die Testinstallation enthält ungültige Metadaten.')
    return data


def _profile(path):
    data = _json(path/'desktop.json')
    backend = data.get('backend_url')
    if (data.get('format') != FORMAT or
            not re.fullmatch('[a-f0-9]{32}', str(data.get('identity', ''))) or
            not isinstance(data.get('version'), str) or
            not isinstance(backend, str) or not backend.endswith('/spoolman') or
            not local_url(backend[:-len('/spoolman')])):
        raise ValueError('Dieser Datenordner ist keine unterstützte lokale Testinstallation.')
    return data


def target_path(source, version):
    if version != TARGET:
        raise ValueError('Für diese Zielversion ist keine Datenübernahme geprüft.')
    return _path(source).with_name(Path(source).name + '-' + version)


def _inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if _link(path):
            raise ValueError('Die Testdaten enthalten eine Verknüpfung.')
        info = path.stat()
        mode = info.st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValueError('Die Testdaten enthalten einen besonderen Dateityp.')
        if info.st_nlink != 1:
            raise ValueError('Die Testdaten enthalten eine mehrfach verknüpfte Datei.')
        if relative == 'desktop.lock':
            continue
        if relative == 'instance.json':
            raise ValueError('Die alte Test-App läuft noch oder wurde nicht vollständig beendet. Bitte ihren Beenden-Starter verwenden; nur das Browserfenster zu schließen reicht nicht.')
        if len(result) >= MAX_FILES:
            raise ValueError('Zu viele Dateien für diese Testdatenübernahme.')
        with path.open('rb') as stream:
            result[relative] = {'sha256': hashlib.file_digest(stream, 'sha256').hexdigest(),
                                'size': path.stat().st_size}
    return result


def _copy(source, destination, inventory):
    destination.mkdir(mode=0o700)
    for relative in inventory:
        incoming = source/relative
        if _link(incoming) or not incoming.is_file():
            raise ValueError('Eine Quelldatei hat sich während der Übernahme geändert.')
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(incoming, target)
        target.chmod(0o600)
    if _inventory(destination) != inventory:
        raise ValueError('Die Datenkopie stimmt nicht mit der Sicherung überein.')


def _database(path, prior=None):
    if _link(path) or not path.is_file():
        raise ValueError('Eine lokale Datenbank fehlt.')
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise ValueError('Eine lokale Datenbank ist beschädigt.')
        if db.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise ValueError('Eine Datenbank enthält beschädigte Beziehungen.')
        tables = prior or {name: {'columns': [row[1] for row in db.execute(
            'PRAGMA table_info("'+name.replace('"','""')+'")')]} for (name,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        result = {}
        for name, description in tables.items():
            columns = description['columns']
            quoted = ','.join('"'+c.replace('"','""')+'"' for c in columns)
            query = 'SELECT '+quoted+' FROM "'+name.replace('"','""')+'" ORDER BY '+quoted
            digest = hashlib.sha256();count = 0
            for row in db.execute(query):
                digest.update(json.dumps(row, separators=(',', ':'),
                    default=lambda b: {'bytes': b.hex()}).encode('utf-8')+b'\n')
                count += 1
            result[name] = {'columns': columns, 'rows': count, 'sha256': digest.hexdigest()}
        return result


def _seal_databases(root):
    """Consolidate WAL only in a byte-verified copy, never open source SQL."""
    for relative in ('monitor/history.sqlite3', 'spoolman/spoolman.db'):
        path = root/relative
        if not path.is_file():
            raise ValueError('Eine lokale Datenbank fehlt.')
        temporary = path.with_name('.'+path.name+'-'+uuid.uuid4().hex)
        try:
            started = time.monotonic()
            def progress(*_):
                if time.monotonic()-started > 120:
                    raise TimeoutError('Die Datenbankkopie dauert zu lange; alte Daten bleiben erhalten.')
            with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)) as incoming, \
                    closing(sqlite3.connect(temporary)) as outgoing:
                incoming.backup(outgoing, pages=256, progress=progress, sleep=.01)
                outgoing.execute('PRAGMA journal_mode=DELETE')
            temporary.chmod(0o600)
            os.replace(temporary, path)
            for suffix in ('-wal', '-shm', '-journal'):
                path.with_name(path.name+suffix).unlink(missing_ok=True)
        finally:
            temporary.unlink(missing_ok=True)


def _validate(root, profile):
    from backup import validate_data
    token = root/'monitor/access-token'
    if not token.is_file() or not 24 <= token.stat().st_size <= 8192:
        raise ValueError('Die lokale Anmeldung ist unvollständig.')
    validate_data(root/'monitor', require_config=False)
    settings = _json(root/'monitor/spoolman.json')
    if settings.get('url') != profile['backend_url']:
        raise ValueError('Externer Spoolman benötigt eine getrennte Datenübernahme.')
    monitor = _database(root/'monitor/history.sqlite3')
    spoolman = _database(root/'spoolman/spoolman.db')
    if not {'jobs', 'events', 'samples'} <= monitor.keys() or not {'vendor', 'filament', 'spool'} <= spoolman.keys():
        raise ValueError('Die erwarteten lokalen Datenbanken fehlen.')
    return {'monitor': monitor, 'spoolman': spoolman}


def existing_target(source, version):
    """Resolve only a previously published upgrade, never create or repair data."""
    source = _path(source)
    target = target_path(source, version)
    if not target.exists():
        return None
    _path(target)
    if not target.is_dir():
        raise ValueError('Das Übernahmeziel ist kein Datenordner.')
    receipt = _json(target/'upgrade.json')
    original = _profile(source);current = _profile(target)
    if (receipt.get('format') != RECEIPT or receipt.get('from_version') != original['version'] or
            receipt.get('to_version') != version or receipt.get('source_identity') != original['identity'] or
            current['identity'] != original['identity'] or current['version'] != version):
        raise ValueError('Ein anderes Übernahmeziel ist bereits vorhanden; es wird nicht ersetzt.')
    return target


def verify_backup(directory):
    directory = _path(directory)
    proof = _json(directory/'backup-proof.json')
    inventory = _inventory(directory)
    inventory.pop('backup-proof.json', None)
    profile = _profile(directory)
    if (proof.get('format') != RECEIPT or proof.get('restore_verified') is not True or
            proof.get('source_identity') != profile['identity'] or
            proof.get('from_version') != profile['version'] or
            proof.get('backup_files') != inventory):
        raise ValueError('Die Übernahmesicherung stimmt nicht mit ihrem Nachweis überein.')
    summary = _validate(directory, profile)
    return {'verified': True, 'version': profile['version'],
            'jobs': summary['monitor']['jobs']['rows'],
            'spools': summary['spoolman']['spool']['rows']}


def upgrade_profile(source, version):
    """Caller must obtain explicit owner consent; old data remains unchanged."""
    source = _path(source);target = target_path(source, version)
    if target.exists() or _link(target):
        raise FileExistsError('Das Ziel der Datenübernahme existiert bereits.')
    original = _profile(source)
    if original['version'] not in SOURCES:
        raise ValueError('Diese Ausgangsversion ist für die Übernahme noch nicht geprüft.')
    lock_path = source/'desktop.lock'
    if _link(lock_path):
        raise ValueError('Die alte Testinstallation enthält eine ungültige Sperrdatei.')
    lock = InstallationLock(lock_path)
    if not lock.acquire():
        raise ValueError('Die alte Test-App läuft noch oder wurde nicht vollständig beendet. Bitte ihren Beenden-Starter verwenden; nur das Browserfenster zu schließen reicht nicht.')
    try:
        inventory = _inventory(source)
        size = sum(item['size'] for item in inventory.values())
        if shutil.disk_usage(source.parent).free < size*3 + 16*1024*1024:
            raise ValueError('Für Sicherung und Datenkopie ist nicht genug Speicher frei.')
        backup_root = source.with_name(source.name+'-Uebernahmesicherungen')
        if _link(backup_root):
            raise ValueError('Der Sicherungsordner darf keine Verknüpfung sein.')
        backup_root.mkdir(mode=0o700, exist_ok=True)
        identity = uuid.uuid4().hex
        saved = backup_root/('vor-'+version+'-'+identity)
        with tempfile.TemporaryDirectory(prefix='.kobra-upgrade-', dir=source.parent) as temporary:
            stage = Path(temporary)
            snapshot = stage/'backup'
            _copy(source, snapshot, inventory)
            _seal_databases(snapshot)
            summary = _validate(snapshot, original)
            backup_inventory = _inventory(snapshot)
            if _inventory(source) != inventory:
                raise ValueError('Die alten Daten haben sich während der Sicherung geändert.')
            restored = stage/'restored'
            _copy(snapshot, restored, backup_inventory)
            if _validate(restored, original) != summary:
                raise ValueError('Die isolierte Wiederherstellung ist fehlgeschlagen.')
            # Upgrade schema only in the restored copy; old data and backup stay intact.
            from history import History
            history = History(restored/'monitor/history.sqlite3')
            history.close()
            _seal_databases(restored)
            for role, relative in [('monitor','monitor/history.sqlite3'),('spoolman','spoolman/spoolman.db')]:
                if _database(restored/relative, summary[role]) != summary[role]:
                    raise ValueError('Bestehende Daten wurden bei der Übernahme verändert.')
            atomic_json(restored/'desktop.json', {**original, 'version': version})
            receipt = {'format': RECEIPT, 'from_version': original['version'], 'to_version': version,
                       'source_identity': original['identity'], 'created_at': time.time(),
                       'backup_directory': saved.name, 'restore_verified': True,
                       'source_files': inventory, 'backup_files': backup_inventory,
                       'sqlite_snapshot_from_verified_copy': True}
            if len(json.dumps(receipt).encode('utf-8')) > 8*1024*1024:
                raise ValueError('Der Übernahmenachweis ist zu groß.')
            atomic_json(restored/'upgrade.json', receipt)
            if _inventory(source) != inventory:
                raise ValueError('Die alten Daten haben sich inzwischen geändert.')
            # Publish backup first. If publishing the target fails, the verified backup remains.
            _publish(snapshot, saved)
            atomic_json(saved/'backup-proof.json', receipt)
            verify_backup(saved)
            if target.exists() or _link(target):
                raise FileExistsError('Das Übernahmeziel wurde inzwischen angelegt.')
            _publish(restored, target)
        return target
    finally:
        lock.close()


def choose_profile(source, version, *, confirm=None, stopping=False):
    """UI consent for a known stopped profile; workers never call this function."""
    source = _path(source)
    if not (source/'desktop.json').exists():
        return source
    profile = _profile(source)
    if profile['version'] == version:
        return source
    if version != TARGET or profile['version'] not in SOURCES:
        raise ValueError('Für diese Testversion ist keine Datenübernahme geprüft.')
    target = existing_target(source, version)
    if target is not None:
        return target
    if stopping:
        return target_path(source, version)  # Cannot stop the old version by mistake.
    if confirm is None or not confirm('Vorhandene Testdaten aus '+profile['version']+' übernehmen?\n\n'
            'Neue Version: '+version+'\nQuelle: '+str(source)+'\nNeue Daten: '+str(target_path(source, version))+
            '\nSicherung: '+str(source.with_name(source.name+'-Uebernahmesicherungen'))+'\n\n'
            'Bitte die alte Test-App zuerst beenden. Monitor und lokaler Spoolman werden gesichert '
            'und in einen neuen Datenordner kopiert. Die Wiederherstellung wird geprüft. '
            'Alte Daten und Sicherung bleiben erhalten; die alte App arbeitet später mit ihrem alten Stand. '
            'Die neue Version verwendet danach die getrennte Kopie. Danach bitte nur die neue App verwenden.\n\n'
            'Datenübernahme jetzt prüfen und ausführen?'):
        return None
    return upgrade_profile(source, version)
