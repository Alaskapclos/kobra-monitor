# SPDX-License-Identifier: GPL-3.0-only
"""Own-process supervisor for a native desktop test bundle. No printer commands."""
import contextlib
import hmac
import http.server
import json
import os
import re
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

FORMAT = 'kobra-native-desktop-v1'

# Isolated POSIX interpreters do not inherit application paths from PYTHONPATH.
# The parent pipe also ends owned children after an unexpected worker exit.
POSIX_BOOTSTRAP = '''import os,runpy,signal,sys,threading
sys.path[:0]=sys.argv[1:3]
fd=int(sys.argv[3]);kind=sys.argv[4];target=sys.argv[5];sys.argv=sys.argv[5:]
if fd>=0:
 def watch():
  try: os.read(fd,1)
  finally: os.close(fd);os.kill(os.getpid(),signal.SIGTERM)
 threading.Thread(target=watch,daemon=True).start()
if kind=='module':runpy.run_module(target,run_name='__main__',alter_sys=True)
else:runpy.run_path(target,run_name='__main__')
'''


def child_command(bundle, role, cwd, args, *, system=None, parent_fd=-1):
    system=sys.platform if system is None else system
    bundle,cwd=Path(bundle),Path(cwd)
    if role not in ('monitor','spoolman'):raise ValueError('Unbekannte native Laufzeit.')
    if system=='darwin':
        kind='module' if args[0]=='-m' else 'script'
        target=args[1] if kind=='module' else str(cwd/args[0])
        rest=args[2:] if kind=='module' else args[1:]
        return [str(bundle/'runtime'/role/'bin/python3.14'),'-I','-B','-X','utf8','-c',
                POSIX_BOOTSTRAP,str(cwd),str(bundle/'app/monitor'),str(parent_fd),kind,target,*rest]
    return [str(bundle/'runtime'/role/'python.exe'),'-X','utf8',*args]


def role_environment(bundle, role, base, *, system=None):
    if role not in ('monitor','spoolman'):raise ValueError('Unbekannte native Laufzeit.')
    system=sys.platform if system is None else system
    runtime=Path(bundle)/'runtime'/role;result=base.copy()
    paths=[str(runtime/'bin')] if system=='darwin' else [str(runtime/'Scripts'),str(runtime)]
    separator=';' if system=='win32' else os.pathsep
    result['PATH']=separator.join([*paths,base.get('PATH','')])
    return result


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name('.' + path.name + '-' + secrets.token_hex(4))
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.write('\n')
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class InstallationLock:
    def __init__(self, path):
        self.path, self.stream = Path(path), None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.stream = self.path.open('a+b')
        # Windows also denies reads through another handle to a locked byte.
        # Inspect the file length without reading the byte owned by that process.
        try:
            if os.fstat(self.stream.fileno()).st_size == 0:
                self.stream.write(b'0'); self.stream.flush()
            self.stream.seek(0)
        except BaseException:
            self.stream.close(); self.stream = None
            raise
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close(); self.stream = None
            return False
        return True

    def close(self):
        if self.stream is not None:
            if os.name == 'nt':
                import msvcrt
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            self.stream.close(); self.stream = None


def local_url(value, *, fragment=False):
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == 'http' and parsed.hostname == '127.0.0.1' and
                parsed.username is None and parsed.password is None and
                type(parsed.port) is int and 1024 <= parsed.port <= 65535 and
                parsed.path in ('', '/') and not parsed.query and (fragment or not parsed.fragment))
    except (ValueError, TypeError):
        return False


def free_port(preferred=None):
    for port in [preferred, 0] if preferred else [0]:
        if type(port) is not int or not (port == 0 or 1024 <= port <= 65535):
            continue
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
                return probe.getsockname()[1]
            except OSError:
                continue
    raise ValueError('Kein freier lokaler Port verfügbar.')


def private_instance(data):
    path = Path(data) / 'instance.json'
    if path.is_symlink() or path.stat().st_size > 8192:
        raise ValueError('Ungültiger lokaler Betriebsstatus.')
    result = json.loads(path.read_text())
    if (result.get('format') != FORMAT or not local_url(result.get('control_url')) or
            not isinstance(result.get('control_token'), str) or not re.fullmatch('[a-f0-9]{64}', result['control_token'])):
        raise ValueError('Ungültiger lokaler Betriebsstatus.')
    return result


def controller_request(data, action='status'):
    if action not in ('status', 'stop'):
        raise ValueError('Unbekannte lokale Aktion.')
    state = private_instance(data)
    request = urllib.request.Request(state['control_url'] + '/' + action,
        method='POST' if action == 'stop' else 'GET',
        headers={'Authorization': 'Bearer ' + state['control_token']})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=3) as response:
        result = json.load(response)
    if result.get('instance') != state['instance']:
        raise ValueError('Die lokale Anwendung wurde inzwischen gewechselt.')
    if action == 'status' and not local_url(result.get('monitor_url'), fragment=True):
        raise ValueError('Ungültige lokale Monitoradresse.')
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Lokale Prozesssteuerung folgt keinen Weiterleitungen.')


