import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from suite.bundle import verify_pair, assemble, digest


class SuiteBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.files={'VERSION':b'0.32.0-alpha.1\n','LICENSE':b'fixture GPL text',
                    'NOTICE.md':b'fixture notice'}
        build={'version':'0.32.0-alpha.1','source_sha256':{
            n:hashlib.sha256(b).hexdigest() for n,b in self.files.items()}}
        self.files['BUILD.json']=json.dumps(build).encode()
        self.source=self.root/'source.zip'
        with zipfile.ZipFile(self.source,'w') as z:
            for name,body in self.files.items():z.writestr('Kobra-Monitor/'+name,body)
        self.archive=self.root/'monitor.tar'
        self.image()

    def tearDown(self):self.temp.cleanup()

    def image(self, *, revision=None, platform='amd64', changed=None, whiteout=False):
        config={'os':'linux','architecture':platform,'config':{'Labels':{
            'org.opencontainers.image.revision':revision or 'local-'+digest(self.source)[:20]}}}
        config_bytes=json.dumps(config).encode()
        config_name=hashlib.sha256(config_bytes).hexdigest()+'.json'
        layer=io.BytesIO()
        with tarfile.open(fileobj=layer,mode='w') as t:
            for name,body in {**self.files,**(changed or {})}.items():
                info=tarfile.TarInfo('app/'+name);info.size=len(body);t.addfile(info,io.BytesIO(body))
            if whiteout:
                info=tarfile.TarInfo('app/.wh.VERSION');info.size=0;t.addfile(info,io.BytesIO())
        manifest=[{'RepoTags':['kobra-monitor:0.32.0-alpha.1'],'Config':config_name,'Layers':['layer.tar']}]
        with tarfile.open(self.archive,'w') as t:
            for name,body in [('manifest.json',json.dumps(manifest).encode()),(config_name,config_bytes),('layer.tar',layer.getvalue())]:
                info=tarfile.TarInfo(name);info.size=len(body);t.addfile(info,io.BytesIO(body))

    def test_exact_pair_assembles_installer_sources_and_notices(self):
        proof=verify_pair(self.archive,self.source)
        self.assertEqual(proof['app_files_verified'],4)
        self.assertEqual(proof['image_sha256'],digest(self.archive))
        target=self.root/'package'
        result=assemble(self.archive,self.source,target)
        self.assertFalse(result['signed_release'])
        self.assertFalse(result['offline_complete'])
        self.assertEqual((target/'LICENSE').read_bytes(),self.files['LICENSE'])
        self.assertEqual(digest(target/'monitor-linux-amd64.tar'),proof['image_sha256'])
        self.assertEqual(digest(target/'Quellcode.zip'),digest(self.source))
        self.assertIn('--no-recreate',(target/'Installieren.sh').read_text())
        with self.assertRaises(FileExistsError):assemble(self.archive,self.source,target)

    def test_wrong_source_revision_platform_or_changed_image_file_is_rejected(self):
        for args in [{'revision':'local-other-source'}, {'platform':'arm64'},
                     {'changed':{'VERSION':b'changed'}},{'whiteout':True}]:
            self.image(**args)
            with self.assertRaises(ValueError):verify_pair(self.archive,self.source)

    def test_corrupt_source_file_never_creates_a_package(self):
        with zipfile.ZipFile(self.source,'w') as z:
            for name,body in self.files.items():
                z.writestr('Kobra-Monitor/'+name,b'changed' if name=='LICENSE' else body)
        self.image()
        with self.assertRaises(ValueError):assemble(self.archive,self.source,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())
