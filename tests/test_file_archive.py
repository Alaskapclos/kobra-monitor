import asyncio,base64,hashlib,importlib.util,io,json,os,sqlite3,sys,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from history import History
from file_archive import digest,validate_package,object_path,verify_catalog
from access import Access
from backup import create,restore
from configuration import save_config
from monitor import build_app
from aiohttp.test_utils import make_mocked_request

spec=importlib.util.spec_from_file_location('archive_client',Path(__file__).resolve().parent.parent/'helpers/archive_client.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def package(value=b'G1 X1\n'):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        # Identical fixture bytes even when a test crosses a ZIP timestamp boundary.
        for name,body in (('[Content_Types].xml','<Types/>'),('Metadata/plate_1.gcode',value)):
            info=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,body)
    return out.getvalue()

class FileArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.h=History(self.root/'data/history.sqlite3');self.a=self.h.files
        self.token=self.a.new_client('Fixture computer');self.client=self.a.authenticate(self.token)
    def tearDown(self):self.h.close();self.temp.cleanup()
    def receive(self,data=None,name='test.gcode.3mf',expected=None):
        data=data or package();path=self.a.incoming/'fixture.part';path.write_bytes(data)
        return self.a.receive(path,name,expected or hashlib.sha256(data).hexdigest(),len(data),self.client)
    def test_verified_idempotent_and_same_name_different_contents(self):
        first=self.receive();self.receive();self.receive(package(b'G1 X2\n'))
        files=self.a.listing()['files'];self.assertEqual(len(files),2);self.assertTrue(first['verified'])
        self.assertEqual(object_path(self.root/'data',first['sha256']).read_bytes(),package())
        self.assertNotIn(self.token,json.dumps(self.a.listing()))
        self.assertNotIn(self.token,self.h.db.execute('SELECT key_hash FROM file_archive_clients').fetchone()[0])
    def test_partial_corruption_and_invalid_zip_never_enter_catalog(self):
        for data,expected in [(b'partial','a'*64),(b'not zip',None),(package(),'b'*64)]:
            with self.assertRaises(ValueError):self.receive(data,expected=expected)
        self.assertEqual(self.a.listing()['files'],[])
    def test_zip_traversal_duplicate_and_unsliced_rejected(self):
        for entries in [[('[Content_Types].xml',b'x'),('../x.gcode',b'x')],[('[Content_Types].xml',b'x'),('a.gcode',b'x'),('a.gcode',b'y')],[('[Content_Types].xml',b'x'),('3D/a.model',b'x')]]:
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w') as z:
                for name,data in entries:z.writestr(name,data)
            with self.assertRaises(ValueError):self.receive(out.getvalue())
    def test_unsafe_filename_revocation_and_quota(self):
        for name in ['../x.gcode.3mf','x\n.gcode.3mf','x.gcode','a\\x.gcode.3mf']:
            with self.assertRaises(ValueError):self.receive(name=name)
        self.a.max_total=1
        with self.assertRaises(ValueError):self.receive()
        self.a.max_total=100000;self.a.revoke(self.client);self.assertIsNone(self.a.authenticate(self.token))
        with self.assertRaises(ValueError):self.receive()
    def test_corrupted_existing_original_fails_closed(self):
        r=self.receive();object_path(self.root/'data',r['sha256']).write_bytes(b'changed')
        with self.assertRaises(ValueError):self.receive()
        with self.assertRaises(ValueError):verify_catalog(self.h.db,self.root/'data')
    def test_report_link_creates_new_immutable_version_and_keeps_evidence_distinct(self):
        self.h.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',('a'*32,'192.168.1.2','1','test.gcode.3mf','finished',10,20,20,1,100,1,1,1));self.h.db.commit()
        self.h.reports.freeze('a'*32);old=self.h.reports.export('a'*32,1,'json')[0]
        r=self.receive();self.a.link('a'*32,r['sha256']);self.h.reports.freeze('a'*32,'Originaldatei manuell zugeordnet')
        result=json.loads(self.h.reports.export('a'*32,2,'json')[0]);self.assertEqual(result['original']['sha256'],r['sha256'])
        self.assertIn('nicht unabhängig belegt',result['limits'][-1]);self.assertEqual(old,self.h.reports.export('a'*32,1,'json')[0])
        self.assertEqual(self.h.reports.freeze('a'*32),2)
    def test_full_backup_restores_original_client_hash_and_ignores_partial(self):
        save_config(self.root/'data',['192.168.1.2']);Access(self.root/'data');r=self.receive();(self.a.incoming/'left.part').write_bytes(b'partial')
        archive=create(self.root/'data',self.root/'backups','fixture');target=self.root/'restored';restore(archive,target)
        self.assertEqual(object_path(target,r['sha256']).read_bytes(),package());self.assertFalse((target/'.archive-incoming').exists())
        restored=History(target/'history.sqlite3')
        try:self.assertEqual(restored.files.authenticate(self.token),self.client)
        finally:restored.close()
    def test_backup_takes_catalog_snapshot_before_new_immutable_objects(self):
        save_config(self.root/'data',['192.168.1.2']);Access(self.root/'data');self.receive()
        import shutil
        real=shutil.copyfile;inserted=[]
        def during_copy(src,dst,*args,**kw):
            if not inserted:inserted.append(True);self.receive(package(b'G1 X9'))
            return real(src,dst,*args,**kw)
        with patch('backup.shutil.copyfile',side_effect=during_copy):archive=create(self.root/'data',self.root/'backups','fixture')
        target=self.root/'restored';restore(archive,target);db=sqlite3.connect(target/'history.sqlite3')
        try:self.assertEqual(db.execute('SELECT count(*) FROM archived_print_files').fetchone()[0],1)
        finally:db.close()

