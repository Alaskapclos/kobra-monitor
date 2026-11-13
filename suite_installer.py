# SPDX-License-Identifier: GPL-3.0-only
"""Small fixed installer operations inside the Monitor image. No Docker access."""
import argparse
import json
from pathlib import Path

from suite.deployment import prepare, validate, compose, bind_address, contract
from suite.packages import unique_object


def inspect_project(directory, expected_image):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Der Installationsordner fehlt oder ist eine Verknüpfung.')
    content = {}
    for name in ('suite.json', 'compose.json'):
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
            raise ValueError('Die Installationsdateien sind unvollständig.')
        content[name] = json.loads(path.read_text(), object_pairs_hook=unique_object)
    config = validate(content['suite.json'])
    if config['monitor_image'] != expected_image:
        raise ValueError('Diese Installation gehört zu einer anderen Version. Eine gezielte Aktualisierung ist erforderlich.')
    if content['compose.json'] != compose(config):
        raise ValueError('Die Dienste-Konfiguration wurde verändert; kein automatischer Start.')
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    for operation in ('project-name', 'endpoint'):
        project = sub.add_parser(operation)
        project.add_argument('--directory', required=True)
        project.add_argument('--image', required=True)
    for operation in ('prepare', 'check-parameters'):
        create = sub.add_parser(operation)
        if operation == 'prepare':
            create.add_argument('--directory', required=True)
        create.add_argument('--image', required=True)
        create.add_argument('--port', type=int, default=17125)
        create.add_argument('--address', default='127.0.0.1')
        create.add_argument('--network', choices=('isolated','lan'), default='isolated')
    link = sub.add_parser('setup-link')
    link.add_argument('--port', type=int, required=True)
    link.add_argument('--address', required=True)
    args = parser.parse_args()
    try:
        if args.operation == 'prepare':
            prepare(args.directory, args.image, port=args.port, address=args.address, network=args.network)
        elif args.operation == 'check-parameters':
            contract(args.image, port=args.port, address=args.address, network=args.network)
        elif args.operation == 'project-name':
            print(inspect_project(args.directory, args.image)['project'])
        elif args.operation == 'endpoint':
            config = inspect_project(args.directory, args.image)
            print(config.get('bind_address', '127.0.0.1') + ':' + str(config['port']))
        else:
            from access import Access
            from urllib.parse import quote
            if not 1024 <= args.port <= 65535:
                raise ValueError('Ungültiger Port.')
            access = Access('/data')
            url = 'http://' + bind_address(args.address) + ':' + str(args.port) + '/'
            if access.account is None:
                url += '#access=' + quote(access.token, safe='')
            print(url)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
