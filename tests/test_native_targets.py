# SPDX-License-Identifier: GPL-3.0-only
"""Wrong-CPU payloads must fail even when their names or tags claim ARM support."""
import base64
import csv
import hashlib
import io
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from suite.native_targets import native_target, wheel_matches
from suite.windows_bundle import check_native_arch, install_wheel as install_windows, wheel_record
from suite.macos_bundle import mach_o_info, mac_tag, install_wheel as install_macos
from suite.packages import PLATFORMS
from tests.test_macos_bundle import thin
from tests.test_windows_bundle import wheel


def pe(cpu):
    body=bytearray(128);body[:2]=b'MZ';struct.pack_into('<I',body,0x3c,64)
    body[64:68]=b'PE\0\0';struct.pack_into('<H',body,68,cpu)
    return bytes(body)


def universal(slices):
    start=8+20*len(slices);headers=[];data=[]
    for cpu,body in slices:
        headers.append(struct.pack('>IIIII',cpu,0,start,len(body),0))
        data.append(body);start+=len(body)
    return struct.pack('>II',0xcafebabe,len(slices))+b''.join(headers+data)


def binary_wheel(path, tag, filename, body):
    prefix='fixture-1.0.dist-info/'
    files={filename:body,prefix+'METADATA':b'Name: fixture\nVersion: 1.0\n',
           prefix+'WHEEL':('Wheel-Version: 1.0\nTag: '+tag+'\n').encode()}
    record=io.StringIO();writer=csv.writer(record)
    for name,data in files.items():
        sha=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
        writer.writerow([name,'sha256='+sha,len(data)])
    writer.writerow([prefix+'RECORD','','']);files[prefix+'RECORD']=record.getvalue().encode()
    with zipfile.ZipFile(path,'w') as archive:
        for name,data in files.items():archive.writestr(name,data)


