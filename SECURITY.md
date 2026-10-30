# Sicherheitsbeschreibung

Diese Alpha ist für vertrauenswürdige Heim-/Druckernetze und privaten Zugriff
über VPN bestimmt. Keine Freigabe direkt im öffentlichen Internet.

- MQTT-Publish und die endgültige Serialisierung sind auf fünf bestehende
  Statusabfragen begrenzt. Automatische Kamera-, ACE- und Spoolman-Schreibaktionen
  sind deaktiviert. Die lokalen HTTP-Routen enthalten keine Druckersteuerung.
- Anmeldung mit einem installationsbezogenen Zugangscode. Sitzungen: maximal
  zwölf Stunden, HttpOnly/SameSite-Strict-Cookie, bei HTTPS zusätzlich Secure.
- Lokale Einrichtung erfordert Sitzung, CSRF-Token und passenden Browser-Ursprung.
  Fünf fehlgeschlagene Anmeldungen pro Quelladresse innerhalb einer Minute
  führen vorübergehend zur Sperre. Hinter einem Proxy können mehrere Nutzer
  dieselbe Quelladresse teilen.
- Alle angemeldeten Nutzer dürfen dieselben Daten sehen und lokale Druckeradressen
  ändern. Es gibt noch keine getrennten Benutzerrollen.
- Die TLS-Serverprüfung des übernommenen Druckerclients ist deaktiviert.
  Verschlüsselung ist vorhanden; die Brokeridentität ist nicht verifiziert.
  Die Durchsetzung von mTLS durch den Drucker wurde nicht nachgewiesen.
- Sitzungsschlüssel liegen im Prozess. Zugangscode und lokale Konfiguration
  liegen im privaten Datenordner. POSIX-Dateirechte werden beschränkt; unter
  Windows sind die Kontorechte/ACLs des Datenordners maßgeblich.

Nicht veröffentlichen: `.state`, Datenvolumes, Zugangscodes, `.env`, Zertifikate,
private Schlüssel, rohe Druckerantworten, Upload-URLs oder unbereinigte Logs.
Der Desktop-Starter übergibt den Zugangscode im URL-Fragment, das sofort entfernt
wird. Trotzdem keine Aufnahme/Screenshot der Start-URL weitergeben.

Für einen Bericht über eine Schwachstelle den privaten GitHub-Meldeweg verwenden,
sobald dieser beim Repository aktiviert ist. Solange kein privater Meldeweg
existiert, keine vertraulichen Details in öffentlichen Issues posten.
Keine echten Drucke als Sicherheitsnachweis starten oder unterbrechen; synthetische
Fixtures und die vorhandenen Leseschutztests verwenden.

Ein externer Sicherheitsaudit und ein echter VPN-/NAS-Test stehen noch aus.
