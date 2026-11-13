# Kobra Monitor

**Drucker beobachten, Spulen verwalten und bewährte Drucke wiederholen – in einer gemeinsamen Oberfläche.**

Kobra Monitor verbindet sich im Heimnetz mit **Anycubic Kobra S1 mit unveränderter Firmware und aktiviertem LAN-Modus**. Du öffnest ihn im Browser auf Computer, Tablet oder Handy. Ein Anycubic-Cloudkonto ist dafür nicht nötig.

Neue Modelle werden weiterhin in OrcaSlicer oder Anycubic Slicer Next geslicet und zum Drucker geschickt. Der Monitor übernimmt Übersicht, Historie, Berichte, Spulenverwaltung und ausdrücklich freigegebene Steuerungen. Erfolgreich abgeschlossene Drucke lassen sich mit einem passenden archivierten Original später direkt aus dem Monitor erneut starten.

**Entwicklungsstand: 0.43.0-alpha.6 – Vorabversion.** Die zuletzt vom Besitzer erprobten Desktop-Pakete tragen Version **0.42.0-alpha.1**, das getestete Docker-Paket **0.43.0-alpha.1**. Diese Pakete werden durch die Dokumentationsüberarbeitung nicht nachträglich verändert. Ein neuer Download gilt erst nach seinem eigenen Bau- und Prüfnachweis als geprüft. [Prüfstand](docs/VALIDATION.md) · [Paketübersicht](docs/PLATFORM_SUPPORT.md) · [Freigabestand](docs/RELEASE.md)

## Was kann der Monitor?

- **Übersicht:** eigener Status, Fortschritt, Restzeit, Temperaturen, Lüfter, Licht und Speed Mode je Drucker. Veraltete Werte werden gekennzeichnet.
- **Kameras:** Einzelansicht mit Vergrößerung oder mehrere Drucker nebeneinander; am Handy untereinander. Es wird kein Video aufgezeichnet.
- **ACE und Spulen:** Slotbelegung, Material und verfügbare Restmengen, Temperatur, Luftfeuchte und Trocknungszustand. Die originale Spoolman-Verwaltung ist in die Oberfläche eingebettet.
- **Druckaufträge:** Historie, Temperaturverlauf, Kundenauftragsnummern, manuelle Qualitätsabnahme und feste Berichtsversionen als PDF, JSON, Markdown oder ZIP.
- **Dateiarchiv:** Originaldateien mit Bild-, 3D- oder Druckbahn-Vorschau, soweit die Datei geeignete Daten enthält. Erfolgreiche Aufträge mit geprüftem Original können erneut gedruckt werden.
- **Optionale Steuerung:** Licht, Lüfter, Speed Mode, Solltemperaturen, Pause/Fortsetzen/Abbruch, Achsen/Homing/Motoren-Aus und ACE-Trocknung. Neue Installationen beginnen lesend; Funktionen werden je Drucker bewusst freigegeben.
- **Betrieb:** lokales Besitzerkonto, Diagnose, Sicherung und optionale Push-Meldungen. Fernzugriff über eigenes VPN und HTTPS.

## Welches Paket brauche ich?

