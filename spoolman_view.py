# SPDX-License-Identifier: GPL-3.0-only
"""Authenticated gateway to the original, unmodified Spoolman web application."""
import asyncio
from urllib.parse import unquote, urlsplit
import aiohttp
from aiohttp import web
from yarl import URL
from spools import local_url

PREFIX = '/spoolman'
MAX_BODY = 16 * 1024 * 1024
MAX_RESPONSE = 32 * 1024 * 1024


def gateway_path(path):
    return path == PREFIX or path.startswith(PREFIX + '/')


def safe_path(raw):
    path = raw.split('?', 1)[0]
    # Reject ambiguous path encodings rather than normalizing across the boundary.
    for _ in range(3):
        decoded = unquote(path)
        if '\\' in decoded or any(p in ('.', '..') for p in decoded.split('/')):
            return False
        if decoded == path:
            return gateway_path(decoded)
        path = decoded
    return False


def allowed_browser_write(request):
    origin = request.headers.get('Origin', '')
    try:
        parsed = urlsplit(origin)
        return (parsed.scheme in ('http', 'https') and parsed.netloc == request.host
                and not parsed.path and not parsed.query and not parsed.fragment
                and request.headers.get('Sec-Fetch-Site') != 'cross-site')
    except ValueError:
        return False


async def gateway(request, service, access):
    if access is None or not access.session(request) or access.account is None:
        return web.json_response({'error': 'Bitte im Monitor anmelden.'}, status=401)
    if not safe_path(request.raw_path):
        return web.Response(status=403)
    websocket = request.headers.get('Upgrade', '').lower() == 'websocket'
    writing = request.method not in ('GET', 'HEAD')
    if request.method not in ('GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'):
        return web.Response(status=403)
    if (writing or websocket) and not allowed_browser_write(request):
        return web.json_response({'error': 'Spoolman bitte aus dem Monitor öffnen.'}, status=403)
    if writing and not request.path.startswith(PREFIX + '/api/v1/'):
        return web.Response(status=403)
    try:
        configured = local_url(getattr(service, 'url', ''))
        upstream = urlsplit(configured)
        if upstream.path != PREFIX:
            return web.json_response({'error': 'Die integrierte Spoolman-Ansicht ist noch nicht eingerichtet.'}, status=503)
        origin = f'{upstream.scheme}://{upstream.netloc}'
        target = URL(origin + request.raw_path, encoded=True)
        headers = {k: request.headers[k] for k in ('Accept', 'Content-Type', 'Range', 'If-None-Match') if k in request.headers}
        if writing or websocket:
            headers['Origin'] = origin
        timeout = aiohttp.ClientTimeout(total=45, connect=8)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=False, cookie_jar=aiohttp.DummyCookieJar()) as client:
            if websocket:
                async with client.ws_connect(target, headers=headers, max_msg_size=4*1024*1024) as remote:
                    socket = web.WebSocketResponse(max_msg_size=4*1024*1024)
                    await socket.prepare(request)
                    async def relay(source, destination):
                        async for message in source:
                            if not access.session(request): break
                            if message.type == aiohttp.WSMsgType.TEXT:
                                await destination.send_str(message.data)
                            elif message.type == aiohttp.WSMsgType.BINARY:
                                await destination.send_bytes(message.data)
                            elif message.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                                break
                    tasks = [asyncio.create_task(relay(socket, remote)), asyncio.create_task(relay(remote, socket))]
                    try:
                        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    finally:
                        for task in tasks: task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
                        await socket.close()
                    return socket
            if request.content_length is not None and request.content_length > MAX_BODY:
                return web.Response(status=413)
            body = bytearray()
            async for chunk in request.content.iter_chunked(65536):
                body.extend(chunk)
                if len(body) > MAX_BODY: return web.Response(status=413)
            async with client.request(request.method, target, headers=headers, data=bytes(body) if writing else None,
                                      allow_redirects=False) as response:
                result = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    result.extend(chunk)
                    if len(result) > MAX_RESPONSE: return web.Response(status=502, text='Spoolman-Antwort zu groß.')
                outgoing = {k: response.headers[k] for k in ('Content-Type', 'Content-Disposition', 'ETag', 'Content-Range', 'Accept-Ranges', 'X-Total-Count') if k in response.headers}
                location = response.headers.get('Location')
                if location:
                    redirected = urlsplit(location)
                    if (redirected.netloc and (redirected.scheme, redirected.netloc) != (upstream.scheme, upstream.netloc)) or not safe_path(redirected.path):
                        return web.Response(status=502, text='Spoolman-Weiterleitung außerhalb der Ansicht gesperrt.')
                    outgoing['Location'] = redirected.path + ('?' + redirected.query if redirected.query else '')
                return web.Response(status=response.status, body=bytes(result), headers=outgoing)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, UnicodeError):
        return web.json_response({'error': 'Spoolman ist gerade nicht erreichbar. Bitte später erneut laden.'}, status=502)
