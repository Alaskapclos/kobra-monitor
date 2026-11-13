# Historischer Projektplan

Fortgeschrieben am 04.11.2026; ursprünglicher Abgleich vom 01.11.2026 mit dem ursprünglichen Gespräch „Tool Schwierigkeit Einschätzen“ und den späteren Nutzerentscheidungen. Dies ist die gemeinsame Arbeitsgrundlage; geplante Punkte sind keine zugesicherten fertigen Funktionen.

## Leitlinien

- Stock-Firmware zuerst; Rinkhals/Klipper optional, keine Voraussetzung.
- Bestehende OSS-Projekte und APIs nutzen. OrcaSlicer bleibt unverändert.
- Spoolman ist die zentrale Spulendatenbank; der Monitor hält nur Verknüpfungen.
- Spoolman-eigene NFC-/RFID-/QR-Funktionen bevorzugen. ReSpool nur bei nachgewiesenem Zusatzbedarf; Nutzer hat am 31.10.2026 ausdrücklich weniger Tools gewünscht. NFC/OpenPrintTag-Kompatibilität vor eigener Implementierung prüfen.
- Einfache Einrichtung auf Rechner oder NAS/Server. Privates GitHub-Repository zunächst beibehalten.
- Fernzugriff über eigenes VPN/Tailscale und Benutzerkonto; keine öffentliche Druckerfreigabe.
- Standardmäßig lesender Betrieb. Seit 02.11.2026 sind Kammerlicht und die drei Lüfter optional pro S1 freigegeben. Licht ohne Zusatzdialog; Lüfterstufe erst nach OK. Physische Abnahme aller vorhandenen Steuerungen auf PC und Handy durch den Besitzer bestätigt. Weitere Steuerfunktionen benötigen eine eigene begrenzte Implementierung; keine allgemeine beschreibbare Bridge. Spoolman-Verbrauchsbuchungen bleiben eine gesonderte Schreibfunktion.

## Bereits umgesetzt und praktisch geprüft

Lokaler Zwei-Drucker-Betrieb, Stock-S1-Status/Temperaturen/ACE, Druckhistorie und Berichte, NAS-Betrieb und isolierte Sicherungswiederherstellung, Benutzerkonto, HTTPS über Tailscale, einfache Druckereinrichtung, gespeicherte Reihenfolge, Kameraübersicht, Web-Push-Testempfang auf iPhone und Android, Betriebsstatus und Druckerkarten mit Einzelwerten.

Offene praktische Nachweise: erste reguläre 24-Stunden-Sicherung am 01.11.2026 mit Manifest, Prüfsummen und isolierter Vollwiederherstellung erfolgreich geprüft; Druckende-Push wurde inzwischen vom Nutzer auf einem Handy bestätigt; Plattform nicht angegeben. Fehler-/Abbruch-/Verbindungsverlust-Meldungen aus realen Ereignissen bleiben separat zu prüfen. Sonderstände ersetzen den täglichen Zyklus nicht.

## Aktueller Steuerbereich (Stand 0.27.1)

