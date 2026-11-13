# SPDX-License-Identifier: GPL-3.0-only
"""Single-attempt, bounded S1 original transfer. No generic URL/file upload API.

This module never starts a print. A successful HTTP response only acknowledges
storage; it is neither proof of remote content integrity nor a print receipt.
"""
import asyncio
import hashlib
import ipaddress
import json
import re
import stat
import uuid
from urllib.parse import parse_qs, urlsplit

import aiohttp
from file_archive import MAX_FILE, SHA


class TransferUncertain(ValueError):
    """Bytes may have reached the printer. Never retry this operation implicitly."""


def remote_name(operation):
    if not isinstance(operation, str) or not re.fullmatch('[a-f0-9]{32}', operation):
        raise ValueError('Ungültige Übertragungskennung.')
    # Unique per attempt: never overwrite a similarly named slicer upload.
    return 'KM_' + operation + '.gcode.3mf'


def upload_endpoint(ip, reported_url):
    """Accept only the configured literal IPv4 printer and the known LAN route."""
    host = ipaddress.IPv4Address(ip)
    if host.is_multicast or host.is_unspecified: raise ValueError('Ungültiger Zieldrucker.')
    try:
        url = urlsplit(reported_url)
        query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
        if (url.scheme != 'http' or url.netloc != f'{ip}:18910' or
                url.hostname != str(host) or url.path != '/gcode_upload' or
                url.fragment or set(query) != {'s'} or len(query['s']) != 1 or
                not re.fullmatch('[A-Za-z0-9_-]{1,256}', query['s'][0])):
            raise ValueError()
        return f'http://{ip}:18910/gcode_upload?s={query["s"][0]}'
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Drucker meldet keinen unterstützten lokalen Uploadzugang.') from exc


async def upload_original(path, sha256, operation, *, ip, reported_url, guard,
                          enabled=False, progress=None, session_factory=aiohttp.ClientSession):
    """Stream the immutable original once; guards are checked before each chunk.

    The coordinator persists 'uploading' BEFORE calling this function. It must
    regard every exception/cancellation after that point as uncertain. No
    credentials or raw printer response bodies escape into diagnostics.
    """
    if enabled is not True: raise PermissionError('Archivübertragung nicht freigegeben.')
    if not callable(guard) or not isinstance(sha256, str) or not SHA.fullmatch(sha256):
        raise ValueError('Geprüftes Archivoriginal und frischer Druckerzustand erforderlich.')
    name = remote_name(operation); endpoint = upload_endpoint(ip, reported_url)
    if not guard(): raise ValueError('Druckerzustand hat sich geändert; keine Übertragung.')
    # O_NOFOLLOW protects the final component; the parent is app-owned archive storage.
    import os
    if stat.S_ISLNK(os.lstat(path).st_mode): raise ValueError('Archivoriginal darf kein Dateilink sein.')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_FILE:
            raise ValueError('Archivoriginal fehlt oder überschreitet das Größenlimit.')
        digest = hashlib.sha256(); md5 = hashlib.md5(usedforsecurity=False)
        for chunk in iter(lambda: stream.read(256 * 1024), b''):
            digest.update(chunk); md5.update(chunk)
        if digest.hexdigest() != sha256: raise ValueError('Originalprüfsumme stimmt nicht.')
        stream.seek(0)
        boundary = 'kobra-' + uuid.uuid4().hex
        prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="filename"\r\n\r\n{name}\r\n'
                  f'--{boundary}\r\nContent-Disposition: form-data; name="gcode"; filename="{name}"\r\n'
                  'Content-Type: application/octet-stream\r\n\r\n').encode()
        suffix = f'\r\n--{boundary}--\r\n'.encode()
        headers = {'Content-Type':f'multipart/form-data; boundary={boundary}',
                   'Content-Length':str(len(prefix) + before.st_size + len(suffix)),
                   'X-File-Length':str(before.st_size), 'User-Agent':'AnycubicSlicerNext/1.3.9.4',
                   'X-BBL-Client-Name':'AnycubicSlicerNext','X-BBL-Client-Type':'slicer',
                   'X-BBL-Client-Version':'01.03.09.04'}
        streamed = hashlib.sha256(); sent = 0; validated = False

        async def body():
            nonlocal sent, validated
            if not guard(): raise TransferUncertain('Druckerzustand geändert; nicht fortgesetzt.')
            yield prefix
            while True:
                if not guard(): raise TransferUncertain('Druckerzustand geändert; nicht fortgesetzt.')
                chunk = stream.read(256 * 1024)
                if not chunk: break
                sent += len(chunk)
                if sent > before.st_size: raise TransferUncertain('Original während der Übertragung geändert.')
                streamed.update(chunk)
                yield chunk
                if progress: progress(sent, before.st_size)
                await asyncio.sleep(0)
            after = os.fstat(stream.fileno())
            if (sent != before.st_size or streamed.hexdigest() != sha256 or
                    (after.st_mtime_ns,after.st_size) != (before.st_mtime_ns,before.st_size)):
                raise TransferUncertain('Original während der Übertragung geändert.')
            if not guard(): raise TransferUncertain('Druckerzustand geändert; nicht fortgesetzt.')
            validated = True
            yield suffix

        try:
            timeout = aiohttp.ClientTimeout(total=120, connect=5, sock_read=15)
            async with session_factory(timeout=timeout, trust_env=False) as session:
                async with session.post(endpoint, data=body(), headers=headers, allow_redirects=False) as response:
                    if response.status != 200:
                        raise TransferUncertain('Drucker hat die Übertragung nicht bestätigt.')
                    raw = bytearray()
                    async for chunk in response.content.iter_chunked(4096):
                        raw.extend(chunk)
                        if len(raw) > 65536:
                            raise TransferUncertain('Druckerantwort überschreitet das Prüflimit.')
                    def unique(items):
                        values={}
                        for key,value in items:
                            if key in values:raise ValueError('Mehrdeutige Antwort.')
                            values[key]=value
                        return values
                    result = json.loads(raw,object_pairs_hook=unique)
                    if (not validated or sent != before.st_size or streamed.hexdigest() != sha256 or
                            not isinstance(result,dict) or type(result.get('code')) is not int or result['code'] != 200 or
                            not isinstance(result.get('data'),dict) or result['data'].get('gcode') != name):
                        raise TransferUncertain('Speicherung unter der erwarteten Kennung nicht bestätigt.')
                    return {'remote_filename':name, 'sha256':sha256, 'bytes':sent,
                            'md5':md5.hexdigest(), 'storage_acknowledged':True,
                            'remote_hash_verified':False, 'print_started':False}
        except asyncio.CancelledError:
            raise
        except (aiohttp.ClientError, OSError, ValueError, TimeoutError) as exc:
            raise TransferUncertain('Übertragung nicht eindeutig bestätigt. Nicht automatisch wiederholen; Druckerdateien prüfen.') from None
