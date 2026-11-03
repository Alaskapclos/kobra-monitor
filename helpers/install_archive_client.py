#!/usr/bin/env python3
"""Install the private archive collector as a macOS login service.
SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys


def install(config, destination=None, agents=None, python=None):
    if sys.platform != 'darwin': raise ValueError('Der Anmeldedienst unterstützt zunächst macOS.')
    from archive_client import read_config
    read_config(config)
    Path(config).chmod(0o600)
    source = Path(__file__).resolve().parent
    destination = destination or Path.home()/'Library/Application Support/Kobra Monitor Archive'
    agents = agents or Path.home()/'Library/LaunchAgents'
    destination.mkdir(parents=True,exist_ok=True,mode=0o700);destination.chmod(0o700)
    (destination/'helpers').mkdir(exist_ok=True,mode=0o700)
    for origin,target in [(source/'archive_client.py',destination/'helpers/archive_client.py'),(source.parent/'file_archive.py',destination/'file_archive.py'),(Path(config),destination/'archive-client.json')]:
        if origin.resolve()!=target.resolve():shutil.copyfile(origin,target)
        target.chmod(0o600)
    # Avoid a stale temporary virtual environment; caller may select a stable interpreter.
    interpreter = str(Path(python or sys.executable).absolute())
    agents.mkdir(parents=True,exist_ok=True)
    label = 'local.kobra-monitor.archive'
    service = agents/(label+'.plist')
    body = {'Label':label,'ProgramArguments':[interpreter,str(destination/'helpers/archive_client.py'),'--config',str(destination/'archive-client.json'),'--queue',str(destination/'queue')],
            'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':30,'ProcessType':'Background','Umask':0o077}
    service.write_bytes(plistlib.dumps(body));service.chmod(0o600)
    domain='gui/'+str(os.getuid())
    subprocess.run(['launchctl','bootout',domain+'/'+label],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    subprocess.run(['launchctl','bootstrap',domain,str(service)],check=True)
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Privaten Kobra-Archivhelfer für die macOS-Anmeldung einrichten.')
    parser.add_argument('config',type=Path);parser.add_argument('--python',type=Path)
    args=parser.parse_args();install(args.config,python=args.python)
    print('Archivhelfer eingerichtet. Bestehende Cache-Dateien werden übersprungen. Status im Monitor unter Druckaufträge prüfen.')
