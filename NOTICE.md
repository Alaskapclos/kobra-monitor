# Copyright, Herkunft und Fremdsoftware

Kobra Monitor: Copyright (C) 2026 Kobra Monitor contributors. GPL-3.0-only.
Keine Garantie; vollständige Bedingungen in LICENSE. Eine Quellcodekopie mit
allen verwendeten Modifikationen gehört zu jeder Veröffentlichung.

Die Kernprotokolle werden aus bestehenden OSS-Projekten übernommen:

- kobra-bridge, GPL-3.0, siehe vendor/kobra-bridge/LICENSE und NOTICE.md.
- kobra-connect, Apache-2.0, siehe vendor/kobra-connect/LICENSE.

Die ursprünglichen Copyright-/Lizenztexte wurden beibehalten. Die enthaltene
upstream-NOTICE beschreibt auch historisches Material des ursprünglichen
Projekts; Anycubic-Slicer-Zertifikate und private Schlüssel sind hier NICHT enthalten.
Bibliotheken und ihre eigenen Lizenzen bleiben durch die Gesamtlizenz unberührt.
Weitere mitgelieferte Browserbibliotheken: siehe
vendor/kobra-bridge/THIRD_PARTY_LICENSES.md. Sie werden vom Monitor nicht geladen.

Im Quellpaket werden Python-Laufzeitabhängigkeiten nicht als Binärdateien mitgeliefert; die Starter installieren sie aus PyPI. Paketversionen stehen in requirements-lock.txt. Native Testpakete bündeln dagegen Laufzeiten und Bibliotheken mit eigenen Herkunfts-/Dateimanifesten. Ihre vollständige konkrete Lizenz-/Quellprüfung für eine öffentliche Binärauslieferung ist gesondert abzuschließen.

Das Docker-/NAS-Abbild installiert zusätzlich FFmpeg als eigenständiges Debian-Paket mit dessen LGPL-/GPL-Komponenten. Lizenztexte und Versionsinformationen bleiben im Abbild erhalten (`/usr/share/doc/ffmpeg/copyright`). Quellpakete: https://sources.debian.org/src/ffmpeg/ . Herkunft und Kamera-Anpassungen: docs/CAMERA.md und docs/UPSTREAM.md.

Optionale Web-Push-Laufzeit: pywebpush 2.5.0 und py-vapid 1.9.6 (MPL-2.0), http-ece 1.2.1 (MIT). Weitere neue Abhängigkeiten: requests (Apache-2.0), certifi (MPL-2.0), charset-normalizer, six und urllib3 (MIT). Unverändert aus PyPI installiert; Versionsbindung in requirements-lock.txt. Eigene Lizenztexte bleiben in den installierten Paketen erhalten.

PDF-Ausgabe: ReportLab 5.1.0 (BSD) und Pillow 13.0.0 (MIT-CMU), unverändert aus PyPI. Die mit ReportLab gelieferten Bitstream-Vera-Schriften werden für PDFs verwendet; zugehörige Lizenztexte verbleiben im installierten Paket. Keine externen Schrift-/Bildabrufe beim Export.

Ergänzte Original-Lizenzdatei für http-ece 1.2.1: `licenses/http-ece-1.2.1-MIT.txt`, aus dem unveränderten MIT-Text des ursprünglichen Projekts (Quellzuordnung in SOURCES.json). Die Bibliothek bleibt unverändert. Paket-Lieferprüfung und passende FFmpeg-/Drittquellen sind unter docs/RELEASE.md gesondert dokumentiert; vorhandene technische Testpakete werden dadurch nicht rückwirkend als öffentlich freigegeben erklärt.

Lizenz- und Quelllieferung für künftige Downloads sowie das Baurezept für die schlanke FFmpeg-Kamera sind unter [Lizenzen für die Auslieferung](docs/DISTRIBUTION_LICENSES.md) dokumentiert.
