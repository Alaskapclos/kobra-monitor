# Installation und dauerhafter Betrieb

## Wahl des Geräts

- **Rechner:** einfacher Start mit Browser; ideal zum Ausprobieren. Keine
  Aufzeichnung während Ausschalten oder Ruhezustand.
- **Linux-Server / Mini-PC:** geeignet für dauerhaften Betrieb; Docker Compose
  mit `restart: unless-stopped` oder eine selbst verwaltete Python-Installation.
- **NAS:** vorgesehen für Geräte mit Docker/Compose und erreichbarem Druckernetz.
  Keine Zusage für NAS ohne Container-Unterstützung oder bestimmte Modelle.

macOS und ein amd64-Container auf UGREEN DXP4800GT wurden mit echten Druckern
geprüft. Automatisierte Prüfungen laufen auf Windows, Linux und macOS; das ersetzt keinen Hardwaretest auf diesen Plattformen.
ARM64 und weitere NAS-Modelle sind noch nicht praktisch geprüft.

## Docker / Compose

Docker und das Compose-Plugin vorher installieren. Auf älteren NAS können
Portbindung, Benutzerrechte und Healthchecks abweichen; vorab prüfen.

```sh
docker compose up -d --build
docker compose ps
docker compose exec monitor python monitor.py --show-setup-link
```

Der Container läuft als Benutzer 10001 ohne zusätzliche Linux-Capabilities.
Die Anwendung ist schreibgeschützt; nur `/data` und der temporäre Ordner sind
beschreibbar. Das benannte Volume wird beim normalen Update wiederverwendet.
Die Standard-Portbindung ist ausschließlich am Host. Ältere Docker-Versionen
vor 28 hatten Einschränkungen bei der Isolation von auf localhost veröffentlichten
Ports; Docker aktuell halten und den Zugriff prüfen.

Für den Browserzugriff von einem anderen Gerät siehe [Fernzugriff](REMOTE_ACCESS.md).
Bei einer NAS-GUI diese Compose-Datei als Projekt importieren und ein dauerhaftes
Datenvolume verwenden. Wird stattdessen ein vorhandener Ordner eingebunden,
muss Benutzer 10001 darin schreiben können. Keine pauschalen 777-Rechte vergeben.

## Desktop / native Python-Installation

Die Starter erstellen `.venv` und installieren die Versionen aus
`requirements-lock.txt`. Ein Hash der Lockdatei sorgt beim nächsten Start für
eine erneute Installation, wenn sich die Vorgaben geändert haben. Das verändert
keine globale Python-Installation.

Alternativ ohne Starter:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python monitor.py --open
```

`--open` öffnet auf dem Host den Browser. Beim ersten Start führt der geschützte
Einrichtungslink direkt zu „Dein Benutzerkonto“. Danach erscheint die normale
Anmeldung mit Benutzername und Passwort. Für die erste Einrichtung eines NAS:
`python monitor.py --show-setup-link`; im ausgegebenen Link `127.0.0.1` durch
die private NAS-Adresse ersetzen und den Link privat im Browser öffnen.
Der Link wird nach dem Anlegen des Kontos nicht mehr zur Anmeldung akzeptiert.
Unter Windows `.venv\Scripts\python.exe` verwenden.

## Einstellungen

- `--data-dir` / `KOBRA_DATA_DIR`: dauerhafter Datenordner, Standard `.state`.
- `--listen` / `KOBRA_LISTEN`: Bindeadresse, Standard `127.0.0.1`.
- `--port`: Standard 7125.
- `--ip`: ausdrücklich vorgegebene Druckeradresse, wiederholbar; alternativ
  `KOBRA_PRINTER_IPS` mit komma-getrennten Adressen. Diese Vorgaben haben beim
  Start Vorrang vor der im Browser gespeicherten Zuordnung.
- `KOBRA_ACCESS_TOKEN`: optionaler Schlüssel für die einmalige Ersteinrichtung
  mit mindestens 24 Zeichen. Er ist nach angelegtem Konto kein Anmeldeweg mehr.

Die Browser-Einrichtung empfiehlt sich für normale Installationen. Es gibt
keine fremden Druckeradressen als Standard und keinen automatischen Netzwerkscan.

## Sicherung und Update

Für den täglichen Betrieb empfiehlt sich der getrennte [Sicherungsdienst](BACKUPS.md), der ohne Unterbrechung konsistente Sicherungen erstellt. Spoolman benötigt eine eigene Sicherung.

Für eine manuelle Dateikopie sichere den vollständigen Datenordner bei gestopptem Monitor. Er enthält die
SQLite-Datenbanken, Druckerzuordnung, `account.json` mit dem Passwort-Prüfwert
und den geheimen Einrichtungsschlüssel. Für eine
Sicherung während des Betriebs ist die SQLite-Backup-API zu verwenden; eine
alleinige Kopie von `history.sqlite3` bei laufendem WAL-Betrieb kann unvollständig sein.

Update: Monitor stoppen, Quellcode ersetzen, Datenordner erhalten, Starter erneut
öffnen. Für Docker: Quellcode aktualisieren und `docker compose up -d --build`.
**Kein `down -v`**, wenn die Historie erhalten bleiben soll.

## Benutzerkonto

Die Installation hat ein lokales Besitzerkonto. Benutzername und Passwort legst
du im Browser selbst fest. Der Benutzername braucht 3–64 Zeichen; das Passwort
15–128 Zeichen. Ein langer Satz oder ein Passwortmanager erleichtert die Eingabe.
Es gibt keine vorgegebenen Standardpasswörter und kein Cloud-Konto.

Nach einem Update einer alten Code-Installation: einmal mit dem bisherigen
Code unter „Bestehende Installation … umstellen“ verbinden. Dann das Konto
anlegen. Der alte Code ist danach gesperrt. Druckeradressen und Historie
bleiben erhalten. Andere Geräte nutzen denselben Benutzernamen und dasselbe
Passwort. Mehrere getrennte Benutzer/Rollen sind noch nicht vorgesehen.

Über **Konto** kannst du Benutzername und Passwort ändern. Dafür ist das bisherige
Passwort nötig. Alle anderen Browser werden abgemeldet; **Abmelden** beendet
nur die Sitzung dieses Browsers. Nach zwölf Stunden oder einem Dienstneustart
ist eine neue Anmeldung erforderlich.

### Passwort vergessen

Mit lokalem Zugriff auf Rechner/NAS kannst du das Konto wiederherstellen.
Zuerst den Monitor stoppen, das Datenvolume behalten. Native Installation:

```sh
.venv/bin/python account_admin.py --data-dir .state
```

Bei Docker Compose aus dem Projektordner:

```sh
docker compose stop monitor
docker compose run --rm --no-deps -it monitor python account_admin.py --data-dir /data
docker compose up -d monitor
```

Das Werkzeug fragt Benutzername und Passwort interaktiv ab; die Passworteingabe
ist verdeckt. Die übrigen Daten bleiben erhalten. Nur auf dem eigenen Host
ausführen. Keine Passwörter in Befehlsargumente, Umgebungsvariablen oder Logs
schreiben. Auf UGOS ohne Kommandozeilen-Zugang alternativ die geprüfte
vollständige Datensicherung zurückspielen; dadurch gilt das Konto des
Sicherungszeitpunkts. Ein komfortabler UGOS-Wiederherstellungsdialog steht aus.

Temporäre Druckerzertifikate liegen außerhalb des Datenordners und werden beim
geordneten Beenden entfernt. Nach einem harten Absturz kann temporäres Material
bis zur Betriebssystembereinigung bestehen bleiben.
