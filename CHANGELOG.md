## 0.16.0-alpha.1

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
