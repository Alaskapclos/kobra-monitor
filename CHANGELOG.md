## 0.28.2-alpha.1

- Nach expliziter Übergangsmeldung wartet die Drucksteuerung bis zu drei Minuten auf den endgültigen Zustand; der Befehl bleibt einmalig. Neue vollständige Rückmeldung, gleiche Verbindung und derselbe Auftrag sind weiter Voraussetzung für eine Bestätigung.
- Vorbereitung und Übergänge werden auch dann korrekt angezeigt, wenn die Bridge allgemein „printing“ meldet. Währenddessen keine alten Prozent-, Restzeit- oder Schichtwerte.
- Offene Rückmeldungen werden bei Neustart, Verbindungs-/Auftragswechsel oder einer weiteren Druckaktion nicht nachträglich als erfolgreich ausgegeben.

## 0.27.1-alpha.1

- Z-Tasten entsprechen der Tischbewegung: Plus nach oben, Minus nach unten; X und Y unverändert.
- Eigene klare Homing-Schaltflächen für Druckkopf X/Y und Druckbett Z; Wartezeit nach Homing und Neustart auf30 Sekunden verkürzt.
- Anwesenheit für X/Y/Z nur vor der ersten Fahrt bestätigen. Weitere Schritte derselben Anmeldung an diesem Drucker bis zum nächsten regulären Druck ohne Dialog; schon dessen Vorbereitung setzt die Freigabe zurück. Hinweis erklärt dies vor der Bestätigung. Homing bleibt einzeln bestätigt.

## 0.28.1-alpha.1

- Eigene Schaltfläche „Motoren ausschalten“ neben Homing. Nur im frischen Leerlauf mit eigener Anwesenheitsbestätigung bei jedem Aufruf und Hinweis auf entfallende Haltekraft.
- Einmaliger begrenzter `axis/turnOff`-Versand mit bestehender Protokollierung, Kontextprüfung und Bewegungssperre. Keine automatische Motorabschaltung nach Homing; keine direkte Steuerung der Elektronikkühlung.

## 0.28.0-alpha.1

- Privates Archiv für vollständige geslicte 3MF-Originale: atomarer Eingang, unabhängige SHA-256-/Größen-/ZIP-Prüfung, inhaltsadressierte unveränderliche Ablage und geschützter Download.
- Separater Computerzugang mit ausschließlich Datei-Eingang/Helferstatus. Optionaler macOS-Helfer übernimmt künftige Sendecache-Pakete; dauerhafte lokale Warteschlange und Wiederholung nur der Archivübertragung bei NAS-Ausfall.
- Archivansicht unter Druckaufträge; ausdrückliche Originalzuordnung erzeugt bei abgeschlossenen Aufträgen eine neue feste Berichtsversion mit Inhaltshash. Keine automatische Gleichsetzung nach Dateinamen und kein Druckstart aus dem Archiv.
- Vollsicherung nimmt den Datenbankschnappschuss vor den unveränderlichen Originalen auf; Wiederherstellung prüft referenzierte Inhalte. Laufzeitdateien, unfertige Eingänge und Computer-Konfiguration bleiben privat.
- Vorher vorbereitete README-/Roadmap-/Sicherheitskorrekturen zum tatsächlichen Steuerungsumfang übernommen. Freigabeprüfung berücksichtigt auch neue nicht ignorierte Quelldateien.
- Reale Slicer-Übernahme und Helfereinrichtung bleiben bis zum nächsten selbst gestarteten Auftrag gesondert abzunehmen; interner Slicer-Cachepfad ist nicht als stabile öffentliche Schnittstelle zugesichert.

## 0.27.0-alpha.1

- Optionale manuelle X/Y/Z-Schritte und getrennte Referenzfahrten XY/Z in der Übersicht. Nur aktueller Leerlauf, separate Druckerfreigabe, Dialog und bestätigte Anwesenheit vor Ort.
- Begrenzte Einzelbefehle, gemeinsames Schaltprotokoll, Schutz vor alten Bestätigungen und keine automatische Wiederholung. Versand wird nicht als abgeschlossene Bewegung ausgegeben.
- Schaltflächen mit klareren Umrandungen, kräftigerer Beschriftung, sichtbaren Fokus-/Auswahlzuständen und erkennbaren gesperrten Zuständen; grüne Farbwelt erhalten.

