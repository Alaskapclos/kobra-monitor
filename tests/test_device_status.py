"""Received peripheral fields must never inherit bridge defaults or false freshness."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from monitor import Telemetry

class DeviceStatusTests(unittest.TestCase):
    def setUp(self):
        self.now = 10
        self.t = Telemetry('192.0.2.1', clock=lambda: self.now)
        self.b = SimpleNamespace(_state={'fan_speed':100, 'light_on':True, 'print_speed_mode':2})
    def send(self, kind, data, code=200):
        self.t.receive(kind, {'code':code,'data':dict(data, type=2) if kind=='light' and 'lights' not in data else data}, self.b)
    def values(self): return self.t.snapshot()['device_status']
    def test_defaults_and_acks_are_not_measurements(self):
        self.send('info', {})
        self.send('light', {})
        self.assertEqual(self.values(), {})
    def test_zero_and_off_are_real_values(self):
        self.send('info', {'fan_speed_pct':0,'aux_fan_speed_pct':0,'box_fan_level':0,'print_speed_mode':2})
        self.send('light', {'status':0,'brightness':0})
        self.assertEqual(self.values()['fan_speed']['value'], 0)
        self.assertIs(self.values()['light_on']['value'], False)
        self.assertEqual(len(self.values()), 6)
    def test_invalid_values_do_not_refresh(self):
        self.send('info', {'fan_speed_pct':20})
        self.now += 15
        for bad in [True, '0', -1, 101, float('nan'), float('inf'), None]:
            self.send('info', {'fan_speed_pct':bad})
        self.assertEqual(self.values()['fan_speed'], {'value':20,'age_s':15,'current_session':True})
        for bad in ['0', 2, None]: self.send('light', {'status':bad})
        self.assertNotIn('light_on', self.values())
    def test_partial_reports_and_ack_preserve_independent_ages(self):
        self.send('light', {'status':True,'brightness':80})
        self.now += 100
        self.send('light', {'status':False})
        self.send('info', {'fan_speed_pct':50})
        self.assertEqual(self.values()['light_on']['age_s'], 0)
        self.assertEqual(self.values()['light_brightness']['age_s'], 100)
    def test_print_settings_mode_without_progress(self):
        self.send('print', {'settings':{'print_speed_mode':3}})
        self.assertEqual(self.values()['speed_mode']['value'], 3)
        self.send('print', {'settings':{'print_speed_mode':1.2}})
        self.assertEqual(self.values()['speed_mode']['value'], 3)
    def test_light_array_selects_chamber_and_rejects_ambiguous_reports(self):
        self.send('light', {'lights':[{'type':1,'status':0},{'type':2,'status':1,'brightness':100}]})
        self.assertIs(self.values()['light_on']['value'],True)
        self.now+=10
        self.send('light', {'lights':[{'type':2,'status':0},{'type':2,'status':1}]})
        self.assertEqual(self.values()['light_on']['age_s'],10)
    def test_failed_report_is_ignored(self):
        self.send('light', {'status':1}, code=500)
        self.assertEqual(self.values(), {})
    def test_reconnect_does_not_revive_old_fields(self):
        self.t.link(True)
        self.send('light', {'status':1})
        self.t.link(False); self.t.link(True)
        self.send('info', {'fan_speed_pct':20})
        self.assertFalse(self.values()['light_on']['current_session'])
        self.assertTrue(self.values()['fan_speed']['current_session'])
    def test_snapshot_is_detached_and_private_keys_excluded(self):
        self.send('info', {'fan_speed_pct':20,'password':'SECRET'})
        s=self.values();s['fan_speed']['value']=99
        self.assertEqual(self.values()['fan_speed']['value'],20)
        self.assertNotIn('SECRET', str(self.t.snapshot()))

if __name__=='__main__':unittest.main()
