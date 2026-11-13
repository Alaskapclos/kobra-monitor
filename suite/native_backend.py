# SPDX-License-Identifier: GPL-3.0-only
"""Keep a native loopback Spoolman backend private to its owning Monitor.

The upstream Spoolman application is not modified. Lifespan events pass through.
The secret belongs to the local supervisor and is never a browser credential.
"""
import hmac
import os
import re
from urllib.parse import urlsplit

HEADER = 'Authorization'


def internal_headers(url, environment=None):
    env = os.environ if environment is None else environment
    target = env.get('KOBRA_NATIVE_SPOOLMAN_URL', '')
    secret = env.get('KOBRA_NATIVE_SPOOLMAN_TOKEN', '')
    if url != target or not re.fullmatch('[a-f0-9]{64}', secret):
        return {}
    try:
        parsed = urlsplit(target)
        if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or
                parsed.path != '/spoolman' or parsed.username or parsed.password or
                parsed.query or parsed.fragment or not 1024 <= (parsed.port or 0) <= 65535):
            return {}
    except ValueError:
        return {}
    # Standard Authorization is stripped by aiohttp on a cross-origin redirect,
    # including during WebSocket handshakes. Never invent a forwarding header.
    return {HEADER: 'Bearer ' + secret}


class PrivateBackend:
    def __init__(self, app, secret):
        if not isinstance(secret, str) or not re.fullmatch('[a-f0-9]{64}', secret):
            raise ValueError('Der interne Backend-Zugang fehlt.')
        self.app, self.secret = app, ('Bearer ' + secret).encode('ascii')

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            return await self.app(scope, receive, send)
        tokens = [value for key, value in scope.get('headers', []) if key.lower() == HEADER.lower().encode()]
        if len(tokens) != 1 or not hmac.compare_digest(tokens[0], self.secret):
            if scope['type'] == 'websocket':
                await send({'type': 'websocket.close', 'code': 1008})
            else:
                await send({'type': 'http.response.start', 'status': 401,
                            'headers': [(b'content-type', b'application/json'), (b'cache-control', b'no-store')]})
                await send({'type': 'http.response.body', 'body': b'{"error":"Monitor access required"}'})
            return
        return await self.app(scope, receive, send)


def create_application():
    from spoolman.main import app
    return PrivateBackend(app, os.environ.get('KOBRA_NATIVE_SPOOLMAN_TOKEN', ''))
