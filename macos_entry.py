# SPDX-License-Identifier: GPL-3.0-only
"""Per-user Mac test application. No administrator or printer actions."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import threading
import uuid

# The bundled interpreter runs in isolated mode; only this app supplies code.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from suite.desktop import InstallationLock, controller_request, supervise
from suite.native_manifest import load_manifest as check_manifest
from suite.native_targets import native_target, runtime_architecture
from suite.native_upgrade import choose_profile


def load_manifest(bundle, *, verify=False):
    return check_manifest(bundle,format='kobra-macos-test-bundle-v1',
                          platform=native_target('macos',runtime_architecture()).platform,verify=verify)


def dialog(text, *, choices=('OK',)):
    # Text is passed as argv, never interpolated into AppleScript source.
    buttons='{'+','.join('"'+v+'"' for v in choices)+'}'
    script='on run argv\n'
    script+='try\nset r to display dialog (item 1 of argv) with title "Kobra Monitor – Mac-Test" '
    script+='buttons '+buttons+' default button "'+choices[-1]+'"\nreturn button returned of r\n'
    script+='on error number -128\nreturn "Abbrechen"\nend try\nend run'
    result=subprocess.run(['/usr/bin/osascript','-e',script,'--',text],capture_output=True,text=True,timeout=3600)
    if result.returncode:raise RuntimeError('Der Mac-Dialog konnte nicht geöffnet werden.')
    return result.stdout.strip()


def install_application(app, destination, manifest):
    """Only create a new user app; never replace a foreign or other version."""
    app,destination=Path(app).resolve(),Path(destination)
    if destination.is_symlink():raise ValueError('Eine bestehende Programmverknüpfung wird nicht ersetzt.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        old=load_manifest(destination/'Contents/Resources/payload',verify=True)
        if old['bundle_id']!=manifest['bundle_id']:
            raise ValueError('Ein anderes Testpaket liegt bereits im Ziel. Eine geprüfte Versionsübernahme folgt separat.')
        return destination
    stage=destination.with_name('.kobra-test-install-'+uuid.uuid4().hex+'.app')
    try:
        shutil.copytree(app,stage,symlinks=False)
        from suite.macos_metadata import clean_packaging_metadata
        clean_packaging_metadata(stage)
        copied=load_manifest(stage/'Contents/Resources/payload',verify=True)
        if copied['bundle_id']!=manifest['bundle_id']:raise ValueError('Die Programmkopie stimmt nicht überein.')
        os.rename(stage,destination)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return destination


def start(bundle,data, *, no_browser=False):
    log=data.parent/'Startprotokolle';log.mkdir(parents=True,exist_ok=True)
    command=[str(bundle/'runtime/monitor/bin/python3.14'),'-I','-B','-X','utf8',
             str(bundle/'app/monitor/macos_entry.py'),'--bundle',str(bundle),'--data',str(data),'--mode','worker']
    if no_browser:command.append('--no-browser')
    with (log/'starter.log').open('ab') as stream:
        subprocess.Popen(command,cwd=bundle,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,
                         start_new_session=True)


def run_worker(bundle, data, manifest, *, no_browser=False):
    lock=InstallationLock(data/'desktop.lock')
    if not lock.acquire():return
    try:supervise(bundle,data,manifest['version'],open_browser=not no_browser)
    finally:lock.close()


def watch_gui_host():
    """Exit if the owning native GUI disappears; child pipe guards stop services."""
    parent=os.getppid()
    def watch():
        while os.getppid()==parent:time.sleep(.5)
        os._exit(1)
    threading.Thread(target=watch,daemon=True,name='kobra-gui-owner').start()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',required=True);parser.add_argument('--data')
    parser.add_argument('--mode',choices=['launch','start','worker','stop','verify'],default='launch')
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--foreground',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if sys.platform!='darwin':raise SystemExit('Dieses Testpaket benötigt macOS auf Intel oder Apple Silicon.')
    bundle=Path(args.bundle).resolve()
    data=Path(args.data).expanduser().absolute() if args.data else Path.home()/'Library/Application Support/KobraMonitor-Test/Daten'
    try:
        manifest=load_manifest(bundle,verify=True)
        if args.mode=='verify':
            print(json.dumps({'version':manifest['version'],'files':len(manifest['files']),'integrity_verified':True}));return
        if args.mode=='worker':
            run_worker(bundle,data,manifest,no_browser=args.no_browser)
            return
        data=choose_profile(data,manifest['version'],stopping=args.mode=='stop',
            confirm=lambda text:dialog(text,choices=('Abbrechen','Prüfen & übernehmen'))=='Prüfen & übernehmen')
        if data is None:return
        try:current=controller_request(data)
        except (OSError,ValueError,KeyError):current=None
        if args.mode=='stop':
            if current is not None:controller_request(data,'stop')
            return
        if current is not None:
            choice='Öffnen' if args.mode=='start' else dialog(
                'Die lokale Testinstallation läuft. Beim Beenden endet ihre Aufzeichnung; '
                'ein Drucker druckt unabhängig weiter.',choices=('Abbrechen','Beenden','Öffnen'))
            if choice=='Beenden':controller_request(data,'stop')
            elif choice=='Öffnen' and not args.no_browser:
                import webbrowser
                webbrowser.open(current['monitor_url'])
            return
        if args.mode=='launch':
            app=bundle.parents[2]
            if app.suffix!='.app' or bundle!=app/'Contents/Resources/payload':
                raise ValueError('Die Mac-Anwendungsstruktur ist ungültig.')
            destination=Path.home()/'Applications'/('Kobra Monitor Test '+manifest['version']+'.app')
            if app!=destination:
                choice=dialog('Kobra Monitor als getrennte Testanwendung installieren?\n\n'
                    'Programm: '+str(destination)+'\nDaten: '+str(data)+'\n\n'
                    'Python, Spoolman und Kamera-Laufzeit sind enthalten. Dein NAS-Monitor bleibt unverändert. '
                    'Konto und Passwort legst du selbst im Browser an. '
                    'Erneutes Öffnen der App bietet Öffnen oder Beenden.',choices=('Abbrechen','Installieren'))
                if choice!='Installieren':return
                installed=install_application(app,destination,manifest)
                if args.foreground:
                    # Let Launch Services register the installed app as the host.
                    command=['/usr/bin/open','-n',str(installed),'--args','--data',str(data)]
                    if args.no_browser:command.append('--no-browser')
                    subprocess.run(command,check=True)
                    return
                bundle=installed/'Contents/Resources/payload'
        if args.foreground:
            watch_gui_host()
            log=data.parent/'Startprotokolle';log.mkdir(parents=True,exist_ok=True)
            with (log/'starter.log').open('a',buffering=1) as stream, \
                    contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
                run_worker(bundle,data,manifest,no_browser=args.no_browser)
        else:start(bundle,data,no_browser=args.no_browser)
    except Exception as error:
        if args.mode in ('worker','verify'):
            print('Mac-Testanwendung: '+str(error),file=sys.stderr);raise SystemExit(1)
        dialog('Kobra Monitor konnte den Vorgang nicht abschließen.\n\n'+str(error)+
               '\n\nLokale Protokolle: '+str(data/'logs'))


if __name__=='__main__':main()
