# SPDX-License-Identifier: GPL-3.0-only
"""Development/acceptance tools for the shared installer core. No install command."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import sys

from suite.packages import PLATFORMS, verify_package
from suite.snapshots import create_snapshot, verify_snapshot
from suite.deployment import prepare
from suite.recovery import restore_to_new_directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    package = commands.add_parser('verify-package', help='Signiertes Komplettpaket nur prüfen')
    package.add_argument('archive')
    package.add_argument('--platform', required=True, choices=sorted(PLATFORMS))
    package.add_argument('--key-id', required=True)
    package.add_argument('--trusted-public-key', required=True,
                         help='Bereits vertrauenswürdiger öffentlicher Ed25519-Schlüssel (32 rohe Bytes), außerhalb des ZIP')
    create = commands.add_parser('create-snapshot', help='Beide Datenbestände sichern und getrennt wiederherstellen')
    create.add_argument('--monitor-data', required=True)
    create.add_argument('--spoolman-database', required=True)
    create.add_argument('--destination', required=True)
    create.add_argument('--monitor-image', required=True)
    create.add_argument('--spoolman-image', required=True)
    create.add_argument('--deployment')
    inspect = commands.add_parser('verify-snapshot', help='Vorhandene Komplettsicherung getrennt wiederherstellen und prüfen')
    inspect.add_argument('directory')
    project = commands.add_parser('prepare-test-project', help='Getrenntes Compose-Testprojekt nur vorbereiten')
    project.add_argument('directory')
    project.add_argument('--monitor-image', required=True)
    project.add_argument('--port', type=int, default=17125)
    project.add_argument('--address', default='127.0.0.1')
    project.add_argument('--network', choices=('isolated','lan'), default='isolated')
    restore = commands.add_parser('restore-offline', help='Suite nur in einen neuen Ordner wiederherstellen')
    restore.add_argument('snapshot')
    restore.add_argument('--target', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'verify-package':
            key = Path(args.trusted_public_key).read_bytes()
            if len(key) != 32:
                raise ValueError('Der öffentliche Ed25519-Schlüssel muss 32 Bytes enthalten.')
            proof = asdict(verify_package(args.archive, {args.key_id: key}, args.platform))
            proof.update(verified=True, installed=False)
        elif args.command == 'create-snapshot':
            path = create_snapshot(args.monitor_data, args.spoolman_database, args.destination,
                                   monitor_image=args.monitor_image, spoolman_image=args.spoolman_image,
                                   deployment=args.deployment)
            proof = {'verified': True, 'directory': str(path), 'production_restored': False}
        elif args.command == 'verify-snapshot':
            proof = verify_snapshot(args.directory)
            proof['production_restored'] = False
        elif args.command == 'prepare-test-project':
            path = prepare(args.directory, args.monitor_image, port=args.port, address=args.address, network=args.network)
            proof = {'directory': str(path), 'services_started': False, 'production_modified': False}
        else:
            path = restore_to_new_directory(args.snapshot, args.target)
            proof = {'directory': str(path), 'restored_offline': True, 'services_started': False}
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
        print('Prüfung fehlgeschlagen: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(proof, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
