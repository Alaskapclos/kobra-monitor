# Prüfstand

Stand **09.11.2026**. Quell-/Paketkandidat 0.43.0-alpha.4. Dieser Stand trennt eingefrorene Paketprüfungen, Besitzerberichte und offene Nachweise. Ältere Angaben stehen in [VALIDATION_HISTORY.md](VALIDATION_HISTORY.md).

## Neuer nativer Paketkandidat

549 Python-Prüffälle einschließlich separater Übernahme eines gestoppten 0.42-Profils, 14 Bridge-Grenzprüfungen und alle 27 JavaScript-Testdateien bestanden. Intel-Krypto und Windows-ARM-Krypto/PostgreSQL wurden neutral gebaut und unabhängig geprüft. Der eigene Intel-Kamerabau mit vollständiger Originalquelle bestand synthetische Bild-, HTTP-/Umleitungsschutz- und parallele H.264-Prüfungen. Native Mac-Programmläufe mit künstlichen Daten prüfen 0.42→0.43, Neustart, Spoolman und Sicherung/Wiederherstellung. Die exakte endgültige Paketkennung und deren Nachweis gehören zur jeweiligen Lieferdatei. Neue Windows-Gesamtpakete benötigen ihren eigenen Lauf auf Windows; die frühere Besitzerabnahme von 0.42 wird nicht übertragen. Kein produktives NAS-Update.

## Eingefrorene Paketstände

| Paketstand | Tatsächlicher Nachweis | Grenze |
| --- | --- | --- |
| Desktop 0.42, alle vier Architekturen | Vollständige ZIP-/Dateimanifestprüfung und Architekturprüfung; Quelle identisch. Besitzer bestätigt funktionierenden Windows x64, Windows ARM64, Intel Mac und Apple Silicon | Keine unabhängige vollständige Einzelgeräte-/Betriebssystemmatrix. Diese Binärpakete enthalten ihren damaligen Quellstand und damalige Docs. |
| Mac 0.42 | ARM nativ und Intel unter Rosetta: Konto, Spoolman mit Testspule 470 g, Start/Stop/Mehrfachstartschutz, explizite 0.40→0.42-Übernahme, Sicherung und isolierte Paarwiederherstellung, Daten nach Neustart; Originalprofile/Programme unverändert | Nur künstliche Testdaten. Freigabe-API mit leerer Druckerliste; gesonderte synthetische Freigabedatei nur im gestoppten Profil gesichert/zurückgelesen. Keine echten Druckerbefehle. |
| Windows ARM 0.42 | Native Quellbauten für die fehlenden ARM-Abhängigkeiten; vollständiger Laufzeit-/Importnachweis und späterer Besitzerbericht einschließlich dauerhafter Freigaben nach Neustart | Signierung und öffentlicher Liefernachweis sind separat. Nicht mit Linux ARM64 gleichsetzen. |
| Docker 0.43.0-alpha.1 | Unter Python 3.11 und 3.14 je 547 Tests und je 14 Bridge-Grenzprüfungen; alle 27 JS-Testdateien. 312 App-Dateien bytegleich zum eingefrorenen Quellpaket, exakte Bild-/Archivprüfung nach Transfer und Entpacken | Keine echten Druckerverbindungen oder NAS-Aktualisierung in diesem Bau. |
| Gemeinsame Docker-Suite 0.43 | Neuinstallation über Installer, Besitzeranmeldung, geschütztes eingebettetes Spoolman, Wiederaufnahme ohne Container-Neuanlage, Abweisung doppelter Installation, Neustart mit Daten, Sicherung und Start der Wiederherstellung in frischen Volumes | Künstlicher Bestand: eine Spule mit 470 g Buchrest, ein historischer Auftrag. Kein allgemeiner Test auf beliebigen NAS-Systemen. |
| Docker-LAN-Konfiguration 0.43 | Nur Monitor mit zusätzlichem Netz; Spoolman intern, Initialisierung/Sicherung ohne Netzwerk; lesender Standard | Leere Druckerliste. Der Netzkonfigurationstest ersetzt keine reale Erreichbarkeits-/Kameraabnahme. |
| Produktiver NAS-Nachweis 0.38 | Vor-/Nachsicherung isoliert geprüft, produktive Anmeldung, echte S1-Daten, Hilfe/Assets, Erhalt von Konten, Aufträgen, Berichten, Originalen und Zuordnungen | Historischer eigener Nachweis. Neue Docs oder Docker-Suite aktualisieren die produktive Installation nicht automatisch. |

