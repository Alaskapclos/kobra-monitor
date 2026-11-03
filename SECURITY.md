# Sicherheitsbeschreibung

Diese Alpha ist für vertrauenswürdige Heim-/Druckernetze und privaten Zugriff
über VPN bestimmt. Keine Freigabe direkt im öffentlichen Internet.

- Der allgemeine Druckerclient und die Bridge bleiben auf begrenzte Statusabfragen beschränkt.
  Optionale Steuerungen nutzen separate, pro S1 ausdrücklich freizugebende Wege für Licht,
  Lüfter, Speed Mode, Solltemperaturen, Pause/Fortsetzen/Abbruch sowie manuelle Achsen/Homing.
  Diese Freigabelisten sind standardmäßig leer. Kein allgemeiner G-Code, Datei-Upload,
  Druckstart, Filamenttransport oder automatisches Kamera-/ACE-/Spoolman-Schreiben.
- Steuerzugriffe erfordern Besitzeranmeldung, CSRF-Token und passenden Browser-Ursprung.
  Aktuelle Telemetrie und die konkrete Verbindung werden unmittelbar vor einem einmaligen
  Versand geprüft. Zustands-/Auftragsänderungen verwerfen alte Bestätigungen. Kein
  automatischer Wiederholungsversuch bei unklarem Ausgang. Ein Schaltprotokoll wird vor
  Versand im privaten Datenbestand gespeichert und mitgesichert.
- Licht schaltet direkt. Lüfter, Speed Mode, Temperaturen und Druckaktionen erfordern eine
  Bestätigung. Manuelle Achsen sind nur im frischen Leerlauf verfügbar: erste X/Y/Z-Fahrt
  mit Anwesenheitsbestätigung, danach weitere Schritte derselben Anmeldung an diesem Drucker
  bis zum nächsten erkannten regulären Druck ohne weiteren Dialog. Schon dessen Vorbereitung
  setzt die Freigabe zurück. Homing benötigt immer eine eigene Bestätigung. Die Anwesenheit
  wird vom Bediener erklärt, nicht technisch nachgewiesen; weder Kamera noch Wartezeiten
  stellen eine Kollisions- oder Stillstandsgarantie dar. Bewegungsversand wird nicht als
  bestätigter mechanischer Abschluss ausgegeben.
- Ein lokales Besitzerkonto mit Benutzername und Passwort. scrypt (N=32768,
  r=8, p=3), zufälliger 16-Byte-Salt, 32-Byte-Prüfwert; kein Klartextpasswort.
  Ersteinrichtung/Altdaten-Umstieg nur mit dem geschützten Einrichtungsschlüssel;
  dieser ist nach Kontoeinrichtung als Anmeldung gesperrt. Sitzungen: maximal
  zwölf Stunden, HttpOnly/SameSite-Strict-Cookie, bei HTTPS zusätzlich Secure.
- Lokale Einrichtung erfordert Sitzung, CSRF-Token und passenden Browser-Ursprung.
  Passwortberechnungen laufen einzeln außerhalb der Status-Ereignisschleife.
  Fünf fehlgeschlagene Anmeldungen pro Quelladresse innerhalb einer Minute
  führen vorübergehend zur Sperre; zusätzlich höchstens 30 Fehlversuche
  pro Minute über alle Quelladressen. Hinter einem Proxy können mehrere Nutzer
  dieselbe Quelladresse teilen.
- Ein Besitzerkonto pro Installation; keine getrennten Rollen. Kontoänderungen
  brauchen das bisherige Passwort und widerrufen alle bestehenden Sitzungen.
  Lokale Kontowiederherstellung setzt Zugriff auf Host/Datenvolume voraus.
- Die TLS-Serverprüfung des übernommenen Druckerclients ist deaktiviert.
  Verschlüsselung ist vorhanden; die Brokeridentität ist nicht verifiziert.
  Die Durchsetzung von mTLS durch den Drucker wurde nicht nachgewiesen.
- Sitzungsschlüssel liegen im Prozess. Kontoprüfwert, Einrichtungsschlüssel und lokale Konfiguration
  liegen im privaten Datenordner. POSIX-Dateirechte werden beschränkt; unter
  Windows sind die Kontorechte/ACLs des Datenordners maßgeblich.

Nicht veröffentlichen: `.state`, Datenvolumes, Zugangscodes, `.env`, Zertifikate,
private Schlüssel, rohe Druckerantworten, Upload-URLs oder unbereinigte Logs.
Nur für die erste Kontoeinrichtung übergibt der Desktop-Starter den Schlüssel im URL-Fragment, das sofort entfernt
wird. Trotzdem keine Aufnahme/Screenshot der Start-URL weitergeben.

