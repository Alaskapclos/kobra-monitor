# Historische Freigabechecklisten

## Erprobungsstand 0.36.0-alpha.1 vom 07.11.2026

Die Archivwiederholung ist im Quellstand mit eigener, standardmäßig leerer Druckerfreigabe integriert. Ein simuliertes Browser-Szenario prüft die getrennte Übertragung/Startbestätigung, den neuen Auftrag, automatische Originalzuordnung und unveränderten Quellbericht; Desktop und 390-Pixel-Ansicht wurden geprüft. Noch kein physischer Handy- oder Stock-S1-Upload-/Startnachweis für diesen Stand. [Einzelheiten](REPRINT.md).

- [ ] Finalen Linuxbau und Prüfungen am eingefrorenen 0.36-Quellpaket abschließen.
- [ ] Vor-/Nachsicherung und getrennte Wiederherstellung bei einer späteren NAS-Aktualisierung prüfen.
- [ ] Die zusätzliche Startfreigabe unmittelbar vor einer kontrollierten Realgeräte-Erprobung ausdrücklich vom Besitzer bestätigen lassen.
- [ ] Originalpaket-Upload, neue Slotzuordnung und tatsächlichen Druckbeginn am Stock-S1 mit Besitzer am vorbereiteten Gerät abnehmen.
- [ ] Öffentliche Freigabe erst nach diesem Nachweis oder mit ausgelassener experimenteller Startfunktion.

## Frühere begrenzte Alpha-Abnahme

Zielstand **0.30.1-alpha.1**, vorbereitet am04.11.2026. Dieses Dokument veröffentlicht nichts und gibt keine Druckerbefehle frei. Weitere Großfunktionen sind keine Voraussetzung dieser begrenzten Alpha.

## Für diese Version abschließen

- [x] Vollständiger Linuxbau mit Python3.11/3.14, Bridge-/JavaScript-Prüfungen, Containerstart, Kamera- und Wiederherstellungsprüfung für exakt den verpackten Quellstand.
- [ ] Versionsangaben, Quellmanifest, Lizenzen und Veröffentlichungsinhalt konsistent; nur geprüfte öffentliche Programmdateien im ZIP/Image. Image und Quellen derselben Version gemeinsam bereitstellen.
- [x] NAS-Update mit erhaltenen Volumes, Vor-/Nachsicherung und getrennter Wiederherstellung. Danach angemeldete Desktop-/schmale Ansicht: Licht/Lüfter sichtbar bei geschlossenem Achsenbereich, Öffnen/Schließen nur für Achsen/Homing, keine Befehle durch das Öffnen.
- [x] Pause/Fortsetzen am laufenden Druck des zweiten S1 am04.11.2026: Pause und Fortsetzen, Rückmeldung „vom Drucker bestätigt“ passend zum tatsächlichen Zustand. Besitzer steht direkt am Gerät; Druck selbst starten und Änderungen ausdrücklich auslösen.
- [ ] Nach einem neuen regulären Druck erneut manuelle X/Y/Z-Fahrt anfordern: erste Anwesenheitsbestätigung erforderlich, danach weitere Schritte ohne wiederholte Nachfrage; Homing behält seine eigene Bestätigung. Im frischen Leerlauf, mit freiem Bauraum und Besitzer am Gerät prüfen.

Der Abschluss dieser Punkte wird mit einem neuen versionsgebundenen Prüfbericht belegt. Keine Statusmeldungen als physische Beobachtung ausgeben. Wird ein Nachweis nicht erbracht, offen lassen und gemeinsam entscheiden, ob die betroffene optionale Funktion bis zur Abnahme aus der öffentlichen Freigabe ausgenommen wird.

## Unmittelbar vor Veröffentlichung

