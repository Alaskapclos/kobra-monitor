# ACE-Klima und Trocknung

**Installationsweg beachten:** Native 0.42-Pakete und die ausdrücklich gewählte LAN-Docker-Suite verwalten Freigaben unter **Einrichten → Steuerung freigeben**. Änderungen gelten nach vollständigem Monitor-Neustart, bei Docker nach Container-Neustart. Bis dahin gelten die alten Freigaben. Die folgenden Umgebungsvariablen betreffen den eigenen Quellstart beziehungsweise entsprechend verwaltete bisherige Container; native Pakete übernehmen keine beliebigen Steuerrechte aus der Umgebung. [Freigabeverwaltung](NATIVE_CONTROLS.md).

Stand **0.38.0-alpha.1**. Auf dem NAS installiert und Sensor-/Zustandsanzeige nach Anmeldung geprüft; noch keine praktische Heizungsabnahme am realen ACE.

## Anzeige und Bedienung

Jede Druckerkachel zeigt je gemeldetem ACE Temperatur, verfügbare relative Luftfeuchte und Trocknungszustand. Während einer gemeldeten Trocknung erscheint die Restzeit. Nicht vorhandene, ungültige oder veraltete Werte erscheinen als „—“ beziehungsweise „unbekannt“; fehlende Luftfeuchte bedeutet nicht 0 %. Reale Nullwerte bleiben sichtbar. Sensorwerte werden unabhängig voneinander auf Frische geprüft, nach 60 Sekunden nicht mehr als aktuell dargestellt.

Der Schalter steht direkt bei den ACE-Werten. Er öffnet einen Dialog für genau diesen Drucker und ACE. Einschalten erfordert eine ausdrücklich gewählte Temperatur und Dauer und die Bestätigung mit OK. Keine automatische Materialvorgabe. Ausschalten benötigt ebenfalls die Bestätigung. Die Trocknung betrifft alle eingelegten Spulen; Grenzen des Filaments und des Spulenkörpers beachten. Das Ausschalten der ACE-Heizung ist kein Druckabbruch.

## Ausdrückliche Freigabe

`KOBRA_DRYING_CONTROL_IPS` ist standardmäßig leer. Nur für ausdrücklich freigegebene S1-Drucker wird ein bedienbarer Schalter angeboten. Die konservative Temperaturgrenze ist 55 °C. Ein nachweislich angeschlossener ACE 2 Pro kann in `KOBRA_DRYING_TEMPERATURE_LIMITS` pro freigegebener Drucker-IP ausdrücklich auf 65 gesetzt werden, als JSON-Objekt. Der Monitor leitet die Gerätegeneration nicht aus fehlender Luftfeuchte ab. Die Freigabe gilt für die angeschlossenen ACE-Geräte dieses Druckers; nach einem Gerätewechsel die Grenze erneut prüfen.

Erlaubt sind ganze Grad von 30 bis zur eingerichteten Grenze und ganze Minuten von 10 bis 1440. Die höhere Grenze lässt sich weder durch einen Browserparameter noch einen beliebigen Befehl überschreiben. Native Desktop-Testpakete übernehmen diese Rechte nicht automatisch.

## Versand und Rückmeldung

Anmeldung, Besitzerrecht, CSRF und Origin bleiben erforderlich. Aktuelle bestätigte Zustandsdaten desselben ACE und derselben Verbindung müssen höchstens 15 Sekunden alt sein. Änderung von ACE-Konfiguration, Verbindung, Material oder Druckauftrag verwirft eine vorbereitete Bestätigung. Einmalige, kurzlebige Vorgänge werden persistent protokolliert. Kein automatischer Neuversuch nach Verbindungsverlust oder Neustart, keine optimistische Anzeige „an“ nur wegen eines gesendeten Befehls.

Ein begrenzter `multiColorBox/setDry`-Aufruf adressiert genau eine ACE-ID. Der generische Bridge-Leseschutz bleibt unverändert. Andere Steuerungen und Archivstarts teilen die Versandreservierung; ein Druckabbruch bleibt verfügbar. Bestätigung erfolgt ausschließlich durch eine nachfolgende passende Druckermeldung. Unklare Rückmeldung verlangt eine Statusprüfung am Gerät.

## Prüfstand und Quellen

Automatisierte Tests verwenden künstliche Geräte und abgefangene Sockets. Desktop- und schmale Browseransicht wurden mit synthetischen Daten geprüft. Kein Heizbefehl wurde dabei an einen echten Drucker gesendet. Die Installation und praktische Abnahme des neuen Schalters sind getrennte Schritte.

Herstellergrenzen: [ACE Pro](https://store.anycubic.com/products/anycubic-ace-pro), [ACE 2 Pro](https://wiki.anycubic.com/en/fdm-3d-printer/ace-2-pro/warm-tips). Protokollvorbild ist der enthaltene [Kobra-Bridge-Quellcode](https://github.com/cluzl/kobra-bridge/blob/main/kobrax_moonraker_bridge.py); keine allgemeine Firmware- oder Modellkompatibilität zugesagt.
