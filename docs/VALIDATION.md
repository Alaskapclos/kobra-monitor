# Prüfstand der Alpha

| Bereich | Status |
| --- | --- |
| Frische Python-Installation, macOS / Python 3.14.6 | Bestanden; eigener neuer venv aus Lockdatei |
| Eigene Python-Tests | 81 bestanden; aktueller lokaler Prüflauf 31.10.2026 |
| Zusätzliche Leseschutztests der Bridge | 14 bestanden |
| JavaScript-Darstellung | Elf Prüffälle bestanden; Syntax geprüft |
| Browser-Ersteinrichtung | Anmeldung, ungültige Adresse, zwei Adressen und Abschluss geprüft; Drucker-I/O in der Testansicht abgeschaltet |
| Geschützter lokaler Dienst nach dem Update | Anmeldung im Browser, zwei Geräte online, bestehende Historie übernommen; aktiver Auftrag blieb erhalten |
| Reale Hardware vor der Einrichtungserweiterung | Zwei Kobra S1 mit Firmware 2.7.2.7; ein vollständiger Druck einschließlich Vorbereitung/Ende |
| macOS / Python 3.11 und 3.14 | GitHub-CI bestanden |
| Linux / Windows, jeweils Python 3.11 und 3.14 | GitHub-CI bestanden; keine reale Druckerhardware an diesen Runnern |
| Docker / Compose, linux/amd64 | GitHub-CI: Build und Container-Starttest bestanden; Abbild auf UGOS importiert und gestartet |
| UGREEN DXP4800GT / UGOS, amd64 | Zwei Kobra S1 live: Status, Temperaturen und ACE; Containerneustart erhält Einrichtung, Zugangscode und beide aktiven Auftrags-IDs |
| Andere NAS / arm64 / Image-Update | Noch nicht praktisch geprüft |
| Bestehendes Tailscale, Mobilfunkzugriff | Nutzer bestätigte erfolgreiche Anmeldung und Zugriff; keine Änderung der VPN-Konfiguration |
| Tailscale Serve / HTTPS | Gültiges Zertifikat, Zugriff ohne Sitzung gesperrt; Nutzer bestätigt Mobilfunkzugriff mit VPN und Nichterreichbarkeit ohne VPN. Keine vollständige ACL-Prüfung |
| Historienumzug Mac → UGOS | Einmalig betreut geprüft: vier geschlossene Aufträge importiert, zwei überlappende Aufträge um frühere Beobachtung ergänzt, aktuelle NAS-Zustände erhalten |
| Historienbackup / Wiederherstellung | SQLite-Backup vor/nach Import; tatsächliche NAS-Sicherung in separater Kopie geöffnet, alle sechs Berichte und Zeitverläufe lesbar; vollständige Installationsbackups einschließlich Konto isoliert wiederhergestellt (siehe spätere Abschnitte) |
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

## Druckerreihenfolge 0.10

81 Python-Tests, 14 Leseschutztests und elf JavaScript-Prüffälle lokal erfolgreich.
Neue Prüfungen: ausschließlich exakte Permutationen der eingerichteten Drucker
zulassen; Reihenfolge in config.json, Snapshot und nach Neustart identisch;
keine Druckerverbindung neu starten; Anmeldung, CSRF und Origin für Sortieren
erforderlich. Browser-Fixture ohne Druckerkommunikation: Ziehen und Tastatur
verschieben die Karten; die Reihenfolge bleibt nach Neuladen erhalten und die
ausgewählte Druckeransicht wird während des Sortierens beibehalten.
Der NAS-Monitor und der getrennte Sicherungsdienst wurden auf das geprüfte
0.10-Image aktualisiert. Alle sieben Aufträge und der Kontoprüfwert sind
unverändert. Die gespeicherte Reihenfolge ist erster Drucker vor zweitem
Drucker; eine vollständige Sicherung wurde mit dieser Reihenfolge isoliert
wiederhergestellt. Fälligkeitsprüfung erzeugt keinen doppelten Tagesstand.
Die Verbindung war beim Versionswechsel rund fünf Sekunden unterbrochen.
Nach erneuter Nutzeranmeldung am echten NAS geprüft: Karten per Ziehen in
beide Richtungen verschoben, jeweils gespeichert und gewünschte Reihenfolge
nach Neuladen bestätigt. Die ausgewählte Druckeransicht blieb beim Ziehen
erhalten; beide Geräte waren verbunden. Tastatur zusätzlich auf Fixture geprüft.
Eine Prüfung auf einem physischen Touchgerät steht noch aus.