0.43.0-alpha.2 wird als eigener Kandidat mit überarbeiteter Dokumentation vorbereitet. Seine endgültige Quell-/Paketprüfung wird separat festgehalten; kein Build wird allein durch Änderung der Versionsnummer als geprüft erklärt.

## Reale Besitzerbestätigungen

- Stock-Kobra-S1 im lokalen Netz; kein allgemeiner Nachweis für andere Anycubic-Modelle.
- Licht, Lüfter, Speed Mode, Temperaturen, Abbruch einschließlich Vorbereitung, X/Y/Z mit passender Z-Tischrichtung, Homing und Motoren-Aus bestätigt. Motoren-Aus beendete im gemeinsam beobachteten Fall den nach Homing laufenden Elektroniklüfter.
- Pause/Fortsetzen am zweiten S1 mit korrigierter Rückmeldung und tatsächlicher normaler Druckfortsetzung bestätigt.
- Erste X/Y/Z-Anwesenheitsbestätigung und anschließende Fahrten funktionieren laut Besitzer. Automatischer Reset bei neuem Druck ist automatisiert geprüft; der vollständige reale Reset-Ablauf bleibt offen.
- Originaldatei aus einem echten macOS-Anycubic-Slicer-Next-Sendecache erfasst, zugeordnet und gesichert/zurückgelesen; kein universeller Slicer-/Cachepfadnachweis.
- Archivwiederholung am zweiten Stock-S1 gestartet und erfolgreich abgeschlossen; passendes Ergebnis am 08.11.2026 vom Besitzer bestätigt. Keine unabhängige visuelle Qualitätsprüfung des Bauteils.
- iPhone-/Android-Push-Testempfang bestätigt; echter Druckende-Push auf einem Handy bestätigt, Plattform für dieses Ereignis nicht belegt. Keine pauschale Abnahme aller Meldungstypen.
- Individuelle ReSpool-SKU mit tatsächlichem Slot-Rückwechsel geprüft. Gemeinsame Hersteller-SKU bleibt Artikelkennung, nicht einzelne Spulenidentität.
- Desktop-Funktionsbestätigungen vom 09.11.2026 wie oben; daraus keinen vollständigen Hardware- oder Restoretest jedes einzelnen Pakets ableiten.

## Offen und bewusst begrenzt

Physischer ACE-Trocknungsstart/-stopp samt Rückmeldung und Achsenfreigabe-Reset nach einem neuen regulären Druck bleiben gesonderte Tests. Die Funktionen beginnen ohne Freigabe und müssen bis zu eigener Abnahme als Erprobung gelten. Keine künstlichen Druckerstörungen erzeugen.

Linux ARM64 und Raspberry Pi sind nicht gebaut/abgenommen. Öffentliche Binärlieferprüfung, Herausgebersignierung, Mac-Notarisierung, komfortable Versionsupdates, NAS-GUI-Installation und ein allgemeiner Wiederherstellungs-/Deinstallationsassistent sind nicht als fertig erklärt.

Drucker-TLS ist verschlüsselt, ohne verifizierte Brokeridentität. Nur vertrauenswürdiges Druckernetz, Fernzugriff über eigenes VPN/HTTPS. Kein öffentlicher Port.

ACE-Prozente und Spoolman-Buchgewichte sind getrennte Quellen; keine automatische Verbrauchsmessung oder Buchung. Verbindungsverlust ist kein Druckende, Befehlsversand ist kein Ausführungs-/Stillstandsnachweis. Kamera ersetzt keine Anwesenheit bei Bewegung.

Monitor und Spoolman besitzen getrennte Datenbanken. Jede wird konsistent gesichert; es gibt keine gemeinsame atomare Transaktion. Ein isolierter Restore und eine private Kopie sind keine kontinuierliche externe Sicherung. Manuelle Sonderstände beweisen keinen regulären Nachtzyklus.

[Freigabecheckliste](RELEASE.md) · [Paketübersicht](PLATFORM_SUPPORT.md) · [Sicherheit](../SECURITY.md).
