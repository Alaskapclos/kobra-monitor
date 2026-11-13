from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch, call

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import macos_entry
import desktop_entry
from suite.native_upgrade import TARGET


class MacUpgradeRoutingTests(unittest.TestCase):
    def run_main(self, mode, chosen):
        self.bundle = Path('/fixture/app/Contents/Resources/payload')
        self.old = Path('/fixture/old-data');self.new = Path('/fixture/new-data')
        self.patches = [patch.object(macos_entry.sys, 'platform', 'darwin'),
            patch.object(sys, 'argv', ['macos_entry.py', '--bundle', str(self.bundle), '--data', str(self.old),
                                     '--mode', mode, '--no-browser']),
            patch.object(macos_entry, 'load_manifest', return_value={'version': TARGET}),
            patch.object(macos_entry, 'choose_profile', return_value=self.new if chosen else None),
            patch.object(macos_entry, 'controller_request', return_value={'monitor_url': 'http://127.0.0.1:19999/'}),
            patch.object(macos_entry, 'run_worker')]
        values = []
        for item in self.patches:values.append(item.start());self.addCleanup(item.stop)
        macos_entry.main()
        return values[3], values[4], values[5]

    def test_cancel_never_launches_or_contacts_the_old_profile(self):
        chooser, controller, worker = self.run_main('start', False)
        controller.assert_not_called();worker.assert_not_called()
        self.assertEqual(chooser.call_args.args[0], self.old)

    def test_start_reopens_only_the_chosen_new_profile(self):
        chooser, controller, worker = self.run_main('start', True)
        controller.assert_called_once_with(self.new);worker.assert_not_called()
        self.assertFalse(chooser.call_args.kwargs['stopping'])

    def test_stop_is_routed_to_new_profile_without_triggering_migration(self):
        chooser, controller, worker = self.run_main('stop', True)
        self.assertTrue(chooser.call_args.kwargs['stopping'])
        self.assertEqual(controller.call_args_list, [call(self.new), call(self.new, 'stop')])
        worker.assert_not_called()

    def test_background_worker_never_shows_a_migration_dialog(self):
        chooser, controller, worker = self.run_main('worker', True)
        chooser.assert_not_called();controller.assert_not_called()
        self.assertEqual(worker.call_args.args[1], self.old)


class WindowsUpgradeRoutingTests(unittest.TestCase):
    def run_main(self, mode):
        self.bundle = Path('/fixture/windows-app');self.old = Path('/fixture/old-data');self.new = Path('/fixture/new-data')
        names = ['load_manifest', 'choose_profile', 'start', 'message', 'controller_request', 'InstallationLock', 'supervise']
        values = {}
        for name in names:
            item = patch.object(desktop_entry, name);values[name] = item.start();self.addCleanup(item.stop)
        values['load_manifest'].return_value = {'version': TARGET}
        values['choose_profile'].return_value = self.new
        values['message'].return_value = True
        values['InstallationLock'].return_value.acquire.return_value = True
        for item in [patch.object(desktop_entry, 'os', SimpleNamespace(name='nt', environ={})),
                     patch.object(sys, 'argv', ['desktop_entry.py', '--bundle', str(self.bundle), '--data', str(self.old), '--mode', mode])]:
            item.start();self.addCleanup(item.stop)
        desktop_entry.main()
        return values

    def test_new_program_integrity_is_checked_before_starting_selected_profile(self):
        spies = self.run_main('start')
        spies['load_manifest'].assert_called_once_with(self.bundle, verify=True)
        spies['start'].assert_called_once_with(self.bundle, self.new, {'version': TARGET})
        spies['controller_request'].assert_not_called()

    def test_stop_cannot_accidentally_stop_the_original_profile(self):
        spies = self.run_main('stop')
        self.assertTrue(spies['choose_profile'].call_args.kwargs['stopping'])
        spies['controller_request'].assert_called_once_with(self.new, 'stop')
        spies['start'].assert_not_called()

    def test_worker_keeps_version_guard_and_never_prompts_for_transfer(self):
        spies = self.run_main('worker')
        spies['choose_profile'].assert_not_called()
        spies['supervise'].assert_called_once_with(self.bundle, self.old, TARGET)


if __name__ == '__main__':unittest.main()
