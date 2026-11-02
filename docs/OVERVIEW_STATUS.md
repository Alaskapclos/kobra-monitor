# Übersicht: Kamera, Lüfter, Licht und Speed Mode

Auf dem Desktop steht die kompakte Kamera links, rechts folgen Druckstatus, Temperaturen und die zusätzlichen Gerätestatuswerte. Auf schmalen Bildschirmen stehen die Bereiche untereinander. Die spätere Steuerung gehört ebenfalls in die Übersicht; diese Version sendet keine Drucker-Steuerbefehle.

„Vergrößern“ öffnet das laufende Bild in einem Dialog. Das funktioniert für die Einzelansicht und pro Kamerakachel. Schließen oder Escape stellt das Bild an seine ursprüngliche Stelle zurück. Das Bild bleibt live, ohne einen zusätzlichen Decoder oder Kamera-Viewer anzufordern. Beim Wechsel der Seite oder Kamera wird der Dialog geschlossen.

## Gemeldete Werte

- Bauteil- und Zusatzlüfter: gemeldete Prozentwerte, keine Drehzahlmessung.
- Kammerlüfter: unveränderte gemeldete Stufe; keine ungeprüfte Umrechnung in Prozent oder U/min.
- Kammerlicht: Lichttyp 2 aus `lights`, An/Aus und separat gemeldete Helligkeit. Andere Lichttypen werden nicht als Kammerlicht angezeigt.
- Speed Mode: 1 Silent, 2 Standard, 3 Sport entsprechend der vorhandenen Bridge-Zuordnung. Weitere Codes bleiben ausdrücklich unbekannt.

Jedes Feld hat einen eigenen Empfangszeitpunkt. Fehlende Felder sind „Nicht gemeldet“; echte 0 und Aus bleiben gültige Werte. Ungültige Werte oder leere Bestätigungen erneuern keinen Empfangszeitpunkt. Ausfall, Alter und ein zwischenzeitlicher Verbindungsabbruch kennzeichnen alte Werte. Statusdaten einer vorherigen Verbindung werden nach Wiederanmeldung erst durch erneuten Empfang aktuell.

`light/query` mit `data=null` ist als zusätzliche reine Statusabfrage freigegeben, einzeln und im vollständigen ausgehenden MQTT-Paket geprüft. `light/control`, Schreibdaten bei einer Abfrage und Druckersteuerung bleiben gesperrt. Bestehende Geräteberichte und info-Abfragen liefern die Lüfter-/Moduswerte.

Protokollreferenz: https://github.com/ChestnutLabs/printer-protocol-orchard/blob/main/protocols/anycubic.md. Modell-/Firmwareunterschiede können fehlende Angaben verursachen. Keine nicht gemeldete Hotend-Lüfterdrehzahl wird aus einem anderen Lüfter abgeleitet.
