# Linux-Testinstaller – technische Vorschau

Stand 09.11.2026: geprüftes Testpaket 0.43.0-alpha.1; Dokumentationskandidat 0.43.0-alpha.2 mit eigenem Abschlussnachweis. Für Linux/amd64 mit lokal vorhandenem Docker Engine und Docker Compose v2. Die praktische Prüfung des jeweiligen Pakets muss sein exaktes Bauprotokoll belegen. Dies ist noch kein natives Windows-/Mac-Paket, kein öffentlich signierter Installer und kein vollständiges Offlinepaket.

## Ein Einstieg

Das vorbereitete Testpaket enthält `Installieren.sh`, das Monitor-Containerabbild einschließlich Python/FFmpeg, die vollständigen Monitor-Quellen, Lizenz-/Fremdhinweise und einen Paketnachweis. Spoolman wird beim ersten Start als offizielles, exakt per Digest festgelegtes Image aus dessen Registry geladen. Dafür ist einmalig Internetzugang nötig. Docker selbst wird nicht automatisch installiert oder umkonfiguriert.

```sh
sh ./Installieren.sh
```

Der Assistent fragt nach einem neuen Installationsordner, Browseradresse, Port und dem ausdrücklich gewählten LAN-Druckerzugang. Standard ist `127.0.0.1:17125`. Die Alternative im Heimnetz muss ausdrücklich eine private IPv4-Adresse des Docker-Rechners sein. Öffentliche und beliebige Bindeadressen wie `0.0.0.0` werden abgewiesen. Die Vorschau verwendet HTTP; für Fernzugriff sind HTTPS/VPN gesondert einzurichten. Die tatsächliche Erreichbarkeit einer gewählten Adresse prüft der Containerstart, keine Routerkonfiguration wird geändert.

Vor der Einrichtung werden Zielsystem, lokaler Docker-Zugang, Compose, Archivprüfsumme und die genaue Image-ID geprüft. Ein abweichendes bereits vorhandenes Image unter derselben Versionskennung wird nicht ersetzt. Quelldateikatalog, Quellarchiv und Image-Anwendungsdateien werden zusätzlich vor dem Paketbau gegeneinander geprüft. Prüfsummen und Image-ID ersetzen keine Herausgebersignatur.

Der Assistent benötigt kein Python auf dem Host. Er ruft die festen Einrichtungsfunktionen im mitgelieferten Monitor-Image auf. Diese kurzlebigen Hilfscontainer haben kein Netzwerk, keine erweiterten Rechte und keinen Docker-Socket. Die dauerhaft laufenden Suite-Dienste erhalten ebenfalls keinen Docker-Socket. Die eigentlichen Docker-Aufrufe laufen über das bereits vom Nutzer bedienbare lokale Container-System.

Nach bestätigtem Start erscheint ein vertraulicher Einrichtungslink. Konto und Passwort legt der Nutzer selbst im Browser an. Der Link wird nicht gespeichert oder übertragen; automatisierte Bauprüfungen halten ihn aus dem Protokoll heraus.

## Vorhandene Installation wieder aufnehmen

```sh
sh ./Installieren.sh start --directory /absoluter/installationsordner
sh ./Installieren.sh status --directory /absoluter/installationsordner
```

`start` prüft die gespeicherte Konfiguration vollständig gegen die vorgesehenen Dienstdefinitionen und die Paketversion. Es verwendet den ursprünglichen Projektnamen, Port und die Adresse. `--no-recreate` erhält laufende Container; gestoppte Dienste können wieder gestartet werden. Das ist keine Aktualisierung auf eine andere Version. Abweichende Versionen oder bearbeitete Dienstdefinitionen werden mit einer verständlichen Meldung abgewiesen. `status` zeigt den vorhandenen Zustand.

Ein bestehender Installationsordner wird bei `install` nicht überschrieben. Ein gescheiterter Start behält Daten und Konfiguration. Weder automatisches Löschen noch eine automatische Versionsumstellung sind in dieser Vorschau enthalten.

## Testumfang und Grenzen

