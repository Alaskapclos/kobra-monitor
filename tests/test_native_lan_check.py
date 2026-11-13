import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error

root=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('native_lan_check',root/'helpers/native_lan_check.py')
diagnostic=importlib.util.module_from_spec(spec);spec.loader.exec_module(diagnostic)


class NativeLANDiagnosisTests(unittest.TestCase):
    def test_no_implicit_printer_target_without_ip_argument(self):
        with patch.object(sys,'argv',['native_lan_check.py']), \
                patch.object(diagnostic,'diagnose') as diagnose, \
                patch.object(sys,'stderr'):
            with self.assertRaises(SystemExit) as error:diagnostic.main()
        self.assertEqual(error.exception.code,2)
        diagnose.assert_not_called()

    def test_error_report_never_includes_exception_message_or_url(self):
        secret='SECRET_DEVICE_PASSWORD_AND_PRIVATE_KEY'
        errors=[ValueError(secret),urllib.error.URLError(secret),
                urllib.error.HTTPError('http://example.com/?token='+secret,403,secret,{},None)]
        for error in errors:self.assertNotIn(secret,json.dumps(diagnostic.safe_error(error)))
        errors[-1].close()
        self.assertEqual(diagnostic.safe_error(OSError(65,secret))['errno'],65)

    def test_handshake_cannot_redirect_secrets_to_foreign_hosts_or_ports(self):
        class Opener:
            def open(self,*args,**kwargs):raise AssertionError('Must not make a network request')
        for url in ['https://192.168.254.254:18910/ctrl','http://example.com:18910/ctrl',
                    'http://192.168.254.254:80/ctrl','http://user:secret@192.168.254.254:18910/ctrl']:
            with self.assertRaises(ValueError):diagnostic.local_fetch(Opener(),'192.168.254.254','POST',url)

    def test_only_private_printer_addresses_are_accepted(self):
        self.assertEqual(diagnostic.target_ip('192.168.254.254'),'192.168.254.254')
        for value in ['127.0.0.1','8.8.8.8','example.com','::1']:
            with self.assertRaises(ValueError):diagnostic.target_ip(value)

    def test_connection_is_read_only_unique_and_cleans_up_private_keys(self):
        secret='SECRET_DEVICE_PASSWORD_AND_PRIVATE_KEY'
        captured={}
        class Client:
            def __init__(self,*args,**kwargs):captured.update(kwargs)
            def connect(self):
                self.cert=Path(captured['cert_file'])
                assert self.cert.exists()
                assert self.cert.stat().st_mode & 0o777 == 0o600
            def disconnect(self):captured['disconnected']=True
        original=lambda *args:None
        handshake=SimpleNamespace(_http_fetch=original,do_handshake=lambda ip:SimpleNamespace(
            broker_host=ip,broker_port=9883,username=secret,password=secret,model_id='1',
            device_id=secret,device_cert=secret,device_key=secret))
        with tempfile.TemporaryDirectory() as folder:
            code=Path(folder)/'app/monitor'
            marker=code/'vendor/kobra-connect/kobra_connect/handshake.py'
            marker.parent.mkdir(parents=True);marker.touch()
            (code/'VERSION').write_text('0.34-test')
            with patch.object(diagnostic.importlib,'import_module',side_effect=[handshake,SimpleNamespace(KobraXClient=Client)]), \
                    patch.object(diagnostic,'local_fetch',return_value={'token':secret,'ctrlInfoUrl':secret,'modelId':'1'}):
                report=diagnostic.diagnose(folder,'192.168.254.254')
        self.assertNotIn(secret,json.dumps(report))
        self.assertTrue(captured['read_only'])
        self.assertTrue(captured['client_id'].startswith('kobra_diag_'))
        self.assertTrue(captured['disconnected'])
        self.assertFalse(Path(captured['key_file']).exists())
        self.assertIs(handshake._http_fetch,original)


if __name__=='__main__':unittest.main()
