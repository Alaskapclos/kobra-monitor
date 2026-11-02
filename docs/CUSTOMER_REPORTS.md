# Kundenaufträge und Berichtsarchiv

Ab Version 0.19 führt die Navigation zu Übersicht, Druckaufträgen, Spulen sowie Betrieb & Hilfe. Am Handy befinden sich die Arbeitsbereiche unten. Die Auswahl des Druckers bleibt beim Wechsel erhalten. Die Kameraansicht wird beim Verlassen der Übersicht geschlossen; die NAS-Aufzeichnung läuft weiter.

## Kundenauftrag bearbeiten

Unter **Druckaufträge → Auftrag & Berichte** lassen sich Kundenauftragsnummer, Position, Teilbezeichnung und Anmerkung eintragen. Die Suche berücksichtigt diese Angaben und den Dateinamen. Mehrere Druckversuche dürfen dieselbe Kundenauftragsnummer erhalten; jeder behält seine vollständige interne Druckauftragskennung.

Für eine manuelle Qualitätsabnahme nach Druckende „Freigegeben“ oder „Beanstandet“ wählen und den Prüfernamen eintragen. Der Monitor speichert den Zeitpunkt. Ein vom Drucker gemeldeter Abschluss und eine manuelle Qualitätsabnahme sind unterschiedliche Aussagen. Der Monitor misst keine Bauteilqualität und bucht keinen Filamentverbrauch.

## Feste Versionen

Neue bestätigte Abschlüsse und Abbrüche erhalten eine feste erste Berichtsversion. Auch ein nicht beobachtetes Ende bleibt ausdrücklich als solches gekennzeichnet. Änderungen an Kundenangaben oder Qualitätsabnahme eines beendeten Auftrags erzeugen eine neue Version. Unverändertes Speichern und wiederholte Abschlussmeldungen erzeugen keine zusätzlichen Versionen. Gleichzeitige Änderungen aus mehreren Browsern werden anhand der Bearbeitungsrevision erkannt; bei einem Konflikt den Auftrag neu öffnen.

Bestehende abgeschlossene Aufträge können mit **Alle bisherigen Abschlüsse archivieren** nachträglich übernommen werden, höchstens 100 pro Durchlauf. Erstellungszeit und Grund zeigen, dass es sich um eine nachträgliche Archivierung handelt. Eine heutige Spoolman-Zuordnung wird dabei nicht als damalige Materialzuordnung ausgegeben.

Die Versionen werden in `history.sqlite3` gespeichert und zusätzlich im eigenen Datenordner unter `report-archive/<vollständige-Auftragskennung>/vN/` als PDF, JSON und Markdown abgelegt. Frühere Versionen werden vom Monitor weder überschrieben noch gelöscht. Anwendungsseitige SQLite-Sperren und Prüfsummen schützen vor versehentlichen Änderungen; ein Administrator mit direktem Datenzugriff kann die Installation weiterhin verändern. Es gibt keine kryptografische Signatur oder externe Zeitstempelbestätigung.

## Inhalt und Exporte

- PDF: lesbarer Bericht zur Kundenakte, mit Seitenzahlen und eingebetteter Schrift.
- JSON: Kundenangaben, Bearbeitungs-/Archivversion, Generatorversion, Auftragsdaten, gespeicherte Messpunkte und Ereignisse, Materialnachweis und Grenzen für die Weiterverarbeitung.
- Markdown: Textbericht zur eigenen Ablage.
- ZIP: bis zu 25 ausgewählte Aufträge, jeweils neueste Archivversion in allen drei Formaten und ein Prüfmanifest; unkomprimierter Inhalt insgesamt höchstens 64 MiB.

Dateinamen enthalten bereinigte Kundenauftragsnummer/Position, Archivdatum, vollständige interne Auftragskennung und Version. Die Kundenangaben selbst bleiben im Bericht vollständig erhalten. Nicht darstellbare Schriftzeichen werden im PDF gekennzeichnet; JSON und Markdown erhalten den Unicode-Text.

Die kombinierte SHA-256-Prüfsumme umfasst die UTF-8-kodierte kanonische JSON-Nutzlast (sortierte Schlüssel, kompakte Trennzeichen), danach den UTF-8-Markdown und die PDF-Bytes. Der zusätzliche `archive_sha256`-Wert im JSON-Download ist kein Bestandteil der ursprünglichen Nutzlast. Die gespeicherte Archivversion wird vor dem Export geprüft.

Originale G-Code-/3MF-Inhalte werden nicht aufbewahrt. Daher enthält der Bericht keinen erfundenen Datei-Inhaltshash. Verfügbare ACE-Daten stammen aus der Aufzeichnung. Eine Spoolman-Zuordnung bei neuen Abschlüssen wird mit ihrem Erfassungszeitpunkt, ihrer Frische und ihrem Buchrestgewicht festgehalten; eine spätere Änderung der Spulenverwaltung verändert keine alte Archivversion. Ein Buchrestgewicht ist keine Verbrauchsmessung.

## Sicherung und Zugriff

Berichte und Kundenangaben erfordern die vorhandene Besitzeranmeldung. Änderungen benötigen zusätzlich den vorhandenen CSRF-/Origin-Schutz. Downloads werden nicht öffentlich geteilt. Monitor-Vollsicherungen enthalten Datenbank und Archivdateien; die Wiederherstellung einer getrennten Kopie ist Bestandteil der Prüfung. Spoolman bleibt separat zu sichern.

Alle Versionen bleiben ohne automatische Löschfrist erhalten. Ein konkreter Aufbewahrungs- oder Löschprozess richtet sich nach den betrieblichen Anforderungen und ist noch kein eigener Verwaltungsbereich. Sieben rotierende Vollsicherungen begrenzen nicht die Aufbewahrung der Auftragsdaten auf sieben Tage. Eine zusätzliche Kopie außerhalb des NAS bleibt sinnvoll. Für einen anderen, separat eingebundenen NAS-Archivordner ist eine gezielte Installationskonfiguration erforderlich; die Oberfläche nimmt keine beliebigen Serverpfade entgegen.