## 0.26.1-alpha.1

- Druckabbruch ab der eindeutig erfassten Vorbereitung, einschließlich Aufheizen und Bettnivellierung. Pause/Fortsetzen bleiben auf Printing/Pause begrenzt.
- Alte, von der Firmware während der Vorbereitung mitgeführte Laufzeitwerte werden nicht als neuer Auftragswechsel gewertet. Vollständige frische Identität, Bestätigung und Schutz vor veralteten Dialogen bleiben erforderlich.

## 0.26.0-alpha.1

- Pause, Fortsetzen und Druckabbruch direkt in der Übersicht mit eigenem Bestätigungsdialog für Drucker und Datei.
- Getrennte ausdrückliche Freigabe, aktuelle Auftrags-/Verbindungsbindung, enger einmaliger print/pause|resume|stop-Versand und neuere Zustandsbestätigung. Leerlauf oder Verbindungsverlust ist keine Abbruchbestätigung.
- README auf den tatsächlichen Funktionsumfang der Version gebracht; praktische Nachweise und offene Grenzen getrennt dokumentiert.

## 0.25.0-alpha.1

- Düse und Druckbett erhalten getrennte Solltemperatur-Dialoge mit OK und Abbrechen direkt neben ihren Anzeigen; 0 °C schaltet den gewählten Heizer aus.
- Separate standardmäßig leere Temperaturfreigabe. Nur S1, aktuelle Verbindung und frischer Leerlauf oder laufender Druck; Status-/Auftragswechsel verwirft die Auswahl. Einmaliger enger SET_TEMPERATURE-Versand, keine Wiederholung.
- Sollwertbestätigung erst durch neuere Telemetrie; keine Behauptung, die Isttemperatur sei bereits erreicht.

## 0.24.0-alpha.1

- Speed Mode direkt am Status: Silent, Standard oder Sport mit OK übernehmen.
- Getrennte Freigabe pro S1, Bindung an den aktuell gemeldeten Druck und die aktuelle Verbindung, keine Übernahme im Leerlauf.
- Auftrag-/Dateiwechsel, Pause, Laufzeitneustart, veraltete Daten und Doppelklicks abgesichert; keine automatische Wiederholung.
- Bestehende Steuerprotokolle bei Schemaerweiterung erhalten.

## 0.23.0-alpha.3

- Einmalige Lüftervorgangskennung auch über private HTTP-LAN-Adressen erzeugen; Browserprüfung ohne crypto.randomUUID ergänzt.

## 0.23.0-alpha.2

- Lesende fan/query-Abfrage ausdrücklich durch die Client-Richtlinie erlaubt; Einstellbefehle bleiben dort gesperrt. Versionsanzeige korrigiert.

## 0.23.0-alpha.1

- Lüftersteuerung bei Bauteil-, Zusatz- und Kammerlüfter: Stufendialog mit Schieberegler, Zahl, Abbrechen und OK.
- Getrennte ausdrückliche Freigabe je Drucker; frische kanalbezogene Rückmeldungen, gemeinsamer Einmalversand und Schaltprotokoll mit abwärtsverträglicher Migration.
- Keine automatischen Wiederholungen oder optimistischen Zustandswerte.

# 0.22.1-alpha.1

- Kammerlichtschalter direkt neben dem Glühbirnensymbol, mit visuellem An/Aus-Regler.
- Lichtwechsel mit einem Klick ohne zusätzlichen Bestätigungsdialog. Sonstige künftige Steuerfunktionen behalten eine ausdrückliche Bestätigung.
- Eindeutiges Ziel, frische Rückmeldungen, Anmeldung/CSRF, Einmalversand und Schutz vor unbeabsichtigtem Versand bei Drucker-/Seitenwechsel bleiben erhalten.
- Separate Licht-Steuerungskarte entfällt; Status und Bedienung stehen an einer Stelle.

# 0.22.0-alpha.1

