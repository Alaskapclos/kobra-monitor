# Kobra Monitor

Eine lokale, ausschließlich lesende Übersicht für den **Anycubic Kobra S1 mit
Stock-Firmware und LAN-Modus**. Status, Temperaturen, ACE-Filamente, Druckhistorie,
Berichte und Temperaturkurven bleiben bei dir. Keine Anycubic-Cloud-Anmeldung.

**Stand: 0.8.0-alpha.1.** Der Monitor ersetzt zunächst die Überwachungsfunktionen
der Cloud. Druckstart, Upload, Pause, Stop, Heizung, Bewegung, Kamera und
Filamentsteuerung sind nicht enthalten. Ein vollständiger Kobra-S1-Druck und
zwei parallele Druckerverbindungen wurden auf macOS beobachtet. Auch auf einem
UGREEN DXP4800GT mit UGOS läuft der amd64-Container mit zwei Druckern;
Einrichtung und aktive Verlaufseinträge blieben beim Containerneustart erhalten.

![Einrichtungsassistent mit Beispieladressen](docs/images/setup.jpg)

## Auf einem Rechner starten

Voraussetzung: Python **3.11 oder neuer**; zur Erstinstallation Internetzugriff auf
PyPI. Der Python-Installer für Windows sollte den Python Launcher mit installieren.

1. Projekt herunterladen und vollständig entpacken.
2. Den passenden Starter öffnen:
   - macOS: `Start-Kobra-Monitor.command`
   - Windows: `Start-Kobra-Monitor.cmd`
   - Linux: `sh Start-Kobra-Monitor.sh`
3. Der Browser öffnet die lokale Oberfläche und meldet diesen Browser automatisch an.
4. Im Assistenten die IP-Adresse(n) der Drucker eingeben und **Speichern und verbinden** wählen.
5. Unter **Einrichten** lassen sich die Adressen später ändern.

Die Adresse findest du am Drucker oder im Router. Aktiviere LAN-Modus. Es findet
kein Netzwerkscan statt. Maximal 16 Adressen können eingerichtet werden;
praktisch getestet wurden zwei Drucker.

Das Terminalfenster geöffnet lassen; **Ctrl+C** beendet nur den Monitor. Der
Rechner muss für die Überwachung eingeschaltet und wach bleiben. Browser schließen
beendet den Dienst nicht. Bei einer erneuten Installation im selben Ordner bleiben
Druckhistorie und Einrichtung erhalten. Die Starter aktualisieren ihre Bibliotheken,
wenn sich die festgelegten Versionen ändern.

macOS kann beim ersten Start einer heruntergeladenen `.command`-Datei eine
Freigabe verlangen. Die Datei über die Systemeinstellungen bzw. das Kontextmenü
nach Prüfung freigeben; das Paket ist nicht signiert oder notarisiert.

## Auf Server oder NAS installieren

Für UGREEN DXP4800GT mit UGOS gibt es eine [eigene Anleitung](docs/UGREEN_UGOS.md).

Für einen dauerhaft eingeschalteten Linux-Server oder ein NAS mit Docker/Compose
ist das eigene [Docker-Paket](docs/INSTALLATION.md) vorgesehen. NAS ohne
Container-Unterstützung sind kein zugesagtes Installationsziel.

```sh
docker compose up -d --build
```

Standardmäßig ist die Oberfläche nur auf dem Server selbst erreichbar. Historie,
Druckerzuordnung und Zugangscode liegen dauerhaft im Volume `monitor-data`.
Für die Einrichtung aus einem anderen Browser wird der Zugangscode angezeigt mit:

```sh
docker compose exec monitor python monitor.py --show-access-code
```

Der Code ist geheim und gehört nicht in Screenshots, öffentliche Issues oder Git.
Der amd64-Container wurde in der CI gebaut und auf einem UGREEN DXP4800GT
mit UGOS praktisch geprüft. Andere NAS-Modelle, arm64 und ein Austausch des
Images mit bestehendem Volume sind noch nicht praktisch geprüft.

## Daten sichern

Ein separater Sicherungsdienst kann auf dem NAS täglich sieben vollständige
Datenstände aufbewahren. Die laufende Überwachung bleibt dabei unverändert.
[Sicherung, Zugangsdaten und Wiederherstellung](docs/BACKUPS.md).

## Von unterwegs zugreifen

Der Monitor läuft bei den Druckern zu Hause. Handy oder Laptop greifen über das
vorhandene VPN auf ihn zu. Es gibt keinen vorgeschriebenen VPN-Anbieter.

