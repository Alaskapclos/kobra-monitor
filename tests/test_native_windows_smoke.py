from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from suite import native_windows_smoke as smoke


class NativeWindowsSmokeTests(unittest.TestCase):
    def test_native_checks_are_local_and_include_launcher_and_image(self):
        replies=[SimpleNamespace(returncode=0,stdout=b'',stderr=b''),
                 SimpleNamespace(returncode=0,stdout=b'',stderr=b''),
                 SimpleNamespace(returncode=0,stdout=b'alembic',stderr=b''),
                 SimpleNamespace(returncode=0,stdout=b'\xff\xd8fixture',stderr=b'')]
        with patch.object(smoke,'runtime_architecture',return_value='arm64'), \
             patch.object(smoke,'load_manifest',return_value={'version':'0.41.0-alpha.1','bundle_id':'a'*64}) as verify, \
             patch.object(smoke.subprocess,'run',side_effect=replies) as run:
            result=smoke.check(Path('fixture'))
        self.assertTrue(result['success'])
        self.assertFalse(result['database_connections'])
        self.assertFalse(result['printer_connections'])
        self.assertEqual(verify.call_args.kwargs['platform'],'windows-arm64')
        self.assertTrue(verify.call_args.kwargs['verify'])
        self.assertEqual(run.call_count,4)
        self.assertTrue(run.call_args_list[2].args[0][0].endswith('alembic.exe'))
        self.assertIn('testsrc=size=64x64:rate=1',run.call_args_list[3].args[0])
        self.assertNotIn('connect(',run.call_args_list[1].args[0][-1])

    def test_successful_exit_without_valid_camera_image_fails(self):
        reply=SimpleNamespace(returncode=0,stdout=b'not a jpeg',stderr=b'')
        with patch.object(smoke,'runtime_architecture',return_value='arm64'), \
             patch.object(smoke,'load_manifest',return_value={'version':'0.41.0-alpha.1','bundle_id':'a'*64}), \
             patch.object(smoke.subprocess,'run',return_value=reply):
            result=smoke.check(Path('fixture'))
        self.assertFalse(result['success'])
        self.assertFalse(result['checks']['ffmpeg_synthetic_image']['ok'])

    def test_manifest_failure_prevents_executing_package_programs(self):
        with patch.object(smoke,'runtime_architecture',return_value='arm64'), \
             patch.object(smoke,'load_manifest',side_effect=ValueError('changed')), \
             patch.object(smoke.subprocess,'run') as run:
            with self.assertRaises(ValueError):smoke.check(Path('fixture'))
        run.assert_not_called()
