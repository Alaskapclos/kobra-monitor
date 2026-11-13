# Plattformen und Paketstand

Stand 09.11.2026. Quell-/Dokumentationskandidat **0.43.0-alpha.2**; vorhandene Desktop-Testpakete **0.42.0-alpha.1** und Docker-Testpaket **0.43.0-alpha.1** bleiben unverändert. Ein neues Quellpaket ist kein nachträglicher Prüfnachweis für bereits gebaute Binärdateien.

| Ziel | Gebaut und geprüft | Praktische Bestätigung / offene Grenzen |
| --- | --- | --- |
| Windows x64 | Vollständiges natives 0.42-ZIP, Python/Spoolman/FFmpeg; Manifest und Binärarchitektur geprüft | Besitzer bestätigt Funktion ohne Fehler, Testgerät Windows 10 x64. Kein separat protokollierter kompletter Update-/Restore-/Deinstallationstest auf diesem Rechner; öffentliche Signierung und Lieferprüfung offen. |
| Windows ARM64 | Natives 0.42-ZIP, vollständige Abhängigkeiten; fehlende ARM-Wheels aus Quelle gebaut und unter Windows ARM geladen; Architektur- und Importprüfung | Besitzer bestätigt Funktion einschließlich dauerhafter Steuerungsfreigaben nach Neustart in Windows ARM unter Parallels. Das ist native ARM-Ausführung, kein x64-Paket unter Emulation. Keine pauschale Freigabe aller Windows-ARM-Geräte oder Versionen. |
| macOS Intel / x86_64 | 0.42-App, Dateikatalog und Ad-hoc-Signatur geprüft; Integration 0.40→0.42 unter Rosetta mit isolierten Testdaten | Besitzer bestätigt Funktion auf dem Intel-iMac. Die Rosetta-Integration ist kein physischer Intel-Hardwaretest; der Besitzerbericht ist davon getrennt. Developer ID/Notarisierung und vollständige Lieferprüfung offen. |
| macOS Apple Silicon / ARM64 | Native 0.42-App; Integration, Übernahme, Start/Stop, Sicherung und Wiederherstellung auf ARM mit isolierten Testdaten | Besitzer bestätigt Funktion ohne Fehler. Keine pauschale Abnahme aller unterstützbaren macOS-Versionen; Developer ID/Notarisierung offen. |
| Linux / Server / NAS AMD64 | Docker-0.43-Testpaket: Python 3.11/3.14 jeweils 547 Tests, je 14 Bridge-Grenztests, 27 JS-Dateien; gemeinsamer Installer-/Neustart-/Paarrestoretest | Auf dedizierter Linux-VM mit künstlichen Daten geprüft. LAN-Modus mit leerer Druckerliste und getrennten Netzen geprüft; kein aktueller echter Drucker-/Kameratest dieser Suite. CLI für Docker Compose v2 erforderlich; allgemeiner NAS-GUI-Assistent und Versionsupdater offen. |
| Linux ARM64 / Raspberry Pi | Noch kein gebautes und abgenommenes Komplettpaket | Pi-Tests zurückgestellt. Vorgesehenes erstes Ziel Pi 4 mit 4 GB und 64-Bit-Linux; Hardwareleistung noch nicht gemessen. Pi 3 und ARM32 sind nicht freigegeben. Windows-/Mac-ARM-Nachweise gelten nicht für Linux. |

## Bedeutung der Nachweise

**Besitzer bestätigt** bedeutet eine tatsächliche Rückmeldung nach eigenen Tests, nicht einen vom Agenten beobachteten Volltest aller Funktionen. Am 09.11.2026 wurden die drei weiteren Desktop-Fassungen mit „laufen ohne Fehler“ bestätigt; Windows ARM war zuvor einschließlich des behobenen Freigabe-/Neustartproblems bestätigt. Kamera, Wiederherstellung und jede einzelne Steueraktion wurden dabei nicht auf jeder Plattform separat protokolliert.

Native Version 0.42 bündelt Laufzeiten und Spoolman. Die Kamera-Laufzeit ist enthalten; keine globale Python-/Homebrew-/Docker-Desktop-Installation erforderlich. Daten und Programme liegen getrennt. Konto und Drucker richtet der Anwender selbst ein, Steuerrechte bleiben zunächst gesperrt. NAS-Daten werden nicht automatisch importiert.

Die Manifest-Mindestversion des konkreten Pakets ist verbindlich; ein erfolgreicher Test auf einer Betriebssystemversion belegt nicht alle älteren Versionen. Windows 8/8.1 und 32-Bit-Systeme sind keine geplanten Ziele. Öffentliche Release-Signierung ist noch nicht eingerichtet; Ad-hoc-Signierung ist kein Herausgebernachweis.

[Installationswege](INSTALLERS.md) · [Prüfstand](VALIDATION.md) · [Freigabecheckliste](RELEASE.md).
