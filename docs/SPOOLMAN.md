# Spoolman-Anbindung – erster Ausbau

Spoolman bleibt die zentrale Datenquelle. Projekt: https://github.com/Donkie/Spoolman, MIT-Lizenz. API: https://donkie.github.io/Spoolman/. Für die neue getrennte Installation ist Version 0.27.0 vorgesehen; keine unveränderliche `latest`-Annahme. Quellenstand am 31.10.2026 geprüft.

Im Monitor unter **Spulenverwaltung → Einrichten** die lokale Basisadresse ohne `/api` eintragen und **Speichern & prüfen** wählen. Die Adresse muss vom Monitor-Rechner/NAS aus erreichbar sein, nicht vom Handy. Unterstützt werden lokale IPv4-Adressen sowie der feste Docker-Dienstname `spoolman` im gemeinsamen Netz. Kein API-Schlüssel/Passwort in der URL. HTTPS wird normal geprüft; keine Zertifikatsausnahme.

**Spulen aktualisieren** liest ausschließlich `GET /api/v1/spool`, begrenzt auf 1000 aktive Spulen und 4 MiB. Keine Weiterleitungen, Cookies, Umgebungs-Proxys oder Übernahme beliebiger API-Pfade. Eine leere Liste ist ein gültiger leerer Bestand. Fehler behalten frühere Daten als veraltet; neue Zuordnungen benötigen eine erfolgreiche Abfrage der letzten 60 Sekunden.

Beim ausgewählten Drucker eine Spule für einen gemeldeten ACE-Slot auswählen und **Zuordnen**. Eine Spule kann nur einem Slot zugeordnet sein. Lösen einer Zuordnung bleibt bei ausgefallenem Spoolman und entfernten Druckern möglich. Vor einem Serverwechsel erst alle Zuordnungen lösen, damit gleiche numerische IDs verschiedener Server nicht verwechselt werden.

Der Monitor ändert weder Spoolman-Spulen noch Druckereinstellungen. Spulen anlegen, wiegen und pflegen erfolgt zunächst in Spoolman selbst. Nach expliziter Verknüpfung einer eindeutigen SKU kann der Monitor die Spule wiedererkennen. Keine Verbrauchsbuchung oder Übernahme aus 3D Filament Profiles. Spoolman-Restgewicht ist ein Buchbestand, keine Live-Waage. ACE-Prozentwerte bleiben getrennt.

## Installation und Sicherung

Spoolman als getrennten Dienst mit eigenem persistentem Volume installieren. Die offizielle Anwendung hat eine eigene Oberfläche; deren direkter Zugang braucht ein privates Netz/eine geeignete Zugangssicherung. Keine öffentliche Portweiterleitung einrichten. Monitor-HTTPS schützt ausschließlich die Monitor-Oberfläche, nicht automatisch einen separat veröffentlichten Spoolman-Port.

`spoolman.json` im Monitor-Datenvolume enthält Endpunkt, Slot-Verknüpfungen und bestätigte SKU-Verknüpfungen und wird privat in der Monitor-Vollsicherung wiederhergestellt. Das ersetzt **keine Sicherung der eigenen Spoolman-Datenbank**. Die getrennte NAS-Installation nutzt Spoolmans vorhandene nächtliche SQLite-Sicherung. Ein manueller Anfangsstand wurde isoliert mit SQLite-Integritätsprüfung geöffnet. Der erste nächtliche Zyklus bleibt zu prüfen; Sicherungen im Spoolman-Datenvolume ersetzen keine Kopie außerhalb des NAS. NFC-/RFID-Unterstützung in Spoolman 0.27 ist vorhanden; Kompatibilität mit ReSpool/Anycubic muss separat praktisch geprüft werden.

## Spulenkennung ab 0.18

Im ausgewählten ACE-Slot zeigt der Monitor die lokal gemeldete SKU. Für eine eindeutige Kennung (z. B. ReSpool) eine vorhandene Spoolman-Spule auswählen, die Bestätigung zur Eindeutigkeit setzen und **Kennung mit ausgewählter Spule verknüpfen** wählen. Eine normale Hersteller-SKU kann mehrere identische Spulen bezeichnen; sie ist kein Beweis für eine Einzelspule und keine Hardware-UID.

Die bestätigte Verbindung wird im Monitor gespeichert und mitgesichert. Nach Steckplatzwechsel zeigt **wiedererkannt** die passende Spoolman-Spule. Eine vorherige manuelle Zuordnung derselben Spule an diesem Slot wird dabei durch die bewegliche Kennungsverknüpfung ersetzt. Andere widersprüchliche manuelle Zuordnungen zuerst lösen. Mehrfach gemeldete Kennungen und Konflikte bleiben ohne Erkennung; offline, älter als 60 Sekunden, leerer Slot oder veralteter/fehlender Spoolman-Bestand ebenso. **Kennung lösen** funktioniert auch ohne Drucker oder Spoolman. Vor Serverwechsel auch gespeicherte Kennungen lösen.

Kein Beschreiben von NFC-Tags, keine Druckersteuerung und keine Spoolman-Bestandsänderung. SKU-Verknüpfungen sind noch keine Verbrauchsautomation oder Synchronisierung der ReSpool-Handybibliothek. Erst mit einer vorhandenen gekennzeichneten Spule praktisch prüfen; keine laufende Spule entnehmen.