- Kammerlicht: direkter Schalter neben der Glühbirne, physisch bestätigt.
- Bauteil-, Zusatz- und Kammerlüfter: Einstellen direkt am Wert, Stufendialog mit OK/Abbrechen, physisch auf PC und Handy bestätigt.
- Speed Mode: Auswahl von Silent, Standard und Sport mit OK-Bestätigung direkt am Wert, nur während eines aktuellen laufenden Drucks. Vom Besitzer praktisch bestätigt.
- Speed Mode vom Besitzer bei laufendem Druck praktisch bestätigt (02.11.2026). Solltemperaturen für Düse und Bett mit eigener OK-Bestätigung in 0.25 implementiert; vom Besitzer direkt am Drucker bestätigt.
- Manuelle X/Y/Z-Schritte und getrennte Homing-Tasten für Druckkopf X/Y und Druckbett Z in 0.27.1 installiert und vom Besitzer praktisch bestätigt. Z-Plus bewegt den Tisch hoch, Z-Minus herunter. Erste X/Y/Z-Fahrt mit Anwesenheitsbestätigung, weitere Fahrten bis zum nächsten regulären Druck ohne Dialog; Homing immer einzeln bestätigt. Ein neuer Druck einschließlich Vorbereitung widerruft die Freigabe serverseitig. Homing-Wartezeit30s, Einzelschritt5s. Der Freigabe-Reset nach einem neuen realen Druck bleibt separat zu prüfen.
- Pause, Fortsetzen und Abbruch implementiert. Abbruch auch während Vorbereitung/Bettnivellierung vom Besitzer bestätigt; Pause am zweiten S1 physisch bestätigt; korrigierte Fortsetzen-Rückmeldung noch separat erneut zu prüfen.
- Dateiübertragung zum Drucker/Druckstart, Filamenttransport und Trocknungssteuerung noch nicht umgesetzt. Das zusätzliche NAS-Originalarchiv ist separat unter 0.28 beschrieben.
- Frische, exakte Ziel-/Verbindungsprüfung, Einmalversand, kein automatischer Wiederholungsversuch und Schaltprotokoll bleiben verbindlich.

## Gesamtplan (ursprüngliche Reihenfolge)

1. **Spoolman-Grundlage:** bestehendes offizielles OSS unverändert als eigenen Dienst betreiben; Bestand lesend anbinden, Spulen manuell ACE-Slots zuordnen. Herkunft/Frische der Gewichtsangaben sichtbar halten. Spoolman-Daten separat sichern; Monitor-Zuordnung im bisherigen Backup erhalten.
2. **Spulen im Alltag:** native Spoolman-Verwaltung zugänglich machen; Spulenwechsel und doppelte Zuordnungen verständlich lösen. Vorhandene Daten aus anderen Diensten nur über belegte Export-/Importmöglichkeiten übernehmen.
3. **ReSpool/NFC/QR:** tatsächliche Tag-Identitäten und Lesedaten der Stock-Drucker prüfen. ReSpool-ID ↔ Spoolman-ID ↔ ACE-Slot verbinden; aktuelle Spoolman-Tag-Funktionen wiederverwenden. OpenPrintTag-/Anycubic-/ReSpool-Tags nicht ohne Test als untereinander austauschbar behandeln. QR über Spoolman nutzen.
4. **Verbrauchsbuchung:** verlässlichen Verbrauch je Spule und Druck nachweisen; Vorbereitung, Farbwechsel/Spülung, Abbruch, Wiederanlauf und Doppelbuchungen berücksichtigen. ACE-Prozentwerte nicht als gemessene Gramm oder Buchungsgrundlage ausgeben. Fehlende Daten transparent lassen.
5. **Materialprüfung und Kosten:** benötigtes Material mit verfügbaren Spulen abgleichen; Kosten aus belegtem Verbrauch und hinterlegten Preisen.
6. **Original-Orca/Moonraker:** Schnittstellen mit vorhandenen Komponenten nutzen; Upload/Start zunächst getrennt testen und nur nach entsprechender Nutzerfreigabe für aktive Druckfunktionen ermöglichen.
7. **Warteschlange und Druckerwahl:** Jobs, Material-Matching, Reservierungen, intelligente Druckerwahl. Nicht automatisch auf unpassenden oder belegten Druckern starten.
8. **Wartung und Integrationen:** Wartungsintervalle, Home Assistant, optionale Klipper/Rinkhals-Erweiterungen und größere Flotten.

## Abweichungen von der ursprünglichen Architektur

Der frühe Spike führte zunächst zu einem bewährten lesenden Monitor. Cloud-Ersatz, Inventar und Druckmanagement bleiben das größere Ziel. Die dokumentierten GPL-/Apache-Anpassungen an vorhandenen Komponenten sind ein Zwischenstand; eine spätere saubere Upstream-/Adapter-Aufteilung bleibt zu prüfen. Ein Upstream-Kontakt oder Pull Request wurde noch nicht versendet. Öffentliche Kommunikation erfolgt nur nach ausdrücklichem Auftrag.

