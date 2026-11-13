# SPDX-License-Identifier: GPL-3.0-only
"""Native Windows test entry: GUI messages, owned local worker and explicit stop."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import re
import subprocess
import sys
import time

from suite.desktop import InstallationLock, controller_request, supervise
from suite.native_upgrade import choose_profile
from suite.native_targets import native_target, runtime_architecture

CPP_DOWNLOAD = 'https://aka.ms/vc14/vc_redist.x64.exe'


def windows_target():
    return native_target('windows', runtime_architecture())


def cpp_runtime_download():
    suffix = {'x86_64': 'x64', 'arm64': 'arm64'}[windows_target().architecture]
    return 'https://aka.ms/vc14/vc_redist.' + suffix + '.exe'


def microsoft_signature(path):
    """Trust the original Windows publisher, never just a downloaded filename."""
    import base64
    literal="'"+str(path).replace("'","''")+"'"
    script='$s=Get-AuthenticodeSignature -LiteralPath '+literal+';'
    script+="@{status=$s.Status.ToString();subject=$s.SignerCertificate.Subject}|ConvertTo-Json -Compress"
    executable=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result=subprocess.run([str(executable),'-NoProfile','-NonInteractive','-EncodedCommand',
        base64.b64encode(script.encode('utf-16le')).decode()],capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
    if result.returncode:raise ValueError('Die Microsoft-Signatur konnte nicht geprüft werden.')
    state=json.loads(result.stdout.decode('utf-8-sig'))
    if state.get('status')!='Valid' or not re.search(r'(^|,\s*)CN=Microsoft Corporation(,|$)',state.get('subject') or ''):
        raise ValueError('Der Download hat keine gültige Microsoft-Herausgebersignatur.')


def ensure_runtime(bundle, data):
    """No redistribution of Microsoft binaries; owner downloads from Microsoft."""
    result=subprocess.run([str(bundle/'runtime/spoolman/python.exe'),'-X','utf8','-c',
        'import greenlet; from sqlalchemy.ext.asyncio import create_async_engine'],
        cwd=bundle/'app/spoolman',capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=20)
    if result.returncode==0:return True
    logs=data.parent/'Startprotokolle';logs.mkdir(parents=True,exist_ok=True)
    (logs/'laufzeitpruefung.log').write_bytes(result.stdout+result.stderr)
    if not message('Eine benötigte Windows-C++-Bibliothek kann nicht geladen werden.\n\n'
        'Soll das passende originale Microsoft Visual C++-Installationsprogramm jetzt direkt von Microsoft '
        'heruntergeladen und geöffnet werden? Internet ist einmalig erforderlich; Microsoft zeigt '
        'seine Lizenzbedingungen und Windows kann Administratorrechte anfordern. '
        'Es wird kein automatischer Neustart ausgeführt.',question=True):return False
    import urllib.request
    import tempfile
    directory=Path(tempfile.mkdtemp(prefix='Kobra-Microsoft-Runtime-'))
    download = cpp_runtime_download()
    target=directory/download.rsplit('/', 1)[1]
    with urllib.request.urlopen(download,timeout=30) as response, target.open('xb') as stream:
        if not response.geturl().startswith('https://'):
            raise ValueError('Der Microsoft-Download verwendet keine sichere Verbindung.')
        total=0;deadline=time.monotonic()+90
        while block:=response.read(1024*1024):
            total+=len(block)
            if total>40*1024*1024 or time.monotonic()>deadline:
                raise ValueError('Der Microsoft-Download überschreitet die erwarteten Grenzen.')
            stream.write(block)
    microsoft_signature(target)
    os.startfile(str(target),'open',arguments='/install /norestart')
    message('Bitte die originale Microsoft-Installation abschließen und anschließend '
            '„Kobra Monitor Test“ auf dem Desktop erneut öffnen.\n\n'
            'Die Monitor-Testinstallation ist bereits eingerichtet; persönliche Daten bleiben erhalten.')
    return False


def message(text, *, question=False):
    if os.name != 'nt':
        raise RuntimeError('Dieses Testpaket benötigt ein passendes Windows-x64- oder Windows-ARM64-System.')
    import ctypes
    flags = 0x24 if question else 0x40  # YESNO/question or OK/info.
    function=ctypes.windll.user32.MessageBoxW
    function.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint]
    function.restype=ctypes.c_int
    return function(None, text, 'Kobra Monitor – Windows-Testpaket', flags) == 6


def load_manifest(bundle, *, verify=False):
    from suite.native_manifest import load_manifest as load
    return load(bundle, format='kobra-windows-test-bundle-v1',
                platform=windows_target().platform, verify=verify)


def create_shortcut(bundle, data):
    # Windows resolves the real Desktop location, including OneDrive redirection.
    # No execution-policy changes, global Python/PATH edits or administrator tasks.
    import base64
    def ps(value): return "'" + str(value).replace("'", "''") + "'"
    executable = bundle / 'runtime/monitor/pythonw.exe'
    arguments = subprocess.list2cmdline(['-X','utf8',str(bundle / 'app/monitor/desktop_entry.py'),
        '--bundle', str(bundle), '--data', str(data), '--mode', 'start'])
    stop_arguments = subprocess.list2cmdline(['-X','utf8',str(bundle / 'app/monitor/desktop_entry.py'),
        '--bundle', str(bundle), '--data', str(data), '--mode', 'stop'])
    script = "$w=New-Object -ComObject WScript.Shell; $d=$w.SpecialFolders.Item('Desktop');"
    for name, args in [('Kobra Monitor Laufzeit-Abnahme.lnk', arguments), ('Kobra Monitor Laufzeit-Abnahme beenden.lnk', stop_arguments)]:
        script += "$s=$w.CreateShortcut((Join-Path $d " + ps(name) + "));"
        script += '$s.TargetPath=' + ps(executable) + ';$s.Arguments=' + ps(args) + ';'
        script += '$s.WorkingDirectory=' + ps(bundle) + ';$s.Save();'
    system_root = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    powershell = system_root / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-EncodedCommand',
        base64.b64encode(script.encode('utf-16le')).decode()], capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
    if result.returncode:
        raise RuntimeError('Die Desktop-Verknüpfung konnte nicht angelegt werden. Der Starter im Programmordner bleibt nutzbar.')


def install(bundle, data, manifest):
    local = Path(os.environ['LOCALAPPDATA']) / 'KobraMonitor-Test'
    program = local / ('Programm-' + manifest['version'])
    if not message('Kobra Monitor als getrennte Testinstallation auf diesem PC einrichten?\n\n'
                   'Python, Spoolman und FFmpeg sind enthalten. Die Microsoft-C++-Laufzeit wird separat installiert. Konto und Passwort legst du selbst im Browser an.\n\n'
                   'Programm: ' + str(program) + '\nDaten: ' + str(data) +
                   '\n\nEs werden zwei Desktop-Verknüpfungen für Start und Beenden angelegt.', question=True):
        return None
    local.mkdir(parents=True, exist_ok=True)
    if program.exists():
        existing = load_manifest(program)
        if existing.get('bundle_id') != manifest.get('bundle_id'):
            raise ValueError('Unter dieser Versionskennung ist bereits ein anderes Testpaket installiert.')
    else:
        stage = local / ('.installation-' + os.urandom(8).hex())
        try:
            shutil.copytree(bundle, stage)
            load_manifest(stage, verify=True)
            os.rename(stage, program)
        finally:
            if stage.exists(): shutil.rmtree(stage)
    try:
        create_shortcut(program, data)
    except RuntimeError as error:
        message(str(error))
    return program


def start(bundle, data, manifest):
    # First launch is a short launcher process. The background worker owns the
    # installation lock and children. Repeated clicks reopen the existing UI.
    try:
        current = controller_request(data)
    except (OSError, ValueError, KeyError):
        current = None
    if current is not None:
        import webbrowser
        webbrowser.open(current['monitor_url'])
        return
    if not ensure_runtime(bundle, data):return
    log_dir = data.parent / 'Startprotokolle'
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / 'starter.log').open('ab') as log:
        subprocess.Popen([str(bundle / 'runtime/monitor/pythonw.exe'),
            '-X','utf8',str(bundle / 'app/monitor/desktop_entry.py'), '--bundle', str(bundle), '--data', str(data),
            '--mode', 'worker'], cwd=bundle, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--data')
    parser.add_argument('--mode', choices=['install', 'start', 'worker', 'stop'], default='start')
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('Native Windows test package only.')
    bundle = Path(args.bundle).resolve()
    data = Path(args.data) if args.data else Path(os.environ['LOCALAPPDATA']) / 'KobraMonitor-Test/Daten-Setup-Abnahme-alpha.6'
    try:
        manifest = load_manifest(bundle, verify=args.mode in ('install', 'start', 'worker'))
        if args.mode != 'worker':
            data = choose_profile(data, manifest['version'], stopping=args.mode == 'stop',
                                  confirm=lambda text: message(text, question=True))
            if data is None:return
        if args.mode == 'install':
            result = install(bundle, data, manifest)
            if result is not None: start(result, data, manifest)
        elif args.mode == 'start':
            start(bundle, data, manifest)
        elif args.mode == 'stop':
            if message('Kobra Monitor und den lokalen Spoolman beenden?\n\n'
                       'Die Aufzeichnung endet. Ein laufender Druck wird dadurch nicht angehalten.', question=True):
                try: controller_request(data, 'stop')
                except (OSError, ValueError, KeyError): message('Diese lokale Testinstallation läuft derzeit nicht.')
        else:
            lock = InstallationLock(data / 'desktop.lock')
            if not lock.acquire():
                for _ in range(30):
                    try:
                        import webbrowser
                        webbrowser.open(controller_request(data)['monitor_url'])
                        return
                    except (OSError, ValueError, KeyError): time.sleep(.3)
                raise RuntimeError('Die lokale Anwendung wird bereits gestartet. Bitte kurz warten und erneut öffnen.')
            try: supervise(bundle, data, manifest['version'])
            finally: lock.close()
    except Exception as error:
        # No credentials/environment dump. Detailed child logs stay in local data.
        message('Kobra Monitor konnte den Vorgang nicht abschließen.\n\n' + str(error) +
                '\n\nLokale Protokolle: ' + str(data / 'logs'))


if __name__ == '__main__':
    main()
