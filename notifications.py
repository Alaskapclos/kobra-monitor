# SPDX-License-Identifier: GPL-3.0-only
"""Opt-in encrypted Web Push from committed observations, never printer commands."""
import asyncio
import base64
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


KINDS = ('completed', 'errors', 'disconnect')
MAX_AGE = 3600


def unbase64(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', value):
        raise ValueError('Ungültiger Geräteschlüssel.')
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def subscription(value):
    if not isinstance(value, dict):
        raise ValueError('Die Geräteanmeldung fehlt.')
    endpoint = value.get('endpoint')
    try:
        url = urlsplit(endpoint) if isinstance(endpoint, str) else None
        host = url.hostname if url else ''
        approved = (host in ('fcm.googleapis.com', 'updates.push.services.mozilla.com', 'web.push.apple.com')
                    or host.endswith('.push.apple.com') or host.endswith('.notify.windows.com'))
        if (not approved or url.scheme != 'https' or url.port not in (None, 443)
                or url.username or url.password or url.fragment or not url.path or len(endpoint) > 3000):
            raise ValueError()
    except (ValueError, AttributeError, TypeError):
        raise ValueError('Der Push-Dienst dieses Browsers wird noch nicht unterstützt.') from None
    keys = value.get('keys')
    if not isinstance(keys, dict):
        raise ValueError('Die Geräteschlüssel fehlen.')
    try:
        public, auth = unbase64(keys.get('p256dh')), unbase64(keys.get('auth'))
        if len(public) != 65 or len(auth) != 16:
            raise ValueError()
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public)
    except (ValueError, TypeError):
        raise ValueError('Ungültiger Geräteschlüssel.') from None
    return {'endpoint': endpoint, 'keys': {'p256dh': keys['p256dh'], 'auth': keys['auth']}}


def preferences(value):
    if not isinstance(value, dict) or any(type(value.get(key)) is not bool for key in KINDS):
        raise ValueError('Bitte die gewünschten Meldungen auswählen.')
    delay = value.get('delay_seconds', 180)
    if type(delay) is not int or delay not in (60, 180, 300, 600):
        raise ValueError('Bitte eine gültige Wartezeit auswählen.')
    return {**{key: value[key] for key in KINDS}, 'delay_seconds': delay}


def deliver(info, payload, key_path, subject):
    # Provider endpoints only, no redirects or environment proxy credentials.
    import requests
    from pywebpush import webpush, WebPushException

    class DirectSession(requests.Session):
        def request(self, method, url, **kwargs):
            kwargs['allow_redirects'] = False
            return super().request(method, url, **kwargs)

    with DirectSession() as session:
        session.trust_env = False
        try:
            result = webpush(subscription(info), json.dumps(payload, ensure_ascii=False),
                             vapid_private_key=str(key_path), vapid_claims={'sub': subject},
                             ttl=MAX_AGE, timeout=10, requests_session=session)
            return result.status_code
        except WebPushException as exc:
            return exc.response.status_code if exc.response is not None else 0
        except (requests.RequestException, ValueError, OSError):
            return 0  # Do not log endpoints, credentials, or private payloads.


