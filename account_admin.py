# SPDX-License-Identifier: GPL-3.0-only
"""Local interactive recovery; stop the monitor before using this tool."""
import argparse
import getpass
import os
from pathlib import Path
from accounts import write_account

def main():
    parser=argparse.ArgumentParser(description='Lokales Kobra-Monitor-Konto wiederherstellen')
    parser.add_argument('--data-dir',default=os.environ.get('KOBRA_DATA_DIR',str(Path(__file__).parent/'.state')))
    args=parser.parse_args()
    print('Bitte den Monitor vorher stoppen. Druckdaten und Druckereinrichtung bleiben erhalten.')
    if input('Ist der Monitor gestoppt? Zum Fortfahren JA eingeben: ').strip()!='JA':
        return
    name=input('Neuer Benutzername: ')
    secret=getpass.getpass('Neues Passwort (mindestens 15 Zeichen): ')
    if secret!=getpass.getpass('Passwort wiederholen: '):
        parser.exit(1,'Die Passwörter stimmen nicht überein. Nichts geändert.\n')
    try:
        write_account(args.data_dir,name,secret)
    except ValueError as exc:
        parser.exit(1,str(exc)+' Nichts geändert.\n')
    print('Konto gespeichert. Starte den Monitor wieder und melde dich im Browser an.')

if __name__=='__main__':main()