def create_control_server(token, instance, monitor_url, stop):
    class LocalServer(http.server.HTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(2)
            return connection, address
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def handle_request(self, method):
            expected_host = '127.0.0.1:' + str(self.server.server_port)
            supplied = self.headers.get_all('Authorization', [])
            authenticated = len(supplied) == 1 and hmac.compare_digest(supplied[0].encode('utf-8'), ('Bearer ' + token).encode('ascii'))
            if (self.headers.get_all('Host', []) != [expected_host] or not authenticated or
                    self.headers.get('Origin') not in (None, 'http://' + expected_host)):
                code, body = 401, {'error': 'Local owner access required'}
            elif method == 'GET' and self.path == '/status':
                code, body = 200, {'instance': instance, 'monitor_url': monitor_url}
            elif method == 'POST' and self.path == '/stop' and self.headers.get('Content-Length', '0') == '0':
                stop.set(); code, body = 200, {'instance': instance, 'stopping': True}
            else:
                code, body = 404, {'error': 'Unknown local action'}
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self): self.handle_request('GET')
        def do_POST(self): self.handle_request('POST')

    server = LocalServer(('127.0.0.1', 0), Handler)
    server.timeout = .5
    return server


def child_environment(data, ffmpeg, backend_url, backend_token):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('KOBRA_', 'SPOOLMAN_', 'PYTHON', 'DYLD_', 'LD_'))}
    data = Path(data)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
        PATH=str(ffmpeg) + os.pathsep + env.get('PATH', ''),
        KOBRA_DATA_DIR=str(data / 'monitor'), KOBRA_LISTEN='127.0.0.1', KOBRA_NATIVE_CONTROL_SETTINGS='1',
        KOBRA_NATIVE_SPOOLMAN_URL=backend_url, KOBRA_NATIVE_SPOOLMAN_TOKEN=backend_token,
        SPOOLMAN_DIR_DATA=str(data / 'spoolman'), SPOOLMAN_DIR_LOGS=str(data / 'logs/spoolman'),
        SPOOLMAN_DIR_BACKUPS=str(data / 'spoolman-native-backups'),
        SPOOLMAN_BASE_PATH='/spoolman', SPOOLMAN_AUTOMATIC_BACKUP='TRUE',
        EXTERNAL_DB_URL='', TZ='UTC')
    return env


def prepare_data(data, version, backend_url):
    data = Path(data)
    if data.is_symlink(): raise ValueError('Verknüpfungen als Datenordner sind nicht erlaubt.')
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = data / 'desktop.json'
    previous = None
    if marker.exists():
        if marker.is_symlink(): raise ValueError('Ungültiger Datenordner.')
        previous = json.loads(marker.read_text())
        if previous.get('format') != FORMAT or previous.get('version') != version:
            raise ValueError('Dieser Datenordner benötigt eine ausdrücklich geprüfte Versionsübernahme.')
    elif any(p.name != 'desktop.lock' for p in data.iterdir()):
        raise ValueError('Vorhandene fremde Daten werden nicht automatisch übernommen.')
    for name in ('monitor', 'spoolman', 'logs', 'logs/spoolman', 'spoolman-native-backups', 'backups'):
        path = data / name
        if path.is_symlink(): raise ValueError('Verknüpfungen in den Datenbereichen sind nicht erlaubt.')
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    settings = data / 'monitor/spoolman.json'
    if settings.exists():
        if settings.is_symlink(): raise ValueError('Ungültige Spoolman-Konfiguration.')
        content = json.loads(settings.read_text())
        if previous and content.get('url') == previous.get('backend_url'):
            content['url'] = backend_url
            atomic_json(settings, content)
    else:
        atomic_json(settings, {'url': backend_url, 'mappings': {}, 'sku_links': {}, 'amount_sources': {}})
    identity = (previous or {}).get('identity') or secrets.token_hex(16)
    atomic_json(marker, {'format': FORMAT, 'identity': identity, 'version': version, 'backend_url': backend_url})
    return identity


def wait_ready(processes, monitor_url, backend_url, token, timeout=90):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('Ein lokaler Dienst wurde beim Start beendet. Bitte das lokale Fehlerprotokoll prüfen.')
        try:
            with opener.open(monitor_url + '/health', timeout=1) as response:
                state = json.load(response)
                assert state.get('service') == 'kobra-monitor' and state.get('ok') is True
            request = urllib.request.Request(backend_url + '/api/v1/health',
                headers={'Authorization': 'Bearer ' + token})
            with opener.open(request, timeout=1) as response:
                assert response.status == 200
            return
        except (OSError, ValueError, AssertionError):
            time.sleep(.25)
    raise TimeoutError('Die lokalen Dienste sind nicht rechtzeitig bereit geworden.')


def terminate_owned(processes):
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    for process in reversed(processes):
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)


