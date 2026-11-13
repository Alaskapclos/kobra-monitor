# SPDX-License-Identifier: GPL-3.0-only
"""Bounded file-integrity checks shared by native test launchers."""
import hashlib
import json
from pathlib import Path
import re
from suite.packages import package_path


def load_manifest(bundle, *, format, platform, verify=False):
    bundle=Path(bundle).resolve();manifest=bundle/'native-bundle.json'
    if manifest.is_symlink() or manifest.stat().st_size>8*1024*1024:
        raise ValueError('Das Paketverzeichnis ist ungültig.')
    data=json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('format')!=format or data.get('platform')!=platform:
        raise ValueError('Dieses Paket gehört nicht zur unterstützten Plattform.')
    if (not isinstance(data.get('version'),str) or
        not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?',data['version']) or
        not isinstance(data.get('bundle_id'),str) or not re.fullmatch('[a-f0-9]{64}',data['bundle_id'])):
        raise ValueError('Die Paketversion ist ungültig.')
    files=data.get('files')
    if not isinstance(files,dict) or not 10<len(files)<=50000:
        raise ValueError('Das Paket ist nicht vollständig.')
    for relative,expected in files.items():
        package_path(relative)
        if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected):
            raise ValueError('Ungültige Dateiprüfsumme im Paket.')
        path=bundle/relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(bundle):
            raise ValueError('Eine Programmdatei fehlt oder wurde ersetzt.')
        if verify:
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(4*1024*1024),b''):digest.update(block)
            if digest.hexdigest()!=expected:
                raise ValueError('Eine Programmdatei wurde verändert. Bitte das Testpaket erneut entpacken.')
    return data
