# Erfolgreiche Archivdrucke wiederholen

**Installationsweg beachten:** Native 0.42-Pakete und die ausdrücklich gewählte LAN-Docker-Suite verwalten Freigaben unter **Einrichten → Steuerung freigeben**. Änderungen gelten nach vollständigem Monitor-Neustart, bei Docker nach Container-Neustart. Bis dahin gelten die alten Freigaben. Die folgenden Umgebungsvariablen betreffen den eigenen Quellstart beziehungsweise entsprechend verwaltete bisherige Container; native Pakete übernehmen keine beliebigen Steuerrechte aus der Umgebung. [Freigabeverwaltung](NATIVE_CONTROLS.md).

Stand **0.38.0-alpha.1**. Ein Archivstart am zweiten Stock-S1 und sein erfolgreicher Abschluss mit passendem Ergebnis sind vom Besitzer bestätigt (08.11.2026). Die zusätzliche Startfreigabe ist standardmäßig ausgeschaltet. Browserprüfungen mit simuliertem Drucker sind kein Nachweis eines erfolgreichen realen Uploads oder Starts.

Neue Modelle werden weiterhin in Orca oder Slicer Next geslicet und erstmals zum Drucker übertragen. Kobra Monitor bleibt die Zentrale für Beobachtung, Steuerung, Spulen, Berichte und Archiv. Nur das Wiederholen bereits erfolgreich abgeschlossener Aufträge übernimmt der Monitor direkt, ohne laufenden Slicer. Bei Betrieb auf dem NAS reicht dafür auch der Handy-Browser mit bestehendem lokalem oder VPN-Zugang.

## Ablauf

1. Unter **Druckaufträge** einen erfolgreich abgeschlossenen Auftrag mit zugeordnetem Original öffnen und **Druck wiederholen** wählen. Der gleiche Zugang steht bei einer Archivdatei zur Verfügung. **Letzten wiederholbaren Druck auswählen** sucht den jüngsten geeigneten Abschluss mit Original; ein jüngerer Auftrag ohne Original wird dabei übersprungen.
2. Einen freigegebenen Zieldrucker und für jedes tatsächlich verwendete Datei-Filament einen belegten ACE-Slot ausdrücklich auswählen. Es gibt keine automatische Übernahme der alten Slotnummern.
3. **Auswahl prüfen**, anschließend **Original zum Drucker übertragen** wählen. Die vollständige archivierte Originaldatei bleibt unverändert. Der Drucker erhält einen je Vorgang eindeutigen Dateinamen. Die Übertragung startet noch keinen Druck.
4. Danach freies und vorbereitetes Druckbett, passendes Material in den gewählten Slots und den zur Datei passenden eingebauten Düsendurchmesser bestätigen. Gespeicherte Slicer-Warnungen werden angezeigt. Die geslicten Einstellungen werden nicht neu berechnet oder auf anderes Material umgestellt.
5. **Druck jetzt starten** sendet genau einen Start mit Bettnivellierung. Erst der passende neu beobachtete Auftrag bestätigt den Beginn. Ein bloßes Befehls-ACK oder eine erfolgreiche Dateiübertragung genügt nicht.

Schließen des Browserbereichs beendet keinen Druck. Der Server beobachtet eine bereits gesendete Startanforderung weiter, auch wenn der Handy-Tab geschlossen wird. Beim Neuladen kann dieselbe Anmeldung den Vorgangsbeleg wieder anzeigen; es wird dadurch weder übertragen noch gestartet. **Vorbereitung verwerfen** verwirft nur noch nicht gesendete nächste Schritte; eine bereits gespeicherte Datei bleibt auf dem Drucker. Ein laufender Druck wird über seine separate Abbruchsteuerung bedient.

## Frische, Verbindung und Bestätigungen

### Materialvorrat vor der Wiederholung

