# SPDX-License-Identifier: GPL-3.0-only
import copy,json,tempfile,unittest
from pathlib import Path
from history import History
from reprint_dispatch import ReprintDispatch
from reprint_identity import normalize,INT32_MAX
from reprint_launch import start_payload
from reprint_transfer import remote_name

OP='09d7a374250ccae11111111111111111';IP='192.0.2.1';FULL=str(int(OP[:15],16))

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.h=History(Path(self.tmp.name)/'history.sqlite3')
        self.dispatch=ReprintDispatch(self.h.files,lambda ip:None,None,None,None)
        self.h.db.execute('INSERT INTO archive_dispatches VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(OP,'a','r',IP,'a'*64,'[]','x',json.dumps({'source_job':'source'}),'confirmed','',99999999999,1,1,json.dumps({'task_id':FULL}),'confirmed'));self.h.db.commit()
    def tearDown(self):self.dispatch.close();self.h.close();self.tmp.cleanup()
    def report(self,task,kind='info',filename=None,state='printing'):
        project={'filename':remote_name(OP) if filename is None else filename,'progress':4,'print_time':5}
        project['task_id' if kind=='info' else 'taskid']=task
        return {'code':200,'data':{'project':dict(project,state=state)} if kind=='info' else project,'state':state}
    def test_info_and_print_aliases_preserve_one_job_and_original_input(self):
        self.h.files.link=lambda *a,**k:None
        for task,kind in [(FULL,'print'),(INT32_MAX,'info'),(FULL,'print'),(INT32_MAX,'info')]:
            p=self.report(task,kind);before=copy.deepcopy(p);self.h.observe(IP,kind,p,{});self.assertEqual(p,before)
        self.assertEqual(len(self.h.jobs()),1);self.assertEqual(self.h.jobs()[0]['identity'],FULL)
        self.assertFalse(any(e['kind']=='unobserved_end' for e in self.h.events()))
    def test_ordinary_changed_identity_is_never_combined(self):
        for task in ('71','72'):self.h.observe(IP,'info',self.report(task),{})
        self.assertEqual(len(self.h.jobs()),2)
    def test_only_confirmed_matching_printer_filename_and_alias(self):
        p=self.report(INT32_MAX);self.assertEqual(normalize(self.h,IP,'info',p)['data']['project']['task_id'],FULL)
        for ip,packet in [('192.0.2.2',p),(IP,self.report(12)),(IP,self.report(INT32_MAX,filename='other.gcode.3mf'))]:
            self.assertIs(normalize(self.h,ip,'info',packet),packet)
        self.h.db.execute("UPDATE archive_dispatches SET state='uncertain'");self.h.db.commit();self.assertIs(normalize(self.h,IP,'info',p),p)
    def test_terminal_last_project_and_partial_print_keep_known_context(self):
        self.h.files.link=lambda *a,**k:None;self.h.observe(IP,'print',self.report(FULL,'print'),{})
        partial=self.report(INT32_MAX,'print');del partial['data']['filename'];self.assertEqual(normalize(self.h,IP,'print',partial)['data']['taskid'],FULL)
        p={'code':200,'data':{'state':'free','last_project':dict(self.report(INT32_MAX)['data']['project'],state='finished')}}
        self.h.observe(IP,'info',p,{});self.assertEqual(self.h.jobs()[0]['state'],'completed');self.assertEqual(len(self.h.jobs()),1)
    def test_new_task_ids_fit_signed_32_bit_and_keep_unique_remote_names(self):
        mapping=[{'paint_index':0,'ams_index':0,'paint_color':[0,0,0,255],'ams_color':[0,0,0,255],'material_type':'PLA'}]
        for op in (OP,'f'*32,'0'*32):self.assertTrue(1<=int(start_payload(op,'b'*32,100,mapping)['taskid'])<INT32_MAX)
        self.assertNotEqual(remote_name(OP),remote_name('f'*32))
    def test_without_dispatch_table_payload_is_unchanged(self):
        self.dispatch.close();self.h.db.execute('DROP TABLE archive_dispatches');self.h.db.commit();p=self.report(INT32_MAX);self.assertIs(normalize(self.h,IP,'info',p),p)

    def test_real_catalog_link_is_carried_to_the_continuing_segment(self):
        import hashlib
        from test_file_archive import package
        raw=package();sha=hashlib.sha256(raw).hexdigest();a=self.h.files
        client=a.authenticate(a.new_client('Fixture'));incoming=a.incoming/'x.part';incoming.write_bytes(raw)
        a.receive(incoming,'source.gcode.3mf',sha,len(raw),client)
        self.h.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',('source',IP,'old','source.gcode.3mf','completed',1,2,2,1,100,1,1,1));self.h.db.commit();a.link('source',sha)
        self.h.db.execute('UPDATE archive_dispatches SET sha256=?',(sha,));self.h.db.commit()
        self.h.observe(IP,'info',self.report(INT32_MAX),{})
        current=next(j for j in self.h.jobs() if j['ended_at'] is None);link=a.linked(current['id'])
        self.assertEqual(link['sha256'],sha);self.assertEqual(link['source_job'],'source');self.assertEqual(link['link_method'],'reprint')
        self.h.observe(IP,'print',self.report(FULL,'print'),{});self.assertEqual(len(self.h.jobs()),2)
    def test_normalized_reports_do_not_reset_telemetry_control_context(self):
        from monitor import Telemetry
        from types import SimpleNamespace
        t=Telemetry(IP);t.link(True);bridge=SimpleNamespace(_state={'print_state':'printing'})
        t.receive('print',normalize(self.h,IP,'print',self.report(FULL,'print')),bridge,'epoch')
        token=t.job_token;print_token=t.print_job.token
        t.receive('info',normalize(self.h,IP,'info',self.report(INT32_MAX)),bridge,'epoch')
        self.assertEqual(t.job_token,token);self.assertEqual(t.print_job.token,print_token);self.assertEqual(t.print_job.task,FULL)

    def test_malformed_saved_receipt_does_not_change_or_discard_printer_report(self):
        p=self.report(INT32_MAX)
        for receipt in ('null','[]','{','{"task_id":"not-a-number"}'):
            self.h.db.execute('UPDATE archive_dispatches SET receipt=?',(receipt,));self.h.db.commit()
            self.assertIs(normalize(self.h,IP,'info',p),p)
