# Historische Prüfnachweise

Stand 07.11.2026. Entwicklungsziel **0.36.0-alpha.1**, zuletzt produktiv geprüft **0.35.0-alpha.1**. Implementierte Funktion, automatisierter Test und physische Bestätigung sind unterschiedliche Nachweise. Ein bestandener früherer GitHub-Lauf gilt nicht als Prüfung des aktuellen Quellstands.

## Erprobungsstand 0.36

Dateivorprüfung, enger Original-Upload/Starttransport, persistenter Zweischritt, aktuelle ACE-/Verbindungsbindung, Besitzer-/CSRF-/Origin-API und mobile Oberfläche sind im Quellstand integriert. Ein tatsächlicher Browserdurchlauf mit ausschließlich simuliertem Drucker bestätigt die separate Startfreigabe, genau einen Schreibaufruf an den Fake-Socket, neuen Historienauftrag, automatische Originalzuordnung und unveränderte ursprüngliche Berichtsversion. Desktop und 390-Pixel-Ansicht geprüft, Dokumentbreite bei 390 Pixeln 375 Pixel. Keine Browserwarnungen/-fehler im beobachteten Ablauf. Kein physischer Handytest.

**Offen:** realer Stock-S1-Originalpaket-Upload und Start, abschließender versionsgebundener Linuxbau sowie spätere NAS-Installation mit Vor-/Nachsicherung. Zusätzliche Startfreigaben bleiben leer. [Ablauf und Grenzen](REPRINT.md).

## Produktiver Vorschau-Stand 0.35

Linuxbau unter Python3.11/3.14 mit jeweils414 Anwendungs- und14 Bridge-Prüfungen,23 JavaScript-Testdateien, getrennter Suite-/Kamera-/Wiederherstellungsprüfung. NAS-Monitor und separater Sicherungsdienst aktualisiert; bestehende Daten erhalten, Vor-/Nachsicherung getrennt wiederhergestellt, angemeldete Vorschau am größten realen Original auf Desktop/390px geprüft. Keine Druckerbefehle durch die Vorschau. Dies ist kein Nachweis für die neuen 0.36-Schreibwege.

## Frühere Abnahme 0.30.1

| Prüfung | Stand |
| --- | --- |
| Begrenzung des Öffnen-Schalters auf Achsen/Homing | 250 JavaScript-Fälle sowie synthetische und produktive Desktop-/390px-Ansicht bestanden. Licht und drei Lüfter bleiben bei geschlossenem Achsenbereich sichtbar. Linuxbau und NAS-Update mit isolierter Vor-/Nachwiederherstellung erfolgreich. |
| Vollständige Python-, Bridge- und JavaScript-Prüfungen | Für0.30.1 bestanden: je326 Python- und14 Bridge-Prüfungen unter3.11/3.14 sowie250 JavaScript-Fälle.219 Quelldateien und214 Anwendungsdateien im Image geprüft. |
| README, Bedienhilfe und öffentliche Checkliste | Auf den tatsächlichen Funktionsumfang abgeglichen; verbleibende Praxisnachweise ausdrücklich benannt. |
| Veröffentlichungsinhalt | Quell-ZIP vor dem Bau auf private Laufzeitpfade, persönliche Installationsmarker und private Schlüssel geprüft. Endprüfung entfernter GitHub-Historien und aller endgültigen Veröffentlichungsartefakte bleibt erforderlich. |

## Zuletzt vollständig geprüfter Stand 0.30

