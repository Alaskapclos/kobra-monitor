# Lüftersteuerung

**Installationsweg beachten:** Native 0.42-Pakete und die ausdrücklich gewählte LAN-Docker-Suite verwalten Freigaben unter **Einrichten → Steuerung freigeben**. Änderungen gelten nach vollständigem Monitor-Neustart, bei Docker nach Container-Neustart. Bis dahin gelten die alten Freigaben. Die folgenden Umgebungsvariablen betreffen den eigenen Quellstart beziehungsweise entsprechend verwaltete bisherige Container; native Pakete übernehmen keine beliebigen Steuerrechte aus der Umgebung. [Freigabeverwaltung](NATIVE_CONTROLS.md).

Optional, standardmäßig aus. `KOBRA_FAN_CONTROL_IPS` enthält die explizit freigegebenen privaten Druckeradressen. Die vorhandene Lichtfreigabe wird dadurch nicht erweitert. Modellkennung 20025 (Kobra S1), kein allgemeiner G-Code oder frei wählbarer Befehl.

„Einstellen“ befindet sich direkt bei Bauteil-, Zusatz- und Kammerlüfter. Der Dialog zeigt den gewählten Drucker, aktuellen Wert und einen Schieberegler mit Zahlenfeld. Werte sind ganze Zahlen 0–100; bei Bauteil-/Zusatzlüfter Prozent, beim Kammerlüfter eine gemeldete Stufe. Erst OK bereitet den exakten Auftrag vor und sendet ihn einmal. Abbrechen, Escape, Seiten- oder Druckerwechsel verwerfen die Auswahl. Ein laufender Druck kann die Einstellung später wieder ändern.

Anmeldung, CSRF und passende Herkunft bleiben erforderlich. Ohne frische kanalspezifische Daten der aktuellen Verbindung bleibt der Knopf gesperrt. Eine Zustandsänderung zwischen Auswahl und Versand verwirft den Auftrag. Licht und Lüfter teilen denselben aktiven Auftrag pro Drucker. Bestätigung nur durch einen neueren Bericht dieses Kanals; kein optimistischer Wert, kein automatischer Wiederholungsversuch bei unklarem Ausgang.

Die Audit-Tabelle bekommt eine zusätzliche Spalte `control` mit Vorgabe `chamber_light`, damit bisherige Lichtvorgänge unverändert lesbar bleiben. Vor einem Update eine Sicherung prüfen. Keine produktive Wiederherstellung ohne gesonderten Anlass.

## Protokollbeleg und Grenze

Upstream dokumentiert den lokalen Weg `fan` / `setSpeed` und je Aufruf genau ein Datenfeld: `fan_speed_pct`, `aux_fan_speed_pct` oder `box_fan_level`.

- [LAN-Zuordnung im Upstream](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/lan/commands.py)
- [Getrennte Lüfterfelder](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/api/functions.py)

Keine Übernahme einer generischen beschreibbaren Bridge. Der einzelne Versandweg baut nur diese begrenzten Frames; alle normalen Clientmethoden bleiben durch die bestehende Leseschutzprüfung geschützt. Software- und simulierte Browserprüfungen belegen noch keine physische Wirkung an allen realen Lüftern. Der erste produktive Wert wird vom Besitzer selbst im Dialog gewählt und mit OK bestätigt.

## Praktischer Nachweis

Am 02.11.2026 bestätigt der Besitzer alle vorhandenen Steuerungen auf PC und Handy direkt vor dem Drucker ohne Fehler. Damit ist die Wirkung der Lüftersteuerung im konkret freigegebenen Umfang praktisch abgenommen. Konkrete Stufen, Handyplattform und weitere Druckermodelle sind damit nicht dokumentiert.
