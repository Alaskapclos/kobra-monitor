from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from monitor import Telemetry
from history import History
from suite.readiness import assess_fleet, same_idle_state


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.
        self.telemetry = Telemetry('192.0.2.1', clock=lambda: self.now)
        self.telemetry.connected = True
        self.epoch = 'fixture-connection'
        self.telemetry.motion.receive('info', {'data': {'state': 'free', 'project': None}}, self.epoch)
        self.jobs = []
        self.fleet = SimpleNamespace(ips=['192.0.2.1'],
            monitors={'192.0.2.1': SimpleNamespace(telemetry=self.telemetry,
                client=SimpleNamespace(control_connection_id=lambda: self.epoch))},
            history=SimpleNamespace(has_active_jobs=lambda: any(j.get('ended_at') is None for j in self.jobs)))

    def test_active_job_older_than_ui_history_limit_still_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            history = History(Path(folder) / 'history.sqlite3')
            try:
                for i in range(60):
                    history.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (str(i).zfill(32), '192.0.2.1', '', 'fixture.gcode', 'completed',
                         i + 1, i + 1, None if i == 0 else i + 1, 1, 20, 2, 10, 5))
                history.db.commit()
                self.assertEqual(len(history.jobs()), 50)
                self.assertTrue(all(j['ended_at'] is not None for j in history.jobs()))
                self.fleet.history = history
                self.assertFalse(self.assess().ready)
                history.db.execute('UPDATE jobs SET ended_at=100 WHERE ended_at IS NULL')
                history.db.commit()
                self.assertTrue(self.assess().ready)
            finally:
                history.close()

    def assess(self):
        return assess_fleet(self.fleet, clock=lambda: self.now)

    def test_fresh_explicit_idle_works_without_enabling_motion_controls(self):
        first = self.assess()
        self.assertTrue(first.ready)
        self.assertTrue(same_idle_state(first, self.assess(), clock=lambda: self.now))

    def test_active_job_blocks_even_with_reported_idle_or_removed_printer(self):
        self.jobs.append({'ended_at': None})
        self.assertFalse(self.assess().ready)
        self.fleet.ips = []
        self.assertFalse(self.assess().ready)

    def test_print_preparation_pause_and_transitions_do_not_mean_idle(self):
        for phase in ['printing', 'paused', 'auto_leveling', 'checking', 'resuming', 'stopping']:
            self.telemetry.motion.receive('info', {'data': {'state': 'busy',
                'project': {'state': phase}}}, self.epoch)
            with self.subTest(phase=phase):
                self.assertFalse(self.assess().ready)

    def test_offline_reconnect_unknown_stale_or_missing_device_blocks(self):
        self.telemetry.connected = False
        self.assertFalse(self.assess().ready)
        self.telemetry.connected = True
        self.epoch = 'different-connection'
        self.assertFalse(self.assess().ready)
        self.epoch = 'fixture-connection'
        self.now += 16
        self.assertFalse(self.assess().ready)
        self.fleet.monitors.clear()
        self.assertFalse(self.assess().ready)

    def test_new_print_invalidates_prepared_plan_even_if_idle_returns(self):
        first = self.assess()
        self.telemetry.motion.receive('info', {'data': {'state': 'busy',
            'project': {'state': 'printing'}}}, self.epoch)
        self.telemetry.motion.receive('info', {'data': {'state': 'free', 'project': None}}, self.epoch)
        self.assertTrue(self.assess().ready)
        self.assertFalse(same_idle_state(first, self.assess(), clock=lambda: self.now))

    def test_cached_check_expires_and_clean_first_install_can_be_planned(self):
        first = self.assess()
        self.assertFalse(same_idle_state(first, first, clock=lambda: self.now + 3))
        self.fleet.ips = []
        self.assertTrue(self.assess().ready)
        self.fleet.ips = ['192.0.2.1', '192.0.2.1']
        self.assertFalse(self.assess().ready)


if __name__ == '__main__':
    unittest.main()
