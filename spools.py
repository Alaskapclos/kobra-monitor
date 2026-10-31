# SPDX-License-Identifier: GPL-3.0-only
"""Optional Spoolman inventory reader. Only local mapping writes; never printer I/O."""
import asyncio
import ipaddress
import json
import math
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit
import aiohttp
from configuration import NETWORKS

LIMIT = 1000
MAX_BYTES = 4 * 1024 * 1024


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
        self.items = None
        self.checked = None
        self.error = ''
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.url = local_url(data['url'])
            self.mappings = self.validate_mappings(data.get('mappings', {}))

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
                json.dump({'url': self.url, 'mappings': self.mappings}, out)
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)

    def state(self):
        return {'url': self.url, 'configured': bool(self.url), 'spools': self.items or [],
                'mappings': self.mappings, 'checked_at': self.checked, 'error': self.error,
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
            if url != self.url and any(self.mappings.values()):
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
