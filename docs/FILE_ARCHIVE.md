# Originaldateien privat archivieren

Der gewohnte Ablauf bleibt: In Anycubic Slicer Next slicen und direkt zum Drucker senden bzw. starten. Ein unabhängiger Helfer auf dem Slicer-Computer kopiert die fertigen `.gcode.3mf`-Pakete zusätzlich zum Monitor. Er ändert weder Slicerdateien noch Drucker und führt keine Druckerbefehle aus.

## Einrichtung auf macOS

1. Im angemeldeten Monitor unter **Druckaufträge → Druckdatei-Archiv → Computer verbinden** einen Computerzugang erstellen. `archive-client.json` privat aufbewahren. Der Zugang erlaubt nur Originaldatei-Eingang und Helferstatus; keine Downloads, Kontoverwaltung oder Druckersteuerung.
2. Mit Python 3.11 oder neuer `python3 helpers/install_archive_client.py /Pfad/zur/archive-client.json` aus dem entpackten Monitorpaket ausführen. Das richtet den privaten Helfer unter `~/Library/Application Support/Kobra Monitor Archive` und einen Dienst für die Benutzeranmeldung ein. Der Computer muss angemeldet sein. Ein dauerhaft verfügbarer Python-Interpreter wird benötigt.
3. Beim nächsten selbst gestarteten Slicer-Auftrag im Monitor den Eingang kontrollieren. Der Helfer überspringt bei seiner allerersten Initialisierung bereits vorhandene Cache-Dateien. Es erfolgt kein stiller Import aller früheren Modelle.

Der automatische Cache-Helfer ist zunächst für den beobachteten macOS-Sendecache von Anycubic Slicer Next vorgesehen (`ACGcode3mf` im temporären Benutzerverzeichnis, eine Unterordnerebene). Dieser interne Slicerpfad ist keine zugesicherte öffentliche Schnittstelle. Nach Slicerupdates muss der reale Eingang erneut geprüft werden. Ein expliziter Exportordner kann über `archive_client.py --source … --config … --queue …` gewählt werden; eine darin gespeicherte fertige Druckdatei wird ebenso verarbeitet. Der reguläre Slicer-Postprocessing-Hook wird nicht verwendet: Er kann lediglich vorläufigen rohen G-Code sehen.

## Was „archiviert“ bedeutet

Der Helfer wartet auf zwei unveränderte Dateibeobachtungen, kopiert das Paket in seine dauerhafte Warteschlange, prüft ZIP-Inhalt und CRC und berechnet SHA-256. Das NAS prüft Größe, SHA-256 und Paket erneut. Erst nach dauerhaftem Speichern und bestätigter Antwort markiert der Helfer die Übertragung als angenommen. Dateien mit gleichem Inhalt werden zusammengefasst; gleicher Name mit anderem Inhalt ergibt eine eigene Originaldatei.

Ohne NAS bleibt die lokale Kopie ausstehend und wird später erneut angeboten. Nur Archivübertragungen werden wiederholt, niemals ein Druckstart. Bestätigte lokale Kopien werden zunächst ebenfalls behalten. Der Monitor zeigt fehlende aktuelle Helferrückmeldungen und blockierte und ausstehende Übertragungen; der Helferstatus ist keine Aussage über einen tatsächlich laufenden Druck.

Der Computer muss für die Übernahme laufen und der Helfer muss aktiv sein. Wenn eine Datei vor der Übernahme verschwindet oder der Slicer seinen Cacheort ändert, kann keine vollständige Erfassung zugesagt werden. Ein Druckbericht oder ein gemeldeter Dateiname allein gilt deshalb nie als Originaldatei-Nachweis. Der echte nächste Slicerauftrag ist die abschließende Praxisabnahme.

## Berichte, Zuordnung und Wiederverwendung

Originale sind unter **Druckaufträge** herunterladbar. Im Auftrag lässt sich eine geprüfte Datei ausdrücklich zuordnen. Bei abgeschlossenen Aufträgen entsteht eine neue feste Berichtsversion mit Inhaltshash, Größe und dem Hinweis auf die manuelle Zuordnung. Frühere Berichtsversionen bleiben unverändert. Eine Zuordnung beweist nicht unabhängig, welche Bytes der Drucker tatsächlich ausgeführt hat.

Der Berichte-ZIP-Export enthält weiterhin die Berichtsdokumente und das Prüfmanifest. Die Originaldatei wird separat heruntergeladen und ist durch die im Bericht gespeicherte SHA-256 eindeutig zuordenbar. Ein erneuter Druckstart aus dem Monitor ist in dieser Archivversion noch nicht enthalten.

## Sicherung und Grenzen

Originale, Dateinamen, Zuordnungen und gehashte Computerzugänge liegen im privaten Monitor-Datenvolume und werden mit der vollständigen Monitorsicherung erfasst. Zuerst wird die Datenbank konsistent kopiert, dann die unveränderlichen Originale; die Wiederherstellungsprüfung verifiziert jede referenzierte Datei anhand Größe und SHA-256. Unfertige Eingänge werden nicht mitgesichert. Das ist kein Nachweis einer externen/offsite Sicherung.

Grenzen der ersten Version: 256 MiB pro Original, 1 GiB entpackter ZIP-Inhalt, 2 GiB NAS-Originalarchiv und 2 GiB lokale Originalkopien. Die Warteschlange hält bei vollem Speicher an und löscht keine letzte Kopie. Es gibt noch keine automatische Bereinigung. Ein widerrufener Computerzugang entfernt keine Originale. Für eine erneute Verbindung einen neuen Zugang erstellen. Privatdaten, Computer-Konfiguration und Originaldateien gehören nicht ins öffentliche Repository.
