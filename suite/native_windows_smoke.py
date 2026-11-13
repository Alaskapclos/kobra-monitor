# SPDX-License-Identifier: GPL-3.0-only
"""Explicit local package check; no services, accounts, databases or printers."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys
import uuid

from suite.native_manifest import load_manifest
from suite.native_targets import native_target, runtime_architecture


def check(bundle):
    bundle = Path(bundle).resolve()
    target = native_target('windows', runtime_architecture())
    manifest = load_manifest(bundle, format='kobra-windows-test-bundle-v1',
                             platform=target.platform, verify=True)
    result = {'format': 'kobra-windows-native-package-check-v1', 'version': manifest['version'],
              'platform': target.platform, 'bundle_id': manifest['bundle_id'],
              'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'success': False, 'file_integrity_verified': True,
              'printer_connections': False, 'nas_services_changed': False,
              'database_connections': False, 'checks': {}}
    scripts = {
        'monitor': 'import aiohttp, cryptography, pywebpush; from cryptography.hazmat.primitives.ciphers.aead import AESGCM; a=AESGCM(AESGCM.generate_key(bit_length=128)); n=bytes(range(12)); assert a.decrypt(n,a.encrypt(n,b"Kobra",None),None)==b"Kobra"',
        'spoolman': 'import asyncpg, psycopg2, httptools, greenlet, fastapi, sqlalchemy, pydantic_core, uvicorn, alembic; from sqlalchemy.ext.asyncio import create_async_engine; from psycopg2.extensions import libpq_version; assert libpq_version()>=100000',
    }
    for role, code in scripts.items():
        process = subprocess.run([str(bundle/'runtime'/role/'python.exe'), '-I', '-B', '-X', 'utf8', '-c',
                                  'import platform; assert platform.machine().lower() in ' +
                                  repr(('arm64', 'aarch64') if target.architecture == 'arm64' else ('amd64', 'x86_64')) + '; ' + code],
                                 capture_output=True, timeout=90)
        result['checks'][role+'_runtime'] = {'ok': process.returncode == 0}
        if process.returncode:
            result['checks'][role+'_runtime']['error'] = (process.stderr or process.stdout).decode('utf-8', 'replace')[-3000:].replace(str(bundle), '<PROGRAMM>')
    process = subprocess.run([str(bundle/'runtime/spoolman/Scripts/alembic.exe'), '--version'],
                             capture_output=True, timeout=40)
    result['checks']['database_launcher'] = {'ok': process.returncode == 0}
    if process.returncode:
        result['checks']['database_launcher']['error'] = process.stderr.decode('utf-8', 'replace')[-2000:].replace(str(bundle), '<PROGRAMM>')
    camera_test = bundle/'ffmpeg/test/Kamera-Test.py'
    if camera_test.is_file():
        process = subprocess.run([sys.executable, '-I', '-B', str(camera_test),
                                  str(bundle/'ffmpeg/bin/ffmpeg.exe')], capture_output=True, timeout=65)
        result['checks']['ffmpeg_synthetic_image'] = {'ok': process.returncode == 0}
    else:
        process = subprocess.run([str(bundle/'ffmpeg/bin/ffmpeg.exe'), '-nostdin', '-hide_banner', '-loglevel', 'error',
                                  '-f', 'lavfi', '-i', 'testsrc=size=64x64:rate=1', '-frames:v', '1',
                                  '-f', 'image2pipe', '-vcodec', 'mjpeg', 'pipe:1'], capture_output=True, timeout=60)
        result['checks']['ffmpeg_synthetic_image'] = {'ok': process.returncode == 0 and process.stdout.startswith(b'\xff\xd8')}
    if not result['checks']['ffmpeg_synthetic_image']['ok']:
        result['checks']['ffmpeg_synthetic_image']['error'] = process.stderr.decode('utf-8', 'replace')[-2000:].replace(str(bundle), '<PROGRAMM>')
    result['success'] = all(item['ok'] for item in result['checks'].values())
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    args = parser.parse_args(argv)
    bundle = Path(args.bundle).resolve()
    try:
        if sys.platform != 'win32':
            raise ValueError('Dieses Pruefprogramm ist fuer Windows bestimmt.')
        result = check(bundle)
    except Exception as error:
        result = {'format': 'kobra-windows-native-package-check-v1', 'success': False,
                  'error_type': type(error).__name__, 'error': str(error).replace(str(bundle), '<PROGRAMM>'),
                  'printer_connections': False, 'nas_services_changed': False}
    name = 'Kobra-ARM-Paketpruefung-' if runtime_architecture() == 'arm64' else 'Kobra-x64-Paketpruefung-'
    name += datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8] + '.json'
    target = bundle.parent / name
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Pruefung erfolgreich.' if result['success'] else 'Pruefung fehlgeschlagen; bitte Bericht weitergeben.')
    print('Bericht:', target)
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
