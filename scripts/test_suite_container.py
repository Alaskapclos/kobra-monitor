# SPDX-License-Identifier: GPL-3.0-only
"""Dedicated build-VM only: real isolated suite startup, persistence and recovery.

Run from the fixed build helper AFTER image/unit checks. This is not a general
installer and must never be pointed at a production Docker host.
"""
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

if not Path('/etc/kobra-build-vm').is_file():
    raise SystemExit('Dedicated build VM marker required.')
source = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(source))
from suite.deployment import contract, prepare, SPOOLMAN_IMAGE
from suite.bundle import render_installer, digest


def run(args, *, capture=False, input=None, check=True):
    result = subprocess.run(args, input=input, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None, timeout=600)
    if check and result.returncode:
        raise RuntimeError('Suite test command failed: ' + str(args[:4]) + '\n' +
                           (result.stderr or '')[-6000:])
    return result.stdout if capture else result.returncode


EXERCISE = r'''
import http.cookiejar,json,sqlite3,urllib.request,urllib.error
from pathlib import Path
root=Path('/data');origin='http://127.0.0.1:7125'
jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
csrf=''
def request(path,body=None):
    headers={'Origin':origin,'Content-Type':'application/json','X-Kobra-CSRF':csrf}
    req=urllib.request.Request(origin+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
    with client.open(req,timeout=40) as response:
        raw=response.read()
        return json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw
try:
    urllib.request.urlopen(origin+'/spoolman/api/v1/spool',timeout=5)
    raise AssertionError('Anonymous inventory access allowed')
except urllib.error.HTTPError as error:
    assert error.code==401,error.code
password='Suite-fixture-only-Not-a-user-password-2026!'
if not (root/'account.json').exists():
    csrf=request('/api/session',{'code':(root/'access-token').read_text().strip()})['csrf']
    csrf=request('/api/account',{'username':'Suite Fixture','password':password,'password_confirmation':password})['csrf']
    request('/api/setup',{'printer_ips':['192.168.254.254']})
    # Internal-only Docker network prevents reaching a real printer or LAN.
    vendor=request('/spoolman/api/v1/vendor',{'name':'Suite fixture vendor'})
    filament=request('/spoolman/api/v1/filament',{'name':'Suite fixture PLA','vendor_id':vendor['id'],
        'material':'PLA','weight':1000,'diameter':1.75,'density':1.24})
    request('/spoolman/api/v1/spool',{'filament_id':filament['id'],'used_weight':530})
    with sqlite3.connect(root/'history.sqlite3') as db:
        db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            ('f'*32,'192.168.254.254','','suite-fixture.gcode','completed',1,2,2,100,200,60,0,1))
else:
    csrf=request('/api/session',{'username':'Suite Fixture','password':password})['csrf']
spools=request('/spoolman/api/v1/spool')
assert len(spools)==1 and abs(spools[0]['remaining_weight']-470)<0.01,spools
html=request('/spoolman/')
assert b'<html' in html.lower() or b'<!doctype' in html.lower()
with sqlite3.connect(root/'history.sqlite3') as db:
    assert db.execute('SELECT count(*) FROM jobs').fetchone()[0]==1
print(json.dumps({'owner_login':True,'gateway_protected':True,'native_spoolman_ui':True,
    'spools':len(spools),'remaining_weight':spools[0]['remaining_weight'],'monitor_jobs':1}))
'''