Für einen Bericht über eine Schwachstelle den privaten GitHub-Meldeweg verwenden,
sobald dieser beim Repository aktiviert ist. Solange kein privater Meldeweg
existiert, keine vertraulichen Details in öffentlichen Issues posten.
Keine echten Drucke als Sicherheitsnachweis starten oder unterbrechen; synthetische
Fixtures und die vorhandenen Leseschutztests verwenden.

Ein externer Sicherheitsaudit und eine vollständige Prüfung der bestehenden
VPN-Zugriffsregeln stehen aus. HTTPS/Serve und der Mobilfunkzugriff mit/ohne VPN
wurden am 31.10.2026 praktisch geprüft. UGOS und der vom Nutzer bestätigte private
Mobilfunk-/Tailscale-Zugriff sind in docs/VALIDATION.md dokumentiert.

Passwortparameter: [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Passwortberechnung: Python `hashlib.scrypt`. Die Anwendung stellt selbst kein HTTPS bereit; für geschützte Übertragung auch innerhalb des Heimnetzes einen privaten HTTPS-Proxy verwenden.

Kamera ab 0.12: ausschließlich GET auf den vorhandenen Stock-FLV-Stream eingerichteter Drucker. Keine startCapture-/stopCapture-Publishes, keine Freigabe zusätzlicher MQTT-Kommandos. Kamera-Bildroute benötigt dieselbe Kontositzung. Decoder akzeptiert nur HTTP/TCP, festes FLV-Format und keine Redirects. Maximal zwei geteilte JPEG-Decoder, inaktive Leser werden beendet; alte Bilder werden nicht als live ausgegeben. Der Browser lädt Bilddaten vom angemeldeten Monitor, einschließlich HTTPS. Keine Aufzeichnung auf Datenträger. FFmpeg verarbeitet Druckerdaten innerhalb desselben eingeschränkten Containers; nur in vertrauenswürdigem Druckernetz betreiben.

Die Kameraübersicht verwaltet zufällige lokale Ansichtskennungen. POST `/api/camera/release` ist nur mit Konto, CSRF und passender Origin erlaubt und räumt ausschließlich Monitor-Leser auf. Keine MQTT- oder Druckerbefehle; keine Änderung von Drucker/Kamera-Einstellungen.

## Eingebettetes Spoolman ab 0.20

Die originale Spoolman-Anwendung unter `/spoolman/` benötigt dieselbe Besitzeranmeldung. Ihre manuellen Bestandsänderungen sind absichtlich möglich; keine automatische Verbrauchsbuchung und keine Druckersteuerung. Native API-Schreibzugriffe benötigen einen ausdrücklich mit dem Monitor-Host übereinstimmenden Origin-Header und ein Sitzungscookie. Die Originaloberfläche kann keinen Monitor-CSRF-Header setzen; hierfür wird der strikte Origin-Abgleich zusammen mit SameSite-Strict verwendet. Cookies, Zugangsdaten, CORS- und externe Weiterleitungsfreigaben werden nicht durchgereicht. Spoolman ist unter demselben Ursprung vertrauenswürdiger Anwendungscode. Details: [Einbettung](docs/SPOOLMAN_EMBEDDED.md).

## Originaldatei-Archiv ab 0.28

Computerzugänge sind getrennte, zufällige Bearer-Schlüssel mit ausschließlich zwei POST-Rechten (`/api/archive/ingest`, `/api/archive/heartbeat`). In der Datenbank liegt nur SHA-256 des Schlüssels. Ein Schlüssel erlaubt weder Dateiauslesen noch Besitzerfunktionen oder Druckerbefehle. Browser-Origin-/Fetch-Site-Anfragen werden für diesen Maschinenpfad abgelehnt. Die Besitzerverwaltung und Originaldownloads bleiben sitzungsgeschützt; Verwaltungsänderungen verlangen Origin/CSRF. Computerschlüssel können widerrufen werden und liegen privat im Helferprofil; vollständige NAS-Sicherungen enthalten ihre Hashes.

Uploadgröße, entpackte Summe, Eintragsanzahl, Speicherreserve und Archivkapazität sind begrenzt. Keine ZIP-Extraktion oder G-Code-Ausführung. Nur ein Eingang gleichzeitig; temporäre Eingänge werden nie als Originale angezeigt. Nach vollständiger CRC-/Größen-/Hash-Prüfung wird vor dem Katalogeintrag atomar und dauerhaft gespeichert. Kein öffentlicher Dateipfad. Der Helfer prüft TLS, lehnt Weiterleitungen/Proxies ab und erlaubt unverschlüsseltes HTTP nur an lokale IP-Adressen. Ausführliche Grenzen und private Datenpfade: [Originaldatei-Archiv](docs/FILE_ARCHIVE.md).
