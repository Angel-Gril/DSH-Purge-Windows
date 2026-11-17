import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import subprocess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workbench', ROOT / 'scripts/workbench.py')
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)


class ProfilePreservation(unittest.TestCase):
    def test_existing_provider_js_tag_and_comments_survive_repeated_deploy(self):
        original = '# private provider\r\n- id: model-provider\r\n  config:\r\n    apiKey: !!js env("MY_KEY")\r\n'
        first = wb.merge_patch(original, '- id: test\n  config: { enabled: true }')
        second = wb.merge_patch(first, '- id: test\n  config: { enabled: false }')
        self.assertIn(original.rstrip('\r\n'), second)
        self.assertEqual(second.count(wb.BEGIN), 1)
        self.assertNotIn('enabled: true', second)
        self.assertIn('enabled: false', second)
        self.assertEqual(second, wb.merge_patch(second, '- id: test\n  config: { enabled: false }'))

    def test_empty_sequence_becomes_valid_block_sequence(self):
        text = wb.merge_patch('# generated\n[]\n', '- id: boot')
        self.assertNotIn('\n[]', text)
        self.assertIn('# generated', text)

    def test_damaged_markers_fail_without_overwriting(self):
        for body in [wb.BEGIN, wb.END, wb.END + '\n' + wb.BEGIN,
                     wb.BEGIN + wb.END + wb.BEGIN + wb.END]:
            with self.subTest(body=body), self.assertRaises(RuntimeError):
                wb.merge_patch(body, '- id: x')

    def test_mapping_layout_is_not_silently_converted(self):
        with self.assertRaises(RuntimeError):
            wb.merge_patch('provider: secret\n', '- id: x')


class Recovery(unittest.TestCase):
    def test_snapshot_restores_files_and_old_state(self):
        with tempfile.TemporaryDirectory(prefix='DSH space-测试-') as temp:
            root = Path(temp)
            home = root / 'home'
            base = home / 'profiles/web'
            base.mkdir(parents=True)
            original = b'# user\n- id: model\n  config: {name: my-model}\n'
            (base / 'cordis.patch.yml').write_bytes(original)
            (base / 'package.json').write_text('{}', encoding='utf-8')
            state = {'root': str(root), 'dshHome': str(home), 'profiles': ['web']}
            previous = {'release': 'old'}
            folder = wb.snapshot(state, root, previous)
            (base / 'cordis.patch.yml').write_text('- id: wrong', encoding='utf-8')
            (base / 'pnpm-lock.yaml').write_text('new', encoding='utf-8')
            with patch.object(wb, 'dsh') as mocked:
                wb.restore_snapshot(folder, state)
            self.assertEqual((base / 'cordis.patch.yml').read_bytes(), original)
            self.assertFalse((base / 'pnpm-lock.yaml').exists())
            self.assertEqual(wb.read_json(root / 'active.json'), previous)
            mocked.assert_called_once()

    def test_failed_new_profile_is_retained_not_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = {'root': str(root), 'dshHome': str(root / 'home'), 'profiles': ['web']}
            folder = wb.snapshot(state, root, None)
            base = root / 'home/profiles/web'
            base.mkdir(parents=True)
            (base / 'evidence.txt').write_text('keep')
            wb.restore_snapshot(folder, state)
            self.assertFalse(base.exists())
            self.assertEqual(len(list(base.parent.glob('web.failed-*/evidence.txt'))), 1)

    def test_concurrent_deploy_is_rejected_and_lock_released_after_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                with wb.deployment_lock(root):
                    with self.assertRaises(RuntimeError):
                        with wb.deployment_lock(root):
                            pass
                    raise ValueError('simulated failure')
            self.assertFalse((root / 'deployment.lock').exists())


