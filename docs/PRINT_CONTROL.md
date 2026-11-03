# Pause, Fortsetzen und Druckabbruch

Optional und standardmäßig aus: `KOBRA_PRINT_CONTROL_IPS` muss die freigegebenen S1-Adressen enthalten. Diese Freigabe ist unabhängig von Licht, Lüftern, Geschwindigkeit und Temperaturen. Modellkennung20025, LAN-Modus; zunächst praktische Freigabe nur für den ausdrücklich ausgewählten S1. Kein Druckstart, Upload, Homing oder allgemeiner Schreibzugriff.

Auf der Übersicht beim gewählten Druckauftrag: Pause nur während Printing, Fortsetzen nur bei bestätigter Pause, Druckabbruch während Printing oder Pause. Vorbereitungen, Übergänge, Fehler und fehlende aktuelle Daten sind gesperrt. Jeder Dialog zeigt Drucker und Dateinamen. Fokus liegt zunächst auf Abbrechen. Der Abbruchdialog erklärt, dass der Druck anschließend nicht fortgesetzt werden kann.

Der Client sendet genau `print/pause`, `print/resume` oder `print/stop` und ausschließlich die tatsächlich beobachtete `taskid`. Lokale S1-Drucke können real `-1` melden; eine fehlende Kennung wird nicht dadurch ersetzt. Zusätzliche Bindung an den Monitorauftrag, empfangene Datei, lokalen Lebenszyklusmarker und aktuelle Verbindung. Erfasster neuer Auftrag, Dateitausch, Laufzeitrückgang oder Wiederverbindung macht alte Bestätigungen ungültig. Ein vollständig zwischen zwei Meldungen unbeobachteter Wechsel ist nicht rekonstruierbar. Vor Versand neue lesende Info-Abfrage und erneute Prüfung unter dem Socket-Lock; keine Wiederholung nach Fehler oder Zeitüberschreitung.

Die Bestätigung benötigt eine neuere vollständige und zur gleichen beobachteten Identität passende Statusmeldung. Ein bloßes Befehls-ACK ist keine Bestätigung. Naturgemäßes Druckende, Leerlauf und Offline-Zustand sind keine bestätigte Stornierung. Meldet die Firmware nach Stop nur Leerlauf oder einen unvollständigen Abschlussbericht, bleibt das Ergebnis ausdrücklich unbestätigt. Nicht automatisch erneut abbrechen. Das Schaltprotokoll dokumentiert vorbereitete, bestätigte und unklare Vorgänge; es liegt privat in der mitgesicherten Historie.

Synthetische Prüfungen ersetzen keinen physischen Versuch. Die erste reale Pause/Fortsetzen/Stop-Probe übernimmt der Besitzer an einem dafür vorgesehenen Druck; der Agent löst diese Aktionen nicht zum Testen an laufenden Nutzdrucken aus.

Protokollquellen:
- https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/lan/commands.py (lokale Pause/Resume/Stop-Verben mit taskid)
- Gebündelter kobrax_client.py: pause_print/resume_print/stop_print nutzen dieselben begrenzten Formen; normale Wege bleiben durch Leseschutz gesperrt.
