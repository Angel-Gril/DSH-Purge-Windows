import argparse
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
from test_workbench import wb


class ModuleContract(unittest.TestCase):
    def test_native_mcp_check_rejects_disconnected_services_and_redacts_private_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            agent = Path(temp) / 'pi/agent'
            wb.save_json(agent / 'workbench-managed.json', {'servers': {'seep': {}}})
            state = {'root': temp, 'node': 'node', 'pi': {'agent': str(agent), 'cli': 'pi.js'}}
            data = {'servers': [{'name': 'seep', 'enabled': True, 'state': 'failed',
                                 'tools': [], 'error': 'request timed out PRIVATE_SENTINEL'}], 'errors': []}
            with patch.object(wb, 'pi_environment', return_value={}), patch.object(wb, 'run',
                 return_value=subprocess.CompletedProcess([], 1, json.dumps(data), '')):
                with self.assertRaises(RuntimeError) as captured:
                    wb.pi_mcp_check(state)
            self.assertIn('seep=failed/timeout', str(captured.exception))
            self.assertNotIn('PRIVATE_SENTINEL', str(captured.exception))
            data['servers'][0].update(state='connected', tools=['seep_status'])
            with patch.object(wb, 'pi_environment', return_value={}), patch.object(wb, 'run',
                 return_value=subprocess.CompletedProcess([], 0, json.dumps(data), '')):
                result = wb.pi_mcp_check(state)
            self.assertEqual(result['servers'], [{'name': 'seep', 'state': 'connected', 'tools': 1}])

    def test_pi_environment_keeps_tool_directories_and_removes_dsh_targets(self):
        state = {'root': 'C:/test', 'sources': {}, 'content': 'C:/content', 'python': 'C:/python.exe',
                 'pi': {'agent': 'C:/test/pi/agent'}}
        with patch.dict(os.environ, {'APKREV_TOOLS': 'D:/android-tools', 'EXEREV_TOOLS': 'D:/native-tools',
                                     'DSH_BASE': 'C:/another-host', 'PURGE_DSH_CLI': 'other.js'}):
            env = wb.pi_environment(state, 'coding')
        self.assertIn('D:/android-tools', env['APKREV_TOOLS'])
        self.assertIn('D:/native-tools', env['EXEREV_TOOLS'])
        self.assertNotIn('DSH_BASE', env)
        self.assertNotIn('PURGE_DSH_CLI', env)

    def test_default_is_full_dsh_without_pi(self):
        self.assertEqual(wb.resolve_modules(None, False), ['dsh', 'purge', 'seep', 'apk', 'exe'])

    def test_pi_apk_has_no_dsh_or_seep_dependency(self):
        self.assertEqual(wb.resolve_modules('pi,apk', False), ['pi', 'apk'])

    def test_dsh_skills_use_native_seep_connector_and_purge(self):
        self.assertEqual(wb.resolve_modules('dsh,exe', False), ['dsh', 'purge', 'seep', 'exe'])

    def test_invalid_or_hostless_selection_fails(self):
        for value in ('', 'apk', 'purge', 'dhs', 'pi,,apk'):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                wb.resolve_modules(value, False)

    def test_pi_config_keeps_user_models_settings_and_mcp(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            agent = root / 'pi/agent'
            agent.mkdir(parents=True)
            wb.save_json(agent / 'settings.json', {'defaultModel': 'mine', 'extensions': ['custom.ts']})
            wb.save_json(agent / 'mcp.json', {'mcpServers': {'mine': {'url': 'https://example.invalid/mcp'}}})
            (agent / 'models.json').write_text('private', encoding='utf-8')
            generation = root / 'generation'
            generation.mkdir()
            state = {'root': str(root), 'generation': str(generation), 'sources': {},
                     'content': str(generation / 'content'), 'modules': ['pi'], 'node': 'node'}
            wb.configure_pi(state)
            self.assertEqual(wb.read_json(agent / 'settings.json')['defaultModel'], 'mine')
            self.assertIn('custom.ts', wb.read_json(agent / 'settings.json')['extensions'])
            self.assertIn('mine', wb.read_json(agent / 'mcp.json')['mcpServers'])
            self.assertEqual((agent / 'models.json').read_text(), 'private')
            self.assertNotIn('seep', wb.read_json(agent / 'mcp.json')['mcpServers'])

    def test_pi_launch_rejects_uninstalled_mode_and_preserves_cwd(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = {'root': temp, 'modules': ['pi'], 'sources': {}, 'python': 'python',
                     'content': str(root / 'content'), 'node': 'node',
                     'pi': {'cli': str(root / 'cli.js'), 'agent': str(root / 'agent')}}
            args = argparse.Namespace(root=temp, pi_mode='apk', project=temp, app_args=['--version'])
            with patch.object(wb, 'load_state', return_value=state), patch.object(wb, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'not installed'):
                    wb.start_pi(args)
                run.assert_not_called()
                args.pi_mode = 'coding'
                run.return_value.returncode = 0
                self.assertEqual(wb.start_pi(args), 0)
                call = run.call_args
                self.assertEqual(call.kwargs['cwd'], root.resolve())
                self.assertTrue(call.kwargs['interactive'])
                self.assertIn('--no-mcp', call.args[0])
                self.assertNotIn('--approve', call.args[0])
                self.assertEqual(call.kwargs['env']['PI_CODING_AGENT_DIR'], state['pi']['agent'])

    def test_pi_snapshot_restores_configuration_without_touching_model_or_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            agent = root / 'pi/agent'
            agent.mkdir(parents=True)
            wb.save_json(agent / 'settings.json', {'defaultModel': 'old'})
            (agent / 'models.json').write_text('user models', encoding='utf-8')
            state = {'root': temp, 'dshHome': str(root / 'unused-home'), 'profiles': [], 'modules': ['pi']}
            snapshot = wb.snapshot(state, root, {'previous': True})
            wb.save_json(agent / 'settings.json', {'defaultModel': 'new'})
            wb.save_json(agent / 'mcp.json', {'mcpServers': {}})
            wb.restore_snapshot(snapshot, state)
            self.assertEqual(wb.read_json(agent / 'settings.json')['defaultModel'], 'old')
            self.assertFalse((agent / 'mcp.json').exists())
            self.assertEqual((agent / 'models.json').read_text(), 'user models')


if __name__ == '__main__':
    unittest.main()
