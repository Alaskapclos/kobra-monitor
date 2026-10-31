# SPDX-License-Identifier: GPL-3.0-only
"""Check the prospective repository contents, not local runtime directories."""
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent.parent
try:
    result=subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True,check=True)
    paths=[root/value for value in result.stdout.decode().split('\0') if value]
except (OSError,subprocess.CalledProcessError):
    paths=[p for p in root.rglob('*') if p.is_file() and not any(v in ('.git','.venv','.state','data','__pycache__') for v in p.relative_to(root).parts)]
errors=[]
for file in paths:
    name=str(file.relative_to(root));parts=file.relative_to(root).parts
    if any(v in ('.state','.venv','data','backups','.backups','__pycache__') for v in parts) or file.name.startswith('kobra-backup-') or file.name.startswith('.account-') or file.name.startswith('.push-') or file.name in ('.env','access-token','account.json','spoolman.json','.DS_Store') or file.suffix in ('.key','.pem','.crt','.sqlite3','.log'):
        errors.append('Runtime/private file: '+name)
    body=file.read_bytes()
    for key_type in ('','RSA ','EC '):
        if ('-----BEGIN '+key_type+'PRIVATE KEY-----').encode() in body:errors.append('Private-key block: '+name)
    if (str(Path.home())+'/').encode() in body:errors.append('Personal absolute path: '+name)
for name in ('LICENSE','NOTICE.md','SOURCES.json','README.md','SECURITY.md','compose.yaml','.github/workflows/ci.yml'):
    if not (root/name).exists():errors.append('Missing '+name)
if errors:
    print('\n'.join(errors));sys.exit(1)
print(f'Release content check passed ({len(paths)} files). This does not replace comprehensive secret scanning.')