Die vorgesehenen Downloads stehen nach ihrer Freigabe unter [GitHub Releases](https://github.com/Alaskapclos/kobra-monitor/releases). Lade das **fertige Paket für dein Gerät**, wenn du eine Anwendung installieren möchtest. GitHubs Schaltfläche **Code → Download ZIP** enthält Quellcode und ersetzt keinen vollständigen Installer.

| Dein Gerät | Passende Fassung | Aktueller Teststand |
| --- | --- | --- |
| Windows-PC mit Intel- oder AMD-Prozessor | Windows **x64** | 0.42 gebaut; Funktion vom Besitzer bestätigt, unter Windows 10 x64 getestet |
| Windows-Gerät mit ARM-Prozessor, auch Windows ARM in Parallels | Windows **ARM64** | 0.42 nativ gebaut; Funktion einschließlich dauerhafter Steuerungsfreigaben vom Besitzer bestätigt |
| Mac mit Intel-Prozessor | macOS **Intel / x86_64** | 0.42 gebaut; Besitzer bestätigt Funktion auf dem Intel-iMac |
| Mac mit M1 oder neuerem Apple-Chip | macOS **Apple Silicon / ARM64** | 0.42 nativ gebaut; Funktion vom Besitzer bestätigt |
| Linux-Rechner, Server oder NAS mit Intel-/AMD-Prozessor | Linux **AMD64 mit Docker Compose** | 0.43-Testpaket einschließlich Neuinstallation, Neustart und Wiederherstellung auf der Linux-Bau-VM geprüft |
| Raspberry Pi oder anderer ARM-Linux-Rechner | Linux **ARM64** | Geplant; noch kein geprüftes Installationspaket. Raspberry-Pi-Tests sind zurückgestellt |

**AMD64 bedeutet hier 64-Bit-Intel/AMD, nicht ARM64.** Das Linux-AMD64-Paket läuft nicht auf einem Raspberry Pi. Ein Windows-ARM-Paket ist ebenfalls kein Linux-/Pi-Paket.

Windows und Mac bringen Python, Spoolman und die Kameralaufzeit mit; Docker Desktop und eine eigene Python-Installation sind dafür nicht nötig. Die bisherigen Mac-Testpakete sind ad hoc signiert, aber noch nicht mit Apple Developer ID signiert oder notarisiert. Die Windows-Testpakete haben noch keine Herausgebersignatur. Die öffentliche Binärfreigabe und vollständigen Liefernachweise bleiben ein eigener Schritt. [Details zur Plattformprüfung](docs/PLATFORM_SUPPORT.md)

Der neue native Paketkandidat 0.43.0-alpha.6 übernimmt die bereinigten Bibliotheken und bietet die getrennte Datenübernahme auch aus 0.42 an. Bau und Gesamtprüfung werden für jede konkrete Lieferdatei gesondert nachgewiesen; die bisherigen Besitzerabnahmen gelten weiter ausschließlich für die oben genannten alten Pakete.

## Windows: installieren und starten

1. Passendes x64- oder ARM64-Paket vollständig in einen lokalen Ordner entpacken.
2. Im enthaltenen Programmordner zuerst **Pruefen.cmd** öffnen. Die Prüfung sendet keine Druckerbefehle.
3. **Installieren.cmd** starten und die angezeigten Programm- und Datenordner prüfen. Falls erforderlich, wird Microsofts C++-Laufzeit nach Prüfung der Herausgebersignatur angeboten.
4. Den angelegten Starter öffnen. Im Browser dein eigenes Konto einrichten und die Drucker hinzufügen.
5. Zum vollständigen Beenden den mitgelieferten Beenden-Starter verwenden. Nur den Browser zu schließen beendet den Monitor nicht.

Das Windows-Paket ist eine lokale Anwendung mit Browseroberfläche. Vorhandene NAS-Daten werden nicht automatisch übernommen. [Windows-Anleitung](docs/WINDOWS_TEST_INSTALLER.md)

## Mac: installieren und starten

1. Das Paket für **Intel** oder **Apple Silicon** vollständig entpacken.
2. **Kobra Monitor Test.app** öffnen. Der Installationsdialog zeigt den eigenen Programm- und Datenbereich; andere Installationen werden nicht ungefragt ersetzt.
3. Falls macOS eine Freigabe verlangt, die Meldung und **Systemeinstellungen → Datenschutz & Sicherheit** prüfen. Die App entfernt keine Sicherheitsattribute.
4. Im Browser das eigene Konto einrichten und Drucker hinzufügen. Einen lokalen Netzwerkzugriff, nach dem macOS fragt, bewusst erlauben.
5. Zum vollständigen Beenden die Beenden-Funktion der App verwenden; der Browser allein beendet die Dienste nicht.

Die Kamera benötigt auf dem Anzeige-Handy keine zusätzliche Installation. FFmpeg ist in der Mac-Test-App enthalten. [Mac-Anleitung](docs/MACOS_TEST_INSTALLER.md)

## Linux, Server und NAS: Docker

Das gemeinsame Projekt betreibt **Monitor, Spoolman und Sicherung in getrennten Containern**. Ein einmaliger Einrichtungsschritt bereitet ausschließlich neue Datenvolumes vor. Für dich gibt es eine gemeinsame Oberfläche.

Voraussetzung: vorhandenes Docker Engine und Docker Compose v2 auf einem passenden Linux-AMD64-System. Die Testfassung benötigt eine bedienbare lokale Compose-Kommandozeile; ein einfacher Importassistent für beliebige NAS-Oberflächen ist noch nicht fertig.

Nach vollständigem Entpacken des fertigen Linux-Pakets:

```sh
sh ./Installieren.sh
```

Der Assistent fragt nach einem **neuen Installationsordner**, Browseradresse, Port und Druckerzugang. Standard ist `127.0.0.1:17125` und ein isoliertes Testnetz. Soll der Monitor echte Drucker erreichen, den **LAN-Zugang ausdrücklich wählen**. Nur der Monitor erhält dafür eine zusätzliche Netzwerkverbindung; Spoolman bleibt intern und der Sicherungsdienst ohne Netzwerk.

Für den Browserzugriff von einem anderen Gerät die private IPv4-Adresse des Linux-/NAS-Rechners wählen. Die Testfassung verwendet HTTP im vertrauten Heimnetz; HTTPS/VPN werden gesondert eingerichtet. Spoolman wird beim ersten Start als exakt festgelegtes offizielles Image geladen; dafür ist einmalig Internet nötig. Das Paket ist daher noch kein vollständiges Offlinepaket.

Bestehende produktive NAS-Projekte und ihre Volumes werden nicht automatisch übernommen oder ersetzt. [Docker-Testinstallation](docs/LINUX_TEST_INSTALLER.md) · [Gemeinsame Suite](docs/SUITE_TEST.md) · [UGREEN/UGOS](docs/UGREEN_UGOS.md)

## Erste Einrichtung im Browser

1. **Konto anlegen:** den vertraulichen Einrichtungslink öffnen und Benutzername sowie eigenes Passwort wählen. Keine Zugangsdaten in Issues oder Screenshots veröffentlichen.
2. **Drucker hinzufügen:** LAN-Modus am S1 einschalten und seine lokale IP-Adresse unter **Einrichten** speichern. Der Rechner mit dem Monitor muss den Drucker erreichen können.
3. **Spulen erfassen:** unter **Spulen → Spulen verwalten** Hersteller, Filamente und Spulen in Spoolman pflegen. Danach die passenden Spulen unter **ACE & Zuordnung** zuweisen.
4. **Kamera öffnen:** in der Übersicht den gewünschten Drucker wählen und **Kamera anzeigen** anklicken. Die Kamera muss bereits ihren lokalen Stream bereitstellen; der Monitor aktiviert sie nicht selbst.
5. **Steuerung freigeben:** nur bei Bedarf unter **Einrichten → Steuerung freigeben → Freigaben bearbeiten** die gewünschten Funktionen je Drucker wählen und bestätigen. In den nativen Paketen und der LAN-Docker-Suite gelten Änderungen erst nach vollständigem Neustart des Monitors beziehungsweise Monitor-Containers. Bis dahin gelten auch bei einem Entzug die bisherigen Freigaben.

Licht schaltet direkt. Andere Steuerungen haben ihre passenden Bestätigungen. **Manuelle Achsenfahrten und Homing nur direkt vor dem Drucker verwenden**, mit freiem Fahrweg und ausreichendem Abstand zwischen Düse und Druckbett. Die Kamera ersetzt diese Anwesenheit nicht. [Bedienung](docs/BEDIENUNG.md) · [Steuerungsfreigaben](docs/NATIVE_CONTROLS.md) · [Bewegung](docs/MOTION_CONTROL.md)

## Originaldateien ins Archiv übernehmen

Der Monitor lädt Druckdateien nicht automatisch vom Drucker zurück. Für eine zusätzliche Archivkopie gibt es einen **separat einzurichtenden Helfer auf dem Slicer-Computer**. Praktisch geprüft ist bisher der macOS-Sendecache von Anycubic Slicer Next. Ein ausdrücklich gewählter Exportordner ist ebenfalls vorgesehen; eine universelle automatische Orca-/Windows-Cacheübernahme ist nicht zugesagt. Die Helfereinrichtung benötigt einen dauerhaft verfügbaren Python-Interpreter; sie ist ein optionaler zusätzlicher Schritt zur nativen Monitor-App. [Helfer einrichten und Eingang prüfen](docs/FILE_ARCHIVE.md).

Erst ein bestätigter Archiveingang mit passender Zuordnung ist ein verfügbares Original. Ein Dateiname in der Historie oder ein Druckbericht allein genügt nicht.

## Einen erfolgreichen Druck wiederholen

Unter **Druckaufträge** einen erfolgreichen Auftrag mit zugeordnetem Archivoriginal öffnen und **Druck wiederholen** wählen. Zielgerät und Materialslots prüfen, danach das Original übertragen. Erst eine zweite bewusste Bestätigung startet den Druck. Druckbett, Material und eingebaute Düse müssen passen; die ursprünglichen Slicer-Einstellungen bleiben erhalten.

Die erprobte Konfiguration ist ein Stock-Kobra-S1 mit einem direkt angeschlossenen Vier-Slot-ACE und einer Druckplatte. Ein erfolgreicher Archivwiederholungsdruck ist vom Besitzer bestätigt; weitere Geräte-/Dateikonfigurationen sind damit nicht pauschal abgenommen. Bei unklarem Ausgang gibt es keinen automatischen erneuten Start. [Ablauf und Grenzen](docs/REPRINT.md)

## Daten sichern und aktualisieren

Programmdateien und persönliche Daten sind getrennt. **Monitor und Spoolman haben eigene Datenbanken; eine reine Monitor-Sicherung ersetzt keine Spoolman-Sicherung.** Die Komplettpakete besitzen einen gemeinsamen Sicherungsweg mit getrennt geprüften Datenbanken. Eine zusätzliche Kopie außerhalb des Geräts bleibt sinnvoll.

Vor einem Update die Sicherung prüfen und das bisherige Paket behalten. Für die nativen 0.42-Testpakete ist eine bestätigte Übernahme bekannter, vollständig gestoppter lokaler Testprofile vorgesehen: prüfen, sichern, getrennt wiederherstellen und in einen neuen Datenordner kopieren. Die alte Installation bleibt erhalten. Bereits separat übernommene Profile werden nicht automatisch als jeweils neuester Stand gesucht; **Quellordner und Version im Dialog kontrollieren**. Die beigelegten profilbezogenen Starter nur für den dazu passenden bisherigen Datenordner verwenden.

Es gibt **noch keinen allgemeinen automatischen Update- oder Wiederherstellungsassistenten**. Das Docker-Skript `start` nimmt dieselbe Installation wieder auf und ist kein Versionsupdate. Bei Docker die Datenvolumes erhalten; `docker compose down -v` würde sie löschen. Eine alte Programmversion niemals ungeprüft mit bereits migrierten Daten starten.

[Datensicherung](docs/BACKUPS.md) · [Native Datenübernahme](docs/NATIVE_UPGRADE.md) · [Updates und Rückweg](docs/UPDATE_RECOVERY.md)

## Handy und Fernzugriff

Im Heimnetz dieselbe Monitor-Installation im Handy-Browser öffnen. Von unterwegs zuerst das eigene VPN, beispielsweise Tailscale, verbinden und die private HTTPS-Adresse verwenden. Der Monitor-Rechner muss eingeschaltet bleiben. Eine öffentliche Router-Portfreigabe ist nicht vorgesehen.

Optionale Push-Meldungen benötigen HTTPS und eine eigene Browserfreigabe auf jedem Gerät. Auf iPhone/iPad die Oberfläche als Home-Bildschirm-App verwenden. [Fernzugriff](docs/REMOTE_ACCESS.md) · [Benachrichtigungen](docs/NOTIFICATIONS.md)

## Bekannte Grenzen

- Bestätigtes Druckende ist keine automatische Qualitätsprüfung des Bauteils. Verbindungsverlust bedeutet kein Druckende; frühe Restzeiten während Vorbereitung können unbrauchbar sein.
- ACE-Prozente stammen vom Drucker, Grammwerte aus dem Spoolman-Buchbestand. **Kein automatischer Verbrauch und keine gemessene Materialbilanz.** Ein Materialvorrat-Hinweis ist eine Schätzung.
- Gemeinsame Hersteller-SKU identifiziert nicht eine einzelne Spule. Nur nachweislich individuelle Kennungen automatisch wiedererkennen; sonst Slots bewusst manuell zuordnen. Kein integriertes NFC-Schreiben und kein automatischer ReSpool-Bibliotheksabgleich.
- Ein lokales Besitzerkonto je Installation; keine getrennten Benutzerrollen. Drucker-TLS verschlüsselt die Verbindung, überprüft aber die Brokeridentität nicht. Nur im vertrauenswürdigen Druckernetz betreiben.
- Nicht alle Firmware-, ACE-, Betriebssystem- und NAS-Kombinationen sind geprüft. Raspberry Pi/ARM-Linux, allgemeine Auto-Updates und öffentliche Installer-Signierung sind noch offen.

[Prüfstand und reale Abnahmen](docs/VALIDATION.md) · [Sicherheitsbeschreibung](SECURITY.md) · [Projektplan](ROADMAP.md)

## Für Entwickler

Der Quellstart ist ein eigener Weg und benötigt Python sowie FFmpeg. Er startet zunächst den Monitor; Spoolman wird separat angebunden. Die nativen Komplettpakete oben ersparen diese Einrichtung.

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python monitor.py --open
```

Unter Windows liegt Python unter `.venv\Scripts\python.exe`. Quellprüfungen:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python vendor/kobra-bridge/test_read_only.py
python scripts/release_check.py
```

Zusätzlich alle `tests/test_*.js` mit Node ausführen. Der eingefrorene Docker-Stand 0.43.0-alpha.1 bestand unter Python 3.11 und 3.14 jeweils 547 Python-Tests, jeweils 14 Bridge-Grenzprüfungen und alle 27 JavaScript-Testdateien. Die Dokumentationsfassung 0.43.0-alpha.2 benötigt ihren eigenen abschließenden Quell-/Paketnachweis. Historische CI-Erfolge ersetzen keinen aktuellen Build; ein Test ohne reale Drucker ist keine Hardwareabnahme.

## Lizenz und Herkunft

**GPL-3.0-only** für Kobra Monitor. Die ursprünglichen Lizenzen und Copyright-Hinweise mitgelieferter Fremdsoftware bleiben erhalten. Grundlage sind unter anderem `cluzl/kobra-bridge` (GPL-3.0) und `rvanderp3/kobra-connect` (Apache-2.0); Spoolman bleibt ein eigenständiger MIT-lizenzierter Dienst. Die Lizenzen aller Abhängigkeiten sind zusätzlich zu beachten.

[LICENSE](LICENSE) · [NOTICE](NOTICE.md) · [Quellenverzeichnis](SOURCES.json) · [Fremdcode-Anpassungen](docs/UPSTREAM.md) · [Freigabecheckliste](docs/RELEASE.md) · [Lizenzen für die Auslieferung](docs/DISTRIBUTION_LICENSES.md)

Das Projekt ist unabhängig von Anycubic und den genannten Slicer-/App-Anbietern. Zugangsdaten, Sicherungen, persönliche Druckarchive und Laufzeitdaten gehören weder ins Repository noch in öffentliche Supportberichte.

Die frühere Windows-ARM-Funktionsbestätigung ist ein Besitzerbericht. Ein späterer Profilvergleich zeigte getrennte Datenstände aus 0.41 und 0.42; die damals tatsächlich geöffnete Version wurde nicht unabhängig protokolliert. Die Datenübernahme des neuen Pakets wird deshalb separat geprüft.
