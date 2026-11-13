# SPDX-License-Identifier: GPL-3.0-only
"""Generate a separate, initially loopback-only suite. Never invoke Docker here."""
import json
import ipaddress
from pathlib import Path
import re
import uuid

FORMAT = 'kobra-suite-deployment-v1'
SPOOLMAN_IMAGE = 'ghcr.io/donkie/spoolman@sha256:ab0a509a7823db96d07d6cb852b2f5d5e7745e74334ef0a1e97ed1a69eb74336'
PROJECT = re.compile(r'kobra-suite-test-[a-f0-9]{12}\Z')
MONITOR_IMAGE = re.compile(r'kobra-monitor:[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?\Z')


def bind_address(value):
    try:
        address = ipaddress.IPv4Address(value)
    except (ValueError, TypeError):
        raise ValueError('Die lokale IPv4-Adresse dieses Rechners angeben.') from None
    ranges = ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')
    if str(address) != '127.0.0.1' and not any(address in ipaddress.IPv4Network(n) for n in ranges):
        raise ValueError('Nur localhost oder eine private Heimnetz-Adresse dieses Rechners verwenden.')
    return str(address)


def contract(monitor_image, *, project=None, port=17125, address='127.0.0.1', network='isolated'):
    project = project or 'kobra-suite-test-' + uuid.uuid4().hex[:12]
    if not isinstance(project, str) or not PROJECT.fullmatch(project):
        raise ValueError('Einen eigenen Suite-Testprojektnamen verwenden.')
    if not isinstance(monitor_image, str) or not MONITOR_IMAGE.fullmatch(monitor_image):
        raise ValueError('Eine genaue lokal gebaute Monitorversion angeben.')
    if type(port) is not int or not 1024 <= port <= 65535 or port in (7125, 7912):
        raise ValueError('Einen getrennten Testport ab 1024 verwenden.')
    if network not in ('isolated', 'lan'):
        raise ValueError('Netzbetrieb muss isolated oder lan sein.')
    value = {'format': FORMAT, 'project': project, 'port': port,
            'monitor_image': monitor_image, 'spoolman_image': SPOOLMAN_IMAGE,
            'platform': 'linux/amd64', 'spoolman_version': '0.27.0'}
    if network == 'lan':
        value['network'] = network
    address = bind_address(address)
    if address != '127.0.0.1':
        value['bind_address'] = address
    return value


def validate(value):
    fields = {
            'format', 'project', 'port', 'monitor_image', 'spoolman_image', 'platform', 'spoolman_version'}
    if not isinstance(value, dict) or not fields <= set(value) <= fields | {'bind_address', 'network'}:
        raise ValueError('Ungültige Suite-Konfiguration.')
    expected = contract(value['monitor_image'], project=value['project'], port=value['port'],
                        address=value.get('bind_address', '127.0.0.1'), network=value.get('network', 'isolated'))
    if value != expected:
        raise ValueError('Diese Suite-Konfiguration wird nicht unterstützt.')
    return expected


