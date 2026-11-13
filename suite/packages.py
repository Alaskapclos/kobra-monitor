# SPDX-License-Identifier: GPL-3.0-only
"""Authenticate and inspect a complete offline package without extracting it.

Trusted public keys come from the installed application/operator, never the ZIP.
This verifies publisher identity and content, not legal compliance or OS signing.
"""
import base64
import hashlib
import json
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

FORMAT = 'kobra-suite-release-v1'
PLATFORMS = frozenset({'windows-x86_64', 'windows-arm64', 'macos-arm64', 'macos-x86_64',
                       'linux-x86_64', 'linux-arm64',
                       'docker-linux-amd64', 'docker-linux-arm64'})
COMPONENTS = frozenset({'monitor', 'spoolman', 'python', 'ffmpeg'})
MAX_MANIFEST = 4 * 1024**2
MAX_FILE = 4 * 1024**3
MAX_TOTAL = 12 * 1024**3
MAX_FILES = 30000
HEX = re.compile(r'[a-f0-9]{64}\Z')
VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?\Z')


@dataclass(frozen=True)
class VerifiedPackage:
    version: str
    platform: str
    key_id: str
    manifest_sha256: str
    files: int
    expanded_bytes: int


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Doppelter Eintrag im Paketverzeichnis.')
        result[key] = value
    return result


def package_path(name):
    if not isinstance(name, str) or not 1 <= len(name) <= 400:
        raise ValueError('Ungültiger Paketpfad.')
    path = PurePosixPath(name)
    if (path.is_absolute() or path.as_posix() != name or
            any(p in ('', '.', '..') for p in name.split('/')) or
            any(ord(c) < 32 or ord(c) > 126 for c in name) or
            any(c in name for c in '\\:<>"|?*') or len(path.parts) > 32):
        raise ValueError('Unsicherer Paketpfad.')
    for part in path.parts:
        stem = part.split('.')[0].upper()
        if (part.endswith((' ', '.')) or stem in {'CON', 'PRN', 'AUX', 'NUL'} or
                re.fullmatch(r'(?:COM|LPT)[1-9]', stem)):
            raise ValueError('Nicht portabler Paketpfad.')
    return name


def validate_manifest(data, platform):
    if (not isinstance(data, dict) or set(data) !=
            {'format', 'version', 'platform', 'key_id', 'components', 'files'} or
            data['format'] != FORMAT or data['platform'] != platform or
            platform not in PLATFORMS or not isinstance(data['version'], str) or
            len(data['version']) > 64 or not VERSION.fullmatch(data['version'])):
        raise ValueError('Paketversion oder Zielsystem passt nicht.')
    files = data['files']
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError('Ungültiges Dateiverzeichnis.')
    total, folded = 0, set()
    for name, info in files.items():
        package_path(name)
        if not name.startswith(('components/', 'licenses/', 'sources/')) and name not in ('README.md', 'NOTICE.md', 'SBOM.json'):
            raise ValueError('Unerwartete Datei außerhalb der Programm-/Lizenzbereiche.')
        if name.casefold() in folded or name in ('release.json', 'release.sig'):
            raise ValueError('Doppelter oder reservierter Paketpfad.')
        folded.add(name.casefold())
        if (not isinstance(info, dict) or set(info) != {'bytes', 'sha256'} or
                type(info['bytes']) is not int or not 0 <= info['bytes'] <= MAX_FILE or
                not isinstance(info['sha256'], str) or not HEX.fullmatch(info['sha256'])):
            raise ValueError('Ungültige Dateiprüfsumme oder Größe.')
        total += info['bytes']
    # File/directory conflicts also matter on case-insensitive filesystems.
    for name in folded:
        if any(parent.as_posix() in folded for parent in PurePosixPath(name).parents
               if parent.as_posix() != '.'):
            raise ValueError('Datei und Verzeichnis kollidieren.')
    if total > MAX_TOTAL:
        raise ValueError('Das Komplettpaket ist zu groß.')
    components = data['components']
    if not isinstance(components, dict) or set(components) != COMPONENTS:
        raise ValueError('Das Paket enthält nicht alle benötigten Komponenten.')
    for component, info in components.items():
        if (not isinstance(info, dict) or set(info) !=
                {'version', 'license', 'license_file', 'source_file', 'payload_files'} or
                not isinstance(info['version'], str) or not 1 <= len(info['version']) <= 64 or
                not isinstance(info['license'], str) or not 1 <= len(info['license']) <= 160):
            raise ValueError('Versions- oder Lizenznachweise fehlen.')
        if info['version'].lower() in ('latest', 'edge', 'main', 'master', 'stable', 'nightly'):
            raise ValueError('Jede Komponente benötigt eine feste Versionsangabe.')
        if component == 'monitor' and info['version'] != data['version']:
            raise ValueError('Die Monitorversion passt nicht zum Paket.')
        for field, prefix in [('license_file', 'licenses/'), ('source_file', 'sources/')]:
            name = package_path(info[field])
            if not name.startswith(prefix) or name not in files or files[name]['bytes'] == 0:
                raise ValueError('Lizenztext oder zugehörige Quelldatei fehlt.')
        payload = info['payload_files']
        if (not isinstance(payload, list) or not payload or
                any(not isinstance(n, str) or n not in files or
                    not n.startswith('components/' + component + '/') for n in payload) or
                len(payload) != len(set(payload))):
            raise ValueError('Komponenten-Dateien fehlen.')
    owned = {n for component in components.values() for n in component['payload_files']}
    if any(n.startswith('components/') and n not in owned for n in files):
        raise ValueError('Eine Programmdatei ist keiner Komponente zugeordnet.')
    return total


