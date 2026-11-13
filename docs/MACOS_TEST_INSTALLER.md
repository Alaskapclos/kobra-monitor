# Mac-Testinstallation

Stand 09.11.2026: **0.42.0-alpha.1**, getrennte Apps für **Intel (x86_64)** und **Apple Silicon (ARM64)**. Der Besitzer bestätigt beide als funktionierend; das Intel-Testgerät ist ein iMac mit macOS 15.8.2. Die Paket-Mindestversion bleibt maßgeblich; daraus folgt keine Abnahme sämtlicher macOS-Versionen.

## Installieren

1. Passendes Paket vollständig in einen lokalen Ordner entpacken.
2. **Kobra Monitor Test.app** öffnen. Die App nennt ihren eigenen Programm- und Datenbereich. Programme werden versionsgebunden im eigenen Programme-Ordner installiert, ohne andere Testversionen ungefragt zu ersetzen.
3. Falls macOS eine Freigabe verlangt, die Meldung und **Systemeinstellungen → Datenschutz & Sicherheit** prüfen. Die App ist für diese Vorschau ad hoc signiert, nicht Developer-ID-signiert oder notarisiert. Sicherheitsattribute und Schutzfunktionen werden nicht entfernt oder deaktiviert.
4. Eigenes Besitzerkonto im Browser einrichten, Drucker bewusst hinzufügen und einen von macOS erfragten lokalen Netzwerkzugriff erlauben.
5. Zum Beenden die App-Funktion zum vollständigen Stoppen verwenden. Das Schließen des Browsers genügt nicht.

Python 3.14.10, die festgelegten Bibliotheken, Spoolman 0.27.0 einschließlich Oberfläche sowie FFmpeg/FFprobe sind enthalten. Docker Desktop, Homebrew, Xcode und eine globale Python-Installation sind auf dem Zielgerät nicht erforderlich. Die internen Dienste lauschen auf localhost; Spoolman hat zusätzlich einen zufälligen internen Zugang und wird über den angemeldeten Monitor geöffnet. Vorhandene NAS-Daten werden nicht importiert.

Der GUI-Prozess bleibt während des Betriebs bestehen und überwacht seine eigenen Kindprozesse. Er enthält die Erklärung für lokalen Netzwerkzugriff. Eine reine Terminal-Netzwerkdiagnose ersetzt nicht die macOS-Freigabe der App.

## Steuerungen und vorhandene Daten

Neue Installationen beginnen lesend. Funktionen je Drucker unter **Einrichten → Steuerung freigeben** wählen und bestätigen. Nach vollständigem Beenden und erneutem Start gelten die neuen Rechte; bis dahin gelten auch bei einem Entzug die bisherigen Freigaben. [Bedienung](NATIVE_CONTROLS.md).

0.42 enthält die bestätigte Übernahme bekannter vollständig gestoppter lokaler Profile in einen neuen Datenordner. Vorher werden Sicherung und isolierte Wiederherstellung geprüft. Ausgangsordner und Version kontrollieren; ein bereits separat übernommenes 0.40-Profil wird nicht automatisch als neuester Datenstand gesucht. Alte und neue Datenstände werden nicht synchronisiert. [Übernahme und Rückweg](NATIVE_UPGRADE.md).

Nach der Einrichtung werden Monitor und der enthaltene lokale Spoolman gemeinsam gesichert und getrennt zurückgelesen. Jede Datenbank ist konsistent, beide besitzen keine gemeinsame atomare Transaktion. Externe Spoolman-Bestände benötigen eigene Sicherungen. Allgemeiner Versionsupdater, komfortable Wiederherstellungsoberfläche und begrenzte Aufbewahrung bleiben offen.

## Nachweis und Grenzen

Die ARM-Integration lief auf einem Apple-Silicon-Baugerät; die Intel-Integration unter bereits vorhandenem Rosetta. Geprüft wurden Konto, Spoolman mit künstlichem Bestand, Start/Stop, Mehrfachstartschutz, 0.40→0.42-Übernahme, Datenerhalt und Paarrestore. Keine echten Druckerverbindungen in diesen Integrationstests. Die Besitzerberichte auf den Zielgeräten sind davon getrennte Nachweise.

Intel benötigt für festgelegte Cryptography-Versionen eigene, nachvollziehbare Quellbauten mit OpenSSL; Apple Silicon hat seine eigene Kamerabaukette. Die Architektur jeder nativen Bibliothek wird geprüft. Ein Dateiname oder eine Ad-hoc-Signatur allein ist kein Herkunfts-/Lizenznachweis. Vor öffentlicher Binärfreigabe bleiben vollständige Lieferprüfung und Herausgebersignierung/Notarisierung offen. [ARM-Bau](NATIVE_ARM.md) · [Plattformmatrix](PLATFORM_SUPPORT.md).