- **Tailscale:** Tailscale auf dem Monitor-Host und dem Mobilgerät; Tailscale Serve
  stellt `http://127.0.0.1:7125` privat im Tailnet als HTTPS bereit.
- **Klassisches VPN:** WireGuard, OpenVPN oder Router-VPN verbinden ins Heimnetz.
  Der Monitor bzw. sein HTTPS-Proxy wird gezielt an eine erreichbare private
  Serveradresse gebunden.

[Anleitung und Grenzen des Fernzugriffs](docs/REMOTE_ACCESS.md).
Kein Portforwarding aus dem öffentlichen Internet auf den Monitor.

## Was du siehst

- Unabhängige Status- und Verbindungsanzeige pro Drucker; veraltete Werte sind markiert.
- Druckdatei, Fortschritt, Layer, verbleibende Zeit und Ist-/Solltemperaturen.
- ACE-Slots, Material, Farben und gemeldete Restmengen.
- Dauerhafte, nach Dateiname und Status durchsuchbare Druckhistorie.
- Herunterladbare Markdown-Berichte und Temperaturkurven mit Zustandsereignissen.

Restprozente, Feuchtigkeit und Firmware-Zeitangaben sind nicht unabhängig
validiert. Nullwerte bedeuten nicht zuverlässig leere Spulen oder echte 0 % Feuchte.
Ein bestätigter Druckabschluss ist kein visueller Qualitätsnachweis des Bauteils.
Verbindungsverlust bedeutet niemals automatisch Druckende.

## Zugang und Daten

Jede Installation erzeugt einen eigenen Zugangscode. Der Desktop-Starter übergibt
ihn einmal im URL-Fragment; die Oberfläche entfernt das Fragment sofort. Andere
Browser melden sich mit diesem Code an. Sitzungen laufen nach zwölf Stunden ab
und werden beim Dienstneustart ungültig. Alle angemeldeten Benutzer dieser Alpha
haben denselben Zugriff einschließlich Änderung der lokalen Druckerzuordnung.

Datenordner: `.state/` im Projekt, im Container `/data`. Für andere Orte:
`--data-dir /pfad` oder `KOBRA_DATA_DIR`. Einzelheiten, Sicherung und Update:
[Installation](docs/INSTALLATION.md). Die `.state`-Dateien gehören nicht ins Repository.

**Wichtige Grenze:** Die übernommene TLS-Serverprüfung zum Drucker ist deaktiviert.
Die Verbindung ist verschlüsselt, die Identität des Brokers aber nicht verifiziert.
Nur in einem vertrauenswürdigen Druckernetz betreiben. [Sicherheitsbeschreibung](SECURITY.md).

## Entwicklung und Tests

```sh
python -m venv .venv
# macOS/Linux:
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python vendor/kobra-bridge/test_read_only.py
node --check static/monitor.js
node --check static/setup.js
node tests/test_timeline_render.js
node tests/test_archive_render.js
python scripts/release_check.py
```

Unter Windows liegt Python unter `.venv\Scripts\python.exe`. Die CI prüft
Python 3.11 und 3.14 auf macOS, Linux und Windows. Alle sechs Plattformläufe
und der Container-Test bestanden am 30.10.2026. Die CI arbeitet ohne reale
Drucker; Hardware- und Fernzugriffstests sind gesondert ausgewiesen.
[Testmatrix und belegter CI-Lauf](docs/VALIDATION.md).

## Herkunft und Lizenz

Gesamtprojekt: **GPL-3.0-only**. Die ursprünglichen Lizenzen und Hinweise der
mitgelieferten Bibliotheken bleiben erhalten. Verwendet werden:

- `cluzl/kobra-bridge`, Basis `25c36815f5e2cab394fc83c73fca447367253fca`, GPL-3.0;
  lokale Lesebeschränkung und getrennte Zertifikatspfade.
- `rvanderp3/kobra-connect`, Basis `3edba24606d7122c4a68accd09af937ba4fdbd08`, Apache-2.0;
  nur Kernmodule und Handshake, mit einer TLS-Parameterkorrektur.

[NOTICE](NOTICE.md), [SOURCES.json](SOURCES.json), [Änderungen an Fremdcode](docs/UPSTREAM.md).
Keine Slicer-Zertifikate oder privaten Schlüssel werden ausgeliefert. Anycubic
und Tailscale sind Marken ihrer jeweiligen Rechteinhaber; dies ist ein unabhängiges Projekt.
