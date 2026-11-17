"""Check the real PI CLI session and workbench commands without a model request."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wb', REPO / 'scripts/workbench.py')
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--mode', choices=('seep', 'apk', 'exe', 'all'), default='all')
    args = parser.parse_args()
    state = wb.load_state(args.root)
    mode = args.mode
    if mode not in wb.pi_modes(state):
        raise RuntimeError('Mode not installed')
    command = [state['node'], state['pi']['cli'], '--mode', 'rpc', '--no-session', '--no-skills']
    skills = wb.read_json(Path(state['content']) / 'sources.json')['skills']
    selected = skills.values() if mode in ('seep', 'all') else [skills[mode + '-reverse']]
    for directory in selected:
        command += ['--skill', directory]
    env = wb.pi_environment(state, mode)
    env['PI_OFFLINE'] = '1'
    # CLI background diagnostics are private; only bounded protocol evidence is reported.
    process = subprocess.Popen(command, cwd=Path(state['root']) / 'pi', env=env,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               creationflags=0x08000000 if os.name == 'nt' else 0)
    records = queue.Queue()
    def read():
        for line in process.stdout:
            try:
                records.put(json.loads(line))
            except ValueError:
                pass
        records.put(None)
    threading.Thread(target=read, daemon=True).start()
    def request(value):
        process.stdin.write((json.dumps(value) + '\n').encode())
        process.stdin.flush()
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            record = records.get(timeout=max(0.1, deadline - time.monotonic()))
            if record is None:
                raise RuntimeError('PI RPC ended before the response')
            if record.get('type') == 'response' and record.get('id') == value['id']:
                if not record.get('success'):
                    raise RuntimeError('PI command failed: ' + value['type'])
                return record.get('data', {})
        raise RuntimeError('PI RPC timed out')
    try:
        commands = request({'id': 'commands', 'type': 'get_commands'})
        names = {item['name'] for item in commands['commands']}
        if not {'lab', 'exit-lab'}.issubset(names):
            raise RuntimeError('Workbench extension commands were not loaded by the actual CLI')
        for name in ('lab', 'exit-lab'):
            result = request({'id': name, 'type': 'prompt', 'message': '/' + name})
            if result.get('disposition') != 'handled':
                raise RuntimeError('PI did not handle /' + name + ' locally')
        print(json.dumps({'ok': True, 'mode': mode, 'commands': ['lab', 'exit-lab'], 'modelRequest': False}))
    finally:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
        else:
            process.terminate()
        process.wait(timeout=20)


if __name__ == '__main__':
    main()
