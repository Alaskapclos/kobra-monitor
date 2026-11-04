# Kobra Monitor im Alltag

Ab Version 0.18.3 öffnet **Hilfe** oben in der Druckerübersicht die lokal gespeicherte Kurzhilfe. Die Themen lassen sich einzeln aufklappen.

## Einmal einrichten

1. **Standort wählen:** Auf einem Rechner läuft die Aufzeichnung, solange er eingeschaltet und wach ist. Ein NAS oder Server mit Docker eignet sich für dauerhaften Betrieb. Der Monitor-Host muss die Drucker im Heimnetz erreichen können. [Installation](INSTALLATION.md) · [UGREEN/UGOS](UGREEN_UGOS.md)
2. **Konto anlegen:** Den privaten Einrichtungslink öffnen und selbst Benutzername und Passwort festlegen. Danach auf weiteren Geräten mit demselben Konto anmelden. Keine Kennwörter weitergeben oder in Diagnoseberichte kopieren.
3. **Drucker hinzufügen:** LAN-Modus am Drucker einschalten, seine IP-Adresse unter **Einrichten** eintragen und **Speichern und verbinden** wählen. Bei mehreren Druckern jede Adresse einzeln hinzufügen. Der Assistent zeigt den Verbindungsstand; die IP findest du am Drucker oder im Router.
4. **Von unterwegs öffnen:** Eigenes VPN verbinden und die private Monitor-Adresse öffnen. Für Kamera und Benachrichtigungen HTTPS verwenden. [Fernzugriff](REMOTE_ACCESS.md)

## Drucker auswählen und anordnen

Jede Druckerkarte zeigt eigene Werte. Eine Karte auswählen, um unten ihre Details zu sehen. Über den Punktgriff die Reihenfolge ändern; alternativ die Karte mit Tab fokussieren und Alt + Pfeiltasten verwenden. Die Reihenfolge gilt auf allen Geräten, die Auswahl kann je Browser unterschiedlich sein.

Einen Druck startest du weiterhin selbst am Drucker oder mit deinem bisherigen Slicer. Der Monitor beobachtet ihn. Vorbereitung und Bettnivellierung gehören zum Auftrag. Frühe Restzeiten sind Schätzungen und können zunächst fehlen; ein Dateiname ist keine verlässliche Laufzeitmessung.

## Kameras öffnen

Unter **Kamera → Ansicht** zwischen ausgewähltem Drucker und Kameraübersicht wählen. In der Übersicht zwei oder vier Bilder pro Seite einstellen und **Kameras anzeigen** wählen. Bei mehr Druckern mit den Seitenknöpfen wechseln. Auf kleinen Bildschirmen stehen die Bilder untereinander.

FFmpeg wird auf dem Rechner oder NAS benötigt, auf dem der Monitor läuft. Handy und Anzeige-Browser brauchen keine FFmpeg-Installation. Im NAS-Paket ist es enthalten. Die Vorschau besteht aus ungefähr zwei Bildern pro Sekunde. Sie wird beim Öffnen geladen; mehrere Browser teilen sich serverseitig höchstens vier Kameraaufbereitungen. Die Kamera muss ihren lokalen Stream bereits bereitstellen; der Monitor sendet keinen Aktivierungsbefehl. [Kamera und Grenzen](CAMERA.md)

## Spulen zuordnen

1. **Spulenverwaltung → Spoolman öffnen** öffnet die angebundene Verwaltung. Falls noch nicht eingerichtet, unter **Einrichten** ihre vom Monitor erreichbare Adresse hinterlegen. Der Browser benötigt für die native Spoolman-Seite ebenfalls einen privaten Zugangsweg.
2. Spule in Spoolman anlegen und Gewicht/Material dort pflegen. Bei benutzten Spulen das gewogene Restgewicht verwenden; Verpackung oder Leer-Spule nicht als Filament mitrechnen.
3. Im Monitor **Spulen aktualisieren** wählen und den angezeigten Lesezeitpunkt prüfen.
4. Eine normale Herstellerkennung kann für mehrere Spulen gleich sein. Solche Spulen fest dem aktuellen Slot zuordnen und nach einem Wechsel selbst bestätigen. Eine feste Zuordnung folgt nicht automatisch dem physischen Wechsel.
5. Nur eine nachweislich individuelle Kennung, beispielsweise eines selbst beschriebenen ReSpool-Tags, ausdrücklich mit der passenden Spoolman-Spule verknüpfen. Danach zeigt der Monitor **Automatisch erkannt**; keine zusätzliche feste Slotbindung anlegen. Bei Duplikaten oder Konflikten zuerst die Angaben prüfen.

