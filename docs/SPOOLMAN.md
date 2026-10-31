# Spoolman-Anbindung – erster Ausbau

Spoolman bleibt die zentrale Datenquelle. Projekt: https://github.com/Donkie/Spoolman, MIT-Lizenz. API: https://donkie.github.io/Spoolman/. Für die neue getrennte Installation ist Version 0.27.0 vorgesehen; keine unveränderliche `latest`-Annahme. Quellenstand am 31.10.2026 geprüft.

Im Monitor unter **Spulenverwaltung → Einrichten** die lokale Basisadresse ohne `/api` eintragen und **Speichern & prüfen** wählen. Die Adresse muss vom Monitor-Rechner/NAS aus erreichbar sein, nicht vom Handy. Unterstützt werden lokale IPv4-Adressen sowie der feste Docker-Dienstname `spoolman` im gemeinsamen Netz. Kein API-Schlüssel/Passwort in der URL. HTTPS wird normal geprüft; keine Zertifikatsausnahme.

**Spulen aktualisieren** liest ausschließlich `GET /api/v1/spool`, begrenzt auf 1000 aktive Spulen und 4 MiB. Keine Weiterleitungen, Cookies, Umgebungs-Proxys oder Übernahme beliebiger API-Pfade. Eine leere Liste ist ein gültiger leerer Bestand. Fehler behalten frühere Daten als veraltet; neue Zuordnungen benötigen eine erfolgreiche Abfrage der letzten 60 Sekunden.

Beim ausgewählten Drucker eine Spule für einen gemeldeten ACE-Slot auswählen und **Zuordnen**. Eine Spule kann nur einem Slot zugeordnet sein. Lösen einer Zuordnung bleibt bei ausgefallenem Spoolman und entfernten Druckern möglich. Vor einem Serverwechsel erst alle Zuordnungen lösen, damit gleiche numerische IDs verschiedener Server nicht verwechselt werden.

Der Monitor ändert weder Spoolman-Spulen noch Druckereinstellungen. Spulen anlegen, wiegen und pflegen erfolgt zunächst in Spoolman selbst. Es gibt noch keine automatische NFC-Zuordnung, Verbrauchsbuchung oder Übernahme aus 3D Filament Profiles. Spoolman-Restgewicht ist ein Buchbestand, keine Live-Waage. ACE-Prozentwerte bleiben getrennt.

## Installation und Sicherung

Spoolman als getrennten Dienst mit eigenem persistentem Volume installieren. Die offizielle Anwendung hat eine eigene Oberfläche; deren direkter Zugang braucht ein privates Netz/eine geeignete Zugangssicherung. Keine öffentliche Portweiterleitung einrichten. Monitor-HTTPS schützt ausschließlich die Monitor-Oberfläche, nicht automatisch einen separat veröffentlichten Spoolman-Port.

`spoolman.json` im Monitor-Datenvolume enthält nur Endpunkt und Slot-Verknüpfungen und wird privat in der Monitor-Vollsicherung wiederhergestellt. Das ersetzt **keine Sicherung der eigenen Spoolman-Datenbank**. Für die neue NAS-Installation eine getrennte Sicherung mit SQLite-Snapshot und isolierter Wiederherstellung einrichten, bevor reale Bestände erfasst werden. NFC-/RFID-Unterstützung in Spoolman 0.27 ist vorhanden; Kompatibilität mit ReSpool/Anycubic muss separat praktisch geprüft werden.
