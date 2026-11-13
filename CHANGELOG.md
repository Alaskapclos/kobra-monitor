## 0.43.0-alpha.4 – verständliche Windows-Sperrprüfung

- Eine laufende alte lokale App blockiert die Übernahme mit einem verständlichen Beenden-Hinweis statt eines Lesefehlers am gesperrten Byte.
- Keine automatische Beendigung, keine Zusammenführung getrennter Profile und keine zusätzlichen Steuerfreigaben.
- Ursprüngliche Dateirechtefehler bleiben erkennbar; Sicherung und isolierte Wiederherstellung erfolgen weiterhin vor Veröffentlichung der neuen Datenkopie.

## 0.43.0-alpha.3 – Paketkandidat

- Native Datenübernahme in eine getrennte neue Kopie auch aus 0.42 vorbereitet.
- Mac-Paketierung verwendet für Intel und ARM die festgelegten eigenen Kamerabauten mit vollständigem Originalquellarchiv; die bisherigen privaten Apps bleiben unverändert.
- Bereinigte Intel-/Windows-ARM-Bibliotheken werden in getrennten neuen Eingaben vorbereitet; endgültige neue Pakete brauchen ihren eigenen Nachweis.
- Vollständiger http-ece-MIT-Hinweis zusätzlich im Mac-Lizenzbereich.

## 0.43.0-alpha.2 – Vorbereitung der öffentlichen Quellalpha

- README, Hilfe, Info, Installation, Plattformmatrix und Prüf-/Freigabestand an die tatsächlich gebauten Desktop-0.42- und Docker-0.43-Pakete angepasst. Automatische Updates und Linux ARM64 bleiben als offen gekennzeichnet.
- GitHub-Actions auf genaue geprüfte Commit-IDs gebunden; Browserprüfung erfasst automatisch alle JavaScript-Prüfdateien einschließlich der nativen Freigaben.
- LAN-Diagnose verlangt die ausdrücklich gewählte `--ip`; keine feste persönliche Druckeradresse mehr. Regression prüft, dass ohne Ziel keine Verbindung versucht wird.
- Vollständigen unveränderten Original-MIT-Text für http-ece 1.2.1 mit Quellzuordnung ergänzt.
- Historie, konkrete Binär-Lizenzinventare und Datenschutzprüfung getrennt dokumentiert. Öffentliche Binärfreigabe bleibt gesperrt, bis persönliche Baupfade, Drittquellen und Signierung fertig geprüft sind. Vorhandene Test-ZIPs unverändert.

## 0.43.0-alpha.1 – Docker-Entwicklung

- Explizit wählbarer LAN-Zugang nur für den Monitor im gemeinsamen Docker-Projekt. Spoolman intern und Sicherung ohne Netzwerk.
- Dauerhafte Steuerungsfreigaben im LAN-Modus über den vorhandenen geschützten Einrichtungsdialog; standardmäßig keine Freigabe.
- Desktop-Testpakete 0.42 bleiben unverändert. Linux ARM64 und Raspberry-Pi-Abnahme noch offen.

## 0.42.0-alpha.1 – dauerhafte native Steuerungsfreigaben

- Besitzer wählen und bestätigen Funktionen pro gespeichertem Drucker; Anmeldung, CSRF-/Origin-Prüfung und aktuelle Einrichtung werden geprüft.
- Private lokale Freigaben werden mitgesichert und nach vollständigem Neustart geladen. Bis dahin gelten bisherige Freigaben. Das Speichern sendet keine Druckerbefehle.
- Entfernte Drucker verlieren gespeicherte Freigaben. NAS/Docker verwendet weiterhin seine getrennten Umgebungsfreigaben.
- Gestoppte 0.41-Profile werden nach Bestätigung mit geprüfter Sicherung in eine neue Datenkopie übernommen.


## 0.41.0-alpha.1 – native Windows-ARM64-Paketierung

- Native Windows-Paketierung wählt Python, FFmpeg, Wheels und Datenbank-Starthelfer nach Zielarchitektur; x64 bleibt getrennt.
- Windows-Starter prüft die Architektur des laufenden Interpreters und bietet bei Bedarf den passenden signaturgeprüften Microsoft-Laufzeitinstaller an.
- ARM64-Binärdateien und normale/verzögerte DLL-Importe werden geprüft. Eine exakt gehashte, von keinem aktiven Paketbestandteil importierte AMD64-Kompatibilitätsdatei des offiziellen ARM-Python-ZIP wird nicht ausgeliefert.
- Bestätigte Übernahme gestoppter lokaler 0.40-Testprofile in eine neue Datenkopie ergänzt; frühere Pakete und NAS bleiben unverändert.
- Windows-ARM64-Gesamtabnahme steht noch aus; einzelne selbst gebaute Abhängigkeiten wurden bereits nativ unter Windows ARM64 geladen und geprüft.