def compose(value):
    c = validate(value)
    hardened = {'init': True, 'read_only': True, 'cap_drop': ['ALL'],
                'security_opt': ['no-new-privileges:true'],
                'tmpfs': ['/tmp:mode=1777,size=128m']}
    monitor = {**hardened, 'image': c['monitor_image'], 'platform': c['platform'],
        'pull_policy': 'never', 'restart': 'unless-stopped',
        'ports': [c.get('bind_address', '127.0.0.1') + ':' + str(c['port']) + ':7125'],
        'volumes': ['monitor-data:/data'], 'networks': ['suite'],
        'depends_on': {'initialize': {'condition': 'service_completed_successfully'},
                       'spoolman': {'condition': 'service_healthy'}}}
    spoolman = {**hardened, 'image': c['spoolman_image'], 'platform': c['platform'],
        'user': '10001:10001', 'restart': 'unless-stopped',
        'entrypoint': ['uvicorn', 'spoolman.main:app', '--host', '0.0.0.0', '--port', '8000'],
        'environment': {'HOME': '/tmp', 'PYTHONDONTWRITEBYTECODE': '1', 'SPOOLMAN_DIR_DATA': '/data',
                        'SPOOLMAN_DIR_LOGS': '/tmp', 'SPOOLMAN_BASE_PATH': '/spoolman',
                        'SPOOLMAN_AUTOMATIC_BACKUP': 'TRUE', 'TZ': 'UTC', 'EXTERNAL_DB_URL': ''},
        'volumes': ['spoolman-data:/data'], 'networks': ['suite'],
        'depends_on': {'initialize': {'condition': 'service_completed_successfully'}},
        'healthcheck': {'test': ['CMD', 'python', '-c',
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/spoolman/api/v1/health',timeout=3)"],
            'interval': '10s', 'timeout': '5s', 'start_period': '30s', 'retries': 12}}
    initialize = {**hardened, 'image': c['monitor_image'], 'platform': c['platform'],
        'pull_policy': 'never', 'user': '0:0', 'network_mode': 'none', 'restart': 'no',
        'cap_add': ['CHOWN', 'DAC_OVERRIDE', 'FOWNER'], 'healthcheck': {'disable': True},
        'command': ['python', 'suite_service.py', 'initialize', '--config', '/suite/suite.json',
                    '--monitor-data', '/monitor', '--spoolman-data', '/spoolman', '--backup-data', '/backups'],
        'volumes': ['monitor-data:/monitor', 'spoolman-data:/spoolman', 'backup-data:/backups',
                    './suite.json:/suite/suite.json:ro']}
    backups = {**hardened, 'image': c['monitor_image'], 'platform': c['platform'],
        'pull_policy': 'never', 'network_mode': 'none', 'restart': 'unless-stopped',
        'healthcheck': {'test': ['CMD', 'python', '-c',
            'from suite_service import heartbeat_healthy; assert heartbeat_healthy()'],
            'interval': '10s', 'timeout': '5s', 'start_period': '10s', 'retries': 3},
        'command': ['python', 'suite_service.py', 'watch', '--config', '/suite/suite.json',
                    '--monitor-data', '/source-monitor', '--spoolman-data', '/source-spoolman',
                    '--destination', '/backups'],
        'depends_on': {'initialize': {'condition': 'service_completed_successfully'}},
        'volumes': ['monitor-data:/source-monitor:ro', 'spoolman-data:/source-spoolman:ro',
                    'backup-data:/backups', './suite.json:/suite/suite.json:ro']}
    networks = {'suite': {'internal': True}}
    if c.get('network') == 'lan':
        # Only the Monitor joins the outbound bridge. No host networking,
        # privileged mode, Docker socket or additional published port.
        networks['printers'] = {}
        monitor['networks'].append('printers')
        monitor['environment'] = {'KOBRA_NATIVE_CONTROL_SETTINGS': '1'}
    return {'name': c['project'], 'services': {'initialize': initialize, 'monitor': monitor,
            'spoolman': spoolman, 'backups': backups},
            'networks': networks,
            'volumes': {'monitor-data': {}, 'spoolman-data': {}, 'backup-data': {}}}


def prepare(destination, monitor_image, *, project=None, port=17125, address='127.0.0.1', network='isolated'):
    """Write a new development project; reject existing directories, never migrate."""
    c = contract(monitor_image, project=project, port=port, address=address, network=network)
    target = Path(destination)
    target.mkdir(mode=0o700)  # No exist_ok: never overwrite another installation.
    for name, data in [('suite.json', c), ('compose.json', compose(c))]:
        path = target / name
        with path.open('x') as out:
            json.dump(data, out, indent=2)
            out.write('\n')
        # Public service settings only, no credentials. Container UID 10001 must
        # be able to read the mounted file even when Docker's operator is root.
        path.chmod(0o644)
    return target