- Repository und tatsächlich zu veröffentlichende ZIPs/Images auf Laufzeitdaten, private Schlüssel, Kontodateien, Archivzugänge, Originalmodelle, Sicherungen, lokale Pfade und persönliche Screenshots prüfen. Beispielbilder dürfen nur Testdaten zeigen.
- README der konkreten Version, Installationswege, Standard-Lesebetrieb und einzeln erforderliche Steuerfreigaben durchgehen. Windows/ARM/andere Modelle nur entsprechend belegter Prüfung nennen.
- Bekannte Grenzen aus [VALIDATION.md](VALIDATION.md) und [SECURITY.md](../SECURITY.md) mitliefern. Keine automatische Verbrauchsbuchung oder garantierte Slicer-Erfassung bewerben. Archivwiederholung nur mit ihren ausdrücklich benannten Erprobungsgrenzen und separater Freigabe beschreiben.
- Quellcode und Fremdlizenzen zu den enthaltenen Komponenten mitliefern; [Herkunft](UPSTREAM.md), [NOTICE](../NOTICE.md) und LICENSE erhalten.
- Erst nach ausdrücklichem Auftrag des Besitzers Release erstellen bzw. Repository öffentlich schalten. Ein vorbereiteter Stand ist keine Veröffentlichungsfreigabe.

## Nach der ersten Alpha

Weitere Slicer-/Plattformabnahme, Archiv-Nachdruck, Verbrauchsbuchung/Statistik, weitere NFC-Formate und große Flotten separat planen. Diese Funktionen werden nicht stillschweigend zur ersten Alpha hinzugefügt.

## Neuer Paketumfang: Komplettinstallation

Native Komplettinstaller und das gemeinsame Server-/NAS-Paket sind jetzt Teil der Vorbereitung, noch keine ausgelieferten Produkte. Ihre Freigabe benötigt je Zielsystem einen frischen Installations-, Update-, Deinstallations- und Wiederherstellungsnachweis sowie das vollständige versionsgebundene Lizenz-/Quellenverzeichnis. Einzelheiten: [INSTALLERS.md](INSTALLERS.md).

## ACE-Erweiterung 0.37

Zusätzliche Trocknungsrechte standardmäßig leer. Vor Freigabe Linuxbau und Wiederherstellung, produktive Sensoranzeige sowie Ein-/Ausschalten am realen passenden ACE prüfen. Keine reale Heizungsabnahme behaupten.

## Aktualisierter Prüfstand 0.38

Die älteren versionsgebundenen Abschnitte bleiben als historische Checklisten erhalten. Für 0.36 und 0.37 sind Linuxbauten, NAS-Installation und isolierte Vor-/Nachwiederherstellung belegt. Der Besitzer hat einen Archivdruck auf dem 2. Stock-S1 gestartet und den laufenden Druck bestätigt; ein vollständiger Abschluss dieses Wiederholungstests ist noch nicht als Abnahme dokumentiert. Die zusätzliche Startfreigabe bleibt auf diesen Drucker begrenzt.

Für 0.38 kommt ausschließlich ein lesender Materialvorrat-Hinweis hinzu. Lokale JavaScript- und simulierte Desktop-/390px-Prüfung erfolgreich; abschließender Linuxbau und NAS-Vor-/Nachsicherung sind vor Installation erneut erforderlich.

Offene praktische Punkte: Achsenbestätigung nach einem neuen regulären Druck, realer ACE-Trocknungsstart/-stopp mit passender Rückmeldung sowie aktuelle native Windows-x64-/Intel-Mac-Installation einschließlich LAN-Verbindung, Update und Wiederherstellung. Zusätzlich sind native Windows-ARM64- und Apple-Silicon-Pakete ausdrücklich angefordert und jeweils separat zu bauen und abzunehmen. Die erfolgreiche native Mac-Netzwerkdiagnose ist kein Nachweis, dass die korrigierte App beide Drucker dauerhaft verbindet.

Vor öffentlicher Freigabe weiterhin erforderlich: konkrete Releaseversion und Downloadumfang festlegen, dazu konsistente Dokumentation, Quell-/Binärmanifest, Fremdlizenzen und private-Daten-Prüfung; Signierung/Notarisierung der nativen Komplettinstaller und deren Plattformabnahme. Automatische Verbrauchsbuchung/Statistik und weitere NFC-Integration bleiben spätere Ausbauten, keine Voraussetzung einer klar begrenzten Alpha.

