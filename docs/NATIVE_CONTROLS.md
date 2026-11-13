# Dauerhafte Steuerungsfreigaben in nativen Installationen ab 0.42

Nach der Anmeldung unter **Einrichten → Steuerung freigeben → Freigaben bearbeiten** für jeden bereits gespeicherten Drucker die gewünschten Funktionen wählen. Licht, Lüfter, Speed Mode, Temperaturen, Druckaktionen, Achsen/Homing, Archivstart und ACE-Trocknung sind getrennt wählbar. Die Trocknungsobergrenze bleibt zunächst 55 °C; 65 °C nur für einen dafür geeigneten ACE wählen. Speichern zeigt Drucker und Funktionen nochmals zur ausdrücklichen Bestätigung an.

Änderungen werden erst nach vollständigem Beenden mit dem lokalen Beenden-Starter und erneutem Start wirksam. Bis dahin gelten die bisherigen Freigaben, auch bei einem Entzug. Ein Neuladen des Browsers reicht nicht. Das Speichern löst keine Druckerbefehle aus. Nach dem Neustart werden die gewählten Freigaben bei weiteren Starts wieder geladen. Neue Installationen und neu hinzugefügte Drucker bleiben zunächst lesend.

Die Freigabe ersetzt keine Bestätigung einzelner kritischer Aktionen. Licht bleibt ohne zusätzlichen Bestätigungsdialog schaltbar; für Bewegungen, Temperaturen, Lüfter und andere kritische Aktionen gelten weiterhin die vorhandenen Dialoge. Achsen und Homing nur direkt vor dem Drucker bedienen. Entfernen eines Druckers löscht dessen gespeicherte Freigaben; erneutes Hinzufügen erteilt sie nicht wieder automatisch.

Die Freigaben gelten für diese lokale Installation und ihre angemeldeten Besitzer. Sie werden privat im Datenbereich gespeichert und von der vollständigen nativen Sicherung und Datenübernahme mit erfasst. Datei `monitor/native-controls.json` und persönliche Sicherungen nicht veröffentlichen. Unbekannte Rechte, fremde/unbekannte Drucker, unbestätigte oder veraltete Formulare werden abgewiesen. Ohne Besitzeranmeldung und CSRF-/Origin-Prüfung kann die Oberfläche keine Freigaben speichern.

NAS-/Docker-Betrieb verwendet weiterhin seine expliziten Umgebungsfreigaben; die neue native Oberfläche erweitert deren Rechte nicht. Eine Freigabe auf einem Rechner erteilt auch keinem anderen Monitor Rechte.

## Docker-Suite ab 0.43

Im ausdrücklich gewählten LAN-Modus verwendet die Docker-Suite denselben geschützten Freigabedialog. Nach dem Speichern den Monitor-Container über die vorhandene Docker-/NAS-Verwaltung vollständig neu starten. Der Desktop-Beenden-Starter gehört nicht zu dieser Installation. Spoolman und Sicherung müssen dafür nicht neu gestartet werden. Ein allgemeiner automatischer Programmupdateweg ist damit nicht verbunden.
