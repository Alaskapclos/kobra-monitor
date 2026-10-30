# Prüfstand der Alpha

| Bereich | Status |
| --- | --- |
| Frische Python-Installation, macOS / Python 3.14.6 | Bestanden; eigener neuer venv aus Lockdatei |
| Eigene Python-Tests | 55 bestanden |
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
| Tailscale Serve / anderes VPN | Anleitungen nach Primärdokumentation; kein echter Fernzugriffstest |
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
