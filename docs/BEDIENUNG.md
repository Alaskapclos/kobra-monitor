# Kobra Monitor im Alltag

Ab Version 0.18.3 öffnet **Hilfe** oben in der Druckerübersicht die lokal gespeicherte Kurzhilfe. Die Themen lassen sich einzeln aufklappen.

Stand 09.11.2026. Für das passende Installationspaket zuerst die [README](../README.md) und [Paketübersicht](PLATFORM_SUPPORT.md) lesen.

## Einmal einrichten

1. **Standort wählen:** Auf einem Rechner läuft die Aufzeichnung, solange er eingeschaltet und wach ist. Ein NAS oder Server mit Docker eignet sich für dauerhaften Betrieb. Der Monitor-Host muss die Drucker im Heimnetz erreichen können. [Installation](INSTALLATION.md) · [UGREEN/UGOS](UGREEN_UGOS.md)
2. **Konto anlegen:** Den privaten Einrichtungslink öffnen und selbst Benutzername und Passwort festlegen. Danach auf weiteren Geräten mit demselben Konto anmelden. Keine Kennwörter weitergeben oder in Diagnoseberichte kopieren.
3. **Drucker hinzufügen:** LAN-Modus am Drucker einschalten, seine IP-Adresse unter **Einrichten** eintragen und **Speichern und verbinden** wählen. Bei mehreren Druckern jede Adresse einzeln hinzufügen. Der Assistent zeigt den Verbindungsstand; die IP findest du am Drucker oder im Router.
4. **Von unterwegs öffnen:** Eigenes VPN verbinden und die private Monitor-Adresse öffnen. Für Kamera und Benachrichtigungen HTTPS verwenden. [Fernzugriff](REMOTE_ACCESS.md)

## Drucker auswählen und anordnen

Jede Druckerkarte zeigt eigene Werte. Eine Karte auswählen, um unten ihre Details zu sehen. Über den Punktgriff die Reihenfolge ändern; alternativ die Karte mit Tab fokussieren und Alt + Pfeiltasten verwenden. Die Reihenfolge gilt auf allen Geräten, die Auswahl kann je Browser unterschiedlich sein.

Neue Modelle slicest und überträgst du weiterhin mit deinem bisherigen Slicer. Erfolgreiche Aufträge mit passendem Archivoriginal kannst du nach Prüfung und ausdrücklicher Startbestätigung aus dem Monitor wiederholen. Vorbereitung und Bettnivellierung gehören zum Auftrag. Frühe Restzeiten sind Schätzungen und können zunächst fehlen; ein Dateiname ist keine verlässliche Laufzeitmessung.

## ACE-Klima und Trocknung

Direkt in jeder Druckerkachel stehen Temperatur, verfügbare Luftfeuchte und gemeldeter Trocknungszustand des jeweiligen ACE. „—“ bedeutet keine aktuelle Messung. Nach Freigabe öffnet der Schalter einen Dialog: beim Einschalten passende Temperatur und Dauer wählen, dann mit OK bestätigen. Auch Ausschalten wird bestätigt. Alle Spulen im ACE werden erwärmt; Material- und Spulengrenzen beachten. [Details und Prüfstand](ACE_DRYING.md).

## Kameras öffnen

Unter **Kamera → Ansicht** zwischen ausgewähltem Drucker und Kameraübersicht wählen. In der Übersicht zwei oder vier Bilder pro Seite einstellen und **Kameras anzeigen** wählen. Bei mehr Druckern mit den Seitenknöpfen wechseln. Auf kleinen Bildschirmen stehen die Bilder untereinander.

FFmpeg wird auf dem Rechner oder NAS benötigt, auf dem der Monitor läuft. Handy und Anzeige-Browser brauchen keine FFmpeg-Installation. Im NAS-Paket ist es enthalten. Die Vorschau besteht aus ungefähr zwei Bildern pro Sekunde. Sie wird beim Öffnen geladen; mehrere Browser teilen sich serverseitig höchstens vier Kameraaufbereitungen. Die Kamera muss ihren lokalen Stream bereits bereitstellen; der Monitor sendet keinen Aktivierungsbefehl. [Kamera und Grenzen](CAMERA.md)

## Spulen zuordnen

