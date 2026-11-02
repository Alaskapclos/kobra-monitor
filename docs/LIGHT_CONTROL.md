# Kammerlicht auf der Übersicht

Standardmäßig bleibt der Monitor im Lesebetrieb. Für ausdrücklich freigegebene Anycubic Kobra S1 (Modell 20025) kann das Kammerlicht geschaltet werden. Weitere Modelle und Befehle sind nicht freigegeben. Der allgemeine MQTT-Versand bleibt an die bestehende Leseschutzregel gebunden; allein der getrennte Lichtaufruf darf einen festen Lichttyp-2-An/Aus-Befehl senden.

## Einmalige Freigabe durch den Betreiber

Im Compose-Projekt `KOBRA_LIGHT_CONTROL_IPS` auf eine oder mehrere eingerichtete private Drucker-IP-Adressen setzen, durch Komma getrennt. Beispiel: `192.168.1.20`. Danach den Monitor mit unverändertem Datenvolume neu bereitstellen. Leer lassen oder entfernen, um beim nächsten Dienststart zum Lesebetrieb zurückzukehren. Die Webseite kann diese Freigabe nicht erweitern. Die Angabe ersetzt nicht die Druckereinrichtung.

Ein Starter übernimmt die Variable aus seiner Umgebung. Für eine Installation genau einen Monitorprozess pro Datenverzeichnis betreiben. Der Sicherungsdienst bleibt netzwerklos; für ihn ist keine Steuerfreigabe erforderlich.

## Bedienung

Mit dem lokalen Besitzerkonto anmelden, auf der Übersicht den Drucker auswählen und den Schalter direkt neben der Glühbirne betätigen. Ein Klick schaltet das Kammerlicht ohne zusätzlichen Bestätigungsdialog. Nur diese Lichtfunktion ist eine direkte Aktion; spätere Bewegungs-, Lüfter- und Temperaturbefehle benötigen weiterhin eine Bestätigung. Die interne, einmalige Vorbereitung verfällt nach 20 Sekunden und wird bei einem Drucker- oder Seitenwechsel vor dem Versand verworfen. Bei fehlenden oder mehr als 15 Sekunden alten Lichtdaten ist das Schalten gesperrt; auch alte Verbindungen werden zurückgewiesen.

Die Anzeige folgt den tatsächlichen Rückmeldungen. Eine erfolgreiche Socket-Übertragung allein ist keine bestätigte Zustandsänderung. Bei einer unklaren Antwort den tatsächlichen Druckerzustand prüfen. Der Monitor wiederholt Befehle nicht automatisch. Ein Neustart verwirft vorbereitete Vorgänge und spielt keine alten Befehle ab. Ein absichtlicher neuer Klick ist ein neuer Bedienauftrag.

## Betrieb und Sicherung

Status, Healthcheck und Oberfläche kennzeichnen den freigegebenen Lichtbetrieb. Andere Drucker können gleichzeitig im Lesebetrieb bleiben. Der Monitor fragt Lichtberichte bei freigegebenen Druckern alle zehn Sekunden ab. Ein Kontrollwechsel löst zusätzlich einen lesenden Abruf aus. Keine Heiz-, Bewegungs-, Lüfter-, Upload-, Druckstart-, Pause- oder Stopbefehle werden angeboten.

Das lokale Vorgangsprotokoll liegt als `control_attempts` in `history.sqlite3` und wird mit dieser Datenbank gesichert. Es enthält Zieladresse, gewünschten und vorher gemeldeten Lichtzustand, Zeit, Ergebnis und eine sitzungsbezogene Kennung. Keine Passwörter oder Zertifikate werden darin gespeichert. Sicherungen und Laufzeitdaten privat halten. Ein wiederhergestellter offener Vorgang wird beim Dienststart verworfen oder als unklar markiert, niemals erneut gesendet.

## Nachweise und Grenzen

Ablauf-, Transport-, Authentifizierungs- und UI-Prüfungen mit künstlichen Druckern. Zusätzlich wurde ein realer S1-Lichtwechsel Aus/An durch neue Berichte bestätigt und vom Betreiber sichtbar geprüft. Das ist kein Nachweis anderer Steuerfunktionen oder aller Firmwareversionen. [Lichttyp und Nutzdaten](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/api/functions.py), [LAN-Topic-Aufbau](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/lan/client.py).
