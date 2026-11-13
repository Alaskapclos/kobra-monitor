# ARM-Pakete: gebauter Stand und Grenzen

Stand 09.11.2026. **Windows ARM64 und macOS Apple Silicon 0.42 sind gebaut und nach Besitzerbericht funktionierend. Linux ARM64/Raspberry Pi ist ein anderes Ziel und noch nicht abgenommen.** [Plattformmatrix](PLATFORM_SUPPORT.md).

## Apple Silicon

Der Mac-Builder verwendet `--architecture arm64`. Monitor und Spoolman erhalten getrennte native Python-3.14.10-Laufzeiten mit vollständigen Abhängigkeiten: 24 Monitor- und 46 Spoolman-Pakete. Binärarchitektur, Bibliotheksabhängigkeiten und Wheel-Tags werden geprüft. Universal2-Dateien brauchen einen tatsächlich vorhandenen passenden Slice; ein ARM-Dateiname genügt nicht. Die Paket-Mindestversion wird mindestens an die höchste enthaltene Bibliotheksanforderung angepasst.

Die eigene Kameralaufzeit basiert auf FFmpeg 9.0.2, Quellcommit `946fcce07b6dcd0331c8cc609192aeff5e1924f8`. Der minimale Bau dient dem lokalen HTTP/FLV-zu-JPEG-Weg, ohne automatisch weitere Codec-Bibliotheken einzubeziehen. Quelle, Baukonfiguration, Lizenztexte und Prüfsummen gehören zum Paketnachweis. Die GitHub-Bestätigung des Quelltags ist keine unabhängige lokale PGP-Verifikation.

Das 0.42-App-Paket ist ad hoc signiert und bytegeprüft. Start/Stop, Datenübernahme, Sicherung und Wiederherstellung liefen nativ mit künstlichen Daten; der Besitzer bestätigt die App-Funktion. Developer-ID-Signierung, Notarisierung und vollständige öffentliche Lieferprüfung sind weitere Schritte. Intel unter Rosetta wird nicht als ARM-Nachweis ausgegeben.

## Windows ARM64

Python 3.14.10 kommt aus dem offiziellen ARM64-Einbettungspaket. Fehlende ARM-Wheels wurden in der Windows-ARM-Bauumgebung aus nachvollziehbaren Quellen gebaut: Cryptography-Versionen für beide Laufzeiten sowie asyncpg, httptools und psycopg2-binary samt benötigtem libpq. Anschließend wurden sie unter Windows ARM geladen; die vollständigen Abhängigkeitsmengen und Wheel-Dateikataloge sind geprüft. Keine Abhängigkeiten werden still ausgelassen und kein x64-Paket wird umbenannt.

Die ungenutzte AMD64-Kompatibilitätsdatei `vcruntime140_1.dll` aus dem offiziellen Python-ARM-Archiv wird ausschließlich anhand ihres festgelegten SHA-256-Werts ausgelassen. Alle aktiven ARM-Dateien werden auch auf normale und verzögerte PE-Importe dieser Datei geprüft. Inerte setuptools-Startvorlagen sind ausdrücklich von aktiven Laufzeitdateien getrennt; dies ist keine allgemeine Ausnahme für gemischte CPU-Pakete.

Das native 0.42-ZIP enthält ARM64-Laufzeiten, FFmpeg und einen passenden Datenbank-Konsolenstarter. Der Besitzer bestätigt Funktion und dauerhafte Steuerungsfreigaben nach Neustart in Windows ARM unter Parallels. Der paketinterne Prüfbericht stammt vom Bauzeitpunkt; spätere Besitzerabnahme ist separat dokumentiert. Eine allgemeine Freigabe aller Windows-ARM-Geräte, öffentlichen Signaturen oder vollständiger Einzelgeräte-Restorematrix folgt daraus nicht.

## Linux ARM64 / Raspberry Pi

Kein fertiges abgenommenes Paket. Ein offizielles ARM64-Abbild des verwendeten Spoolman 0.27.0 ist vorhanden; die eigene Linux-Monitor-/FFmpeg-Baukette und reale Leistung müssen gesondert geprüft werden. Geplantes erstes Ziel ist ein Pi 4 mit 4 GB und 64-Bit-Linux. Pi 3, ARM32 und eine feste Zahl gleichzeitig nutzbarer Kameras sind nicht freigegeben. Die Pi-Einrichtung ist auf Nutzerwunsch zurückgestellt.

## Quellen

- [Offizielles Python 3.14.10](https://www.python.org/downloads/release/python-31410/)
- [Python-Build-Standalone 20261026](https://github.com/astral-sh/python-build-standalone/releases/tag/20261026)
- [FFmpeg-Quellstand](https://github.com/FFmpeg/FFmpeg/tree/n9.0.2)
- Herkunft und Prüfsummen der konkreten Paketdateien stehen im zugehörigen Dateimanifest. Private Laufzeitdaten und persönliche Baupfade werden nicht veröffentlicht.
