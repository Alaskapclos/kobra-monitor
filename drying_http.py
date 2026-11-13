# SPDX-License-Identifier: GPL-3.0-only
import hashlib
from aiohttp import web

PATH='/api/drying'


def install(app,fleet,access,base):
    async def endpoint(request):
        if access is None or access.account is None or not access.session(request):return web.json_response({'error':'Besitzeranmeldung erforderlich.'},status=401)
        if not access.can_write(request):return web.json_response({'error':'Anmeldung und Bestätigung erforderlich.'},status=403)
        service=getattr(fleet,'drying',None)
        if service is None:return web.json_response({'error':'Trocknungssteuerung nicht freigegeben.'},status=403)
        try:
            if request.content_type!='application/json':raise ValueError('Ungültiges Datenformat.')
            b=await request.json();action=b.get('action') if isinstance(b,dict) else None
            fields={'prepare':{'action','ip','box','on','temperature','duration','request_id'},'execute':{'action','id','token'},'status':{'action','id'},'cancel':{'action','id'}}
            if not isinstance(action,str) or action not in fields or set(b)!=fields[action]:raise ValueError('Ungültiger Trocknungsauftrag.')
            auth=lambda:access.can_write(request)
            if not auth():raise PermissionError('Bitte erneut anmelden.')
            actor=hashlib.sha256(access.session(request)['csrf'].encode()).hexdigest()
            if action=='prepare':result=await service.prepare(actor,b['ip'],b['box'],b['on'],b['temperature'],b['duration'],b['request_id'],auth)
            else:result=await service.action(actor,b['id'],action,b.get('token'),auth)
            if not auth():raise PermissionError('Bitte erneut anmelden; Druckerstatus prüfen.')
            return web.json_response(result)
        except PermissionError as e:return web.json_response({'error':str(e)},status=403)
        except (ValueError,TypeError,KeyError,AttributeError):return web.json_response({'error':'Angaben oder aktueller ACE-Zustand ungültig; bitte neu öffnen.'},status=400)
    app.router.add_post(PATH,endpoint)
    async def script(request):return web.FileResponse(base/'static/ace-controls.js')
    app.router.add_get('/assets/ace-controls.js',script)
