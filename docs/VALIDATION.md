# Prüfstand der Alpha

| Bereich | Status |
| --- | --- |
| Frische Python-Installation, macOS / Python 3.14.6 | Bestanden; eigener neuer venv aus Lockdatei |
| Eigene Python-Tests | 65 bestanden |
| Zusätzliche Leseschutztests der Bridge | 14 bestanden |
| JavaScript-Darstellung | 6 Prüffälle bestanden; Syntax geprüft |
| Browser-Ersteinrichtung | Anmeldung, ungültige Adresse, zwei Adressen und Abschluss geprüft; Drucker-I/O in der Testansicht abgeschaltet |
| Geschützter lokaler Dienst nach dem Update | Anmeldung im Browser, zwei Geräte online, bestehende Historie übernommen; aktiver Auftrag blieb erhalten |
| Reale Hardware vor der Einrichtungserweiterung | Zwei Kobra S1 mit Firmware 2.7.2.7; ein vollständiger Druck einschließlich Vorbereitung/Ende |
| macOS / Python 3.11 und 3.14 | GitHub-CI bestanden |
| Linux / Windows, jeweils Python 3.11 und 3.14 | GitHub-CI bestanden; keine reale Druckerhardware an diesen Runnern |
| Docker / Compose, linux/amd64 | GitHub-CI: Build und Container-Starttest bestanden; Abbild auf UGOS importiert und gestartet |
| UGREEN DXP4800GT / UGOS, amd64 | Zwei Kobra S1 live: Status, Temperaturen und ACE; Containerneustart erhält Einrichtung, Zugangscode und beide aktiven Auftrags-IDs |
| Andere NAS / arm64 / Image-Update | Noch nicht praktisch geprüft |
| Bestehendes Tailscale, Mobilfunkzugriff | Nutzer bestätigte erfolgreiche Anmeldung und Zugriff; keine Änderung der VPN-Konfiguration |
| Tailscale Serve / HTTPS / VPN-Zugriffsregeln | Noch nicht praktisch geprüft |
| Historienumzug Mac → UGOS | Einmalig betreut geprüft: vier geschlossene Aufträge importiert, zwei überlappende Aufträge um frühere Beobachtung ergänzt, aktuelle NAS-Zustände erhalten |
| Historienbackup / Wiederherstellung | SQLite-Backup vor/nach Import; tatsächliche NAS-Sicherung in separater Kopie geöffnet, alle sechs Berichte und Zeitverläufe lesbar; vollständiges Installationsbackup noch offen |
| Brokerzertifikatsprüfung | Deaktiviert; bekannte Sicherheitsgrenze der Alpha |
| Physischer WLAN-Ausfall während eines Drucks | Noch kein gezielt ausgelöster Hardwaretest |

