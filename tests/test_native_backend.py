import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from suite.native_backend import PrivateBackend, internal_headers, HEADER
from spools import Spools


class NativeBackendTests(unittest.IsolatedAsyncioTestCase):
    async def call(self, kind='http', tokens=()):
        messages=[];passed=[]
        async def application(scope,receive,send):passed.append(scope['type'])
        async def receive():return {'type':'lifespan.startup'}
        async def send(item):messages.append(item)
        backend=PrivateBackend(application,'a'*64)
        await backend({'type':kind,'headers':[(HEADER.lower().encode(),t) for t in tokens]},receive,send)
        return messages,passed

    async def test_http_backend_refuses_missing_wrong_and_duplicate_credentials(self):
        for tokens in [(),(b'wrong',),(b'a'*64,b'a'*64)]:
            result,passed=await self.call(tokens=tokens)
            self.assertEqual(result[0]['status'],401)
            self.assertEqual(passed,[])
            self.assertNotIn(b'a'*64,result[-1]['body'])
        result,passed=await self.call(tokens=(b'Bearer '+b'a'*64,))
        self.assertEqual((result,passed),([],['http']))

    async def test_websocket_auth_and_lifespan_migrations(self):
        result,passed=await self.call('websocket')
        self.assertEqual(result,[{'type':'websocket.close','code':1008}])
        self.assertEqual(passed,[])
        self.assertEqual((await self.call('websocket',(b'Bearer '+b'a'*64,)))[1],['websocket'])
        self.assertEqual((await self.call('lifespan'))[1],['lifespan'])

    def test_secret_never_follows_a_changed_backend_or_external_server(self):
        url='http://127.0.0.1:17136/spoolman'
        env={'KOBRA_NATIVE_SPOOLMAN_URL':url,'KOBRA_NATIVE_SPOOLMAN_TOKEN':'a'*64}
        self.assertEqual(internal_headers(url,env),{HEADER:'Bearer '+'a'*64})
        for other in ['http://192.168.1.20:8000/spoolman','http://localhost:17136/spoolman',
                      'http://127.0.0.1:17137/spoolman',url+'/api/v1']:
            self.assertEqual(internal_headers(other,env),{})
        for bad in ['http://example.com:8000/spoolman','http://u:p@127.0.0.1:8000/spoolman']:
            self.assertEqual(internal_headers(bad,{**env,'KOBRA_NATIVE_SPOOLMAN_URL':bad}),{})

    def test_native_secret_is_not_serialized_in_spool_state(self):
        with tempfile.TemporaryDirectory() as folder:
            service=Spools(folder);service.url='http://127.0.0.1:17136/spoolman'
            env={'KOBRA_NATIVE_SPOOLMAN_URL':service.url,'KOBRA_NATIVE_SPOOLMAN_TOKEN':'a'*64}
            with patch.dict('os.environ',env):
                self.assertEqual(service.backend_headers(),{HEADER:'Bearer '+'a'*64})
                self.assertNotIn('a'*64,json.dumps(service.state()))
