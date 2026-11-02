"""Local read-only monitor using the bundled, attributed OSS clients.

SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import asyncio
import contextlib
import copy
import hashlib
import ipaddress
import json
import logging
import math
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time
import uuid
import urllib.request
from urllib.parse import quote
from types import SimpleNamespace

BASE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE/'vendor/kobra-bridge'), str(BASE/'vendor/kobra-connect')]
from aiohttp import web
from kobra_connect import do_handshake, CloudModeError
from history import History
from access import Access
from configuration import printer_ips, load_config, save_config
from spools import Spools
from spoolman_view import gateway, gateway_path
from notifications import Notifications
from controls import LightControls, ControlRefused
from light_transport import LightControlClient
from diagnostics import summary as diagnostic_summary
from camera_view import CameraViews, decoder_available

STALE_AFTER = 90
RETRY_AFTER = 15


class Telemetry:
    """Separate received data from connectivity and per-section freshness."""
    def __init__(self, ip, clock=time.monotonic):
        self.ip, self.clock = ip, clock
        self.lock = threading.RLock()
        self.seen = {}
        self.data = {}
        self.connected = False
        self.message = 'Verbindung zum Drucker wird aufgebaut.'
        self.last_project = None
        self.device_values = {}
        self.device_seen = {}
        self.device_session = 0
        self.device_sessions = {}
        self.light_revision = 0
        self.light_connection_id = None

    def link(self, connected, message=''):
        with self.lock:
            if self.connected and not connected:
                self.device_session += 1
            self.connected = connected
            self.message = message

    def receive(self, kind, payload, bridge, connection_id=None):
        if payload.get('code') not in (None, 200) or not isinstance(payload.get('data'), dict):
            return
        raw = payload['data']
        # Read received fields directly; bridge defaults are not measurements.
        candidates = {}
        if kind in ('info', 'fan'):
            for source, target in (('fan_speed_pct', 'fan_speed'),
                    ('aux_fan_speed_pct', 'aux_fan_speed'),
                    ('box_fan_level', 'box_fan_level'),
                    ('print_speed_mode', 'speed_mode')):
                if source in raw:
                    candidates[target] = raw[source]
        if kind == 'print' and isinstance(raw.get('settings'), dict):
            if 'print_speed_mode' in raw['settings']:
                candidates['speed_mode'] = raw['settings']['print_speed_mode']
        if kind == 'light':
            lights = raw.get('lights')
            chamber = [entry for entry in lights if isinstance(entry, dict)
                       and type(entry.get('type')) is int and entry['type'] == 2] if isinstance(lights, list) else []
            light = chamber[0] if len(chamber) == 1 else raw if raw.get('type') == 2 else {}
            if 'status' in light:
                candidates['light_on'] = light['status']
            if 'brightness' in light:
                candidates['light_brightness'] = light['brightness']
        with self.lock:
            for key, val in candidates.items():
                if key == 'light_on':
                    if type(val) not in (bool, int) or val not in (0, 1):
                        continue
                    val = bool(val)
                elif (type(val) not in (int, float) or not math.isfinite(val)
                        or val < 0 or val > (100 if key != 'speed_mode' else 255)):
                    continue
                if key in ('speed_mode', 'box_fan_level') and int(val) != val:
                    continue
                if key == 'light_on':
                    self.light_revision += 1
                    self.light_connection_id = connection_id
                self.device_values[key] = val
                self.device_seen[key] = self.clock()
                self.device_sessions[key] = self.device_session
        groups = []
        if kind == 'info':
            if any(key in raw for key in ('printerName','model','version')):
                groups.append('printer')
            if isinstance(raw.get('temp'),dict) and 'curr_nozzle_temp' in raw['temp']:
                groups.append('temperature')
            if 'state' in raw or 'project' in raw:
                groups.append('print')
        elif kind == 'tempature' and 'curr_nozzle_temp' in raw:
            groups.append('temperature')
        elif kind == 'print' and ('progress' in raw or 'filename' in raw
                or payload.get('state') in ('printing','paused','finished','free','canceled','stoped')):
            groups.append('print')
        elif kind == 'multiColorBox' and isinstance(raw.get('multi_color_box'),list):
            groups.append('ace')
        if not groups:
            return
        with self.lock:
            now = self.clock()
            for group in groups:
                self.seen[group] = now
            state = bridge._state
            fields = {
                'printer':('printer_name','model_id','model_name','firmware_version'),
                'temperature':('nozzle_temp','nozzle_target','bed_temp','bed_target','fan_speed'),
                'print':('print_state','progress','filename','print_duration','remain_time','curr_layer','total_layers'),
            }
            for group in groups:
                for key in fields.get(group, ()):
                    self.data[key] = copy.deepcopy(state.get(key))
            if 'ace' in groups:
                slot_fields = ('index','global_index','box_id','type','color','status','edit_status','consumables_percent')
                has_boxes = bool(raw['multi_color_box'])
                self.data['ace_slots'] = [{k:copy.deepcopy(slot.get(k)) for k in slot_fields} for slot in bridge._ams_slots] if has_boxes else []
                for result, slot in zip(self.data['ace_slots'], bridge._ams_slots):
                    from spools import spool_sku
                    result['sku'] = spool_sku(slot.get('sku'))
                self.data['loaded_slot'] = bridge._ams_loaded_slot if has_boxes else -1
                self.data['ace_drying'] = copy.deepcopy(state.get('ace_drying', {})) if has_boxes else {}
                self.data['ace_units'] = list(bridge._ace_box_ids) if has_boxes else []
            previous = payload['data'].get('last_project')
            if isinstance(previous, dict):
                self.last_project = {k: previous.get(k) for k in
                    ('state','filename','progress','curr_layer','total_layers','print_time')}

    def snapshot(self):
        with self.lock:
            now = self.clock()
            ages = {group: max(0, round(now-stamp, 1)) for group,stamp in self.seen.items()}
            latest = min(ages.values()) if ages else None
            if not self.connected:
                status = 'offline' if ages else 'connecting'
            elif latest is None:
                status = 'connecting'
            elif latest > STALE_AFTER:
                status = 'stale'
            else:
                status = 'online'
            return {'read_only':True, 'ip':self.ip, 'connection':status,
                    'message':self.message, 'age_s':latest, 'section_age_s':ages,
                    'stale_after_s':STALE_AFTER, 'data':copy.deepcopy(self.data) if ages else None,
                    'device_status': {key: {'value': value,
                        'age_s': max(0, round(now-self.device_seen[key], 1)),
                        'current_session': self.device_sessions[key] == self.device_session}
                        for key, value in self.device_values.items()},
                    'last_project':copy.deepcopy(self.last_project), 'server_time':time.time()}


class Monitor:
    def __init__(self, ip, runtime, data_dir, history=None, light_control=False):
        self.ip, self.runtime, self.data_dir = ip, Path(runtime), data_dir
        self.telemetry = Telemetry(ip)
        self.client = self.bridge = None
        self.task = None
        self.history = history
        self.light_control_enabled = light_control

    async def connect(self):
        hs = await asyncio.to_thread(do_handshake, self.ip)
        if hs.broker_host != self.ip or hs.broker_port != 9883:
            raise ValueError('Unexpected MQTT broker')
        cert = self.runtime/'anycubic_slicer.crt'
        key = self.runtime/'anycubic_slicer.key'
        cert.write_text(hs.device_cert)
        key.write_text(hs.device_key)
        os.chmod(cert, 0o600)
        os.chmod(key, 0o600)
        # Certificate paths belong to this client, never shared process globals.
        from kobrax_client import KobraXClient
        from kobrax_moonraker_bridge import KobraXBridge
        logging.getLogger().setLevel(logging.WARNING)
        args = SimpleNamespace(read_only=True, model_id=hs.model_id, mode_id=hs.model_id,
            printer_ip=self.ip, device_id=hs.device_id, data_dir=self.data_dir,
            camera_on_print=0, spoolman_server='', poll_interval=3)
        self.client = LightControlClient(self.ip, hs.username, hs.password, hs.model_id, hs.device_id,
                                  client_id='kobra-monitor-'+uuid.uuid4().hex[:12],
                                  control_enabled=self.light_control_enabled,
                                  cert_file=str(cert), key_file=str(key))
        self.bridge = KobraXBridge(self.client, args=args)
        self.client.callbacks.setdefault('fan/report', lambda payload: None)
        for suffix, original in list(self.client.callbacks.items()):
            kind = suffix.split('/')[0]
            def report(payload, callback=original, kind=kind, source_bridge=self.bridge, source_client=self.client):
                callback(payload)
                self.telemetry.receive(kind, payload, source_bridge, source_client.control_connection_id())
                if self.history:
                    self.history.observe(self.ip,kind,payload,self.telemetry.snapshot())
            self.client.callbacks[suffix] = report
        connection = asyncio.create_task(asyncio.to_thread(self.client.connect))
        try:
            await asyncio.shield(connection)
        except asyncio.CancelledError:
            with contextlib.suppress(Exception):
                await connection
            raise
        self.telemetry.link(True)
        if self.history:self.history.link(self.ip,True)

    def light_snapshot(self):
        client = self.client
        epoch = client.control_connection_id() if client else None
        with self.telemetry.lock:
            return {'online': bool(epoch and epoch == self.telemetry.light_connection_id
                                   and self.telemetry.connected),
                    'connection_id': epoch,
                    'light_on': self.telemetry.device_values.get('light_on'),
                    'light_revision': self.telemetry.light_revision,
                    'light_age_s': max(0, self.telemetry.clock()-self.telemetry.device_seen.get('light_on', float('-inf')))}

    def light_supported(self):
        return bool(self.light_control_enabled and self.client
                    and str(self.client.mode_id) == '20025')

    async def refresh_light(self):
        client = self.client
        if not self.light_supported() or not client.control_connection_id():
            raise ControlRefused('Lichtsteuerung für diesen Drucker nicht verfügbar.')
        await asyncio.wait_for(asyncio.to_thread(client.publish, 'light', 'query', None, 1), 2)

    async def send_light(self, desired, epoch):
        client = self.client
        if not self.light_supported() or not client:
            raise ControlRefused('Lichtsteuerung für diesen Drucker nicht verfügbar.')
        deadline = time.monotonic()+4
        await asyncio.to_thread(client.send_light_once, desired, epoch, send_deadline=deadline)
        # Read back the state explicitly; never retry the control command.
        await asyncio.to_thread(client.publish, 'light', 'query', None, .5)

    async def disconnect(self):
        client, bridge = self.client, self.bridge
        self.client = self.bridge = None
        self.telemetry.link(False, 'Verbindung unterbrochen. Neuer Versuch folgt automatisch.')
        if self.history:self.history.link(self.ip,False)
        if client:
            await asyncio.to_thread(client.disconnect)
            reader = getattr(client, '_reader_thread', None)
            if reader:
                await asyncio.to_thread(reader.join, 2)
        if bridge:
            bridge._store._conn.close()
        for name in ('anycubic_slicer.crt', 'anycubic_slicer.key'):
            (self.runtime/name).unlink(missing_ok=True)

    async def run(self):
        try:
            while True:
                try:
                    if self.client is None:
                        self.telemetry.link(False, 'Verbindung zum Drucker wird aufgebaut.')
                        await self.connect()
                        next_info = next_ace = next_light = 0
                        session_started = time.monotonic()
                    connected = self.client._sock is not None and self.client._running
                    self.telemetry.link(connected, '' if connected else 'Drucker nicht erreichbar. Verbindung wird erneuert.')
                    if self.history:self.history.link(self.ip,connected)
                    snapshot = self.telemetry.snapshot()
                    age = snapshot['age_s']
                    if time.monotonic()-session_started>STALE_AFTER and (age is None or age>STALE_AFTER):
                        raise TimeoutError('No fresh telemetry')
                    now = time.monotonic()
                    if connected and now >= next_info:
                        await asyncio.wait_for(asyncio.to_thread(self.client.query_info), timeout=12)
                        next_info = time.monotonic()+30
                    if connected and now >= next_light:
                        await asyncio.wait_for(asyncio.to_thread(self.client.publish,
                            'light', 'query', None, timeout=5), timeout=7)
                        next_light = time.monotonic()+(10 if self.light_control_enabled else 30)
                    if connected and now >= next_ace:
                        await asyncio.wait_for(asyncio.to_thread(self.client.query_multicolor_box), timeout=12)
                        next_ace = time.monotonic()+60
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    await self.disconnect()
                    message = ('Bitte LAN-Modus am Drucker aktivieren.' if isinstance(exc,CloudModeError)
                               else 'Drucker nicht erreichbar. Neuer Verbindungsversuch in Kürze.')
                    self.telemetry.link(False, message)
                    await asyncio.sleep(RETRY_AFTER)
        finally:
            await self.disconnect()

    async def start(self, app):
        self.task = asyncio.create_task(self.run())

    async def stop(self, app):
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task


class Fleet:
    """Independent sessions, certificates, caches and databases per printer."""
    def __init__(self, ips, runtime, data_dir, *, light_control_ips=None):
        self.light_control_ips = set(printer_ips(light_control_ips)) if light_control_ips else set()
        self.started = time.monotonic()
        self.ips = list(ips)
        self.ip = self.ips[0] if self.ips else None
        self.runtime = Path(runtime)
        self.data_dir = Path(data_dir)
        self.config_lock = asyncio.Lock()
        self.monitors = {}
        self.history = History(Path(data_dir)/'history.sqlite3')
        for ip in self.ips:
            private = Path(runtime)/ip
            private.mkdir(mode=0o700)
            self.monitors[ip] = Monitor(ip, private, str(Path(data_dir)/ip),self.history, ip in self.light_control_ips)
        self.controls = LightControls(Path(data_dir)/'history.sqlite3', self.light_snapshot,
            self.send_light, enabled=True) if self.light_control_ips else None
        self.telemetry = self
        self.cameras = CameraViews()
        self.notifications = Notifications(self.history,self.data_dir,self.notification_names)
        self.spools = Spools(self.data_dir)
        self.history.report_materials=self.report_materials

    @property
    def read_only(self):
        return not bool(self.light_control_ips & set(self.ips))

    def light_snapshot(self, ip):
        item = self.monitors.get(ip)
        return item.light_snapshot() if item and item.light_supported() else None

    async def send_light(self, ip, desired, epoch):
        item = self.monitors.get(ip)
        if not item or not item.light_supported():
            raise ControlRefused('Dieser Drucker ist nicht für Lichtsteuerung freigegeben.')
        await item.send_light(desired, epoch)

    def report_materials(self,ip):
        state=self.spools.state()
        printers=[self.monitors[v].telemetry.snapshot() for v in self.ips if v in self.monitors]
        detections=[r for r in self.spools.detections(printers) if r['ip']==ip]
        ids={r['spool_id'] for r in detections if r['status']=='recognized'}
        manual=dict(self.spools.mappings.get(ip,{}))
        return {'basis':'Zum Archivierungszeitpunkt erfasst; keine Verbrauchsmessung.',
                'captured_at':time.time(),'inventory_current':state['inventory_current'],
                'inventory_checked_at':state['checked_at'],'detections':detections,'manual_slots':manual,
                'inventory':[r for r in state['spools'] if r['id'] in ids|set(manual.values())] if state['inventory_current'] else []}

    def notification_names(self):
        return {ip:(item.telemetry.snapshot().get('data') or {}).get('printer_name') or 'Drucker '+str(self.ips.index(ip)+1) for ip,item in self.monitors.items()}

    def snapshot(self):
        printers = [self.monitors[ip].telemetry.snapshot() for ip in self.ips if ip in self.monitors]
        for data in printers:
            item = self.monitors[data['ip']]
            data['read_only'] = not item.light_control_enabled
            data['light_control'] = {'enabled': item.light_control_enabled,
                                     'supported': item.light_supported()}
        return {**(printers[0] if printers else {}), 'configured':bool(printers), 'printers':printers, 'ips':self.ips, 'read_only':self.read_only,'controls':{'chamber_light':not self.read_only},'history':self.history.jobs(), 'camera_available':self.cameras.available(),'camera_message':decoder_available.message(),'report_archive_error':self.history.report_error}

    async def reorder(self,ips):
        async with self.config_lock:
            if (not isinstance(ips,list) or len(ips)!=len(self.ips)
                    or any(not isinstance(ip,str) for ip in ips)
                    or set(ips)!=set(self.ips)):
                raise ValueError('Die Druckerliste hat sich geändert. Bitte aktualisieren und erneut sortieren.')
            save_config(self.data_dir,ips)
            self.ips=list(ips);self.ip=self.ips[0] if self.ips else None

    async def configure(self,ips):
        ips=printer_ips(ips)
        async with self.config_lock:
            save_config(self.data_dir,ips)
            for ip in list(self.monitors):
                if ip not in ips:
                    await self.monitors.pop(ip).stop(None)
            for ip in ips:
                if ip not in self.monitors:
                    private=self.runtime/ip;private.mkdir(mode=0o700,exist_ok=True)
                    item=Monitor(ip,private,str(self.data_dir/ip),self.history,ip in self.light_control_ips)
                    self.monitors[ip]=item
                    await item.start(None)
            self.ips=ips;self.ip=ips[0]
            await self.cameras.prune(ips)

    async def start(self, app):
        for item in self.monitors.values():
            await item.start(app)

    async def stop(self, app):
        await asyncio.gather(*(item.stop(app) for item in self.monitors.values()))
        if self.controls:self.controls.close()
        self.history.close()


def build_app(monitor,access=None):
    allowed = {'/','/api/status','/api/report','/api/timeline','/api/jobs','/api/session','/about','/license','/notice','/assets/setup.js','/assets/setup.css','/health','/assets/monitor.css','/assets/monitor.js','/api/camera/frame','/assets/camera.js','/assets/notifications.js','/assets/diagnostics.js','/assets/spools.js','/service-worker.js','/manifest.webmanifest','/assets/app-icon.svg','/api/notifications','/api/diagnostics','/api/spools','/api/order-report','/api/report-export','/assets/orders.js','/assets/navigation.js','/assets/spool-workspace.js','/assets/controls.js','/favicon.ico'}
    @web.middleware
    async def boundary(request, handler):
        public={'/','/about','/license','/notice','/health','/assets/monitor.css','/assets/monitor.js','/assets/setup.css','/assets/setup.js','/assets/camera.js','/assets/notifications.js','/assets/diagnostics.js','/assets/spools.js','/service-worker.js','/manifest.webmanifest','/assets/app-icon.svg','/favicon.ico','/api/session','/assets/orders.js','/assets/navigation.js','/assets/spool-workspace.js','/assets/controls.js'}
        is_login=access is not None and request.method=='POST' and request.path=='/api/session'
        is_setup=access is not None and request.method=='POST' and request.path in ('/api/setup','/api/order','/api/camera/release','/api/notifications','/api/spools','/api/order-report','/api/controls')
        is_account=access is not None and request.method=='POST' and request.path in ('/api/account','/api/logout')
        integrated=gateway_path(request.path)
        valid_method=integrated or (request.method=='GET' and request.path in allowed) or is_login or is_setup or is_account
        if not valid_method:
            response = web.json_response({'error':'Nur Statusabfragen und lokale Einrichtung erlaubt.','read_only':True}, status=403)
        elif access is not None and request.path not in public and not access.session(request):
            response = web.json_response({'error':'Bitte anmelden.','read_only':True},status=401)
        elif access is not None and access.account is None and request.path not in public|{'/api/account','/api/logout'}:
            response = web.json_response({'error':'Bitte zuerst dein Benutzerkonto einrichten.','read_only':True},status=403)
        elif (is_setup or is_account) and not access.can_write(request):
            response = web.json_response({'error':'Einrichtung bitte aus dieser Oberfläche aufrufen.'},status=403)
        else:
            response = await handler(request)
        if response.content_type == 'application/json' and request.path in ('/api/session','/health','/api/status'):
            # Report the installation mode consistently, including login responses.
            try:
                body = json.loads(response.body)
                if isinstance(body, dict) and 'read_only' in body:
                    body['read_only'] = getattr(monitor, 'read_only', True)
                    response.body = json.dumps(body).encode()
            except (ValueError, TypeError, AttributeError):
                pass
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
            'Referrer-Policy':'no-referrer', 'Content-Security-Policy':
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'"})
        if integrated:
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'; object-src 'none'"
        return response
    app = web.Application(middlewares=[boundary], client_max_size=8192)
    async def index(request): return web.FileResponse(BASE/'static/index.html')
    async def about(request):return web.FileResponse(BASE/'static/about.html')
    async def license_text(request):return web.FileResponse(BASE/'LICENSE',headers={'Content-Type':'text/plain; charset=utf-8'})
    async def notice_text(request):return web.FileResponse(BASE/'NOTICE.md',headers={'Content-Type':'text/plain; charset=utf-8'})
    async def setup_js(request):return web.FileResponse(BASE/'static/setup.js')
    async def camera_js(request):return web.FileResponse(BASE/'static/camera.js')
    async def setup_css(request):return web.FileResponse(BASE/'static/setup.css')
    async def session(request):
        if access is None:return web.json_response({'authenticated':True,'csrf':'','read_only':True})
        if request.method=='POST':return await access.login(request)
        return web.json_response(access.state(request))
    async def control_action(request):
        if access is None or access.account is None or not access.can_write(request):
            return web.json_response({'error':'Anmeldung und Bestätigung erforderlich.'}, status=403)
        service = getattr(monitor, 'controls', None)
        if service is None or not service.enabled:
            return web.json_response({'error':'Die Lichtsteuerung ist nicht freigegeben.'}, status=403)
        if request.content_type != 'application/json':
            return web.json_response({'error':'Ungültiges Datenformat.'}, status=400)
        try:
            body = await request.json()
            if not isinstance(body, dict):raise ValueError('Ungültiger Steuerauftrag.')
            action = body.get('action')
            fields = {'prepare': {'action','ip','desired','request_id'},
                      'execute': {'action','id','token'}, 'cancel': {'action','id'},
                      'receipt': {'action','id'}}
            if not isinstance(action,str) or action not in fields or set(body) != fields[action]:
                raise ValueError('Ungültiger Steuerauftrag.')
            # Recheck after reading request body; an account change can revoke the session.
            if not access.can_write(request):
                return web.json_response({'error':'Bitte erneut anmelden.'}, status=401)
            actor = hashlib.sha256(access.session(request)['csrf'].encode()).hexdigest()
            if action == 'prepare':
                ip = body['ip']
                item = monitor.monitors.get(ip) if isinstance(ip,str) else None
                if item is None or not item.light_supported():
                    raise ControlRefused('Dieser Drucker ist nicht für Lichtsteuerung freigegeben.')
                await item.refresh_light()
                if not access.can_write(request):
                    return web.json_response({'error':'Bitte erneut anmelden.'}, status=401)
                result = await service.prepare(actor,ip,body['desired'],body['request_id'])
            else:
                if not isinstance(body['id'],str) or len(body['id'])!=32:
                    raise ValueError('Ungültige Vorgangskennung.')
                if action == 'execute':result = await service.execute(actor,body['id'],body['token'])
                elif action == 'cancel':result = await service.cancel(actor,body['id'])
                else:result = await service.receipt(actor,body['id'])
            return web.json_response(result)
        except (ValueError, TypeError, AttributeError) as exc:
            return web.json_response({'error': str(exc) if isinstance(exc,ValueError) else 'Ungültiger Steuerauftrag.'},status=400)
        except (OSError, asyncio.TimeoutError):
            return web.json_response({'error':'Druckerrückmeldung nicht verfügbar; bitte Status prüfen.'},status=503)

    async def setup(request):
        if request.content_type!='application/json':return web.json_response({'error':'Ungültiges Datenformat.'},status=400)
        try:
            body=await request.json()
            ips=printer_ips(body.get('printer_ips'))
            await monitor.configure(ips)
        except (ValueError,TypeError,AttributeError) as exc:
            return web.json_response({'error':str(exc)},status=400)
        return web.json_response({'ok':True,'read_only':True,'ips':ips})

    async def order(request):
        if request.content_type!='application/json':
            return web.json_response({'error':'Ungültiges Datenformat.'},status=400)
        try:
            body=await request.json()
            await monitor.reorder(body.get('printer_ips'))
        except (ValueError,TypeError,AttributeError) as exc:
            return web.json_response({'error':str(exc) if isinstance(exc,ValueError) else 'Ungültige Druckerliste.'},status=400)
        return web.json_response({'ok':True,'read_only':True,'ips':monitor.ips})

    async def css(request): return web.FileResponse(BASE/'static/monitor.css')
    async def js(request): return web.FileResponse(BASE/'static/monitor.js')
    async def controls_js(request): return web.FileResponse(BASE/'static/controls.js')
    async def status(request): return web.json_response(monitor.telemetry.snapshot())
    async def report(request):
        job_id=request.query.get('job','')
        if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):
            return web.json_response({'error':'Ungültiger Auftrag.'},status=400)
        history=getattr(monitor,'history',None)
        text=await asyncio.to_thread(history.report,job_id) if history else None
        if text is None:return web.json_response({'error':'Auftrag nicht gefunden.'},status=404)
        return web.Response(text=text,content_type='text/markdown',charset='utf-8',headers={
            'Content-Disposition':f'attachment; filename="Kobra-Druckbericht-{job_id[:8]}.md"'})
    async def order_report(request):
        history=getattr(monitor,'history',None)
        if history is None:return web.json_response({'error':'Historie nicht verfügbar.'},status=503)
        try:
            if request.method=='GET':
                return web.json_response(await asyncio.to_thread(history.reports.detail,request.query.get('job','')))
            if request.content_type!='application/json':raise ValueError('JSON erforderlich.')
            body=await request.json()
            job=body.get('job','')
            action=body.get('action')
            if action=='save':
                result=await asyncio.to_thread(history.reports.save,job,body.get('annotation',{}))
            elif action=='archive':
                await asyncio.to_thread(history.reports.freeze,job,'Manuell nachträglich archiviert')
                result=await asyncio.to_thread(history.reports.detail,job)
            elif action=='backfill':
                result={'archived':await asyncio.to_thread(history.reports.bootstrap),'read_only':True}
            elif action=='bundle':
                data=await asyncio.to_thread(history.reports.bundle,body.get('jobs'))
                return web.Response(body=data,content_type='application/zip',headers={'Content-Disposition':'attachment; filename="Kobra-Auftragsberichte.zip"'})
            else:raise ValueError('Unbekannte Aktion.')
            return web.json_response(result)
        except RuntimeError as exc:return web.json_response({'error':str(exc)},status=409)
        except (ValueError,TypeError,AttributeError) as exc:return web.json_response({'error':str(exc)},status=400)
        except Exception:return web.json_response({'error':'Bericht konnte nicht gespeichert werden. Bisherige Archivversionen bleiben erhalten.'},status=503)

    async def report_export(request):
        try:
            version=request.query.get('version','')
            if not version.isascii() or not version.isdigit() or len(version)>8:raise ValueError('Ungültige Version.')
            history=getattr(monitor,'history',None)
            if history is None:return web.json_response({'error':'Historie nicht verfügbar.'},status=503)
            data,mime,name=await asyncio.to_thread(history.reports.export,request.query.get('job',''),int(version),request.query.get('format','pdf'))
            return web.Response(body=data,content_type=mime,headers={'Content-Disposition':f'attachment; filename="{name}"'})
        except (ValueError,TypeError):return web.json_response({'error':'Archivversion oder Format nicht gefunden.'},status=404)

    async def orders_js(request):return web.FileResponse(BASE/'static/orders.js')
    async def navigation_js(request):return web.FileResponse(BASE/'static/navigation.js')
    async def health(request):
        result={'ok':True,'service':'kobra-monitor','read_only':True,'ip':monitor.ip,'ips':getattr(monitor,'ips',[monitor.ip])}
        cameras=getattr(monitor,'cameras',None)
        if cameras is not None and hasattr(cameras,'available'):result['camera_available']=cameras.available()
        return web.json_response(result)
    async def timeline(request):
        job_id=request.query.get('job','')
        if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):
            return web.json_response({'error':'Ungültiger Auftrag.'},status=400)
        history=getattr(monitor,'history',None)
        result=await asyncio.to_thread(history.timeline,job_id) if history else None
        if result is None:return web.json_response({'error':'Auftrag nicht gefunden.'},status=404)
        return web.json_response(result)
    async def camera_frame(request):
        viewer=request.query.get('viewer','legacy')
        if viewer!='legacy' and (len(viewer)!=32 or any(c not in '0123456789abcdef' for c in viewer)):
            return web.json_response({'error':'Ungültige Kameraansicht.'},status=400)
        if viewer=='legacy':return await monitor.cameras.frame(request.query.get('ip',''),monitor.ips)
        return await monitor.cameras.frame(request.query.get('ip',''),monitor.ips,viewer)
    async def camera_release(request):
        try:body=await request.json()
        except (ValueError,TypeError):body={}
        viewer=body.get('viewer','') if isinstance(body,dict) else ''
        if not isinstance(viewer,str) or len(viewer)!=32 or any(c not in '0123456789abcdef' for c in viewer):
            return web.json_response({'error':'Ungültige Kameraansicht.'},status=400)
        await monitor.cameras.release(viewer)
        return web.json_response({'released':True,'read_only':True})
    async def notification_assets(request):
        file={'/assets/spools.js':'spools.js','/assets/diagnostics.js':'diagnostics.js','/assets/notifications.js':'notifications.js','/service-worker.js':'service-worker.js','/manifest.webmanifest':'manifest.webmanifest','/assets/app-icon.svg':'app-icon.svg'}[request.path]
        response=web.FileResponse(BASE/'static'/file)
        if file=='service-worker.js':response.headers['Service-Worker-Allowed']='/'
        return response
    async def diagnostics(request):
        return web.json_response(await asyncio.to_thread(diagnostic_summary,monitor))

    async def spools(request):
        service=getattr(monitor,'spools',None)
        if service is None:return web.json_response({'error':'Spulenverwaltung hier nicht verfügbar.'},status=503)
        def snapshots():
            return [p.telemetry.snapshot() for ip,p in getattr(monitor,'monitors',{}).items()
                    if ip in getattr(monitor,'ips',[])]
        def with_detections(result):
            return {**result, 'detections': service.detections(snapshots())}
        try:
            if request.method=='GET':return web.json_response(with_detections(service.state()))
            if request.content_type!='application/json':raise ValueError('Ungültiges Datenformat.')
            body=await request.json()
            if body.get('action')=='configure':result=await service.configure(body.get('url'))
            elif body.get('action')=='refresh':result=await service.refresh()
            elif body.get('action')=='link_sku':
                if body.get('spool_id') is not None and body.get('unique_confirmed') is not True:
                    raise ValueError('Bitte bestätigen, dass diese Kennung nur zu dieser Spule gehört.')
                if body.get('spool_id') is not None and (not isinstance(body.get('ip'),str) or type(body.get('slot')) is not int):
                    raise ValueError('Bitte den gemeldeten Steckplatz auswählen.')
                result=await service.link_sku(body.get('sku'),body.get('spool_id'),snapshots(),(body.get('ip'),body.get('slot')))
            elif body.get('action')=='assign':
                ip=body.get('ip')
                printer=monitor.monitors.get(ip) if isinstance(ip,str) else None
                snapshot=printer.telemetry.snapshot() if printer else {}
                slots=(snapshot.get('data') or {}).get('ace_slots') or []
                reported={slot.get('global_index',slot.get('index')) for slot in slots if isinstance(slot,dict)}
                # Removing an old mapping remains possible after a slot/printer disappears.
                if body.get('spool_id') is None and ip in service.mappings:
                    reported.update(int(slot) for slot in service.mappings[ip])
                ips=list(getattr(monitor,'ips',[]))
                if body.get('spool_id') is None and ip in service.mappings:ips.append(ip)
                result=await service.assign(ip,body.get('slot'),body.get('spool_id'),ips,reported)
            else:raise ValueError('Unbekannte Aktion.')
            return web.json_response(with_detections(result))
        except ValueError as exc:
            return web.json_response({'error':str(exc)[:350] or 'Bitte die Angaben prüfen.'},status=400)
        except (TypeError,AttributeError):
            return web.json_response({'error':'Bitte die Angaben prüfen.'},status=400)

    async def notifications(request):
        service=getattr(monitor,'notifications',None)
        if service is None:return web.json_response({'error':'Benachrichtigungen sind hier nicht verfügbar.'},status=503)
        try:
            if request.method=='GET':return web.json_response({**service.state(),'public_key':service.public_key()})
            if request.content_type!='application/json':raise ValueError('Ungültiges Datenformat.')
            body=await request.json()
            action=body.get('action')
            if action=='subscribe':
                device_id=service.subscribe(body.get('subscription'),body.get('label'),body.get('preferences'),request.headers.get('Origin',''))
                return web.json_response({'ok':True,'id':device_id,'read_only':True})
            device_id=body.get('id')
            if not isinstance(device_id,str) or len(device_id)!=32 or any(c not in '0123456789abcdef' for c in device_id):raise ValueError('Ungültiges Gerät.')
            if action=='remove':service.remove(device_id)
            elif action=='test':service.test(device_id)
            else:raise ValueError('Unbekannte Aktion.')
            return web.json_response({'ok':True,'read_only':True})
        except (ValueError,TypeError,AttributeError):
            return web.json_response({'error':'Die Angaben sind ungültig oder das Gerät ist nicht verfügbar. Bitte prüfen und gegebenenfalls eine Minute warten.'},status=400)

    async def favicon(request): return web.Response(status=204)
    async def jobs(request):
        ip=request.query.get('ip','')
        if ip not in getattr(monitor,'ips',[]):
            return web.json_response({'error':'Drucker nicht konfiguriert.'},status=400)
        try:
            page_text=request.query.get('page','0')
            if len(page_text)>7 or not page_text.isascii() or not page_text.isdigit():raise ValueError()
            query={'search':request.query.get('search',''),'state':request.query.get('state','all'),'page':int(page_text)}
            history=getattr(monitor,'history',None)
            if history is None:return web.json_response({'error':'Historie nicht verfügbar.'},status=503)
            result=await asyncio.to_thread(history.archive,ip,**query)
        except ValueError:
            return web.json_response({'error':'Ungültiger Suchfilter.'},status=400)
        return web.json_response(result)
    async def integrated_spoolman(request):
        return await gateway(request,getattr(monitor,'spools',None),access)
    async def spool_workspace_js(request):return web.FileResponse(BASE/'static/spool-workspace.js')
    async def blocked(request): return web.json_response({'error':'Nur Statusabfragen erlaubt.'},status=403)
    app.router.add_get('/about',about)
    app.router.add_get('/license',license_text)
    app.router.add_get('/notice',notice_text)
    app.router.add_get('/', index)
    app.router.add_get('/assets/setup.js',setup_js)
    app.router.add_get('/assets/setup.css',setup_css)
    app.router.add_get('/assets/camera.js',camera_js)
    app.router.add_get('/api/session',session)
    app.router.add_post('/api/session',session)
    if access is not None:
        app.router.add_post('/api/account',access.save_account)
        app.router.add_post('/api/logout',access.logout)
    app.router.add_post('/api/setup',setup)
    app.router.add_post('/api/order',order)
    app.router.add_get('/assets/monitor.css',css)
    app.router.add_get('/assets/monitor.js',js)
    app.router.add_get('/assets/controls.js',controls_js)
    app.router.add_post('/api/controls',control_action)
    app.router.add_get('/api/status',status)
    app.router.add_get('/api/report',report)
    app.router.add_get('/api/order-report',order_report)
    app.router.add_post('/api/order-report',order_report)
    app.router.add_get('/api/report-export',report_export)
    app.router.add_get('/assets/orders.js',orders_js)
    app.router.add_get('/assets/navigation.js',navigation_js)
    app.router.add_get('/api/timeline',timeline)
    app.router.add_get('/api/jobs',jobs)
    app.router.add_get('/health',health)
    app.router.add_get('/api/camera/frame',camera_frame)
    if access is not None:app.router.add_post('/api/camera/release',camera_release)
    for path in ('/assets/notifications.js','/assets/diagnostics.js','/assets/spools.js','/service-worker.js','/manifest.webmanifest','/assets/app-icon.svg'):
        app.router.add_get(path,notification_assets)
    app.router.add_get('/api/notifications',notifications)
    app.router.add_get('/api/diagnostics',diagnostics)
    app.router.add_get('/api/spools',spools)
    if access is not None:app.router.add_post('/api/spools',spools)
    if access is not None:app.router.add_post('/api/notifications',notifications)
    app.router.add_get('/favicon.ico',favicon)
    app.router.add_get('/assets/spool-workspace.js',spool_workspace_js)
    app.router.add_route('*','/spoolman',integrated_spoolman)
    app.router.add_route('*','/spoolman/{path:.*}',integrated_spoolman)
    app.router.add_route('*','/{path:.*}',blocked)
    if getattr(monitor,'cameras',None) is not None:
        app.on_startup.append(monitor.cameras.start)
        app.on_cleanup.append(monitor.cameras.stop)
    if getattr(monitor,'notifications',None) is not None:
        app.on_startup.append(monitor.notifications.start)
        app.on_cleanup.append(monitor.notifications.stop)
    app.on_startup.append(monitor.start)
    app.on_cleanup.append(monitor.stop)
    return app


async def serve(args):
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix='kobra-monitor-') as runtime:
        data_dir = Path(args.data_dir)
        data_dir.mkdir(exist_ok=True, mode=0o700)
        monitor = Fleet(args.ips, runtime, str(data_dir),
            light_control_ips=printer_ips(os.environ['KOBRA_LIGHT_CONTROL_IPS'].split(','))
            if os.environ.get('KOBRA_LIGHT_CONTROL_IPS','').strip() else None)
        access=Access(data_dir)
        runner = web.AppRunner(build_app(monitor,access), access_log=None)
        try:
            await runner.setup()
            await web.TCPSite(runner,args.listen,args.port).start()
            print(f'Kobra Monitor: http://127.0.0.1:{args.port}',flush=True)
            print('Lichtsteuerung freigegeben. Anmeldung im Browser.' if not monitor.read_only else
                  'Nur lesen. Anmeldung und Einrichtung im Browser.',flush=True)
            if not access.account:print('Erste Einrichtung: python monitor.py --show-setup-link',flush=True)
            if args.open:
                import webbrowser
                webbrowser.open(f'http://127.0.0.1:{args.port}/'+('' if Access(args.data_dir).account else '#access='+quote(Access(args.data_dir).token,safe='')))
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:loop.add_signal_handler(sig,stop.set)
                except NotImplementedError:
                    signal.signal(sig,lambda *_:loop.call_soon_threadsafe(stop.set))
            await stop.wait()
        finally:
            await runner.cleanup()


def main():
    parser=argparse.ArgumentParser(description='Lokaler Kobra-Statusmonitor – ausschließlich lesend')
    parser.add_argument('--ip',action='append',help='Lokale Drucker-IP; für mehrere Drucker wiederholen')
    parser.add_argument('--port',type=int,default=7125,help='Lokaler Port der Statusübersicht')
    parser.add_argument('--open',action='store_true',help='Statusübersicht im Browser öffnen')
    parser.add_argument('--listen',default=os.environ.get('KOBRA_LISTEN','127.0.0.1'),help='Lokale Bindeadresse; Standard nur dieser Rechner')
    parser.add_argument('--data-dir',default=os.environ.get('KOBRA_DATA_DIR',str(BASE/'.state')),help='Dauerhafter Datenordner')
    parser.add_argument('--show-setup-link',action='store_true',help='Geschützten Link für die einmalige Kontoeinrichtung anzeigen')
    parser.add_argument('--show-access-code',action='store_true',help='Lokalen Zugangscode anzeigen und beenden')
    args=parser.parse_args()
    try:ipaddress.ip_address(args.listen)
    except ValueError:parser.error('Ungültige Bindeadresse.')
    if args.show_access_code or args.show_setup_link:
        access=Access(args.data_dir)
        if access.account:
            print('Ein Benutzerkonto ist eingerichtet. Bitte mit Benutzername und Passwort anmelden.')
            return
        print(f'http://127.0.0.1:{args.port}/#access='+quote(access.token,safe='') if args.show_setup_link else access.token)
        return
    try:
        configured=args.ip or ([v.strip() for v in os.environ['KOBRA_PRINTER_IPS'].split(',')] if os.environ.get('KOBRA_PRINTER_IPS') else load_config(args.data_dir))
        args.ips=printer_ips(configured) if configured else []
    except ValueError as exc:parser.error(str(exc))
    if not 1024<=args.port<=65535: parser.error('Port muss zwischen 1024 und 65535 liegen.')
    if args.open:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/health',timeout=0.7) as response:
                running=json.loads(response.read())
            if running.get('service')=='kobra-monitor' and set(running.get('ips',[running.get('ip')]))==set(args.ips) and type(running.get('read_only')) is bool:
                import webbrowser
                webbrowser.open(f'http://127.0.0.1:{args.port}/'+('' if Access(args.data_dir).account else '#access='+quote(Access(args.data_dir).token,safe='')))
                print('Der Kobra Monitor läuft bereits. Statusübersicht geöffnet.',flush=True)
                return
        except (OSError,ValueError):
            pass
    try:
        asyncio.run(serve(args))
    except OSError as exc:
        if exc.errno in (48,98):
            print(f'Port {args.port} ist bereits belegt. Beende den anderen Dienst oder wähle --port 7126.',file=sys.stderr)
            raise SystemExit(1) from None
        raise


if __name__=='__main__': main()