- Explizit bestätigte Übernahme lokaler Profile aus 0.34/0.39 in einen eigenen Datenordner. Alte Daten bleiben erhalten; laufende Instanzen, unbekannte Versionen, fremde Ziele und externe Spoolman-Bestände werden nicht ungeprüft übernommen.
- Bytegeprüfte Sicherungskopie, Zusammenführung vorhandener WAL-Daten ausschließlich in der Kopie, isolierte Wiederherstellung und Prüfung aller bestehenden Tabelleninhalte vor Veröffentlichung. Kein Entfernen alter Daten oder Sicherungen.
- Mac-Programme bekommen einen versionsgebundenen Installationsnamen. Neue Starts und Beenden beziehen sich auf das übernommene Profil; Hintergrundprozesse zeigen keine Übernahmedialoge.
- Kein produktives NAS-Update und keine echte Geräteabnahme durch diesen Entwicklungsschritt.

## 0.37.0-alpha.1 – ACE-Klima und bestätigte Trocknung

## 0.39.0-alpha.1

- Getrennter Apple-Silicon-Testbau mit ARM64-Laufzeit, passenden Bibliotheken und eigener Kameralaufzeit vorbereitet. Mac-Starter prüft die Architektur seines tatsächlich laufenden Interpreters.
- Vier native Zielkennungen, architekturspezifische Wheel-/PE-/Mach-O-Prüfung und Schutz vor falsch beschrifteten ARM-Paketen; WindowsARM64-Eingaben noch unvollständig.
- Dokumentation und Freigabeprüfung aktualisiert, historisches Prüfmaterial getrennt; Besitzer bestätigt erfolgreichen Archivwiederholungsabschluss. Kein produktives NAS-Update durch diesen Installer-Teststand.


## 0.38.0-alpha.1

- Archivwiederholung zeigt den geschätzten Dateibedarf neben dem aktuellen, eindeutig zugeordneten Spoolman-Buchbestand; Fehlmengen in Gramm, unbekannte Daten ausdrücklich nicht beurteilbar.
- Mehrere Datei-Filamente derselben physischen Spule teilen sich einen Vorrat. Nullbestand, Frische und erkennbare Slotänderungen berücksichtigt.
- Lesender Hinweis ohne zusätzliche Druckerrechte, Bestandsbuchung oder Startsperre.


- Temperatur, verfügbare Luftfeuchte, Trocknungszustand und Restzeit je ACE direkt in der jeweiligen Druckerkachel; getrennte Datenfrische und ehrliche unbekannte Werte.
- Separat freizugebender Schalter mit Ziel-/Parameterdialog und OK für Ein- und Ausschalten. Standardgrenze 55 °C, ausdrücklich eingerichteter ACE 2 Pro bis 65 °C.
- Einmalige protokollierte Vorgänge, aktuelle Ziel-/Verbindungsprüfung, gemeinsame Steuerreservierung, bestätigte Telemetrie statt optimistischer Anzeige; kein automatischer Neuversuch.
- Archivstart-Kennung auf den positiven 31-Bit-Bereich begrenzt. Bereits bestätigte 0.36-Archivstarts mit nachgewiesenem Lang-/Kurzkennungswechsel werden nur über passenden Drucker, eindeutigen Monitor-Dateinamen und gespeicherten Versandbeleg zusammengehalten; bestehende Historienfragmente bleiben erhalten.
- Reale Heizungsabnahme und NAS-Installation noch offen; automatisierte und synthetische Browserprüfungen ersetzen diese nicht.

## 0.36.0-alpha.1 – Archivwiederholung (Erprobungsstand)

- Erfolgreiche Abschlüsse mit geprüftem Original über Historie, Archiv oder letzten geeigneten Auftrag auswählen; Desktop und Handyansicht.
- Explizite Ziel-/ACE-Zuordnung, getrennte Originalübertragung und Startbestätigung mit Druckbett-/Material-/Düsenprüfung; zusätzliche Startfreigabe standardmäßig leer.
- Persistente einmalige Vorgänge, erneute Verbindungs-/Leerlauf-/Materialprüfung, serverseitige Startbeobachtung unabhängig vom Browser, kein automatischer Neuversuch.
- Neuer Auftrag mit Original- und Quellauftragsbezug; alte Berichtsversionen unverändert. Generischer Bridge-Leseschutz erhalten.
- Reale Stock-S1-Abnahme des Originalpaket-Uploads und Starts noch offen. Nicht als bereits praktisch freigegebene Funktion ausgeben.

## 0.35.0-alpha.1 – Druckdatei-Vorschau

