# Getrennte Server-/NAS-Suite – Entwicklungsprüfung

Stand 09.11.2026. Der beschriebene isolierte Suite-Test bestand im Docker-Bau 0.43.0-alpha.1. Dieser Bereich ist für die isolierte Bau-VM vorbereitet. Er ist kein öffentlich freigegebener Komplettinstaller und wird nicht auf bestehende NAS-Projekte angewandt. Den bestandenen Praxistest muss das Bauprotokoll für den exakten Quellstand separat belegen.

## Eigenes Testprojekt

```sh
python suite_cli.py prepare-test-project ./new-suite-test --monitor-image kobra-monitor:EXACT_VERSION
```

Das Werkzeug schreibt `suite.json` und `compose.json` in einen neuen Ordner. Ein bereits vorhandener Ordner wird abgewiesen. Der Projektname wird zufällig mit dem Präfix `kobra-suite-test-` erzeugt; Datenvolumes sind ausschließlich diesem Projekt zugeordnet. Es gibt keine externen Volumes und keine Verbindung zu bestehenden Monitor-/Spoolman-Projekten.

Die öffentliche Konfiguration enthält keine Zugangsdaten. Sie ist für die Container lesbar und dort nur lesend eingebunden. Änderungen an den vorgesehenen Dienstdefinitionen werden bei der Offline-Wiederherstellung abgewiesen.

## Dienste und Abgrenzung

- **Initialisierung:** Einmaliger netzwerkloser Prozess. Er richtet ausschließlich leere Volumes ein, kennzeichnet sie mit Projekt und Zweck und vergibt die interne Benutzerkennung 10001. Vorhandene unmarkierte Daten oder fremde Kennungen werden abgewiesen. Bereits passende Daten werden weder rekursiv umgeschrieben noch neu konfiguriert.
- **Monitor:** Nutzt sein eigenes Datenvolume und bleibt standardmäßig ohne Steuerungsfreigaben. Für die Testinstallation wird nur ein getrennter Loopback-Port veröffentlicht, standardmäßig 17125.
- **Spoolman:** Offizielles Image 0.27.0, auf einen genauen linux/amd64-Manifestdigest festgelegt. Eigener Datenbereich, Start als Benutzer 10001 und Datenpfad `/data`. Der Start erfolgt direkt über den unveränderten enthaltenen Uvicorn-Server, damit keine Benutzeränderung im schreibgeschützten Container nötig ist. Kein eigener Hostport. Die Verbindung `http://spoolman:8000/spoolman` ist im Monitor vorbereitet.
- **Sicherung:** Netzwerkloser Prozess, der beide Quellen nur lesend einbindet. Er wartet auf die erste Druckereinrichtung und eine vorhandene Spoolman-Datenbank. Danach entsteht eine gemeinsame Sicherung mit isolierter Wiederherstellungsprüfung. Die erzeugte Compose-Konfiguration ist darin enthalten. Nach einer erfolgreichen Prüfung wird der Zeitpunkt im laufenden Prozess zwischengespeichert, damit nicht jede Minute erneut alle Archive wiederhergestellt werden.

Das Testnetz ist ausdrücklich `internal`. Damit kann die Testinstallation keine realen Drucker oder Internetdienste erreichen. Der externe Filamentkatalog ist in dieser isolierten Testkonfiguration abgeschaltet. Diese Einschränkung gehört zur Entwicklungsprüfung und ist keine endgültige Festlegung für das später nutzbare Serverpaket. Auch am Docker-Host selbst sind die drei internen Dienste nicht durch veröffentlichte Einzelports freigegeben; Docker-Administratoren behalten technisch Zugriff auf ihre Container.

Die Vorschau löscht keine alten Sicherungsstände automatisch. Eine geprüfte Aufbewahrung mit begrenzter Anzahl und verständlicher Platzanzeige ist noch zu integrieren.

Der Sicherungsdienst meldet seine Prozessbereitschaft über eine eigene frische Statusdatei im flüchtigen Containerbereich. Warten auf die Ersteinrichtung ist ein erreichbarer Dienst, aber noch kein Nachweis einer vorhandenen Sicherung. Ein Sicherungsfehler oder länger ausbleibende Statusaktualisierung macht die Bereitschaftsprüfung negativ. Dadurch kann der gemeinsame Startablauf alle laufenden Dienste prüfen, ohne eine erfolgreiche Sicherung vorzutäuschen.

