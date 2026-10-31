# Sicherung und Wiederherstellung

`backup.py` sichert die vollständigen **dauerhaften Anwendungsdaten**: Historie,
Druckerzuordnung, Zugangscode und weitere reguläre Dateien im Datenordner.
Ein Manifest enthält Einzelprüfsummen und das für die Wiederherstellung benötigte
Monitor-Image. Optional wird die tatsächlich verwendete Compose-Datei mitgesichert.
Temporäre MQTT-Zertifikate entstehen beim LAN-Handshake neu und werden nicht
als dauerhafte Zugangsdaten benötigt. Alte Unterordner `backups` werden ausgelassen.

Die ZIP-Datei enthält den Zugangscode im Klartext. Sie ist privat aufzubewahren;
neu erzeugte Dateien haben ausschließlich Besitzerrechte. Die Sicherung ist
nicht verschlüsselt. Eine Kopie auf demselben NAS schützt nicht gegen dessen
Ausfall. Mindestens einen geprüften Stand und das passende Container-Image
zusätzlich außerhalb des NAS aufbewahren. Python-Pakete und Betriebssystem
selbst sind nicht Bestandteil des Datenarchivs.

## Auf dem UGREEN-NAS automatisch sichern

Das separate Projekt `kobra-monitor-backup` verwendet
`deploy/ugos/backups.compose.yaml`. Die laufende Monitor-Installation wird nicht
ersetzt. Der Sicherungscontainer hat **kein Netzwerk** und liest Monitor-Volume
und Projektordner ausschließlich lesend. Seine ZIP-Dateien liegen in einem
eigenen Volume des Sicherungsprojekts. Dieses Volume beim Löschen eines Projekts
nicht mit entfernen.

Für die Vorlage müssen fünf Werte aus der bestehenden Installation eingesetzt
werden: Image-Tag, tatsächlicher Datenvolume-Name, absoluter Projektordner,
Gruppen-ID des Projektordners (UGOS zeigt beim Projektformular PGID an) sowie
das importierte Sicherungsimage `kobra-monitor:0.8.0-alpha.1`. Beispielwerte sind
keine voreingestellten persönlichen Ziele. Das vorhandene Monitor-Volume muss
als **external** referenziert werden; andernfalls würde ein leeres Volume gesichert.
Die zusätzliche Gruppe erlaubt das Lesen der bereits vorhandenen Compose-Datei
im ausschließlich lesend eingebundenen Projektordner. Die NAS-Verzeichnisrechte
werden dafür nicht erweitert. Die Gruppen-ID muss zum tatsächlichen Besitzer
dieses Ordners passen; auf dem geprüften UGOS-System war sie 10.

Nach dem Start entsteht sofort eine Sicherung. Anschließend wird nach jeweils
24 Stunden ein neuer Stand erstellt; sieben erfolgreiche Stände bleiben erhalten.
Nach Neustart wird die letzte geprüfte Sicherung berücksichtigt. Bei Fehlern
erfolgt nach fünf Minuten ein neuer Versuch. Alte Stände werden erst entfernt,
wenn die neue Sicherung vollständig geschrieben und geprüft wurde. Im Container-
Protokoll erscheint `Sicherung geprüft: …`; Zugangscodes erscheinen dort nicht.

Der erste Start und ein Wiederanlauf müssen auf dem konkreten NAS geprüft werden.
Ein noch laufender Druck muss dafür nicht angehalten werden: SQLite erzeugt
eine konsistente Kopie der Datenbank einschließlich bereits bestätigter WAL-Daten.

## Manuell sichern

Auf einem Rechner aus dem Projektordner:

```sh
python backup.py create --data-dir .state --destination /separater/sicherungsordner --image kobra-monitor:0.8.0-alpha.1
python backup.py inspect /separater/sicherungsordner/kobra-backup-ZEIT-ID.zip
```

