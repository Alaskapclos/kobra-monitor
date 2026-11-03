# Speed Mode

Optional, standardmäßig ausgeschaltet. `KOBRA_SPEED_CONTROL_IPS` enthält ausdrücklich freigegebene S1-Adressen (Modellkennung 20025). Licht- und Lüfterfreigabe bleiben getrennt.

Direkt bei „Speed Mode“ öffnet „Einstellen“ den Dialog mit Silent (1), Standard (2) und Sport (3). Nur OK übernimmt die Auswahl; Abbrechen und Escape senden nichts. Drucker und Druckdatei stehen im Dialog. Im Leerlauf, bei Pause oder fehlenden aktuellen Daten bleibt die Auswahl gesperrt. Eine höhere Geschwindigkeit kann die Druckqualität verändern.

## Bindung an den aktuellen Druck

Der Auftrag wird an die vom Monitor erfasste Druckkennung, eine empfangene Auftrags-/Dateikombination und die aktuelle Verbindung gebunden. Der S1 kann bei lokalen Drucken tatsächlich task_id=-1 melden. Dieser beobachtete Wert ist von einer fehlenden ID zu unterscheiden: keine Ersatz-ID wird erfunden. Die konkrete Bindung verwendet zusätzlich den Monitorauftrag und einen lokalen Lebenszyklusmarker. Empfangener Datei-/Auftrags-/Statuswechsel, Wiederverbindung oder sinkende gemeldete Laufzeit verwerfen die alte Auswahl. Ein zwischen zwei Meldungen vollständig unbeobachteter Druckwechsel lässt sich aus diesen Daten nicht sicher rekonstruieren; deshalb erfolgt vor Übernahme eine neue lesende Info-Abfrage und unmittelbar vor dem einmaligen Versand eine erneute Prüfung.

Der einzige neue Schreibrahmen ist `print` / `update` mit genau `taskid` und `settings.print_speed_mode`. Keine Heiz-, Pause-, Stop-, Start- oder Bewegungsbefehle. Normale Client- und Bridge-Methoden bleiben lesend. Anmeldung, CSRF, passende Herkunft, Frische, Einzelversand und gemeinsames Schaltprotokoll sind erforderlich. Keine optimistische Anzeige und keine automatische Wiederholung bei unklarem Ausgang; Bestätigung benötigt eine neuere Modusmeldung desselben beobachteten Drucks.

Der Dienst fragt bei Speed-Mode-Freigabe Info-Berichte alle zehn Sekunden ab. Die zusätzliche Audit-Spalte `target_context` hat für bisherige Licht-/Lüftervorgänge den leeren Standardwert; vorherige Felder bleiben erhalten. Vor dem Update eine vollständige Sicherung prüfen.

## Protokollquellen und Nachweise

- [Lokaler print/update-Weg mit taskid](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/lan/commands.py)
- [Ändern einzelner Druckeinstellungen](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/api/functions.py)
- [Aktueller LAN-Druck über project.task_id](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/data_models/printer.py)

Die gebündelte S1-Bridge verwendet ebenfalls print/update und Moduscodes 1/2/3. Der Monitor nutzt dafür einen eigenen begrenzten Versandweg. Eine lesende Gegenprobe an den vorhandenen S1 bestätigt Standard=2 und die lokale task_id=-1 beim laufenden Druck. Reale Moduswechsel wurden durch den Agenten nicht ausgelöst. Physische Wirkung der drei Modi bleibt separat durch den Besitzer zu prüfen.

Besitzerabnahme vom 02.11.2026: Speed Mode beim laufenden Druck direkt getestet, funktioniert. Keine konkrete Modusfolge oder weitere Modellfreigabe daraus ableiten.