- Archiv mit Bildkarten, Dateisuche und großer Detailvorschau; Zugriff auch aus zugeordneten Aufträgen.
- Lokale dreh- und zoombare 3MF-Kernmodell-/lineare Druckbahnvorschau, Höhenregler und klare Format-/Größenlimits.
- Geschützte, ausschließlich lesende Vorschauabrufe mit Integritätsprüfung; keine neue Fremdbibliothek und keine Druckeraktion.
- Auf dem NAS mit Vor-/Nachsicherung, getrennter Wiederherstellung und angemeldeter Vorschauprüfung installiert. Ein erneuter Druckstart war in 0.35 nicht enthalten.

## 0.34.0-alpha.1 – native Intel-Mac-Testanwendung

- Eigenständige Intel-Mac-App mit portabler Python-Laufzeit, originalem Spoolman und FFmpeg/FFprobe; getrennte Benutzerinstallation ohne Docker oder System-Python.
- Eigener Datenordner, kontrollierter Einmalstart und Öffnen/Beenden über dieselbe App. Bestehende fremde oder anders versionierte Programme werden nicht ersetzt.
- Isolierte Python-Prozesse und Elternprozess-Überwachung; keine übernommenen Druckersteuerfreigaben oder fremden dynamischen Bibliothekspfade.
- Aktuelle Cryptography-Versionen für Intel aus unveränderten Originalquellen mit statischem OpenSSL 4.0.3 gebaut. Intel-Wheels werden upstream nicht mehr angeboten; der eigene Bau bleibt eine zusätzliche Wartungsaufgabe.
- Integritätsprüfung und lokale Ad-hoc-Signatur sind keine Apple-Herausgebersignierung oder Notarisierung. Physische iMac-Abnahme und öffentliche Binärfreigabe bleiben separat.

## 0.33.0-alpha.1 – native Windows-Testinstallation

- Vollständiges Windows-x64-Testpaket mit getrennten Python-Laufzeiten, originalem Spoolman 0.27 einschließlich Oberfläche und FFmpeg.
- Benutzerinstallation, Desktop-Verknüpfungen, Einmalstart-Sperre und geschütztes Beenden ausschließlich eigener Prozesse; keine globale Python-Installation. Falls Microsofts C++-Laufzeit fehlt, wird nach Zustimmung der signaturgeprüfte Originalinstaller von Microsoft geöffnet; dieser kann Administratorrechte verlangen.
- Spoolman nur lokal mit zusätzlichem internem Zugangsschutz; Druckersteuerrechte werden nicht aus der Umgebung übernommen.
- Gemeinsame lokale Sicherung beider Datenbanken mit isolierter Wiederherstellungsprüfung. Kein automatisches Update oder produktiver Datenumzug.
- Echte Windows-Abnahme, Intel-Mac-Paket und Prüfung für die öffentliche Binärveröffentlichung bleiben offen. Produktiver NAS-Monitor unverändert.

## 0.32.0-alpha.1 – Linux-Testinstaller

- Geführtes Linux/amd64-Testpaket mit Image-/Prüfsummenprüfung, eigener Installation, ausdrücklicher Wahl einer privaten Browseradresse und vertraulichem Einrichtungslink. Kein Python auf dem Host nötig.
- Vorhandene passende Installation ohne Neuerstellung laufender Container wiederaufnehmbar; veränderte Konfigurationen, fremde Versionen und doppelte Zielordner werden abgewiesen.
- Paketbau bindet Image-ID, Revisionskennung, Anwendungsdateien und Quellarchiv aneinander. Noch kein signiertes Release, kein vollständiges Offlinepaket und kein natives Windows-/Mac-Paket.

## 0.31.1-alpha.1 – Suite-Testvorbereitung

- Neues getrenntes Compose-Testprojekt mit eigenen Volumes, vorbereiteter Spoolman-Einbettung und ausschließlich internem Testnetz. Kein automatischer Import bestehender Daten.
- Netzwerklose Initialisierung und gemeinsame zeitgesteuerte Sicherung mit Dienste-Konfiguration; Wiederherstellung beider Datenbanken und Konfiguration in einen neuen Offline-Ordner.
- Echter Mehrcontainer-Test für die eigene Bau-VM vorbereitet: Neuinstallation, Anmeldung, Spoolman-API, Neustart mit Datenerhalt und Start eines wiederhergestellten Testprojekts. Erfolg erst nach separatem Bauprotokoll behaupten.
- Windows 10/11 als geplante Ziele, Windows 8/8.1 ausgeschlossen; Intel-Mac-Testziel macOS 15.8.2 festgehalten. Noch keine fertigen nativen Installer.