class DesktopAndSources(unittest.TestCase):
    def test_offline_permission_uncertainty_cannot_hide_host_patch_failures(self):
        result = {'state': 'unknown', 'patch': {'missing_file': 0}, 'summary': {
            'host': {'ok': True, 'total': 22}, 'runtime': {'ok': True}, 'layout': {'ok': True},
            'config': {'ok': False}, 'pending': {'patches': 0}, 'broken': {'layers': 0}}}
        self.assertTrue(wb.purge_disk_ready(result))
        result['summary']['pending']['patches'] = 1
        self.assertFalse(wb.purge_disk_ready(result))
        result['summary']['pending']['patches'] = 0
        result['patch']['missing_file'] = 1
        self.assertFalse(wb.purge_disk_ready(result))
        result['patch']['missing_file'] = 0
        result['summary']['host']['total'] = 0
        self.assertFalse(wb.purge_disk_ready(result))

    def test_desktop_initialization_does_not_accept_missing_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            state = {'root': temp, 'dshHome': str(Path(temp) / 'home'), 'profiles': ['desktop'],
                     'desktopExe': str(Path(temp) / 'Desktop.exe')}
            with patch.object(wb, 'environment', return_value={'ELECTRON_RUN_AS_NODE': '1'}), \
                 patch.object(wb, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'did not initialize'):
                    wb.initialize_desktop(state)
                self.assertNotIn('ELECTRON_RUN_AS_NODE', run.call_args.kwargs['env'])
                self.assertIn('--user-data-dir=' + str(Path(temp) / 'desktop-user-data'), run.call_args.args[0])

    def test_initialized_desktop_profile_does_not_launch_gui_during_update(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / 'home'
            package = home / 'profiles/desktop/package.json'
            package.parent.mkdir(parents=True)
            package.write_text('{}')
            with patch.object(wb, 'run') as run:
                wb.initialize_desktop({'dshHome': str(home), 'profiles': ['desktop']})
                run.assert_not_called()

    def test_desktop_management_never_falls_back_to_web_or_global_cli(self):
        with patch.object(wb, 'environment', return_value={}), patch.object(wb, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'official Electron'):
                wb.dsh_invocation({'desktopExe': None}, 'desktop')
            run.assert_not_called()

    def test_desktop_resolver_rejects_another_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = {'desktopExe': str(root / 'chosen/Desktop.exe'), 'plugins': {'purge': str(root / 'purge')}}
            cases = [
                {'command': str(root / 'other/Desktop.exe'), 'cli': str(root / 'chosen/resources/app/cli.js')},
                {'command': state['desktopExe'], 'cli': str(root / 'other/resources/app/cli.js')},
            ]
            for selected in cases:
                selected.update({'args': [], 'env': {}})
                with self.subTest(selected=selected), patch.object(wb, 'environment', return_value={}), \
                     patch.object(wb, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(selected), '')):
                    with self.assertRaises(RuntimeError):
                        wb.dsh_invocation(state, 'desktop')

    def test_uninstalled_surface_cannot_patch_a_host(self):
        with patch.object(wb, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'not installed'):
                wb.purge_command({'profiles': ['web']}, 'desktop', 'apply')
            run.assert_not_called()

    def test_canonical_skill_replaces_duplicates_in_both_roots_and_retains_originals(self):
        with tempfile.TemporaryDirectory() as temp:
            generation = Path(temp) / 'deployment'
            content = generation / 'content'
            for relative in ('skill/apk-reverse', 'safe-skills/apk-reverse'):
                folder = content / relative
                folder.mkdir(parents=True)
                (folder / 'SKILL.md').write_text('---\nname: apk-reverse\n---\nOld', encoding='utf-8')
            source = Path(temp) / 'selected'
            (source / 'scripts').mkdir(parents=True)
            (source / 'SKILL.md').write_text('---\nname: apk-reverse\n---\nSelected', encoding='utf-8')
            (source / 'scripts/doctor.py').write_text('print(1)', encoding='utf-8')
            selected = wb.overlay_skill(content, generation, source, 'apk-reverse')
            self.assertEqual(len(list(content.rglob('SKILL.md'))), 1)
            self.assertEqual(len(list((generation / 'upstream-skill-backups').rglob('SKILL.md'))), 2)
            self.assertIn('Selected', (selected / 'SKILL.md').read_text(encoding='utf-8'))
            self.assertTrue((selected / 'scripts/doctor.py').is_file())

    def test_desktop_version_must_satisfy_seep_contract(self):
        for version in ['0.2.2-rc.3']:
            self.assertTrue(wb.compatible_desktop(version))
        for version in ['0.2.1-rc.5', '0.2.2-rc.1', '0.2.2', '0.2.2-rc.4', '0.2.2-alpha.2', '0.3.0', 'unknown', '0.2.2-rc.0']:
            self.assertFalse(wb.compatible_desktop(version))

    def test_read_asar_metadata_without_unpack(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'app.asar'
            payload = b'{"version":"0.2.2-rc.3"}'
            header = json.dumps({'files': {'package.json': {'size': len(payload), 'offset': '0'}}}).encode()
            padding = b'\0' * ((4 - len(header) % 4) % 4)
            header_size = 8 + len(header) + len(padding)
            file.write_bytes(struct.pack('<IIII', 4, header_size, header_size - 4, len(header)) + header + padding + payload)
            self.assertEqual(wb.read_asar_json(file, 'package.json')['version'], '0.2.2-rc.3')

    def test_lock_has_all_sources_without_credentials(self):
        lock = wb.read_json(ROOT / 'sources.lock.json')
        self.assertEqual({x['id'] for x in lock['sources']}, {'seep', 'apk', 'exe', 'purge'})
        for item in lock['sources']:
            self.assertRegex(item['commit'], r'^[a-f0-9]{40}$')
            self.assertRegex(item['url'], r'^https://github\.com/[^@]+\.git$')

    def test_runtime_lock_includes_required_dsh_peers(self):
        packages = wb.read_json(ROOT / 'runtime/package-lock.json')['packages']
        missing = []
        for path, package in packages.items():
            if not path.startswith('node_modules/@deepseek-ai/'):
                continue
            for name in package.get('peerDependencies', {}):
                if package.get('peerDependenciesMeta', {}).get(name, {}).get('optional'):
                    continue
                if name.startswith('@deepseek-ai/') and 'node_modules/' + name not in packages:
                    missing.append((path, name))
        self.assertEqual(missing, [], 'Required peer modules must be explicit in the legacy-peer-deps runtime')


if __name__ == '__main__':
    unittest.main()
