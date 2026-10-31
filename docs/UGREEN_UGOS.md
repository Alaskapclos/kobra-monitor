# UGREEN DXP4800GT mit UGOS

Erster NAS-Praxistest am 30.10.2026 bestanden. Der DXP4800GT gehört laut UGREEN zu den
Docker-fähigen DXP-Modellen mit x86-64/AMD64. Die Menübezeichnungen können je nach
UGOS-Version leicht abweichen. Auf einem echten DXP4800GT wurden Import des CI-Abbilds, Compose-Start,
Browser-Einrichtung, zwei laufende Kobra S1 und ein Containerneustart geprüft.
Die genaue UGOS-Version wurde nicht erfasst. Image-Updates und HTTPS/Serve
wurden danach geprüft; der Nutzer bestätigte Mobilfunkzugriff über Tailscale
und Nichterreichbarkeit ohne VPN. Ein NAS-Neustart wurde nicht geprüft.

## Ziel

Der Monitor läuft dauerhaft als eigener Container auf dem NAS. Seine Historie,
Einrichtung und der Zugangscode bleiben im Volume `monitor-data`. Rechner,
Handy und Tablet öffnen nur die Weboberfläche. Die Drucker bleiben im LAN-Modus.

Wir beginnen mit Heimnetzzugriff auf die private NAS-Adresse. Der spätere
Fernzugriff erfolgt über das vorhandene VPN. Für Tailscale Serve kann die
Portbindung stattdessen auf Loopback beschränkt bleiben.

## 1. Docker bereitstellen

In UGOS das App Center öffnen und prüfen, ob Docker installiert ist. Die
Docker-Anwendung öffnen. Der Bereich **Project / Projekt** verwaltet Compose-
Projekte; **Image / Image-Abbilder** importiert Container-Abbilder.

Keine anderen Container oder UGOS-Dienste verändern. Vorher prüfen, dass Port
7125 auf dem NAS frei ist. Die NAS-Adresse und die installierte UGOS-Version
für den Test notieren.

## 2. Geprüftes Abbild beschaffen

Für die einfache GUI-Installation soll die GitHub-CI nach einem erfolgreichen
Container-Test das Artefakt **kobra-monitor-linux-amd64** bereitstellen:

1. Im privaten Repository **Actions → Checks** den erfolgreichen Lauf öffnen.
2. Unter **Artifacts** das Paket `kobra-monitor-linux-amd64` herunterladen.
3. Das ZIP entpacken. Es enthält `kobra-monitor-linux-amd64.tar`.
4. Diese TAR-Datei in UGOS unter **Docker → Image → Import** importieren.

Erwarteter Image-Name: `kobra-monitor:0.14.0-alpha.1`. Das Abbild enthält den
Quellcode und seine Bibliotheken; persönliche Datenvolumes und Zugangscodes
werden nicht in das Abbild exportiert. Das Artefakt ist privat und wird sieben
Tage aufbewahrt. Ein neuer erfolgreicher Workflow kann es erneut erzeugen.
Der erste erfolgreiche Lauf ist in der [Testmatrix](VALIDATION.md) verlinkt.

## 3. Eigenes Projekt anlegen

UGOS **Docker → Project → Create** öffnen. Projektname: `kobra-monitor`.
Die Konfiguration aus `deploy/ugos/compose.yaml` verwenden. Dort die Variable
`KOBRA_BIND_ADDRESS` auf die tatsächliche private LAN-IP des NAS setzen. Wenn
die UGOS-GUI keine Projektvariablen anbietet, den Ausdruck vor `:7125:7125`
direkt durch die private NAS-IP ersetzen, zum Beispiel:

```yaml
ports:
  - "192.168.1.20:7125:7125"
```

Die Beispieladresse ist kein voreingestelltes Ziel. Immer die eigene NAS-IP
verwenden. Für Tailscale Serve auf dem NAS stattdessen `127.0.0.1` verwenden.
Der Container selbst lauscht intern auf 7125; keine Host-Netzwerkfreigabe nötig.

Das benannte Volume `monitor-data` und die Schutzoptionen beibehalten. Die
Anwendung läuft als Benutzer 10001. Bei einem frischen benannten Volume wird
kein persönlicher NAS-Ordner mit erweiterten Rechten benötigt. Bei Importen
eines bestehenden Datenordners müssen seine Zugriffsrechte gesondert geprüft werden.

Das Projekt starten. Den Zustand des Containers und seine Logs prüfen. Ein
Neustart durch `restart: unless-stopped` startet nur die lokale Überwachung.

## 4. Im Browser einrichten

1. In UGOS den Monitor-Container öffnen und dessen **Terminal** verwenden.
2. Dort eingeben:

```sh
python monitor.py --show-setup-link
```

