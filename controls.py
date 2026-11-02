# SPDX-License-Identifier: GPL-3.0-only
"""Explicit, single-use control intents. No transport is enabled by this module.

Chamber light and three fan channels share a per-printer single-use intent lock.
Senders and channel snapshots must be injected deliberately.
"""
import asyncio
import math
import secrets
import sqlite3
import time
import uuid


class ControlRefused(ValueError):
    pass


FAN_FIELDS = {'part_fan': 'fan_speed', 'aux_fan': 'aux_fan_speed', 'chamber_fan': 'box_fan_level'}


class LightControls:
    """Prepare an exact target, send once, then wait for observed telemetry.

    snapshot(ip) supplies connection_id, online, light_on, light_age_s and
    light_revision. connection_id changes after any reconnect; light_revision
    increases for every received light report. Revisions are never inferred from
    bridge defaults. sender(ip, on, connection_id) must send at most once and
    must reject a changed connection immediately before writing to its socket.
    """
    def __init__(self, database, snapshot, sender=None, *, enabled=False,
                 clock=time.time, monotonic=time.monotonic,
                 token_lifetime=20, confirmation_timeout=8, fan_snapshot=None, fan_sender=None, speed_snapshot=None, speed_sender=None):
        if type(enabled) is not bool or (sender is not None and not callable(sender)):
            raise ValueError('Explicit boolean mode and a callable sender required')
        for value, maximum in ((token_lifetime, 60), (confirmation_timeout, 30)):
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= maximum:
                raise ValueError('Invalid control timeout')
        self.fan_snapshot, self.fan_sender = fan_snapshot, fan_sender
        self.speed_snapshot, self.speed_sender = speed_snapshot, speed_sender
        self.snapshot = snapshot
        self.sender = sender
        self.enabled = enabled
        self.clock = clock
        self.monotonic = monotonic
        self.deadlines = {}
        self.token_lifetime = token_lifetime
        self.confirmation_timeout = confirmation_timeout
        self.lock = asyncio.Lock()
        self.db = sqlite3.connect(str(database), isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=3000')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS control_attempts (
                id TEXT PRIMARY KEY, actor TEXT NOT NULL,
                request_id TEXT NOT NULL, ip TEXT NOT NULL,
                desired INTEGER NOT NULL, before_value INTEGER NOT NULL,
                connection_id TEXT NOT NULL, before_revision INTEGER NOT NULL,
                token TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL,
                state TEXT NOT NULL, updated REAL NOT NULL,
                sent_revision INTEGER, detail TEXT NOT NULL,
                UNIQUE(actor, request_id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_control_per_printer
            ON control_attempts(ip) WHERE state IN ('prepared','sending');
        ''')
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(control_attempts)')}
        if 'control' not in columns:
            self.db.execute("ALTER TABLE control_attempts ADD COLUMN control TEXT NOT NULL DEFAULT 'chamber_light'")
        if 'target_context' not in columns:
            self.db.execute("ALTER TABLE control_attempts ADD COLUMN target_context TEXT NOT NULL DEFAULT ''")
        # A restart cannot know whether a socket write reached the printer.
        self.db.execute("UPDATE control_attempts SET state='uncertain', token='', "
                        "detail='Dienst neu gestartet; nicht erneut gesendet.', updated=? "
                        "WHERE state='sending'", (self.clock(),))
        self.db.execute("UPDATE control_attempts SET state='expired', token='', "
                        "detail='Vorbereitung durch Neustart verworfen.', updated=? "
                        "WHERE state='prepared'", (self.clock(),))

    def close(self):
        self.db.close()

    def _row(self, operation_id, actor):
        row = self.db.execute('SELECT * FROM control_attempts WHERE id=? AND actor=?',
                              (operation_id, actor)).fetchone()
        if row is None:
            raise ControlRefused('Dieser Vorgang gehört nicht zu deiner Sitzung.')
        return row

    @staticmethod
    def _public(row, include_token=False):
        result = {key: row[key] for key in ('id', 'ip', 'created', 'state', 'detail')}
        cast = bool if row['control'] == 'chamber_light' else int
        result.update(action=row['control'], desired=cast(row['desired']),
                      previous=cast(row['before_value']))
        if row['control'] == 'speed_mode':result['context'] = row['target_context']
        if include_token and row['state'] == 'prepared':
            result.update(token=row['token'], expires=row['expires'])
        return result

    def _fresh(self, ip, control='chamber_light'):
        data = self.snapshot(ip) if control == 'chamber_light' else (
            self.speed_snapshot(ip) if control == 'speed_mode' and self.speed_snapshot else
            self.fan_snapshot(ip, control) if control in FAN_FIELDS and self.fan_snapshot else None)
        if not isinstance(data, dict):
            raise ControlRefused('Der ausgewählte Drucker ist nicht verfügbar.')
        age = data.get('light_age_s')
        revision = data.get('light_revision')
        if (data.get('online') is not True or not self._valid_value(control, data.get('light_on'))
                or not isinstance(data.get('connection_id'), str)
                or not data['connection_id'] or len(data['connection_id']) > 128
                or type(revision) is not int or revision < 0
                or type(age) not in (int, float) or not math.isfinite(age)
                or not 0 <= age <= 15):
            raise ControlRefused('Frische Zustandsdaten und eine aktuelle Verbindung fehlen.')
        if control == 'speed_mode' and (not isinstance(data.get('context'),str)
                or len(data['context']) != 64):
            raise ControlRefused('Aktueller Druckauftrag fehlt; Speed Mode ist gesperrt.')
        return data

    @staticmethod
    def _valid_value(control, value):
        return (type(value) is bool if control == 'chamber_light' else
                type(value) is int and value in (1,2,3) if control == 'speed_mode' else
                control in FAN_FIELDS and type(value) is int and 0 <= value <= 100)

    def _expire(self):
        self.db.execute("UPDATE control_attempts SET state='expired', token='', "
                        "detail='Vorbereitung abgelaufen; bitte neu prüfen.', updated=? "
                        "WHERE state='prepared' AND expires<=?", (self.clock(), self.clock()))
        # Clock/NTP changes must not extend the authorization window.
        prepared = self.db.execute("SELECT id FROM control_attempts WHERE state='prepared'").fetchall()
        for row in prepared:
            if self.monotonic() >= self.deadlines.get(row['id'], float('-inf')):
                self.db.execute("UPDATE control_attempts SET state='expired', token='', "
                                "detail='Vorbereitung abgelaufen; bitte neu prüfen.', updated=? WHERE id=?",
                                (self.clock(), row['id']))
        active = {row['id'] for row in self.db.execute(
            "SELECT id FROM control_attempts WHERE state='prepared'")}
        self.deadlines = {key:value for key,value in self.deadlines.items() if key in active}

    async def prepare(self, actor, ip, desired, request_id, control='chamber_light'):
        if not self.enabled or self.sender is None:
            raise ControlRefused('Die Druckersteuerung ist noch nicht freigegeben.')
        if (not isinstance(actor, str) or not 1 <= len(actor) <= 128
                or not isinstance(ip, str) or len(ip) > 64
                or not isinstance(control, str) or not self._valid_value(control, desired)
                or (control in FAN_FIELDS and self.fan_sender is None)
                or (control == 'speed_mode' and self.speed_sender is None)):
            raise ControlRefused('Ungültiger Steuerauftrag.')
        try:
            if str(uuid.UUID(request_id)) != request_id:
                raise ValueError()
        except (ValueError, AttributeError, TypeError):
            raise ControlRefused('Ungültige Vorgangskennung.') from None
        async with self.lock:
            self._expire()
            old = self.db.execute('SELECT * FROM control_attempts WHERE actor=? AND request_id=?',
                                  (actor, request_id)).fetchone()
            if old:
                if old['ip'] != ip or old['control'] != control or old['desired'] != desired:
                    raise ControlRefused('Diese Vorgangskennung wurde bereits anders verwendet.')
                return self._public(old, include_token=True)
            data = self._fresh(ip, control)
            now, operation_id = self.clock(), uuid.uuid4().hex
            same = data['light_on'] == desired
            try:
                self.db.execute('INSERT INTO control_attempts '
                                '(id,actor,request_id,ip,desired,before_value,connection_id,before_revision,'
                                'token,created,expires,state,updated,sent_revision,detail,control,target_context) VALUES '
                                '(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
                    operation_id, actor, request_id, ip, int(desired), int(data['light_on']),
                    data['connection_id'], data['light_revision'],
                    '' if same else secrets.token_urlsafe(32), now,
                    now + self.token_lifetime, 'unchanged' if same else 'prepared', now, None,
                    'Bereits so gemeldet; kein Befehl gesendet.' if same else
                    'Vorbereitet; noch kein Befehl gesendet.', control, data.get('context','')))
            except sqlite3.IntegrityError:
                raise ControlRefused('Für diesen Drucker läuft bereits ein Steuervorgang.') from None
            if not same:
                self.deadlines[operation_id] = self.monotonic() + self.token_lifetime
            return self._public(self._row(operation_id, actor), include_token=True)

    async def cancel(self, actor, operation_id):
        async with self.lock:
            row = self._row(operation_id, actor)
            if row['state'] == 'prepared':
                self.db.execute("UPDATE control_attempts SET state='cancelled', token='', "
                                "updated=?, detail='Ohne Versand verworfen.' WHERE id=?",
                                (self.clock(), operation_id))
            self.deadlines.pop(operation_id, None)
            return self._public(self._row(operation_id, actor))

    async def execute(self, actor, operation_id, token):
        if not self.enabled or self.sender is None:
            raise ControlRefused('Die Druckersteuerung ist noch nicht freigegeben.')
        async with self.lock:
            self._expire()
            row = self._row(operation_id, actor)
            if row['state'] != 'prepared':
                # Double clicks, HTTP retries and old pages never send twice.
                return self._public(row)
            if not isinstance(token, str) or not secrets.compare_digest(row['token'], token):
                raise ControlRefused('Die Bestätigung ist ungültig.')
            try:
                data = self._fresh(row['ip'], row['control'])
                if data['connection_id'] != row['connection_id']:
                    raise ControlRefused('Verbindung gewechselt; bitte neu vorbereiten.')
                if row['control'] == 'speed_mode' and data['context'] != row['target_context']:
                    raise ControlRefused('Druckauftrag gewechselt; bitte neu auswählen.')
                if data['light_on'] != row['before_value']:
                    raise ControlRefused('Der Zustand wurde zwischenzeitlich geändert.')
            except ControlRefused as exc:
                self.db.execute("UPDATE control_attempts SET state='rejected', token='', "
                                "updated=?, detail=? WHERE id=?",
                                (self.clock(), str(exc), operation_id))
                raise
            # Commit BEFORE transport. A failure to write the audit prevents sending.
            self.db.execute("UPDATE control_attempts SET state='sending', token='', "
                            "sent_revision=?, updated=?, detail='Versand angefordert; "
                            "Rückmeldung wird geprüft.' WHERE id=?",
                            (data['light_revision'], self.clock(), operation_id))
            self.deadlines.pop(operation_id, None)
        try:
            # The sender has no reconnect, replay or retry path.
            send = (self.sender(row['ip'], bool(row['desired']), row['connection_id'])
                    if row['control'] == 'chamber_light' else
                    self.speed_sender(row['ip'], row['desired'], row['connection_id'], row['target_context'])
                    if row['control'] == 'speed_mode' else
                    self.fan_sender(row['ip'], row['control'], row['desired'], row['connection_id']))
            await asyncio.wait_for(send, timeout=5)
            deadline = asyncio.get_running_loop().time() + self.confirmation_timeout
            while asyncio.get_running_loop().time() < deadline:
                data = self._fresh(row['ip'], row['control'])
                if data['connection_id'] != row['connection_id']:
                    raise ControlRefused('Verbindung nach Versand gewechselt.')
                if row['control'] == 'speed_mode' and data['context'] != row['target_context']:
                    raise ControlRefused('Druckauftrag nach Versand gewechselt.')
                if (data['light_revision'] > self._row(operation_id, actor)['sent_revision']
                        and data['light_on'] == row['desired']):
                    return await self._finish(actor, operation_id, 'confirmed',
                                              'Neuer Zustand vom Drucker gemeldet.')
                await asyncio.sleep(.1)
        except asyncio.CancelledError:
            await self._finish(actor, operation_id, 'uncertain',
                               'Prüfung unterbrochen; nicht automatisch erneut gesendet.')
            raise
        except Exception:
            pass
        return await self._finish(actor, operation_id, 'uncertain',
                                  'Ausgang nicht bestätigt. Nicht automatisch erneut gesendet.')

    async def _finish(self, actor, operation_id, state, detail):
        async with self.lock:
            self.db.execute('UPDATE control_attempts SET state=?, updated=?, detail=? WHERE id=?',
                            (state, self.clock(), detail, operation_id))
            return self._public(self._row(operation_id, actor))

    async def receipt(self, actor, operation_id):
        async with self.lock:
            self._expire()
            return self._public(self._row(operation_id, actor))
