# SPDX-License-Identifier: GPL-3.0-only
"""Assemble an internal Linux test installer from an exact verified image/source pair."""
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import tarfile
import zipfile

from suite.deployment import contract


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def render_installer(image, image_id, archive_name, archive_sha256):
    contract(image)
    if (not re.fullmatch(r'sha256:[a-f0-9]{64}', image_id) or
            not re.fullmatch(r'[a-f0-9]{64}', archive_sha256) or
            not re.fullmatch(r'[A-Za-z0-9._-]+\.tar', archive_name)):
        raise ValueError('Ungültige Paketkennung oder Prüfsumme.')
    template = (Path(__file__).resolve().parent.parent / 'deploy/suite/Installieren.sh.in').read_text()
    for name, value in [('IMAGE', image), ('IMAGE_ID', image_id),
                        ('ARCHIVE', archive_name), ('IMAGE_SHA', archive_sha256)]:
        template = template.replace('@' + name + '@', shlex.quote(value))
    return template


def verify_pair(image_archive, source_archive):
    """No extraction or execution. Check source catalogue, revision and image files."""
    source_hash = digest(source_archive)
    with zipfile.ZipFile(source_archive) as source:
        names = source.namelist()
        if len(names) != len(set(names)) or not 1 <= len(names) <= 30000:
            raise ValueError('Doppelte oder zu viele Quelldateien.')
        if sum(x.file_size for x in source.infolist()) > 128 * 1024**2:
            raise ValueError('Das Quellarchiv ist zu groß.')
        raw_build = source.read('Kobra-Monitor/BUILD.json')
        build = json.loads(raw_build)
        files = build['source_sha256']
        if set(names) != {'Kobra-Monitor/' + n for n in files} | {'Kobra-Monitor/BUILD.json'}:
            raise ValueError('Das Quellverzeichnis ist nicht vollständig.')
        for name, expected in files.items():
            if hashlib.sha256(source.read('Kobra-Monitor/' + name)).hexdigest() != expected:
                raise ValueError('Eine Quelldatei wurde verändert.')
        license_text = source.read('Kobra-Monitor/LICENSE')
        notice_text = source.read('Kobra-Monitor/NOTICE.md')
    image = 'kobra-monitor:' + build['version']
    contract(image)
    expected = {n: v for n, v in files.items() if not n.startswith('.github/') and n != '.env.example'}
    expected['BUILD.json'] = hashlib.sha256(raw_build).hexdigest()
    found = {}
    with tarfile.open(image_archive) as archive:
        manifest = json.load(archive.extractfile('manifest.json'))
        if len(manifest) != 1 or manifest[0].get('RepoTags') != [image]:
            raise ValueError('Das Image gehört nicht zur angegebenen Monitorversion.')
        entry = manifest[0]
        config_bytes = archive.extractfile(entry['Config']).read()
        config = json.loads(config_bytes)
        if config['architecture'] != 'amd64' or config['os'] != 'linux':
            raise ValueError('Nur das geprüfte Linux/amd64-Ziel wird unterstützt.')
        revision = config.get('config', {}).get('Labels', {}).get('org.opencontainers.image.revision')
        if revision != 'local-' + source_hash[:20]:
            raise ValueError('Programmabbild und Quellpaket gehören nicht zum selben Bau.')
        for name in entry['Layers']:
            with tarfile.open(fileobj=archive.extractfile(name)) as layer:
                for member in layer:
                    path = member.name.removeprefix('./')
                    if not path.startswith('app/'):
                        continue
                    relative = path[4:]
                    parent, _, basename = relative.rpartition('/')
                    if basename == '.wh..wh..opq':
                        for previous in list(found):
                            if not parent or previous.startswith(parent + '/'):
                                found.pop(previous)
                    elif basename.startswith('.wh.'):
                        found.pop((parent + '/' if parent else '') + basename[4:], None)
                    elif relative in expected:
                        if not member.isfile():
                            found.pop(relative, None)
                        else:
                            found[relative] = hashlib.sha256(layer.extractfile(member).read()).hexdigest()
    if found != expected:
        raise ValueError('Die Anwendungsdateien passen nicht zum Quellpaket.')
    return {'image': image, 'image_id': 'sha256:' + hashlib.sha256(config_bytes).hexdigest(),
            'image_sha256': digest(image_archive), 'source_sha256': source_hash,
            'app_files_verified': len(found), 'license': license_text, 'notice': notice_text}


