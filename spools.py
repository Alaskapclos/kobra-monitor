# SPDX-License-Identifier: GPL-3.0-only
"""Optional Spoolman inventory reader. Only local mapping writes; never printer I/O."""
import asyncio
import ipaddress
import json
import math
import os
import re
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit
import aiohttp
from configuration import NETWORKS

LIMIT = 1000
MAX_BYTES = 4 * 1024 * 1024


def spool_sku(value):
    """Exact logical identity, never a hardware UID or a product-name guess."""
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}', value) else None


def local_url(value):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError('Bitte die lokale Spoolman-Adresse eintragen.')
    value = value.strip().rstrip('/')
    if not value:
        return ''
    try:
        u = urlsplit(value)
        if u.scheme not in ('http', 'https') or u.username or u.password or u.query or u.fragment or u.path:
            raise ValueError()
        if not u.hostname or not 1 <= (u.port or (443 if u.scheme == 'https' else 80)) <= 65535:
            raise ValueError()
        if u.hostname != 'spoolman':
            ip = ipaddress.ip_address(u.hostname)
            if ip.version != 4 or not (ip.is_loopback or any(ip in net for net in NETWORKS)):
                raise ValueError()
        return value
    except ValueError:
        raise ValueError('Lokale Adresse ohne Pfad oder Zugangsdaten verwenden, z. B. http://192.168.1.20:7912. Im gemeinsamen Docker-Netz ist http://spoolman:8000 möglich.') from None


def weight(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def normalize(items):
    if not isinstance(items, list) or len(items) > LIMIT:
        raise ValueError('Ungültige Spulenliste.')
    result = []
    seen = set()
    for item in items:
        if not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] <= 0 or item['id'] in seen:
            raise ValueError('Ungültige Spulenkennung.')
        seen.add(item['id'])
        if item.get('archived') is True:
            continue
        filament = item.get('filament', {})
        if filament is None:filament = {}
        if not isinstance(filament, dict):
            raise ValueError('Ungültige Materialdaten.')
        vendor = filament.get('vendor') or {}
        def text(v): return v[:100] if isinstance(v, str) else ''
        result.append({'id': item['id'], 'name': text(filament.get('name')), 'material': text(filament.get('material')),
                       'vendor': text(vendor.get('name')) if isinstance(vendor, dict) else '',
                       'remaining_weight': weight(item.get('remaining_weight')), 'location': text(item.get('location'))})
    return result