Die CI startet ohne reale Drucker und prüft Container/Healthcheck mit leerer
Ersteinrichtung. Der [GitHub-Lauf 41109579545](https://github.com/Alaskapclos/kobra-monitor/actions/runs/41109579545)
prüfte Quellcode-Commit `5223629616b33fe822e6bc9b47e6ae785164d601`: alle sieben Jobs grün.
Spätere reine Dokumentationsänderungen sind davon getrennt.

Der NAS-Praxistest erfolgte am 30.10.2026 mit dem aus diesem Lauf exportierten
Abbild `kobra-monitor:0.7.0-alpha.1`. Nach einem gezielten Neustart nur dieses
Containers waren beide laufenden Aufträge weiterhin aktiv und hatten jeweils
denselben Historieneintrag, ohne zusätzliche Aufträge oder falschen Abschluss.
Die kurze Unterbrechung des Monitors ist eine Beobachtungslücke; die
Drucke wurden bereits laufend entdeckt, nicht vollständig vom NAS beobachtet.
Die genaue UGOS-Version wurde nicht erfasst. Der Mac-Monitor lief parallel
mit eigener Historie weiter. Ein Image-Austausch und ein NAS-Neustart wurden
nicht getestet.

## Vor einem öffentlichen Alpha-Release

1. Erledigt: GitHub-CI mit sieben erfolgreichen Jobs.
2. Erledigt: NAS-Start und Containerneustart mit zwei Druckern; noch offen:
   Image-Update mit bestehendem Volume und konsistente Sicherung/Wiederherstellung.
3. Zugriff von einem zweiten Gerät über VPN/HTTPS sowie Ablehnung ohne Sitzung
   testen. Proxy muss den Host-Header erhalten. Gerät außerhalb des VPN darf die
   private Adresse nicht erreichen.
4. Zugangscode, private Daten und Git-Historie vor Veröffentlichung prüfen.
5. Read-only-Grenze, Broker-TLS-Grenze und tatsächliche Plattformabdeckung nennen.

Keine Pause/Stop/Temperatur-/Bewegungs-/Upload-/Filamentbefehle für diese Tests.

## Nachfolgender Betriebsumzug

Die Mac-Historie wurde am selben Tag nach konsistenten Sicherungen mit der
NAS-Historie zusammengeführt. Überlappende Aufträge wurden anhand von
Druckeradresse, identischem Dateinamen und überlappender Beobachtungszeit
zugeordnet. Nur Beobachtungen vor der ursprünglichen NAS-Erkennung wurden
ergänzt; NAS-Auftrags-IDs, aktueller Fortschritt und Endzustände blieben erhalten.
Herkunft und Quellprüfsumme stehen als Importereignisse in der Datenbank.
Ein Test auf einer Kopie prüfte Wiederholbarkeit ohne zusätzliche Einträge und
Zurückrollen bei mehrdeutiger Zuordnung. Die tatsächliche NAS-Sicherung nach
dem Import wurde anschließend separat geöffnet. Der Mac-Monitor wurde erst
nach dieser Kontrolle beendet; das NAS zeichnete ohne Neustart weiter auf.

Das war ein betreuter Einzelumzug, keine im Einrichtungsassistenten verfügbare
Importfunktion. Ursprüngliche Beobachtungslücken bleiben bestehen. Die danach eingerichtete vollständige Sicherung ist im folgenden Abschnitt dokumentiert.

## Sicherungsdienst 0.8.0-alpha.1

65 Python-Tests (darunter zehn neue Sicherungs-/Wiederherstellungstests) und
14 Leseschutztests bestanden lokal. Der zusätzliche Container-CI-Test prüft
Sicherung und Wiederherstellung bei nur lesend eingebundenem Monitor-Volume
und abgeschaltetem Netzwerk des Sicherungscontainers. Der [GitHub-Lauf 41120149518](https://github.com/Alaskapclos/kobra-monitor/actions/runs/41120149518)
für Code-Commit `1eaef09deec750fe03938dcbbbecd1255e130102` bestand mit allen
sieben Jobs. Zunächst wurde der getrennte Sicherungscontainer auf 0.8.0-alpha.1 eingerichtet;
der anschließende Monitorwechsel ist unten dokumentiert.

Auf UGOS wurde eine echte vollständige Sicherung mit sieben Aufträgen,
Druckerzuordnung, Zugangscode und aktiver Monitor-Compose-Datei erzeugt.
Sie wurde im netzlosen Sicherungscontainer in einen getrennten Ordner
wiederhergestellt und zusätzlich auf dem Mac zurückgelesen. Einrichtung und
Zugangscode stimmen überein; alle sieben Berichte und Zeitverläufe sind lesbar.
Die Prüfsumme der externen Kopie stimmt mit dem NAS-Original überein.

Das Quellvolume ist nur lesend eingebunden; der Sicherungscontainer hat nur
eine Loopback-Netzwerkschnittstelle. Für das Lesen des UGOS-Projektordners
war dessen vorhandene Gruppen-ID 10 erforderlich; die zusätzliche Gruppe ist
nur dem Sicherungscontainer zugewiesen. NAS-Dateirechte wurden nicht erweitert.
Eine erneute Prüfung der Fälligkeit mit dem echten Archiv erzeugte keinen
zusätzlichen Stand. Tagesrhythmus und Aufbewahrung über mehrere Tage wurden
mit kontrollierter Testzeit geprüft; der erste reale 24-Stunden-Termin ist
noch nicht verstrichen. Ein echter NAS-Ausfall/Ersatzgeräte-Test steht aus.

## Tatsächlicher NAS-Versionswechsel 0.7 → 0.8

Am 30.10.2026 wurde das bestehende UGOS-Monitorprojekt mit dem geprüften
Image 0.8.0-alpha.1 neu bereitgestellt. Das benannte Datenvolume, die
Portbindung und die bestehenden Schutzmaßnahmen blieben erhalten.
Vorher und nachher wurden vollständige Sicherungen erstellt und geprüft.

Alle sieben Auftragskennungen sind unverändert vorhanden. Beide laufenden
Aufträge wurden unter derselben Kennung fortgeführt, ohne fälschlichen
Abschluss oder zusätzlich erzeugten Auftrag. Einrichtung und Zugangscode
stimmen per SHA-256 mit dem Stand vor dem Update überein; die Anmeldung
mit dem bisherigen Code und Live-Daten beider Drucker wurden geprüft.

Das Verbindungsprotokoll zeigt eine Unterbrechung am 30.10.2026 von etwa
21:38:41 bis 21:38:48 MEZ, je Drucker rund 6–7 Sekunden. In dieser Zeit
fehlen Live-Daten. Der größte Abstand gespeicherter Messpunkte im
geprüften Zeitfenster betrug unter 24 Sekunden. Laufende Drucke wurden
nicht gesteuert. Der Mac-Monitor blieb ausgeschaltet.

Der Sicherungsdienst dokumentiert nun ebenfalls Monitor-Image 0.8.
Der neue vollständige Stand wurde isoliert wiederhergestellt (sieben
Aufträge) und zusätzlich mit identischer Prüfsumme außerhalb des NAS
gespeichert. Die Fälligkeitsprüfung erzeugte keinen zusätzlichen
Tagesstand; die Prüfung eines realen 24-Stunden-Zyklus steht weiterhin aus.
Ein tatsächliches Downgrade oder Austausch des produktiven Datenvolumes
wurde nicht ausgeführt. Tailscale und NAS-Sicherheitseinstellungen wurden
nicht verändert.

## Benutzerkonto 0.9.0-alpha.1

78 Python-Tests und 14 Leseschutztests bestanden lokal. Darunter: geschützte
Ersteinrichtung, Umstieg mit Sperre des alten Codes, Unicode-Benutzernamen,
Passwortbestätigung und Längenprüfung, scrypt/Salt/Dateirechte, Fehlerdrosselung,
CSRF/Origin, Abmelden, Widerruf anderer Sitzungen nach Kontoänderung und
vollständige Sicherung/Wiederherstellung einschließlich Konto. Beschädigte
Kontodateien aktivieren keinen Code-Ausweichzugang.

Die Browserprüfung erfolgte auf einem getrennten lokalen Testdienst mit
ausgeschalteter Druckerkommunikation: Konto anlegen, falsche Bestätigung,
Druckereinrichtung, Abmelden und erneutes Anmelden mit selbst gewählten
Testdaten erfolgreich. Keine echten Benutzerpasswörter durch den Agenten gesetzt.
Die NAS-Hauptinstanz und der getrennte Sicherungsdienst wurden danach auf
0.9 aktualisiert. Alle sieben Aufträge und die Druckerzuordnung sind erhalten.
Die Installation hat zunächst ein Besitzerkonto, keine Benutzerverwaltung mit
mehreren Rollen. Die Rücksetzung erfolgt lokal, nicht per E-Mail.

Der [CI-Lauf 41133000053](https://github.com/Alaskapclos/kobra-monitor/actions/runs/41133000053)
für Code-Commit `639a270353924ee51232174889d4519e199abbef` bestand mit
allen sieben Jobs (Windows, macOS, Linux und Container). Das getestete amd64-
Abbild wurde per Artefakt-Prüfsumme kontrolliert und auf UGOS eingesetzt.
Der Nutzer hat das echte Konto selbst angelegt; die angemeldete Browseransicht
zeigt beide Drucker mit Live-Daten. Die echte vollständige Sicherung enthält
den Kontoprüfwert und wurde isoliert auf NAS und Mac wiederhergestellt.
Die zusätzliche Mac-Kopie hat dieselbe Prüfsumme wie das NAS-Original.

Verbindungsereignisse beim Update: 30.10.2026 ca. 22:48:14–22:48:21 MEZ,
rund sechs Sekunden Unterbrechung je Drucker. Beide Drucke waren bereits vor
dem Update abgeschlossen. Ihre gespeicherten Zustände/Endzeiten blieben
unverändert. Keine Druckersteuerung und kein Neustart des Mac-Monitors.
Der echte 24-Stunden-Sicherungszyklus bleibt bis zum Folgetag ungeprüft.
