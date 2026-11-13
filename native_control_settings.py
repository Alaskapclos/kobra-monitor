# SPDX-License-Identifier: GPL-3.0-only
"""Owner-confirmed native grants, loaded on the next local application start."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from configuration import printer_ips

PATH = '/api/native-controls'
FORMAT = 'kobra-native-control-grants-v1'
SCOPES = {'light':'Licht', 'fans':'Lüfter', 'speed':'Speed Mode', 'temperature':'Temperaturen',
          'print':'Pause, Fortsetzen und Abbruch', 'motion':'Achsen und Homing',
          'archive':'Archivdruck starten', 'drying':'ACE-Trocknung'}
ENV = {'light':'KOBRA_LIGHT_CONTROL_IPS','fans':'KOBRA_FAN_CONTROL_IPS',
       'speed':'KOBRA_SPEED_CONTROL_IPS','temperature':'KOBRA_TEMPERATURE_CONTROL_IPS',
       'print':'KOBRA_PRINT_CONTROL_IPS','motion':'KOBRA_MOTION_CONTROL_IPS',
       'archive':'KOBRA_ARCHIVE_START_IPS','drying':'KOBRA_DRYING_CONTROL_IPS'}


def validate(grants):
    if not isinstance(grants, dict) or len(grants)>16:
        raise ValueError('Ungültige Steuerungsfreigaben.')
    result = {}
    for ip, row in grants.items():
        if not isinstance(ip,str) or printer_ips([ip]) != [ip] or not isinstance(row,dict) or set(row)!={'controls','drying_limit'}:
            raise ValueError('Ungültiger Drucker in den Freigaben.')
        controls = row['controls']
        if not isinstance(controls,list) or any(not isinstance(x,str) or x not in SCOPES for x in controls) or len(set(controls))!=len(controls):
            raise ValueError('Unbekannte oder doppelte Steuerungsfreigabe.')
        if type(row['drying_limit']) is not int or row['drying_limit'] not in (55,65):
            raise ValueError('ACE-Grenze muss 55 oder 65 °C sein.')
        if controls:result[ip]={'controls':sorted(controls),'drying_limit':row['drying_limit']}
    return result


class NativeControlSettings:
    def __init__(self,directory):
        self.path=Path(directory)/'native-controls.json'

    def read(self):
        if self.path.is_symlink():raise ValueError('Verknüpfte Steuerungsfreigaben sind ungültig.')
        if not self.path.exists():return {}
        if self.path.is_symlink() or (hasattr(self.path,'is_junction') and self.path.is_junction()) or self.path.stat().st_size>65536:
            raise ValueError('Lokale Steuerungsfreigaben sind ungültig.')
        value=json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(value,dict) or set(value)!={'format','grants'} or value['format']!=FORMAT:
            raise ValueError('Lokale Steuerungsfreigaben sind ungültig.')
        return validate(value['grants'])

    def revision(self,grants=None):
        return hashlib.sha256(json.dumps(self.read() if grants is None else grants,sort_keys=True).encode()).hexdigest()

    def write(self,grants):
        grants=validate(grants)
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd,name=tempfile.mkstemp(prefix='.native-controls-',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as stream:
                json.dump({'format':FORMAT,'grants':grants},stream,ensure_ascii=False);stream.write('\n')
            os.replace(name,self.path)
        finally:Path(name).unlink(missing_ok=True)

    def prune(self,ips):
        old=self.read();new={ip:row for ip,row in old.items() if ip in ips}
        if old!=new:self.write(new)

    def environment(self,ips):
        grants={ip:r for ip,r in self.read().items() if ip in ips}
        result={ENV[scope]:','.join(ip for ip,row in grants.items() if scope in row['controls']) for scope in SCOPES}
        result['KOBRA_DRYING_TEMPERATURE_LIMITS']=json.dumps({ip:r['drying_limit'] for ip,r in grants.items() if 'drying' in r['controls']})
        return result


def install(app,fleet,access,base):
    from aiohttp import web
    async def endpoint(request):
        store=getattr(fleet,'native_control_settings',None)
        if access is None or access.account is None or not access.session(request):
            return web.json_response({'error':'Besitzeranmeldung erforderlich.'},status=401)
        if store is None:return web.json_response({'available':False}) if request.method=='GET' else web.json_response({'error':'Nur für native Installationen verfügbar.'},status=403)
        try:
            if request.method=='POST':
                if not access.can_write(request):return web.json_response({'error':'Bitte erneut anmelden.'},status=403)
                if request.content_type!='application/json':raise ValueError('Ungültiges Datenformat.')
                body=await request.json()
                if not isinstance(body,dict) or set(body)!={'grants','printer_ips','revision','confirmed'} or body['confirmed'] is not True:
                    raise ValueError('Freigabe bitte ausdrücklich bestätigen.')
                async with fleet.config_lock:
                    if not access.can_write(request):return web.json_response({'error':'Bitte erneut anmelden.'},status=403)
                    if body['printer_ips']!=fleet.ips or body['revision']!=store.revision():
                        return web.json_response({'error':'Einrichtung wurde geändert. Bitte neu öffnen.'},status=409)
                    grants=validate(body['grants'])
                    if any(ip not in fleet.ips for ip in grants):raise ValueError('Nur gespeicherte Drucker freigeben.')
                    store.write(grants)
            saved=store.read()
            return web.json_response({'available':True,'printer_ips':list(fleet.ips),'grants':saved,
                                      'revision':store.revision(saved),'scopes':SCOPES,'restart_required':True})
        except (ValueError,TypeError,KeyError,OSError):
            return web.json_response({'error':'Freigaben konnten nicht gespeichert oder gelesen werden. Bitte Einrichtung neu öffnen.'},status=400)
    app.router.add_get(PATH,endpoint);app.router.add_post(PATH,endpoint)
    async def script(request):return web.FileResponse(base/'static/native-controls.js')
    app.router.add_get('/assets/native-controls.js',script)
