# SPDX-License-Identifier: GPL-3.0-only
"""Build an isolated native Mac test app from verified, locally cached inputs."""
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from suite.macos_metadata import clean_packaging_metadata
from suite.native_targets import native_target, wheel_matches
from suite.native_entrypoints import MAC_ALEMBIC
from suite.windows_bundle import (digest, checked_archive, extract, write_file,
                                 wheel_record, copy_monitor, SPOOLMAN_SHA, install_camera_component)

PYTHON_ARCHIVE='python-3.14.10-pbs-20261026-macos-x86_64.tar.gz'
PYTHON_SHA='2fd8becd48cf0ff5f0a15df3c0db7cae7aa708dcaacf901bd30d6cdd6229370b'
PYTHON_RUNTIMES={
    'x86_64': (PYTHON_ARCHIVE,PYTHON_SHA),
    'arm64': ('cpython-3.14.10+20261026-aarch64-apple-darwin-install_only.tar.gz',
              '30a18bcb9ab75e485b4bf4e5d783dde165571e7e42c56dff47a2d2c5345183a4'),
}
# Filled only from the reviewed local source build, not caller-supplied hashes.
ARM_CAMERA_SHA={'ffmpeg': '3118efbdf0375038c3d313e36718eadaa1edfad2b0ebf09078a9794a7fb1ffc7', 'ffprobe': 'e57a046c62de68e95417d16d058056aa0f4ffa41494e2ee88049305ebb1160f1'}
ARM_CAMERA_SOURCE_SHA='0aa2b1de2a5698b20a23e93d539a9a8e82ca0117496c5bdf05d198805f42bb3b'
ARM_CAMERA_COMMIT='946fcce07b6dcd0331c8cc609192aeff5e1924f8'
INTEL_CAMERA_SHA={'ffmpeg': '86341dd5c23b1a44d857496edcf05835c522df869c85f53be17a0a1aa6fee7ee', 'ffprobe': 'c24a1bf705db2c966b434e9345cb3b19c7b1b8c2871beb1407e7d54a8ef376fd'}
MAGICS={b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xca\xfe\xba\xbf',
        b'\xbe\xba\xfe\xca',b'\xbf\xba\xfe\xca'}


def mach_o_info(body, *, architecture='x86_64'):
    """Inspect the requested native slice, including its deployment target."""
    target = native_target('macos', architecture)
    if len(body)<32 or body[:4] not in MAGICS:raise ValueError('Ungültiger Mac-Binärkopf.')
    if body[:4] in (b'\xca\xfe\xba\xbe',b'\xca\xfe\xba\xbf',b'\xbe\xba\xfe\xca',b'\xbf\xba\xfe\xca'):
        endian='>' if body[0]==0xca else '<';wide=body[:4] in (b'\xca\xfe\xba\xbf',b'\xbf\xba\xfe\xca')
        count=struct.unpack_from(endian+'I',body,4)[0]
        if not 1<=count<=32:raise ValueError('Ungültige Mac-Architekturanzahl.')
        table_end=8+count*(32 if wide else 20)
        if table_end>len(body):raise ValueError('Unvollständige Mac-Architekturtabelle.')
        for i in range(count):
            at=8+i*(32 if wide else 20);cpu=struct.unpack_from(endian+'I',body,at)[0]
            offset,size=struct.unpack_from(endian+('QQ' if wide else 'II'),body,at+8)
            if offset<table_end or size<32 or offset+size>len(body):raise ValueError('Unvollständige Mac-Architektur.')
            if cpu==target.cpu:return mach_o_info(body[offset:offset+size],architecture=architecture)
        raise ValueError('Eine native Bibliothek enthält keinen Code für '+target.architecture+'.')
    endian='<' if body[:4]==b'\xcf\xfa\xed\xfe' else '>'
    if struct.unpack_from(endian+'I',body,4)[0]!=target.cpu:
        raise ValueError('Eine native Bibliothek passt nicht zu '+target.architecture+'.')
    count,total=struct.unpack_from(endian+'II',body,16);at=32
    if count>4096 or total>len(body)-32:raise ValueError('Ungültige Mac-Ladebefehle.')
    minimum=0;dependencies=[];rpaths=[]
    for _ in range(count):
        command,size=struct.unpack_from(endian+'II',body,at)
        if size<8 or at+size>len(body):raise ValueError('Ungültiger Mac-Ladebefehl.')
        if command in (0xc,0x80000018,0x8000001f,0x80000023,0x8000001c):
            offset=struct.unpack_from(endian+'I',body,at+8)[0]
            if not 12<=offset<size:raise ValueError('Ungültiger Mac-Bibliothekspfad.')
            text=body[at+offset:at+size].split(b'\0',1)[0].decode('utf-8')
            (rpaths if command==0x8000001c else dependencies).append(text)
        if command==0x24:minimum=max(minimum,struct.unpack_from(endian+'I',body,at+8)[0])
        if command==0x32:minimum=max(minimum,struct.unpack_from(endian+'I',body,at+12)[0])
        at+=size
    if minimum>15<<16:raise ValueError('Eine Bibliothek benötigt eine neuere macOS-Version als das Testziel.')
    return {'minimum_macos':[minimum>>16,(minimum>>8)&255,minimum&255],
            'dependencies':dependencies,'rpaths':rpaths,'architecture':target.architecture}