- Optionales Kammerlicht An/Aus auf der Übersicht für ausdrücklich freigegebene S1-Drucker; Standard bleibt Lesebetrieb.
- Besitzeranmeldung, Origin-/CSRF-Prüfung und kurz gültige Bestätigung mit konkretem Drucker. Doppelversand und Wiederholung nach Neustart gesperrt.
- Erfolg erst nach neuer Lichttelemetrie derselben Verbindung; unklare Ergebnisse bleiben als solche sichtbar, ohne automatische Wiederholung.
- Eng begrenzter Versandweg für Lichttyp 2, ohne allgemeinen Steuerzugriff. Keine Heiz-, Bewegungs-, Lüfter-, Upload- oder Druckbefehle.
- Lokales Vorgangsprotokoll in der mitgesicherten Verlaufsdatenbank. Mobile Ansicht bleibt untereinander.

# 0.20.0-alpha.1

## 0.21.2-alpha.1

- Chamber fan gets a matching bar on its reported 0–100 level scale.
- Chamber light shows an on/off bulb icon, neutral for unknown/stale readings.
- Remove brightness row from the overview; no control added.

## 0.21.1-alpha.1

- Mobile Bereichsnavigation oben unter dem Logo, beim Scrollen erreichbar.
- Kleine Balken zusätzlich zu Bauteil- und Zusatzlüfter-Prozentwerten; bei fehlenden/veralteten Werten ausgeblendet. Kammerstufe weiterhin unverändert.

## 0.21.0-alpha.1

- Desktop overview places the compact camera on the left and printer status on the right; mobile stacks all sections.
- Enlarge a single camera or grid tile in an accessible dialog while reusing its running view; close with the button or Escape.
- Show received part/auxiliary fan percentages, raw chamber-fan level, chamber light and brightness, and Silent/Standard/Sport modes. Missing, invalid, stale and previous-session fields are distinguished.
- Poll the read-only light/query report with null data; light/control and other setting commands remain blocked. Chamber-light type 2 is selected from the lights array without bridge defaults.


- Originale Spoolman-Oberfläche unter Spulen eingebettet, mit ACE-/Verwaltungs-Unterbereichen.
- Besitzeranmeldung, begrenzter nativer Unterpfad, Origin-Schutz und Live-Verbindungen; keine Frontend-Kopie oder Spoolman-Codeänderung.
- Manuelle Bestandsverwaltung getrennt vom weiterhin lesenden Druckerzugriff.

## 0.19.0-alpha.1

- Separate workspace navigation with a mobile bottom bar for overview, customer jobs, spools and operation/help.
- Local customer order references, part/position and manual post-print quality approval with optimistic edit concurrency.
- Frozen, versioned completion reports in SQLite plus private archive files; PDF, JSON, Markdown and bounded ZIP batch export.
- Captured material provenance and explicit limits; historical backfill never invents end-time inventory assignments.
- Existing owner, CSRF and Origin protections apply; no new printer or inventory commands.

# 0.18.3-alpha.1 (vorbereitet)

- Lokale Bedienhilfe über „Hilfe“ erreichbar: Drucker, Kameraübersicht, Spulen, Handy-Meldungen, Verbindungsprobleme und Sicherungsgrundlagen. Ohne zusätzliche Verbindung oder neue Skripte.

- Detailansicht kennzeichnet letzte Temperatur-/ACE-Werte auch unmittelbar nach Verbindungsabbruch und blendet veralteten Fortschritt, Schichten und Restzeit aus.
- Vorbereitung verwendet keine zwischengespeicherten Fortschritts-/Restzeitwerte.
- Spulenerkennung übernimmt den Alterungs- und Ausfallzustand des Browsers; Rückkehr frischer Daten stellt die Erkennung wieder her.
- Neue Ausfall-/Wiederverbindungsprüfungen der Detailansicht und Kamera; produktive NAS-Installation während eines laufenden Drucktests unverändert.

# 0.18.2-alpha.1

