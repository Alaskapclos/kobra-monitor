# Update und Rückkehr zum bisherigen Stand

Ein Update unterbricht die Aufzeichnung kurz. Plane es nach einem Druck ein,
wenn du dessen Beginn und Ende möglichst lückenlos dokumentieren möchtest.
Diese Anleitung führt selbst keine Änderung aus.

## Vorbereiten

1. Installierte Version und Betriebsart festhalten: Rechner oder Container/NAS.
2. Den zuletzt geprüften Sicherungsstand und das dazu passende bisherige
   Programm bzw. Container-Image aufbewahren. Das Monitor-Archiv nennt sein
   passendes Image im Manifest als `restore_image`.
3. Die vollständige Monitor-Sicherung in einen **neuen, getrennten Ordner**
   probeweise wiederherstellen und prüfen. Die vorhandene Installation bleibt
   dabei unverändert. Eine Spoolman-Sicherung separat aufbewahren.
4. Die verwendeten Datenordner bzw. Volumes, Projektname und private
   Zugangsadresse notieren. Diese Angaben und die Sicherung bleiben privat.

Die Quellcode-ZIP enthält keine Benutzerdaten und ersetzt keine Datensicherung.
Sie enthält auch kein fertig importierbares NAS-Image. Für UGOS ist zusätzlich
ein zur Version und Prozessorarchitektur passendes Image erforderlich.

## Native Komplettpakete

Für die nativen 0.42-Testpakete zuerst [NATIVE_UPGRADE.md](NATIVE_UPGRADE.md) lesen: nur bekannte vollständig gestoppte Profile, ausdrückliche Bestätigung, Sicherung und isolierte Wiederherstellung, danach eine getrennte Datenkopie. Ein zuvor separat übernommenes Profil wird nicht automatisch als neuester Stand gesucht. Die folgende allgemeine Quell-/Containeranleitung darf diesen Weg nicht durch ungeprüftes Wiederverwenden einer anderen Datenversion ersetzen.

## Quellstart und bisherige Container-Projekte aktualisieren

- **Eigener Python-Quellstart:** Monitor beenden, neue Programmdateien in einem getrennten
  Programmordner bereitstellen und den bisherigen Datenordner ausdrücklich
  weiterverwenden. Die neue Version mit dem passenden Starter starten.
  Ein leerer neuer Datenordner würde wie eine neue Installation aussehen.
- **Container/NAS:** Vorhandenes Projekt mit neuer Programmversion bzw. neuem
  Image aktualisieren. Dasselbe Datenvolume und dieselbe Port-/VPN-Konfiguration
  beibehalten. Ein anderes Projekt kann ein neues, leeres Volume erzeugen.
- Den getrennten Sicherungsdienst auf das passende Image abstimmen; sein
  vorhandenes Sicherungsvolume erhalten. Den Sicherungsrhythmus nicht
  versehentlich durch ein zweites Projekt duplizieren.

Keine Volumes löschen. Insbesondere `docker compose down -v` entfernt Daten.
Kein zweites Monitor-Exemplar gleichzeitig mit demselben Datenordner starten.
Installationsdetails: [Rechner/Docker](INSTALLATION.md), [UGOS](UGREEN_UGOS.md).

## Danach kontrollieren

Mit dem bisherigen Konto anmelden. Beide bzw. alle eingerichteten Drucker,
ihre Reihenfolge und den vorhandenen Verlauf prüfen. Bei frischen Daten
Temperaturen, Kamera und gespeicherte Spulenzuordnungen kontrollieren.
Die gespeicherten Benachrichtigungsgeräte prüfen; eine Testmeldung bei Bedarf
selbst auslösen. Die neue Sicherung erneut getrennt wiederherstellen und auf
Integrität und erhaltene Daten prüfen. Eine kurze Aufzeichnungslücke dokumentieren.

Erscheint unerwartet die Ersteinrichtung, zuerst den Datenpfad bzw. das Volume
prüfen. Kein neues Konto anlegen und die vermeintlich fehlenden Daten nicht
überschreiben.

## Wenn die neue Version nicht funktioniert

Neue Instanz anhalten und ihre Daten für die Diagnose erhalten. Die bisherige
Programmversion bzw. das gesicherte Image mit einer **getrennten Kopie** des
dazu passenden geprüften Datenstands starten. Neuere Daten können ein anderes
Schema verwenden; nicht ungeprüft ein altes Programm darauf loslassen.

Erst nach erfolgreicher Kontrolle wieder auf die private produktive Adresse
umschalten. Niemals gleichzeitig auf dasselbe Datenvolume schreiben lassen.
Eine Rückkehr auf einen älteren Datenstand verliert spätere Aufzeichnungen
und Änderungen; den Unterschied vorher prüfen und benennen. Spoolman bleibt
ein eigenständiger Dienst und wird bei einem Monitor-Update nicht zurückgesetzt.

Einsteigerhilfe: [Bedienung](BEDIENUNG.md). Details zu geprüften Archiven und
isolierter Wiederherstellung: [Sicherung](BACKUPS.md).

## Gemeinsame Docker-Testinstallation

Der Suite-Installer `start` verwendet dieselbe gespeicherte Version und Konfiguration; er ist kein Versionsupdate. Andere Versionen oder geänderte Dienstdefinitionen werden abgewiesen. Ein automatischer Suite-Update-/Restoreassistent und die Übernahme vorhandener produktiver NAS-Projekte sind noch nicht fertig.
