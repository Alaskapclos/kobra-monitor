# SPDX-License-Identifier: GPL-3.0-only
"""Inspect prospective public source files or a source ZIP; never runtime data."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile

MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
REQUIRED = ('LICENSE', 'NOTICE.md', 'SOURCES.json', 'README.md', 'SECURITY.md',
            'VERSION', 'compose.yaml', '.github/workflows/ci.yml')
PRIVATE_PARTS = {'.git', '.state', '.venv', 'data', 'backups', '.backups', 'report-archive',
                 'file-archive', '.archive-incoming', 'archive-queue', '__pycache__'}
PRIVATE_NAMES = {'.env', 'access-token', 'account.json', 'spoolman.json',
                 'archive-client.json', 'native-controls.json', 'push-vapid.pem', '.DS_Store', 'config.json'}


def safe_name(name):
    parts = PurePosixPath(name).parts
    return bool(name and not name.startswith('/') and '\\' not in name and
                ':' not in name and all(p not in ('', '.', '..') for p in name.split('/'))
                and all(ord(c) >= 32 for c in name) and parts)


def collect_source(root):
    """Git's prospective file list includes new files, but ignores private working data."""
    frozen = False
    try:
        result = subprocess.run(['git', 'ls-files', '--cached', '--others',
                                 '--exclude-standard', '-z'], cwd=root,
                                capture_output=True, check=True)
        names = result.stdout.decode().split('\0')
    except FileNotFoundError:
        # Source-only build containers need not contain Git. Inspect every
        # member and require the complete frozen catalogue with every hash.
        if (root / '.git').exists():
            raise
        names = []
        for path in root.rglob('*'):
            if path.is_symlink() or path.is_file():
                names.append(path.relative_to(root).as_posix())
                if len(names) > 20000:
                    return {}, ['Frozen source tree exceeds member limit']
        frozen = True
    files, errors, total = {}, [], 0
    for name in sorted(set(n for n in names if n)):
        if not safe_name(name):
            errors.append('Unsafe source path: ' + repr(name)); continue
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            errors.append('Missing or linked source file: ' + name); continue
        size = path.stat().st_size; total += size
        if size > MAX_FILE or total > MAX_TOTAL:
            errors.append('Source size limit exceeded: ' + name); continue
        files[name] = path.read_bytes()
    if frozen:
        errors += check_files(files, check_build=True)
    return files, errors


def collect_zip(path):
    """Read a bounded source archive without extracting any member."""
    files, errors = {}, []
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 20000 or sum(i.file_size for i in entries) > MAX_TOTAL:
            return {}, ['Source ZIP exceeds size or member limit']
        seen = set()
        for entry in entries:
            raw = entry.filename.rstrip('/')
            if raw == 'Kobra-Monitor' and entry.is_dir():
                kind = stat.S_IFMT(entry.external_attr >> 16)
                if kind not in (0, stat.S_IFDIR) or entry.flag_bits & 1:
                    errors.append('Linked, encrypted or special ZIP root')
                continue
            if not safe_name(raw) or not raw.startswith('Kobra-Monitor/'):
                errors.append('Unsafe or unexpected ZIP path: ' + repr(entry.filename)); continue
            name = raw[len('Kobra-Monitor/'):]
            if not name:
                continue
            if name.casefold() in seen:
                errors.append('Duplicate ZIP path: ' + name); continue
            seen.add(name.casefold())
            kind = stat.S_IFMT(entry.external_attr >> 16)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or entry.flag_bits & 1:
                errors.append('Linked, encrypted or special ZIP member: ' + name); continue
            if entry.is_dir():
                continue
            if entry.file_size > MAX_FILE:
                errors.append('ZIP member exceeds size limit: ' + name); continue
            files[name] = archive.read(entry)
    return files, errors