## Stand 0.18

Lokale ACE-SKU wird übernommen; explizit bestätigte eindeutige Kennungen sind dauerhaft mit Spoolman-IDs verknüpfbar. Wiedererkennung bei Slotwechsel mit Frische-/Duplikat-/Konfliktprüfung implementiert. Praktischer Einzelspulentest auf Stock-S1 mit vollständiger ReSpool-Kennung und Slot-Rückwechsel ohne Zuordnungskorrektur bestätigt; erster Wechsel erforderte das Lösen einer alten festen Bindung. Kein Tag-Schreiben, keine Spoolman-Verbrauchsbuchung. Zuerst Bedienung und Lesefunktionen gemäß folgender Abnahme abschließen. Optionale Slicer-Bedarfsdaten sind Schätzungen; Verbrauchsbuchung und Steuerung folgen als eigene spätere Schritte. Monatliche App-Abos sind keine Voraussetzung.

## Historische Abnahmegrundlage des Lesebetriebs vor dem Steuerbereich

1. Spulenanzeige: automatische Erkennung klar von fester Slotbindung unterscheiden; Doppelbindungen verhindern. Nachweise für getestete Kombinationen und Grenzen dokumentieren.
2. Spulendaten: Frische, Verlust des Bestands und Wiederanlauf mit vorhandenen Verknüpfungen prüfen. Native Spoolman-Sicherung eines echten Bestands ist separat isoliert geprüft (alle neun Tabellen, Schema, Integrität und Datenbeziehungen). Nächtlichen Ablauf noch separat belegen; einmalige Mac-Kopie bytegleich und isoliert geprüft, fortlaufende externe Kopien nicht eingerichtet. Monitorbackup allein genügt nicht. Weitere NFC-/QR-Formate nur nach belegtem Bedarf und Kompatibilitätsnachweis.
3. Betrieb: Status/Temperaturen/Kamera bei Verbindungsverlust klar als veraltet kennzeichnen; Wiederverbindung, Mehrfachbrowser und kleine Bildschirme prüfen. Fehler-/Ausfallmeldungen zunächst mit isolierten Testdaten prüfen; Druckerfehler nicht künstlich auslösen.
4. Einrichtung und Dokumentation: Rechner/NAS, VPN-Zugang, Sicherung/Wiederherstellung und bekannte Grenzen nachvollziehbar beschreiben; automatisierte Prüfungen und gezielte Praxistests abschließen.
5. Abschluss mit dem Nutzer: verbleibende Einschränkungen gemeinsam bewerten. Erst danach den getrennten Steuerbereich planen und freigeben. Diese historische Vorgabe wurde durch die gesonderte Licht-/Lüfterfreigabe vom 02.11.2026 erweitert; weitere Funktionen bleiben getrennt freizugeben.

Materialbedarf und Kosten bleiben im Gesamtplan. Belastbare Verbrauchserfassung ist hierfür eine gesonderte Datenfrage; ACE-Prozentwerte liefern keinen gemessenen Grammverbrauch.

## Öffentliche Alpha vorbereiten

Besitzer möchte am 03.11.2026 eine öffentliche GitHub-Freigabe nach den nächsten praktischen Steuerprüfungen vorbereiten. README muss exakt zur freizugebenden Version passen und vorhandene Funktionen, Grenzen und offene Nachweise unterscheiden. Vor Veröffentlichung Repository-Inhalt und Bild-/Artefaktdateien auf private Laufzeitdaten prüfen. Noch keine öffentliche Freigabe oder Änderung der Sichtbarkeit autorisiert.

## Originaldatei-Archiv 0.28 – implementiert, Praxisabnahme erfolgt