def assemble(image_archive, source_archive, destination):
    image_archive, source_archive = Path(image_archive), Path(source_archive)
    proof = verify_pair(image_archive, source_archive)
    target = Path(destination)
    target.mkdir(mode=0o700)  # Never replace an existing package.
    shutil.copyfile(image_archive, target / 'monitor-linux-amd64.tar')
    shutil.copyfile(source_archive, target / 'Quellcode.zip')
    installer = target / 'Installieren.sh'
    installer.write_text(render_installer(proof['image'], proof['image_id'],
                         'monitor-linux-amd64.tar', proof['image_sha256']))
    installer.chmod(0o755)
    (target / 'LICENSE').write_bytes(proof.pop('license'))
    (target / 'NOTICE.md').write_bytes(proof.pop('notice'))
    proof.update(format='kobra-suite-linux-test-installer-v1', signed_release=False,
                 offline_complete=False, spoolman_download_required=True,
                 native_windows_macos=False, production_installed=False)
    (target / 'Paketnachweis.json').write_text(json.dumps(proof, indent=2) + '\n')
    (target / 'LIESMICH.md').write_text('''# Kobra Monitor – Linux-Testinstallation

Technische Vorschau für Linux/amd64 mit vorhandenem Docker Engine und Compose v2.
Noch kein öffentlich signierter Komplettinstaller und kein natives Windows-/Mac-Paket.
Der Monitor einschließlich Python und FFmpeg ist enthalten. Spoolman wird beim ersten
Start direkt als genau festgelegtes offizielles Image heruntergeladen; Internetzugang
ist deshalb erforderlich. Eine vollständig offline nutzbare Auslieferung folgt separat.

Start im entpackten Paketordner: `sh ./Installieren.sh`
Der Assistent fragt nach einem neuen Ordner, der Browseradresse, dem Druckerzugang und einem freien Port.
Standard ist localhost:17125. Für einen anderen Rechner im Heimnetz muss ausdrücklich
die private IPv4-Adresse des Docker-Rechners gewählt werden. Die Anmeldung verwendet
in dieser Vorschau HTTP; für Fernzugriff sind ein gesondert eingerichtetes VPN/HTTPS nötig.
Konto und Passwort legst du selbst im Browser über den vertraulichen Einrichtungslink an.

Erneut starten: `sh ./Installieren.sh start --directory /absoluter/installationsordner`
Status ansehen: `sh ./Installieren.sh status --directory /absoluter/installationsordner`
Die Wiederaufnahme verändert keine Konfiguration und verwendet `--no-recreate`.
Andere Programmversionen und veränderte Dienstdefinitionen werden abgewiesen.

Diese Vorschau legt ausschließlich ein neues Testprojekt an. Standard ist ein isoliertes
Netz ohne Druckerzugang. Mit --network lan beziehungsweise bewusster Auswahl im Assistenten
erhält nur der Monitor Zugang zum Druckernetz. Spoolman bleibt intern; die Sicherung
bleibt netzwerklos. Steuerungen sind zunächst gesperrt und werden je Drucker unter
Einrichten freigegeben. Nach Speichern den Monitor-Container vollständig neu starten.
Ein Druck wird durch die Installation oder das Speichern nicht gestartet. Bestehende Projekte werden nicht migriert.
Ein fehlgeschlagener Start behält Ordner und Daten. Es gibt absichtlich keinen Lösch-
oder automatischen Updatebefehl; eine sichere Updateführung folgt separat.

Die vollständigen Monitor-Quellen samt Fremdhinweisen liegen in Quellcode.zip.
Spoolman-Herkunft und Lizenz: https://github.com/Donkie/Spoolman/tree/v0.27.0
Der Paketnachweis enthält Prüfsummen und Bildkennung. Diese Integritätsprüfung ersetzt
keine Herausgebersignatur; die Vorschau ist kein für öffentliche Verteilung signiertes Release.
''')
    return proof
