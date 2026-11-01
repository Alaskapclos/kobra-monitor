# Projektplan und aktueller Stand

Abgleich vom 01.11.2026 mit dem ursprünglichen Gespräch „Tool Schwierigkeit Einschätzen“ und den späteren Nutzerentscheidungen. Dies ist die gemeinsame Arbeitsgrundlage; geplante Punkte sind keine zugesicherten fertigen Funktionen.

## Leitlinien

- Stock-Firmware zuerst; Rinkhals/Klipper optional, keine Voraussetzung.
- Bestehende OSS-Projekte und APIs nutzen. OrcaSlicer bleibt unverändert.
- Spoolman ist die zentrale Spulendatenbank; der Monitor hält nur Verknüpfungen.
- Spoolman-eigene NFC-/RFID-/QR-Funktionen bevorzugen. ReSpool nur bei nachgewiesenem Zusatzbedarf; Nutzer hat am 31.10.2026 ausdrücklich weniger Tools gewünscht. NFC/OpenPrintTag-Kompatibilität vor eigener Implementierung prüfen.
- Einfache Einrichtung auf Rechner oder NAS/Server. Privates GitHub-Repository zunächst beibehalten.
- Fernzugriff über eigenes VPN/Tailscale und Benutzerkonto; keine öffentliche Druckerfreigabe.
- Aktueller Betrieb ausschließlich lesend gegenüber den Druckern. Der Nutzer hat am 01.11.2026 festgelegt: zuerst die Lesefunktionen vollständig abschließen; erst danach den Steuerbereich beginnen. Spoolman-Verbrauchsbuchungen sind eine gesonderte Schreibfunktion, keine Lesefunktion.

## Bereits umgesetzt und praktisch geprüft

Lokaler Zwei-Drucker-Betrieb, Stock-S1-Status/Temperaturen/ACE, Druckhistorie und Berichte, NAS-Betrieb und isolierte Sicherungswiederherstellung, Benutzerkonto, HTTPS über Tailscale, einfache Druckereinrichtung, gespeicherte Reihenfolge, Kameraübersicht, Web-Push-Testempfang auf iPhone und Android, Betriebsstatus und Druckerkarten mit Einzelwerten.

Offene praktische Nachweise: erste reguläre 24-Stunden-Sicherung am 01.11.2026 mit Manifest, Prüfsummen und isolierter Vollwiederherstellung erfolgreich geprüft; Druckende-Push wurde inzwischen vom Nutzer auf einem Handy bestätigt; Plattform nicht angegeben. Fehler-/Abbruch-/Verbindungsverlust-Meldungen aus realen Ereignissen bleiben separat zu prüfen. Sonderstände ersetzen den täglichen Zyklus nicht.

## Nächste Schritte in dieser Reihenfolge

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

## Abnahme des Lesebetriebs vor dem Steuerbereich

1. Spulenanzeige: automatische Erkennung klar von fester Slotbindung unterscheiden; Doppelbindungen verhindern. Nachweise für getestete Kombinationen und Grenzen dokumentieren.
2. Spulendaten: Frische, Verlust des Bestands und Wiederanlauf mit vorhandenen Verknüpfungen prüfen. Native Spoolman-Sicherung eines echten Bestands separat isoliert prüfen; Monitorbackup allein genügt nicht. Weitere NFC-/QR-Formate nur nach belegtem Bedarf und Kompatibilitätsnachweis.
3. Betrieb: Status/Temperaturen/Kamera bei Verbindungsverlust klar als veraltet kennzeichnen; Wiederverbindung, Mehrfachbrowser und kleine Bildschirme prüfen. Fehler-/Ausfallmeldungen zunächst mit isolierten Testdaten prüfen; Druckerfehler nicht künstlich auslösen.
4. Einrichtung und Dokumentation: Rechner/NAS, VPN-Zugang, Sicherung/Wiederherstellung und bekannte Grenzen nachvollziehbar beschreiben; automatisierte Prüfungen und gezielte Praxistests abschließen.
5. Abschluss mit dem Nutzer: verbleibende Einschränkungen gemeinsam bewerten. Erst danach den getrennten Steuerbereich planen und freigeben. Keine Steuerbefehle im aktuellen Ausbau.

Materialbedarf und Kosten bleiben im Gesamtplan. Belastbare Verbrauchserfassung ist hierfür eine gesonderte Datenfrage; ACE-Prozentwerte liefern keinen gemessenen Grammverbrauch.
