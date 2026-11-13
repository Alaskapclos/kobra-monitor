# Projektplan und aktueller Stand

Stand **0.43.0-alpha.2**,09.11.2026. Desktop-Testpakete 0.42 und Docker-Testpaket 0.43 sind getrennte eingefrorene Nachweise. Historische Entwicklungsstände und ursprüngliche Reihenfolge: [Projektverlauf](docs/ROADMAP_HISTORY.md). Geplante Funktionen sind keine fertigen Zusagen.

## Verbindliche Leitlinien

- Standard-Firmware und vorhandene Schnittstellen. Keine Modifikationen an Drucker, ACE oder Slicer und keine Rinkhals-/Klipper-Abhängigkeit.
- Monitor als zentrale Beobachtungs-, Steuerungs-, Spulen- und Berichtszentrale. Neue Modelle in Orca oder Anycubic Slicer Next slicen und erstmals senden; erfolgreiche Archivdrucke bewusst über den Monitor wiederholen.
- Spoolman bleibt zentrale Bestandsdatenbank. Der Monitor hält Zuordnungen und Herkunft der Angaben; keine parallele Bestandsdatenbank ohne begründeten Bedarf.
- Private Nutzung mit lokalem Konto und VPN/HTTPS. Standardmäßig lesende Druckeranbindung; jede Steuerfunktion gesondert pro Drucker freigeben. Kein automatisches Wiederholen unklar ausgegangener Befehle.
- Einfache Komplettinstallation und Updates. Native Downloads für Windowsx64, WindowsARM64, macOSIntel und AppleSilicon; Server/NAS als gemeinsames Projekt mit getrennten Monitor-/Spoolman-/Sicherungscontainern.

## Umgesetzt

Zwei Stock-Kobra-S1 im LAN, Status/Temperaturen/ACE-Klima und Spulen, Kameraübersicht, Historie, feste Kundenberichte, Originaldatei-Archiv und Vorschau, Konto/VPN/Push, eingebettete Spoolman-Verwaltung und eindeutige SKU-/Slotzuordnung. Licht, Lüfter, Speed Mode, Solltemperaturen, Pause/Fortsetzen/Abbruch, Achsen/Homing und Motoren-Aus sind begrenzt optional implementiert. ACE-Trocknung besitzt einen gesonderten bestätigten Dialog.

Archivwiederholung mit getrenntem Übertragen/Starten ist am zweiten Stock-S1 einschließlich erfolgreichem Abschluss vom Besitzer bestätigt. Die beobachtete Kennungsaufspaltung wurde in0.37 korrigiert; frühere Fragmente und Quellberichte bleiben erhalten.0.38 ergänzt einen lesenden Materialhinweis gegen aktuellen eindeutig zugeordneten Spoolman-Buchbestand; keine automatische Buchung oder Verbrauchsmessung.

Linuxbau/NAS-Update0.38 mit getrennter Vor-/Nachwiederherstellung und produktiver Anmeldung geprüft. Aktuelle Nachweise und praktische Grenzen: [VALIDATION.md](docs/VALIDATION.md).

## Jetzt: öffentliche Alpha vorbereiten

1. Dokumentation und Freigabecheckliste auf den tatsächlichen aktuellen Funktions-/Prüfstand bringen; vergangene Arbeitsstände getrennt aufbewahren.
2. Verbleibende echte Tests: Achsenfreigabe-Reset nach regulärem Druck und ACE-Trocknungsstart/-stopp. Keine künstlichen Druckerstörungen erzeugen.
3. Die vier nativen 0.42-Pakete sind gebaut und vom Besitzer als funktionierend bestätigt. Öffentliche Liefer-/Signierungsprüfung und die Grenzen der Einzelgeräteabnahmen dokumentieren. Docker 0.43 ist mit künstlichen Daten geprüft. Linux ARM64/Raspberry Pi bleibt zurückgestellt. Komfortable Updates, vollständige Sicherungs-/Wiederherstellungsführung und Datenerhalt bei Deinstallation abnehmen. [Plattformmatrix](docs/PLATFORM_SUPPORT.md).
4. Endgültigen Releaseumfang einfrieren, passende Quellen/Binärpakete bauen, Lizenzen und Signierung/Notarisierung abschließen, private Daten in Dateien/Git-Historie ausschließen und erst nach Veröffentlichungsauftrag freigeben. [Checkliste](docs/RELEASE.md).

## Nach der ersten begrenzten Alpha

- Kontrollierte Verbrauchsbuchung je physischer Spule und Auftrag: Spülung, Abbruch, Wiederanlauf und Doppelbuchungen berücksichtigen. ACE-Prozente sind kein gemessener Grammverbrauch.
- Statistik und belegte Kostenrechnung einschließlich leerer archivierter Spulen. Der Materialhinweis aus0.38 bleibt davon getrennt.
- NFC/QR und ReSpool-Automatisierung nur über belegte Schnittstellen; kein direkter automatischer Bibliotheksabgleich zugesagt. Bestehende Originaltags nicht ungefragt überschreiben; keine Pflicht zu monatlichen App-Abos.
- Warteschlange, Materialreservierung und weitere Modelle erst nach eigenem Kompatibilitäts-/Praxistest. Keine automatischen Starts auf ungeprüften oder belegten Druckern.
