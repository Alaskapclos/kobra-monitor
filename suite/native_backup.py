# SPDX-License-Identifier: GPL-3.0-only
"""Local native paired backup worker. No HTTP, printer or deployment operations."""
import argparse
import json
from pathlib import Path
import time
from suite.snapshots import create_snapshot, verify_snapshot


def run_due(data, version, *, clock=time.time, interval=86400, state=None):
    data=Path(data)
    if not (data/'monitor/config.json').is_file() or not (data/'spoolman/spoolman.db').is_file():
        return None
    profile=json.loads((data/'desktop.json').read_text())
    settings=json.loads((data/'monitor/spoolman.json').read_text())
    if settings.get('url') != profile.get('backend_url') or not profile.get('backend_url'):
        raise ValueError('Die lokale Komplettsicherung kann keinen externen Spoolman-Bestand sichern.')
    now=clock()
    previous=(state or {}).get('last_verified')
    if previous is not None and 0 <= now-previous < interval:
        return None
    destination=data/'backups'
    times=[]
    if destination.exists():
        for snapshot in destination.glob('kobra-suite-*'):
            try:times.append(verify_snapshot(snapshot)['created_at'])
            except (OSError,ValueError,KeyError):continue
    if times and 0 <= now-max(times) < interval:
        if state is not None:state['last_verified']=max(times)
        return None
    # The generic backup's historical deployment member is called compose.yaml;
    # here it records the native profile JSON, explicitly identified by format.
    result=create_snapshot(data/'monitor',data/'spoolman/spoolman.db',destination,
        monitor_image='kobra-monitor-native:'+version,spoolman_image='spoolman-native:0.27.0',
        deployment=data/'desktop.json',clock=clock)
    if state is not None:state['last_verified']=now
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',required=True);parser.add_argument('--version',required=True)
    args=parser.parse_args();state={}
    while True:
        try:
            result=run_due(args.data,args.version,state=state)
            print(json.dumps({'backup':'verified' if result else 'waiting_or_not_due'}),flush=True)
        except Exception:
            print(json.dumps({'backup':'failed','message':'Ältere Sicherungen bleiben erhalten.'}),flush=True)
        time.sleep(60)


if __name__=='__main__':main()