3. Im ausgegebenen privaten Link `127.0.0.1` durch deine NAS-IP ersetzen,
   den Rest einschließlich `#access=…` unverändert lassen und im Browser öffnen.
   Dies ist nur beim ersten Einrichten nötig. Den Link nicht veröffentlichen.
4. Deinen Benutzernamen und dein Passwort festlegen, Passwort wiederholen,
   **Konto anlegen** wählen.
5. Im Assistenten die Druckeradressen aus den Drucker-/Routereinstellungen eintragen.
6. **Speichern und verbinden**, anschließend **Zur Druckerübersicht** wählen.
7. Auf weiteren Geräten einfach `http://NAS-IP:7125` bzw. die private VPN-/HTTPS-
   Adresse öffnen und mit Benutzername und Passwort anmelden.

Beim Update einer Code-Installation statt Schritt 2–3 den bisherigen Code im
Browser unter „Bestehende Installation … umstellen“ einmal eingeben. Danach ist
der Code kein Anmeldeweg mehr. [Passwort vergessen / Konto ändern](INSTALLATION.md#benutzerkonto).

Der Monitor veranlasst keine Pause, keinen Start, keinen Upload und keine
Heizung oder Bewegung. Eine nicht erreichbare Druckeradresse erscheint offline.

## 5. Prüfliste für weitere Installationen

- Beide eingerichteten Drucker liefern Modell, Status und Temperaturen.
- ACE-Slots gehören jeweils zum richtigen Drucker.
- Bestehende Aufträge bleiben nach einem Containerneustart in der Historie.
- Ein Update mit demselben Volume erhält Einrichtung und Aufzeichnung.
- Der Browser lehnt Statuszugriff ohne Anmeldung ab.
- Ein zweites Gerät im Heimnetz erreicht den Monitor an der vorgesehenen Adresse.
- Ein anschließender VPN-/HTTPS-Test prüft die Erreichbarkeit von unterwegs.

Beim Löschen eines UGOS-Projekts darauf achten, dass sein Datenvolume nicht
mitgelöscht wird. Vor einem Update die persistenten Daten sichern. Für eine
konsistente Sicherung den Monitor stoppen oder die SQLite-Backup-API verwenden.

Der Mac-Monitor kann bis zum erfolgreichen NAS-Test weiterlaufen. Gleichzeitige
Instanzen haben getrennte Historien; ein Umzug bestehender Daten wird deshalb
als eigener Schritt geplant. Kein automatischer Wechsel des Aufzeichnungsgeräts.

## Alternative: selbst auf dem NAS bauen

Die vollständigen Projektdateien in einen eigenen NAS-Projektordner kopieren.
Die normale `compose.yaml` baut das Image aus diesem Ordner. Falls die UGOS-GUI
lokale Builds nicht unterstützt, kann ein bereits eingerichteter SSH-/Terminal-
Zugang dort `docker compose up -d --build` ausführen. SSH wird hierfür nicht
automatisch aktiviert. Der Import des CI-Abbilds vermeidet diesen Bau-Schritt auf dem NAS.

## Offizielle Quellen

- https://ai.ugreen.com/pages/solution-software
- https://ai.ugreen.com/blogs/knowledge/docker-docker-compose-ugreen-nas
- https://support.ugnas.com/detail/article/en-US/236

## Ergebnis des ersten Praxistests

Beide Geräte lieferten Status, Firmware, Temperaturen und jeweils ihre ACE-Slots.
Einrichtung und Zugangscode blieben beim Neustart des Monitor-Containers erhalten;
beide aktiven Aufträge wurden mit denselben Auftrags-IDs fortgeführt.
Ohne Anmeldung antwortete `/api/status` mit HTTP 401. Der Neustart erforderte
erwartungsgemäß eine erneute Browser-Anmeldung. Ein vorhandener anderer
Container blieb unverändert. Während des Monitorneustarts entsteht eine kurze
Beobachtungslücke; daraus wird kein Druckende abgeleitet.

Die NAS-Instanz begann mit eigener Historie und erkannte bereits laufende Drucke.
Bestehende Rechner-Historie wurde nicht automatisch kopiert oder zusammengeführt.

## Nachfolgend geprüfter Umzug

Ein betreuter Einzelumzug ergänzte vier ältere abgeschlossene Aufträge und die
frühere Rechner-Beobachtung zweier bereits auf dem NAS vorhandener Aufträge.
Beide Datenbanken wurden vorher gesichert; der zusammengeführte NAS-Stand wurde
zusätzlich außerhalb des NAS gesichert und testweise separat wieder geöffnet.
Der Rechner-Monitor wurde danach beendet. Ein automatischer Import ist derzeit
kein Bestandteil des Assistenten. Diese Verlaufssicherungen ersetzen noch kein
vollständiges Backup von Einrichtung, Zugangscode und TLS-Dateien.
