"""Explicit local integration test; uses only a new Root, never the normal DSH_HOME.

Run after installation: python tests/integration.py --root <isolated-test-root>
Optional --desktop-exe exercises its real management CLI, never the Electron UI.
"""
import argparse
import copy
import importlib.util
from pathlib import Path
import subprocess
import time
import urllib.request
import urllib.error
import json
import os
import http.cookiejar
import re

spec = importlib.util.spec_from_file_location('workbench', Path(__file__).resolve().parents[1] / 'scripts/workbench.py')
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--port', type=int, default=18736)
    parser.add_argument('--startup-timeout', type=int, default=600)
    parser.add_argument('--desktop-exe', help='Only manage the isolated profile; do not start or patch this installation')
    parser.add_argument('--skip-registration', action='store_true', help='Probe an already configured deployment')
    args = parser.parse_args()
    state = wb.load_state(args.root)
    if Path(state['dshHome']).resolve() != (Path(args.root).resolve() / 'dsh-home'):
        raise RuntimeError('Integration tests require the isolated root/dsh-home')
    state = copy.deepcopy(state)
    state['profiles'] = ['web']
    if args.desktop_exe:
        state['desktopExe'] = str(Path(args.desktop_exe).resolve())
        state['profiles'].append('desktop')
    # Exercise real CLI registrations; no desktop runtime patching or version bypass in install.
    if not args.skip_registration:
        wb.configure_profiles(state)
    for profile in state['profiles']:
        text = (Path(state['dshHome']) / 'profiles' / profile / 'cordis.patch.yml').read_text(encoding='utf-8')
        if text.count(wb.BEGIN) != 1:
            raise RuntimeError('Non-idempotent profile merge')
    report = {'profileRegistration': state['profiles'], 'registrationRepeated': not args.skip_registration,
              'desktopGui': 'not-tested', 'http': {}}
    # Local acceptance must reach this process directly, even with an exported proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    log = Path(state['root']) / 'reports/integration-web.log'
    with log.open('wb') as output:
        # --port is an app-level flag, not a launcher flag.
        process = subprocess.Popen([state['node'], state['cli'], '--profile', 'web', '--port', str(args.port), '--no-open'],
                                   cwd=state['root'], env=wb.environment(state), stdout=output, stderr=output,
                                   creationflags=0x08000000 if os.name == 'nt' else 0)
        print(f'[web] PID {process.pid}; waiting for http://127.0.0.1:{args.port}/', flush=True)
        try:
            deadline = time.monotonic() + args.startup_timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Web process exited; inspect the private integration log')
                try:
                    # The fresh host prints its one-time local bootstrap URL.
                    # Use it privately to establish the same cookie as a browser.
                    private_log = log.read_text(encoding='utf-8', errors='replace')
                    bootstrap = re.search(r'http://127\.0\.0\.1:' + str(args.port) + r'/\?token=[A-Za-z0-9_-]+', private_log)
                    url = bootstrap.group(0) if bootstrap else f'http://127.0.0.1:{args.port}/'
                    with opener.open(url, timeout=5) as response:
                        report['http']['root'] = response.status
                    break
                except urllib.error.HTTPError as error:
                    # The server binds before the frontend fallback and auth
                    # bootstrap finish mounting. Wait for the official URL.
                    if error.code in (401, 404, 503) and not bootstrap:
                        time.sleep(1)
                        continue
                    raise RuntimeError(f'Web answered HTTP {error.code}; verify host authentication and routing') from None
                except OSError:
                    time.sleep(1)
            else:
                raise RuntimeError('Web startup timed out; inspect the private integration log')
            for name, path in [('seep', '/seep-workbench/api?skills=1'), ('purge', '/dsh-purge/status')]:
                with opener.open(f'http://127.0.0.1:{args.port}' + path, timeout=30) as response:
                    data = json.load(response)
                    if data.get('ok') is False:
                        raise RuntimeError(name + ' plugin returned a failure response')
                    report['http'][name] = {'status': response.status, 'ok': data.get('ok'),
                                            'topLevelKeys': sorted(data.keys())[:16]}
        finally:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
            else:
                process.terminate()
            process.wait(timeout=15)
    wb.save_json(Path(state['root']) / 'reports/integration.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