[GitHub-Prüflauf 41135356856](https://github.com/Alaskapclos/kobra-monitor/actions/runs/41135356856) für Code-Commit `0e8d9552525edbf848ebe079e9a2e4414f0f9f10`: alle sieben Jobs erfolgreich.

## HTTPS und Einrichtung 0.11

HTTPS auf dem NAS mit bestehendem Tailscale Serve aktiviert. Zertifikat vom Mac ohne Ausnahme gültig. Startseite und Healthcheck 200, Status ohne Sitzung 401. Nutzer bestätigt Anmeldung, Betrieb und Mobilfunk-Gegenprobe: mit Tailscale erreichbar, ohne gesperrt. Konto/Einrichtung und sieben bestehende Aufträge nach kurzer Monitor-Neubereitstellung unverändert; vollständiges Folgearchiv isoliert wiederhergestellt. Beobachtungslücke rund zehn Sekunden. Keine Druckersteuerung oder Änderung von VPN-Zugriffsregeln.

Neuer Einrichtungsdialog: einzelne Druckeradressfelder, Hinzufügen/Entfernen, Duplicate-Meldung, Grenze 16 und Rückkehr ohne Speichern in isolierter Browser-Fixture ohne Druckerkommunikation geprüft. Verbindungsübersicht unterscheidet gespeicherte Einrichtung und tatsächliche Verbindung. Lokale Python-Prüfungen: 81 bestanden. Alle sieben CI-Jobs des [Prüflaufs 41185025363](https://github.com/Alaskapclos/kobra-monitor/actions/runs/41185025363) für Commit `397d83a8d1b9f4b93d2935337f62dc6286be6e65` erfolgreich. Monitor und Sicherungsdienst auf UGOS auf 0.11 aktualisiert. Sieben Aufträge, Konto und Einrichtung unverändert, Folgearchiv isoliert erfolgreich wiederhergestellt. Beobachtungslücke 6,27 Sekunden. Echte Browserprüfung über bestehende LAN-Sitzung: zwei Druckerzeilen verbunden; unverändertes Speichern und Abschlussanzeige erfolgreich. HTTPS liefert neue Oberfläche mit gültiger Zertifikatsprüfung aus. Keine eigene Sichtprüfung einer angemeldeten HTTPS-Sitzung oder eines physischen Handy-Layouts behauptet.

## Kamera 0.12

90 Python-Tests, 14 unveränderte MQTT-Leseschutztests und elf JavaScript-Prüffälle lokal erfolgreich. Zwei echte Stock-S1-Streams ausschließlich lesend in 1280×720 dekodiert; isolierte angemeldete Browser-Vorschau beider Kameras und Schließen bei Druckerwechsel geprüft. Decoder-Test mit künstlicher lokaler FLV-Quelle und tatsächlich blockierter HTTP-Weiterleitung bestanden. Anmeldung, feste eingerichtete IPs, Kapazitätsgrenze, veraltete Bilder und Beenden ungenutzter Leser geprüft. NAS-Container und Handyprüfung stehen noch aus. Keine Kamera-Aktivierungsbefehle.

Alle sieben Jobs von [Prüflauf 41186287793](https://github.com/Alaskapclos/kobra-monitor/actions/runs/41186287793) erfolgreich, einschließlich echter Decoder- und Weiterleitungsprüfung im NAS-Image. Monitor und Backup auf UGOS aktualisiert. Sieben Aufträge, Konto und Einrichtung unverändert; vollständige Folge-Sicherung in frischem /tmp-Ordner wiederhergestellt. Beobachtungslücke 6,20 Sekunden. HTTPS-Auslieferung und Kamerazugang ohne Anmeldung (401) geprüft. Angemeldete NAS-Sichtprüfung und mobile Kameraansicht noch offen.

## Kamerabildwechsel 0.12.1

Nutzer bestätigt die Kameraansicht auf dem Handy, meldet dabei periodisches Flackern. Ursache im Frontend: Löschen/Ausblenden des sichtbaren Bildes vor jedem Ersatz. Neue Bilder werden vor dem sichtbaren Wechsel dekodiert. Sechs gezielte JS-Regressionen decken verzögerte/fehlgeschlagene Decodierung, Fehler, Ablauf alter Bilder und Druckerwechsel ab. Insgesamt 17 JS-Prüffälle erfolgreich. Getrennte Browser-Vorschau mit echtem S1-Bild erfolgreich; keine MQTT-Sitzung in der Vorschau. Alle sieben Jobs von [Prüflauf 41187023196](https://github.com/Alaskapclos/kobra-monitor/actions/runs/41187023196) erfolgreich. Monitor und Backup auf UGOS aktualisiert, sieben Aufträge/Konto/Einrichtung unverändert, Sicherung vollständig isoliert wiederhergestellt. Beobachtungslücke 5,53 Sekunden. HTTPS liefert bytegleich die geprüfte Kamera-Datei; ohne Sitzung weiterhin 401. Erneuter physischer Handytest der Korrektur noch offen.

## Kameraübersicht 0.13

92 Python-Tests, 14 unveränderte MQTT-Leseschutztests und 24 JavaScript-Prüffälle erfolgreich. Neu geprüft: vier gemeinsame Leser als Obergrenze; Freigabe und Ablauf pro Ansicht ohne Unterbrechen anderer Browser; Freigabe mit Anmeldung, CSRF und Origin. Sieben virtuelle Drucker in Browser-Fixture: Vierer-/Zweier-Ansicht und Seitenwechsel; zwei echte Stock-S1-Kameras gleichzeitig in getrennter Vorschau sichtbar, keine MQTT-Verbindungen in dieser Vorschau. Aktuelle Ansichtskennungen nutzen getRandomValues auch für gewöhnliches LAN-HTTP. Alle sieben Jobs von [Prüflauf 41188848065](https://github.com/Alaskapclos/kobra-monitor/actions/runs/41188848065) für Commit 3802000372810d55c4ab925be0775d21d7bad0ed erfolgreich. Monitor und Sicherungsdienst auf UGOS aktualisiert; Konto/Einrichtung/sieben Aufträge unverändert, Vollsicherung isoliert wiederhergestellt. Beobachtungslücke 7,33 Sekunden. HTTPS liefert die neuen Skripte bytegleich; Status/Kamera ohne Sitzung weiterhin 401. Vier reale Kameras, eine größere reale Flotte und physische Handy-Matrix noch nicht geprüft. Nutzer bestätigt die vorangegangene einzelne Kameraansicht auf Mac, Handy im WLAN und Mobilfunk über Tailscale ohne weiteres Flackern.


## Kameraerkennung 0.13.1

Auf dem NAS war FFmpeg vorhanden und direkt funktionsfähig. Die bisherige Erkennung konnte einen einmaligen Fehler dauerhaft als „nicht verfügbar“ speichern. Negative Ergebnisse werden jetzt nach fünf Sekunden erneut geprüft. Der konkrete erste Auslöser wurde zuvor nicht protokolliert und ist deshalb nicht bewiesen. Auf Handy und Mac als Anzeige ist keine FFmpeg-Installation nötig.

97 Python-, 14 MQTT-Leseschutz- und 24 JS-Prüffälle erfolgreich; fünf neue Regressionen prüfen Wiederanlauf nach Timeout, fehlendem Programm, Fehler und ungeeigneter Version einschließlich Erholung im selben laufenden HTTP-Dienst. Alle sieben Jobs von [Prüflauf 41190324154](https://github.com/Alaskapclos/kobra-monitor/actions/runs/41190324154) für Commit 6e669d60b4556e9f404bb0ff7980e4d2a10d031d erfolgreich. CI prüft zusätzlich die Kamerabereitschaft des tatsächlich laufenden Monitors.

Monitor und Sicherungsdienst auf UGOS aktualisiert. Der laufende NAS-Dienst meldet über HTTPS camera_available=true. Konto, Einrichtung und sieben Aufträge unverändert; vollständiges Folgearchiv isoliert wiederhergestellt, einschließlich Konto und SQLite-Prüfung. Beobachtungslücke 6,71 Sekunden. Regulärer Tagesstand noch nicht fällig; Nachkontrolle unverändert am 01.11.2026 um 08:00 Uhr. Nutzer bestätigt am 31.10.2026 funktionierende Kameraansicht von unterwegs über Tailscale. Keine Druckersteuerung.

## Benachrichtigungen 0.14

115 Python-Tests und 14 unveränderte MQTT-Leseschutztests; 34 JS-Prüffälle vorgesehen. Neue Prüfungen: bestätigte Enden statt Verbindungsverlust, Verzögerung und Wiederverbindung, Fehler-Entdoppelung, Geräteauswahl, Neustart, alte Ereignisse, Senderetries/Entfernung, Zielbegrenzung, Anmeldung/CSRF/Origin, echte Verschlüsselung mit anschließender Entschlüsselung ohne externen Versand. Vollsicherung stellt Schlüssel, Geräte und Warteschlange gemeinsam wieder her. Zehn JS-Fälle decken iOS-Hinweis, HTTPS, explizite Aktivierung, Test/Entfernen sowie sicheren Service Worker ohne Seiten-Cache ab. Browser-Fixture bei 390 Pixeln geprüft, ohne Druckerkommunikation oder externen Push. CI, produktive Installation und physischer Handyempfang noch offen.
