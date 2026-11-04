# Solltemperaturen

`KOBRA_TEMPERATURE_CONTROL_IPS` ist standardmäßig leer und unabhängig von Licht, Lüftern und Speed Mode. Nur ausdrücklich freigegebene Stock-S1 (Modellkennung 20025). Getrennte Dialoge direkt bei Düse/Bett, ganze Grad, Düse 0–320 °C und Bett 0–120 °C. 0 schaltet den ausgewählten Heizer aus. Erst OK übernimmt; Abbrechen, Navigation und Druckerwechsel senden nichts.

Nur frische originale Sollwertfelder, beobachteter Leerlauf oder laufender Druck und dieselbe Verbindung autorisieren einen Auftrag. Vorbereitung, Nivellierung, Pause, unklare Phasen und veraltete Daten bleiben gesperrt. Jeder Intent bindet den lokalen Auftrags-/Phasenmarker; Status- und Verbindungswechsel sowie beobachteter Laufzeitrückgang verwerfen alte Auswahlen. Ein vollständig zwischen Berichten unbeobachteter Wechsel ist nicht rekonstruierbar. Vor Versand werden die Zustandsdaten lesend abgefragt und unter dem Socket-Lock erneut geprüft.

Eng begrenzter Versand: `tempature/set`, `type=0` nur Düse beziehungsweise `type=1` nur Bett, Zielwert im zugehörigen Feld; das andere Zahlenfeld enthält die vom Slicer verwendete Null-Platzhalterzahl. Kein gemeinsamer Heizerauftrag und kein allgemeiner Schreibzugriff. Normale Bridge-Wege bleiben lesend. Keine automatische Wiederholung. Die Bestätigung benötigt einen neueren passenden Sollwertbericht im selben Kontext und bedeutet nicht, dass die Isttemperatur erreicht ist.

Anmeldung, CSRF und Origin-Prüfung, per-Drucker-Sperre, begrenztes Audit und isolierte Sicherungswiederherstellung folgen den vorhandenen Steuerungen. Keine reale Heizwirkung durch automatische Tests auslösen. Physische Abnahme separat mit dem Besitzer.

Protokollquellen:
- https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/lan/commands.py (SET_TEMPERATURE → tempature/set)
- https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/api/functions.py (_send_order_set_temperature, type wählt nur einen Heizer)
- https://uk.anycubic.com/products/kobra-s1 (Herstellergrenzen 320 °C/120 °C)

Die ältere gebündelte Bridge setzt beide Felder gemeinsam ohne Selektor; dieser Weg wird nicht verwendet. Die native physische Gegenprobe des neuen selektiven Wegs steht aus.
