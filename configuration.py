# SPDX-License-Identifier: GPL-3.0-only
"""Local installation configuration; no printer commands."""
import ipaddress
import json
import os
from pathlib import Path
import tempfile

NETWORKS=tuple(ipaddress.ip_network(v) for v in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))

def printer_ips(values):
    if not isinstance(values,list) or not 1<=len(values)<=16:
        raise ValueError('Trage mindestens eine Druckeradresse ein (höchstens 16).')
    result=[]
    for raw in values:
        try:address=ipaddress.ip_address(str(raw).strip())
        except ValueError:raise ValueError('Bitte gültige lokale IPv4-Adressen angeben.') from None
        if address.version!=4 or not any(address in network for network in NETWORKS):
            raise ValueError('Diese Adresse gehört nicht zu einem lokalen Heimnetz. Bitte die IP-Adresse aus den Netzwerkeinstellungen des Druckers verwenden.')
        if str(address) not in result:result.append(str(address))
    return result

def load_config(directory):
    file=Path(directory)/'config.json'
    if not file.exists():return []
    try:return printer_ips(json.loads(file.read_text())['printer_ips'])
    except (ValueError,KeyError,TypeError):raise ValueError('Die lokale Konfiguration ist ungültig. config.json prüfen.') from None

def save_config(directory,values):
    values=printer_ips(values);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,name=tempfile.mkstemp(prefix='.config-',dir=directory)
    try:
        with os.fdopen(fd,'w') as out:
            json.dump({'printer_ips':values},out,indent=2);out.write('\n')
        os.replace(name,directory/'config.json')
    finally:Path(name).unlink(missing_ok=True)