class Spools:
    def __init__(self, directory, clock=time.time):
        self.path = Path(directory) / 'spoolman.json'
        self.clock = clock
        self.lock = asyncio.Lock()
        self.url = ''
        self.mappings = {}
        self.sku_links = {}
        self.items = None
        self.checked = None
        self.error = ''
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.url = local_url(data['url'])
            self.mappings = self.validate_mappings(data.get('mappings', {}))
            self.sku_links = self.validate_sku_links(data.get('sku_links', {}))

    @staticmethod
    def validate_sku_links(links):
        if not isinstance(links, dict) or len(links) > LIMIT:
            raise ValueError('Ungültige Spulenkennungen.')
        if any(spool_sku(sku) is None or type(spool) is not int or spool <= 0 for sku, spool in links.items()):
            raise ValueError('Ungültige Spulenkennung oder Spule.')
        if len(set(links.values())) != len(links):
            raise ValueError('Diese Spule hat bereits eine andere Kennung. Zuerst die alte Verknüpfung lösen.')
        return dict(links)

    def detections(self, printers):
        rows = []
        for printer in printers:
            age = printer.get('section_age_s', {}).get('ace')
            fresh = (printer.get('connection') == 'online' and type(age) in (int, float)
                     and math.isfinite(age) and 0 <= age <= 60)
            for slot in (printer.get('data') or {}).get('ace_slots', []):
                index = slot.get('global_index', slot.get('index'))
                if type(index) is not int or not 0 <= index < 16:
                    continue
                sku = spool_sku(slot.get('sku'))
                empty = slot.get('edit_status') == 2
                rows.append({'ip': printer['ip'], 'slot': index, 'sku': sku,
                             'status': 'stale' if not fresh else ('empty' if empty else ('unknown' if sku else 'no_sku')),
                             'spool_id': None})
        ids = {v['id'] for v in self.items or []}
        for row in rows:
            if row['status'] != 'unknown':
                continue
            sku = row['sku']
            # Include other live occurrences before resolving either one.
            if sum(other['sku'] == sku and other['status'] not in ('stale', 'empty', 'no_sku') for other in rows) > 1:
                row['status'] = 'duplicate'
            elif sku in self.sku_links:
                spool = self.sku_links[sku]
                manual = self.mappings.get(row['ip'], {}).get(str(row['slot']))
                elsewhere = any(value == spool and (ip != row['ip'] or key != str(row['slot']))
                                for ip, slots in self.mappings.items() for key, value in slots.items())
                if manual not in (None, spool) or elsewhere:
                    row['status'] = 'conflict'
                elif not self.state()['inventory_current'] or spool not in ids:
                    row['status'] = 'inventory_unavailable'
                else:
                    row.update(status='recognized', spool_id=spool)
        return rows

    async def link_sku(self, sku, spool, printers, target=None):
        async with self.lock:
            if spool_sku(sku) is None:
                raise ValueError('Ungültige Spulenkennung.')
            candidate = dict(self.sku_links)
            if spool is None:
                candidate.pop(sku, None)
            else:
                rows = [row for row in self.detections(printers) if row['sku'] == sku and row['status'] not in ('stale', 'empty')]
                if len(rows) != 1 or rows[0]['status'] not in ('unknown', 'recognized'):
                    raise ValueError('Kennung nicht frisch und eindeutig erkannt. Druckerdaten aktualisieren und Konflikte lösen.')
                if target is not None and (rows[0]['ip'], rows[0]['slot']) != target:
                    raise ValueError('Die Spule wurde inzwischen gewechselt. Bitte die Anzeige aktualisieren.')
                if not self.state()['inventory_current'] or type(spool) is not int or spool not in {v['id'] for v in self.items or []}:
                    raise ValueError('Spulen zuerst aktualisieren und eine vorhandene Spule auswählen.')
                if sku in candidate and candidate[sku] != spool:
                    raise ValueError('Kennung ist schon verknüpft. Zuerst die alte Verknüpfung lösen.')
                row = rows[0]
                if any((value == spool and (ip != row['ip'] or key != str(row['slot'])))
                       or (ip == row['ip'] and key == str(row['slot']) and value != spool)
                       for ip, slots in self.mappings.items() for key, value in slots.items()):
                    raise ValueError('Bitte zuerst die widersprüchliche manuelle Slot-Zuordnung lösen.')
                candidate[sku] = spool
            candidate = self.validate_sku_links(candidate)
            old = self.sku_links
            old_mappings = self.mappings
            if spool is not None:
                # Identity now follows the spool; do not leave a fixed old-slot claim.
                self.mappings = {ip: {key: value for key, value in slots.items() if value != spool}
                                 for ip, slots in self.mappings.items()}
            self.sku_links = candidate
            try:
                self.save()
            except OSError:
                self.sku_links = old
                self.mappings = old_mappings
                raise ValueError('Die Verknüpfung konnte nicht gespeichert werden.') from None
            return self.state()

    @staticmethod
    def validate_mappings(mappings):
        if not isinstance(mappings, dict) or len(mappings) > 256:
            raise ValueError('Ungültige Spulenzuordnung.')
        result = {}
        ids = set()
        for ip, slots in mappings.items():
            if not isinstance(slots, dict) or len(slots) > 16:
                raise ValueError('Ungültige Slot-Zuordnung.')
            address = ipaddress.ip_address(ip)
            if address.version != 4 or not any(address in net for net in NETWORKS):
                raise ValueError('Ungültiger Drucker.')
            result[ip] = {}
            for slot, spool in slots.items():
                if slot not in [str(i) for i in range(16)] or type(spool) is not int or spool <= 0 or spool in ids:
                    raise ValueError('Eine Spule kann nur einem Steckplatz zugeordnet sein.')
                ids.add(spool)
                result[ip][slot] = spool
        return result

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, name = tempfile.mkstemp(prefix='.spoolman-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w') as out:
                json.dump({'url': self.url, 'mappings': self.mappings, 'sku_links': self.sku_links}, out)
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)

    def state(self):
        return {'url': self.url, 'configured': bool(self.url), 'spools': self.items or [],
                'mappings': self.mappings, 'sku_links': self.sku_links, 'checked_at': self.checked, 'error': self.error,
                'inventory_current': self.checked is not None and self.clock() - self.checked <= 60 and not self.error,
                'limit_reached': self.items is not None and len(self.items) >= LIMIT, 'read_only': True}

    async def refresh(self):
        # One request at a time, no cookies, proxy settings, redirects or arbitrary paths.
        async with self.lock:
            if not self.url:
                return self.state()
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8), trust_env=False,
                                                 cookie_jar=aiohttp.DummyCookieJar()) as client:
                    async with client.get(self.url + '/api/v1/spool', params={'limit': LIMIT, 'allow_archived': 'false'}, allow_redirects=False) as response:
                        if response.status != 200:
                            raise ValueError('Spoolman hat die Abfrage nicht angenommen.')
                        chunks = bytearray()
                        async for chunk in response.content.iter_chunked(65536):
                            chunks.extend(chunk)
                            if len(chunks) > MAX_BYTES:
                                raise ValueError('Die Spulenliste ist zu groß.')
                        items = normalize(json.loads(chunks))
                self.items = items
                self.checked = self.clock()
                self.error = ''
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, UnicodeError):
                self.error = 'Spoolman nicht lesbar. Adresse, Dienst und Verbindung prüfen. Frühere Werte sind nicht aktuell.'
            return self.state()

    async def configure(self, url):
        url = local_url(url)
        async with self.lock:
            if url != self.url and (any(self.mappings.values()) or self.sku_links):
                raise ValueError('Vor dem Wechsel des Spoolman-Servers zuerst alle Spulenzuordnungen lösen.')
            old = self.url
            self.url = url
            try:
                self.save()
            except OSError:
                self.url = old
                raise ValueError('Die Einrichtung konnte nicht gespeichert werden.') from None
            self.items = None
            self.checked = None
            self.error = ''
        return await self.refresh()

    async def assign(self, ip, slot, spool, configured_ips, reported_slots):
        async with self.lock:
            if ip not in configured_ips or type(slot) is not int or slot not in reported_slots:
                raise ValueError('Dieser Steckplatz wird vom eingerichteten Drucker nicht gemeldet.')
            if spool is not None:
                if spool in self.sku_links.values():
                    raise ValueError('Diese Spule folgt bereits ihrer Kennung. Keine feste Slot-Zuordnung nötig. Zum manuellen Zuordnen zuerst die Kennung lösen.')
                if not self.state()['inventory_current'] or type(spool) is not int or spool not in {v['id'] for v in self.items}:
                    raise ValueError('Spulen zuerst aktualisieren und eine vorhandene Spule auswählen.')
            candidate = {key: dict(value) for key, value in self.mappings.items()}
            slots = candidate.setdefault(ip, {})
            if spool is None:
                slots.pop(str(slot), None)
            else:
                slots[str(slot)] = spool
            candidate = self.validate_mappings(candidate)
            old = self.mappings
            self.mappings = candidate
            try:
                self.save()
            except OSError:
                self.mappings = old
                raise ValueError('Die Zuordnung konnte nicht gespeichert werden.') from None
            return self.state()
