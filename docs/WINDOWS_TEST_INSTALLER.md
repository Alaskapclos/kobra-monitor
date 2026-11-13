# Windows-Testinstallation

Neuer Paketkandidat: **0.43.0-alpha.4**, Gesamtprüfung je Lieferdatei gesondert nachgewiesen; neue Windows-Ausführung noch offen. Die folgenden bisherigen Nutzerabnahmen gelten weiterhin für 0.42.

Zielplattformen der neuen Fassung: **Windows 10 22H2 oder neuer auf x64**, **Windows 11 auf ARM64**. Die konkrete Buildnummer des bisherigen Windows-10-Testrechners ist nicht protokolliert; daraus wird kein Test einer bestimmten Unterversion abgeleitet.

Stand 09.11.2026: **0.42.0-alpha.1**, getrennte Pakete für **x64** und **ARM64**. Beide sind gebaut; der Besitzer bestätigt ihre Funktion. Windows x64 wurde auf Windows 10 x64 getestet, Windows ARM auf einer ARM-Installation in Parallels. Das ist keine allgemeine Abnahme aller Windows-Versionen oder ein vollständiger Restore-/Deinstallationstest auf jedem Gerät. [Prüfstand](VALIDATION.md).

## Installieren

1. Architektur passend zum Windows-System wählen. ARM64 ist nicht x64, auch wenn Windows x64-Anwendungen übersetzen kann.
2. ZIP vollständig in einen lokalen Ordner entpacken. Nicht direkt im ZIP oder in einem entfernten Freigabeordner starten.
3. **Pruefen.cmd** im enthaltenen Programmordner ausführen. Die Paket-, Import- und Kameralaufzeitprüfung sendet keine Druckerbefehle und verbindet keine echte Druckerdatenbank.
4. **Installieren.cmd** öffnen. Programm- und Datenordner unter `%LOCALAPPDATA%/KobraMonitor-Test` kontrollieren. Der Installer legt Starter für Öffnen und vollständiges Beenden an.
5. Eigenes Konto im Browser anlegen und Drucker unter **Einrichten** hinzufügen. Vorhandene NAS-Daten werden nicht übernommen.

Python, die festgelegten Bibliotheken, originaler Spoolman 0.27.0 einschließlich Oberfläche und FFmpeg sind enthalten. Keine eigene Python-/Docker-Desktop-Installation nötig. Microsofts C++-Laufzeit wird per Importtest geprüft. Falls sie fehlt, bietet der Assistent nach Zustimmung den originalen Microsoft-Installer für die **passende Architektur** an. Vor dem Öffnen muss Windows dessen gültige Microsoft-Signatur bestätigen; Microsoft zeigt seine eigenen Lizenzbedingungen. Dafür können Internetzugang und Administratorrechte nötig sein. Kein automatischer Windows-Neustart. Der Microsoft-Installer ist nicht im Test-ZIP enthalten; eine frische Installation ist daher nicht immer vollständig offline möglich.

## Verwenden und beenden

Oberfläche und interne Dienste lauschen nur auf localhost. Spoolman ist zusätzlich durch einen eigenen zufälligen internen Zugang geschützt; Browserzugriffe laufen über den angemeldeten Monitor. Ein zweiter Start öffnet die vorhandene Anwendung. Nur den Browser zu schließen beendet die Aufzeichnung nicht. Der Beenden-Starter beendet ausschließlich die zu dieser Installation gehörenden Prozesse.

Neue Installationen beginnen lesend. Unter **Einrichten → Steuerung freigeben** einzelne Funktionen je Drucker bewusst bestätigen. Danach die ganze Anwendung beenden und erneut starten; Browser-Neuladen genügt nicht. Bis dahin gelten die bisherigen Freigaben, auch bei einem Entzug. [Freigaben](NATIVE_CONTROLS.md).

## Vorhandene Daten, Sicherung und Grenzen

Die ausdrücklich bestätigte Übernahme bekannter gestoppter Testprofile in 0.42 kopiert Daten nach Sicherungs-/Wiederherstellungsprüfung in einen neuen Ordner. Quelle und Version prüfen, besonders bei bereits separat übernommenen 0.40-Profilen. Es gibt keinen allgemeinen automatischen Versionsupdater oder eine automatische Suche nach dem neuesten Profil. [Datenübernahme](NATIVE_UPGRADE.md).

Nach der Einrichtung erstellt der lokale Prozess eine gemeinsame Monitor-/Spoolman-Sicherung mit isolierter Prüfung beider Datenbanken und wiederholt sie nach 24 Stunden. Es gibt keine gemeinsame atomare Transaktion beider Dienste. Sicherungen bleiben lokal; ein allgemeiner Wiederherstellungsdialog und begrenzte Aufbewahrung sind noch offen. Ein externer Spoolman-Bestand benötigt seine eigene Sicherung.

SHA-256-Katalog und Architekturprüfung sind Integritätsnachweise, keine Herausgebersignatur. Öffentliche Signierung und vollständiger Binärliefer-/Quellnachweis sind separat zu erledigen. Fehlerprotokolle können persönliche Pfade enthalten und müssen vor öffentlicher Weitergabe geprüft werden. Persönliche Daten bei einem Programmwechsel oder Entfernen niemals ungeprüft löschen.

## Windows-Sperrprüfung ab 0.43.0-alpha.4

Eine laufende alte Test-App wird mit einem verständlichen Hinweis zum Beenden abgewiesen. Die Prüfung liest nicht mehr das unter Windows gesperrte Byte. Der Installer beendet keine alte App automatisch. Echte fehlende Dateirechte werden weiterhin als eigener Fehler gemeldet. Ohne bestätigte Datenübernahme wird der Installationsvorgang abgebrochen.

Mehrere Versionsprofile bleiben getrennt. Prüfe Quelle und Version im Dialog; Steuerfreigaben werden aus genau diesem Profil übernommen, nicht aus einer anderen Installation ergänzt. Ein Datenbestand ohne Freigaben bleibt zunächst lesend.

Die frühere Windows-ARM-Funktionsbestätigung ist ein Besitzerbericht. Ein späterer Profilvergleich zeigte getrennte Datenstände aus 0.41 und 0.42; die damals tatsächlich geöffnete Version wurde nicht unabhängig protokolliert. Die Datenübernahme des neuen Pakets wird deshalb separat geprüft.
