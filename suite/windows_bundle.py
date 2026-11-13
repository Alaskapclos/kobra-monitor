# SPDX-License-Identifier: GPL-3.0-only
"""Cross-assemble a native Windows test payload. Never executes Windows binaries."""
import base64
import csv
import email
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import stat
import struct
import tempfile
import zipfile

from suite.packages import package_path
from suite.native_entrypoints import windows_alembic
from suite.native_targets import native_target, wheel_matches

PYTHON_ARCHIVE = 'python-3.14.10-embed-amd64.zip'
PYTHON_SHA = '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
SPOOLMAN_ARCHIVE = 'spoolman-0.27.0.zip'
SPOOLMAN_SHA = 'bcc961af4c20d7ad7f1740f5609cd3efd94c4556baafaeba5036122dd7e46704'
FFMPEG_ARCHIVE = 'ffmpeg-win64-lgpl-shared-368ccdd1.zip'
FFMPEG_SHA = '368ccdd16812dd8bea088c3581ba4bab27151b4711049354f87680d2c129cc9b'
PYTHON_ARM_ARCHIVE = 'python-3.14.10-embed-arm64.zip'
PYTHON_ARM_SHA = 'bbe116bb1248820359cbf25127ac5c7794ea161869d83686cfbc9a45203ff836'
FFMPEG_ARM_ARCHIVE = 'ffmpeg-n9.0.2-48-gd4070a14ce-winarm64-lgpl-9.0.zip'
FFMPEG_ARM_SHA = '98bd572e1e4cf98b54cbba24f492441e29cea600bc9cf77a7739cff502c677fc'
# The official ARM Python ZIP also carries this unused AMD64 compatibility DLL.
# Omit exactly these bytes; every active import is checked below before publication.
ARM_UNUSED_DLL = 'vcruntime140_1.dll'
ARM_UNUSED_DLL_SHA = '60c70e34e2e156f8bd214b92c2125c252e17d86ac8a25799ea1a4ecabde1d97c'

# Setuptools ships these inert launcher templates in its platform-neutral wheel.
# They are package data, never used by our explicit python.exe entrypoints.
SETUPTOOLS_TEMPLATES = {name: machine for name, machine in (
    ('cli.exe', 0x14c), ('gui.exe', 0x14c), ('cli-32.exe', 0x14c),
    ('gui-32.exe', 0x14c), ('cli-64.exe', 0x8664), ('gui-64.exe', 0x8664), ('cli-arm64.exe', 0xaa64), ('gui-arm64.exe', 0xaa64))}


def check_native_arch(relative, body, *, architecture='x86_64'):
    expected = native_target('windows', architecture).cpu
    for name, machine in SETUPTOOLS_TEMPLATES.items():
        if relative.endswith('Lib/site-packages/setuptools/' + name):
            expected = machine
            break
    if pe_machine(body) != expected:
        raise ValueError('Eine native Bibliothek hat eine unerwartete Windows-Architektur: '+relative)


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):value.update(block)
    return value.hexdigest()


def checked_archive(path, expected):
    if digest(path)!=expected:raise ValueError('Die Eingabedatei hat eine falsche Prüfsumme: '+Path(path).name)
    return zipfile.ZipFile(path)


def members(archive):
    entries=archive.infolist()
    if len(entries)>50000 or sum(x.file_size for x in entries)>1024**3:
        raise ValueError('Das Eingabearchiv ist zu groß.')
    seen=set()
    for info in entries:
        name=info.filename.rstrip('/')
        package_path(name)
        if name.casefold() in seen:raise ValueError('Doppelte Windows-Dateinamen im Archiv.')
        seen.add(name.casefold())
        kind=stat.S_IFMT(info.external_attr>>16)
        if kind not in (0,stat.S_IFREG,stat.S_IFDIR) or info.flag_bits&1:
            raise ValueError('Unsicherer Archiv-Dateityp.')
    return entries