class Notifications:
    def __init__(self, history, directory, names=lambda: {}, clock=time.time, sender=deliver):
        self.history, self.db, self.lock = history, history.db, history.lock
        self.directory, self.names, self.clock, self.sender = Path(directory), names, clock, sender
        self.task = None
        self.key_path = self.directory / 'push-vapid.pem'
        self.send_lock = asyncio.Lock()
        with self.lock:
            self.db.executescript('''
              CREATE TABLE IF NOT EXISTS push_devices(id TEXT PRIMARY KEY, endpoint_hash TEXT UNIQUE,
                subscription TEXT, label TEXT, preferences TEXT, subject TEXT, created_at REAL,
                last_status TEXT, last_at REAL, test_at REAL DEFAULT 0);
              CREATE TABLE IF NOT EXISTS push_queue(id INTEGER PRIMARY KEY, device_id TEXT,
                event_key TEXT, payload TEXT, created_at REAL, attempts INTEGER DEFAULT 0,
                next_at REAL, status TEXT DEFAULT 'pending', UNIQUE(device_id,event_key));
              CREATE TABLE IF NOT EXISTS push_meta(key TEXT PRIMARY KEY, value TEXT);
            ''')
            if not self.db.execute("SELECT 1 FROM push_meta WHERE key='cursor'").fetchone():
                last = self.db.execute('SELECT coalesce(max(id),0) FROM events').fetchone()[0]
                self._meta('cursor', last)
            self.db.commit()

    def _meta(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO push_meta VALUES(?,?)', (key, json.dumps(value)))

    def _read(self, key, default):
        row = self.db.execute('SELECT value FROM push_meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def public_key(self):
        with self.lock:
            if not self.key_path.exists():
                if self.db.execute('SELECT count(*) FROM push_devices').fetchone()[0]:
                    raise ValueError('Der Benachrichtigungsschlüssel fehlt. Bitte die vollständige Sicherung wiederherstellen.')
                self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
                key = ec.generate_private_key(ec.SECP256R1())
                fd, name = tempfile.mkstemp(prefix='.push-', dir=self.directory)
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(key.private_bytes(serialization.Encoding.PEM,
                            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
                    os.replace(name, self.key_path)
                finally:
                    with contextlib.suppress(FileNotFoundError): os.unlink(name)
            key = serialization.load_pem_private_key(self.key_path.read_bytes(), password=None)
            if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
                raise ValueError('Der lokale Benachrichtigungsschlüssel ist ungültig.')
            public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
            return base64.urlsafe_b64encode(public).decode().rstrip('=')

    def state(self):
        with self.lock:
            devices = []
            for row in self.db.execute('SELECT * FROM push_devices ORDER BY created_at'):
                devices.append({key: row[key] for key in ('id', 'label', 'last_status', 'last_at')}
                               | {'preferences': json.loads(row['preferences'])})
            return {'devices': devices, 'read_only': True}

    def subscribe(self, info, label, prefs, subject):
        info, prefs = subscription(info), preferences(prefs)
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 60 or any(ord(c) < 32 for c in label):
            raise ValueError('Bitte einen Gerätenamen mit höchstens 60 Zeichen eingeben.')
        parsed = urlsplit(subject)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('Benachrichtigungen bitte über die HTTPS-Adresse einrichten.')
        self.public_key()
        fingerprint = hashlib.sha256(info['endpoint'].encode()).hexdigest()
        with self.lock:
            old = self.db.execute('SELECT id FROM push_devices WHERE endpoint_hash=?', (fingerprint,)).fetchone()
            if not old and self.db.execute('SELECT count(*) FROM push_devices').fetchone()[0] >= 20:
                raise ValueError('Es sind bereits 20 Geräte angemeldet. Bitte zuerst ein altes Gerät entfernen.')
            device_id = old[0] if old else secrets.token_hex(16)
            if old:
                self.db.execute('UPDATE push_devices SET subscription=?,label=?,preferences=?,subject=?,last_status=? WHERE id=?',
                    (json.dumps(info), label.strip(), json.dumps(prefs), subject, 'ready', device_id))
                self.db.execute("DELETE FROM push_queue WHERE device_id=? AND status='pending'", (device_id,))
            else:
                self.db.execute('INSERT INTO push_devices(id,endpoint_hash,subscription,label,preferences,subject,created_at,last_status) VALUES(?,?,?,?,?,?,?,?)',
                    (device_id, fingerprint, json.dumps(info), label.strip(), json.dumps(prefs), subject, self.clock(), 'ready'))
            self.db.commit()
            return device_id

    def remove(self, device_id):
        with self.lock:
            self.db.execute('DELETE FROM push_devices WHERE id=?', (device_id,))
            self.db.execute('DELETE FROM push_queue WHERE device_id=?', (device_id,))
            self.db.commit()

    def _enqueue(self, device, key, title, body, at):
        self.db.execute('INSERT OR IGNORE INTO push_queue(device_id,event_key,payload,created_at,next_at) VALUES(?,?,?,?,?)',
            (device['id'], key, json.dumps({'title': title, 'body': body, 'tag': hashlib.sha256(key.encode()).hexdigest()[:32], 'url': '/'}, ensure_ascii=False), at, self.clock()))

    def test(self, device_id):
        with self.lock:
            device = self.db.execute('SELECT * FROM push_devices WHERE id=?', (device_id,)).fetchone()
            if not device:
                raise ValueError('Dieses Gerät ist nicht mehr angemeldet.')
            if self.clock() - device['test_at'] < 60:
                raise ValueError('Bitte vor der nächsten Testmeldung eine Minute warten.')
            self._enqueue(device, 'test:' + secrets.token_hex(8), 'Kobra Monitor · Test', 'Benachrichtigungen für dieses Gerät sind eingerichtet.', self.clock())
            self.db.execute('UPDATE push_devices SET test_at=? WHERE id=?', (self.clock(), device_id))
            self.db.commit()

    def collect(self):
        now, names = self.clock(), self.names()
        with self.lock:
            cursor, offline, errors = self._read('cursor', 0), self._read('offline', {}), self._read('errors', {})
            devices = self.db.execute('SELECT * FROM push_devices').fetchall()
            events = self.db.execute('SELECT * FROM events WHERE id>? ORDER BY id LIMIT 500', (cursor,)).fetchall()
            for event in events:
                cursor = event['id']; ip = event['ip']; kind = event['kind']; at = event['at']
                if ip not in names:
                    offline.pop(ip, None)
                    continue
                name = str(names[ip])[:80]
                if kind == 'connected':
                    incident = offline.pop(ip, None)
                    if incident:
                        self.db.execute("DELETE FROM push_queue WHERE event_key=? AND status='pending'", (incident['key'],))
                if kind == 'disconnected': offline.setdefault(ip, {'at': at, 'key': 'offline:' + str(event['id'])})
                if not 0 <= now - at < MAX_AGE:
                    continue
                category = None
                if kind in ('completed', 'cancelled'):
                    category = 'completed'
                    title = 'Druck abgeschlossen' if kind == 'completed' else 'Druck abgebrochen'
                    body = name + (' meldet einen abgeschlossenen Druck.' if kind == 'completed' else ' meldet einen abgebrochenen Druck.')
                elif kind == 'printer_error':
                    detail = json.loads(event['details']); signature = ip + ':' + str(detail.get('code')) + ':' + str(detail.get('state'))
                    if now - errors.get(signature, float('-inf')) < 900:
                        continue
                    errors[signature] = now
                    category, title, body = 'errors', 'Drucker meldet eine Störung', name + ': Bitte den Druckerstatus prüfen.'
                if category:
                    for device in devices:
                        if at >= device['created_at'] and json.loads(device['preferences'])[category]:
                            self._enqueue(device, 'event:' + str(event['id']), title, body, at)
            for ip, incident in list(offline.items()):
                if ip not in names:
                    offline.pop(ip); continue
                for device in devices:
                    prefs = json.loads(device['preferences'])
                    # Newly enabled devices wait their own grace period; an outage is never a job end.
                    incident.setdefault('notified', [])
                    if device['id'] not in incident['notified'] and prefs['disconnect'] and now - max(incident['at'], device['created_at']) >= prefs['delay_seconds']:
                        self._enqueue(device, incident['key'], 'Drucker nicht erreichbar',
                            str(names[ip])[:80] + ': Die Verbindung fehlt länger. Der Druckstatus ist unbekannt.', now)
                        incident['notified'].append(device['id'])
            self._meta('cursor', cursor); self._meta('offline', offline)
            self._meta('errors', {k:v for k,v in errors.items() if now-v < 900})
            self.db.execute("UPDATE push_queue SET status='expired' WHERE status='pending' AND created_at<?", (now-MAX_AGE,))
            self.db.execute("DELETE FROM push_queue WHERE created_at<? AND status!='pending'", (now-7*86400,))
            self.db.commit()

    async def flush(self):
        async with self.send_lock:
            with self.lock:
                rows = self.db.execute("SELECT q.id AS queue_id,q.payload,q.attempts,q.created_at,d.* FROM push_queue q JOIN push_devices d ON d.id=q.device_id WHERE q.status='pending' AND q.next_at<=? ORDER BY q.id LIMIT 10", (self.clock(),)).fetchall()
            for row in rows:
                with self.lock:
                    if not self.db.execute('SELECT 1 FROM push_devices WHERE id=?', (row['id'],)).fetchone(): continue
                try:
                    status = await asyncio.to_thread(self.sender, json.loads(row['subscription']), json.loads(row['payload']), self.key_path, row['subject'])
                except Exception:
                    status = 0
                with self.lock:
                    if status in (404, 410):
                        self.remove(row['id']); continue
                    accepted = status in (200, 201, 202)
                    terminal = accepted or row['attempts'] >= 2 or self.clock()-row['created_at'] >= MAX_AGE or status in (400, 401, 403) or 300 <= status < 400
                    self.db.execute('UPDATE push_queue SET attempts=attempts+1,next_at=?,status=? WHERE id=?',
                        (self.clock() + (30 if row['attempts'] == 0 else 120), 'accepted' if accepted else 'failed' if terminal else 'pending', row['queue_id']))
                    self.db.execute('UPDATE push_devices SET last_status=?,last_at=? WHERE id=?',
                        ('accepted' if accepted else 'failed' if terminal else 'retrying', self.clock(), row['id']))
                    self.db.commit()

    async def run(self):
        while True:
            try:
                self.collect()
                await self.flush()
            except (OSError, ValueError):
                pass
            await asyncio.sleep(5)

    async def start(self, app):
        self.task = asyncio.create_task(self.run())

    async def stop(self, app):
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError): await self.task
