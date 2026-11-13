# OrcaSlicer 2.5: Einordnung für Kobra Monitor

Geprüft am 07.11.2026 anhand der offiziellen Veröffentlichung, Entwicklerdokumentation und einzelner Header im veröffentlichten Tag `v2.5.0`, Commit `40ecc66f78ed72dc368e0c1ebe40d77f00cc8a19`. Recherche, keine Installation oder zugesagte Kompatibilität mit realen S1-Druckdateien.

Nach der Recherche hat der Besitzer die Architektur ausdrücklich festgelegt und anschließend präzisiert: Kobra Monitor bleibt die zentrale Beobachtungsstelle und Spulenverwaltung. Neue Dateien werden in Orca oder Slicer Next geslicet und erstmals übertragen. Erfolgreich abgeschlossene archivierte Drucke sollen dagegen direkt über den Monitor wiederholt werden können, auch am Handy ohne Slicer. Ein optionales Orca-Plugin dient der zusätzlichen Archivkopie. Printer Agent und eine primäre Monitor-Oberfläche innerhalb Orca sind keine aktuellen Entwicklungsziele. Die unten beschriebenenen Schnittstellen sind recherchierte Möglichkeiten, keine Ausbauzusage.

## Größter Nutzen: explizite Archiv-Anbindung

Orca 2.5 unterstützt Python-Erweiterungen, einschließlich lokaler Installation. Ein optionaler Archiv-Connector könnte die vorhandene geprüfte Archivannahme verwenden, statt Orca-Dateien ausschließlich über Cache-Verzeichnisse zu entdecken. Eigene Python-Installation und Orca-Cloud-Verteilung wären für eine lokal installierte Erweiterung keine notwendige Grundlage. Der bestehende Helfer für andere Slicer bleibt unabhängig nutzbar.

Die Lifecycle-API meldet unter anderem `GCodeExportFinished`, `UploadFinished` und Print-/Send-Jobs. Ihre Nutzdaten sind jedoch klein und können Felder auslassen. Ein Exportpfad kann auf G-Code vor der endgültigen Druckpaketerstellung zeigen; ein Uploadereignis enthält gegebenenfalls nur einen Namen. Deshalb zuerst ohne Netzwerkübertragung prüfen, bei welchen realen Orca-S1-Abläufen das fertige unveränderte `.gcode.3mf` tatsächlich zugänglich ist. Keine Rekonstruktion eines vermeintlichen Originals aus einem Exportereignis. Ein Export- oder Send-Job-Ende ist kein Nachweis eines physisch abgeschlossenen Drucks; dafür bleibt der NAS-Monitor maßgeblich.

Ein möglicher Connector kopiert eine belegte fertige Datei in eine dauerhafte lokale Warteschlange, überträgt sie außerhalb des Slicer-Ereignishandlers, prüft die Archivbestätigung und führt keine Druckerbefehle aus. Netzwerk-/Dateifreigaben erfolgen einmalig durch den Benutzer. Fehlschläge dürfen den Slicer weder blockieren noch Dateien als archiviert kennzeichnen. Der bisherige Archivzugang reicht nur für Dateiannahme und Helferstatus, nicht für Steuerung oder Abruf alter Dateien.

## Weitere Möglichkeiten, getrennt priorisieren

- **Printer Agent:** Die neue Python-Schnittstelle erhält beim Senden einen Dateipfad und Druckoptionen einschließlich Filamentzuordnung. Sie könnte später „An Kobra Monitor senden“ als direkten Slicer-Weg ermöglichen. Das erfordert eine eigene vollständige Verbindungsschicht und ist derzeit experimentell sowie standardmäßig deaktiviert. Es liefert keinen fertigen Stock-S1-Upload-/Starttreiber und ersetzt dessen praktische Abnahme nicht.
- **Eigene Slicer-Seite:** Eine Pages-Erweiterung kann eine HTML-Seite und Nachrichtenbrücke bereitstellen. Damit wären später eine kompakte Archiv-/Statusansicht oder ein Monitor-Zugang denkbar. Die vollständige geschützte Monitor-Weboberfläche lässt sich dadurch nicht ohne Prüfung ihrer Anmeldung und Einbettungsschutzregeln übernehmen.
- **Dateikompatibilität:** Die Release-Hinweise nennen eine Option zum Weglassen des G-Code-Konfigurationsblocks gegen bestimmte Anycubic-Parser-/LAN-Probleme. Der beschriebene Kobra-3-Fall ist kein belegter S1-Fehler. Keine bestehenden S1-Profile automatisch ändern. Neue Orca-Dateien einschließlich Metadaten und gegebenenfalls G2/G3-Bögen separat gegen Archiv, Vorschau und Wiederholungs-Vorprüfung testen. Die aktuelle strenge Vorprüfung basiert auf tatsächlich geprüften Anycubic-Slicer-Paketen und darf unbekannte Orca-Varianten weiterhin ablehnen.

## Reihenfolge

Den direkten Archiv-Wiederholungsablauf im Monitor für erfolgreich abgeschlossene Aufträge mit geprüftem Original fertigstellen und praktisch abnehmen. Auswahl, Vorschau, Ziel- und Materialprüfung sowie bewusster Start erfolgen im Monitor; ein laufender Slicer ist dafür nicht vorgesehen. Der vorhandene Originaldownload bleibt ein optionaler Weg. Danach einen kleinen optionalen Orca-Archiv-Connector mit belegter fertiger Datei erproben. Kein Orca-Fork und keine neue verpflichtende Slicer-Abhängigkeit erforderlich. Konkrete Fremdcodeübernahme ist mit dieser Recherche nicht erfolgt.

## Primärquellen

- [Release 2.5.0](https://github.com/OrcaSlicer/OrcaSlicer/releases/tag/v2.5.0)
- [Vollständige Neuerungen seit 2.4 in den Alpha-Hinweisen](https://github.com/OrcaSlicer/OrcaSlicer/releases/tag/v2.5.0-alpha)
- [Plugin-Entwicklung](https://www.orcaslicer.com/wiki/developer_reference/plugin_development/plugin_development)
- [Lifecycle-Ereignisse und Grenzen der Nutzdaten](https://www.orcaslicer.com/wiki/developer_reference/plugin_development/api_reference/lifecycle_events)
- [Printer Agent und Druckparameter](https://www.orcaslicer.com/wiki/developer_reference/plugin_development/api_reference/printer_agent)
- [Pages](https://www.orcaslicer.com/wiki/developer_reference/plugin_development/api_reference/pages)
- [Lokale Plugin-Installation](https://www.orcaslicer.com/wiki/plugins/plugins_local)
- [Lifecycle-Definitionen im geprüften Release-Commit](https://github.com/OrcaSlicer/OrcaSlicer/blob/40ecc66f78ed72dc368e0c1ebe40d77f00cc8a19/src/libslic3r/LifecycleEvents.hpp)
- [Printer-Agent-Vertrag im geprüften Release-Commit](https://github.com/OrcaSlicer/OrcaSlicer/blob/40ecc66f78ed72dc368e0c1ebe40d77f00cc8a19/src/slic3r/plugin/pluginTypes/printerAgent/PrinterAgentPluginCapability.hpp)
