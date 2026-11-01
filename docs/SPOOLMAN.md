# Spoolman-Anbindung – erster Ausbau

Spoolman bleibt die zentrale Datenquelle. Projekt: https://github.com/Donkie/Spoolman, MIT-Lizenz. API: https://donkie.github.io/Spoolman/. Für die neue getrennte Installation ist Version 0.27.0 vorgesehen; keine unveränderliche `latest`-Annahme. Quellenstand am 31.10.2026 geprüft.

Im Monitor unter **Spulenverwaltung → Einrichten** die lokale Basisadresse ohne `/api` eintragen und **Speichern & prüfen** wählen. Die Adresse muss vom Monitor-Rechner/NAS aus erreichbar sein, nicht vom Handy. Unterstützt werden lokale IPv4-Adressen sowie der feste Docker-Dienstname `spoolman` im gemeinsamen Netz. Kein API-Schlüssel/Passwort in der URL. HTTPS wird normal geprüft; keine Zertifikatsausnahme.

**Spulen aktualisieren** liest ausschließlich `GET /api/v1/spool`, begrenzt auf 1000 aktive Spulen und 4 MiB. Keine Weiterleitungen, Cookies, Umgebungs-Proxys oder Übernahme beliebiger API-Pfade. Eine leere Liste ist ein gültiger leerer Bestand. Fehler behalten frühere Daten als veraltet; neue Zuordnungen benötigen eine erfolgreiche Abfrage der letzten 60 Sekunden.

Beim ausgewählten Drucker eine Spule für einen gemeldeten ACE-Slot auswählen und **Fest diesem Slot zuordnen**. Eine Spule kann nur einem Slot zugeordnet sein. Lösen einer Zuordnung bleibt bei ausgefallenem Spoolman und entfernten Druckern möglich. Vor einem Serverwechsel erst alle Zuordnungen lösen, damit gleiche numerische IDs verschiedener Server nicht verwechselt werden.

Der Monitor ändert weder Spoolman-Spulen noch Druckereinstellungen. Spulen anlegen, wiegen und pflegen erfolgt zunächst in Spoolman selbst. Nach expliziter Verknüpfung einer eindeutigen SKU kann der Monitor die Spule wiedererkennen. Keine Verbrauchsbuchung oder Übernahme aus 3D Filament Profiles. Spoolman-Restgewicht ist ein Buchbestand, keine Live-Waage. ACE-Prozentwerte bleiben getrennt.

## Installation und Sicherung

Spoolman als getrennten Dienst mit eigenem persistentem Volume installieren. Die offizielle Anwendung hat eine eigene Oberfläche; deren direkter Zugang braucht ein privates Netz/eine geeignete Zugangssicherung. Keine öffentliche Portweiterleitung einrichten. Monitor-HTTPS schützt ausschließlich die Monitor-Oberfläche, nicht automatisch einen separat veröffentlichten Spoolman-Port.

`spoolman.json` im Monitor-Datenvolume enthält Endpunkt, Slot-Verknüpfungen und bestätigte SKU-Verknüpfungen und wird privat in der Monitor-Vollsicherung wiederhergestellt. Das ersetzt **keine Sicherung der eigenen Spoolman-Datenbank**. Die getrennte NAS-Installation nutzt Spoolmans vorhandene nächtliche SQLite-Sicherung. Ein manueller Anfangsstand und anschließend ein nativer Sicherungsstand mit echtem Bestand wurden isoliert mit SQLite-Integritätsprüfung geöffnet. Beim echten Bestand wurden alle neun Tabellen, das Schema und die Datenbeziehungen gegen den nur lesend geöffneten Livebestand geprüft. Der erste nächtliche Zyklus bleibt separat zu prüfen; Sicherungen im Spoolman-Datenvolume ersetzen keine Kopie außerhalb des NAS. NFC-/RFID-Unterstützung in Spoolman 0.27 ist vorhanden; Kompatibilität mit ReSpool/Anycubic muss separat praktisch geprüft werden.

## Spulenkennung ab 0.18

Im ausgewählten ACE-Slot zeigt der Monitor die lokal gemeldete SKU. Für eine eindeutige Kennung (z. B. ReSpool) eine vorhandene Spoolman-Spule auswählen, die Bestätigung zur Eindeutigkeit setzen und **Kennung mit ausgewählter Spule verknüpfen** wählen. Eine normale Hersteller-SKU kann mehrere identische Spulen bezeichnen; sie ist kein Beweis für eine Einzelspule und keine Hardware-UID.

