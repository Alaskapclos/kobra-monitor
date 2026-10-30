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
| macOS / Python 3.11 | CI vorbereitet, noch kein GitHub-Lauf |
| Linux / Windows | CI vorbereitet; noch keine bestätigten Plattformläufe |
| Docker / Compose | YAML geprüft; Build/Start nicht lokal ausgeführt, Docker hier nicht installiert |
| NAS und amd64/arm64-Container | Vorbereitet; konkrete Hardwaretests ausstehend |
| Tailscale Serve / anderes VPN | Anleitungen nach Primärdokumentation; kein echter Fernzugriffstest |
| Brokerzertifikatsprüfung | Deaktiviert; bekannte Sicherheitsgrenze der Alpha |
| Physischer WLAN-Ausfall während eines Drucks | Noch kein gezielt ausgelöster Hardwaretest |

Die CI startet ohne reale Drucker und prüft Container/Healthcheck mit leerer
Ersteinrichtung. Ein konfigurierter Workflow wird erst nach einem tatsächlichen
grünen GitHub-Lauf als bestanden bezeichnet.

## Vor einem öffentlichen Alpha-Release

1. GitHub-CI grün; fehlgeschlagene Plattformen reparieren oder klar ausklammern.
2. Container auf mindestens einem vorgesehenen Server/NAS starten, Datenvolume
   nach Neustart/Update erhalten und beide Drucker lesend prüfen.
3. Zugriff von einem zweiten Gerät über VPN/HTTPS sowie Ablehnung ohne Sitzung
   testen. Proxy muss den Host-Header erhalten. Gerät außerhalb des VPN darf die
   private Adresse nicht erreichen.
4. Zugangscode, private Daten und Git-Historie vor Veröffentlichung prüfen.
5. Read-only-Grenze, Broker-TLS-Grenze und tatsächliche Plattformabdeckung nennen.

Keine Pause/Stop/Temperatur-/Bewegungs-/Upload-/Filamentbefehle für diese Tests.
