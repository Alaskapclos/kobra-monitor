# Kamera

Unter **Kamera anzeigen** öffnest du den vorhandenen lokalen Stream des ausgewählten Druckers. Die Ansicht lädt ungefähr zwei Bilder pro Sekunde. Bilder werden im Arbeitsspeicher verarbeitet, nicht aufgezeichnet. Beim Wechsel des Druckers, Öffnen der Einrichtung oder Verlassen des Tabs wird die Ansicht geschlossen. Eine ungenutzte Verbindung wird nach etwa 15–18 Sekunden beendet.

Die Kamera nutzt dieselbe Anmeldung wie Status und Verlauf. Auf Handy und Rechner über die private HTTPS-Adresse zugreifen; Tailscale oder das eigene VPN muss verbunden sein. Der Browser spricht nur mit dem Monitor, nicht direkt mit dem Drucker.

## Voraussetzungen

Getestetes Ziel: Stock-Kobra-S1 mit bereits erreichbarem FLV-Stream an Port 18088. Es werden keine startCapture-/stopCapture-Befehle gesendet. Eine ausgeschaltete oder nicht bereitgestellte Kamera wird nicht automatisch aktiviert. Der Leseschutz der MQTT-Verbindung bleibt unverändert.

Das Docker-/NAS-Paket installiert FFmpeg aus Debian. Native Installationen benötigen aktuelles FFmpeg mit HTTP-Option `max_redirects` im Suchpfad; anschließend den Monitor neu starten. Ohne passenden Decoder bleibt die Schaltfläche deaktiviert. Der Kamerapfad lehnt HTTP-Weiterleitungen und andere Eingabeprotokolle ab. Er akzeptiert ausschließlich eingerichtete Drucker, keine frei eingegebenen Stream-URLs.

Maximal zwei Drucker werden gleichzeitig dekodiert. Mehrere Browser mit demselben Drucker teilen sich einen Decoder. Dies begrenzt Last und Verbindungen zum Drucker. Aufnahmen, Ton, Kameraaktivierung, Bewegungs- und Drucksteuerung gehören nicht zu dieser Funktion.

## Herkunft

JPEG-Decodierung und Cache: bestehende `CameraCache`-Implementierung aus kobra-bridge (GPL-3.0), siehe SOURCES.json. Die eigene schmale Anbindung startet ausschließlich den JPEG-Teil und beendet inaktive Leser. Kleine lokale Anpassung der JPEG-Ausgabe: voller Farbbereich und ein Encoder-Thread für kompatible FFmpeg-Versionen. Keine eigene Video- oder Druckerprotokollimplementierung.

FFmpeg: https://ffmpeg.org/ ; [Debian-Quellpaket](https://sources.debian.org/src/ffmpeg/). Paketversion und komponentenspezifische Lizenzhinweise stehen im Container unter `/usr/share/doc/ffmpeg/copyright` bzw. können mit `dpkg-query -W ffmpeg` ermittelt werden. FFmpeg und seine Bibliotheken behalten ihre jeweiligen LGPL-/GPL-Lizenzen. Sie sind eigenständige Prozesse, keine Python-Abhängigkeit aus PyPI.

## Prüfstand

Auf beiden vorhandenen S1 ohne MQTT-Kamerabefehle FLV gelesen und echte 1280×720-JPEG-Bilder erzeugt. Getrennte Browser-Vorschau: beide Kameras sichtbar, beim Druckerwechsel vorheriges Bild geschlossen. Automatische Tests prüfen Anmeldung, verbotene Steuerpfade, festes Ziel, Weiterleitungssperre, gemeinsame Decoder, Leerlaufbereinigung, veraltete Bilder und Kapazitätsgrenze. Zusätzlicher echter Decoder-Test verwendet nur einen künstlichen lokalen FLV-Stream. NAS-Deployment und Handyprüfung werden nachgetragen.
