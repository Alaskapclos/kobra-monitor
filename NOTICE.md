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

Die Python-Laufzeitabhängigkeiten werden aus PyPI installiert und nicht als
Binärpakete mitgeliefert. Paketversionen stehen in requirements-lock.txt.

Das Docker-/NAS-Abbild installiert zusätzlich FFmpeg als eigenständiges Debian-Paket mit dessen LGPL-/GPL-Komponenten. Lizenztexte und Versionsinformationen bleiben im Abbild erhalten (`/usr/share/doc/ffmpeg/copyright`). Quellpakete: https://sources.debian.org/src/ffmpeg/ . Herkunft und Kamera-Anpassungen: docs/CAMERA.md und docs/UPSTREAM.md.
