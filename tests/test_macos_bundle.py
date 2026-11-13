from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from suite.macos_bundle import mach_o_info, mac_tag


def thin(cpu=0x1000007,minimum=13):
    # mach_header_64 followed by LC_BUILD_VERSION (no tools).
    return struct.pack('<IIIIIIII',0xfeedfacf,cpu,3,2,1,24,0,0)+struct.pack('<IIIIII',0x32,24,1,minimum<<16,15<<16,0)


class MacBundleTests(unittest.TestCase):
    def test_intel_and_universal_binary_have_a_compatible_intel_slice(self):
        intel=thin();arm=thin(0x100000c)
        self.assertEqual(mach_o_info(intel)['minimum_macos'],[13,0,0])
        start=48
        fat=struct.pack('>II',0xcafebabe,2)+struct.pack('>IIIII',0x100000c,0,start,len(arm),0)+struct.pack('>IIIII',0x1000007,3,start+len(arm),len(intel),0)+arm+intel
        self.assertEqual(mach_o_info(fat)['architecture'],'x86_64')

    def test_foreign_architecture_newer_system_and_broken_headers_fail(self):
        for body in (thin(0x100000c),thin(minimum=16),b'not executable',thin()[:40]):
            with self.assertRaises((ValueError,struct.error)):mach_o_info(body)

    def test_only_matching_python_and_intel_macos_wheels_are_allowed(self):
        for tag in ['py3-none-any','cp314-cp314-macosx_10_15_x86_64','cp39-abi3-macosx_11_0_universal2']:
            self.assertTrue(mac_tag(tag),tag)
        for tag in ['cp314-cp314-macosx_11_0_arm64','cp314-cp314-win_amd64',
                    'cp314-cp314-macosx_16_0_x86_64','cp313-cp313-macosx_13_0_x86_64']:
            self.assertFalse(mac_tag(tag),tag)


if __name__=='__main__':unittest.main()
