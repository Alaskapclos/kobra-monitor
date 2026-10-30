import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from history import History

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'history.sqlite3'
        self.now=1000;self.h=History(self.path,clock=lambda:self.now);self.ip='192.168.1.101'
    def tearDown(self):self.h.close();self.tmp.cleanup()
    def info(self,state='printing',task=7,progress=0,filename='test.gcode',elapsed=0):
        payload={'code':200,'data':{'state':'busy','project':{'state':state,'task_id':task,'filename':filename,'progress':progress,'print_time':elapsed,'curr_layer':1,'total_layers':10}}}
        self.h.observe(self.ip,'info',payload,{'data':{'print_state':state,'nozzle_temp':210},'read_only':True})
    def idle(self):self.h.observe(self.ip,'info',{'code':200,'data':{'state':'free','project':None,'last_project':{'state':'finished','task_id':1,'filename':'old.gcode'}}},{'data':{'print_state':'standby'}})
    def test_old_completion_does_not_become_new_job(self):
        self.idle();self.assertEqual(self.h.jobs(),[])
    def test_full_start_and_finish_and_disconnect_is_not_finish(self):
        self.idle();self.now+=30;self.info();self.assertEqual(self.h.jobs()[0]['observed_start'],1)
        self.h.link(self.ip,False);self.assertIsNone(self.h.jobs()[0]['ended_at'])
        self.now+=120;self.info(state='finished',progress=100)
        self.assertEqual(self.h.jobs()[0]['state'],'completed');self.assertEqual(len(self.h.jobs()),1)
    def test_reopen_keeps_job_identity(self):
        self.info(progress=30,elapsed=4);self.h.close();self.h=History(self.path,clock=lambda:self.now)
        self.info(progress=40,elapsed=5);self.assertEqual(len(self.h.jobs()),1)
        self.assertEqual(self.h.jobs()[0]['observed_start'],0)
    def test_leveling_with_previous_elapsed_is_observed_after_fresh_idle(self):
        self.idle();self.now+=30
        self.info(state='auto_leveling',elapsed=206,progress=100)
        self.assertEqual(self.h.jobs()[0]['observed_start'],1)
        self.now+=400;self.info(elapsed=0)
        self.assertEqual(len(self.h.jobs()),1)
        self.assertEqual(self.h.jobs()[0]['observed_start'],1)
    def test_leveling_discovered_without_prior_idle_stays_partial(self):
        self.info(state='auto_leveling',elapsed=206)
        self.assertEqual(self.h.jobs()[0]['observed_start'],0)
    def test_stale_idle_does_not_establish_start_coverage(self):
        self.idle();self.now+=300;self.info(state='auto_leveling')
        self.assertEqual(self.h.jobs()[0]['observed_start'],0)
    def test_disconnect_invalidates_prior_idle(self):
        self.idle();self.h.link(self.ip,False);self.now+=10
        self.h.link(self.ip,True);self.info(state='auto_leveling')
        self.assertEqual(self.h.jobs()[0]['observed_start'],0)
    def test_restart_does_not_treat_cached_idle_as_live_observation(self):
        self.idle();self.h.close();self.h=History(self.path,clock=lambda:self.now)
        self.info(state='auto_leveling')
        self.assertEqual(self.h.jobs()[0]['observed_start'],0)
    def test_placeholder_taskid_does_not_split_valid_job(self):
        self.info(task=123);self.info(task=-1,progress=30);self.info(task=123,progress=40)
        self.assertEqual(len(self.h.jobs()),1);self.assertEqual(self.h.jobs()[0]['identity'],'123')
    def test_old_last_project_during_preparation_does_not_finish_new_job(self):
        self.info(state='init',task=9)
        self.h.observe(self.ip,'info',{'code':200,'data':{'state':'busy','project':None,'last_project':{'state':'finished','task_id':9,'filename':'test.gcode'}}},{'data':{'print_state':'init'}})
        self.assertIsNone(self.h.jobs()[0]['ended_at'])
    def test_jobs_are_printer_specific_and_ack_ignored(self):
        self.info();self.h.observe('192.168.1.102','print',{'state':'done','data':{}},{'data':{}})
        self.assertEqual(len(self.h.jobs()),1);self.assertEqual(self.h.jobs('192.168.1.102'),[])
    def test_fault_is_recorded_without_ending_or_cancelling_job(self):
        self.info()
        self.h.observe(self.ip,'print',{'code':10125,'state':'pause','msg':'Filament warning','data':{}},{'data':{}})
        self.assertEqual(self.h.jobs()[0]['state'],'paused')
        self.assertIsNone(self.h.jobs()[0]['ended_at'])
        self.assertEqual(self.h.events()[0]['kind'],'printer_error')

if __name__=='__main__':unittest.main()
