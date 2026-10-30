# Fernzugriff

## Architektur

```text
Handy / Laptop → eigenes VPN → Rechner, NAS oder Server → Drucker im LAN
                              Kobra Monitor
```

Der Server braucht keine grafische Oberfläche. Die Browseroberfläche kann lokal
und von unterwegs genutzt werden. Nur der Server muss den Drucker erreichen.
Ein Browser-Tab allein zeichnet nichts auf: Dafür muss der Dienst laufen.

## Tailscale mit Serve

1. Tailscale auf dem Monitor-Host und dem Mobilgerät installieren und beide
   Geräte im eigenen Tailnet anmelden. Keine fremden Geräte unbeabsichtigt zulassen.
2. Monitor lokal starten; bei Docker das standardmäßige Loopback-Portmapping beibehalten.
3. Auf dem Host ausführen:

```sh
tailscale serve --bg http://127.0.0.1:7125
```

4. Die von Tailscale angezeigte HTTPS-Adresse auf dem Mobilgerät öffnen.
5. Den Zugangscode dieser Monitor-Installation eingeben. Bei Docker:

```sh
docker compose exec monitor python monitor.py --show-access-code
```

Die Tailscale-Einrichtung kann eine Freigabe für HTTPS/MagicDNS verlangen.
Serve ist für das Tailnet; **Funnel wird für dieses Projekt nicht verwendet**.
Tailscale-Gruppen/Geräteregeln bestimmen zusätzlich, wer den Host erreichen darf.
Reverse Proxies müssen den ursprünglichen Host-Header erhalten, damit die
Prüfung des Browser-Ursprungs bei Anmeldung und Einrichtung funktioniert.
Keine Tailscale-Zugangsschlüssel im Compose-Paket hinterlegen.

Die konkrete Kombination aus Host, Serve, HTTPS und Mobilgerät ist vor einem
Release praktisch zu prüfen. Wir ändern keine Tailscale-Einstellungen automatisch.

## Klassisches VPN (WireGuard, OpenVPN, Router-VPN)

Das VPN muss den Client zum Monitor-Host routen. Es muss nicht die Drucker direkt
für den Client erreichbar machen. DNS-Name bzw. private Hostadresse und Port
müssen über das VPN erreichbar sein.

Für eine native Installation kann an die private Hostadresse gebunden werden:

```sh
python monitor.py --listen 192.168.1.20
```

Die Beispieladresse durch die tatsächliche Serveradresse ersetzen. Für Docker:
`.env.example` als `.env` kopieren und `KOBRA_BIND_ADDRESS` auf diese private
Serveradresse setzen. Danach `docker compose up -d`. Die Docker-Standardbindung
bleibt ansonsten `127.0.0.1`.

Für mehrere Rechner im Heimnetz und Fernzugriff ist ein HTTPS-Reverse-Proxy
empfohlen, der an der gewünschten privaten bzw. VPN-Schnittstelle lauscht und
intern auf den Loopback-Monitor weiterleitet. Ein VPN zum Router verschlüsselt
nicht automatisch den weiteren HTTP-Weg zwischen Router und Server. HTTPS
schützt diesen Weg ebenfalls. Host-Header beibehalten. Die Anwendung unterstützt
keinen Betrieb unter einem URL-Unterpfad; eine eigene Hostadresse verwenden.

Firewall-Regeln auf dem Host und VPN-Zugriffsregeln auf das gewünschte Netz
beschränken. Keine öffentliche Router-Portweiterleitung einrichten. Der
Zugangscode ergänzt das VPN, ersetzt es aber nicht.

## Reichweite des Cloud-Ersatzes

Aktuell: Status, Temperaturen, ACE-Daten, Historie, Berichte und Verlauf.
Später separat zu entwerfen: Upload und Drucksteuerung, Berechtigungen,
Bestätigungen und Wiederholschutz. Die aktuelle Lesebeschränkung wird dafür
nicht stillschweigend aufgehoben. Kamera, Filamentbuchung und Benachrichtigungen
sind ebenfalls eigene spätere Funktionen.

## Primärquellen

- https://tailscale.com/docs/reference/tailscale-cli/serve
- https://tailscale.com/docs/features/tailscale-serve
- https://docs.docker.com/engine/network/port-publishing/

## Stand des Praxistests

Am 30.10.2026 bestätigte der Nutzer nach dem vorgesehenen Test über Mobilfunk
und seine bestehende Tailscale-Verbindung die erfolgreiche Anmeldung und Nutzung
der NAS-Oberfläche. Dabei wurde die vorhandene VPN-Konfiguration nicht verändert.
Dieser Test bestätigt nicht zusätzlich Tailscale Serve, HTTPS oder eine
Überprüfung der Tailnet-Zugriffsregeln; diese Punkte bleiben gesondert zu prüfen.
