# SPDX-License-Identifier: GPL-3.0-only
"""Restore paired data and exact suite configuration to a NEW offline directory."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

import backup
from suite.deployment import contract, compose, validate
from suite.packages import unique_object
from suite.snapshots import verify_snapshot


def deployment_from_snapshot(snapshot, proof):
    with zipfile.ZipFile(Path(snapshot) / 'monitor.zip') as archive:
        if archive.getinfo('compose.yaml').file_size > 65536:
            raise ValueError('Die Dienste-Konfiguration ist zu groß.')
        deployment = json.loads(archive.read('compose.yaml'), object_pairs_hook=unique_object)
    if not isinstance(deployment, dict):
        raise ValueError('Die Dienste-Konfiguration fehlt.')
    try:
        port_binding = deployment['services']['monitor']['ports'][0]
        port = int(port_binding.split(':')[1])
        c = contract(proof['images']['monitor'], project=deployment['name'], port=port,
                     address=port_binding.split(':')[0])
    except (KeyError, TypeError, ValueError, IndexError):
        raise ValueError('Keine unterstützte Suite-Konfiguration.') from None
    if proof['images']['spoolman'] != c['spoolman_image'] or compose(c) != deployment:
        raise ValueError('Die Dienste-Konfiguration passt nicht zu den geprüften Komponenten.')
    return validate(c), deployment


def restore_to_new_directory(snapshot, target):
    """No Docker, no live restore, no overwrite. Installation/start is a later step."""
    source, target = Path(snapshot).resolve(), Path(target).absolute()
    if target.exists() or target.is_symlink() or not target.parent.is_dir():
        raise ValueError('Ein neues Ziel in einem vorhandenen getrennten Ordner verwenden.')
    resolved = target.resolve()
    if resolved == source or resolved in source.parents or source in resolved.parents:
        raise ValueError('Das Wiederherstellungsziel muss getrennt von der Sicherung liegen.')
    proof = verify_snapshot(source)
    config, deployment = deployment_from_snapshot(source, proof)
    with tempfile.TemporaryDirectory(prefix='.kobra-suite-restore-', dir=target.parent) as folder:
        stage = Path(folder) / 'restored'
        stage.mkdir(mode=0o700)
        backup.restore(source / 'monitor.zip', stage / 'monitor-data')
        spoolman = stage / 'spoolman-data'
        spoolman.mkdir(mode=0o700)
        shutil.copyfile(source / 'spoolman.sqlite3', spoolman / 'spoolman.db')
        (spoolman / 'spoolman.db').chmod(0o600)
        # These are offline data folders, NOT existing Docker volumes. Starting a
        # restored deployment requires an explicit future import/migration step.
        for name, data in [('recorded-suite.json', config), ('recorded-compose.json', deployment)]:
            file = stage / name
            file.write_text(json.dumps(data, indent=2) + '\n')
            file.chmod(0o600)
        metadata = json.loads((source / 'snapshot.json').read_text(), object_pairs_hook=unique_object)
        if backup.digest(spoolman / 'spoolman.db') != metadata['files']['spoolman.sqlite3']['sha256']:
            raise ValueError('Die Spoolman-Sicherung änderte sich während der Wiederherstellung.')
        if target.exists() or target.is_symlink():
            raise ValueError('Das Wiederherstellungsziel wurde zwischenzeitlich angelegt.')
        os.rename(stage, target)
    return target
