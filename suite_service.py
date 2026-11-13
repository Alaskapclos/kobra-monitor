# SPDX-License-Identifier: GPL-3.0-only
"""Internal suite volume initialization and networkless paired backup service."""
import argparse
import json
import math
import os
from pathlib import Path
import time

import backup
from suite.deployment import validate
from suite.packages import unique_object
from suite.snapshots import create_snapshot, verify_snapshot

MARKER = '.kobra-suite-volume.json'
HEARTBEAT = Path('/tmp/suite-backup-heartbeat.json')


def write_heartbeat(status, path=HEARTBEAT, clock=time.time):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'status': status, 'checked_at': clock()}))
    temporary.chmod(0o600)
    os.replace(temporary, path)


def heartbeat_healthy(path=HEARTBEAT, clock=time.time):
    try:
        data = json.loads(path.read_text())
        stamp = data['checked_at']
        return (data['status'] in ('verified', 'waiting_or_not_due') and
                type(stamp) in (int, float) and math.isfinite(stamp) and 0 <= clock()-stamp < 180)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def read_config(path):
    p = Path(path)
    if p.is_symlink() or p.stat().st_size > 65536:
        raise ValueError('Ungültige Suite-Konfiguration.')
    return validate(json.loads(p.read_text(), object_pairs_hook=unique_object))


def volume_identity(config, role):
    return {'format': 'kobra-suite-volume-v1', 'project': config['project'], 'role': role}


def initialize(config, monitor, spoolman, backups, *, set_owner=False):
    """Only empty volumes or exact matching identities. Never adopt existing data."""
    config = validate(config)
    paths = {name: Path(path) for name, path in
             [('monitor', monitor), ('spoolman', spoolman), ('backups', backups)]}
    if len({p.resolve() for p in paths.values()}) != 3:
        raise ValueError('Getrennte Suite-Datenbereiche verwenden.')
    for role, path in paths.items():
        if path.is_symlink() or not path.is_dir():
            raise ValueError('Echte, getrennte Datenvolumes verwenden.')
        for other in paths.values():
            if path != other and (path.resolve() in other.resolve().parents):
                raise ValueError('Datenvolumes dürfen nicht ineinander liegen.')
        marker = path / MARKER
        if marker.is_symlink():
            raise ValueError('Unsichere Volume-Kennung.')
        if marker.exists():
            if json.loads(marker.read_text()) != volume_identity(config, role):
                raise ValueError('Das Volume gehört zu einer anderen Installation.')
        elif any(path.iterdir()):
            raise ValueError('Vorhandene Daten werden nicht automatisch übernommen.')
    # Validate all volumes before making the first write.
    for role, path in paths.items():
        marker = path / MARKER
        if not marker.exists():
            with marker.open('x') as out:
                json.dump(volume_identity(config, role), out)
            marker.chmod(0o600)
        path.chmod(0o750 if role == 'spoolman' else 0o700)
        if set_owner:
            os.chown(path, 10001, 10001)
            os.chown(marker, 10001, 10001)
    settings = paths['monitor'] / 'spoolman.json'
    if not settings.exists():
        with settings.open('x') as out:
            json.dump({'url': 'http://spoolman:8000/spoolman', 'mappings': {},
                       'sku_links': {}, 'amount_sources': {}}, out)
        settings.chmod(0o600)
        if set_owner:
            os.chown(settings, 10001, 10001)


def run_due(config, monitor, spoolman, destination, *, clock=time.time, interval=86400, state=None):
    config = validate(config)
    # A new, not-yet-configured installation is not a corrupt backup. Wait for setup.
    if not (Path(monitor) / 'config.json').is_file() or not (Path(spoolman) / 'spoolman.db').is_file():
        return None
    destination = Path(destination)
    now = clock()
    cached = (state or {}).get('last_verified')
    if type(cached) in (int, float) and math.isfinite(cached) and 0 <= now-cached < interval:
        return None
    valid_times = []
    if destination.exists():
        for p in destination.glob('kobra-suite-*'):
            if p.is_dir() and not p.is_symlink():
                try:
                    proof = verify_snapshot(p)
                    valid_times.append(proof['created_at'])
                except (OSError, ValueError, KeyError):
                    continue  # A damaged stand never prevents a new valid backup.
    if valid_times and 0 <= now - max(valid_times) < interval:
        if state is not None:
            state['last_verified'] = max(valid_times)
        return None
    # Store the exact generated Compose configuration inside the Monitor archive.
    # It includes Spoolman's environment and all volume/service definitions.
    import tempfile
    from suite.deployment import compose
    with tempfile.TemporaryDirectory(prefix='kobra-suite-config-') as folder:
        deployment = Path(folder) / 'compose.json'
        deployment.write_text(json.dumps(compose(config), indent=2))
        result = create_snapshot(monitor, Path(spoolman) / 'spoolman.db', destination,
            monitor_image=config['monitor_image'], spoolman_image=config['spoolman_image'],
            deployment=deployment, clock=clock)
        if state is not None:
            state['last_verified'] = now
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['initialize', 'watch', 'backup'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--monitor-data', required=True)
    parser.add_argument('--spoolman-data', required=True)
    parser.add_argument('--backup-data')
    parser.add_argument('--destination')
    args = parser.parse_args()
    config = read_config(args.config)
    if args.action == 'initialize':
        if not args.backup_data:
            parser.error('--backup-data fehlt')
        initialize(config, args.monitor_data, args.spoolman_data, args.backup_data, set_owner=True)
        return
    if not args.destination:
        parser.error('--destination fehlt')
    state = {}
    while True:
        try:
            result = run_due(config, args.monitor_data, args.spoolman_data, args.destination, state=state)
            status = 'verified' if result else 'waiting_or_not_due'
            write_heartbeat(status)
            print(json.dumps({'backup': status}), flush=True)
        except Exception:
            # Do not leak private paths/data from a background service log.
            write_heartbeat('failed')
            print(json.dumps({'backup': 'failed', 'message': 'Sicherung fehlgeschlagen; ältere Stände bleiben erhalten.'}), flush=True)
            if args.action == 'backup':
                raise SystemExit(2)
        if args.action != 'watch':
            return
        time.sleep(60)


if __name__ == '__main__':
    main()
