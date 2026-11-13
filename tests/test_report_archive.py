import io,json,sqlite3,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch,AsyncMock
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from history import History
from monitor import build_app
from access import Access
from aiohttp.test_utils import make_mocked_request

class ArchiveTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.now=1000;self.h=History(Path(self.tmp.name)/'history.sqlite3',clock=lambda:self.now)
  self.h.link('192.168.1.10',True)
  self.observe('printing');self.job=self.h.jobs()[0]['id']
 def tearDown(self):self.h.close();self.tmp.cleanup()
 def observe(self,state):
  self.h.observe('192.168.1.10','info',{'code':200,'data':{'project':{'state':state,'task_id':'123','filename':'Feine_Statue_ÄÖÜ_ß.gcode.3mf','progress':100 if state=='finished' else 5}}},{'connection':'online','data':{'nozzle_temp':215,'bed_temp':65}})
 def finish(self):self.now+=100;self.observe('finished')
 def edit(self,**kw):
  a=self.h.reports.annotation(self.job);a.pop('approved_at');a['expected_revision']=a.pop('revision');a.update(kw);return self.h.reports.save(self.job,a)
 def test_end_creates_fixed_files_and_repeated_end_is_idempotent(self):
  self.finish();self.observe('finished');v=self.h.reports.detail(self.job)['versions'];self.assertEqual(len(v),1)
  files=list((Path(self.tmp.name)/'report-archive'/self.job/'v1').iterdir());self.assertEqual(len(files),3)
  pdf=self.h.reports.export(self.job,1,'pdf')[0];self.assertTrue(pdf.startswith(b'%PDF'))
  self.h.db.execute('delete from samples');self.h.db.commit();self.assertEqual(pdf,self.h.reports.export(self.job,1,'pdf')[0])
 def test_edit_revisions_preserve_old_exports_and_material_snapshot(self):
  self.h.report_materials=lambda ip:{'spool':2,'remaining_book_g':581};self.finish();old=self.h.reports.export(self.job,1,'pdf')[0]
  self.edit(customer_order='KA-42',position='01',approval='accepted',approver='Prüfer',part='Statue')
  self.assertEqual(len(self.h.reports.detail(self.job)['versions']),2)
  self.assertEqual(old,self.h.reports.export(self.job,1,'pdf')[0]);self.h.report_materials=lambda ip:{'spool':9}
  exported=json.loads(self.h.reports.export(self.job,2,'json')[0]);self.assertEqual(exported['materials']['spool'],2)
  self.assertEqual(exported['annotation']['approval'],'accepted');self.assertIn('KA-42',self.h.reports.export(self.job,2,'pdf')[2])
 def test_identical_save_does_not_create_new_version(self):
  self.finish();self.edit(customer_order='K1');self.edit(customer_order='K1');self.assertEqual(len(self.h.reports.detail(self.job)['versions']),2)
 def test_concurrent_revision_fails_without_overwriting(self):
  self.edit(part='first')
  with self.assertRaises(RuntimeError):self.h.reports.save(self.job,{'expected_revision':0,'part':'second'})
  self.assertEqual(self.h.reports.annotation(self.job)['part'],'first')
 def test_active_job_no_final_report_or_quality_invention(self):
  self.edit(customer_order='A1');self.assertEqual(self.h.reports.detail(self.job)['versions'],[])
  with self.assertRaises(ValueError):self.h.reports.freeze(self.job)
  with self.assertRaises(ValueError):self.edit(approval='accepted')
 def test_failed_pdf_rolls_back_annotation_and_keeps_previous_version(self):
  self.finish()
  with patch('report_archive.pdf_report',side_effect=OSError('full')):
   with self.assertRaises(OSError):self.edit(part='lost')
  self.assertEqual(self.h.reports.annotation(self.job)['part'],'');self.assertEqual(len(self.h.reports.detail(self.job)['versions']),1)
 def test_immutable_sql_versions_and_invalid_inputs(self):
  self.finish()
  with self.assertRaises(sqlite3.IntegrityError):self.h.db.execute('delete from report_versions')
  self.h.db.rollback()
  with self.assertRaises(ValueError):self.edit(customer_order='bad\x00id')
  with self.assertRaises(ValueError):self.h.reports.export("' OR 1=1",1,'pdf')
 def test_zip_contains_all_formats_and_manifest_and_rejects_bad_selection(self):
  self.finish();raw=self.h.reports.bundle([self.job])
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   self.assertEqual(len(z.namelist()),4);self.assertTrue(all('/' not in n for n in z.namelist()))
   self.assertEqual(json.loads(z.read('manifest.json'))[0]['job_id'],self.job)
  for ids in [[],[self.job]*2,['missing'],['x']*26]:
   with self.assertRaises(ValueError):self.h.reports.bundle(ids)
 def test_bootstrap_historical_reports_has_no_retrospective_material_assignment(self):
  self.now+=10;self.h.db.execute("update jobs set state='unknown_end',ended_at=? where id=?",(self.now,self.job));self.h.db.commit()
  self.h.report_materials=lambda ip:{'spool':99};self.assertEqual(self.h.reports.bootstrap(),1)
  p=json.loads(self.h.reports.export(self.job,1,'json')[0]);self.assertNotIn('spool',p['materials']);self.assertEqual(self.h.reports.bootstrap(),0)
 def test_search_finds_customer_order_and_part(self):
  self.edit(customer_order='KUNDE-42',part='Feiner Würfel')
  self.assertEqual(self.h.archive('192.168.1.10',search='kunde-42')['total'],1)
  self.assertEqual(self.h.archive('192.168.1.10',search='WÜRFEL')['total'],1)