Der Zielordner muss außerhalb des Datenordners liegen. `--deployment` nimmt
optional die aktive Compose-Datei auf. Bei einem extern per Umgebungsvariable
gesetzten Zugangscode muss dieser separat sicher dokumentiert werden: Die
vollständige Standardsicherung verlangt einen vorhandenen lokalen `access-token`.
Verschlüsselungs-/VPN-Einstellungen des NAS und anderer Dienste gehören nicht
zu diesem Anwendungsbackup.

## Wiederherstellung zuerst prüfen

```sh
python backup.py restore /sicherungen/kobra-backup-ZEIT-ID.zip --target /neuer/datenordner
```

Der Zielordner darf noch nicht existieren. Vor dem Anlegen prüft das Werkzeug
Archivpfade, Einzelprüfsummen, Datenbank und erforderliche Einrichtung. Bestehende
Daten werden nicht überschrieben. Die wiederhergestellte Kopie lässt sich mit
`History`, `load_config` und `Access` prüfen, ohne einen Drucker zu verbinden.
`inspect` zeigt Metadaten, niemals den Zugangscode.

Für den echten Umzug nur den Monitor und Sicherungsdienst stoppen. Ihre Volumes
erhalten. Den bisherigen Datenordner einschließlich zugehöriger WAL/SHM-Dateien
separat behalten; keine alten WAL/SHM-Dateien mit einer fremden Datenbank mischen.
Den geprüften neuen Datenordner als Monitor-Datenvolume verwenden. Das passende
Image aus dem Manifest importieren und die im Archiv enthaltene Compose-Datei
an die Wiederherstellungsumgebung anpassen. Für Docker müssen Besitzerrechte zu
UID/GID 10001 passen. Erst danach Monitor und Sicherungsdienst starten und beide
Drucker sowie Historie im Browser kontrollieren. Der vorhandene Zugangscode
bleibt erhalten; alte Browser-Sitzungen werden nicht wiederhergestellt.

Der zusätzliche Test auf einer getrennten Kopie bestätigt Daten und Einrichtung.
Ein kompletter NAS-Ausfall oder eine Wiederherstellung auf Ersatzhardware ist
damit noch nicht getestet.

## Bestätigter Praxistest

Am 30.10.2026 wurde der getrennte Sicherungsdienst auf UGREEN DXP4800GT / UGOS
in Betrieb genommen. Die erste Sicherung einschließlich Zugangscode und
Compose-Datei wurde auf NAS und Mac in getrennten Kopien wiederhergestellt;
sieben Aufträge samt Berichten und Zeitverläufen waren lesbar. Die Übertragung
auf den Mac war einmalig, der tägliche Dienst sichert im eigenen NAS-Volume.
Beide für die Wiederherstellung benötigten Container-Abbilder wurden ebenfalls
außerhalb des NAS aufbewahrt. Sie sind nicht im kleinen Daten-ZIP enthalten.

## Benutzerkonten ab 0.9

`account.json` enthält Benutzername, zufälligen Salt und scrypt-Prüfwert. Diese
Datei gehört zur vollständigen Sicherung und wird validiert. Änderungen während
der Sicherung lassen diese sicher fehlschlagen; der nächste Versuch verwendet
einen konsistenten Stand. Eine Wiederherstellung stellt das damalige Konto
wieder her. Der alte Einrichtungsschlüssel ist bei eingerichtetem Konto kein
Anmeldeweg. Archive bleiben vertraulich. Für 0.9-Stände Monitor und Sicherungs-
werkzeug ab 0.9 verwenden; ein Downgrade auf die frühere Code-Anmeldung würde
das neue Kontomodell nicht durchsetzen und ist nicht unterstützt.

Seit 0.14 gehören auch `push-vapid.pem`, Geräteanmeldungen und Benachrichtigungswarteschlange zur vollständigen Sicherung. Sie sind privat. Eine wiederhergestellte Kopie zum Prüfen nicht als zweiten sendenden Monitor starten.
