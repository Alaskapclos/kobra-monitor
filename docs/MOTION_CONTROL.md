# Manuelle Achsensteuerung

**Installationsweg beachten:** Native 0.42-Pakete und die ausdrücklich gewählte LAN-Docker-Suite verwalten Freigaben unter **Einrichten → Steuerung freigeben**. Änderungen gelten nach vollständigem Monitor-Neustart, bei Docker nach Container-Neustart. Bis dahin gelten die alten Freigaben. Die folgenden Umgebungsvariablen betreffen den eigenen Quellstart beziehungsweise entsprechend verwaltete bisherige Container; native Pakete übernehmen keine beliebigen Steuerrechte aus der Umgebung. [Freigabeverwaltung](NATIVE_CONTROLS.md).

Standardmäßig deaktiviert. `KOBRA_MOTION_CONTROL_IPS` muss die freigegebenen S1-Adressen enthalten. Separate Freigabe, Modell 20025; zuerst nur ein betreut getesteter Drucker. Kein allgemeiner G-Code, keine Extrusion und kein automatisches Homing vor einem Schritt.

In der Übersicht: X/Y/Z jeweils ±1, ±15 oder ±50 mm; getrennte Referenzfahrten XY und Z. Vor der ersten X/Y/Z-Fahrt ein Dialog mit Drucker und genauer Fahrt. Nach erfolgreichem Versand mit bestätigter Anwesenheit gelten weitere X/Y/Z-Klicks in derselben Anmeldung an diesem Drucker bis zum nächsten regulären Druck ohne erneuten Dialog. Schon dessen Vorbereitung setzt die Freigabe zurück. Neue Anmeldung oder Dienstneustart erfordern ebenfalls eine neue Bestätigung. Homing und „Motoren ausschalten“ behalten immer einen eigenen Bestätigungsdialog. Die Bestätigung bleibt gesperrt, bis der Bediener seine Anwesenheit und den geprüften freien Fahrweg bestätigt. Nur direkt vor dem Drucker verwenden: Kollisions- und Beschädigungsgefahr. Kamerabeobachtung ersetzt die Anwesenheit nicht. Bauteile und Hindernisse entfernen; Düse und Bett beobachten. Bei Z bewegt sich das Druckbett, das Plus fährt den Tisch nach oben, Minus nach unten; dafür wird das Vorzeichen beim Versand gegenüber der Z-Koordinate umgekehrt.

Nur frische empfangene `info` mit `state=free` und ohne Projekt erlauben Fahrten. Druck, Pause, Vorbereitung, Fehler, unvollständige oder veraltete Daten und Wiederverbindungen sperren sie. Jede neue Phase verwirft alte Bestätigungen; erneute Abfrage vor Vorbereitung und erneuter Leerlauf-/Verbindungscheck unmittelbar unter Socket-Lock vor Versand. Ein zwischen Meldungen unbemerkter Zustandswechsel bleibt grundsätzlich unbeobachtbar.

Gemeinsame einmalige Steuerabsicht und SQLite-Schaltprotokoll mit den anderen Steuerungen. Genau ein Versandversuch, keine Queue von Fahrbefehlen und keine Wiederholung nach Fehler/Timeout. 5 Sekunden Abstand nach Schritten, 30 Sekunden nach Referenzfahrten. Nach Neustart gilt vorsorglich 30 Sekunden Sperre, wenn frühere Bewegungsversuche protokolliert sind. Wartezeiten sind keine Stillstands- oder Sicherheitsgarantie. Der Bediener muss die Bewegung und ihren Stillstand vor Ort prüfen.

Ohne belegte Positions- und Abschlussmeldung lautet das Ergebnis ausdrücklich „Befehl gesendet“, niemals „Fahrt abgeschlossen“. Ein ACK oder eine weiterhin freie Statusmeldung beweist keine mechanische Ausführung. Bei Fehler unbestätigter Ausgang; nicht automatisch erneut versuchen. Unreferenzierte Achsen können vom Drucker abgelehnt werden. Keine eigene Kollisionserkennung oder Behauptung bekannter Achspositionen.

## Protokollgrundlage

- [anycubic-cloud-api LAN-Befehle](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/lan/commands.py): `axis/move`.
- [Bewegungsparameter](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/api/functions.py): Achsen 1=X, 2=Y, 3=Z; move_type 0=minus, 1=plus, 2=Referenz; positive Entfernung.
- [S1-spezifische Referenzfahrt](https://github.com/Nino6689/anycubic-cloud-api/blob/main/src/anycubic_cloud_api/data_models/printer.py): Achse4 referenziert XY, Z separat über3. Keine gemeinsame Folge automatisch senden.

Die gebündelte ältere Bridge enthält widersprüchliche Kommentare und einen anderen signed-distance-Aufruf. Sie wird dafür nicht freigeschaltet oder kopiert. Neuer begrenzter Versand nutzt ausschließlich die oben dokumentierten Formen. Synthetische Prüfungen ersetzen nicht die erste beaufsichtigte physische Abnahme; zunächst 1-mm-Richtungen am ausgewählten S1 testen.

Die gesonderten Schaltflächen heißen „Homing Druckkopf (X/Y)“ und „Homing Druckbett (Z)“. X/Y-Zuordnung ist durch Besitzer bestätigt; Z-Anzeige seit0.27.1 auf Tischrichtung angepasst. Die darunterliegende Protokollachse und XY-Homingform bleiben unverändert.

## Motoren ausschalten

Eigene Schaltfläche im Achsenbereich; ausschließlich im frischen Leerlauf, nach bestehender Bewegungssperre und mit eigener Anwesenheitsbestätigung bei jedem Aufruf. Die Haltekraft entfällt; Achsen können ihre Position verlieren, weitere Fahrten können Referenzfahrt benötigen. Keine Heizungsabschaltung und kein Not-Aus. Es wird einmal `axis/turnOff` mit `data=null` gesendet, niemals automatisch nach Homing. Gemeinsame Sperre, Sitzungs-/Kontextprüfung und Protokollierung wie bei Fahrten; keine automatische Wiederholung. Eine Freigabe für wiederholte X/Y/Z-Fahrten ersetzt diesen Dialog nicht, der Motor-Aus-Dialog erteilt auch keine X/Y/Z-Freigabe. Ergebnis bleibt ausdrücklich „Befehl gesendet“; keine belegte Motorstatus-Telemetrie.

Am 03.11.2026 wurde dieser exakte Befehl am zweiten S1 betreut getestet: Besitzer bestätigte, dass der zuvor nach Homing laufende Lüfter ausging. Das ist kein unabhängiger Nachweis der Lüfterhardware oder ein Test des ersten Geräts. Protokollbeleg: gebündelte Bridge `handle_api_axis`, Aktion `turnOff`.
