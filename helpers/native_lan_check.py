# SPDX-License-Identifier: GPL-3.0-only
"""Owner-run native LAN diagnosis; no controls, settings writes or secret output."""
import argparse
import contextlib
import importlib
import ipaddress
import json
import logging
import os
from pathlib import Path
import platform
import sys
import tempfile
import uuid
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Redirect refused')


def target_ip(value):
    ip=ipaddress.ip_address(value)
    networks=('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')
    if ip.version!=4 or not any(ip in ipaddress.ip_network(n) for n in networks):
        raise ValueError('Private printer IPv4 required')
    return str(ip)


def safe_error(error):
    # Exception messages can contain URLs, tokens, certificate paths or payloads.
    result={'ok':False,'error_type':type(error).__name__}
    cause=error.reason if isinstance(error,urllib.error.URLError) else error
    if isinstance(error,urllib.error.HTTPError):result['http_status']=error.code
    if isinstance(cause,OSError) and type(cause.errno) is int:result['errno']=cause.errno
    return result


def local_fetch(opener,ip,method,url):
    parsed=urllib.parse.urlsplit(url)
    if (parsed.scheme!='http' or parsed.hostname!=ip or parsed.port!=18910 or
            parsed.username is not None or parsed.password is not None or parsed.fragment):
        raise ValueError('Unexpected handshake endpoint')
    request=urllib.request.Request(url,method=method)
    if method=='POST':request.add_header('Content-Type','application/json')
    with opener.open(request,timeout=8) as response:
        body=response.read(131073)
        if len(body)>131072:raise ValueError('Oversized handshake response')
        return json.loads(body)


def diagnose(bundle,ip):
    bundle=Path(bundle).resolve();ip=target_ip(ip)
    code=bundle/'app/monitor'
    if not (code/'vendor/kobra-connect/kobra_connect/handshake.py').is_file():
        raise ValueError('Installed test app not found')
    sys.path[:0]=[str(code/'vendor/kobra-connect'),str(code/'vendor/kobra-bridge')]
    hs_module=importlib.import_module('kobra_connect.handshake')
    client_module=importlib.import_module('kobrax_client')
    report={'format':'kobra-native-lan-diagnosis-v1',
            'app_version':(code/'VERSION').read_text().strip(),
            'python':platform.python_version(),'architecture':platform.machine(),
            'proxy_types':sorted(k for k in urllib.request.getproxies() if k in ('http','https','all')),
            'printer_controls_sent':False,'monitor_data_modified':False}
    default=urllib.request.build_opener(NoRedirect())
    direct=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    for label,opener in [('http_default',default),('http_direct',direct)]:
        try:
            info=local_fetch(opener,ip,'GET','http://'+ip+':18910/info')
            report[label]={'ok':True,'lan_mode':info.get('ctrlType')!='cloud',
                           'required_fields_present':all(bool(info.get(k)) for k in ('token','ctrlInfoUrl','modelId'))}
        except Exception as error:report[label]=safe_error(error)
    original=hs_module._http_fetch
    hs_module._http_fetch=lambda method,url:local_fetch(direct,ip,method,url)
    client=None
    try:
        try:
            hs=hs_module.do_handshake(ip)
            if hs.broker_host!=ip or hs.broker_port!=9883:
                raise ValueError('Unexpected MQTT endpoint')
            report['lan_handshake_direct']={'ok':True}
        except Exception as error:
            report['lan_handshake_direct']=safe_error(error);return report
        # Certificates are ephemeral, private and never printed or retained.
        with tempfile.TemporaryDirectory(prefix='kobra-lan-diagnosis-') as folder:
            cert=Path(folder)/'client.crt';key=Path(folder)/'client.key'
            cert.write_text(hs.device_cert);cert.chmod(0o600)
            key.write_text(hs.device_key);key.chmod(0o600)
            try:
                client=client_module.KobraXClient(ip,hs.username,hs.password,hs.model_id,hs.device_id,
                    client_id='kobra_diag_'+uuid.uuid4().hex[:12],
                    read_only=True,cert_file=str(cert),key_file=str(key))
                client.connect()  # TLS, MQTT login and read-only subscription; no publish/query/control.
                report['mqtt_read_only_connect']={'ok':True}
            except Exception as error:report['mqtt_read_only_connect']=safe_error(error)
            finally:
                if client is not None:
                    with contextlib.suppress(Exception):client.disconnect()
                    thread=getattr(client,'_reader_thread',None)
                    if thread is not None:thread.join(timeout=2)
    finally:
        hs_module._http_fetch=original
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',default=str(Path.home()/'Applications/Kobra Monitor Test.app/Contents/Resources/payload'))
    parser.add_argument('--ip',required=True,help='Ausdrücklich gewählte private IPv4-Adresse des Druckers');args=parser.parse_args()
    os.umask(0o077);logging.disable(logging.CRITICAL)
    try:result=diagnose(args.bundle,args.ip)
    except Exception as error:result={'format':'kobra-native-lan-diagnosis-v1','startup':safe_error(error)}
    print(json.dumps(result,indent=2,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