def check_files(files, *, home=None, check_build=False):
    errors = []
    for name, body in files.items():
        path = PurePosixPath(name); lower = path.name.lower()
        if (set(path.parts) & PRIVATE_PARTS or path.name in PRIVATE_NAMES or
            path.name.startswith(('kobra-backup-', '.account-', '.push-', '.spoolman-')) or
            path.suffix.lower() in ('.key', '.pem', '.crt', '.ppk', '.p12', '.pfx', '.log', '.3mf', '.gcode', '.stl', '.obj', '.step', '.stp') or
            re.search(r'\.(?:sqlite3?|db)(?:-(?:wal|shm|journal))?$', lower)):
            errors.append('Runtime/private file: ' + name)
        for key_type in ('', 'RSA ', 'EC ', 'OPENSSH ', 'DSA ', 'ENCRYPTED '):
            marker = ('-----BEGIN ' + key_type + 'PRIVATE KEY-----').encode()
            if marker in body:
                errors.append('Private-key block: ' + name); break
        # The vendored bridge contains public Klipper service defaults. Permit only
        # those exact literals in that exact file; other home paths remain blocked.
        path_body = body
        if name == 'vendor/kobra-bridge/kobrax_moonraker_bridge.py':
            for default in (b'/home/' + b'pi/klipper', b'/home/' + b'pi/klippy-env/bin/python',
                            b'/home/' + b'pi/printer.cfg'):
                path_body = path_body.replace(b'"' + default + b'"', b'"service-default"')
        personal_path = rb'(?:/Users/[A-Za-z0-9_.-]+/|/home/[A-Za-z0-9_.-]+/|[A-Za-z]:\\Users\\[A-Za-z0-9_. -]+\\)'
        if ((home and (str(home).rstrip('/') + '/').encode() in body) or
            re.search(personal_path, path_body)):
            errors.append('Personal absolute path: ' + name)
    for name in REQUIRED:
        if name not in files:
            errors.append('Missing ' + name)
    version = files.get('VERSION', b'').decode('utf-8', errors='replace').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?', version):
        errors.append('Invalid VERSION')
    for name in ('compose.yaml', 'deploy/ugos/compose.yaml',
                 'deploy/ugos/backups.compose.yaml', '.github/workflows/ci.yml'):
        if name in files:
            for value in re.findall(r'kobra-monitor:([0-9][0-9A-Za-z.\-]+)', files[name].decode()):
                if value != version:
                    errors.append('Image version mismatch: ' + name)
    readme = files.get('README.md', b'').decode(errors='replace')
    if '**Entwicklungsstand: ' + version + ' ' not in readme:
        errors.append('README version mismatch')
    index = files.get('static/index.html', b'').decode(errors='replace')
    if index and 'KOBRA MONITOR / ' + '.'.join(version.split('.')[:2]) + ' ALPHA' not in index:
        errors.append('UI version mismatch')
    if check_build:
        try:
            build = json.loads(files['BUILD.json'])
            expected = build['source_sha256']
            if build['version'] != version or not isinstance(expected, dict):
                raise ValueError('version or file map')
            actual = {name: hashlib.sha256(body).hexdigest()
                      for name, body in files.items() if name != 'BUILD.json'}
            if expected != actual:
                errors.append('BUILD source manifest differs from prospective contents; freeze and rebuild')
        except (KeyError, ValueError, TypeError):
            errors.append('Missing or invalid BUILD source manifest')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-zip', type=Path, help='Check the exact source ZIP without extracting it')
    parser.add_argument('--check-build', action='store_true', help='Require a current, complete BUILD.json')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    try:
        files, errors = collect_zip(args.source_zip) if args.source_zip else collect_source(root)
        errors += check_files(files, home=Path.home(), check_build=args.check_build)
    except (OSError, subprocess.CalledProcessError, zipfile.BadZipFile, RuntimeError) as error:
        print('Release inspection could not complete: ' + type(error).__name__)
        return 1
    if errors:
        print('\n'.join(errors)); return 1
    print(f'Release content check passed ({len(files)} files). '
          'This does not replace comprehensive secret, history, image or license review.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
