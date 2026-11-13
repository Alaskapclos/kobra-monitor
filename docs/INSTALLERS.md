# Installationspakete und gemeinsamer Betrieb

Stand 09.11.2026. Die vier nativen Desktop-Testpakete **0.42.0-alpha.1** und das Linux-AMD64-Docker-Testpaket **0.43.0-alpha.1** sind gebaut. Die vier Desktop-Fassungen sind vom Besitzer als funktionierend bestätigt; Docker wurde auf einer getrennten Linux-VM mit künstlichen Daten geprüft. Eine öffentliche Veröffentlichung, vollständige Binärlieferfreigabe oder komfortable allgemeine Updatefunktion ist damit nicht erklärt.

## Paket wählen

| System | Paket und heutiger Ablauf |
| --- | --- |
| Windows mit Intel/AMD | x64-ZIP vollständig entpacken, `Pruefen.cmd`, anschließend `Installieren.cmd`. Python, Spoolman und Kameralaufzeit sind enthalten. |
| Windows ARM | Eigenes ARM64-ZIP mit nativen Bibliotheken und passenden Starthelfern. Kein umbenanntes x64-Paket; unter Windows ARM in Parallels bestätigt. |
| Intel-Mac | Eigene x86_64-App mit gebündelten Laufzeiten; Installation im Benutzerbereich. |
| Apple-Silicon-Mac | Eigene native ARM64-App, gleiche Oberfläche und Datenverträge. |
| Linux, Server, NAS mit Intel/AMD | Gemeinsames Docker-Compose-Testpaket für AMD64. Vorhandene lokale Engine/Compose-v2-Kommandozeile erforderlich; ein allgemeiner NAS-GUI-Assistent fehlt noch. |
| Raspberry Pi / Linux ARM64 | Noch kein geprüftes Komplettpaket. Pi-Abnahme zurückgestellt; nicht durch Desktop-ARM-Tests abgedeckt. |

Für Linux bleibt Docker der bevorzugte Weg über Distributionen hinweg. Es ist kein DEB-Paket als Voraussetzung der ersten Alpha vorgesehen. Unterstützte Container-Laufzeit, Prozessorarchitektur, Netzweg und Schreibrechte müssen passen; kein Versprechen „läuft auf jedem NAS“.

Die nativen Pakete benötigen kein Docker Desktop, keine globale Python-Installation und kein separates FFmpeg auf dem Zielgerät. Windows kann Microsofts C++-Laufzeit benötigen; sie wird getrennt mit Zustimmung und Signaturprüfung angeboten. Mac-Test-Apps sind ad hoc signiert, nicht Developer-ID-signiert oder notarisiert. Die Windows-Test-ZIPs besitzen keine Herausgebersignatur.

[Windows](WINDOWS_TEST_INSTALLER.md) · [Mac](MACOS_TEST_INSTALLER.md) · [Docker](LINUX_TEST_INSTALLER.md) · [Plattformnachweise](PLATFORM_SUPPORT.md)

## Eine Oberfläche, getrennte Komponenten

Monitor und Spoolman bleiben getrennte Programme mit eigenen Datenbanken. Die native Anwendung startet und überwacht eigene Kindprozesse; Browser und interne Dienste verwenden localhost. Der Besitzer legt sein Konto selbst an. Spoolman wird über den angemeldeten Monitor eingebettet und benötigt keinen separat zu merkenden Browserzugang.

Die Server-Suite verwendet ein gemeinsames Compose-Projekt:

- **Monitor:** Oberfläche, Druckeranbindung und bewusst freigegebene Steuerung, eigenes Datenvolume.
- **Spoolman:** festgelegtes offizielles 0.27.0-Abbild, eigenes Datenvolume, kein eigener veröffentlichter Hostport.
- **Sicherung:** kein Netzwerk, Quelldaten nur lesend, eigenes beschreibbares Sicherungsvolume.
- **Einmalige Initialisierung:** ausschließlich neue eigene Volumes vorbereiten; vorhandene fremde Daten nicht übernehmen oder überschreiben.

Standard der technischen Docker-Testinstallation ist ein isoliertes Netz. LAN-Zugang ausdrücklich wählen; nur der Monitor erhält dann eine zusätzliche ausgehende Bridge. Spoolman bleibt intern. Kein Hostnetz und kein Docker-Socket in den Diensten. Für Spoolman wird beim ersten Start Internet benötigt; das ZIP ist noch kein vollständiges Offlinepaket. Ein öffentlicher Zugang wird nicht automatisch eingerichtet.