1. **Spulen → Spulen verwalten** öffnet die angebundene Originalverwaltung innerhalb des Monitors. Falls noch nicht eingerichtet, unter **ACE & Zuordnung → Einrichten** ihre vom Monitor erreichbare Adresse hinterlegen. Der zusätzliche Link **Spoolman öffnen** bietet den direkten Zugang in einem eigenen Tab.
2. Spule in Spoolman anlegen und Gewicht/Material dort pflegen. Bei benutzten Spulen das gewogene Restgewicht verwenden; Verpackung oder Leer-Spule nicht als Filament mitrechnen.
3. Im Monitor **Spulen aktualisieren** wählen und den angezeigten Lesezeitpunkt prüfen.
4. Eine normale Herstellerkennung kann für mehrere Spulen gleich sein. Solche Spulen fest dem aktuellen Slot zuordnen und nach einem Wechsel selbst bestätigen. Eine feste Zuordnung folgt nicht automatisch dem physischen Wechsel.
5. Nur eine nachweislich individuelle Kennung, beispielsweise eines selbst beschriebenen ReSpool-Tags, ausdrücklich mit der passenden Spoolman-Spule verknüpfen. Danach zeigt der Monitor **Automatisch erkannt**; keine zusätzliche feste Slotbindung anlegen. Bei Duplikaten oder Konflikten zuerst die Angaben prüfen.

Die ACE-Prozentanzeige stammt vom Drucker. Grammwerte stammen aus dem Spoolman-Buchbestand. Das sind verschiedene Angaben: Der Monitor bucht noch keinen Verbrauch. Originaltags müssen für die manuelle Zuordnung nicht verändert werden. [Spulenverwaltung und Kennungen](SPOOLMAN.md)

## Benachrichtigungen aktivieren

Auf jedem gewünschten Gerät unter **Benachrichtigungen → Einrichten** selbst aktivieren, die Browsererlaubnis bestätigen und eine Testmeldung senden. Auf iPhone/iPad den Monitor zuerst in Safari zum Home-Bildschirm hinzufügen und über dieses Symbol öffnen. Auf Android einen unterstützten Browser über HTTPS verwenden. Hinweise in der Oberfläche beachten. [Voraussetzungen und Zustellung](NOTIFICATIONS.md)

## Verlauf und Verbindungsprobleme

Im **Druckverlauf** nach Datei oder Status filtern, **Verlauf ansehen** öffnen oder einen Bericht laden. **Beginn beobachtet** und **laufenden Druck erkannt** unterscheiden sich: Ein später entdeckter Druck wurde nicht vollständig beobachtet.

Bei fehlenden Daten den Lesezeitpunkt und **Betriebsstatus → Öffnen** prüfen. Ein Verbindungsverlust ist kein bestätigtes Druckende. Alte Werte und Bilder dürfen nicht als aktuelle Messung verstanden werden. Die Detailansicht zeigt ausdrücklich **Status veraltet** und blendet alten Fortschritt aus; installierte ältere Versionen können anders aussehen.

- Nur unterwegs nicht erreichbar: VPN-Verbindung und richtige HTTPS-Adresse prüfen.
- Oberfläche erreichbar, Drucker offline: Strom/LAN-Modus/IP am Drucker und Netzwerkweg vom Monitor-Host prüfen.
- Kamera fehlt: Hinweise unter Kamera/Betriebsstatus prüfen; FFmpeg gehört auf den Monitor-Host.
- Spule nicht automatisch erkannt: Bestand lesend aktualisieren, individuelle Kennung, Konflikte und Druckerdatenfrische prüfen.
- Nach einem Dienstneustart abgemeldet: mit dem bestehenden Konto anmelden. Kein neues Konto anlegen.

