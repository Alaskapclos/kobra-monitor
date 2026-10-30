# Sicherheitsbeschreibung

Diese Alpha ist für vertrauenswürdige Heim-/Druckernetze und privaten Zugriff
über VPN bestimmt. Keine Freigabe direkt im öffentlichen Internet.

- MQTT-Publish und die endgültige Serialisierung sind auf fünf bestehende
  Statusabfragen begrenzt. Automatische Kamera-, ACE- und Spoolman-Schreibaktionen
  sind deaktiviert. Die lokalen HTTP-Routen enthalten keine Druckersteuerung.
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

Ein externer Sicherheitsaudit und ein echter VPN-/NAS-Test stehen noch aus.

Passwortparameter: [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Passwortberechnung: Python `hashlib.scrypt`. Die Anwendung stellt selbst kein HTTPS bereit; für geschützte Übertragung auch innerhalb des Heimnetzes einen privaten HTTPS-Proxy verwenden.
