# Lizenzen für die Auslieferung

## Quellpaket

Kobra Monitor steht unter GPL-3.0-only. Zum Quellpaket gehören auch die verwendeten Build- und Installationsskripte. Die Originaltexte und die dokumentierten Änderungen der eingebundenen Projekte bleiben erhalten. Die Projektlizenz, die Herkunftsnachweise und die Hinweise auf die Fremdsoftware liegen unter [LICENSE](../LICENSE), [SOURCES.json](../SOURCES.json) und [NOTICE.md](../NOTICE.md).

Ein Quellpaket enthält die Docker-Bauanleitung und die Abhängigkeitslisten. Python, Wheels, Spoolman und FFmpeg werden beim jeweiligen lokalen Installations- oder Buildvorgang aus ihren Bezugsquellen geladen. Die Veröffentlichung fertig gebauter Images oder Installer hat einen eigenen Lieferumfang.

## FFmpeg in künftigen Desktop-Installern

Die Kamera liest H.264 aus dem HTTP-FLV-Stream und liefert JPEG-Bilder. Das [Baurezept für die Kamera](../scripts/configure_camera_ffmpeg.sh) baut dafür FFmpeg mit dynamischen FFmpeg-Bibliotheken und deaktivierter Erkennung externer Bibliotheken. GPL-, Versions-3- und Nonfree-Optionen sind ausdrücklich deaktiviert. Die Kamera nutzt FFmpeg als separaten Prozess.

Für jeden fertigen Windows- oder Mac-Bau müssen das genaue FFmpeg-Quellarchiv, die Konfiguration, der verwendete Toolchain-Stand, etwaige Änderungen sowie der Auslieferungsbestand festgehalten werden. Das Quellarchiv und das Rezept gehören als Downloads zur selben Veröffentlichung. Im Installer und in der Programminformation werden FFmpeg, der mitgelieferte LGPL-Originaltext und der Zugang zu den passenden Quellen genannt. Die installierte Kamera muss sich auch mit einem kompatiblen selbst gebauten FFmpeg betreiben lassen. Dazu müssen Programmstart, Bibliothekspfade und Paketprüfung am endgültigen Paket geprüft werden. Die [FFmpeg-Hinweise zur Auslieferung](https://ffmpeg.org/legal.html) erläutern außerdem, warum H.264-Patentrechte gesondert zu betrachten sind.

Der bisherige Windows-Installer verwendet ein breiter konfiguriertes FFmpeg. Dessen Quellen- und Hinweissammlung bleibt der Nachweis für diesen Teststand. Das neue Rezept wurde für Apple Silicon, Intel-Mac, Windows x64 und Windows ARM64 gebaut. Die Mac-Komponenten wurden aus einem verschobenen Ordner mit künstlichem HTTP-FLV geprüft, Intel unter Rosetta. Die Windows-Bauten wurden auf Architektur und DLL-Importe geprüft. Die nativen Testpaketbauer können das Kameraarchiv über `--camera-input ZIP SHA256` übernehmen und legen Lizenztexte, Baunachweis und die lokale Streamprüfung dazu. Die Windows-Ausführung und der Austausch im endgültig signierten Installer bleiben eigene Abnahmeschritte.

## Python, Spoolman und Container

- **Python und Wheels.** Die jeweils ausgelieferten Originaltexte von Python, Laufzeitbibliotheken und Wheels bleiben im Paket. Bei mitgelieferten Laufzeitbibliotheken und selbst gebauten Wheels werden Version, Originalquelle und eigene Bauänderungen separat erfasst. Für die unter MPL 2.0 ausgelieferten Teile muss der Zugang zur entsprechenden Quellform in den Lieferhinweisen stehen. [Python-Lizenz und Fremdhinweise](https://docs.python.org/3/license.html) · [MPL 2.0, Abschnitt 3](https://www.mozilla.org/en-US/MPL/2.0/)
- **Spoolman.** Für native Pakete ist der genaue Spoolman-Release samt Original-Lizenztext zu übernehmen. Beide Oberflächen des Spoolman-Releases 0.27.0 wurden aus dem festgelegten Quellstand und den Lockdateien bytegleich nachgebaut. Zu den vier zuvor offenen Modulen liegen inzwischen die Originaltexte der Projekte vor. Der Modulabgleich dokumentiert die zeitliche Zuordnung zur eingebauten Version. Beim command-score stammt der Originaltext aus einem späteren Stand mit Codeänderungen. Die eingebundene Version war bei npm als MIT deklariert. Die Backend-Wheels, PostgreSQL-Bibliotheken und mitgelieferte Schriften gehören ebenfalls in das Inventar. [PostgreSQL-Lizenz](https://www.postgresql.org/about/licence/)
- **Docker.** Das Quellpaket kann den lokalen Build beschreiben. Für ein von uns bereitgestelltes Image wird der vollständige Bestand inventarisiert, einschließlich Basisabbild, Debian-Paketen und Python-Wheels. Bei Debian-Paketen werden die Originalhinweise und die genauen Quellpaketversionen erfasst. Verweise innerhalb der Debian-Lizenztexte auf gemeinsame Lizenzdateien müssen im Abbild auflösbar bleiben. [Debian Policy zu Copyright-Dateien](https://www.debian.org/doc/debian-policy/ch-docs.html#copyright-information)

Ein Binärdownload wird dem passenden Quellstand, den Originalhinweisen und dem geprüften Endbestand zugeordnet. Die Prüfsummen identifizieren die tatsächlich bereitgestellten Dateien. Die endgültigen Lizenzhinweise und Quellenzugänge werden vor Freigabe am Installer und an der Downloadseite gegengeprüft.

Der private Windows-Laufzeitteststand 0.43.0-alpha.6 verwendet das separat von Microsoft installierte Visual C++ Redistributable. Das Setup prüft Python und native Module vor der Installation.