Die bestätigte Verbindung wird im Monitor gespeichert und mitgesichert. Nach Steckplatzwechsel zeigt **wiedererkannt** die passende Spoolman-Spule. Eine vorherige manuelle Zuordnung derselben Spule an diesem Slot wird dabei durch die bewegliche Kennungsverknüpfung ersetzt. Andere widersprüchliche manuelle Zuordnungen zuerst lösen. Mehrfach gemeldete Kennungen und Konflikte bleiben ohne Erkennung; offline, älter als 60 Sekunden, leerer Slot oder veralteter/fehlender Spoolman-Bestand ebenso. **Kennung lösen** funktioniert auch ohne Drucker oder Spoolman. Vor Serverwechsel auch gespeicherte Kennungen lösen.

Kein Beschreiben von NFC-Tags, keine Druckersteuerung und keine Spoolman-Bestandsänderung. SKU-Verknüpfungen sind noch keine Verbrauchsautomation oder Synchronisierung der ReSpool-Handybibliothek. Erst mit einer vorhandenen gekennzeichneten Spule praktisch prüfen; keine laufende Spule entnehmen.

## Spoolman öffnen

Nach der Anmeldung steht bei eingerichteter Verbindung direkt neben „Einrichten“ der Link „Spoolman öffnen“. Er öffnet die gespeicherte Adresse in einem neuen Tab. Auf dem Handy muss diese Adresse im Heimnetz oder über das eigene VPN erreichbar sein. Der Monitor richtet damit keine zusätzliche öffentliche Freigabe ein.

## Klare Unterscheidung ab 0.18.2

**Automatisch erkannt** zeigt bei aktuellen eindeutigen Daten die passende Spoolman-Spule direkt im Slot. Die Spule folgt ihrer Kennung; eine feste Slotbindung ist nicht nötig und wird auch serverseitig abgewiesen. In anderen Auswahllisten sind diese Spulen als „folgt ihrer Kennung“ markiert und nicht manuell wählbar.

**Keine feste Slot-Zuordnung** bezieht sich ausschließlich auf manuelle Bindungen. Ohne eindeutige Kennung bleibt die manuelle Zuordnung möglich; sie folgt einem physischen Spulenwechsel nicht. Alte widersprüchliche Bindungen lassen sich mit **Alte feste Zuordnung lösen** entfernen, ohne den gespeicherten Kennungslink zu verlieren. Eine Kennungsverknüpfung muss zuerst gelöst werden, bevor diese Spule wieder manuell fest zugeordnet werden kann. Keine automatische Konfliktbereinigung oder Änderung bestehender Bestände.

Ein realer Stock-S1/ACE-Test bestätigte am 01.11.2026 die vollständige selbst beschriebene ReSpool-Kennung und Wiedererkennung nach Slotwechsel. Beim ersten Wechsel musste eine alte manuelle Bindung gelöst werden; der anschließende Rückwechsel gelang ohne Zuordnungskorrektur. Dies ist kein Nachweis für jede Tag-/ACE-/Firmware-Kombination. Originale Hersteller-SKUs können produktgleich sein und bleiben manuell zuzuordnen.

## Nachweis der Spoolman-Sicherung am 01.11.2026

Die native Sicherungsfunktion erzeugte einen aktuellen Stand mit realen Spulen. Eine Kopie wurde in einem frischen temporären Verzeichnis geöffnet; alle neun Tabellen und das Schema stimmten mit dem laufenden, ausschließlich lesend geöffneten Bestand überein. SQLite-Integrität und Fremdschlüsselprüfung bestanden. Der bisherige ältere Sicherungsstand blieb erhalten. Kein produktiver Restore, keine Bestandsbuchung und keine Druckersteuerung.

Dies belegt die Sicherung und isolierte Wiederherstellbarkeit des aktuellen Bestands, nicht den nächtlichen Ablauf. Die native Mitternachtssicherung ist aktiviert; ein tatsächlich durchgelaufener Nachtzyklus bleibt separat zu belegen. Bei unveränderten Daten kann ein vorhandener Stand wiederverwendet werden. Ein älterer Dateizeitstempel allein belegt deshalb keinen Fehler. Eine zusätzliche private einmalige Kopie auf einem Mac wurde bytegleich und mit lokaler SQLite-/Fremdschlüsselprüfung bestätigt. Fortlaufende externe Kopien sind nicht eingerichtet.