Die ACE-Prozentanzeige stammt vom Drucker. Grammwerte stammen aus dem Spoolman-Buchbestand. Das sind verschiedene Angaben: Der Monitor bucht noch keinen Verbrauch. Originaltags müssen für die manuelle Zuordnung nicht verändert werden. [Spulenverwaltung und Kennungen](SPOOLMAN.md)

## Benachrichtigungen aktivieren

Auf jedem gewünschten Gerät unter **Benachrichtigungen → Einrichten** selbst aktivieren, die Browsererlaubnis bestätigen und eine Testmeldung senden. Auf iPhone/iPad den Monitor zuerst in Safari zum Home-Bildschirm hinzufügen und über dieses Symbol öffnen. Auf Android einen unterstützten Browser über HTTPS verwenden. Hinweise in der Oberfläche beachten. [Voraussetzungen und Zustellung](NOTIFICATIONS.md)

## Verlauf und Verbindungsprobleme

Im **Druckverlauf** nach Datei oder Status filtern, **Verlauf ansehen** öffnen oder einen Bericht laden. **Beginn beobachtet** und **laufenden Druck erkannt** unterscheiden sich: Ein später entdeckter Druck wurde nicht vollständig beobachtet.

Bei fehlenden Daten den Lesezeitpunkt und **Betriebsstatus → Öffnen** prüfen. Ein Verbindungsverlust ist kein bestätigtes Druckende. Alte Werte und Bilder dürfen nicht als aktuelle Messung verstanden werden. In der vorbereiteten Version 0.18.3 zeigt die Detailansicht ausdrücklich **Status veraltet** und blendet alten Fortschritt aus; installierte ältere Versionen können anders aussehen.

- Nur unterwegs nicht erreichbar: VPN-Verbindung und richtige HTTPS-Adresse prüfen.
- Oberfläche erreichbar, Drucker offline: Strom/LAN-Modus/IP am Drucker und Netzwerkweg vom Monitor-Host prüfen.
- Kamera fehlt: Hinweise unter Kamera/Betriebsstatus prüfen; FFmpeg gehört auf den Monitor-Host.
- Spule nicht automatisch erkannt: Bestand lesend aktualisieren, individuelle Kennung, Konflikte und Druckerdatenfrische prüfen.
- Nach einem Dienstneustart abgemeldet: mit dem bestehenden Konto anmelden. Kein neues Konto anlegen.

Der kopierbare Betriebsbericht ist für eine gezielte Diagnose gedacht; private Sicherungen, Passwörter oder Schlüssel nicht veröffentlichen. Kontowiederherstellung: [Benutzerkonto](INSTALLATION.md#benutzerkonto).

## Daten erhalten

Der Monitor muss weiterlaufen, damit die Historie aufgezeichnet wird. Das Schließen des Browsers beendet den Dienst nicht. Vor Updates die Sicherung prüfen und das Datenvolume erhalten. Monitor und Spoolman getrennt sichern; eine zusätzliche Kopie außerhalb des NAS schützt gegen dessen Ausfall. [Sicherung und Wiederherstellung](BACKUPS.md) · [Update und Rückkehr zum bisherigen Stand](UPDATE_RECOVERY.md)

Aktuelle Grenzen und noch offene Nachweise: [Prüfstand](VALIDATION.md) · [Projektplan](../ROADMAP.md). Upload, Druckstart, Pause/Stop, Heizung, Bewegung und Filamentsteuerung sind im Lesebetrieb nicht enthalten.