Der kopierbare Betriebsbericht ist für eine gezielte Diagnose gedacht; private Sicherungen, Passwörter oder Schlüssel nicht veröffentlichen. Kontowiederherstellung: [Benutzerkonto](INSTALLATION.md#benutzerkonto).

## Daten erhalten

Der Monitor muss weiterlaufen, damit die Historie aufgezeichnet wird. Das Schließen des Browsers beendet den Dienst nicht. Vor Updates die Sicherung prüfen und das Datenvolume erhalten. Monitor und Spoolman getrennt sichern; eine zusätzliche Kopie außerhalb des NAS schützt gegen dessen Ausfall. [Sicherung und Wiederherstellung](BACKUPS.md) · [Update und Rückkehr zum bisherigen Stand](UPDATE_RECOVERY.md)

Aktuelle Grenzen und noch offene Nachweise: [Prüfstand](VALIDATION.md) · [Projektplan](../ROADMAP.md). Upload, Druckstart, Pause/Stop, Heizung, Bewegung und Filamentsteuerung sind im Lesebetrieb nicht enthalten.


## Achsen und Homing bewusst öffnen

Lichtschalter, Lüftereinstellungen, Speed Mode, Temperaturen und Druckaktionen bleiben in der Übersicht an ihrer passenden Stelle sichtbar, soweit sie für den Drucker freigegeben sind. Ihre Verfügbarkeit hängt weiterhin von frischen Daten und dem passenden Druckzustand ab. Licht schaltet direkt; andere Aktionen behalten ihre Bestätigung.

Nur für manuelle Bewegung, Homing und Motoren-Aus zunächst „Achsen & Homing öffnen“ direkt über dem Achsenbereich wählen. „Achsen & Homing schließen“, ein Drucker- oder Bereichswechsel sowie eine verlorene Verbindung schließen diesen Bereich wieder. Beim Neuladen startet er geschlossen. Das Öffnen sendet keinen Druckerbefehl und ersetzt keine Anwesenheits- oder Aktionsbestätigung. Lüfter- und Lichtsteuerung hängen nicht von diesem Schalter ab.

## Restmenge ohne ACE-Meldung

Wenn das ACE keine Restmenge übermittelt, verwendet die Slotkarte die zugeordnete aktuelle Spoolman-Spule: Restgewicht / ursprüngliches Filamentgewicht × 100. Die Grammangabe nennt Spoolman als Quelle. Ein Beispiel: 375 g von ursprünglich 750 g ergeben 50 Prozent. Ohne gültiges Ausgangsgewicht wird nur das Restgewicht angezeigt; es wird nicht pauschal 1 kg angenommen. Eine vom Drucker gemeldete Restmenge hat Vorrang, auch bei 0 Prozent.

Die Anzeige ist ein Buchbestand, keine Messung und kein automatisch abgezogener Druckverbrauch. Gewichte weiterhin in Spoolman pflegen. Zuordnungskonflikte, leere Steckplätze, Verbindungsverlust und nicht aktueller Bestand führen nicht zu erfundenen Restwerten. Die sichtbare Oberfläche liest den Bestand regelmäßig erneut; bei ausgeblendeter Browserseite wird keine regelmäßige Aktualisierung vorausgesetzt.

Unter „Spulen → ACE & Zuordnung“ kann die Restmengenquelle je Drucker gewählt werden. Standard ist „ACE · Spoolman bei fehlender Angabe“. Liefert ein ACE nicht nutzbare Nullwerte, ausdrücklich „Spoolman-Bestand“ wählen. Dann zählen ausschließlich aktuelle zugeordnete Spoolman-Spulen; fehlende Zuordnungen bleiben unbekannt, statt einen ACE-Wert unter dieser Quellenwahl auszugeben. Die Wahl wird auf dem Monitor gespeichert und verändert weder ACE noch Spoolman-Bestand.


## ACE direkt in der Druckerkachel

Auf der Übersicht zeigt jede Druckerkachel ihre eigenen ACE-Slots mit Spulenfarbe, Material, geladenem Slot und Restmenge. Die Zuordnung und die je Drucker gewählte Restmengenquelle entsprechen der großen Ansicht unter „Spulen“. Spoolman-Buchwerte sind entsprechend gekennzeichnet; sie werden nicht automatisch verbraucht. Bei fehlendem Ausgangsgewicht ist kein Prozentwert berechenbar. Veraltete ACE-Daten sind gekennzeichnet und zeigen keine aktuelle Restmenge. Ein Klick auf die Kachel wählt die Detailansicht dieses Druckers; Zuordnungen werden unter „Spulen“ verwaltet.

## Druckdateien ansehen

Unter **Druckaufträge → Druckdatei-Archiv** nach dem Dateinamen suchen und **Vorschau öffnen** wählen. Bildquellen, 3D-Kernmodelle und lineare Druckbahnen lassen sich einzeln auswählen. Drehen mit Ziehen oder Pfeiltasten, Zoomen mit +/− oder Mausrad. In der Druckbahnenansicht begrenzt ein Höhenregler die sichtbaren Bahnen. Bei zugeordneten Aufträgen führt **Zugeordnete Datei ansehen** zur Vorschau. [Formate, Größenlimits und Entwicklungsstand](FILE_ARCHIVE.md#bildübersicht-und-lokale-3d-vorschau-entwicklungsstand).

Der neue Erprobungsstand bietet **Druck wiederholen** für erfolgreiche Abschlüsse mit Original und einen zusätzlich freigegebenen S1. Ziel und ACE-Slots auswählen, erst prüfen und übertragen, danach freies Druckbett, Material und Düse bestätigen und bewusst starten. Neue Historie und Berichte bleiben vom Quellauftrag getrennt. Ein realer Stock-S1-Start und erfolgreicher Abschluss sind vom Besitzer bestätigt; andere Konfigurationen bleiben separat zu prüfen; die Freigabe ist standardmäßig ausgeschaltet. [Vollständiger Wiederholungsablauf](REPRINT.md).

## Dauerhafte Freigaben und Updates

Native 0.42-Pakete und die LAN-Docker-Suite beginnen lesend. Unter Einrichten die Funktionen pro Drucker bewusst speichern; erst nach vollständigem Monitor-Neustart gelten die neuen Freigaben. In Docker den Monitor-Container neu starten. Bis dahin gelten auch bei einem Entzug die bisherigen Rechte. Ein Browser-Neuladen genügt nicht.

Die bestätigte native Profilübernahme ist kein allgemeiner automatischer Versionsupdater. Quellordner und Ausgangsversion kontrollieren; zuvor separat übernommene Profile werden nicht automatisch als jeweils neuester Stand gesucht. [Details](NATIVE_UPGRADE.md).