def mac_tag(tag, *, architecture='x86_64'):
    return wheel_matches(tag, native_target('macos', architecture))


def check_relocation(path, payload, info, *, architecture='x86_64'):
    native_target('macos', architecture)
    path,payload=Path(path),Path(payload)
    relative=path.relative_to(payload).parts
    executable=payload/'runtime'/relative[1]/'bin/python3.14' if relative[0]=='runtime' else path
    def expand(value):
        if value=='@loader_path':return path.parent
        if value.startswith('@loader_path/'):return path.parent/value[len('@loader_path/'):]
        if value=='@executable_path':return executable.parent
        if value.startswith('@executable_path/'):return executable.parent/value[len('@executable_path/'):]
        if value.startswith(('/usr/lib/','/System/Library/')):return Path(value)
        raise ValueError('Eine Bibliothek hat einen fremden Suchpfad: '+value)
    rpaths=list(info['rpaths'])
    if executable!=path:
        exe=mach_o_info(executable.read_bytes(),architecture=architecture)
        for value in exe['rpaths']:
            rpaths.append(value.replace('@loader_path','@executable_path'))
    roots=[expand(value) for value in rpaths]
    for dependency in info['dependencies']:
        if dependency.startswith(('/usr/lib/','/System/Library/')):continue
        if dependency.startswith('@rpath/'):
            candidates=[root/dependency[len('@rpath/'):] for root in roots]
        else:candidates=[expand(dependency)]
        if not any(p.is_file() and p.resolve().is_relative_to(payload.resolve()) for p in candidates):
            raise ValueError('Eine dynamische Bibliothek ist nicht vollständig enthalten: '+dependency)


def install_wheel(path,runtime, *, architecture='x86_64'):
    native_target('macos', architecture)
    with zipfile.ZipFile(path) as archive:
        metadata=wheel_record(archive,compatible_tag=lambda tag:mac_tag(tag,architecture=architecture))
        for info in archive.infolist():
            if info.is_dir():continue
            name=info.filename;parts=name.split('/');body=archive.read(info)
            if len(parts)>2 and parts[0].endswith('.data'):
                category=parts[1];tail='/'.join(parts[2:])
                if category in ('purelib','platlib'):name='lib/python3.14/site-packages/'+tail
                elif category=='scripts':name='bin/'+tail
                elif category=='headers':name='include/'+metadata['name']+'/'+tail
                elif category=='data':name='share/'+metadata['name']+'/'+tail
                else:raise ValueError('Unbekannter Wheel-Datenbereich.')
            else:name='lib/python3.14/site-packages/'+name
            if body[:4] in MAGICS:mach_o_info(body,architecture=architecture)
            write_file(runtime,name,body)
    return metadata


def python_runtime(archive,target, *, architecture='x86_64'):
    native_target('macos',architecture)
    if digest(archive)!=PYTHON_RUNTIMES[architecture][1]:raise ValueError('Die Python-Prüfsumme für das gewählte Ziel stimmt nicht.')
    with tempfile.TemporaryDirectory(dir=target.parent) as folder:
        with tarfile.open(archive) as incoming:incoming.extractall(folder,filter='data')
        source=Path(folder)/'python'
        for path in source.rglob('*'):
            if path.is_symlink() and (not path.resolve().is_relative_to(source.resolve()) or not path.resolve().is_file()):
                raise ValueError('Unerwartete Verknüpfung in der Python-Laufzeit.')
        # Materialize internal file links for reliable Archive Utility extraction.
        shutil.copytree(source,target,symlinks=False)