Fertige Slicer-Sendepakete zusätzlich archivieren, vollständige Integritätsprüfung, private Originaldownloads, manuelle ausdrückliche Auftragszuordnung und unveränderte alte Berichtsversionen. Ein macOS-Anmeldehelfer mit dauerhafter Warteschlange unterstützt den beobachteten Anycubic-Sendecache. Synthetische Übertragung, NAS-Ausfallverhalten und vollständige Wiederherstellung geprüft; reale Helfereinrichtung und ein echter Slicerauftrag einschließlich Original-Wiederherstellung sind inzwischen praktisch bestätigt. Ein Cachepfadwechsel kann Übernahmen verhindern und darf nicht als vollständige Erfassung ausgegeben werden. Nachdruckstart, automatischer Speicherbereinigungsplan und herstellerübergreifende Slicerunterstützung folgen separat.


## Aktueller Stand 0.29.2 (04.11.2026)

0.29.2 auf dem NAS installiert, Desktop und schmale Ansicht sowie Vor-/Nachsicherung mit vollständiger isolierter Wiederherstellung geprüft. Steuerung öffnet bewusst per Button direkt über der Achsensteuerung. Restmengenquelle je Drucker ist wählbar; eindeutige manuelle Zuordnungen funktionieren auch bei gemeinsamer Hersteller-Artikelkennung. Originaldatei-Erfassung aus dem realen Slicer-Cache und Wiederherstellung echter archivierter Dateien sind inzwischen belegt.

Die korrigierte Fortsetzen-Rückmeldung wurde praktisch bestätigt; der Achsen-Anwesenheitsreset nach einem neuen regulären Druck bleibt separat abzunehmen. Archivwiederholung liegt inzwischen als 0.36-Erprobungsstand vor, mit getrennt gesperrter Startfreigabe und noch offener realer Stock-S1-Abnahme. Verbrauchsbuchung ist nicht umgesetzt.

## Aktueller Stand 0.30 und Vorbereitung 0.30.1

Kompakte ACE-/Spulenübersicht je Druckerkachel, unabhängig von der gewählten Detailansicht, mit derselben Darstellung und Restmengenquelle wie unter Spulen. 0.30 ist auf dem NAS installiert und nach Nutzeranmeldung auf Desktop und in390px-Ansicht geprüft. Beide echten Drucker zeigen getrennte Quellen/Restmengen; Vor-/Nachsicherung vollständig isoliert wiederhergestellt. Linuxbau mit326 Python- und14 Bridge-Prüfungen je Laufzeit sowie246 JS-Fällen bestanden.

Der eingeschränkte dauerhafte Bauzugang zur separaten Linux-VM wurde nach ausdrücklicher Freigabe eingerichtet und durch einen vollständigen Bau samt verschlüsseltem Paketdownload abgenommen. Keine Änderung der NAS-Verwaltungszugänge.

0.30.1 beschränkt das Ein-/Ausblenden auf Achsen und Homing; übrige freigegebene Steuerungen bleiben sichtbar. README und aktueller Prüfstand werden für die öffentliche Alpha bereinigt. Abschließende Nachweise und offene Punkte: [Freigabecheckliste](RELEASE.md).

## ACE-Erweiterung 0.37 (07.11.2026)

ACE-Temperatur, verfügbare Luftfeuchte und bestätigte Trocknung direkt in den Übersichtskacheln; eigener bestätigter Heizdialog. Lokal 482 Python-Prüfungen, 14 Bridge-Leseschutzprüfungen und 25 JavaScript-Prüfdateien erfolgreich. Desktop und390px mit künstlichen Geräten geprüft. Der Besitzer meldet einen laufenden Wiederholungsdruck; erfolgreicher Abschluss und neuer ACE-Heizschalter sind noch separat abzunehmen. Linuxbau und NAS-Installation dieses Stands noch offen.

Die Kennungskorrektur aus dem realen ersten Archivstart wird gesondert geprüft: begrenzte neue Startkennungen, bekannte alte Aliaswerte nur mit bestätigtem Versandbeleg, ein fortlaufender Auftrag und erhaltene Archivherkunft. Frühere fehlerhafte Fragmente bleiben erhalten; keine vollständige nachträgliche Beobachtung behaupten.

Aktueller Projektplan: [ROADMAP.md](../ROADMAP.md).