class NativeTargetTests(unittest.TestCase):
    def test_four_targets_are_distinct_and_unknown_targets_fail(self):
        platforms={native_target(f,a).platform for f in ('windows','macos') for a in ('x86_64','arm64')}
        self.assertEqual(platforms,{'windows-x86_64','windows-arm64','macos-x86_64','macos-arm64'})
        self.assertTrue(platforms<=PLATFORMS)
        for family,arch in [('windows','x64'),('macos','universal2'),('linux','arm64'),('macos',None)]:
            with self.assertRaises(ValueError):native_target(family,arch)

    def test_native_wheel_tags_must_match_exact_cpu_and_python_abi(self):
        for family in ('windows','macos'):
            for arch in ('x86_64','arm64'):
                target=native_target(family,arch)
                platform=target.wheel_platform if family=='windows' else 'macosx_13_0_'+arch
                self.assertTrue(wheel_matches('py3-none-any',target))
                self.assertTrue(wheel_matches('cp314-cp314-'+platform,target))
                self.assertTrue(wheel_matches('cp311-abi3-'+platform,target))
                self.assertFalse(wheel_matches('cp313-cp313-'+platform,target))
                self.assertFalse(wheel_matches('cp315-abi3-'+platform,target))
                self.assertFalse(wheel_matches('not-a-valid-wheel-tag',target))
                other=native_target(family,'arm64' if arch=='x86_64' else 'x86_64')
                self.assertFalse(wheel_matches('cp314-cp314-'+platform,other))
        self.assertTrue(mac_tag('cp314-cp314-macosx_13_0_universal2',architecture='arm64'))
        self.assertFalse(mac_tag('cp314-cp314-macosx_16_0_arm64',architecture='arm64'))

    def test_windows_pe_checks_cpu_not_filename(self):
        for arch,cpu in [('x86_64',0x8664),('arm64',0xaa64)]:
            check_native_arch('runtime/python.exe',pe(cpu),architecture=arch)
            with self.assertRaises(ValueError):
                check_native_arch('runtime/arm64.exe',pe(0x8664 if cpu==0xaa64 else 0xaa64),architecture=arch)
        # Inert known setuptools launcher templates are data, not our entrypoint.
        check_native_arch('Lib/site-packages/setuptools/cli-64.exe',pe(0x8664),architecture='arm64')
        with self.assertRaises(ValueError):
            check_native_arch('Scripts/cli-64.exe',pe(0x8664),architecture='arm64')

    def test_windows_arm_wheel_record_and_install_guard(self):
        with wheel(tag='cp314-cp314-win_arm64') as archive:
            self.assertEqual(wheel_record(archive,architecture='arm64')['name'],'fixture')
        with wheel(tag='cp314-cp314-win_amd64') as archive:
            with self.assertRaises(ValueError):wheel_record(archive,architecture='arm64')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'fixture.whl'
            with wheel(tag='cp314-cp314-win_arm64') as source, zipfile.ZipFile(path,'w') as out:
                for name in source.namelist():out.writestr(name,source.read(name))
            install_windows(path,root/'arm-runtime',architecture='arm64')
            self.assertTrue((root/'arm-runtime/Lib/site-packages/fixture.py').exists())
            with self.assertRaises(ValueError):install_windows(path,root/'intel-runtime')
            self.assertFalse((root/'intel-runtime').exists())

    def test_macos_arm_and_universal_slices_are_checked_independently(self):
        intel,arm=thin(),thin(0x100000c)
        fat=universal([(0x1000007,intel),(0x100000c,arm)])
        self.assertEqual(mach_o_info(arm,architecture='arm64')['architecture'],'arm64')
        self.assertEqual(mach_o_info(fat,architecture='arm64')['architecture'],'arm64')
        self.assertEqual(mach_o_info(fat)['architecture'],'x86_64')
        with self.assertRaises(ValueError):mach_o_info(intel,architecture='arm64')
        with self.assertRaises(ValueError):mach_o_info(arm)
        forged=universal([(0x100000c,intel)])
        with self.assertRaises(ValueError):mach_o_info(forged,architecture='arm64')

    def test_macos_truncated_or_overlapping_fat_table_fails(self):
        bad=struct.pack('>II',0xcafebabe,2)+b'\0'*24
        with self.assertRaises(ValueError):mach_o_info(bad,architecture='arm64')
        overlap=struct.pack('>II',0xcafebabe,1)+struct.pack('>IIIII',0x100000c,0,8,32,0)+thin(0x100000c)
        with self.assertRaises(ValueError):mach_o_info(overlap,architecture='arm64')

    def test_arm_wheel_label_cannot_hide_foreign_executable_code(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'fixture.whl'
            binary_wheel(path,'cp314-cp314-win_arm64','fixture.pyd',pe(0x8664))
            with self.assertRaises(ValueError):install_windows(path,root/'windows',architecture='arm64')
            binary_wheel(path,'cp314-cp314-macosx_13_0_arm64','fixture.so',thin())
            with self.assertRaises(ValueError):install_macos(path,root/'macos',architecture='arm64')

    def test_mac_launcher_accepts_only_current_interpreter_architecture(self):
        import json
        from unittest.mock import patch
        from macos_entry import load_manifest
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);files={}
            for n in range(12):
                name=str(n)+'.py';(root/name).write_bytes(b'fixture')
                files[name]=hashlib.sha256(b'fixture').hexdigest()
            manifest={'format':'kobra-macos-test-bundle-v1','platform':'macos-arm64',
                      'version':'0.39.0-alpha.1','bundle_id':'a'*64,'files':files}
            (root/'native-bundle.json').write_text(json.dumps(manifest))
            with patch('macos_entry.runtime_architecture',return_value='arm64'):
                self.assertEqual(load_manifest(root,verify=True)['platform'],'macos-arm64')
            with patch('macos_entry.runtime_architecture',return_value='x86_64'):
                with self.assertRaises(ValueError):load_manifest(root,verify=True)

    def test_macos_arm_wheel_installs_but_rejects_intel_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'fixture.whl'
            with wheel(tag='cp314-cp314-macosx_13_0_arm64') as source, zipfile.ZipFile(path,'w') as out:
                for name in source.namelist():out.writestr(name,source.read(name))
            install_macos(path,root/'arm-runtime',architecture='arm64')
            self.assertTrue((root/'arm-runtime/lib/python3.14/site-packages/fixture.py').exists())
            with self.assertRaises(ValueError):install_macos(path,root/'intel-runtime')
            self.assertFalse((root/'intel-runtime').exists())