Nach der ausdrücklichen Slot-Auswahl zeigt der Monitor den geschätzten Materialbedarf der Datei neben dem gebuchten Restgewicht der eindeutig zugeordneten Spoolman-Spule. Eine Fehlmenge wird in Gramm genannt. Nutzen mehrere Datei-Filamente dieselbe Spule, werden ihre Bedarfe zusammengezählt; der Vorrat wird nur einmal gezählt. Eine leere Spule mit 0 g bleibt eine leere Spule.

Fehlen eine eindeutige Zuordnung, ein belastbarer Slicerbedarf oder aktuelle Drucker-/Spoolman-Daten, steht dort **nicht beurteilbar**. Ein zwischenzeitlicher erkennbarer Slotwechsel macht die Anzeige ebenfalls ungültig. Der Hinweis ist eine Entscheidungshilfe und keine Startsperre oder Garantie: Slicer-Schätzung und Buchbestand sind keine Verbrauchsmessung. Materialeignung, tatsächliche Spule und Druckeinrichtung bleiben vor dem Start zu prüfen. Der Hinweis schreibt weder Bestände noch Druckerdaten und benötigt keine zusätzliche Software oder modifizierte Firmware.

Vor Übertragung und Start sind eindeutiger Leerlauf sowie höchstens 15 Sekunden alte Drucker-/ACE-Daten derselben Verbindung erforderlich. Material-, Belegungs- oder Verbindungswechsel machen die Vorbereitung ungültig, auch wenn eine gemeldete Änderung danach zurückgetauscht wird. Bei gleichen produktgleichen Original-SKUs ist ein physischer Spulentausch nicht immer aus den LAN-Daten erkennbar; die tatsächliche Spule und Materialeignung müssen deshalb vom Benutzer geprüft werden. Spoolman-Bestände werden nicht automatisch verbraucht oder verändert.

Dateiprüfung und Übertragung sind an Originalprüfsumme, Quelle, Ziel, Filamentauswahl und Anmeldung gebunden. Übertragungs- und Startbestätigung verwenden verschiedene einmalige Tokens. Die Übertragungsbestätigung gilt 30 Sekunden; nach bestätigter Speicherung stehen fünf Minuten für die separate Startbestätigung zur Verfügung. Danach neu vorbereiten. Neue Starts können nur erfolgreich abgeschlossene Monitoraufträge mit dem genau zugeordneten Archivoriginal wiederholen; Dateiname allein genügt nicht.

Die Übertragung läuft begrenzt als einzelner Stream direkt zum konfigurierten Drucker. Keine Weiterleitungen, Umgebungs-Proxys oder beliebigen Ziel-URLs; keine neue Dateifreigabe im Netzwerk. Der allgemeine Bridge-Leseschutz bleibt aktiv. Für den engen Startweg gelten Modell-, Verbindungs-, Zustands- und Zeitprüfungen unmittelbar vor dem einmaligen Socket-Schreibaufruf. Bestehende Steuerungen teilen sich die Reservierung; ein ausdrücklich angeforderter Druckabbruch bleibt möglich. Auch nach einem Neustart gibt es keinen automatischen erneuten Upload oder Start.

Bei Fehler oder Zeitüberschreitung bleibt ein möglicherweise gesendeter Schritt **unbestätigt**. Den Druckerstatus prüfen. Das Programm wiederholt keine solche Aktion automatisch. Ein erfolgreicher Upload belegt die Speicherbestätigung des Druckers, keine unabhängig ausgelesene Inhaltsprüfsumme seiner gespeicherten Datei.

## Historie und Berichte

Ein bestätigter Start erzeugt durch die normale Beobachtung einen neuen Auftrag. Der neue Auftrag erhält das Archivoriginal automatisch, einschließlich Bezug zum erfolgreichen Quellauftrag und ursprünglichem Dateinamen. Der alte Auftrag, dessen manuelle Angaben und bereits archivierte Berichtsversionen bleiben unverändert. Neue Berichte unterscheiden die bestätigte Archivwiederholung von einer manuellen Dateizuordnung; fehlende unabhängige Remote-Inhaltsprüfung bleibt ausdrücklich benannt.