class ArchiveBackupTests(unittest.TestCase):
 def test_snapshot_versions_and_export_files_survive_full_backup_restore(self):
  from configuration import save_config
  import backup
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=root/'source';data.mkdir();Access(data);save_config(data,['192.168.1.10'])
   h=History(data/'history.sqlite3')
   h.db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",('a'*32,'192.168.1.10','','test.gcode','completed',1000,1100,1100,1,100,10,10,1));h.db.commit()
   h.reports.freeze('a'*32);pdf=h.reports.export('a'*32,1,'pdf')[0]
   archive=backup.create(data,root/'backup','test');backup.restore(archive,root/'restore')
   restored=History(root/'restore/history.sqlite3');self.assertEqual(pdf,restored.reports.export('a'*32,1,'pdf')[0])
   self.assertEqual(len(list((root/'restore/report-archive').rglob('*.pdf'))),1)
   restored.close();h.close()

class ArchiveAccessTests(unittest.IsolatedAsyncioTestCase):
 async def test_owner_and_csrf_required_for_archive_writes_and_downloads(self):
  with tempfile.TemporaryDirectory() as tmp:
   access=Access(tmp);reports=SimpleNamespace(detail=lambda j:{'job':j},bootstrap=lambda:0)
   app=build_app(SimpleNamespace(history=SimpleNamespace(reports=reports),start=AsyncMock(),stop=AsyncMock()),access)
   async def call(method,path,body=None,headers=None):
    r=make_mocked_request(method,path,headers={'Host':'localhost',**(headers or {})});r.json=AsyncMock(return_value=body or {})
    match=await app.router.resolve(r);return await app.middlewares[0](r,match.handler)
   for route in ['/api/order-report?job=x','/api/report-export?job=x&version=1']:
    self.assertEqual((await call('GET',route)).status,401)
   self.assertEqual((await call('POST','/api/order-report',{'action':'backfill'})).status,401)
   login=await call('POST','/api/session',{'code':access.token},{'Content-Type':'application/json','Origin':'http://localhost'})
   session={'Cookie':'kobra_session='+login.cookies['kobra_session'].value,'Content-Type':'application/json','Origin':'http://localhost','X-Kobra-CSRF':json.loads(login.text)['csrf']}
   account=await call('POST','/api/account',{'username':'tester','password':'Long isolated test passphrase','password_confirmation':'Long isolated test passphrase'},session)
   session['Cookie']='kobra_session='+account.cookies['kobra_session'].value;session['X-Kobra-CSRF']=json.loads(account.text)['csrf']
   self.assertEqual((await call('POST','/api/order-report',{'action':'backfill'},session)).status,200)
   session['Origin']='https://evil.invalid';self.assertEqual((await call('POST','/api/order-report',{'action':'backfill'},session)).status,403)