## Offline-Wiederherstellung

```sh
python suite_cli.py restore-offline /path/to/snapshot --target /path/to/new-offline-folder
```

Das Ziel muss neu sein und außerhalb der Sicherung liegen. Beide Datenbanken werden geprüft und in `monitor-data` und `spoolman-data` wiederhergestellt. `recorded-suite.json` und `recorded-compose.json` bewahren die ursprüngliche Dienste-Konfiguration. Diese Dateien heißen absichtlich nicht wie eine automatisch startbare Compose-Datei: Ein späterer Start darf nicht versehentlich wieder die alten Projektvolumes verwenden.

Der Befehl startet keine Dienste und ersetzt keine produktiven Daten. Der spätere Installationsassistent muss den Import in neue bzw. ausdrücklich gewählte, gestoppte Volumes und die Rückkehr auf passende Images übernehmen. Der eigene Bau-VM-Test verwendet dafür ausschließlich frische Testvolumes mit neuen Projektkennungen.

## Tatsächlicher Containertest

`scripts/test_suite_container.py` verweigert den Start ohne die Kennzeichnung `/etc/kobra-build-vm`. Der feste Bauhelfer kann es nach den normalen Image-/Unit-Prüfungen aufrufen. Das Skript:

1. prüft die erzeugte Compose-Datei und startet ein frisches, isoliertes Projekt;
2. legt ausschließlich ein bekanntes Testkonto, einen Testauftrag und eine Testspule über die echte eingebettete Spoolman-API an;
3. prüft Anmeldung, geschützten Zugriff, Originaloberfläche und die Restmenge 470 g;
4. startet dieselben Dienste mit erhaltenen Volumes neu und prüft die Daten erneut;
5. sichert beide Datenbanken und die Konfiguration, stellt sie in frische Volumes eines zweiten Testprojekts wieder her und startet die wiederhergestellten Dienste;
6. entfernt ausschließlich die beiden zufällig benannten Testprojekte und deren Testvolumes.

Ein erfolgreicher Lauf schreibt `SUITE_CONTAINER_PROOF` ins Bauprotokoll. Ein solcher Nachweis darf erst nach tatsächlichem Abschluss behauptet werden. Der Test verwendet das auf der Bau-VM vorhandene Compose oder ersatzweise ein offizielles Docker-CLI-Testimage; dieses gehört nicht zum auszuliefernden Suite-Paket. Es erhält den Docker-Socket ausschließlich innerhalb der ohnehin privilegierten, getrennten Bau-VM. Kein Docker-Socket wird an einen Suite-Dienst weitergegeben.

## Noch keine endgültige Auslieferung

Offen bleiben Paketassistent und gemeinsame Updateführung, geprüfte Aufbewahrung, Import bestehender Installationen, konkrete Lizenz-/Quellpakete aller ausgelieferten Binärdateien, Herausgebersignierung sowie Windows-/macOS-Installer. Windows-Ziele sind Windows 10/11; die Laufzeit Python 3.14 setzt Windows 10 oder neuer voraus. Windows 8/8.1 sind kein Ziel. Der Intel-Mac-Test ist auf macOS 15.8.2 vorgesehen.

Quellen: [Python unter Windows](https://docs.python.org/3/using/windows.html), [Microsoft-Supportzeiträume](https://www.microsoft.com/en-us/windows/end-of-support), [Spoolman-Konfiguration](https://github.com/Donkie/Spoolman/wiki/Configuration), [Quellstand des verwendeten Spoolman-Images](https://github.com/Donkie/Spoolman/tree/bed3f14ee77a3a571d31b14215d54b0b88a7519c).

## Optionaler LAN-Modus ab 0.43

Das obige interne Netz bleibt Standard der isolierten Entwicklungsprüfung. Der Installer kann ausdrücklich `lan` wählen. Dann erhält ausschließlich der Monitor eine zweite ausgehende Bridge, ohne Hostnetz oder Docker-Socket. Spoolman bleibt intern; Initialisierung und Sicherung ohne Netzwerk. Der zusätzliche echte Container-Netztest startet mit leerer Druckerliste und prüft diese Zuordnung sowie den lesenden Standard. Er ersetzt keine reale Drucker-/Kameraabnahme.