- Automatisch per Kennung erkannte Spulen stehen direkt in der Slotanzeige. Die feste Slotzuordnung wird dabei ausgeblendet.
- Kennungsverknüpfte Spulen können nicht zusätzlich manuell an einen Slot gebunden werden; Server prüft dies auch bei direkten oder veralteten Anfragen.
- Alte feste Bindungen lassen sich gezielt lösen, ohne die Kennungsverknüpfung zu löschen. Veraltete Daten gelten weiterhin nicht als aktuelle Erkennung.
- Reihenfolge bestätigt: erst Lesefunktionen abschließen; Steuerbereich anschließend separat.

# 0.18.1-alpha.1

- Direkter Link „Spoolman öffnen“ in der Spulenverwaltung, auch bei geschlossener Einrichtung. Nutzt die gespeicherte HTTP(S)-Adresse und öffnet einen getrennten Tab ohne Weitergabe der Herkunftsseite.

# 0.18.0-alpha.1

- Lokale ACE-SKU lesen und eindeutige Spulenkennungen nach Bestätigung dauerhaft mit Spoolman-Spulen verknüpfen.
- Wiedererkennung nach Slotwechsel; mehrfache Kennungen, Konflikte und veraltete Daten sperren die Erkennung.
- Verknüpfungen lösen und sichern; keine Verbrauchsbuchung oder Tag-/Druckeränderungen.

## 0.16.0-alpha.1

## 0.17.0-alpha.1

- Optionale lesende Spoolman-Anbindung und manuelle ACE-Slot-Zuordnung im Monitor.
- Private Zuordnungen in Vollsicherung; getrennte Gewichtsherkunft, Frische und Fehleranzeige.
- Ursprünglichen Gesamtplan in ROADMAP.md abgeglichen; ReSpool/NFC, Verbrauch, Orca und Warteschlange bleiben enthalten.


- Druckerkarten zeigen unabhängig voneinander Druckstatus, Fortschritt, geschätzte Restzeit und Ist-Temperaturen.
- Druck- und Temperaturdaten werden getrennt auf Aktualität geprüft. Bei Verbindungsverlust werden Livewerte ausgeblendet.
- Vorbereitung zeigt keinen möglicherweise alten Fortschritt oder Restzeitwert. Details und gespeicherte Sortierung bleiben erhalten.

## 0.15.0-alpha.1

- Betriebsstatus mit Druckerfrische, Kameraaufbereitung, Verlauf und Benachrichtigungsdienst.
- Verständliche Hinweise zu HTTPS, fehlender Browser-Unterstützung und blockierter Benachrichtigungserlaubnis.
- Kopierbarer Prüfbericht mit ausdrücklich begrenzten technischen Feldern, ohne IP-Adressen, Drucker-/Dateinamen, Zugangsdaten oder Zustellschlüssel.

## 0.14.0-alpha.1

- Optionale verschlüsselte Web-Push-Meldungen pro Gerät für bestätigtes Druckende/Abbruch, Druckerstörungen und längere Verbindungsabbrüche.
- iPhone/iPad als Home-Bildschirm-App, Android und unterstützte Desktop-Browser über HTTPS. Geführte Einrichtung, Auswahl, Testmeldung und Entfernen.
- Dauerhafte Warteschlange, begrenzte Wiederholungen und Entdoppelung; Verbindungsverlust ist kein Druckende.
- VAPID-Schlüssel und Geräteanmeldungen werden mit der vollständigen Installation gesichert. Kein Offline-Cache für Konto, Status oder Kamerabilder.

## 0.13.1-alpha.1

- Fehlgeschlagene Decoderprüfung nach kurzer Wartezeit wiederholen, statt eine Kamera dauerhaft zu sperren.
- Meldungen unterscheiden die Aufbereitung auf dem Monitor-Server von Handy/Mac als reinen Anzeigegeräten.


## 0.13.0-alpha.2

- Optionale Kameraübersicht mit zwei oder vier Bildern pro Seite, Druckernamen und eigener Fehlermeldung je Bild.
- Seitennavigation folgt der gespeicherten Druckerreihenfolge; nur die sichtbare Seite wird geladen.
- Ansichten geben ihre lokalen Leser beim Wechsel frei, ohne andere Browser desselben Druckers zu unterbrechen. Vier gemeinsame Decoder als Obergrenze.


