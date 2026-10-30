# SPDX-License-Identifier: GPL-3.0-only
"""Create/update a private Python environment, then launch the monitor."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent

def ensure_runtime(root=ROOT):
    root=Path(root);environment=root/'.venv'
    python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():
        print('Kobra Monitor wird einmalig eingerichtet …',flush=True)
        subprocess.check_call([sys.executable,'-m','venv',str(environment)])
    digest=hashlib.sha256((root/'requirements-lock.txt').read_bytes()).hexdigest()
    marker=environment/'installed-lock.sha256'
    if not marker.exists() or marker.read_text().strip()!=digest:
        print('Benötigte Bibliotheken werden installiert bzw. aktualisiert …',flush=True)
        subprocess.check_call([str(python),'-m','pip','install','-r',str(root/'requirements-lock.txt')])
        marker.write_text(digest+'\n')
    return python

def main():
    if sys.version_info<(3,11):raise SystemExit('Bitte Python 3.11 oder neuer installieren.')
    python=ensure_runtime()
    return subprocess.call([str(python),str(ROOT/'monitor.py'),*sys.argv[1:]],cwd=ROOT)

if __name__=='__main__':raise SystemExit(main())
