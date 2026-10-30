# Installation und dauerhafter Betrieb

## Wahl des Geräts

- **Rechner:** einfacher Start mit Browser; ideal zum Ausprobieren. Keine
  Aufzeichnung während Ausschalten oder Ruhezustand.
- **Linux-Server / Mini-PC:** geeignet für dauerhaften Betrieb; Docker Compose
  mit `restart: unless-stopped` oder eine selbst verwaltete Python-Installation.
- **NAS:** vorgesehen für Geräte mit Docker/Compose und erreichbarem Druckernetz.
  Keine Zusage für NAS ohne Container-Unterstützung oder bestimmte Modelle.

macOS wurde am echten Drucker getestet. Windows und Linux sind vorbereitete
Installationswege, bis ihre CI- und Hardwaretests vorliegen. Container auf
amd64/arm64 sind durch die Basis vorbereitet, aber noch nicht praktisch gebaut.

## Docker / Compose

Docker und das Compose-Plugin vorher installieren. Auf älteren NAS können
Portbindung, Benutzerrechte und Healthchecks abweichen; vorab prüfen.

```sh
docker compose up -d --build
docker compose ps
docker compose exec monitor python monitor.py --show-access-code
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

`--open` öffnet auf dem Host einen Browser mit der automatischen Anmeldung.
Für andere Browser: `.venv/bin/python monitor.py --show-access-code`.
Unter Windows `.venv\Scripts\python.exe` verwenden.

## Einstellungen

- `--data-dir` / `KOBRA_DATA_DIR`: dauerhafter Datenordner, Standard `.state`.
- `--listen` / `KOBRA_LISTEN`: Bindeadresse, Standard `127.0.0.1`.
- `--port`: Standard 7125.
- `--ip`: ausdrücklich vorgegebene Druckeradresse, wiederholbar; alternativ
  `KOBRA_PRINTER_IPS` mit komma-getrennten Adressen. Diese Vorgaben haben beim
  Start Vorrang vor der im Browser gespeicherten Zuordnung.
- `KOBRA_ACCESS_TOKEN`: optional selbst vorgegebener Zugangscode mit mindestens
  24 Zeichen. Standard ist der automatisch erzeugte Code in `access-token`.

Die Browser-Einrichtung empfiehlt sich für normale Installationen. Es gibt
keine fremden Druckeradressen als Standard und keinen automatischen Netzwerkscan.

## Sicherung und Update

Sichere den vollständigen Datenordner bei gestopptem Monitor. Er enthält die
SQLite-Datenbanken, Druckerzuordnung und den geheimen Zugangscode. Für eine
Sicherung während des Betriebs ist die SQLite-Backup-API zu verwenden; eine
alleinige Kopie von `history.sqlite3` bei laufendem WAL-Betrieb kann unvollständig sein.

Update: Monitor stoppen, Quellcode ersetzen, Datenordner erhalten, Starter erneut
öffnen. Für Docker: Quellcode aktualisieren und `docker compose up -d --build`.
**Kein `down -v`**, wenn die Historie erhalten bleiben soll.

Zugangscode zurücksetzen: Dienst stoppen, `access-token` im Datenordner nach
Sicherung entfernen und neu starten. Bei gesetztem `KOBRA_ACCESS_TOKEN` muss
stattdessen dieser Wert geändert werden. Alle Browsersitzungen sind nach einem
Dienstneustart ohnehin ungültig.

Temporäre Druckerzertifikate liegen außerhalb des Datenordners und werden beim
geordneten Beenden entfernt. Nach einem harten Absturz kann temporäres Material
bis zur Betriebssystembereinigung bestehen bleiben.