def build(inputs,source,destination, *, architecture='x86_64', camera_input=None):
    target=native_target('macos',architecture)
    if camera_input is None and architecture=='arm64' and set(ARM_CAMERA_SHA)!={'ffmpeg','ffprobe'}:
        raise ValueError('Der geprüfte ARM-Kamerabau fehlt noch.')
    python_archive,python_sha=PYTHON_RUNTIMES[architecture]
    if sys.platform!='darwin':raise ValueError('Die Mac-App wird auf einem Mac gebaut und signaturgeprüft.')
    inputs,source,destination=Path(inputs),Path(source),Path(destination)
    if destination.exists() or destination.is_symlink():raise FileExistsError('Der Paketordner existiert bereits.')
    provenance=json.loads((inputs/'wheel-provenance.json').read_text())
    closure=json.loads((inputs/'wheel-closure-proof.json').read_text())
    with tempfile.TemporaryDirectory(prefix='.mac-bundle-',dir=destination.parent) as temporary:
        stage=Path(temporary);app=stage/'Kobra Monitor Test.app';contents=app/'Contents'
        payload=contents/'Resources/payload';payload.mkdir(parents=True)
        version=copy_monitor(source,payload/'app/monitor');components={'python':{'version':'3.14.10','sha256':python_sha},'spoolman':{'version':'0.27.0','sha256':SPOOLMAN_SHA},'wheels':{}}
        for role in ('monitor','spoolman'):
            if not closure[role]['dependency_closure_verified']:raise ValueError('Die Abhängigkeiten sind nicht vollständig.')
            runtime=payload/'runtime'/role;runtime.parent.mkdir(exist_ok=True)
            python_runtime(inputs/python_archive,runtime,architecture=architecture)
            wheels=sorted((inputs/('wheels-'+role+'-macos')).glob('*.whl'))
            if len(wheels)!=closure[role]['packages']:raise ValueError('Eine Mac-Bibliothek fehlt.')
            installed=[]
            for wheel in wheels:
                proof=next((v for v in provenance if v['file']==wheel.relative_to(inputs).as_posix()),None)
                if proof is None or digest(wheel)!=proof['sha256']:raise ValueError('Die Wheel-Herkunft ist nicht belegt.')
                installed.append({**install_wheel(wheel,runtime,architecture=architecture),'sha256':proof['sha256'],'origin':proof})
            components['wheels'][role]=installed
            if role=='spoolman':
                write_file(runtime,'bin/alembic',MAC_ALEMBIC.encode('utf-8'))
                (runtime/'bin/alembic').chmod(0o755)
        with checked_archive(inputs/'spoolman-0.27.0.zip',SPOOLMAN_SHA) as archive:extract(archive,payload/'app/spoolman')
        licenses=payload/'licenses';licenses.mkdir()
        if camera_input is None:
            camera_proof = json.loads((inputs/'camera-build-proof.json').read_text())
            camera_hashes = INTEL_CAMERA_SHA if architecture == 'x86_64' else ARM_CAMERA_SHA
            if (camera_proof.get('source_commit') != ARM_CAMERA_COMMIT or
                    camera_proof.get('source_archive_sha256') != ARM_CAMERA_SOURCE_SHA or
                    not camera_proof.get('synthetic_jpeg_passed')):
                raise ValueError('Der festgelegte Kameraquell-/Funktionsnachweis fehlt.')
            if architecture == 'x86_64' and camera_proof.get('full_camera_fixture_test') != 'passed':
                raise ValueError('Der Intel-Kamera-Integrationstest fehlt.')
            if architecture == 'arm64' and not camera_proof.get('github_tag_signature_verified'):
                raise ValueError('Der ARM-Kameraquellnachweis fehlt.')
            camera_archive = inputs/'ffmpeg-9.0.2-source-github.tar.gz'
            if digest(camera_archive) != ARM_CAMERA_SOURCE_SHA:
                raise ValueError('Das Kameraquellarchiv wurde verändert.')
            camera_source = inputs/('FFmpeg-'+ARM_CAMERA_COMMIT)
            for role, sha in camera_hashes.items():
                binary = camera_source/role
                if digest(binary) != sha:
                    raise ValueError('Der Kamera-Binärbau wurde verändert.')
                write_file(payload, 'ffmpeg/bin/'+role, binary.read_bytes())
                (payload/'ffmpeg/bin'/role).chmod(0o755)
            with tarfile.open(camera_archive) as archive:
                prefix = 'FFmpeg-'+ARM_CAMERA_COMMIT+'/'
                for member in archive.getmembers():
                    relative = member.name.removeprefix(prefix)
                    if member.isfile() and '/' not in relative and relative.startswith('COPYING'):
                        write_file(licenses, 'ffmpeg/'+relative, archive.extractfile(member).read())
            write_file(licenses, 'ffmpeg/FFmpeg-original-source.tar.gz', camera_archive.read_bytes())
            write_file(licenses, 'ffmpeg/source-build.json', (inputs/'camera-build-proof.json').read_bytes())
            components['camera'] = {'version':'9.0.2-kobra-'+architecture,
                'source_commit':ARM_CAMERA_COMMIT, 'binary_sha256':camera_hashes,
                'source_archive_sha256':ARM_CAMERA_SOURCE_SHA}
        else:
            camera_platform = 'macos-arm64' if architecture == 'arm64' else 'macos-x64'
            components['camera'] = install_camera_component(camera_input, payload, platform=camera_platform)
        write_file(licenses, 'http-ece-1.2.1-MIT.txt',
                   (source/'licenses/http-ece-1.2.1-MIT.txt').read_bytes())
        if architecture == 'x86_64':
            for archive_name, label in [('cryptography-50.0.0.tar.gz','crypto-50.0.0'),
                    ('cryptography-50.0.2.tar.gz','crypto-50.0.2'), ('openssl-4.0.3.tar.gz','openssl-4.0.3')]:
                with tarfile.open(inputs/archive_name) as archive:
                    for member in archive.getmembers():
                        if member.isfile() and member.name.split('/')[-1].startswith(('LICENSE','COPYING','NOTICE')):
                            write_file(licenses, label+'/'+member.name, archive.extractfile(member).read())
            for name in ('crypto-build-proof.json','source-build-provenance.json'):
                write_file(licenses, name, (inputs/name).read_bytes())
        binaries={}
        clean_packaging_metadata(app)
        for path in payload.rglob('*'):
            if path.is_file():
                with path.open('rb') as stream:magic=stream.read(4)
                if magic in MAGICS:
                    info=mach_o_info(path.read_bytes(),architecture=architecture)
                    removed=[value for value in info['rpaths'] if not value.startswith(
                        ('@loader_path','@executable_path','/usr/lib/','/System/Library/'))]
                    # Some upstream wheels retain unused CI build-directory
                    # rpaths. Remove these only from our packaged copy, then
                    # require every dependency to resolve inside this payload.
                    for value in removed:
                        subprocess.run(['/usr/bin/install_name_tool','-delete_rpath',value,str(path)],
                                       check=True,capture_output=True)
                    if removed:
                        info=mach_o_info(path.read_bytes(),architecture=architecture);info['removed_build_rpaths']=removed
                    for dependency in info['dependencies']:
                        if not dependency.startswith(('/usr/lib/','/System/Library/','@loader_path/','@rpath/','@executable_path/')):
                            raise ValueError('Eine Bibliothek benötigt einen fremden Installationspfad: '+dependency)
                    check_relocation(path,payload,info,architecture=architecture)
                    binaries[path.relative_to(payload).as_posix()]=info
                    subprocess.run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',str(path)],check=True,capture_output=True)
        write_file(payload,'native-binary-audit.json',(json.dumps(binaries,indent=2)+'\n').encode())
        files={p.relative_to(payload).as_posix():digest(p) for p in sorted(payload.rglob('*')) if p.is_file()}
        import hashlib
        identity=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
        manifest={'format':'kobra-macos-test-bundle-v1','version':version,'platform':target.platform,'bundle_id':identity,
                  'macos_launcher_revision':2,
                  'files':files,'components':components,'offline_complete':True,'developer_id_signed':False,
                  'notarized':False,'physical_platform_acceptance_passed':False,'target_architecture':architecture}
        (payload/'native-bundle.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (contents/'MacOS').mkdir()
        subprocess.run(['/Library/Developer/CommandLineTools/usr/bin/clang','-arch',architecture,'-isysroot',
            '/Library/Developer/CommandLineTools/SDKs/MacOSX14.4.sdk','-mmacosx-version-min=13.0','-O2',
            '-x','objective-c','-fobjc-arc','-framework','Cocoa',
            str(source/'deploy/native/macos_launcher.c'),'-o',str(contents/'MacOS/KobraMonitorTest')],check=True,capture_output=True)
        plist={'CFBundleExecutable':'KobraMonitorTest','CFBundleIdentifier':'local.kobra-monitor.test',
               'CFBundleName':'Kobra Monitor Test','CFBundlePackageType':'APPL','CFBundleShortVersionString':version.split('-')[0],
               'CFBundleVersion':version.split('-')[0],'LSMinimumSystemVersion':'.'.join(map(str,max([(13,0,0)]+[tuple(info['minimum_macos']) for info in binaries.values()]))),'LSUIElement':True,
               'NSLocalNetworkUsageDescription':'Kobra Monitor verbindet sich mit deinen 3D-Druckern im Heimnetz, um Status, Temperaturen, Filamentdaten und Kamerabilder anzuzeigen.',
               'LSArchitecturePriority':[architecture],'NSHighResolutionCapable':True}
        (contents/'Info.plist').write_bytes(plistlib.dumps(plist))
        clean_packaging_metadata(app)
        subprocess.run(['/usr/bin/codesign','--force','--sign','-','--timestamp=none',str(app)],check=True,capture_output=True)
        subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True,capture_output=True)
        os.rename(app,destination)
    return {'version':version,'platform':target.platform,'bundle_id':identity,'files':len(files),'native_modules':len(binaries),
            'ad_hoc_signature_verified':True,'developer_id_signed':False,'notarized':False,'offline_complete':True}
