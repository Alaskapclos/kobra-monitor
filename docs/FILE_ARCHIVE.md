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

Der Computer muss für die Übernahme laufen und der Helfer muss aktiv sein. Wenn eine Datei vor der Übernahme verschwindet oder der Slicer seinen Cacheort ändert, kann keine vollständige Erfassung zugesagt werden. Ein Druckbericht oder ein gemeldeter Dateiname allein gilt deshalb nie als Originaldatei-Nachweis. Ein echter Anycubic-Slicer-Next-Auftrag auf macOS wurde einschließlich Eingang auf dem NAS, manueller Zuordnung und Wiederherstellung des archivierten Originals praktisch geprüft. Das belegt den getesteten Ablauf, keine allgemeine Kompatibilität mit beliebigen Slicern oder zukünftigen Cachepfaden.

## Berichte, Zuordnung und Wiederverwendung

Originale sind unter **Druckaufträge** herunterladbar. Im Auftrag lässt sich eine geprüfte Datei ausdrücklich zuordnen. Bei abgeschlossenen Aufträgen entsteht eine neue feste Berichtsversion mit Inhaltshash, Größe und dem Hinweis auf die manuelle Zuordnung. Frühere Berichtsversionen bleiben unverändert. Eine Zuordnung beweist nicht unabhängig, welche Bytes der Drucker tatsächlich ausgeführt hat.

Der Berichte-ZIP-Export enthält weiterhin die Berichtsdokumente und das Prüfmanifest. Die Originaldatei wird separat heruntergeladen und ist durch die im Bericht gespeicherte SHA-256 eindeutig zuordenbar. Ein erneuter Druckstart aus dem Monitor ist in dieser Archivversion noch nicht enthalten.

## Sicherung und Grenzen

Originale, Dateinamen, Zuordnungen und gehashte Computerzugänge liegen im privaten Monitor-Datenvolume und werden mit der vollständigen Monitorsicherung erfasst. Zuerst wird die Datenbank konsistent kopiert, dann die unveränderlichen Originale; die Wiederherstellungsprüfung verifiziert jede referenzierte Datei anhand Größe und SHA-256. Unfertige Eingänge werden nicht mitgesichert. Das ist kein Nachweis einer externen/offsite Sicherung.

Grenzen der ersten Version: 256 MiB pro Original, 1 GiB entpackter ZIP-Inhalt, 2 GiB NAS-Originalarchiv und 2 GiB lokale Originalkopien. Die Warteschlange hält bei vollem Speicher an und löscht keine letzte Kopie. Es gibt noch keine automatische Bereinigung. Ein widerrufener Computerzugang entfernt keine Originale. Für eine erneute Verbindung einen neuen Zugang erstellen. Privatdaten, Computer-Konfiguration und Originaldateien gehören nicht ins öffentliche Repository.

## Bildübersicht und lokale 3D-Vorschau (Entwicklungsstand)

Das Druckdatei-Archiv zeigt Bildkarten und eine Dateinamensuche. „Vorschau öffnen“ zeigt ein eingebettetes PNG in groß. Enthält das Paket mehrere Bilder, Druckplatten oder Modellquellen, lassen sie sich einzeln auswählen. In einem zugeordneten Druckauftrag führt „Zugeordnete Datei ansehen“ zur gleichen Vorschau. Am Desktop stehen Karten und Detailbereich nebeneinander, bei schmaler Ansicht untereinander.

Die 3D-Ansicht wird ausschließlich nach Klick auf eine 3D-Quelle vorbereitet. Drehen mit Ziehen oder Pfeiltasten; Zoomen mit Mausrad oder +/−. Die Druckbahnenansicht hat zusätzlich einen Höhenregler. Für große Druckbahnenansichten wird WebGL verwendet; ohne WebGL sind bis zu 50.000 Segmente über die einfache Darstellung möglich. Die Darstellung erfolgt lokal im Browser, ohne Fremddienst, CDN oder neue Bibliotheksabhängigkeit. Originale werden weder verändert noch als Programme ausgeführt. Die neue Vorschau-API erfordert die Besitzeranmeldung; Archivhelfer-Zugänge erhalten keinen Lesezugriff. Vor jedem Abruf wird die Originalprüfsumme kontrolliert. Es entsteht kein dauerhafter Vorschaucache.

