# Freigabecheckliste

Stand **09.11.2026**, Quell-/Paketkandidat **0.43.0-alpha.4**. Repository bleibt privat. Vorbereitung, privater Entwurf und öffentliche Veröffentlichung sind unterschiedliche Schritte. Ein Quellpaket, Docker-Abbild und native Binärpakete besitzen jeweils einen eigenen Prüfumfang.

Die neuen nativen Kandidaten verwenden die separat bereinigten Bibliotheken. Ihre vollständigen Paketkennungen und abschließenden Gesamtnachweise werden bei der jeweiligen Lieferdatei festgehalten. Besitzerberichte zu 0.42 werden nicht als Abnahme von 0.43 ausgegeben.

## Bereits belegt

- [x] Desktop-Testpakete 0.42 für Windows x64, Windows ARM64, Intel Mac und Apple Silicon gebaut; Dateikataloge und Architekturen geprüft. Besitzer bestätigt Funktion aller vier Fassungen.
- [x] Mac-Integration mit künstlichen Daten: ARM nativ, Intel unter Rosetta; Start/Stop, Datenübernahme, Sicherung und Wiederherstellung. Besitzerbericht am echten Intel-Mac getrennt festgehalten.
- [x] Windows-ARM-Abhängigkeiten einschließlich fehlender nativer Wheels aus nachvollziehbaren Quellen gebaut und unter Windows ARM geladen. Dauerhafte Freigaben nach Neustart vom Besitzer bestätigt.
- [x] Docker 0.43.0-alpha.1: unter Python 3.11 und 3.14 je 547 Tests, je 14 Bridge-Grenzprüfungen, alle 27 JS-Testdateien; Neuinstallation, geschütztes Spoolman, Neustart, Paarrestore und LAN-Netzzuordnung mit künstlichen Daten bestanden.
- [x] Früherer produktiver NAS-Nachweis 0.38 einschließlich Konten-/Auftrags-/Archivdatenerhalt und getrennter Vor-/Nachwiederherstellung bleibt erhalten. Neue Kandidaten aktualisieren ihn nicht automatisch.
- [x] Licht, Lüfter, Speed Mode, Temperaturen, Abbruch einschließlich Vorbereitung, Achsen/Homing und Pause/Fortsetzen mit realen Besitzerbestätigungen. Archivwiederholungsdruck erfolgreich abgeschlossen; passendes Ergebnis bestätigt.
- [x] Remote-Historie getrennt gelesen: alle vier von GitHub gemeldeten Referenzen einschließlich PR-Kopf/Merge, 80 erreichbare Commits, 79 Bäume, 901 unterschiedliche Blobs. Blob-Hashes und Elternabdeckung geprüft; keine Treffer der definierten privaten Pfad-/Schlüssel-/Adressregeln. Ein historisches Beispielbild visuell geprüft, ohne EXIF/Kommentar.
- [x] Aktuelle Einstiegsdokumentation, Plattformmatrix und Hilfe unterscheiden Desktop 0.42, Docker 0.43 und den neuen Kandidaten. Ältere Prüfstände bleiben als Historie erhalten.
- [x] Komponenteninventar der vier nativen Pakete: je 24 Monitor- und 46 Spoolman-Abhängigkeiten samt tatsächlich enthaltenen Lizenzdateien erfasst. Fehlender vollständiger http-ece-MIT-Text im Quellkandidaten ergänzt. Alte ZIPs unverändert.

Die Historienprüfung ist eine begrenzte Regel-/Pfadprüfung, keine Garantie gegen beliebige versteckte Geheimnisse. Sie umfasst aktuell von GitHub gemeldete Referenzen; nicht mehr gemeldete gelöschte Objekte können hier nicht aufgezählt werden. Ein Dateiscan ersetzt keine Bilder-/Inhaltsprüfung. Ein Besitzerbericht ist keine vollständige Einzelgeräte-Abnahmematrix.

## Letzte Kontrolle des konkreten Quellkandidaten

- [ ] Den endgültigen Kandidaten einfrieren und sein vollständiges BUILD-Dateimanifest prüfen. Neue Dokumentation gehört nicht rückwirkend zu bereits gebauten Paketen.
- [ ] Den exakt eingefrorenen Quell-ZIP erneut unabhängig auf private Daten, Versionen, sichere Pfade, lokale Dokumentlinks und passende Lizenzdateien prüfen.
- [ ] README, Hilfe, Versionsdatei, Compose-Dateien, Paketübersicht, bekannte Grenzen und Release-Text gegeneinander kontrollieren.
- [ ] Endgültigen Dateiumfang gegen den privaten GitHub-Stand prüfen und den konkreten privaten Entwurf reviewbar bereitstellen. Keine persönliche Historie/Archive aus dem Arbeitsordner hinzufügen.
- [ ] Nach jeder Änderung am endgültigen Stand die betroffenen Prüfungen erneut ausführen. Historische CI-Läufe oder Tests einer anderen Paketkennung nicht als aktuellen Nachweis ausgeben.