Diese Vorschau verwendet das in [SUITE_TEST.md](SUITE_TEST.md) beschriebene interne Docker-Netz. Im isolierten Modus sind Oberfläche und Spulenverwaltung prüfbar, reale Drucker aber nicht erreichbar. Der ausdrücklich gewählte LAN-Modus verbindet nur den Monitor zusätzlich mit einer ausgehenden Bridge. Der externe Filamentkatalog bleibt in dieser Vorschau abgeschaltet. Sie ersetzt keine produktive Installation und übernimmt keine bestehenden Volumes. Linux-/NAS-Systeme ohne bedienbare Compose-v2-Kommandozeile benötigen später einen eigenen Paketimportweg; die Vorschau setzt diesen Zugang voraus.

Der Bau-VM-Test erstellt ein echtes Installationspaket aus dem gebauten Image, führt das Skript zur Neuinstallation aus und prüft danach Kontoanlage, Spoolman und Bestand. Anschließend ruft er `start` und `status` auf und vergleicht die IDs der laufenden Container. Die doppelte Installation muss ohne Änderung abgewiesen werden. Darauf folgen Neustart mit Datenerhalt und die bereits vorbereitete vollständige Wiederherstellung in frischen Testvolumes.

Der lokale Paketbau erfolgt nach einem erfolgreichen exakten Imagebau mit `scripts/build_suite_test_package.py`. Im endgültigen Serverpaket sollen die gemeinsame Updateführung, begrenzte Sicherungsaufbewahrung, passende Liefer-/Quellnachweise, Herausgebersignierung und ein vollständiger Offlineumfang hinzukommen. Native Windows10/11- und macOS-Pakete bleiben eigene weitere Ziele.


## Entwicklungsstand 0.43: optionaler Druckerzugang

Im Assistenten kann der Druckerzugang bewusst gewählt werden; unbeaufsichtigt mit `--network lan`. Ohne Auswahl bleibt `isolated` aktiv. Nur der Monitor wird zusätzlich mit einer ausgehenden Docker-Bridge verbunden. Spoolman bleibt im internen Netz, Sicherung und Initialisierung ohne Netzwerk. Kein Hostnetz, kein Docker-Socket, kein zusätzlicher Spoolman-Port. Der LAN-Modus ist kein Netzwerkfilter gegen beliebige ausgehende Internetverbindungen des Monitors.

Steuerungsfreigaben sind standardmäßig leer und werden im angemeldeten Monitor je Drucker unter Einrichten festgelegt. Erst ein vollständiger Neustart des Monitor-Containers aktiviert die gespeicherten Änderungen. Kein Docker-Socket in der Webanwendung: Der Benutzer startet den Container über seine Docker-Verwaltung neu. Änderungen an Netzbetrieb oder Version bestehender Projekte sind kein unterstützter automatischer Updateweg.

Das derzeit gebaute Ziel bleibt Linux AMD64. Als zusätzliches Ziel ist Linux ARM64 für Raspberry Pi mit 64-Bit-Betriebssystem vorgesehen. Vorläufiges Leistungsziel: Pi 4 mit 4 GB RAM; 2 GB als zu messende Untergrenze. Pi 3, ARM32 und eine feste Anzahl gleichzeitig nutzbarer Kameras sind nicht freigegeben. ARM64-Abhängigkeitsabbilder, Bau und reale Leistung müssen erst geprüft werden.

## Abgeschlossener 0.43-Pakettest

Python 3.11/3.14 bestanden jeweils 547 Tests und je 14 Bridge-Grenzprüfungen; alle 27 JavaScript-Testdateien bestanden. Neuinstallation über das erzeugte Paket, Anmeldung, Spoolman, Wiederaufnahme ohne Container-Neuanlage, Abweisung doppelter Installation, Neustart und Paarrestore in frische Volumes liefen erfolgreich. LAN-Netzzuordnung mit leerer Druckerliste geprüft. Keine echten Druckerverbindungen oder produktiven NAS-Änderungen. Ein reiner NAS-GUI-Installationsweg und automatische Versionsupdates sind weiterhin offen.