Unterstützt sind einfarbige 3MF-Kernmodelle mit lokalen Meshes, Komponenten, Build-Transformationen und Einheiten sowie lineare G0/G1-Druckbahnen mit G90/G91, M82/M83 und G92. Vorschauen sind keine Drucksimulation, Kollisionsprüfung oder Kompatibilitätsfreigabe. Farben, Texturen, druckerspezifische Makros und Produktions-/Mehrdatei-Erweiterungen werden nicht vollständig abgebildet. G2/G3-Kurven sowie unbekannte G-Koordinatenbefehle führen zu einer ausdrücklichen Meldung statt einer nur teilweise gezeichneten Bahn. Das Original bleibt herunterladbar.

Die erste Vorschauversion begrenzt einzelne Quellen auf 32 MiB, Druckbahnen auf 500.000 Extrusionssegmente und Modelle auf 30.000 Dreiecke. PNGs: höchstens 8 MiB, 4.096 Pixel pro Seite und 8 Millionen Pixel. Pro Paket werden bis zu 32 Bild- und 32 Geometriequellen angeboten. Bei Überschreitung bitte das eingebettete Bild oder den Slicer verwenden. Diese Grenzen gelten für die Vorschau; die Archivgrenzen bleiben unverändert.

Diese Vorschau ist seit 0.35 auf dem produktiven NAS installiert. Sieben lokale Archivkopien wurden gegen den angemeldeten NAS-Katalog anhand ihrer SHA-256 geprüft. Die größte Datei mit 479.577 Extrusionsbahnen wurde auch im produktiven Browser auf Desktop und bei 390 Pixel Breite geprüft. Ein physischer Handytest ist separat offen. Der neue Wiederholungsablauf liegt als 0.36-Erprobungsstand vor; seine reale Stock-S1-Abnahme ist separat offen.

## Vorprüfung für Druckwiederholungen (unveröffentlichter Quellstand)

Die lesende Vorbereitung unter `GET /api/archive/preview?mode=preflight&sha256=…` benötigt dieselbe Besitzeranmeldung wie die Vorschau. Sie prüft die archivierte Originalprüfsumme vor und nach der Auswertung. Computerzugänge erhalten keinen Zugriff. Dieser Leseabruf spricht keine Drucker an, überträgt keine Dateien und erteilt keine Startrechte. Der getrennte Wiederholungsablauf ist in [REPRINT.md](REPRINT.md) beschrieben; seine Schreibschritte benötigen zusätzliche Druckerfreigabe und Besitzerbestätigungen.

Die erste Fassung liest eine einzelne Anycubic-S1-Druckplatte mit eindeutigem 250×250×250-mm-Profil, Düsendurchmesser, 1,75-mm-Filament und übereinstimmenden Material-/Farb-/Werkzeugangaben aus Projektprofil, Druckplattenbeschreibung und G-Code. Tatsächliche Werkzeugnummern bleiben erhalten, auch wenn eine einfarbige Datei beispielsweise nur T1 verwendet. Zusätzlich werden innere MD5-Prüfsumme und SHA-256 des G-Codes geprüft. Die MD5 dient nur dem Abgleich mit dem Slicer; das unveränderte Archivoriginal wird weiterhin über SHA-256 identifiziert.

Mehrere Druckplatten, übersprungene Objekte, widersprüchliche Angaben, unbekannte Werkzeugauswahl sowie zu große oder unvollständige Quellen werden ausdrücklich abgelehnt. Grenzen: 32 MiB G-Code, 64 KiB je Zeile und 1 MiB je Metadatenquelle. Die Prüfung zertifiziert keinen beliebigen G-Code als sicher und prüft weder die tatsächlich eingebaute Düse noch das freie Druckbett. Der getrennte Übertragungs-/Startablauf prüft frischen Druckerzustand und explizite ACE-Zuordnung; Düse, Druckbett und Materialbereitschaft muss der Besitzer zusätzlich bestätigen.