class WindowsJob:
    """Only handles of child processes created by this supervisor are accepted."""
    def __init__(self):
        self.handle = None
        if os.name != 'nt': return
        import ctypes as c
        u32, u64, size = c.c_uint32, c.c_uint64, c.c_size_t
        class Basic(c.Structure):
            _fields_ = [('process_time', u64), ('job_time', u64), ('flags', u32),
                        ('minimum', size), ('maximum', size), ('active', u32),
                        ('affinity', size), ('priority', u32), ('scheduling', u32)]
        class Extended(c.Structure):
            _fields_ = [('basic', Basic), ('io', u64 * 6), ('process_memory', size),
                        ('job_memory', size), ('peak_process', size), ('peak_job', size)]
        kernel = c.WinDLL('kernel32', use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [c.c_void_p, c.c_wchar_p]
        kernel.CreateJobObjectW.restype = c.c_void_p
        kernel.SetInformationJobObject.argtypes = [c.c_void_p, c.c_int, c.c_void_p, u32]
        kernel.AssignProcessToJobObject.argtypes = [c.c_void_p, c.c_void_p]
        kernel.CloseHandle.argtypes = [c.c_void_p]
        handle = kernel.CreateJobObjectW(None, None)
        if not handle: raise OSError(c.get_last_error(), 'Lokale Prozessgruppe konnte nicht angelegt werden.')
        info = Extended(); info.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(handle, 9, c.byref(info), c.sizeof(info)):
            kernel.CloseHandle(handle)
            raise OSError(c.get_last_error(), 'Lokale Prozessgruppe konnte nicht geschützt werden.')
        self.kernel, self.handle = kernel, handle

    def add(self, process):
        if self.handle is not None and not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise OSError('Ein eigener Kindprozess konnte nicht der lokalen Prozessgruppe zugeordnet werden.')

    def close(self):
        if self.handle is not None:
            self.kernel.CloseHandle(self.handle); self.handle = None


def supervise(bundle, data, version, *, open_browser=True):
    """Blocking worker; entrypoint must keep its InstallationLock for this call."""
    bundle, data = Path(bundle), Path(data)
    monitor_port, spoolman_port = free_port(17135), free_port(17136)
    while monitor_port == spoolman_port: spoolman_port = free_port()
    base = 'http://127.0.0.1:' + str(monitor_port)
    backend = 'http://127.0.0.1:' + str(spoolman_port) + '/spoolman'
    identity = prepare_data(data, version, backend)
    env = child_environment(data, bundle / 'ffmpeg/bin', backend, secrets.token_hex(32))
    token = secrets.token_hex(32); stop = threading.Event(); processes=[]; streams=[]; parent_pipes=[]
    job = WindowsJob(); server = None
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        commands = [
            ('spoolman', 'spoolman', bundle / 'app/spoolman',
             ['-m', 'uvicorn', 'suite.native_backend:create_application', '--factory', '--host', '127.0.0.1',
              '--port', str(spoolman_port), '--loop', 'asyncio', '--no-access-log']),
            ('monitor', 'monitor', bundle / 'app/monitor',
             ['monitor.py', '--listen', '127.0.0.1', '--port', str(monitor_port)]),
            ('backups', 'monitor', bundle / 'app/monitor',
             ['-m', 'suite.native_backup', '--data', str(data), '--version', version])]
        from access import Access
        from urllib.parse import quote
        access = Access(data / 'monitor')
        browser_url = base + '/' + ('' if access.account else '#access=' + quote(access.token, safe=''))
        for name, role, cwd, args in commands:
            stream = (data / 'logs' / (name + '.log')).open('ab'); streams.append(stream)
            reader=-1;options={}
            if sys.platform=='darwin':
                reader,writer=os.pipe();parent_pipes.append(writer);options['pass_fds']=(reader,)
            try:
                process = subprocess.Popen(child_command(bundle,role,cwd,args,parent_fd=reader), cwd=cwd, env=role_environment(bundle,role,env),
                    stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, creationflags=flags,**options)
            finally:
                if reader>=0:os.close(reader)
            processes.append(process); job.add(process)
        wait_ready(processes, base, backend, env['KOBRA_NATIVE_SPOOLMAN_TOKEN'])
        server = create_control_server(token, identity, browser_url, stop)
        atomic_json(data / 'instance.json', {'format': FORMAT, 'instance': identity,
            'control_url': 'http://127.0.0.1:' + str(server.server_port),
            'control_token': token, 'version': version})
        if open_browser:
            import webbrowser
            webbrowser.open(browser_url)
        while not stop.is_set():
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('Ein lokaler Dienst wurde beendet. Das lokale Fehlerprotokoll enthält weitere Angaben.')
            server.handle_request()
    finally:
        if server is not None: server.server_close()
        terminate_owned(processes); job.close()
        for writer in parent_pipes:os.close(writer)
        for stream in streams: stream.close()
        with contextlib.suppress(OSError, ValueError, KeyError):
            state = private_instance(data)
            if state['control_token'] == token: (data / 'instance.json').unlink()
