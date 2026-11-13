# SPDX-License-Identifier: GPL-3.0-only
"""Owner-only archive-repeat API. Upload-only archive clients have no access."""
import asyncio
import hashlib
from aiohttp import web
from file_archive import digest,object_path
from reprint_preflight import inspect

PATH='/api/reprints'


def install(app,fleet,access,base):
    service=getattr(fleet,'reprints',None)
    check_lock=asyncio.Lock()

    async def endpoint(request):
        if access is None or access.account is None or not access.session(request):
            return web.json_response({'error':'Besitzeranmeldung erforderlich.'},status=401)
        if service is None:return web.json_response({'error':'Archivwiederholung hier nicht verfügbar.'},status=503)
        if request.method=='GET':
            with service.archive.h.lock:
                jobs=[dict(r) for r in service.archive.h.db.execute('''SELECT j.id,j.ip,j.filename,j.ended_at,l.sha256
                    FROM jobs j JOIN file_job_links l ON j.id=l.job_id JOIN archived_print_files f ON f.sha256=l.sha256
                    WHERE j.state='completed' AND j.ended_at IS NOT NULL ORDER BY j.ended_at DESC,j.id DESC LIMIT 100''')]
            targets=[]
            for ip,item in getattr(fleet,'monitors',{}).items():
                snapshot=item.telemetry.snapshot();data=snapshot.get('data') or {}
                enabled=bool(getattr(getattr(item,'archive_repeat',None),'enabled',False) and service.enabled)
                current=service.snapshot(ip) if enabled else None
                available=False
                try:service._fresh(ip);available=not service.busy(ip)
                except (ValueError,PermissionError):pass
                # No connection/session identifiers or upload URLs in this catalog.
                targets.append({'ip':ip,'name':data.get('printer_name') or ip,'enabled':enabled,
                    'available':available,'slots':current.get('slots',[]) if current else [],
                    'reason':'Bereit' if available else 'Nicht freigegeben' if not enabled else 'Aktuellen Leerlauf und ACE-Daten prüfen'})
            return web.json_response({'jobs':jobs,'targets':targets})
        if not access.can_write(request):return web.json_response({'error':'Anmeldung und Bestätigung erforderlich.'},status=403)
        try:
            if request.content_type!='application/json':raise ValueError('Ungültiges Datenformat.')
            body=await request.json()
            fields={'check':{'action','job','sha256'},
                'prepare':{'action','job','sha256','ip','assignments','request_id'},
                'transfer':{'action','id','token'},
                'start':{'action','id','token','bed_clear','material_ready','nozzle_mm'},
                'status':{'action','id'},'cancel':{'action','id'}}
            action=body.get('action') if isinstance(body,dict) else None
            if not isinstance(action,str) or action not in fields or set(body)!=fields[action]:raise ValueError('Ungültiger Archivauftrag.')
            authorized=lambda:access.can_write(request)
            if not authorized():raise PermissionError('Bitte erneut anmelden.')
            actor=hashlib.sha256(access.session(request)['csrf'].encode()).hexdigest()
            if action=='check':
                if check_lock.locked():return web.json_response({'error':'Dateiprüfung läuft bereits; kurz warten.'},status=429)
                service.eligible(body['job'],body['sha256'])
                path=object_path(service.archive.root,body['sha256'])
                def read():
                    if path.is_symlink() or not path.is_file() or digest(path)!=body['sha256']:raise ValueError('Geprüftes Original nicht verfügbar.')
                    result=inspect(path)
                    if digest(path)!=body['sha256']:raise ValueError('Original während der Prüfung geändert.')
                    return result
                async with check_lock:
                    task=asyncio.create_task(asyncio.to_thread(read))
                    try:result=await asyncio.shield(task)
                    except asyncio.CancelledError:await task;raise
                if not authorized():raise PermissionError('Bitte erneut anmelden.')
                return web.json_response(dict(result,sha256=body['sha256'],source_job=body['job']))
            if action=='prepare':
                result=await service.prepare(actor,body['request_id'],body['ip'],body['sha256'],body['assignments'],
                    source_job=body['job'],authorized=authorized)
            elif action=='transfer':result=await service.transfer(actor,body['id'],body['token'],authorized=authorized)
            elif action=='start':result=await service.launch(actor,body['id'],body['token'],
                bed_clear=body['bed_clear'],material_ready=body['material_ready'],nozzle_mm=body['nozzle_mm'],authorized=authorized)
            elif action=='cancel':result=await service.cancel(actor,body['id'])
            else:result=await service.status(actor,body['id'])
            if not authorized():raise PermissionError('Bitte erneut anmelden; Ergebnis im Druckerstatus prüfen.')
            return web.json_response(result)
        except PermissionError as exc:return web.json_response({'error':str(exc)},status=403)
        except (ValueError,TypeError,KeyError,AttributeError) as exc:
            return web.json_response({'error':str(exc) if isinstance(exc,ValueError) else 'Ungültige Angaben zur Druckwiederholung.'},status=400)
        except (OSError,TimeoutError):return web.json_response({'error':'Drucker oder Originaldatei derzeit nicht verfügbar.'},status=503)

    app.router.add_get(PATH,endpoint);app.router.add_post(PATH,endpoint)
    async def script(request):return web.FileResponse(base/'static/reprints.js')
    app.router.add_get('/assets/reprints.js',script)