| Bereich | Nachweis und Grenze |
| --- | --- |
| Linux / Python3.14 und3.11, amd64 | Je326 eigene Python-Tests und14 Bridge-Prüfungen erfolgreich. Bau auf getrennter Linux-VM, ohne reale Drucker in den Tests. |
| JavaScript | 246 Fälle, Syntax- und Release-Dateiprüfung erfolgreich. |
| Container und Originalarchiv | Start, synthetische Kamera, getrennte Sicherungswiederherstellung und Quellvergleich des Linux-Images erfolgreich. |
| NAS-Update | Monitor und Sicherungsdienst auf UGREEN DXP4800GT/UGOS aktualisiert. Bestehende Volumes erhalten; Vollsicherung davor/danach isoliert wiederhergestellt, SQLite-Integrität und private Dateien geprüft. |
| Produktive Oberfläche | Nach Besitzeranmeldung zwei echte S1-Kacheln, eigene ACE-/Spoolman-Quellen und Druckerwechsel geprüft. Desktop und390px-Ansicht; kein horizontaler Überlauf. Größenprüfung im Desktop-Browser ersetzt keinen zusätzlichen physischen Handytest. |
| Zugriffsschutz | Auslieferung über privates HTTPS geprüft; Status, Konfiguration, Spulen, Originaldateien und Steuerung ohne Sitzung gesperrt. |
| Weitere Plattformen | Frühere GitHub-CI-Läufe prüften macOS, Linux und Windows/Python3.11 und3.14. Kein aktueller0.30.1-Nachweis daraus; andere NAS-Modelle und ARM64 nicht praktisch bestätigt. |

## Reale Bedienungsnachweise

- Zwei Stock-Kobra-S1 im LAN auf macOS und auf dem NAS betrieben. Keine allgemeine Freigabe für andere Anycubic-Modelle.
- Licht, drei Lüfter, Speed Mode und Solltemperaturen vom Besitzer direkt am Drucker bestätigt; Bedienung auch auf PC und Handy bestätigt.
- Abbruch einschließlich Vorbereitung/Bettnivellierung, X/Y/Z, Z-Tischrichtung und getrenntes Homing praktisch bestätigt. Motoren-Aus-Befehl löste den nach Homing weiterlaufenden Elektroniklüfter im beobachteten Fall.
- Pause am zweiten S1 bestätigt. Am04.11.2026 Pause und Fortsetzen am zweiten S1 jeweils einmal gesendet und im Steuerprotokoll bestätigt. Besitzer bestätigt normale Fortsetzung; die Oberfläche zeigt „Fortsetzen vom Drucker bestätigt“. Der dabei laufende Druck wurde nicht als abgeschlossen gewertet.
- Erste X/Y/Z-Bestätigung und anschließende Fahrten funktionieren laut Besitzer. Der automatische Widerruf nach einem neuen regulären Druck einschließlich Vorbereitung ist automatisiert geprüft, der gesamte reale Ablauf bleibt offen.
- Originaldatei aus echtem Anycubic-Slicer-Next-Sendecache übernommen, ausdrücklich einem Auftrag zugeordnet und aus NAS-Sicherung wiederhergestellt. Das ist kein universeller Slicer- oder Cachepfadnachweis.
- Push-Testempfang auf iPhone und Android bestätigt; Meldung zu echtem Druckende auf einem Handy bestätigt, Plattform nicht belegt. Physischer Empfang jedes Fehler-/Abbruch-/Ausfalltyps ist nicht pauschal bestätigt. Keine künstliche Störung am echten Drucker erzeugen.
- Individuelle ReSpool-Kennung mit tatsächlichem Slot-Rückwechsel geprüft. Gemeinsame Hersteller-SKU bleibt eine Artikelkennung, keine eindeutige Spulenidentität.

## Verbleibende Grenzen

Die Druckeranbindung übernimmt den vorhandenen lokalen TLS-Handshake; eine verifizierte Broker-Zertifikatskette wird nicht zugesagt. Nur im vertrauenswürdigen Druckernetz einsetzen, Fernzugriff ausschließlich über eigenes VPN und geschützte Monitor-Oberfläche. Keine öffentliche Drucker- oder Monitor-Portfreigabe.

ACE-Prozente und Spoolman-Buchgewichte sind unterschiedliche Quellen; kein gemessener automatischer Verbrauch. Versand eines Befehls beweist weder Bewegung noch vollständigen Stillstand. Verlorene Verbindungen sind kein Druckende. Kamera und Monitor ersetzen keine Anwesenheit bei manuellen Fahrten.

Monitor und Spoolman haben getrennte Datenbestände und Sicherungen. Isolierte Wiederherstellung und eine zusätzliche private Kopie wurden praktisch geprüft; eine kontinuierliche externe Kopie wird nicht zugesagt. Der tatsächlich erfolgreiche native nächtliche Spoolman-Zyklus ist noch gesondert zu belegen.