## Erste unterstützte Konfiguration

Stock **Kobra S1, Modell 20025**, ein direkt angeschlossener Vier-Slot-ACE mit Box-ID 0, eine geslicte Druckplatte im geprüften Anycubic-Paketformat, 250×250×250-mm-Profil und 1,75-mm-Filament. Dateivorprüfung: höchstens 32 MiB G-Code, 64 KiB je Zeile und 1 MiB pro Metadatenquelle. Mehrplatten, übersprungene Objekte, widersprüchliche Material-/Werkzeugangaben und unbekannte Topologien sind gesperrt. PLA/PLA+ werden als eine Materialfamilie behandelt; dies ersetzt keine Prüfung der Eignung des konkreten gespeicherten Profils. Eine bestandene Dateivorprüfung zertifiziert beliebigen G-Code nicht als gefahrlos.

Der Originalpaket-Upload und anschließende lokale `.gcode.3mf`-Start auf Stock-S1 bleiben trotz erster erfolgreicher Besitzerabnahme ein begrenzter **Erprobungsweg**. Andere Modelle, ACE-Hubs, externe Spulen und beliebige Orca-Exportvarianten sind nicht praktisch freigegeben. Bestehende erfolgreiche Slicer-Drucke und synthetische Paketprüfungen ersetzen diesen separaten Realtest nicht.

## Gesonderte Einrichtung

Administratoren setzen ausschließlich die gewünschten bereits eingerichteten S1-Adressen in `KOBRA_ARCHIVE_START_IPS`. Leer bedeutet: keine Übertragung oder Startfreigabe. Die Variable ist von den Freigaben für Pause/Fortsetzen/Abbruch und Achsen getrennt. Die Compose-Vorlagen reichen sie standardmäßig leer weiter. Zur kontrollierten Realgeräteabnahme erst nach Paket- und Sicherungsprüfung gezielt für den Testdrucker aktivieren; reguläre Nutzung erst nach erfolgreicher Abnahme. Keine Drucker werden durch eine Aktualisierung automatisch zusätzlich freigegeben.

## Protokollreferenzen

Die begrenzten eigenen Implementierungen orientieren sich an den bereits gebündelten, GPL-lizenzierten Bibliothekswegen: `kobrax_client.py:upload_gcode`, `kobrax_moonraker_bridge.py:handle_kx_printer_file_start`, `mapping_for`/ACE-Zuordnungslogik und an den beobachteten S1-Statusdaten. Der bisherige allgemeine Store-Start der Bridge nutzt eine separate Datei-URL und ist nicht unverändert übernommen. Ein direkter Originalpaket-Start und erfolgreicher Abschluss wurden inzwischen am zweiten Stock-S1 vom Besitzer bestätigt. Das ist kein pauschaler Nachweis anderer Modelle, ACE-Topologien oder Slicerformate.

## S1-Auftragskennung (Korrektur 0.37)

Beim ersten realen Archivdruck beobachtet: info meldet für eine zu große Kennung den maximalen 32-Bit-Wert, print dagegen die vollständige Kennung. 0.36 konnte dadurch denselben Druck in mehrere Historieneinträge teilen. Neue Starts nutzen positive Kennungen unter dieser Grenze. Für bereits bestätigte alte Monitorstarts gilt eine eng begrenzte Normalisierung anhand gespeicherten Versandbelegs, Drucker und exakt passendem Monitor-Dateinamen. Allgemein unterschiedliche Aufträge werden weiterhin getrennt. Bestehende Fragmente und Berichte werden nicht gelöscht oder rückwirkend als vollständiger Ablauf ausgegeben. Ein laufender passender Folgeabschnitt erhält denselben belegten Archivbezug. Kein erneuter Druckstart und keine automatische Wiederholung.
