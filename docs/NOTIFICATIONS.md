# Benachrichtigungen

Optional und standardmäßig ohne angemeldete Geräte. Der Monitor sendet weiterhin keine Druckersteuerung.

## Einrichten

1. Öffne den Monitor über seine HTTPS-Adresse. Von unterwegs schalte Tailscale oder dein VPN ein.
2. Auf iPhone/iPad ab iOS/iPadOS 16.4: in Safari „Teilen → Zum Home-Bildschirm“. Öffne das neue Symbol und melde dich mit deinem lokalen Konto an. Auf Android einen aktuellen Push-fähigen Browser verwenden.
3. Unter „Benachrichtigungen → Einrichten“ einen Gerätenamen und die gewünschten Meldungen wählen.
4. „Auf diesem Gerät aktivieren“ drücken und die Browserfrage selbst erlauben.
5. „Testmeldung senden“ und tatsächlichen Empfang auf diesem Gerät prüfen. Für jedes weitere Gerät wiederholen.

Druck abgeschlossen oder abgebrochen, explizite Störungen und Verbindungsabbruch sind getrennte Ereignisse. Verbindungsabbrüche werden standardmäßig nach drei Minuten gemeldet, wählbar nach einer, drei, fünf oder zehn Minuten. Abmelden beendet den Empfang nicht; „Entfernen“ meldet ein Gerät ab. Entfernen kann eine bereits an den Push-Dienst übergebene Meldung nicht zurückrufen.

## Datenschutz und Zugriff

Inhalte: Druckername und Anlass. Keine Dateinamen, IP-Adressen, Kamerabilder oder Kontodaten. Verschlüsselung mit der etablierten OSS-Bibliothek pywebpush (MPL-2.0), VAPID mit py-vapid (MPL-2.0), Nutzdatenverschlüsselung mit http-ece (MIT). Apple/Google/Mozilla/Microsoft betreiben je nach Browser den Zustellweg und sehen Zustellmetadaten; der Inhalt wird für das empfangende Gerät verschlüsselt. Keine zusätzliche Kontoerstellung bei einem Benachrichtigungsdienst. Keine öffentliche Freigabe des Monitors.

Geräteschlüssel und Zustelladresse liegen ausschließlich in der lokalen Verlaufsdatenbank; privater VAPID-Schlüssel in `push-vapid.pem`. Beides ist sensibel und Bestandteil der vollständigen Sicherung. Niemals veröffentlichen. Nach einer isolierten Wiederherstellung keinesfalls versehentlich einen zweiten sendenden Monitor starten.

Zieladressen sind auf HTTPS-Endpunkte der bekannten Browser-Push-Dienste beschränkt: fcm.googleapis.com, updates.push.services.mozilla.com, web.push.apple.com bzw. Subdomains von push.apple.com und notify.windows.com. Keine Weiterleitungen oder Umgebungs-Proxys. Geräteverwaltung nur nach Anmeldung mit Konto sowie CSRF- und Origin-Prüfung. Andere Push-Dienste sind derzeit nicht implementiert.

## Verhalten und Grenzen

- Ereignisse werden aus bestätigten, gespeicherten Beobachtungen abgeleitet. Verbindungsverlust oder ein unbemerktes Jobende gilt niemals als erfolgreicher Abschluss. Keine nachträglichen Meldungen für vorhandene Historie bei erster Aktivierung.
- Dauerhafte Warteschlange, höchstens drei Sendeversuche mit Wartezeiten; nach einer Stunde abgelaufen. Abgelaufene Geräte (404/410) werden entfernt. Ein gleicher Fehler wird höchstens einmal je 15 Minuten gemeldet. Ein längerer Verbindungsabbruch einmal je Unterbrechung und Gerät.
- Verarbeitung etwa alle fünf Sekunden; Betriebssystem/Push-Dienst können verzögern oder unterdrücken. „An den Push-Dienst übergeben“ bedeutet noch keine bestätigte Anzeige am Handy. Identische Tags mindern doppelte Anzeigen nach einem Absturz; exakte Einmalzustellung ist nicht garantiert.
- Das NAS muss laufen und Internetzugriff auf den jeweiligen Push-Dienst haben. Ein ausgeschalteter Monitor kann seinen eigenen Ausfall nicht melden. Ein durchgehend verbundener, aber stummer Drucker wird derzeit nicht als getrennte Verbindung gewertet.
- Die Meldung kann über den Push-Dienst ankommen, während Tailscale aus ist; zum Öffnen der privaten Monitorseite bleibt VPN/Tailscale erforderlich.
- Kein Service-Worker-Cache: Konto, Status und Kamerabilder werden nicht für Offline-Anzeige gespeichert.

Der Nutzer hat am 31.10.2026 den tatsächlichen Empfang einer Testmeldung auf iPhone und Android bestätigt. Eine Meldung zu einem realen Druckabschluss wurde ebenfalls auf einem Handy bestätigt; die Plattform ist dabei nicht belegt. Der reale Empfang jedes Fehler-/Abbruch-/Verbindungstyps auf beiden Plattformen bleibt offen; synthetische Prüfungen ersetzen diese Nachweise nicht.

Quellen: [Apple Web Push](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers), [pywebpush](https://github.com/web-push-libs/pywebpush).