class CollectorTests(unittest.TestCase):
    def test_future_complete_file_is_durable_and_survives_source_deletion(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'cache';source.mkdir();(source/'old.gcode.3mf').write_bytes(package())
            c=helper.Collector(source,root/'queue');c.scan();c.scan();self.assertEqual(c.status()['pending'],0)
            new=source/'new.gcode.3mf';new.write_bytes(b'partial');c.scan();c.scan();self.assertEqual(c.status()['pending'],0)
            new.write_bytes(package(b'G1 X3'));c.scan();c.scan();self.assertEqual(c.status()['pending'],1)
            new.unlink();self.assertEqual(len(list((root/'queue').glob('*.gcode.3mf'))),1)
            c.db.close();other=helper.Collector(source,root/'queue');self.assertEqual(other.status()['pending'],1);other.db.close()
    def test_missing_or_wrong_ack_keeps_pending_original(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'cache';source.mkdir();c=helper.Collector(source,root/'queue')
            (source/'new.gcode.3mf').write_bytes(package());c.scan();c.scan()
            bad=SimpleNamespace(open=lambda *a,**kw:io.BytesIO(b'{"verified":true,"sha256":"wrong","size":1}'))
            with self.assertRaises(ValueError):c.send_one(bad,'http://127.0.0.1','x'*43)
            self.assertEqual(c.status()['pending'],1);self.assertEqual(len(list((root/'queue').glob('*.gcode.3mf'))),1);c.db.close()
    def test_config_refuses_remote_http_userinfo_redirect(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'config.json'
            for url in ['http://8.8.8.8','https://user:password@example.com','https://example.com/path']:
                p.write_text(json.dumps({'format':'kobra-archive-client-v1','base_url':url,'token':'x'*43}))
                with self.assertRaises(ValueError):helper.read_config(p)
        with self.assertRaises(ValueError):helper.NoRedirect().redirect_request(None,None,302,'',{},'https://other.invalid')

class FileArchiveBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_machine_key_cannot_read_catalog_or_send_printer_commands(self):
        with tempfile.TemporaryDirectory() as t:
            h=History(Path(t)/'history.sqlite3');access=Access(t);access.account={'username':'fixture'}
            app=build_app(SimpleNamespace(history=h,start=AsyncMock(),stop=AsyncMock()),access);token=h.files.new_client('fixture')
            async def call(method,path,body=None,headers=None):
                request=make_mocked_request(method,path,headers={'Host':'localhost','Authorization':'Bearer '+token,**(headers or {})});request.json=AsyncMock(return_value=body or {})
                match=await app.router.resolve(request);return await app.middlewares[0](request,match.handler)
            try:
                self.assertEqual((await call('POST','/api/archive/heartbeat',{'state':'ready'})).status,200)
                for path in ['/api/archive','/api/archive/original?sha256='+'a'*64,'/api/status']:
                    self.assertEqual((await call('GET',path)).status,401)
                self.assertEqual((await call('POST','/api/controls',{'control':'light'})).status,401)
                self.assertEqual((await call('POST','/api/archive',{'action':'pair','name':'other'})).status,401)
                self.assertEqual((await call('POST','/api/archive/heartbeat',{'state':'ready'},{'Origin':'http://localhost'})).status,401)
            finally:h.close()

class FileArchiveOwnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_pairing_requires_owner_csrf_and_matching_origin(self):
        with tempfile.TemporaryDirectory() as t:
            h=History(Path(t)/'history.sqlite3');access=Access(t);access.account={'username':'fixture'}
            access.sessions['fixture-session']={'expires':access.clock()+100,'csrf':'fixture-csrf'}
            app=build_app(SimpleNamespace(history=h,start=AsyncMock(),stop=AsyncMock()),access)
            async def call(headers):
                request=make_mocked_request('POST','/api/archive',headers={'Host':'localhost','Cookie':'kobra_session=fixture-session',**headers});request.json=AsyncMock(return_value={'action':'pair','name':'Fixture computer'})
                match=await app.router.resolve(request);return await app.middlewares[0](request,match.handler)
            try:
                self.assertEqual((await call({})).status,403)
                self.assertEqual((await call({'Origin':'https://evil.invalid','X-Kobra-CSRF':'fixture-csrf'})).status,403)
                response=await call({'Origin':'https://localhost','X-Kobra-CSRF':'fixture-csrf'})
                self.assertEqual(response.status,200);config=json.loads(response.text)
                self.assertEqual(config['base_url'],'https://localhost');self.assertIsNotNone(h.files.authenticate(config['token']));self.assertEqual(response.headers['Cache-Control'],'no-store')
                self.assertEqual(h.db.execute('SELECT count(*) FROM file_archive_clients').fetchone()[0],1)
            finally:h.close()

class FileArchiveHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stream_upload_retry_download_and_ingest_only_scope(self):
        from aiohttp.test_utils import TestClient,TestServer
        from accounts import write_account
        import urllib.request
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);data=root/'data';data.mkdir();write_account(data,'fixture','A long fixture passphrase 2026!')
            h=History(data/'history.sqlite3');access=Access(data)
            app=build_app(SimpleNamespace(history=h,start=AsyncMock(),stop=AsyncMock()),access)
            client=TestClient(TestServer(app));await client.start_server();c=None
            try:
                token=h.files.new_client('isolated');source=root/'source';source.mkdir();c=helper.Collector(source,root/'queue')
                # Random content exceeds the ordinary 8-KB JSON boundary.
                original=package(os.urandom(24000));(source/'ready.gcode.3mf').write_bytes(original);c.scan();c.scan()
                base=str(client.make_url('/')).rstrip('/');opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),helper.NoRedirect())
                self.assertTrue(await asyncio.to_thread(c.send_one,opener,base,token));self.assertEqual(c.status()['pending'],0)
                sha=hashlib.sha256(original).hexdigest()
                self.assertEqual((await client.get('/api/archive/original?sha256='+sha,headers={'Authorization':'Bearer '+token})).status,401)
                response=await client.post('/api/session',json={'username':'fixture','password':'A long fixture passphrase 2026!'},headers={'Origin':base})
                self.assertEqual(response.status,200);cookie=response.cookies['kobra_session'].value
                response=await client.get('/api/archive/original?sha256='+sha,headers={'Cookie':'kobra_session='+cookie})
                self.assertEqual(response.status,200);self.assertEqual(await response.read(),original)
                self.assertTrue(response.headers['Content-Disposition'].startswith('attachment;'))
            finally:
                if c is not None:c.db.close()
                await client.close();h.close()