## 0.31.0-alpha.1 – Entwicklung, nicht produktiv installiert

- Gemeinsame signierte Komplettpaketprüfung mit extern vertrauenswürdigem Ed25519-Schlüssel, festem Komponentenverzeichnis und Datei-/Pfadprüfung. Noch keine Veröffentlichungsschlüssel oder nativen Installer.
- Monitor- und Spoolman-SQLite-Sicherung mit tatsächlicher isolierter Wiederherstellungsprüfung vor Bereitstellung. Keine Migration oder Änderung vorhandener NAS-Daten.
- Lesender Leerlaufprüfer für den künftigen Updatekoordinator; aktive oder unklare Druckzustände stellen ein Update zurück. Noch keine angeschlossene Updateoberfläche und kein Dienstneustart.
- Installationsplan, Entwicklungswerkzeug und Grenzen dokumentiert.

## 0.30.1-alpha.1

- Der Schalter „Achsen & Homing öffnen“ blendet ausschließlich Achsen, Referenzfahrten und Motoren-Aus ein. Licht, Lüfter und weitere freigegebene Bedienelemente bleiben sichtbar; ihre bisherigen Bestätigungen und Zustandsprüfungen bleiben erhalten.
- Das Schließen des Achsenbereichs schließt keinen unabhängigen Lüfterdialog. Der Öffnen-Button richtet sich ausschließlich nach der vorhandenen Bewegungsfreigabe.
- README, Bedienhilfe und aktueller Prüfstand für die öffentliche Alpha bereinigt; reale Archivabnahme, erfolgte Pause und noch offene Rückmeldungs-/Anwesenheitstests getrennt ausgewiesen. Keine öffentliche Freigabe in diesem Update.

## 0.30.0-alpha.1

- Jede Druckerkachel enthält eine kompakte ACE-Ansicht mit Slotnummer, Spulenfarbe, Material, geladenem Slot und Restmengenbalken. Jede Kachel verwendet die eigene ACE-/Spoolman-Quelle und Zuordnung, unabhängig vom ausgewählten Drucker.
- Große und kleine Spulenansicht verwenden denselben Renderer. Leere Slots und veraltete Daten zeigen keine aktuelle Restmenge; unbekannte Bestände bleiben unbekannt.
- Kompakte ACE-Ansichten passen sich an die Kachelbreite an, am Handy weiterhin untereinander.

## 0.29.2-alpha.1

- „Steuerung öffnen“ steht direkt über der Achsensteuerung in derselben Karte. Beim Öffnen bleibt der Button mit den darunterliegenden Bedienelementen im Blick. Desktop und Handy verwenden dieselbe zusammenhängende Anordnung. Die Freigaben und Bestätigungen bleiben unverändert.

## 0.29.1-alpha.1

- Manuell und eindeutig einem Slot zugeordnete Spoolman-Spulen zeigen ihre Restmenge auch dann, wenn mehrere Hersteller-Originaltags dieselbe Artikelkennung tragen. Automatische Kennungsverknüpfungen mit doppelter Kennung bleiben gesperrt; ebenso widersprüchliche, veraltete oder mehrfach vergebene manuelle Zuordnungen.

## 0.29.0-alpha.1

- Steuerungen bleiben zunächst geschlossen. „Steuerung öffnen“ blendet die vorhandenen Schaltflächen am ausgewählten Drucker ein; Statuswerte bleiben sichtbar. Druckerwechsel, Bereichswechsel, Anmeldewechsel, fehlende Freigabe und Verbindungsverlust schließen die Steuerung wieder. Bestehende Bestätigungen und serverseitige Schutzprüfungen bleiben erhalten.
- Restmengenquelle je Drucker wählbar: ACE mit Spoolman-Fallback oder ausschließlich Spoolman-Bestand. Damit lassen sich nicht nutzbare ACE-Nullwerte ohne Heuristik behandeln.
- ACE-Slots ohne gemeldete Restmenge zeigen bei aktueller eindeutiger Spoolman-Zuordnung Prozent, Gramm und Balken aus dem Buchbestand. Gemeldete ACE-Werte einschließlich 0 Prozent haben Vorrang. Die Quelle wird sichtbar genannt; kein automatischer Verbrauchsabzug.
- Berechnung verwendet das explizite Ausgangsgewicht der Spule. Ohne gültiges Ausgangsgewicht nur Gramm, ohne aktuelle Zuordnung keine Schätzung. Konflikte, leere Slots und veraltete Daten werden nicht als aktueller Bestand dargestellt.
- Spoolman-Bestand wird bei sichtbarer angemeldeter Oberfläche spätestens mit dem nächsten Statuslauf nach 30 Sekunden erneut gelesen; kein zusätzlicher Hintergrunddienst.

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