def write_file(root, relative, body):
    package_path(relative)
    target=Path(root)/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and target.read_bytes()!=body:
        raise ValueError('Zwei Komponenten überschreiben dieselbe Datei: '+relative)
    target.write_bytes(body)


def extract(archive,target,*,strip_prefix=''):
    for info in members(archive):
        if info.is_dir():continue
        name=info.filename
        if strip_prefix:
            if not name.startswith(strip_prefix):raise ValueError('Unerwarteter Archivwurzelordner.')
            name=name[len(strip_prefix):]
        if name:write_file(target,name,archive.read(info))


def pe_machine(body):
    if len(body)<64 or body[:2]!=b'MZ':raise ValueError('Keine gültige Windows-Binärdatei.')
    offset=struct.unpack_from('<I',body,0x3c)[0]
    if offset>len(body)-6 or body[offset:offset+4]!=b'PE\x00\x00':
        raise ValueError('Ungültiger PE-Dateikopf.')
    return struct.unpack_from('<H',body,offset+4)[0]


def pe_imports(body):
    """Read normal and delay imports of an active PE32+ image, with bounded RVAs."""
    pe_machine(body)
    pe = struct.unpack_from('<I', body, 60)[0]
    count, optsize = struct.unpack_from('<H', body, pe + 6)[0], struct.unpack_from('<H', body, pe + 20)[0]
    opt = pe + 24
    if optsize < 112 or opt + optsize > len(body) or struct.unpack_from('<H', body, opt)[0] != 0x20b:
        raise ValueError('Ungültiger PE32+-Importkatalog.')
    sections = []
    for i in range(count):
        pos = opt + optsize + i * 40
        if pos + 40 > len(body):raise ValueError('Ungültiger PE-Abschnitt.')
        virtual, address, size, raw = struct.unpack_from('<IIII', body, pos + 8)
        sections.append((address, size, raw))
    def offset(rva, size=1):
        for address, rawsize, raw in sections:
            delta = rva - address
            if 0 <= delta and delta + size <= rawsize and raw + delta + size <= len(body):return raw + delta
        raise ValueError('Ungültiger Import-Zeiger.')
    def name(rva):
        pos = offset(rva)
        end = body.find(b'\0', pos, min(len(body), pos + 260))
        if end < pos:raise ValueError('Nicht abgeschlossener DLL-Name.')
        return body[pos:end].decode('ascii').casefold()
    imports = []
    dirs = struct.unpack_from('<I', body, opt + 108)[0]
    for index, stride in ((1, 20), (13, 32)):
        if dirs <= index:continue
        pos = opt + 112 + index * 8
        if pos + 8 > opt + optsize:raise ValueError('Ungültiges Import-Verzeichnis.')
        rva, size = struct.unpack_from('<II', body, pos)
        if not rva:continue
        if not size or size // stride > 4096:raise ValueError('Import-Verzeichnis zu groß.')
        terminated = False
        for i in range(size // stride):
            pos = offset(rva + i * stride, stride)
            fields = struct.unpack_from('<' + 'I' * (stride // 4), body, pos)
            if not any(fields):terminated = True;break
            if index == 13 and fields[0] != 1:raise ValueError('Nicht unterstützte verzögerte Import-Adresse.')
            imports.append(name(fields[3] if index == 1 else fields[1]))
        if not terminated:raise ValueError('Nicht abgeschlossener Import-Katalog.')
    return imports


def extract_python(archive, target, architecture):
    for info in members(archive):
        if info.is_dir():continue
        body = archive.read(info)
        if architecture == 'arm64' and info.filename == ARM_UNUSED_DLL:
            if hashlib.sha256(body).hexdigest() != ARM_UNUSED_DLL_SHA or pe_machine(body) != 0x8664:
                raise ValueError('Unerwartete Python-Kompatibilitätsdatei.')
            continue
        write_file(target, info.filename, body)


def wheel_record(archive, *, compatible_tag=None, architecture='x86_64'):
    target = native_target('windows', architecture)
    entries=members(archive);names={x.filename for x in entries if not x.is_dir()}
    metadata=[n for n in names if n.count('/') == 1 and n.endswith('.dist-info/METADATA')]
    if len(metadata)!=1:raise ValueError('Wheel-Metadaten fehlen oder sind doppelt.')
    prefix=metadata[0].removesuffix('METADATA')
    wheel=email.message_from_bytes(archive.read(prefix+'WHEEL'))
    compatible=False
    for tag in wheel.get_all('Tag',[]):
        if compatible_tag is not None:
            compatible=compatible or compatible_tag(tag)
            continue
        compatible = compatible or wheel_matches(tag, target)
    if not compatible:raise ValueError('Das Wheel passt nicht zur vorgesehenen Python-Plattform.')
    rows=list(csv.reader(io.StringIO(archive.read(prefix+'RECORD').decode())))
    if len(rows)!=len({r[0] for r in rows}) or {r[0] for r in rows}!=names:
        raise ValueError('Das Wheel-Dateiverzeichnis ist nicht vollständig.')
    for name,checksum,size in rows:
        if name==prefix+'RECORD' and not checksum:continue
        if not checksum.startswith('sha256='):raise ValueError('Eine Wheel-Prüfsumme fehlt.')
        body=archive.read(name)
        expected=base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b'=').decode()
        if checksum!='sha256='+expected or int(size)!=len(body):raise ValueError('Das Wheel wurde verändert.')
    meta=email.message_from_bytes(archive.read(metadata[0]))
    return {'name':meta['Name'],'version':meta['Version'],
            'license_expression':meta.get('License-Expression'),
            'license_files':[n for n in names if '/licenses/' in n or n.endswith(('LICENSE','LICENSE.txt','COPYING'))]}


def install_wheel(path,runtime, *, architecture='x86_64'):
    native_target('windows', architecture)
    runtime=Path(runtime)
    with zipfile.ZipFile(path) as archive:
        metadata=wheel_record(archive,architecture=architecture)
        for info in archive.infolist():
            if info.is_dir():continue
            name=info.filename
            if name.endswith(('.so','.dylib')):raise ValueError('Fremde native Bibliothek im Windows-Paket.')
            parts=name.split('/')
            if len(parts)>2 and parts[0].endswith('.data'):
                category=parts[1];tail='/'.join(parts[2:])
                if category in ('purelib','platlib'):name='Lib/site-packages/'+tail
                elif category=='scripts':name='Scripts/'+tail
                elif category=='headers':name='include/'+metadata['name']+'/'+tail
                elif category=='data':name='share/'+metadata['name']+'/'+tail
                else:raise ValueError('Unbekannter Wheel-Datenbereich.')
            else:name='Lib/site-packages/'+name
            body=archive.read(info)
            if name.lower().endswith(('.dll','.pyd','.exe')):
                check_native_arch(name, body, architecture=architecture)
            write_file(runtime,name,body)
    return metadata


def copy_monitor(source,target):
    source,target=Path(source),Path(target)
    build=json.loads((source/'BUILD.json').read_text())
    if (source/'VERSION').read_text().strip()!=build['version']:
        raise ValueError('Quellcode und Versionskatalog passen nicht zusammen.')
    for name,sha in build['source_sha256'].items():
        path=source/name
        if digest(path)!=sha:raise ValueError('Eine Monitor-Quelldatei passt nicht zum geprüften Katalog.')
        write_file(target,name,path.read_bytes())
    write_file(target,'BUILD.json',(source/'BUILD.json').read_bytes())
    return build['version']


def install_camera_component(camera_input, target, *, platform):
    """Install a checksum-pinned camera kit without using the historic FFmpeg bundles."""
    path, checksum = camera_input
    with checked_archive(path, checksum) as archive:
        entries = {info.filename for info in members(archive) if not info.is_dir()}
        proof_name = 'Bau-und-Lizenznachweis.json'
        proof = json.loads(archive.read(proof_name))
        hashes = proof['files']
        required = {'Kamera-Test.py', 'Kamera-Teststream.flv', 'Lizenzen/COPYING.LGPLv2.1',
                    'Lizenzen/LICENSE.md', 'Lizenzen/configure_camera_ffmpeg.sh'}
        executable = 'ffmpeg/bin/ffmpeg.exe' if platform.startswith('windows') else 'ffmpeg/bin/ffmpeg'
        if (proof['platform'] != platform or proof['license'] != 'LGPL-2.1-or-later'
                or entries != set(hashes) | {proof_name}
                or not required | {executable} <= set(hashes)):
            raise ValueError('Der Kamera-Bau- und Lizenznachweis passt nicht zum Zielpaket.')
        if sum(name.startswith('ffmpeg/') for name in hashes) != 6:
            raise ValueError('Der Kamera-Bau enthält unerwartete Laufzeitdateien.')
        for name, expected in hashes.items():
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError('Eine Kamera-Datei passt nicht zum Lizenznachweis.')
            if name.startswith('ffmpeg/'):
                destination = name
            elif name.startswith('Lizenzen/'):
                destination = 'licenses/ffmpeg/' + name.removeprefix('Lizenzen/')
            elif name in {'Kamera-Test.py', 'Kamera-Teststream.flv'}:
                destination = 'ffmpeg/test/' + name
            else:
                raise ValueError('Unerwartete Datei im Kamera-Paket.')
            write_file(target, destination, data)
            if name.startswith('ffmpeg/') and platform.startswith('macos'):
                (target/destination).chmod(0o755)
        write_file(target, 'licenses/ffmpeg/' + proof_name, archive.read(proof_name))
    return {'version': '8.1.3', 'sha256': checksum, 'license': proof['license'],
            'source_archive': proof['source_archive'], 'source_sha256': proof['source_sha256']}


def build(inputs,source,destination, *, architecture='x86_64', camera_input=None):
    target = native_target('windows', architecture)
    python_archive, python_sha = (PYTHON_ARM_ARCHIVE, PYTHON_ARM_SHA) if architecture == 'arm64' else (PYTHON_ARCHIVE, PYTHON_SHA)
    ffmpeg_archive, ffmpeg_sha = (FFMPEG_ARM_ARCHIVE, FFMPEG_ARM_SHA) if architecture == 'arm64' else (FFMPEG_ARCHIVE, FFMPEG_SHA)
    inputs,source,destination=Path(inputs),Path(source),Path(destination)
    if destination.exists() or destination.is_symlink():raise FileExistsError('Das Paketverzeichnis existiert bereits.')
    provenance=json.loads((inputs/'wheel-provenance.json').read_text())
    closure=json.loads((inputs/'wheel-closure-proof.json').read_text())
    if not all(closure[role]['dependency_closure_verified'] for role in ('monitor','spoolman')):
        raise ValueError('Der Nachweis der Windows-Abhängigkeiten fehlt.')
    with tempfile.TemporaryDirectory(prefix='.windows-bundle-',dir=destination.parent) as folder:
        stage=Path(folder)/'payload';stage.mkdir()
        version=copy_monitor(source,stage/'app/monitor')
        components={'python':{'version':'3.14.10','sha256':python_sha,'architecture':architecture},
                    'spoolman':{'version':'0.27.0','sha256':SPOOLMAN_SHA},
                    'ffmpeg':{'version':('9.0.2-btbn-d4070a14ce' if architecture == 'arm64' else '8.1-btbn-368ccdd1'),'sha256':ffmpeg_sha},'wheels':{}}
        if architecture == 'arm64':
            components['python']['omitted_unused_compatibility_files'] = [{'file':ARM_UNUSED_DLL,'sha256':ARM_UNUSED_DLL_SHA,'reason':'AMD64 compatibility file; no normal or delay import from active ARM64 members.'}]
        for role in ('monitor','spoolman'):
            runtime=stage/'runtime'/role
            with checked_archive(inputs/python_archive,python_sha) as archive:extract_python(archive,runtime,architecture)
            wheel_files=sorted((inputs/('wheels-'+role+('-winarm64' if architecture == 'arm64' else '-win64'))).glob('*.whl'))
            if len(wheel_files)!=closure[role]['packages']:raise ValueError('Eine Windows-Bibliothek fehlt.')
            installed=[]
            for wheel in wheel_files:
                relative=str(wheel.relative_to(inputs))
                proof=next((p for p in provenance if p['file']==relative),None)
                if proof is None or digest(wheel)!=proof['sha256']:raise ValueError('Die Wheel-Herkunft ist nicht belegt.')
                installed.append({**install_wheel(wheel,runtime,architecture=architecture),'sha256':proof['sha256'],
                                  'url':proof['url'],'source_url':proof['source_url']})
            components['wheels'][role]=installed
            paths=['python314.zip','.','Lib/site-packages','../../app/'+role]
            if role=='spoolman':paths.append('../../app/monitor')
            (runtime/'python314._pth').write_text('\n'.join(paths)+'\n',encoding='utf-8')
        distlib=json.loads((inputs/'distlib-provenance.json').read_text())
        with checked_archive(inputs/distlib['file'],distlib['sha256']) as archive:
            wheel_record(archive)
            launcher=archive.read('distlib/t64-arm.exe' if architecture == 'arm64' else 'distlib/t64.exe')
            if pe_machine(launcher)!=target.cpu:raise ValueError('Der Datenbank-Starthelfer passt nicht zur Windows-Architektur.')
            write_file(stage,'runtime/spoolman/Scripts/alembic.exe',windows_alembic(launcher))
            for info in archive.infolist():
                if not info.is_dir() and ('/licenses/' in info.filename or info.filename.endswith(('LICENSE.txt','METADATA'))):
                    write_file(stage,'licenses/distlib/'+info.filename,archive.read(info))
        components['database_console_launcher']={**distlib,'relative_python':'<launcher_dir>\\..\\python.exe'}
        with checked_archive(inputs/SPOOLMAN_ARCHIVE,SPOOLMAN_SHA) as archive:extract(archive,stage/'app/spoolman')
        if camera_input is None:
            with checked_archive(inputs/ffmpeg_archive,ffmpeg_sha) as archive:
                prefix=archive.infolist()[0].filename.split('/')[0]+'/'
                extract(archive,stage/'ffmpeg',strip_prefix=prefix)
        else:
            camera_platform = 'windows-arm64' if architecture == 'arm64' else 'windows-x64'
            components['ffmpeg'] = install_camera_component(camera_input, stage, platform=camera_platform)
        write_file(stage, 'licenses/http-ece-1.2.1-MIT.txt',
                   (source/'licenses/http-ece-1.2.1-MIT.txt').read_bytes())
        for path in stage.rglob('*'):
            if path.is_file() and path.suffix.lower() in ('.exe','.dll','.pyd'):
                check_native_arch(path.relative_to(stage).as_posix(), path.read_bytes(), architecture=architecture)
                if architecture == 'arm64' and pe_machine(path.read_bytes()) == target.cpu and ARM_UNUSED_DLL in pe_imports(path.read_bytes()):
                    raise ValueError('Eine aktive Bibliothek benötigt die ausgelassene Kompatibilitätsdatei.')
        for file in ('ffmpeg.exe', 'ffprobe.exe') if camera_input is None else ('ffmpeg.exe',):
            if not (stage/'ffmpeg/bin'/file).is_file():raise ValueError('Die Kamera-Laufzeit fehlt.')
        for name,mode in [('Installieren.cmd','install'),('Start-Kobra-Monitor.cmd','start'),('Kobra-Monitor-beenden.cmd','stop')]:
            (stage/name).write_text('@echo off\r\nsetlocal\r\nstart "" "%~dp0runtime\\monitor\\pythonw.exe" -X utf8 "%~dp0app\\monitor\\desktop_entry.py" --bundle "%~dp0." --mode '+mode+'\r\n',encoding='ascii',newline='')
        (stage/'Pruefen.cmd').write_text('@echo off\r\nsetlocal\r\n"%~dp0runtime\\monitor\\python.exe" -I -B -X utf8 "%~dp0app\\monitor\\suite\\native_windows_smoke.py" --bundle "%~dp0."\r\nset "KOBRA_CHECK_RESULT=%ERRORLEVEL%"\r\npause\r\nexit /b %KOBRA_CHECK_RESULT%\r\n',encoding='ascii',newline='')
        (stage/'LIESMICH.md').write_text('''# Kobra Monitor – native Windows-Testversion

Windows x64 oder ARM64 entsprechend der Paketkennung. Python, Spoolman mit Weboberfläche und FFmpeg sind enthalten.
Docker und eine eigene Python-Installation sind nicht erforderlich. Microsofts C++-Laufzeit
wird beim Start geprüft; falls sie fehlt, kann der Assistent den Originalinstaller direkt
von Microsoft herunterladen und nach Signaturprüfung öffnen. Dafür sind einmalig Internet
und gegebenenfalls Administratorrechte erforderlich. Microsofts Lizenzbedingungen werden
im Originalinstaller angezeigt. Das Paket zuerst
vollständig entpacken, dann Installieren.cmd doppelt anklicken. Der Assistent richtet
eine getrennte Testinstallation unter LocalAppData/KobraMonitor-Test ein und legt
Start-/Beenden-Verknüpfungen auf dem Desktop an. Konto und Passwort legst du selbst
im geöffneten Browser an. Ein erneuter Start öffnet die laufende lokale Anwendung.

Monitor, Spoolman und die lokale Prozesssteuerung sind nur über localhost erreichbar.
Spoolman ist zusätzlich intern geschützt. Drucker müssen selbst im Monitor eingerichtet
werden; Druckersteuerungen sind in dieser Testinstallation standardmäßig nicht freigegeben.
Vorhandene NAS-Installationen und ihre Daten werden nicht übernommen oder verändert.

Programmdaten und persönliche Daten liegen getrennt. Die lokale Datensicherung beginnt
nach der Druckereinrichtung und sichert beide Datenbanken mit isolierter Restoreprüfung.
Die Komplettsicherung umfasst nur den enthaltenen lokalen Spoolman. Ein extern angebundener
Spoolman benötigt eine eigene Sicherung. Backups bleiben im lokalen Datenordner.
Automatische Versionsupdates, eine komfortable
Wiederherstellungsoberfläche und begrenzte Aufbewahrung sind noch nicht fertig.

Dies ist eine erste Windows-Testversion, kein öffentlich signiertes Release. Die echte
Windows-Abnahme muss auf dem Testrechner erfolgen. Bei einem Fehler erscheint ein Hinweis
mit dem lokalen Protokollordner. Protokolle können private Pfade enthalten; nicht ungeprüft
veröffentlichen. Die vollständige konkrete Lizenz-/Quellprüfung für eine öffentliche
Auslieferung ist noch offen; Original-Lizenztexte und Paketmetadaten bleiben enthalten.
''',encoding='utf-8')
        files={str(p.relative_to(stage)).replace('\\','/'):digest(p) for p in sorted(stage.rglob('*')) if p.is_file()}
        bundle_id=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
        manifest={'format':'kobra-windows-test-bundle-v1','version':version,
                  'platform':target.platform,'bundle_id':bundle_id,'files':files,
                  'components':components,'offline_complete':False,'signed_release':False,
                  'windows_acceptance_passed':False}
        (stage/'native-bundle.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        import os
        os.rename(stage,destination)
    return {'version':version,'bundle_id':bundle_id,'files':len(files),'offline_complete':False,
            'windows_acceptance_passed':False,'programs_executed_during_build':False}