def main():
    image = sys.argv[2]
    contract(image)  # Validate exact development tag before any Docker operation.
    run(['docker', 'image', 'inspect', image], capture=True)
    run(['docker', 'pull', '--platform', 'linux/amd64', SPOOLMAN_IMAGE])
    native = subprocess.run(['docker','compose','version'],capture_output=True).returncode == 0
    if not native:
        run(['docker','pull','docker:27-cli'])  # Build tool only, never shipped in suite.
    with tempfile.TemporaryDirectory(prefix='suite-integration-', dir=source.parent) as folder:
        root = Path(folder)
        projects = []
        def cli(path, *args, capture=False, check=True):
            prefix=['docker','compose'] if native else ['docker','run','--rm','--network','none',
                '-e','DOCKER_HOST=unix:///var/run/docker.sock',
                '-v','/var/run/docker.sock:/var/run/docker.sock',
                '-v',str(root)+':'+str(root)+':ro','-w',str(path),'docker:27-cli','docker','compose']
            return run([*prefix,'-f',str(path/'compose.json'),*args],capture=capture,check=check)
        def new_project(name, network='isolated'):
            path=prepare(root/name,image,port=20000+secrets.randbelow(30000),network=network)
            projects.append(path)
            cli(path,'config','--quiet')
            return path
        def execute(path, service, code):
            return cli(path,'exec','-T',service,'python','-c',code,capture=True)
        try:
            if not native:
                raise RuntimeError('Install the Compose v2 host plugin to test the shell installer.')
            package=root/'installer-package';package.mkdir()
            image_archive=package/'monitor-linux-amd64.tar'
            run(['docker','image','save','--output',str(image_archive),image])
            image_id=run(['docker','image','inspect','--format','{{.Id}}',image],capture=True).strip()
            installer=package/'Installieren.sh'
            installer.write_text(render_installer(image,image_id,image_archive.name,digest(image_archive)))
            installer.chmod(0o755)
            first_home=root/'first'
            first=first_home/'project';projects.append(first)
            # Capture stdout: the new installation's private setup link is NOT a build log.
            run(['sh',str(installer),'install','--yes','--directory',str(first_home),
                 '--port',str(20000+secrets.randbelow(30000))],capture=True)
            print('Suite installer: fresh installation completed; setup link kept private.',flush=True)
            first_proof=json.loads(execute(first,'monitor',EXERCISE))
            before_ids=cli(first,'ps','--quiet','monitor','spoolman','backups',capture=True).split()
            run(['sh',str(installer),'start','--yes','--directory',str(first_home)],capture=True)
            run(['sh',str(installer),'status','--yes','--directory',str(first_home)],capture=True)
            after_ids=cli(first,'ps','--quiet','monitor','spoolman','backups',capture=True).split()
            assert sorted(before_ids)==sorted(after_ids) and len(before_ids)==3
            refused=run(['sh',str(installer),'install','--yes','--directory',str(first_home)],check=False)
            assert refused!=0
            print('Suite installer: start/status kept existing containers; duplicate installation refused.',flush=True)
            config=json.loads((first/'suite.json').read_text())
            # An explicit test snapshot after all fixture writes avoids racing
            # the scheduler's first backup against the fixture creation.
            snapshot=execute(first,'backups',r'''
import json,tempfile
from pathlib import Path
from suite_service import read_config
from suite.deployment import compose
from suite.snapshots import create_snapshot
c=read_config('/suite/suite.json')
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'compose.json';p.write_text(json.dumps(compose(c)))
 result=create_snapshot('/source-monitor','/source-spoolman/spoolman.db','/backups',
  monitor_image=c['monitor_image'],spoolman_image=c['spoolman_image'],deployment=p)
 print(result.name)
''').strip()
            assert snapshot.startswith('kobra-suite-') and '/' not in snapshot
            # Restart original services, preserving all named volumes.
            cli(first,'down')
            cli(first,'up','-d','--wait','--wait-timeout','180')
            restart_proof=json.loads(execute(first,'monitor',EXERCISE))
            assert first_proof==restart_proof
            recovered=new_project('recovered')
            cli(recovered,'run','--rm','initialize')
            old=json.loads(cli(first,'config','--format','json',capture=True))
            new=json.loads(cli(recovered,'config','--format','json',capture=True))
            importer=r'''
import os,shutil
from pathlib import Path
from suite.recovery import restore_to_new_directory
from suite_service import MARKER
restored=restore_to_new_directory(Path('/snapshots')/SNAPSHOT,'/tmp/restored')
for role in ('monitor','spoolman'):
 src=restored/(role+'-data');dst=Path('/'+role)
 for p in src.iterdir():
  if p.name==MARKER:continue
  target=dst/p.name
  if p.is_dir():shutil.copytree(p,target,dirs_exist_ok=True)
  else:shutil.copyfile(p,target)
 for p in [dst,*dst.rglob('*')]:os.chown(p,10001,10001)
print('Both fixture databases restored into separate fresh test volumes.')
'''.replace('SNAPSHOT',repr(snapshot))
            run(['docker','run','--rm','--network','none','--read-only','--user','0:0',
                '--cap-drop','ALL','--cap-add','CHOWN','--cap-add','DAC_OVERRIDE','--cap-add','FOWNER',
                '--tmpfs','/tmp:mode=1777,size=128m',
                '-v',old['volumes']['backup-data']['name']+':/snapshots:ro',
                '-v',new['volumes']['monitor-data']['name']+':/monitor',
                '-v',new['volumes']['spoolman-data']['name']+':/spoolman',
                image,'python','-c',importer])
            cli(recovered,'up','-d','--wait','--wait-timeout','180')
            restored_proof=json.loads(execute(recovered,'monitor',EXERCISE))
            assert restored_proof==first_proof
            # LAN networking is checked with an empty printer configuration.
            # No real device address is ever configured in this project.
            lan=new_project('lan', network='lan')
            cli(lan,'up','-d','--wait','--wait-timeout','180')
            monitor_id=cli(lan,'ps','--quiet','monitor',capture=True).strip()
            spoolman_id=cli(lan,'ps','--quiet','spoolman',capture=True).strip()
            def networks(container):
                return json.loads(run(['docker','inspect',container],capture=True))[0]['NetworkSettings']['Networks']
            assert len(networks(monitor_id))==2
            assert len(networks(spoolman_id))==1
            health=json.loads(execute(lan,'monitor',"import json,urllib.request; print(urllib.request.urlopen('http://127.0.0.1:7125/health').read().decode())"))
            assert health['ips']==[] and health['read_only'] is True
            print('LAN_SUITE_CONTAINER_PROOF '+json.dumps({'monitor_two_networks':True,
                'spoolman_internal_only':True,'no_configured_printers':True,
                'read_only_default':True,'real_printer_connections':False}),flush=True)
            print('SUITE_CONTAINER_PROOF '+json.dumps({'fresh_install':True,'restart_persistence':True,
                'installer_fresh_install':True,'installer_resume_without_recreation':True,
                'installer_duplicate_refused':True,'installer_status_read_only':True,
                'paired_database_restore_started':True,'configuration_restored':True,
                'fixture':restored_proof,'spoolman_image':SPOOLMAN_IMAGE,
                'real_printer_connections':False,'production_modified':False}))
        except Exception:
            for path in projects:
                if (path/'compose.json').is_file():cli(path,'logs','--tail','80',check=False)
            raise
        finally:
            for path in reversed(projects):
                if (path/'compose.json').is_file():cli(path,'down','--volumes','--remove-orphans',check=False)


if __name__=='__main__':
    main()