## 0.12.1-alpha.1

- Kamerabild erst nach vollständiger Decodierung austauschen; vorheriges Bild bleibt beim Nachladen sichtbar.
- Kurze Verbindungsfehler kennzeichnen das letzte Bild statt die Ansicht wiederholt zu leeren; nach zehn Sekunden ohne Aktualisierung wird es entfernt.
- Sechs gezielte Prüfungen für Bildwechsel, Fehler und verspätete Bilder nach Druckerwechsel.

- Geschützte Kameraansicht aus vorhandenen Stock-FLV-Streams, etwa zwei Bilder pro Sekunde.
- Bestehenden CameraCache und FFmpeg wiederverwendet; keine Kamera- oder Drucksteuerbefehle.
- Decoder geteilt und begrenzt; alte Bilder abgewiesen, Leerlauf und Druckerwechsel beenden Ansicht.

## 0.11.0-alpha.1

- Drucker einzeln hinzufügen/entfernen, doppelte Adressen und Grenze 16 sichtbar.
- Verbindungsstatus in Einrichtung und Abschlussanzeige; vorhandene Daten erhalten.
- HTTPS über vorhandenes Tailscale Serve mit Nutzer-Gegenprobe erfolgreich geprüft.

## 0.10.0-alpha.1

- Druckerkarten per Drag-and-drop dauerhaft anordnen; auf Touchgeräten am Punktgriff.
- Alternative mit Alt + Pfeiltasten, Bestätigung und verständliche Speicherfehler.
- Reihenfolge über alle Browser hinweg; Auswahl und Druckerverbindungen bleiben erhalten.
- Sortierroute akzeptiert nur vorhandene Drucker und erfordert Anmeldung/CSRF.

## 0.9.0-alpha.1

- Lokales Besitzerkonto mit frei gewähltem Benutzernamen und Passwort.
- Geschützter einmaliger Umstieg von der Code-Anmeldung; Code danach gesperrt.
- Konto ändern, Abmelden, Sitzungen widerrufen, lokale interaktive Wiederherstellung.
- Passwörter mit scrypt gehasht und gesalzen; kein Klartext in Datenablage/Logs.
- Assistent: Konto → Drucker → Übersicht. Kontodaten in vollständigen Sicherungen.
- Druckerzugriff weiterhin ausschließlich lesend.

# Änderungen

## 0.8.0-alpha.1

- Vollständige Datenarchive mit SQLite-Snapshot, Einrichtung, Zugangscode und Prüfsummen.
- Separater NAS-Sicherungsdienst ohne Netzwerk und mit lesendem Zugriff auf Monitor-Daten.
- Täglicher Rhythmus, sieben erfolgreiche Stände, Wiederholversuche bei Fehlern.
- Wiederherstellung in neue Ordner mit Archivprüfung; bestehende Daten werden nicht überschrieben.

## 0.7.0-alpha.1

- Eigenständiger Projektstand mit Startanleitung, Lizenz-/Sicherheitsdokumentation und CI.
- Keine persönlichen Druckeradressen als Standard; browsergestützte Einrichtung.
- Zugangscode und geschützte lokale Konfiguration für Desktop und privaten VPN-Zugriff.
- Starter für macOS, Linux und Windows; Bibliotheksupdates anhand der Lockdatei.
- Eigenes Docker-/Compose-Paket mit dauerhaftem Datenvolume.
- Die bisherige Übersicht, Suche, Berichte und Temperaturverläufe bleiben enthalten.

## 0.6

Durchsuchbares, blätterbares Archiv pro Drucker mit Statusfilter und Zählern.

## 0.5

Temperaturkurven, Sollwerte und Verbindungs-/Zustandsereignisse pro Auftrag.

## 0.4

Lokale Markdown-Berichte pro Auftrag.

## 0.3 / 0.3.1

Dauerhafte Historie und Erkennung des Beginns bei alten Laufzeitwerten.

## 0.1 / 0.2

Lesende Oberfläche und zwei unabhängige Druckerverbindungen.