Die bisherige produktive NAS-Installation nutzt getrennte Projekte. Sie wird nicht automatisch in diese Suite umgewandelt. Keine zweite Instanz auf denselben Volumes starten; vorhandener Spoolman-Bestand darf nicht still durch einen leeren Bestand ersetzt werden.

## Daten und Rechte

Programme und private Daten sind getrennt. Die Anwendung beginnt lesend; Steuerungen je Drucker bewusst freigeben. In nativen 0.42-Paketen und im Docker-LAN-Modus werden diese Rechte privat gespeichert. Erst der vollständige Monitor-Neustart aktiviert Änderungen; bis dahin gelten die bisherigen Freigaben auch bei einem Entzug. [Details](NATIVE_CONTROLS.md).

Die gemeinsame Sicherung prüft Monitor und enthaltenen lokalen Spoolman getrennt durch Wiederherstellung. Es gibt keine gemeinsame atomare Datenbanktransaktion. Eine reine Monitor-Sicherung enthält nicht automatisch eine externe Spoolman-Datenbank. Sicherungen können Kontoangaben, Historien und Originaldateien enthalten und bleiben privat.

## Was Updates heute können

Native 0.42-Pakete können bekannte vollständig gestoppte lokale Profile nach ausdrücklicher Zustimmung in einen neuen Ordner übernehmen. Vorher werden Datenintegrität, Sicherung und isolierte Wiederherstellung geprüft. Die ursprünglichen Daten bleiben erhalten. Die bisherige Ausgangsversion und den Quellordner kontrollieren; separat übernommene Profile werden nicht automatisch als jeweils neuester Stand gesucht. [Übernahme und Rückweg](NATIVE_UPGRADE.md).

Das Linux-Skript `start` nimmt eine vorhandene Installation derselben Version wieder auf, ohne laufende Container neu zu erstellen. Ein abweichendes Image oder eine geänderte Dienstdefinition wird abgewiesen. Das ist kein allgemeiner Versionsupdater. [Suite-Testablauf](SUITE_TEST.md).

## Noch geplanter Komfort

Gewünscht bleibt ein gemeinsamer verständlicher Updatebereich: neue Version und Änderungen anzeigen, Paketquelle/Signatur/Plattform und Speicher prüfen, beide Datenbestände sichern und tatsächlich zurücklesen, vor Dienstunterbrechung aktuellen Druckzustand erneut prüfen, danach Migration und Betrieb kontrollieren. Laufende oder nicht zuverlässig bekannte Druckzustände dürfen nicht als freier Updatezeitpunkt gelten. Keine heimlichen Neustarts und keine Druckerbefehle durch Updates.

Außerdem offen: allgemeiner Restoreassistent, abgestimmte Aufbewahrung mit Platzanzeige, Deinstallation mit standardmäßig erhaltenen persönlichen Daten, einfache NAS-GUI-Installation und sichere Übernahme bestehender Projekte. Diese Ziele beschreiben künftigen Komfort, keine bereits ausgelieferte Funktion.

## Öffentliche Lieferung

Jedes konkrete Binärpaket braucht seinen Dateikatalog, genaue Komponentenherkunft, Original-Lizenztexte und die zur jeweiligen Lizenz passende Quellenbereitstellung. Spoolmans MIT-Lizenz erlaubt nicht pauschal die Weitergabe sämtlicher Abhängigkeiten unter denselben Bedingungen. Python, Bibliotheken, Schriften, FFmpeg und seine aktivierten Komponenten sind zusätzlich zu erfassen.

Die Projektquellen tragen GPL-3.0-only; Fremdhinweise bleiben erhalten. Prüfsummen belegen Integrität, keine Herausgebersignatur. Öffentliche Signierung und Mac-Notarisierung bleiben gesonderte Schritte. Fertige Dateien erst nach Prüfung der genau auszuliefernden Kombination und ausdrücklichem Veröffentlichungsauftrag freigeben.

[Freigabecheckliste](RELEASE.md) · [NOTICE](../NOTICE.md) · [SOURCES.json](../SOURCES.json)