Die aktuelle Entscheidung vor öffentlicher Freigabe steht in [RELEASE.md](RELEASE.md). Historische Testergebnisse wurden bei der Konsolidierung nicht als aktuelle Prüfung übernommen.

## ACE-Erweiterung 0.37

Automatisierte Protokoll-/Frische-/Rechteprüfungen und synthetische Desktop-/390px-Prüfung. Höhere ACE-2-Pro-Grenze ausdrücklich konfiguriert. Keine realen Heizbefehle; NAS-Bau, Installation und physische Abnahme bleiben separat.

Die Kennungskorrektur aus dem realen ersten Archivstart wird gesondert geprüft: begrenzte neue Startkennungen, bekannte alte Aliaswerte nur mit bestätigtem Versandbeleg, ein fortlaufender Auftrag und erhaltene Archivherkunft. Frühere fehlerhafte Fragmente bleiben erhalten; keine vollständige nachträgliche Beobachtung behaupten.

Endgültiger lokaler Prüfstand: 482 Python-Fälle, darunter neun zur Archivkennungs-Korrektur; 14 Bridge-Leseschutzfälle und 25 JavaScript-Prüfdateien. Der nachfolgende Linuxbau prüft exakt das verpackte Quellmanifest erneut.

Aktueller Prüfstand: [VALIDATION.md](VALIDATION.md).


---

## Vor der Bereinigung vom 09.11.2026

# Prüfstand der Alpha

Stand **0.38.0-alpha.1**, abgeglichen am08.11.2026. Implementierung, automatisierter Test und physische Besitzerbestätigung werden getrennt ausgewiesen. Historische Nachweise stehen in [VALIDATION_HISTORY.md](VALIDATION_HISTORY.md).

## Aktueller Linux-/NAS-Nachweis

| Bereich | Nachweis und Grenze |
| --- | --- |
| Linuxamd64 | Je482Python- und14Bridge-Prüfungen unter Python3.11 und3.14,26JavaScript-Prüfdateien bestanden. Keine echten Druckerverbindungen in diesen Tests. |
| Fertiges Image |293Anwendungsdateien bytegleich zum eingefrorenen0.38-Quellpaket, Image-Prüfsumme auf Bau-VM, Mac und NAS identisch. |
| Gemeinsame Suite | Monitor, Spoolman und Sicherung mit synthetischen Daten: Neuinstallation, Wiederanlauf, geschützter Spoolman-Zugang und getrennte Wiederherstellung erfolgreich. Kein allgemeiner Nachweis für beliebige NAS-Systeme. |
| Produktiver NAS-Stand | Monitor und separater netzwerkloser Sicherungsdienst auf0.38. Vor-/Nachsicherung isoliert wiederhergestellt; SQLite-Integrität, vorhandene Aufträge, Berichtsversionen, Originaldateien, Verknüpfungen, Konto, Einrichtung und Push-Geräte erhalten. Kein produktiver Restore. |
| Oberfläche und Zugriff | Nach Besitzeranmeldung zwei echte S1 mit frischen Daten,0.38-Hilfe und bytegleiche Assets geprüft. Geschützte APIs ohne Sitzung401. |
| Materialhinweis | Slicerbedarf gegen eindeutigen aktuellen Spoolman-Buchbestand; genug/Fehlmenge/echter Nullbestand/unbekannt, gemeinsame physische Spule und erkennbare Slotänderung getestet. Simulierter Desktop-/390px-Browser ohne horizontalen Überlauf; keine Druck-/Bestandsbefehle. Produktiv Hilfe und Auslieferung geprüft. |
| Aufzeichnung beim Update | Im begrenzten geprüften Neustartfenster rund5,5s unterbrochene Druckerverbindungen, maximal rund20,3s zwischen Stichproben; keine printer_error-Ereignisse in diesem Fenster. Kein vollständiger lückenloser Beobachtungsumfang behauptet. |
| Native Pakete | Windowsx64 und Intel-Mac als getrennte Teststände; keine pauschale Freigabe der ARM-Pakete. [Plattformmatrix](PLATFORM_SUPPORT.md). |