## Sperren vor öffentlicher Binärauslieferung

Die [Lizenzanforderungen für die Auslieferung](DISTRIBUTION_LICENSES.md) beschreiben die Zuordnung zu den tatsächlichen Lieferdateien. Für FFmpeg ist ein separates Kamera-Baurezept im Quellstand enthalten.

- [ ] **Private Baupfade entfernen:** einige selbst gebaute Windows-ARM- und Intel-Mac-Bibliotheken enthalten persönliche Compiler-/Baupfade. Aus neutralen Verzeichnissen mit passenden Pfadabbildungen neu bauen und erneut im endgültigen Paket prüfen. Nicht nachträglich an signierten Binärdateien herumändern.
- [ ] **Alte Diagnosevorgabe ersetzen:** die privaten 0.42-Testpakete enthalten noch den früheren festen LAN-Diagnosewert. Im neuen Quellkandidaten ist `--ip` ausdrücklich erforderlich; alte ZIPs bleiben gesperrt und müssen für eine öffentliche Lieferung aus dem bereinigten Stand neu paketiert werden.

- [ ] **Passende Drittquellen und Bauangaben:** für die tatsächlich enthaltenen FFmpeg-Varianten und ihre Bibliotheken vollständig zusammenstellen. Ein Projektlink und ein Lizenzname allein sind kein vollständiger konkreter Liefernachweis. Bei Docker das gesamte auszuliefernde Abbild betrachten, nicht nur Monitor-Pythondateien.
- [ ] **Alle Originalhinweise:** Python, Spoolman einschließlich Weboberfläche, Python-Abhängigkeiten, Datenbank-/Kryptobibliotheken, Schriften und Kameralaufzeiten paketbezogen abnehmen. Die Ergänzung des http-ece-Lizenztexts im Quellkandidaten ändert nicht die älteren signierten Testprogramme.
- [ ] **Herausgebernachweis:** öffentliche Windows-Signierung und Mac Developer ID/Notarisierung einrichten. Ad-hoc-Signatur, Prüfsumme und eine Signatur eines einzelnen upstream-Bausteins sind kein öffentlicher Herausgebernachweis des Gesamtpakets.
- [ ] **Exakte Lieferdateien:** endgültige Quellen und Binärdownloads mit Version, Architektur, Herkunft, Dateikatalog, Prüfsumme und verbliebenen Grenzen festlegen und nach dem Packen erneut prüfen.

Solange diese konkreten Binärsperren offen sind, die bisherigen technischen Test-ZIPs nicht als vollständig freigegebene öffentliche Komplettinstaller anbieten. Ein privater Entwurf kann sie zur weiteren Prüfung referenzieren. Eine begrenzte öffentliche Quellalpha und eine öffentliche Binärfreigabe sind getrennte Entscheidungen.

## Praktische Grenzen, die sichtbar bleiben müssen

- Physischer ACE-Trocknungsstart/-stopp samt Rückmeldung und Achsenfreigabe-Reset nach neuem regulären Druck bleiben gesondert zu bestätigen. Die Funktionen beginnen gesperrt und bleiben bis eigener Abnahme Erprobungsfunktionen.
- Nicht alle Betriebssystem-/Firmware-/ACE-/NAS-Kombinationen sind geprüft; keine pauschale Freigabe aus automatisierten Tests ableiten.
- Komfortable Auto-Updates, allgemeiner Restore-/Deinstallationsassistent und einfacher NAS-GUI-Installationsweg sind nicht fertig.
- Raspberry Pi/Linux ARM64 ist zurückgestellt und kein geprüfter Download.

Diese Grenzen verhindern keine klar beschriebene Quellalpha mit lesendem Standard. Echte Druckeraktionen sind kein Teil der Dokument- oder GitHub-Prüfung.

## Veröffentlichung

Erst nach ausdrücklichem Veröffentlichungsauftrag einen öffentlichen Release erstellen oder die Repository-Sichtbarkeit ändern. Vorher den genauen Versionsstand, Downloadumfang und die verbleibenden Grenzen vorlegen. Keine Passwörter, Einrichtungsschlüssel, Sicherungen, Kundendaten, Druckoriginale oder persönlichen Screenshots hochladen.

Quellprüfung:

```sh
python scripts/release_check.py
python scripts/release_check.py --source-zip /pfad/Kobra-Monitor.zip --check-build
```

Im Arbeitsverzeichnis verwendet die Prüfung Git zur Dateiauswahl. In einem Quellcontainer ohne Git müssen sämtliche Dateien zum vollständigen eingefrorenen Katalog passen. Zusätzliche/geänderte Dateien, unsichere Pfade und private Laufzeitdaten werden abgewiesen. Dies prüft Integrität, nicht rechtliche Vollständigkeit oder Herausgeberauthentizität.

[README](../README.md) · [Plattformen](PLATFORM_SUPPORT.md) · [Prüfstand](VALIDATION.md) · [Fremdhinweise](../NOTICE.md) · [Ältere Freigabechecklisten](RELEASE_HISTORY.md).
