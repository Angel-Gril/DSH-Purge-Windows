"""Real isolated PI deployment, optional verified source cache; no model credentials.

python tests/integration_pi.py --root C:/AI/PiTest --modules pi,apk,exe \
    --source-cache C:/AI/ExistingWorkbench
"""
import argparse
import importlib.util
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wb', REPO / 'scripts/workbench.py')
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--modules', default='pi,seep,apk,exe')
    parser.add_argument('--source-cache')
    parser.add_argument('--reconfigure', action='store_true', help='Extend an existing PI-only test deployment')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if root == REPO or root in REPO.parents or ((root / 'active.json').exists() and not args.reconfigure):
        raise RuntimeError('Use a fresh independent test root')
    if args.reconfigure and ((root / 'dsh-home').exists() or wb.load_state(root).get('profiles')):
        raise RuntimeError('Reconfiguration test requires a PI-only test root')
    selected = wb.resolve_modules(args.modules)
    if 'dsh' in selected or 'pi' not in selected:
        raise RuntimeError('This test requires standalone PI')
    if args.source_cache:
        for item in wb.read_json(REPO / 'sources.lock.json')['sources']:
            if item['id'] not in selected:
                continue
            source = Path(args.source_cache).resolve() / 'sources' / item['id'] / item['commit']
            wb.verify_source(source, item)
            target = root / 'sources' / item['id'] / item['commit']
            if target.exists():
                wb.verify_source(target, item)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            wb.run(['git', '-c', 'core.longpaths=true', '-c', 'advice.detachedHead=false',
                    'clone', '--quiet', '--no-hardlinks', source, target])
            wb.run(['git', '-C', target, 'remote', 'set-url', 'origin', item['url']])
            wb.run(['git', '-C', target, 'config', 'core.longpaths', 'true'])
    wb.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            REPO / 'install.ps1', '-Root', root, '-Modules', args.modules], timeout=3600)
    state = wb.load_state(root)
    assert not state['profiles'] and not state['plugins'] and state['runtime'] is None
    assert not (root / 'dsh-home').exists()
    assert set(state['sources']) == set(selected) - {'pi'}
    for mode in wb.pi_modes(state):
        wb.run([sys.executable, REPO / 'scripts/workbench.py', 'start-pi', '--root', root,
                '--pi-mode', mode, '--', '--version'], capture=True)
    wb.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            REPO / 'doctor.ps1', '-Root', root, '-ProbeMcp'], timeout=1200)
    invalid = wb.run([sys.executable, REPO / 'scripts/workbench.py', 'start', '--root', root],
                     capture=True, check=False)
    assert invalid.returncode != 0
    print('PI deployment, resource loading, doctor and missing-DSH boundary passed.')


if __name__ == '__main__':
    main()