Diese Abschnitte sind historische Arbeitsstände. Der aktuelle Freigabestand steht in [RELEASE.md](RELEASE.md).


---

## Vor der Bereinigung vom 09.11.2026

# Checkliste vor der öffentlichen Alpha

Vorbereitung **0.40.0-alpha.1**, abgeglichen am08.11.2026. Der NAS-Stand0.38 ist installiert und geprüft;0.39 enthält getrennte native Testpakete; 0.40 ergänzt die begrenzte Datenübernahme. Eine Veröffentlichung wurde noch nicht vorgenommen. Frühere Checklisten stehen getrennt in [RELEASE_HISTORY.md](RELEASE_HISTORY.md).

## Bereits belegt

- [x] Linux/amd64-Bau mit jeweils482Python- und14Bridge-Prüfungen unter Python3.11 und3.14 sowie26JavaScript-Prüfdateien erfolgreich.
- [x] Gemeinsamer Monitor-/Spoolman-Test: Neuinstallation, Wiederanlauf mit Daten, geschützter Spoolman-Zugang und getrennte Wiederherstellung geprüft; ausschließlich simulierte Drucker.
- [x] NAS-Monitor und separater netzwerkloser Sicherungsdienst auf0.38; Vor-/Nachsicherung isoliert wiederhergestellt, vorhandene Konten, Zuordnungen, Berichte und Originaldateien erhalten.
- [x] Produktive Anmeldung, beide S1 mit aktuellen Daten, neue Hilfe und bytegleiche Programmdateien geprüft. Der Materialhinweis wurde zusätzlich mit ausreichend/Fehlmenge/leer/unbekannt im simulierten Desktop-/390px-Browser abgenommen.
- [x] Besitzer bestätigt Licht, Lüfter, Speed Mode, Temperaturen, Abbruch einschließlich Vorbereitung, X/Y/Z, Homing und Pause/Fortsetzen. Der Motor-Aus-Befehl beendete im gemeinsam beobachteten Fall den nach Homing laufenden Elektroniklüfter.
- [x] Ein Archivdruck auf dem2.Stock-S1 wurde vom Besitzer gestartet und als laufend bestätigt. Nach der Kennungskorrektur bleibt derselbe Auftrag mit Archivbezug stabil.

## Noch offene Abnahmen

- [x] Besitzer bestätigt am08.11.2026 erfolgreichen Abschluss und passendes Ergebnis des Archivwiederholungsdrucks. Quellauftrag und neue Aufzeichnung bleiben getrennt; die geprüften früheren Quellberichte wurden beim Update unverändert erhalten.
- [ ] Nach einem neuen regulären Druck die erste manuelle Achsenfahrt am Gerät erneut bestätigen; nachfolgende Schritte ohne erneute Nachfrage. Homing behält seinen eigenen Dialog.
- [ ] ACE-Trocknung ein-/ausschalten am passenden Gerät und die Rückmeldung ausdrücklich bestätigen. Ein Versandbeleg oder veränderte Sensortemperatur allein ist keine vollständige physische Abnahme.
- [ ] Native Pakete je Zielsystem praktisch prüfen: Neuinstallation, LAN-Verbindung, Update, Datensicherung/Wiederherstellung und Deinstallation mit Datenerhalt. Windowsx64 und Intel-Mac sind Teststände; WindowsARM64 benötigt noch eigene Quellbauten; AppleSilicon erhält einen eigenen0.39-Testbauweg, dessen konkrete Paketabnahme gesondert auszuweisen ist. [Plattformmatrix](PLATFORM_SUPPORT.md).

## Vor dem öffentlichen Release