def verify_package(archive, trusted_keys, platform):
    """Read only. Signature covers the exact release.json bytes; hashes cover all files."""
    if platform not in PLATFORMS or not isinstance(trusted_keys, dict):
        raise ValueError('Zielsystem oder vertrauenswürdige Schlüssel fehlen.')
    try:
        with zipfile.ZipFile(archive) as source:
            members = source.infolist()
            if not 3 <= len(members) <= MAX_FILES + 2:
                raise ValueError('Ungültige Dateianzahl.')
            folded = set()
            for item in members:
                package_path(item.filename)
                kind = stat.S_IFMT(item.external_attr >> 16)
                if (item.is_dir() or kind not in (0, stat.S_IFREG) or
                        item.flag_bits & 1 or item.file_size > MAX_FILE or
                        item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) or
                        item.filename.casefold() in folded):
                    raise ValueError('Unsicherer Dateityp oder doppelter Paketpfad.')
                folded.add(item.filename.casefold())
            if (source.getinfo('release.json').file_size > MAX_MANIFEST or
                    source.getinfo('release.sig').file_size > 128):
                raise ValueError('Das signierte Paketverzeichnis ist zu groß.')
            body = source.read('release.json')
            data = json.loads(body, object_pairs_hook=unique_object)
            key_id = data.get('key_id') if isinstance(data, dict) else None
            if not isinstance(key_id, str) or key_id not in trusted_keys:
                raise ValueError('Der Herausgeber ist nicht vertrauenswürdig.')
            signature = base64.b64decode(source.read('release.sig').strip(), validate=True)
            if len(signature) != 64:
                raise ValueError('Ungültige Paketsignatur.')
            Ed25519PublicKey.from_public_bytes(trusted_keys[key_id]).verify(signature, body)
            total = validate_manifest(data, platform)
            if set(source.namelist()) != set(data['files']) | {'release.json', 'release.sig'}:
                raise ValueError('Das Paket ist unvollständig oder enthält zusätzliche Dateien.')
            for name, expected in data['files'].items():
                if source.getinfo(name).file_size != expected['bytes']:
                    raise ValueError('Eine Dateigröße stimmt nicht.')
                digest, size = hashlib.sha256(), 0
                with source.open(name) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        size += len(block)
                        if size > expected['bytes']:
                            raise ValueError('Eine Paketdatei überschreitet ihre Größe.')
                        digest.update(block)
                if size != expected['bytes'] or digest.hexdigest() != expected['sha256']:
                    raise ValueError('Eine Paketdatei wurde verändert oder ist beschädigt.')
            return VerifiedPackage(data['version'], platform, key_id,
                                   hashlib.sha256(body).hexdigest(), len(data['files']), total)
    except (InvalidSignature, KeyError, UnicodeError, json.JSONDecodeError,
            zipfile.BadZipFile, base64.binascii.Error) as error:
        raise ValueError('Das Komplettpaket konnte nicht sicher geprüft werden.') from error
