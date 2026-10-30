"""Local read-only monitor using the bundled, attributed OSS clients.

SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import asyncio
import contextlib
import copy
import ipaddress
import json
import logging
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

    def link(self, connected, message=''):
        with self.lock:
            self.connected = connected
            self.message = message

    def receive(self, kind, payload, bridge):
        if payload.get('code') not in (None, 200) or not isinstance(payload.get('data'), dict):
            return
        raw = payload['data']
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
                    'last_project':copy.deepcopy(self.last_project), 'server_time':time.time()}


class Monitor:
    def __init__(self, ip, runtime, data_dir, history=None):
        self.ip, self.runtime, self.data_dir = ip, Path(runtime), data_dir
        self.telemetry = Telemetry(ip)
        self.client = self.bridge = None
        self.task = None
        self.history = history

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
        self.client = KobraXClient(self.ip, hs.username, hs.password, hs.model_id, hs.device_id,
                                  client_id='readonly-monitor-'+uuid.uuid4().hex[:12], read_only=True,
                                  cert_file=str(cert), key_file=str(key))
        self.bridge = KobraXBridge(self.client, args=args)
        for suffix, original in list(self.client.callbacks.items()):
            kind = suffix.split('/')[0]
            def report(payload, callback=original, kind=kind, source_bridge=self.bridge):
                callback(payload)
                self.telemetry.receive(kind, payload, source_bridge)
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
                        next_info = next_ace = 0
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
    def __init__(self, ips, runtime, data_dir):
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
            self.monitors[ip] = Monitor(ip, private, str(Path(data_dir)/ip),self.history)
        self.telemetry = self

    def snapshot(self):
        printers = [item.telemetry.snapshot() for item in self.monitors.values()]
        return {**(printers[0] if printers else {}), 'configured':bool(printers), 'printers':printers, 'ips':self.ips, 'read_only':True,'history':self.history.jobs()}

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
                    item=Monitor(ip,private,str(self.data_dir/ip),self.history)
                    self.monitors[ip]=item
                    await item.start(None)
            self.ips=ips;self.ip=ips[0]

    async def start(self, app):
        for item in self.monitors.values():
            await item.start(app)

    async def stop(self, app):
        await asyncio.gather(*(item.stop(app) for item in self.monitors.values()))
        self.history.close()


def build_app(monitor,access=None):
    allowed = {'/','/api/status','/api/report','/api/timeline','/api/jobs','/api/session','/about','/license','/notice','/assets/setup.js','/assets/setup.css','/health','/assets/monitor.css','/assets/monitor.js','/favicon.ico'}
    @web.middleware
    async def boundary(request, handler):
        public={'/','/about','/license','/notice','/health','/assets/monitor.css','/assets/monitor.js','/assets/setup.css','/assets/setup.js','/favicon.ico','/api/session'}
        is_login=access is not None and request.method=='POST' and request.path=='/api/session'
        is_setup=access is not None and request.method=='POST' and request.path=='/api/setup'
        is_account=access is not None and request.method=='POST' and request.path in ('/api/account','/api/logout')
        valid_method=(request.method=='GET' and request.path in allowed) or is_login or is_setup or is_account
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
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
            'Referrer-Policy':'no-referrer', 'Content-Security-Policy':
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'"})
        return response
    app = web.Application(middlewares=[boundary], client_max_size=8192)
    async def index(request): return web.FileResponse(BASE/'static/index.html')
    async def about(request):return web.FileResponse(BASE/'static/about.html')
    async def license_text(request):return web.FileResponse(BASE/'LICENSE',headers={'Content-Type':'text/plain; charset=utf-8'})
    async def notice_text(request):return web.FileResponse(BASE/'NOTICE.md',headers={'Content-Type':'text/plain; charset=utf-8'})
    async def setup_js(request):return web.FileResponse(BASE/'static/setup.js')
    async def setup_css(request):return web.FileResponse(BASE/'static/setup.css')
    async def session(request):
        if access is None:return web.json_response({'authenticated':True,'csrf':'','read_only':True})
        if request.method=='POST':return await access.login(request)
        return web.json_response(access.state(request))
    async def setup(request):
        if request.content_type!='application/json':return web.json_response({'error':'Ungültiges Datenformat.'},status=400)
        try:
            body=await request.json()
            ips=printer_ips(body.get('printer_ips'))
            await monitor.configure(ips)
        except (ValueError,TypeError,AttributeError) as exc:
            return web.json_response({'error':str(exc)},status=400)
        return web.json_response({'ok':True,'read_only':True,'ips':ips})

    async def css(request): return web.FileResponse(BASE/'static/monitor.css')
    async def js(request): return web.FileResponse(BASE/'static/monitor.js')
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
    async def health(request): return web.json_response({'ok':True,'service':'kobra-monitor','read_only':True,'ip':monitor.ip,'ips':getattr(monitor,'ips',[monitor.ip])})
    async def timeline(request):
        job_id=request.query.get('job','')
        if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):
            return web.json_response({'error':'Ungültiger Auftrag.'},status=400)
        history=getattr(monitor,'history',None)
        result=await asyncio.to_thread(history.timeline,job_id) if history else None
        if result is None:return web.json_response({'error':'Auftrag nicht gefunden.'},status=404)
        return web.json_response(result)
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
    async def blocked(request): return web.json_response({'error':'Nur Statusabfragen erlaubt.'},status=403)
    app.router.add_get('/about',about)
    app.router.add_get('/license',license_text)
    app.router.add_get('/notice',notice_text)
    app.router.add_get('/', index)
    app.router.add_get('/assets/setup.js',setup_js)
    app.router.add_get('/assets/setup.css',setup_css)
    app.router.add_get('/api/session',session)
    app.router.add_post('/api/session',session)
    if access is not None:
        app.router.add_post('/api/account',access.save_account)
        app.router.add_post('/api/logout',access.logout)
    app.router.add_post('/api/setup',setup)
    app.router.add_get('/assets/monitor.css',css)
    app.router.add_get('/assets/monitor.js',js)
    app.router.add_get('/api/status',status)
    app.router.add_get('/api/report',report)
    app.router.add_get('/api/timeline',timeline)
    app.router.add_get('/api/jobs',jobs)
    app.router.add_get('/health',health)
    app.router.add_get('/favicon.ico',favicon)
    app.router.add_route('*','/{path:.*}',blocked)
    app.on_startup.append(monitor.start)
    app.on_cleanup.append(monitor.stop)
    return app


async def serve(args):
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix='kobra-monitor-') as runtime:
        data_dir = Path(args.data_dir)
        data_dir.mkdir(exist_ok=True, mode=0o700)
        monitor = Fleet(args.ips, runtime, str(data_dir))
        access=Access(data_dir)
        runner = web.AppRunner(build_app(monitor,access), access_log=None)
        try:
            await runner.setup()
            await web.TCPSite(runner,args.listen,args.port).start()
            print(f'Kobra Monitor: http://127.0.0.1:{args.port}',flush=True)
            print('Nur lesen. Anmeldung und Einrichtung im Browser.',flush=True)
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
            if running.get('service')=='kobra-monitor' and set(running.get('ips',[running.get('ip')]))==set(args.ips) and running.get('read_only') is True:
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
