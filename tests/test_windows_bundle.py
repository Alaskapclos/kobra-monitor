import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from suite.windows_bundle import members, pe_machine, wheel_record, extract_python, ARM_UNUSED_DLL, ARM_UNUSED_DLL_SHA, pe_imports
from desktop_entry import load_manifest


def wheel(tag='py3-none-any', changed=False):
    prefix='fixture-1.0.dist-info/'
    files={'fixture.py':b'VALUE = 1\n',prefix+'METADATA':b'Name: fixture\nVersion: 1.0\n',
           prefix+'WHEEL':('Wheel-Version: 1.0\nTag: '+tag+'\n').encode()}
    stream=io.StringIO();writer=csv.writer(stream)
    for name,body in files.items():
        sha=base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b'=').decode()
        writer.writerow([name,'sha256='+sha,len(body)])
    writer.writerow([prefix+'RECORD','',''])
    files[prefix+'RECORD']=stream.getvalue().encode()
    if changed:files['fixture.py']=b'changed'
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        for name,body in files.items():archive.writestr(name,body)
    output.seek(0)
    return zipfile.ZipFile(output)


class WindowsBundleTests(unittest.TestCase):
    def test_wheel_record_verifies_contents_and_target(self):
        with wheel() as archive:self.assertEqual(wheel_record(archive)['name'],'fixture')
        for options in ({'changed':True},{'tag':'cp314-cp314-manylinux_2_28_x86_64'}):
            with wheel(**options) as archive:
                with self.assertRaises(ValueError):wheel_record(archive)

    def test_unsafe_and_case_colliding_archives_are_rejected(self):
        for names in [['../escape'],['A.txt','a.txt']]:
            body=io.BytesIO()
            with zipfile.ZipFile(body,'w') as archive:
                for name in names:archive.writestr(name,b'fixture')
            body.seek(0)
            with zipfile.ZipFile(body) as archive:
                with self.assertRaises(ValueError):members(archive)

    def test_pe_machine_reads_architecture_and_rejects_bad_header(self):
        body=bytearray(128);body[:2]=b'MZ';struct.pack_into('<I',body,0x3c,64)
        body[64:68]=b'PE\0\0';struct.pack_into('<H',body,68,0x8664)
        self.assertEqual(pe_machine(body),0x8664)
        for value in (b'',b'MZ'+b'\xff'*126):
            with self.assertRaises(ValueError):pe_machine(value)

    def test_installer_checks_every_file_and_rejects_traversal_version(self):
        with tempfile.TemporaryDirectory() as folder, patch('desktop_entry.runtime_architecture', return_value='x86_64'):
            root=Path(folder);files={}
            for n in range(12):
                name=f'app/{n}.py';path=root/name;path.parent.mkdir(exist_ok=True)
                path.write_bytes(b'fixture');files[name]=hashlib.sha256(b'fixture').hexdigest()
            manifest={'format':'kobra-windows-test-bundle-v1','platform':'windows-x86_64',
                      'version':'0.33.0-alpha.1','bundle_id':'a'*64,'files':files}
            target=root/'native-bundle.json';target.write_text(json.dumps(manifest))
            self.assertEqual(load_manifest(root,verify=True)['version'],manifest['version'])
            (root/'app/0.py').write_bytes(b'changed')
            with self.assertRaises(ValueError):load_manifest(root,verify=True)
            manifest['version']='../../other';target.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):load_manifest(root)

    def test_manifest_requires_interpreter_architecture(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);files={}
            for index in range(12):
                name=f'app/{index}.py';p=root/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b'fixture')
                files[name]=hashlib.sha256(b'fixture').hexdigest()
            for bundle_arch in ('arm64','x86_64'):
                data={'format':'kobra-windows-test-bundle-v1','platform':'windows-'+bundle_arch,
                      'version':'0.41.0-alpha.1','bundle_id':'a'*64,'files':files}
                (root/'native-bundle.json').write_text(json.dumps(data))
                for process_arch in ('arm64','x86_64'):
                    with patch('desktop_entry.runtime_architecture',return_value=process_arch):
                        if bundle_arch==process_arch:self.assertEqual(load_manifest(root,verify=True)['platform'],'windows-'+process_arch)
                        else:
                            with self.assertRaises(ValueError):load_manifest(root,verify=True)

    def test_normal_and_delayed_imports_are_both_checked(self):
        body=bytearray(1024);body[:2]=b'MZ';struct.pack_into('<I',body,60,64)
        body[64:68]=b'PE\0\0';struct.pack_into('<HH',body,68,0xaa64,1);struct.pack_into('<H',body,84,240)
        opt=88;struct.pack_into('<H',body,opt,0x20b);struct.pack_into('<I',body,opt+108,16)
        struct.pack_into('<II',body,opt+120,0x1000,40)
        struct.pack_into('<II',body,opt+112+13*8,0x1080,64)
        struct.pack_into('<IIII',body,opt+240+8,512,0x1000,512,512)
        struct.pack_into('<IIIII',body,512,0,0,0,0x1040,0)
        body[576:589]=b'kernel32.dll\0'
        struct.pack_into('<IIIIIIII',body,640,1,0x10c0,0,0,0,0,0,0)
        name=b'vcruntime140_1.dll\0';body[704:704+len(name)]=name
        self.assertEqual(pe_imports(body),['kernel32.dll','vcruntime140_1.dll'])
        struct.pack_into('<I',body,640,0)
        with self.assertRaises(ValueError):pe_imports(body)

    def test_arm_compatibility_omission_requires_exact_bytes_and_name(self):
        body=bytearray(128);body[:2]=b'MZ';struct.pack_into('<I',body,60,64)
        body[64:68]=b'PE\0\0';struct.pack_into('<H',body,68,0x8664)
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as archive:archive.writestr(ARM_UNUSED_DLL,body)
        with tempfile.TemporaryDirectory() as folder, zipfile.ZipFile(data) as archive:
            with self.assertRaises(ValueError):extract_python(archive,folder,'arm64')
            with patch('suite.windows_bundle.ARM_UNUSED_DLL_SHA',hashlib.sha256(body).hexdigest()):
                extract_python(archive,folder,'arm64')
            self.assertFalse((Path(folder)/ARM_UNUSED_DLL).exists())
            extract_python(archive,folder,'x86_64')
            self.assertEqual((Path(folder)/ARM_UNUSED_DLL).read_bytes(),body)


if __name__=='__main__':unittest.main()