- [ ] Konkrete Releaseversion und geprüften Downloadumfang festlegen. Nicht geprüfte Varianten ausdrücklich als Vorschau kennzeichnen oder noch nicht ausliefern.
- [ ] Den endgültigen Quellstand einfrieren, Dateimanifest prüfen und passende Images/Pakete daraus bauen. Die jetzige Dokumentbereinigung verändert den lokalen Quellstand; der installierte0.38-Bau bleibt als eigener unveränderter Nachweis erhalten.
- [ ] Quell-/Binärdateien einschließlich veröffentlichter Git-Historie auf private Daten, Schlüssel, Konten, Sicherungen, Druckoriginale und persönliche Screenshots prüfen. Automatische Dateiprüfung ersetzt keine vollständige Geheimnis-/Bildprüfung.
- [ ] Vollständige Fremdlizenzen und passende Quellzuordnung für die tatsächlich gebündelten Komponenten abschließen. Native Release-Signierung und Apple-Notarisierung einrichten; eine Ad-hoc-Signatur ist keine öffentliche Herausgebersignatur.
- [ ] README, Hilfe, Installation und bekannte Grenzen an genau diese Version und ihren Paketumfang binden. Komfortabler gemeinsamer Update-/Wiederherstellungsablauf und Plattformabnahme bleiben Teil der Komplettinstaller-Arbeit.
- [ ] Erst nach ausdrücklichem Veröffentlichungsauftrag GitHub-Release erstellen bzw. die Sichtbarkeit ändern.

Fehlt eine praktische Abnahme, bleibt sie offen. Eine begrenzte Alpha kann eine optionale Erprobungsfunktion gesperrt lassen; keine pauschale Hardware- oder Plattformfreigabe aus automatisierten Tests ableiten. Neue Druckerrechte oder echte Testbefehle gehören nicht zur Dokumentprüfung.

## Spätere Erweiterungen

Kontrollierte Verbrauchsbuchung, Statistik einschließlich leerer archivierter Spulen, zusätzliche NFC-Automatisierung und weitere Druckermodelle sind geplant. Sie sind keine Voraussetzung für eine klar begrenzte erste Alpha. Spoolman bleibt die Bestandsdatenbank; Stock-Drucker, ACE und Slicer benötigen keine Modifikation.

## Prüfweg für öffentliche Quellpakete

Im Quellverzeichnis prüft `python scripts/release_check.py` die von Git erfassten und noch nicht ignorierten neuen Dateien. Bei fehlendem Git-Nachweis wird abgebrochen, statt ungeprüft das Arbeitsverzeichnis einzupacken.

Vor Veröffentlichung des tatsächlich eingefrorenen Quellpakets zusätzlich:

```sh
python scripts/release_check.py --source-zip /pfad/Kobra-Monitor.zip --check-build
```

Dieser Prüfweg entpackt nichts. Er begrenzt Dateigröße und Anzahl, verwirft unsichere/mehrdeutige Pfade, Verknüpfungen, private Laufzeitdateien, Datenbank-Nebendateien, Originalmodelle, private Schlüsselblöcke und persönliche absolute Pfade. README-/UI-/Imageversionen müssen passen; `--check-build` verlangt ein vollständiges bytegleiches BUILD-Dateimanifest. Nach Quelländerungen schlägt die strenge Manifestprüfung bewusst fehl, bis ein neuer Stand eingefroren ist.

Das ist keine Authentizitätssignatur und kein Ersatz für vollständige Geheimnis-, Git-Historien-, Bild- oder Lizenzprüfung. Native Komplett-ZIPs mit Laufzeiten brauchen weiterhin ihre eigenen plattformspezifischen Binär-/Herkunftsprüfungen; dieser Modus prüft ausschließlich den öffentlichen Monitor-Quellbaum unter `Kobra-Monitor/`.

## Native Datenübernahme 0.40

Für gestoppte lokale Profile aus 0.34 und 0.39 ist eine ausdrücklich bestätigte Kopie mit Sicherungs-/Wiederherstellungsprüfung implementiert. Das ersetzt keine automatische Programmaktualisierung und keine Plattformabnahme. [Ablauf, Rückweg und Grenzen](NATIVE_UPGRADE.md).