Der am07.11.2026 installierte0.38-Bau ist ein eingefrorener Nachweis. Spätere Dokument- oder Prüfwerkzeugänderungen im Arbeitsverzeichnis sind nicht automatisch im produktiven Image enthalten und benötigen vor einer Veröffentlichung ein neues konsistentes Quell-/Paketmanifest.

## Reale Besitzerbestätigungen

- Zwei Stock-Kobra-S1 im LAN unter macOS und auf dem NAS betrieben; keine allgemeine Freigabe weiterer Anycubic-Modelle.
- Licht, drei Lüfter, Speed Mode und Solltemperaturen direkt am Drucker bestätigt, Bedienung auch auf PC und Handy.
- Abbruch einschließlich Vorbereitung/Bettnivellierung, X/Y/Z, Z-Tischrichtung und getrenntes Homing bestätigt. Motoren-Aus beendete im gemeinsam beobachteten Fall den nach Homing laufenden Elektroniklüfter.
- Pause/Fortsetzen am zweiten S1 bestätigt, einschließlich korrigierter Monitor-Rückmeldung und tatsächlicher normaler Fortsetzung.
- Erste X/Y/Z-Anwesenheitsbestätigung und anschließende Fahrten funktionieren laut Besitzer. Automatischer Widerruf bei neuem Druck ist automatisiert geprüft; der vollständige reale Reset-Ablauf bleibt offen.
- Originaldatei aus echtem Anycubic-Slicer-Next-Sendecache übernommen, einem Auftrag zugeordnet und aus NAS-Sicherung wiederhergestellt; kein universeller Cachepfad-/Slicernachweis.
- Archivwiederholung am zweiten Stock-S1 vom Besitzer gestartet. Nach Korrektur der zu großen Auftragskennung blieb derselbe laufende Auftrag mit Archivbezug stabil. Am08.11.2026 bestätigt der Besitzer: erfolgreich abgeschlossen und Ergebnis passt. Keine unabhängige visuelle Qualitätsprüfung durch den Agenten.
- iPhone-/Android-Push-Testempfang bestätigt; echter Druckende-Push auf einem Handy bestätigt, Plattform nicht belegt. Nicht jeden realen Fehler-/Abbruch-/Ausfalltyp pauschal als geprüft ausgeben.
- Individuelle ReSpool-Kennung mit physischem Slot-Rückwechsel geprüft. Gemeinsame Hersteller-SKU bleibt Artikelkennung, keine individuelle Spulenidentität.

## Noch offene Abnahmen und Grenzen

ACE-Trocknungsstart/-stopp mit tatsächlicher Ausführung und passender Rückmeldung, Achsenfreigabe-Reset nach neuem regulären Druck sowie native Plattforminstallationen/Updates/Wiederherstellungen bleiben gesondert abzunehmen. Erfolgreiche native Mac-Netzwerkdiagnose ist kein Nachweis dauerhafter Verbindungen der korrigierten App auf dem iMac.

Drucker-TLS übernimmt den vorhandenen lokalen Handshake; keine verifizierte Broker-Zertifikatskette zugesagt. Nur im vertrauenswürdigen Druckernetz, Fernzugriff über eigenes VPN und geschützte Oberfläche. Keine öffentliche Portfreigabe.

ACE-Prozente und Spoolman-Buchgewichte sind unterschiedliche Quellen; kein gemessener automatischer Verbrauch. Materialhinweis ist eine Schätzung, keine Garantie. Befehlsversand beweist weder physische Ausführung noch Stillstand. Verbindungsverlust ist kein Druckende. Kamera und Monitor ersetzen keine Anwesenheit bei manuellen Fahrten.

Monitor und Spoolman haben getrennte Datenbanken und Sicherungen. Isolierte Wiederherstellung und zusätzliche private Kopien wurden geprüft; keine kontinuierliche externe Kopie zugesagt. Der tatsächlich erfolgreiche native nächtliche Spoolman-Zyklus ist gesondert zu belegen; manuelle Sonderstände ersetzen ihn nicht.

[Freigabecheckliste](RELEASE.md) · [Paketumfang](INSTALLERS.md).
