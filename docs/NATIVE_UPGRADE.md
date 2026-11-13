# Aktueller Paketkandidat

Ziel ist 0.43.0-alpha.4. Zusätzlich zu 0.34/0.39/0.40/0.41 wird jetzt ein vollständig gestopptes 0.42-Profil unterstützt. Die tatsächliche Abnahme des neuen Gesamtpakets wird gesondert festgehalten.

# Übernahme lokaler Testdaten ab 0.40

Dieser begrenzte Weg gilt für die native Testinstallation mit enthaltenem lokalem Spoolman. Er wurde im Entwicklungsstand 0.40 eingeführt; 0.41 ergänzt die Übernahme aus 0.40, 0.42 aus 0.41. Bereits ausgegebene 0.39-ZIPs werden nicht nachträglich verändert. NAS-/Docker-Updates gehören nicht zu diesem Ablauf.

## Bedienung

Die alte Test-App zuerst vollständig beenden. Beim Öffnen der neuen Testfassung kann die Übernahme eines vorhandenen Standardprofils aus 0.34.0-alpha.1, 0.39.0-alpha.1, 0.40.0-alpha.1 0.41.0-alpha.1 oder 0.42.0-alpha.1 bestätigt werden. Der Dialog nennt Ausgangsversion, Zielversion, Quelle, neuen Datenordner und Sicherungsordner. Abbrechen verändert die Daten nicht.

Die neue App überschreibt weder das alte Programm noch dessen Datenordner. Mac-Programme erhalten einen versionsgebundenen Namen im eigenen Programme-Ordner; Windows verwendet bereits versionsgebundene Programmordner. Für spätere Starts wird ein schon erfolgreich übernommenes Standardprofil anhand seines Übernahmenachweises wiedergefunden. Beenden aus der neuen Fassung richtet sich an das neue Profil, nicht versehentlich an die alte Version.

Nach erfolgreicher Übernahme bitte nur noch die neue App verwenden. Die alte App würde weiterhin ihren eigenen alten Datenstand bearbeiten; beide Stände werden nicht automatisch zusammengeführt. Ein ausdrücklich abweichend gestartetes Profil, etwa `Daten-0.39-Neutest`, muss weiterhin mit demselben `--data`-Ausgangspunkt geöffnet werden. Eine allgemeine Profilauswahl ist damit nicht zugesagt.

Ein bereits früher aus „Daten“ in „Daten-0.40.0-alpha.1“ übernommenes Profil wird nicht automatisch als neuester Quellstand gesucht. Im Dialog Quelle und Version prüfen; die paketbegleitenden 0.40-Starter verwenden nur diesen ausdrücklich ausgewählten Standardordner. Für andere eigene Profile den bisherigen `--data`-Ausgangspunkt beibehalten.

## Sicherung und neue Datenkopie

1. Echte Datenpfade, bekannte Version, gestoppte Instanz und Speicherplatz prüfen. Verknüpfungen, Junctions, mehrfach verknüpfte Dateien, besondere Dateitypen und fremde Ziele sperren.
2. Die Dateien des alten Profils mit Prüfsummen erfassen und bytegleich in einen getrennten Arbeitsordner kopieren. Die Originaldatenbanken werden dabei nicht mit SQLite geöffnet oder verändert.
3. Vorhandene WAL-Daten ausschließlich in dieser Kopie zu konsistenten SQLite-Dateien zusammenführen. Konto, Druckereinrichtung, Spulenzuordnungen, Benachrichtigungsschlüssel, Archivdateien, Datenbankintegrität und Datenbeziehungen prüfen.
4. Die vollständige Sicherung in einen weiteren getrennten Ordner zurückkopieren und tatsächlich prüfen. Notwendige Verlaufs-Schemaanpassungen ausschließlich in dieser wiederhergestellten Kopie ausführen; alle zuvor vorhandenen Tabelleninhalte müssen erhalten bleiben.
5. Zuerst die geprüfte Sicherung veröffentlichen, danach den neuen Datenordner exklusiv und ohne Ersetzen eines vorhandenen Ziels veröffentlichen. Die Sicherung erneut anhand ihrer Prüfsummen und Datenbanken kontrollieren.

Die neue Kopie heißt beispielsweise `Daten-0.43.0-alpha.4`. Sicherungen bleiben neben der Quelle im Ordner `Daten-Uebernahmesicherungen`; ihr `backup-proof.json` dokumentiert Quell- und Sicherungsdateien. SQLite-Dateien der Sicherung enthalten auch die übernommenen bestätigten WAL-Transaktionen und können deshalb physisch von den ursprünglichen Datenbankdateien abweichen. Die Originaldateien bleiben erhalten. Sicherungen enthalten private Konten, Historien und Originaldateien und dürfen nicht veröffentlicht werden.

## Fehler und Rückweg

Ein abgelehnter oder fehlgeschlagener Lauf veröffentlicht keinen neuen Datenordner. Schlägt erst dessen Veröffentlichung fehl, bleibt die zuvor geprüfte Sicherung erhalten. Ältere Daten und Sicherungen werden nicht gelöscht oder überschrieben. Ein bereits existierendes fremdes Ziel wird auch dann nicht ersetzt, wenn es leer ist.

Zum Rückweg die neue App vollständig beenden und die alte App mit ihrem alten Datenordner verwenden. Nach der Übernahme in der neuen Version entstandene Änderungen sind dort nicht enthalten. Es gibt keine automatische Rücksynchronisierung.

## Grenzen

Nur die genannten Ausgangsversionen und das konkrete Ziel 0.43.0-alpha.4 sind vorgesehen. Fremde oder unvollständig eingerichtete Profile, ein externer Spoolman, unbekannte Versionen und nicht sauber beendete Instanzen bleiben gesperrt. Eine verwaiste Instanzdatei wird nicht eigenmächtig gelöscht. Für Sicherung und Arbeitskopien ist vorübergehend zusätzlicher Speicher erforderlich; es erfolgt keine automatische Bereinigung älterer Sicherungen.

Dies ist keine automatische Programmsuche, kein Downloader und kein vollständiger Update-/Deinstallationsassistent. Die vier 0.42-Desktop-Fassungen sind nach Besitzerbericht funktionierend. Die automatisierten Mac-Übernahme-/Restoretests und die Besitzerberichte sind getrennte Nachweise; keine vollständige Einzelgeräte-Restorematrix behaupten. Die Übernahmearbeit selbst startet keine Dienste und sendet keine Druckerbefehle. Erst der danach bewusst gestartete Monitor nimmt seine regulären Verbindungen auf.

## Windows-Sperrprüfung ab 0.43.0-alpha.4

Eine laufende alte Test-App wird mit einem verständlichen Hinweis zum Beenden abgewiesen. Die Prüfung liest nicht mehr das unter Windows gesperrte Byte. Der Installer beendet keine alte App automatisch. Echte fehlende Dateirechte werden weiterhin als eigener Fehler gemeldet. Ohne bestätigte Datenübernahme wird der Installationsvorgang abgebrochen.

Mehrere Versionsprofile bleiben getrennt. Prüfe Quelle und Version im Dialog; Steuerfreigaben werden aus genau diesem Profil übernommen, nicht aus einer anderen Installation ergänzt. Ein Datenbestand ohne Freigaben bleibt zunächst lesend.

Die frühere Windows-ARM-Funktionsbestätigung ist ein Besitzerbericht. Ein späterer Profilvergleich zeigte getrennte Datenstände aus 0.41 und 0.42; die damals tatsächlich geöffnete Version wurde nicht unabhängig protokolliert. Die Datenübernahme des neuen Pakets wird deshalb separat geprüft.
