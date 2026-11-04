"""Owner archive UI and separately scoped, upload-only computer access.
SPDX-License-Identifier: GPL-3.0-only
"""
import asyncio
import base64
import json
import os
import tempfile
from aiohttp import web
from file_archive import MAX_FILE, digest, filename, object_path

MACHINE_PATHS = {'/api/archive/ingest', '/api/archive/heartbeat'}
OWNER_PATHS = {'/api/archive', '/api/archive/original'}


def machine_client(request, archive):
    if request.method != 'POST' or request.path not in MACHINE_PATHS or request.headers.get('Origin') or request.headers.get('Sec-Fetch-Site'): return None
    auth = request.headers.get('Authorization', '')
    return archive.authenticate(auth[7:]) if auth.startswith('Bearer ') else None


def install(app, archive, access, base):
    upload_lock = asyncio.Lock()

    async def catalog(request):
        if request.method == 'GET': return web.json_response(await asyncio.to_thread(archive.listing))
        body = await request.json()
        try:
            if body.get('action') == 'pair':
                token = archive.new_client(body.get('name'))
                # Same installation origin only; never supplied by an untrusted helper.
                return web.json_response({'format':'kobra-archive-client-v1', 'base_url':request.headers.get('Origin') or f'{request.scheme}://{request.host}', 'token':token})
            if body.get('action') == 'revoke': archive.revoke(body.get('id'))
            elif body.get('action') == 'link':
                archive.link(body.get('job'), body.get('sha256'))
                if archive.h.reports.job(body['job'])['ended_at'] is not None:
                    archive.h.reports.freeze(body['job'], reason='Originaldatei manuell zugeordnet')
            else: raise ValueError('Unbekannte Archivaktion.')
            return web.json_response({'ok':True})
        except (ValueError, TypeError) as exc: return web.json_response({'error':str(exc)}, status=400)

    async def heartbeat(request):
        client = machine_client(request, archive)
        if not client: return web.json_response({'error':'Computerzugang ungültig.'}, status=401)
        try:
            body = await request.json(); archive.heartbeat(client, body.get('state'))
            return web.json_response({'ok':True})
        except (ValueError, TypeError, AttributeError): return web.json_response({'error':'Ungültiger Status.'}, status=400)

    async def ingest(request):
        client = machine_client(request, archive)
        if not client: return web.json_response({'error':'Computerzugang ungültig.'}, status=401)
        if upload_lock.locked(): return web.json_response({'error':'Andere Übertragung läuft. Bitte später wiederholen.'}, status=429)
        temporary = None
        async with upload_lock:
            try:
                size = int(request.headers.get('X-Kobra-Size','0'))
                if not 0 < size <= MAX_FILE or request.content_length != size or request.content_type != 'application/octet-stream': raise ValueError('Dateigröße oder Übertragungsformat ungültig.')
                name = filename(base64.b64decode(request.headers.get('X-Kobra-Filename',''), altchars=b'-_', validate=True).decode('utf-8'))
                fd, temporary = tempfile.mkstemp(suffix='.part', dir=archive.incoming)
                with os.fdopen(fd, 'wb') as stream:
                    received = 0
                    async with asyncio.timeout(180):
                        async for chunk in request.content.iter_chunked(256*1024):
                            received += len(chunk)
                            if received > size: raise ValueError('Datei überschreitet die angegebene Größe.')
                            stream.write(chunk)
                        stream.flush(); os.fsync(stream.fileno())
                task = asyncio.create_task(asyncio.to_thread(archive.receive, temporary, name, request.headers.get('X-Kobra-SHA256',''), size, client))
                try:
                    result = await asyncio.shield(task)
                except asyncio.CancelledError:
                    await task
                    raise
                return web.json_response(result)
            except (ValueError, UnicodeError, TimeoutError) as exc: return web.json_response({'error':str(exc)}, status=400)
            except OSError: return web.json_response({'error':'Original konnte nicht dauerhaft gespeichert werden.'}, status=507)
            finally:
                if temporary and os.path.exists(temporary): os.unlink(temporary)

    async def original(request):
        try:
            sha = request.query.get('sha256'); path = object_path(archive.root, sha)
            with archive.h.lock:
                exists = archive.h.db.execute('SELECT 1 FROM archived_print_files WHERE sha256=?', (sha,)).fetchone()
            if not exists or not path.is_file() or path.is_symlink() or await asyncio.to_thread(digest, path) != sha: raise ValueError('Geprüftes Original nicht verfügbar.')
            # App-owned filename avoids header injection and platform ambiguity.
            return web.FileResponse(path, headers={'Content-Type':'application/octet-stream', 'Content-Disposition':f'attachment; filename="{sha}.gcode.3mf"'})
        except ValueError as exc: return web.json_response({'error':str(exc)}, status=404)

    app.router.add_get('/api/archive', catalog)
    app.router.add_post('/api/archive', catalog)
    app.router.add_get('/api/archive/original', original)
    app.router.add_post('/api/archive/heartbeat', heartbeat)
    app.router.add_post('/api/archive/ingest', ingest)
    async def javascript(request): return web.FileResponse(base/'static/file-archive.js')
    app.router.add_get('/assets/file-archive.js', javascript)
