# Verwendete Projekte und lokale Änderungen

Die gepinnten Quellen stehen in SOURCES.json. Änderungen vom 30.10.2026:

- kobra-connect: TLS-Zertifikatsparameter berichtigt; nur benötigte Kernmodule
  übernommen. Der Monitor nutzt den vorhandenen lokalen Handshake.
- kobra-bridge: expliziter Lesemodus mit Publish- und Framing-Filter; Kamera-, ACE-
  und Spoolman-Automatiken im Lesemodus deaktiviert; getrennte Zertifikatspfade
  pro Client. Details in vendor/kobra-bridge/READ_ONLY_BUILD.json.
- Fremde Docker-/Compose-Dateien und die verschachtelte Fremd-CI aus dem
  Monitor-Paket entfernt, damit nur der eigene Monitor-Dienst gestartet wird.
- Eigene Oberfläche, Historie, Reports, Zugangsverwaltung, Konfiguration,
  Einrichtungsassistent und Starter liegen im Projektstamm und static/.

Keine eigenen MQTT-/Handshake-Protokollimplementierungen. Keine mitgelieferten
Slicer-Zugangsdaten. Ein unveränderter Upstream-Bridge-Start ist nicht mit dem
hier abgesicherten Monitorstart gleichzusetzen.

Änderung vom 31.10.2026 für Kameraansicht: CameraCache wird für den vorhandenen FLV-Stream wiederverwendet, ausschließlich dessen JPEG-Worker. In `_run_jpeg_loop` wird voller JPEG-Farbbereich explizit gewählt und ein Encoder-Thread verwendet. MQTT-Whitelist und Kamera-Steuerpfade bleiben unverändert gesperrt. Die eigene Anbindung akzeptiert nur konfigurierte IP-Adressen und lässt den Decoder keine Redirects verfolgen.

## Spätere begrenzte Steuerfreigaben

Seit den Versionen0.22–0.28 besitzt der Monitor getrennte, explizite Transportwege für Licht, Lüfter, Speed Mode, Solltemperaturen, Pause/Fortsetzen/Abbruch sowie Achsen/Homing/Motoren-Aus. Die normalen Bridge-Routen bleiben lesend; „keine Kamera-MQTT-Befehle“ gilt weiterhin für die Kameraansicht. Freigaben sind standardmäßig leer und pro Drucker getrennt. Diese Erweiterungen sind keine allgemeine beschreibbare Bridge. Die jeweiligen Dateien und Protokollgrenzen stehen in den Steuerungsdokumenten.

Die geplante Komplettinstallation bündelt Spoolman als getrennten unveränderten Dienst. Version, Originalquelle, Lizenztext und vollständige Abhängigkeiten müssen für jedes tatsächlich verteilte Paket festgehalten werden; dessen MIT-Lizenz ersetzt die Lizenzen seiner Abhängigkeiten nicht.
