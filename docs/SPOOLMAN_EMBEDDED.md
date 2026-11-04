# Originale Spoolman-Oberfläche im Monitor

Ab 0.20 gibt es im Bereich **Spulen** die Unterbereiche **ACE & Zuordnung** und **Spulen verwalten**. Letzterer lädt die originale Spoolman-Weboberfläche in einem Rahmen. Spoolmans Programmcode und Dateien bleiben unverändert; der Monitor baut keine zweite Bestandsverwaltung auf. Vor einem Bereichswechsel Eingaben in Spoolman speichern. Der Rahmen wird beim Verlassen geschlossen, die NAS-Aufzeichnung läuft weiter.

## Einmalige Einrichtung

Spoolman unterstützt nativ einen Unterpfad. In seiner vorhandenen Compose-Datei ergänzen:

```yaml
environment:
  SPOOLMAN_BASE_PATH: /spoolman
```

Vorhandenes Image, Datenvolume, Sicherung und übrige Einstellungen erhalten. Nach dem Neustart lautet der native Zugang beispielsweise `http://192.168.1.20:7912/spoolman/`; die API liegt darunter unter `/api/v1`. Im Monitor als Spoolman-Adresse `http://192.168.1.20:7912/spoolman` eintragen. Bei einer bestehenden Installation mit Spulenverknüpfungen muss der Betreiber die Adresse als dokumentierten Umzug desselben Dienstes mit gesicherter Konfiguration anpassen; der Schutz gegen versehentlichen Serverwechsel bleibt bestehen.

Unter dem Monitor-Ursprung steht dann `/spoolman/` zur Verfügung. Monitor-Anmeldung und eingerichtetetes Besitzerkonto sind für alle Unterseiten, Anlagen, APIs und Websocket-Verbindungen erforderlich. HTTPS des Monitors reicht bis zum Browser; die NAS-interne Verbindung verwendet die konfigurierte Spoolman-Adresse. Spoolman erhält weder das Monitor-Sitzungscookie noch Zugangsdaten. Es gibt keine öffentliche Portfreigabe und keinen zusätzlichen Dienst.

Spoolman selbst bleibt auf seinem bisherigen privaten LAN-Port erreichbar, nun mit Unterpfad. Die Monitor-Einbettung ersetzt keine Netzwerksicherung dieses direkten Zugangs.

## Bedienung und Grenzen

Änderungen in der Originaloberfläche schreiben direkt in Spoolman. Das schließt manuelle Bestandsänderungen ein; es ist keine automatische Verbrauchsbuchung durch den Monitor. Druckerbefehle bleiben gesperrt. Im Rahmen stehen die Originalfunktionen der installierten Spoolman-Version zur Verfügung. Nach Spulenänderungen unter **ACE & Zuordnung → Einrichten → Spulen aktualisieren** den gelesenen Monitor-Bestand erneuern.

Nur passende Browser-Ursprünge dürfen Änderungen ausführen. Fremde Ursprünge, nicht angemeldete Anfragen, Weiterleitungen aus dem Unterpfad und beliebige Zieladressen bleiben gesperrt. Original-Frontend und Monitor teilen einen Web-Ursprung; Spoolman ist dadurch ein vertrauenswürdiger Bestandteil der angemeldeten Anwendung. Seine Skripte werden nicht umgeschrieben. Alle nicht eingebetteten Monitorseiten behalten ihre bisherige strengere Inhaltsrichtlinie. Uploads sind auf 16 MiB, Antworten auf 32 MiB begrenzt. Externe eingebettete Medien und Popups sind nicht Teil des geprüften Grundablaufs.

## Künftige Updates

Die Einstellung `SPOOLMAN_BASE_PATH` und dieselben Datenvolumes in der Compose-Datei beibehalten. Die Spoolman-Oberfläche und APIs werden bei jedem Aufruf vom laufenden Dienst geladen; keine kopierten Frontend-Dateien und keine versionsabhängigen HTML-Ersetzungen. Nach Updates Anmeldung, Liste, Bearbeitungsformular und Sicherung prüfen. Monitor- und Spoolman-Daten weiterhin getrennt sichern.

Quellen: [offizielle Konfiguration](https://github.com/Donkie/Spoolman/wiki/Configuration), [Spoolman 0.27 Hauptanwendung](https://github.com/Donkie/Spoolman/blob/v0.27.0/spoolman/main.py).
