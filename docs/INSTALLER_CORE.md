# Gemeinsamer Installationskern – Entwicklungsstand

Stand 09.11.2026. Diese Bausteine sind implementiert und teilweise in den getrennten nativen beziehungsweise Docker-Testinstallationen eingebunden. Die signierte Paketprüfung ist noch kein aktiver allgemeiner Updateassistent. Die bisherige produktive NAS-Installation wird dadurch nicht automatisch verändert. Die Zielpakete und die weitere Abnahmefolge stehen in [INSTALLERS.md](INSTALLERS.md).

## Paketprüfung

`suite/packages.py` prüft ein ZIP ohne Entpacken oder Ausführen. Eine Ed25519-Signatur schützt die exakten Bytes von `release.json`; das signierte Verzeichnis enthält Größe und SHA-256 jeder Datei. Der vertrauenswürdige öffentliche Schlüssel muss aus einer bereits vertrauenswürdigen Quelle außerhalb des Pakets stammen. Ein mitgelieferter Schlüssel begründet kein Vertrauen. Der dauerhafte Veröffentlichungsschlüssel und dessen Verteilung sind noch einzurichten; Tests benutzen ausschließlich kurzlebige Testschlüssel.

Das Format `kobra-suite-release-v1` bindet Zielsystem, feste Paketversion sowie Monitor, Spoolman, Python und FFmpeg aneinander. Jede Komponente benötigt Programmdateien, Lizenztext und Quellzuordnung. Zusätzliche Dateien, veränderte Inhalte, doppelte Pfade, symbolische Links, Verzeichniseinträge und auf Windows problematische Pfade werden abgewiesen. Größen und Dateianzahl sind begrenzt. Ein positives Ergebnis besagt, dass die geprüften Bytes zum vertrauten Herausgeber und Katalog passen. Es ersetzt weder die inhaltliche Lizenzprüfung noch Windows-/macOS-Signierung und Notarisierung.

Entwicklungswerkzeug:

```sh
python suite_cli.py verify-package release.zip --platform linux-x86_64 \
  --key-id publisher-v1 --trusted-public-key publisher.pub
```

`publisher.pub` enthält genau 32 rohe öffentliche Schlüsselbytes. Der Prüfer installiert nichts. Spätere Installation muss dieselben verifizierten Bytes verwenden und darf die Quelldatei zwischen Prüfung und Verarbeitung nicht ungeschützt austauschen lassen.

## Gemeinsame Datensicherung

`suite/snapshots.py` erstellt die bestehende vollständige Monitor-Sicherung einschließlich Berichten, Originaldatei-Archiv und privaten Kontodaten sowie eine konsistente SQLite-Sicherung von Spoolman. Die Quellen werden lesend geöffnet; auch noch im WAL liegende bestätigte SQLite-Änderungen werden übernommen. Beide Datenbanken sind jeweils konsistent, bilden aber keine gemeinsame Transaktion.

Ein privater Sicherungsordner enthält `monitor.zip`, `spoolman.sqlite3` und `snapshot.json`. Vor der endgültigen Bereitstellung werden Monitor und Spoolman in getrennten temporären Pfaden tatsächlich wiederhergestellt und geprüft. Die Spoolman-Prüfung umfasst SQLite-Integrität, Fremdschlüssel, Schema und Tabellenzahlen. Eine fehlgeschlagene Prüfung veröffentlicht keinen halben Sicherungsstand und löscht keine älteren Sicherungen. Wiederholtes `verify-snapshot` führt die isolierte Prüfung erneut aus, ohne produktive Daten zu ersetzen oder Dienste zu starten.

```sh
python suite_cli.py create-snapshot --monitor-data /path/to/monitor-data \
  --spoolman-database /path/to/spoolman-data/spoolman.db \
  --destination /path/to/separate-backups \
  --monitor-image kobra-monitor:EXACT_VERSION --spoolman-image spoolman:EXACT_VERSION
python suite_cli.py verify-snapshot /path/to/separate-backups/kobra-suite-TIMESTAMP-ID
```

Die Sicherung enthält private Daten und gehört nicht in öffentliche Repositories oder Diagnose-Downloads. Prüfsummen erkennen Beschädigungen; sie sind keine Herausgebersignatur. Die Programm-/Imageangaben müssen vom späteren Installationskoordinator aus dem geprüften Bestand kommen. Die Images selbst sind nicht in dieser Datensicherung enthalten. Unter Windows sind zusätzlich passende Benutzerrechte/ACLs einzurichten; POSIX-Dateimodi allein ersetzen dies nicht.

Der aktuelle Baustein unterstützt die SQLite-Datenbank von Spoolman. Externe Datenbankserver, Spoolman-Einstellungen außerhalb der Datenbank, die gemeinsame Dienste-Konfiguration und die tatsächliche Rückkehr auf passende Programmversionen benötigen noch die Integration im Installationskoordinator. Vor dessen Abnahme ist dies keine vollständige Sicherung jeder denkbaren bestehenden Installation. Eine bestehende NAS-Installation wird nicht automatisch übernommen.

## Rückstellung bei laufendem Druck

`suite/readiness.py` liest den vorhandenen Flottenzustand ohne Druckerbefehle. Offene Aufträge, Vorbereitung, Pause, unklare Phasen, fehlende Geräte, neue Verbindungen oder veraltete Daten geben ein Update nicht frei. Für jeden eingerichteten Drucker ist expliziter aktueller Leerlauf erforderlich. Eine Bewegungsfreigabe ist dafür nicht nötig.

Ein vorbereiteter Stand muss unmittelbar vor einem späteren Dienststopp erneut geprüft werden. Neue Drucke, Verbindungen oder geänderte Geräte machen ihn ungültig; ein alter Prüfstand ist keine Installationsfreigabe. Dieser Adapter ist noch nicht an eine Updateoberfläche oder einen Dienststopp angeschlossen. Er kann einen unabhängig gestarteten Druck nach der letzten Abfrage nicht ausschließen; Zeitfenster und verständliche Rückmeldung sind im Koordinator zu behandeln.

## Integration der getrennten Testinstallation

Zunächst folgt eine isolierte gemeinsame Server-/NAS-Testinstallation mit eigenem Spoolman und eigenen Datenvolumes. Sie muss Einrichtung, gemeinsame Dienstkonfiguration, Sicherung, tatsächliche Wiederherstellung beider Dienste und Updatefehler abdecken. Anschließend folgen native Laufzeiten und die zielsystemspezifischen Installer. Die vorhandene produktive NAS-Installation bleibt während der Entwicklung unverändert.

Die Erzeugung dieses Testprojekts, die netzwerklose Volume-Initialisierung und Sicherung sowie die Wiederherstellung beider Datenbanken samt aufgezeichneter Compose-Konfiguration sind inzwischen implementiert. Die geplante echte Mehrcontainer-Abnahme beschreibt [SUITE_TEST.md](SUITE_TEST.md); ihr Erfolg muss für den jeweiligen Bau gesondert nachgewiesen werden.
