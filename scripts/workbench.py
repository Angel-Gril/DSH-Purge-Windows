"""Windows workbench deployer. Python stdlib only until the isolated venv exists.

State and credentials belong to the target machine, never this Git repository.
All external processes use argument arrays; shell interpolation is prohibited.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
import uuid

REPO = Path(__file__).resolve().parents[1]
BEGIN = '# BEGIN DSH-WINDOWS-WORKBENCH v1'
END = '# END DSH-WINDOWS-WORKBENCH v1'
PROFILE_FILES = ('package.json', 'pnpm-lock.yaml', 'cordis.patch.yml', 'pnpm-workspace.yaml')
DEFAULT_MODULES = ['dsh', 'purge', 'seep', 'apk', 'exe']
MODULE_ORDER = ['dsh', 'purge', 'pi', 'seep', 'apk', 'exe']


def resolve_modules(value=None, with_pi=False):
    selected = set(DEFAULT_MODULES if value is None else [x.strip().lower() for x in value.split(',')])
    if with_pi:
        selected.add('pi')
    if not selected.issubset(MODULE_ORDER) or not selected.intersection({'dsh', 'pi'}):
        raise RuntimeError('Select a host (dsh or pi) and modules: dsh,purge,pi,seep,apk,exe')
    if 'purge' in selected and 'dsh' not in selected:
        raise RuntimeError('Purge requires the DSH host')
    if 'dsh' in selected:
        selected.add('purge')  # DSH + Purge is this workbench host unit.
        if selected.intersection({'apk', 'exe'}):
            selected.add('seep')  # Native DSH skill connector.
    return [x for x in MODULE_ORDER if x in selected]


def modules_of(state):
    return state.get('modules', DEFAULT_MODULES)


def read_json(file: Path):
    return json.loads(file.read_text(encoding='utf-8-sig'))


def save_json(file: Path, data):
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_name(file.name + '.tmp-' + uuid.uuid4().hex)
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(file)


def digest(file: Path):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def run(args, *, cwd=None, env=None, capture=False, timeout=1800, check=True, interactive=False):
    argv = [str(x) for x in args]
    # Windows .cmd needs CreateProcess's standard handling, never shell=True.
    process = subprocess.Popen(argv, cwd=cwd, env=env, text=True, encoding='utf-8', errors='replace',
                               stdout=subprocess.PIPE if capture else sys.stdout,
                               stderr=subprocess.PIPE if capture else sys.stderr,
                               creationflags=0x08000000 if os.name == 'nt' and not interactive else 0)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
        else:
            process.kill()
        process.communicate()
        raise
    completed = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    if check and completed.returncode:
        # Captured config dumps may contain credentials. Never echo captured output.
        raise RuntimeError(f'{Path(argv[0]).name} failed (exit {completed.returncode}); '
                           'captured private output omitted' if capture else
                           f'{Path(argv[0]).name} failed (exit {completed.returncode})')
    return completed


def executable(name):
    found = shutil.which(name + '.cmd' if os.name == 'nt' and name == 'npm' else name)
    if not found:
        raise RuntimeError('Missing prerequisite: ' + name)
    return found


def strip_block(text):
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise RuntimeError('Managed block markers are damaged; repair the profile before retrying')
    if BEGIN in text:
        start, end = text.index(BEGIN), text.index(END) + len(END)
        if end < start:
            raise RuntimeError('Managed block markers are reversed')
        text = text[:start] + text[end:].lstrip('\r\n')
    return text


def merge_patch(original, block):
    """Preserve user bytes, comments, !!js and provider settings outside our block."""
    body = strip_block(original)
    meaningful = [x.strip() for x in body.splitlines() if x.strip() and not x.lstrip().startswith('#')]
    if meaningful == ['[]']:
        body = '\n'.join(x for x in body.splitlines() if x.strip() != '[]') + '\n'
    elif meaningful and not meaningful[0].startswith('-'):
        raise RuntimeError('Unsupported YAML layout. Use a block sequence profile overlay.')
    return body.rstrip('\r\n') + '\n\n' + BEGIN + '\n' + block.rstrip() + '\n' + END + '\n'


def profile_block(state):
    q = lambda x: json.dumps(str(x), ensure_ascii=False)
    block = f'''- id: seep-workbench-boot
  disabled: false
  config:
    repoRoot: {q(state['sources']['seep'])}
    pythonPath: {q(state['python'])}
    contentRoot: {q(state['content'])}
    enableSkills: true
    labGate: true
    enableIda: {str(state['options']['with_ida']).lower()}
    enablePlaywright: {str(state['options']['with_playwright']).lower()}
''' if 'seep' in state['plugins'] else ''
    return block + '''- id: dsh-purge
  disabled: false
  config:
    enabled: true
    autoApplyOnStart: false
    autoUpdateOnStart: false
- id: dsh-purge-redteam
  disabled: false
- id: dsh-purge-presets
  disabled: false
- id: dsh-purge-redteam-store
  disabled: false
- id: dsh-purge-redteam-ui
  disabled: false
'''


@contextlib.contextmanager
def deployment_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    file = root / 'deployment.lock'
    try:
        fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        raise RuntimeError(f'Deployment lock exists: {file}. If its PID has exited, remove this file manually.')
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        file.unlink(missing_ok=True)


def source_checkout(root, item):
    destination = root / 'sources' / item['id'] / item['commit']
    if destination.exists():
        actual = run(['git', '-C', destination, 'rev-parse', 'HEAD'], capture=True).stdout.strip()
        dirty = run(['git', '-C', destination, 'status', '--porcelain', '--untracked-files=no'], capture=True).stdout
        origin = run(['git', '-C', destination, 'remote', 'get-url', 'origin'], capture=True).stdout.strip()
        if actual != item['commit'] or dirty or origin != item['url']:
            raise RuntimeError(f'Source checkout changed; retained without overwriting: {destination}')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(destination.name + '.download-' + uuid.uuid4().hex[:8])
    print(f"[source] {item['id']} @ {item['commit'][:12]}", flush=True)
    run(['git', 'init', '--quiet', staging])
    if os.name == 'nt':
        run(['git', '-C', staging, 'config', 'core.longpaths', 'true'])
    run(['git', '-C', staging, 'remote', 'add', 'origin', item['url']])
    # Git uses its own credential manager. Never accept token-bearing URLs.
    run(['git', '-C', staging, 'fetch', '--depth', '1', 'origin', item['commit']], timeout=3600)
    run(['git', '-C', staging, 'checkout', '--quiet', '--detach', 'FETCH_HEAD'])
    actual = run(['git', '-C', staging, 'rev-parse', 'HEAD'], capture=True).stdout.strip()
    if actual != item['commit']:
        raise RuntimeError('Fetched source does not match sources.lock.json')
    staging.rename(destination)
    return destination


def verify_source(destination, item):
    destination = Path(destination)
    if not destination.is_dir():
        raise RuntimeError('Source is missing: ' + str(destination))
    actual = run(['git', '-C', destination, 'rev-parse', 'HEAD'], capture=True).stdout.strip()
    dirty = run(['git', '-C', destination, 'status', '--porcelain', '--untracked-files=no'], capture=True).stdout
    if actual != item['commit'] or dirty:
        raise RuntimeError('Source changed: ' + str(destination))
    return actual


def install_runtime(root):
    expected_version = read_json(REPO / 'runtime/package.json')['dependencies']['@deepseek-ai/dsh']
    key = digest(REPO / 'runtime/package-lock.json')[:16]
    target = root / 'runtimes' / key
    target.mkdir(parents=True, exist_ok=True)
    for name in ('package.json', 'package-lock.json'):
        shutil.copy2(REPO / 'runtime' / name, target / name)
    cli = target / 'node_modules/@deepseek-ai/dsh/lib/bin.js'
    if not (target / 'complete.json').exists():
        print('[runtime] Installing locked DSH and JS MCP; bundled native tools can make the first download large.', flush=True)
        run([executable('npm'), 'ci', '--legacy-peer-deps', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=target, timeout=3600)
        if not cli.exists():
            raise RuntimeError('DSH runtime installation is incomplete')
        smoke_env = dict(os.environ, DSH_HOME=str(root / 'dsh-home'))
        version = run([executable('node'), cli, '--version'], env=smoke_env, capture=True).stdout.strip()
        if version != expected_version:
            raise RuntimeError('DSH CLI failed its startup/version check')
        save_json(target / 'complete.json', {'lockSha256': digest(target / 'package-lock.json')})
    if read_json(target / 'node_modules/@deepseek-ai/dsh/package.json')['version'] != expected_version:
        raise RuntimeError('Managed DSH version mismatch')
    return target


def install_python(root):
    key = digest(REPO / 'requirements.txt')[:12] + f'-py{sys.version_info.major}{sys.version_info.minor}'
    target = root / 'python' / key
    python = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not (target / 'complete.json').exists():
        print('[python] Creating/updating the isolated MCP environment.', flush=True)
        if not python.exists():
            run([sys.executable, '-m', 'venv', target])
        run([python, '-m', 'pip', 'install', '--disable-pip-version-check', '-r', REPO / 'requirements.txt'])
        run([python, '-c', 'import mcp'])
        frozen = run([python, '-m', 'pip', 'freeze'], capture=True).stdout
        (target / 'installed-requirements.txt').write_text(frozen, encoding='utf-8')
        save_json(target / 'complete.json', {'requirementsSha256': digest(REPO / 'requirements.txt')})
    return python


def install_node_bundle(root, bundle):
    source = REPO / bundle
    target = root / 'runtimes' / (bundle + '-' + digest(source / 'package-lock.json')[:16])
    target.mkdir(parents=True, exist_ok=True)
    for name in ('package.json', 'package-lock.json'):
        shutil.copy2(source / name, target / name)
    if not (target / 'complete.json').exists():
        print('[runtime] Installing locked ' + bundle, flush=True)
        run([executable('npm'), 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=target, timeout=3600)
        save_json(target / 'complete.json', {'lockSha256': digest(source / 'package-lock.json')})
    return target


def copy_tree(source, destination):
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('.git', 'node_modules', '__pycache__',
                                                                     '.venv', 'venv', '*.pyc', '.env', '.env.*'))


def link_host_dependencies(plugin, runtime):
    # link: packages live outside the profile's node_modules; Seep's manifest
    # does not declare its host imports. Share the exact managed host modules.
    link, target = Path(plugin) / 'node_modules', Path(runtime) / 'node_modules'
    if link.exists() or link.is_symlink():
        raise RuntimeError('Plugin dependency directory already exists; retained')
    if os.name == 'nt':
        run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
             REPO / 'scripts/link-dependencies.ps1', '-Link', link, '-Target', target])
    else:
        link.symlink_to(target, target_is_directory=True)


def skill_name(file):
    text = file.read_text(encoding='utf-8-sig')
    match = re.search(r'^name:\s*[\'"]?([^\r\n\'"]+)', text, re.M)
    return match.group(1).strip() if match else file.parent.name


def overlay_skill(content, generation, source, name):
    """Select a canonical skill across both Seep skill roots, retaining every original."""
    for file in list(content.rglob('SKILL.md')):
        if not file.exists() or skill_name(file) != name:
            continue
        old = file.parent
        backup = generation / 'upstream-skill-backups' / old.relative_to(content)
        if not old.resolve().is_relative_to(content.resolve()) or not backup.resolve().is_relative_to(generation.resolve()):
            raise RuntimeError('Skill overlay path escapes deployment directory')
        backup.parent.mkdir(parents=True, exist_ok=True)
        old.rename(backup)
    target = content / 'skill' / name
    if target.exists():
        raise RuntimeError('Canonical skill target exists without a matching SKILL.md: ' + str(target))
    copy_tree(source, target)
    if not (target / 'SKILL.md').is_file() or skill_name(target / 'SKILL.md') != name:
        raise RuntimeError('Canonical skill has the wrong manifest name: ' + name)
    return target


def build_generation(root, sources, runtime, python, options):
    generation = root / 'deployments' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    content = generation / 'content'
    content.mkdir(parents=True)
    if 'seep' in sources:
        copy_tree(sources['seep'] / 'Tool/skill', content / 'skill')
    nested = content / 'skill/safe-skills'
    if nested.exists():
        nested.rename(content / 'safe-skills')
    # Same-name Seep skills are retained in source; selected Angel-Gril skills win in the overlay.
    mapping = {}
    for item in ('apk', 'exe'):
        if item not in sources:
            continue
        name = item + '-reverse'
        target = overlay_skill(content, generation, sources[item] / 'skills' / name, name)
        if (sources[item] / 'LICENSE').is_file() and not (target / 'LICENSE').exists():
            shutil.copy2(sources[item] / 'LICENSE', target / 'LICENSE')
        if not (target / 'SKILL.md').is_file():
            raise RuntimeError('Missing full skill: ' + name)
        mapping[name] = str(sources[item] / 'skills' / name)
    # A second skill with the same frontmatter name would silently hide one version.
    names = {}
    for skill in content.rglob('SKILL.md'):
        name = skill_name(skill)
        if name in names:
            raise RuntimeError(f'Duplicate skill name: {name}: {names[name]}, {skill}')
        names[name] = str(skill.parent)
    save_json(content / 'sources.json', {'overrides': mapping, 'skills': names})
    plugins = generation / 'plugins'
    plugins.mkdir()
    selected_plugins = {}
    if 'dsh' in options['modules'] and 'seep' in sources:
        seep = plugins / 'seep-lab'
        prepare_seep_plugin(sources['seep'], seep, runtime)
        selected_plugins['seep'] = str(seep)
    if 'purge' in sources:
        purge = plugins / 'dsh-purge-community'
        copy_tree(sources['purge'], purge)
        run([executable('npm'), 'ci', '--omit=dev', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=purge)
        selected_plugins['purge'] = str(purge)
    return {'schemaVersion': 2, 'generation': str(generation), 'root': str(root),
            'modules': options['modules'],
            'sources': {k: str(v) for k, v in sources.items()}, 'runtime': str(runtime) if runtime else None,
            'cli': str(runtime / 'node_modules/@deepseek-ai/dsh/lib/bin.js') if runtime else None,
            'python': str(python), 'content': str(content), 'plugins': selected_plugins,
            'node': executable('node'), 'options': options, 'createdAt': time.time()}


def prepare_seep_plugin(source, seep, runtime):
    copy_tree(source / 'packages/seep-lab', seep)
    # Local compatibility adapter: retain the native UI/lab gate/skills, pin MCP commands.
    # Strict source anchors fail closed when upstream changes instead of guessing.
    file = seep / 'lib/index.js'
    text = file.read_text(encoding='utf-8')
    anchor = "command: 'npx',\n        args: ['-y', 'js-reverse-mcp'],"
    replacement = ('command: ' + json.dumps(executable('node')) + ',\n        args: [' +
                   json.dumps(str(runtime / 'node_modules/js-reverse-mcp/build/src/index.js')) + '],')
    if text.count(anchor) != 1:
        raise RuntimeError('Seep JS MCP adapter anchor changed; review the new upstream source')
    text = text.replace(anchor, replacement)
    # Optional Playwright also uses a fixed npm version, never @latest.
    text = text.replace("'@playwright/mcp@latest'", "'@playwright/mcp@0.0.85'")
    file.write_text(text, encoding='utf-8')
    link_host_dependencies(seep, runtime)


def read_asar_json(file, relative):
    """Read only a small package.json from Electron ASAR; do not unpack or modify it."""
    with file.open('rb') as stream:
        lead = stream.read(16)
        if len(lead) != 16:
            raise ValueError('Invalid ASAR header')
        header_size, string_size = struct.unpack_from('<I', lead, 4)[0], struct.unpack_from('<I', lead, 12)[0]
        if string_size > 64 * 1024 * 1024:
            raise ValueError('ASAR header exceeds limit')
        header = json.loads(stream.read(string_size))
        entry = header
        for part in relative.split('/'):
            entry = entry['files'][part]
        if entry['size'] > 1024 * 1024:
            raise ValueError('ASAR package metadata exceeds limit')
        stream.seek(8 + header_size + int(entry['offset']))
        return json.loads(stream.read(entry['size']))


def desktop_metadata(exe):
    resources = exe.parent / 'resources'
    # Purge may already have moved app.asar aside and activated resources/app.
    app = resources / 'app/package.json'
    if app.exists() and not (resources / 'app.asar').exists():
        return read_json(app)
    if (resources / 'app.asar').exists():
        return read_asar_json(resources / 'app.asar', 'package.json')
    raise RuntimeError('Desktop installation has neither app.asar nor resources/app/package.json')


def desktop_base(exe):
    resources = Path(exe).parent / 'resources'
    archive = resources / 'app.asar'
    known = ('dsh/node_modules/@deepseek-ai', 'node_modules/@deepseek-ai')
    if archive.exists():
        with archive.open('rb') as stream:
            lead = stream.read(16)
            size = struct.unpack_from('<I', lead, 12)[0]
            if size > 64 * 1024 * 1024:
                raise RuntimeError('Desktop ASAR header exceeds size limit')
            header = json.loads(stream.read(size))
        for relative in known:
            entry = header
            try:
                for part in (relative + '/dsh-agent-instructions').split('/'):
                    entry = entry['files'][part]
                return str(archive / Path(relative))
            except KeyError:
                continue
    else:
        for relative in known:
            candidate = resources / 'app' / relative
            if (candidate / 'dsh-agent-instructions/lib').is_dir():
                return str(candidate)
    raise RuntimeError('Desktop host module layout is unsupported; refusing to patch a different installation')


def compatible_desktop(version):
    expected = read_json(REPO / 'runtime/package.json')['dependencies']['@deepseek-ai/dsh']
    return version == expected


def find_desktop(explicit=None):
    candidates = [Path(explicit)] if explicit else []
    for env, rel in [('LOCALAPPDATA', 'Programs/DeepSeek Harness/DeepSeek Harness.exe'),
                     ('ProgramFiles', 'DeepSeek Harness/DeepSeek Harness.exe')]:
        if os.environ.get(env):
            candidates.append(Path(os.environ[env]) / rel)
    for file in candidates:
        if file.is_file():
            data = desktop_metadata(file)
            version = str(data.get('version', ''))
            if not compatible_desktop(version):
                expected = read_json(REPO / 'runtime/package.json')['dependencies']['@deepseek-ai/dsh']
                raise RuntimeError(f'Desktop version {version} differs from the locked {expected} baseline: {file}')
            return file, version
    raise RuntimeError('Desktop executable missing. Supply -DesktopExe or use -InstallDesktop; -WebOnly is an explicit partial deployment.')


def install_desktop(root, url):
    destination = root / 'downloads/dsh-windows-x64.exe'
    destination.parent.mkdir(parents=True, exist_ok=True)
    print('[desktop] Download official installer; its graphical installer may require interaction.', flush=True)
    urllib.request.urlretrieve(url, destination)
    # Verify signature via literal path (no string-built PowerShell commands).
    run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
         REPO / 'scripts/verify-installer.ps1', '-Installer', destination])
    save_json(destination.with_suffix('.receipt.json'), {'url': url, 'sha256': digest(destination)})
    run([destination], timeout=3600)


def environment(state, surface='web'):
    env = dict(os.environ)
    env.update({'DSH_HOME': state['dshHome'], 'DSH_SURFACE': surface, 'DSH_PROFILE': surface,
                'PURGE_PROFILE_DIR': str(Path(state['dshHome']) / 'profiles' / surface),
                'SEEP_PYTHON': state['python'],
                'SEEP_CONTENT_ROOT': state['content'], 'SEEP_DSH_PROFILE': surface,
                'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1',
                'APKREV_TOOLS': str(Path(state['root']) / 'tools/apk'),
                'EXEREV_TOOLS': str(Path(state['root']) / 'tools/exe')})
    safe = Path(state['sources'].get('seep', str(Path(state['root']) / 'tools'))) / 'Tool/mcp/Tool/safe'
    if 'seep' in state['sources']:
        env['SEEP_ROOT'] = state['sources']['seep']
    tool_paths = [str(Path(state['runtime']) / 'node_modules/.bin'),
                  str(Path(state['python']).parent), str(safe / 'radare2/bin'), str(safe / 'jadx/bin'),
                  str(Path(state['root']) / 'tools/capabilities/bin')]
    env['PATH'] = os.pathsep.join(tool_paths) + os.pathsep + env.get('PATH', '')
    env['APKREV_TOOLS'] = os.pathsep.join([str(safe), str(Path(state['root']) / 'tools/apk'),
                                          os.environ.get('APKREV_TOOLS', '')])
    env['EXEREV_TOOLS'] = os.pathsep.join([str(safe), str(Path(state['root']) / 'tools/exe'),
                                          os.environ.get('EXEREV_TOOLS', '')])
    env['SEEP_ANDROID_TOOLBOX'] = str(Path(state['root']) / 'tools/capabilities')
    env['SEEP_WEB_TOOLBOX'] = str(Path(state['root']) / 'tools/capabilities')
    env['SEEP_NODE'] = state['node']
    if state['options'].get('ida_root'):
        env['SEEP_IDA_ROOT'] = state['options']['ida_root']
    # Prevent stale shell variables from redirecting patches to the user's other DSH installation.
    for name in ('DSH_BASE', 'PURGE_DSH_CLI', 'DSH_DESKTOP_INSTALL', 'DSH_APP', 'DSH_EXE'):
        env.pop(name, None)
    if surface == 'desktop' and state.get('desktopExe'):
        env['DSH_DESKTOP_INSTALL'] = str(Path(state['desktopExe']).parent)
        env['DSH_EXE'] = state['desktopExe']
        env['DSH_BASE'] = desktop_base(state['desktopExe'])
    else:
        env['DSH_BASE'] = str(Path(state['runtime']) / 'node_modules/@deepseek-ai')
        env['PURGE_DSH_CLI'] = state['cli']
    return env


def dsh_invocation(state, surface='web'):
    env = environment(state, surface)
    if surface == 'web':
        return [state['node'], state['cli']], env
    if not state.get('desktopExe'):
        raise RuntimeError('Desktop management requires the selected official Electron executable')
    env['ELECTRON_RUN_AS_NODE'] = '1'
    result = run([state['desktopExe'], '--expose-internals', REPO / 'scripts/desktop-cli.mjs',
                  state['plugins']['purge']], env=env, capture=True, timeout=60)
    selected = json.loads(result.stdout)
    if Path(selected['command']).resolve() != Path(state['desktopExe']).resolve():
        raise RuntimeError('Desktop CLI resolver selected a different executable')
    cli = Path(selected['cli'])
    resources = Path(state['desktopExe']).parent / 'resources'
    if not cli.is_relative_to(resources):
        raise RuntimeError('Desktop CLI resolver escaped the selected installation')
    env.update(selected['env'])
    return [selected['command'], *selected['args']], env


def dsh(state, args, surface='web', capture=False):
    command, env = dsh_invocation(state, surface)
    return run([*command, *args], env=env, capture=capture, timeout=1800)


def check_plugin_import(state, name):
    script = "import {pathToFileURL} from 'node:url'; await import(pathToFileURL(process.argv[1]));"
    run([state['node'], '--input-type=module', '-e', script,
         str(Path(state['plugins'][name]) / 'lib/index.js')], env=environment(state), capture=True, timeout=180)
    return 'actual Node import succeeded; live Loader acceptance remains separate'


def desktop_launch(state):
    # Electron single-instance state must be isolated as well as DSH_HOME.
    user_data = state.get('desktopUserData', str(Path(state['root']) / 'desktop-user-data'))
    return [state['desktopExe'], '--user-data-dir=' + user_data]


def initialize_desktop(state):
    if 'desktop' not in state['profiles']:
        return
    package = Path(state['dshHome']) / 'profiles/desktop/package.json'
    if package.is_file():
        return
    print('[desktop] First start: finish the desktop welcome screen, then fully quit it. '
          'The installer will continue after the window closes.', flush=True)
    env = environment(state, 'desktop')
    env.pop('ELECTRON_RUN_AS_NODE', None)
    run(desktop_launch(state), env=env, cwd=state['root'], timeout=3600)
    if not package.is_file():
        raise RuntimeError('Desktop did not initialize its profile in the selected DSH_HOME. '
                           'Open this workbench desktop, finish initialization, fully quit, and retry.')


def snapshot(state, root, previous):
    folder = root / 'snapshots' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    record = {'dshHome': state['dshHome'], 'profiles': {}, 'previousState': previous, 'candidateState': state}
    for profile in state['profiles']:
        base = Path(state['dshHome']) / 'profiles' / profile
        record['profiles'][profile] = {'existed': base.exists(), 'files': {}}
        for name in PROFILE_FILES:
            file = base / name
            record['profiles'][profile]['files'][name] = file.exists()
            if file.exists():
                target = folder / profile / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, target)
    record['piFiles'] = {}
    if 'pi' in modules_of(state) or (previous and 'pi' in modules_of(previous)):
        for name in ('settings.json', 'mcp.json', 'workbench-managed.json'):
            file = root / 'pi/agent' / name
            record['piFiles'][name] = file.exists()
            if file.exists():
                (folder / 'pi').mkdir(exist_ok=True)
                shutil.copy2(file, folder / 'pi' / name)
    save_json(folder / 'snapshot.json', record)
    return folder


def restore_snapshot(folder, state):
    record = read_json(folder / 'snapshot.json')
    for profile, info in record['profiles'].items():
        base = Path(record['dshHome']) / 'profiles' / profile
        if not info['existed']:
            if base.exists():
                # Retain the failed new profile for inspection; never recursively delete it.
                base.rename(base.with_name(profile + '.failed-' + uuid.uuid4().hex[:8]))
            continue
        for name, existed in info['files'].items():
            file = base / name
            if existed:
                file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(folder / profile / name, file)
            else:
                file.unlink(missing_ok=True)
        if info['files'].get('package.json'):
            dsh(state, ['plugin', '--profile', profile, 'install', '--frozen-lockfile'], profile)
    for name, existed in record.get('piFiles', {}).items():
        file = Path(state['root']) / 'pi/agent' / name
        if existed:
            file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(folder / 'pi' / name, file)
        else:
            file.unlink(missing_ok=True)
    active = Path(state['root']) / 'active.json'
    if record['previousState']:
        save_json(active, record['previousState'])
    else:
        active.unlink(missing_ok=True)


def configure_profiles(state):
    for profile in state['profiles']:
        print('[profile] ' + profile, flush=True)
        base = Path(state['dshHome']) / 'profiles' / profile
        package = base / 'package.json'
        if package.exists() and 'dsh-purge' in read_json(package).get('dependencies', {}):
            dsh(state, ['plugin', '--profile', profile, 'remove', 'dsh-purge'], profile)
        # Remove only a previously managed connector when the selection changes.
        for name in state.get('removeBundles', []):
            if package.exists() and name in read_json(package).get('dependencies', {}):
                dsh(state, ['plugin', '--profile', profile, 'remove', name], profile)
        for plugin in state['plugins']:
            dsh(state, ['plugin', '--profile', profile, 'add', '-w', state['plugins'][plugin]], profile)
        patch = base / 'cordis.patch.yml'
        original = patch.read_text(encoding='utf-8-sig') if patch.exists() else ''
        # Old hand-generated Seep MCP routes require an explicit migration, not duplicate mounts.
        if '# BEGIN SEEP' in original or '# === SEEP' in original:
            raise RuntimeError('Legacy Seep block found. Back it up and remove old MCP entries before migration.')
        new = merge_patch(original, profile_block(state))
        temp = patch.with_name('workbench-candidate.yml')
        temp.write_text(new, encoding='utf-8')
        try:
            run([state['node'], REPO / 'scripts/profile.mjs', state['runtime'], temp], capture=True)
            temp.replace(patch)
        finally:
            temp.unlink(missing_ok=True)
        package_data = read_json(package)
        bundles = package_data.get('dsh', {}).get('profile', {}).get('bundles', [])
        expected = {'seep': 'seep-lab', 'purge': 'dsh-purge-community'}
        if not {expected[p] for p in state['plugins']}.issubset(set(bundles)):
            raise RuntimeError(f'{profile}: plugin dependencies exist but bundle registration is incomplete')
        if profile == 'web':
            # Composition is validation only. Its private output is discarded.
            dsh(state, ['--profile', profile, '--dump-config'], profile, capture=True)


def pi_modes(state):
    return ['coding'] + [x for x in ('seep', 'apk', 'exe') if x in state['sources']] + (
        ['all'] if state['sources'] else [])


def pi_version(state):
    expected = read_json(Path(state['pi']['runtime']) / 'package.json')['dependencies']['@earendil-works/pi-coding-agent']
    actual = run([state['node'], state['pi']['cli'], '--version'],
                 env=dict(pi_environment(state, 'coding'), PI_OFFLINE='1'), capture=True).stdout.strip()
    if actual != expected:
        raise RuntimeError('PI runtime version differs from its locked package')
    return actual


def pi_mcp_check(state):
    result = run([state['node'], state['pi']['cli'], 'mcp', 'list', '--json'],
                 env=pi_environment(state, 'all'), cwd=Path(state['root']) / 'pi',
                 capture=True, timeout=600, check=False)
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError('PI native MCP returned an invalid report; private output omitted') from None
    required = read_json(Path(state['pi']['agent']) / 'workbench-managed.json')['servers']
    summary, failed = [], []
    for server in data.get('servers', []):
        name, status = server['name'], server['state']
        summary.append({'name': name, 'state': status, 'tools': len(server.get('tools', []))})
        if server.get('enabled', True) and status != 'connected':
            # Never expose raw errors, transport arguments, URLs or credential-bearing headers.
            error = str(server.get('error', ''))
            category = ('timeout' if re.search(r'timeout|timed out', error, re.I) else
                        'missing-entry' if re.search(r'ENOENT|MODULE_NOT_FOUND', error) else 'connection')
            failed.append(name + '=' + status + '/' + category)
    for name in required:
        if not any(s['name'] == name and s['state'] == 'connected' and s['tools'] for s in summary):
            if not any(item.startswith(name + '=') for item in failed):
                failed.append(name + '=missing-tools')
    if result.returncode or data.get('errors') or failed:
        raise RuntimeError('PI native MCP failed: ' + ', '.join(failed or ['configuration-or-cli']))
    return {'servers': summary, 'configErrors': 0}


def configure_pi(state):
    root = Path(state['root'])
    agent = root / 'pi/agent'
    agent.mkdir(parents=True, exist_ok=True)
    settings_file, mcp_file = agent / 'settings.json', agent / 'mcp.json'
    settings = read_json(settings_file) if settings_file.exists() else {}
    mcp = read_json(mcp_file) if mcp_file.exists() else {'mcpServers': {}}
    marker = agent / 'workbench-managed.json'
    old = read_json(marker) if marker.exists() else {}
    extension = Path(state['generation']) / 'pi-workbench.mjs'
    shutil.copy2(REPO / 'scripts/pi-workbench.mjs', extension)
    extensions = [x for x in settings.get('extensions', []) if x not in old.get('extensions', [])]
    settings['extensions'] = extensions + [str(extension)]
    settings.setdefault('defaultTools', ['read', 'powershell', 'edit', 'write', 'grep', 'find', 'ls'])
    servers = mcp.setdefault('mcpServers', {})
    # The names are reserved only after first registration; no overwriting user servers.
    managed = {}
    if 'seep' in state['sources']:
        source = state['sources']['seep']
        managed = {
            'seep': {'command': state['python'], 'args': [str(Path(source) / 'Tool/mcp/seep_mcp_server.py')],
                     'cwd': source, 'env': {'PYTHONIOENCODING': 'utf-8'}, 'exposure': 'deferred'},
            'js-reverse': {'command': state['node'], 'args': [str(Path(state['mcpRuntime']) /
                           'node_modules/js-reverse-mcp/build/src/index.js')], 'cwd': source, 'exposure': 'deferred'}}
        if state.get('options', {}).get('with_ida'):
            managed['ida'] = {'command': state['python'], 'args': ['-m', 'ida_pro_mcp.idalib_supervisor'],
                              'cwd': source, 'exposure': 'deferred'}
        if state.get('options', {}).get('with_playwright'):
            managed['playwright'] = {'command': executable('npx'),
                                     'args': ['-y', '@playwright/mcp@0.0.85'], 'exposure': 'deferred'}
    for name in managed:
        if name in servers and name not in old.get('servers', {}):
            raise RuntimeError('PI MCP name belongs to the user: ' + name + '; rename it before installing')
    for name, entry in old.get('servers', {}).items():
        if name in servers and servers[name] != entry:
            raise RuntimeError('Managed PI MCP entry was edited: ' + name + '; retain it under a user-owned name')
        servers.pop(name, None)
    servers.update(managed)
    save_json(settings_file, settings)
    save_json(mcp_file, mcp)
    save_json(marker, {'extensions': [str(extension)], 'servers': managed})


def pi_environment(state, mode):
    env = dict(os.environ)
    # No DSH profile or patch target is inherited by a standalone PI process.
    for name in list(env):
        if name.startswith(('DSH_', 'PURGE_', 'SEEP_')):
            env.pop(name)
    env.update({'PI_CODING_AGENT_DIR': state['pi']['agent'],
                'PI_CODING_AGENT_SESSION_DIR': str(Path(state['root']) / 'pi/sessions' / mode),
                'PI_TELEMETRY': '0', 'PI_SKIP_VERSION_CHECK': '1',
                'WORKBENCH_MODE': mode, 'WORKBENCH_ROOT': state['root'],
                'SEEP_CONTENT_ROOT': state['content'], 'SEEP_PYTHON': state['python'],
                'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1',
                'APKREV_TOOLS': str(Path(state['root']) / 'tools/apk'),
                'EXEREV_TOOLS': str(Path(state['root']) / 'tools/exe')})
    for name in ('APKREV_TOOLS', 'EXEREV_TOOLS'):
        if os.environ.get(name):
            env[name] += os.pathsep + os.environ[name]
    paths = [str(Path(state['python']).parent), str(Path(state['root']) / 'tools/capabilities/bin')]
    if 'seep' in state['sources']:
        env['SEEP_ROOT'] = state['sources']['seep']
        safe = Path(state['sources']['seep']) / 'Tool/mcp/Tool/safe'
        paths += [str(safe / 'radare2/bin'), str(safe / 'jadx/bin')]
        env['SEEP_NODE'] = state['node']
        for name in ('APKREV_TOOLS', 'EXEREV_TOOLS'):
            env[name] += os.pathsep + str(safe)
        for name in ('SEEP_ANDROID_TOOLBOX', 'SEEP_WEB_TOOLBOX'):
            env[name] = str(Path(state['root']) / 'tools/capabilities')
    if state.get('options', {}).get('ida_root'):
        env['SEEP_IDA_ROOT'] = state['options']['ida_root']
    env['PATH'] = os.pathsep.join(paths) + os.pathsep + env.get('PATH', '')
    return env


def start_pi(args):
    state = load_state(args.root)
    if 'pi' not in modules_of(state):
        raise RuntimeError('PI was not installed; redeploy with -WithPi or -Modules pi,...')
    if (Path(state['root']) / 'deployment.lock').exists():
        raise RuntimeError('Deployment or recovery is still running')
    mode = args.pi_mode
    if mode not in pi_modes(state):
        raise RuntimeError(mode + ' was not installed in this deployment')
    project = Path(args.project).expanduser().resolve() if args.project else Path(state['root']) / 'projects' / mode
    if args.project and not project.is_dir():
        raise RuntimeError('Project directory does not exist: ' + str(project))
    project.mkdir(parents=True, exist_ok=True)
    command = [state['node'], state['pi']['cli']]
    # Shell subcommands must precede session flags. They never contact a model.
    if args.app_args[:1] != ['mcp']:
        command += ['--no-skills']
        if mode == 'coding':
            command += ['--no-mcp']
        else:
            skills = read_json(Path(state['content']) / 'sources.json')['skills']
            selected = skills.values() if mode in ('seep', 'all') else [skills[mode + '-reverse']]
            for skill in selected:
                command += ['--skill', skill]
    return run([*command, *args.app_args], env=pi_environment(state, mode), cwd=project,
               check=False, timeout=None, interactive=True).returncode


def purge_command(state, surface, command):
    if surface not in state['profiles']:
        raise RuntimeError(surface + ' was not installed in this deployment')
    if 'purge' not in state['plugins']:
        raise RuntimeError('Purge was not installed in this deployment')
    shim = Path(state['runtime']) / 'node_modules/.bin' / ('dsh.cmd' if os.name == 'nt' else 'dsh')
    if command in ('apply', 'revert') and not shim.is_file():
        raise RuntimeError('Managed launcher missing; refusing to fall back to a global DSH shim')
    return run([state['node'], Path(state['plugins']['purge']) / 'bin/community.js', command],
               env=environment(state, surface), timeout=1800)


def purge_check(state, surface):
    result = run([state['node'], Path(state['plugins']['purge']) / 'bin/community.js', 'selfcheck', '--json'],
                 env=environment(state, surface), capture=True, timeout=180, check=False)
    if not result.stdout.strip():
        raise RuntimeError('Purge selfcheck failed without a JSON report; inspect host-status')
    data = json.loads(result.stdout)
    # selfcheck differentiates pending, inferred and unknown; exit zero alone is insufficient.
    return {key: data.get(key) for key in ('ok', 'state', 'host_version', 'patch', 'summary')}


def purge_disk_ready(result):
    summary = result.get('summary') or {}
    return (summary.get('host', {}).get('ok') is True
            and summary.get('host', {}).get('total', 0) > 0
            and summary.get('runtime', {}).get('ok') is True
            and summary.get('layout', {}).get('ok') is True
            and summary.get('pending', {}).get('patches', 1) == 0
            and summary.get('broken', {}).get('layers', 1) == 0
            and (result.get('patch') or {}).get('missing_file', 1) == 0)


def install(args):
    root = Path(args.root).expanduser().resolve()
    if root == REPO or root in REPO.parents or (root.is_relative_to(REPO) and not root.is_relative_to(REPO / '.workbench')):
        raise RuntimeError('Installation root must be outside the source repository or in .workbench')
    if sys.version_info < (3, 11):
        raise RuntimeError('Python 3.11+ is required')
    node_version = run([executable('node'), '--version'], capture=True).stdout.strip()
    numbers = tuple(int(x) for x in re.findall(r'\d+', node_version)[:3])
    modules = resolve_modules(args.modules, args.with_pi)
    minimum = (22, 19, 0) if 'pi' in modules else (22, 18, 0)
    if numbers < minimum:
        raise RuntimeError('Node.js ' + '.'.join(map(str, minimum)) + '+ is required')
    if args.apply_purge and 'purge' not in modules:
        raise RuntimeError('-ApplyPurge requires the DSH + Purge modules')
    if (args.with_ida or args.with_playwright) and 'seep' not in modules:
        raise RuntimeError('-WithIda/-WithPlaywright require the seep module')
    if (args.install_desktop or args.desktop_exe) and 'dsh' not in modules:
        raise RuntimeError('Desktop options require the dsh module')
    executable('git')
    executable('npm')
    manifest = read_json(REPO / 'sources.lock.json')
    with deployment_lock(root):
        previous = read_json(root / 'active.json') if (root / 'active.json').exists() else None
        profiles = (['web'] if args.web_only else ['web', 'desktop']) if 'dsh' in modules else []
        desktop, desktop_version = None, None
        if 'desktop' in profiles:
            if args.install_desktop:
                install_desktop(root, manifest['desktopInstaller'])
            desktop, desktop_version = find_desktop(args.desktop_exe or (previous or {}).get('desktopExe'))
        selected_sources = [item for item in manifest['sources'] if item['id'] in modules]
        sources = {item['id']: source_checkout(root, item) for item in selected_sources}
        runtime = install_runtime(root) if 'dsh' in modules else None
        python = install_python(root) if 'seep' in modules else Path(sys.executable)
        ida_root = os.environ.get('SEEP_IDA_ROOT') or (previous or {}).get('options', {}).get('ida_root')
        options = {'with_ida': args.with_ida, 'with_playwright': args.with_playwright,
                   'ida_root': ida_root, 'modules': modules}
        if args.with_ida and not ida_root:
            raise RuntimeError('-WithIda requires SEEP_IDA_ROOT pointing to a licensed local IDA installation')
        state = build_generation(root, sources, runtime, python, options)
        if 'pi' in modules:
            pi_runtime = install_node_bundle(root, 'pi-runtime')
            state['pi'] = {'runtime': str(pi_runtime), 'agent': str(root / 'pi/agent'),
                           'cli': str(pi_runtime / 'node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js')}
            pi_version(state)
        if 'seep' in modules:
            state['mcpRuntime'] = str(runtime or install_node_bundle(root, 'mcp-runtime'))
        state.update({'dshHome': str(Path(args.dsh_home).resolve()) if args.dsh_home else
                      (previous or {}).get('dshHome', str(root / 'dsh-home')),
                      'profiles': profiles, 'desktopExe': str(desktop) if desktop else None,
                      'desktopVersion': desktop_version, 'release': manifest['release'],
                      'desktopUserData': str(root / 'desktop-user-data'),
                      'sourceManifest': selected_sources,
                      'lockSha256': digest(REPO / 'sources.lock.json'), 'purgeApplied': False})
        state['removeBundles'] = ['seep-lab'] if (previous and 'seep' in previous.get('plugins', {})
                                                       and 'seep' not in state['plugins']) else []
        for directory in ('samples', 'workspace', 'tools/apk', 'tools/exe', 'reports'):
            (root / directory).mkdir(parents=True, exist_ok=True)
        transaction = snapshot(state, root, previous)
        state['snapshot'] = str(transaction)
        print('[backup] ' + str(transaction), flush=True)
        try:
            for plugin in state['plugins']:
                check_plugin_import(state, plugin)
            initialize_desktop(state)
            configure_profiles(state)
            if 'pi' in modules:
                configure_pi(state)
        except Exception:
            print('[recovery] Restoring profile files and dependencies.', flush=True)
            restore_snapshot(transaction, state)
            raise
        save_json(root / 'active.json', state)
        save_json(Path(state['generation']) / 'deployment.json', state)
        # Host patches have their own per-host backups; profile rollback alone cannot undo them.
        if args.apply_purge:
            state['purgeResults'] = {}
            for profile in profiles:
                purge_command(state, profile, 'apply')
                validation = purge_check(state, profile)
                state['purgeResults'][profile] = validation
                save_json(root / 'active.json', state)
                save_json(Path(state['root']) / 'reports' / ('purge-' + profile + '.json'), validation)
                if not purge_disk_ready(validation):
                    raise RuntimeError(f'{profile}: Purge application needs attention; inspect reports/purge-{profile}.json')
                if validation.get('state') in ('inferred', 'unknown'):
                    print(f'[UNVERIFIED] {profile}: disk patch checks completed; verify the live host in its UI.', flush=True)
            state['purgeApplied'] = True
            save_json(root / 'active.json', state)
        print('[installed] Modules: ' + ', '.join(modules) + '; DSH profiles: ' + ', '.join(profiles), flush=True)
        print('Run doctor.ps1 -ProbeMcp, then start the selected entries and verify model requests.' +
              (' DSH GUI acceptance is still pending.' if profiles else ''), flush=True)
    return 0


def load_state(root):
    file = Path(root).expanduser().resolve() / 'active.json'
    if not file.exists():
        raise RuntimeError('No completed deployment at ' + str(file.parent))
    return read_json(file)


def doctor(args):
    state = load_state(args.root)
    report = {'release': state['release'], 'checks': [], 'runtimeVerified': False,
              'uiAndModelRequest': 'requires live acceptance on this device'}
    def check(name, action):
        try:
            detail = action()
            status = ({'pending': 'pending', 'inferred': 'unverified', 'unknown': 'unverified'}.get(detail.get('state'), 'pass')
                      if isinstance(detail, dict) else 'pass')
            report['checks'].append({'name': name, 'status': status, 'detail': detail})
            print('[' + status.upper() + '] ' + name, flush=True)
        except Exception as exc:
            report['checks'].append({'name': name, 'status': 'fail', 'errorType': type(exc).__name__})
            print('[FAIL] ' + name + ': ' + str(exc), flush=True)
    for item in state.get('sourceManifest', read_json(REPO / 'sources.lock.json')['sources']):
        check('source:' + item['id'], lambda i=item: verify_source(state['sources'][i['id']], i))
    if 'seep' in state['sources']:
        check('python:mcp', lambda: run([state['python'], '-c', 'import mcp'], capture=True).returncode)
    for plugin in state['plugins']:
        check('plugin:' + plugin + ':import', lambda p=plugin: check_plugin_import(state, p))
    for profile in state['profiles']:
        def profile_check(p=profile):
            base = Path(state['dshHome']) / 'profiles' / p
            pkg = read_json(base / 'package.json')
            bundles = pkg.get('dsh', {}).get('profile', {}).get('bundles', [])
            expected = {'seep': 'seep-lab', 'purge': 'dsh-purge-community'}
            if not {expected[p] for p in state['plugins']}.issubset(set(bundles)):
                raise RuntimeError('Missing registered bundles')
            run([state['node'], REPO / 'scripts/profile.mjs', state['runtime'], base / 'cordis.patch.yml'], capture=True)
            if p == 'web':
                dsh(state, ['--profile', p, '--dump-config'], p, capture=True)
            return 'bundle registration + YAML composition; live Loader still requires UI check'
        check('profile:' + profile, profile_check)
        def check_purge(p=profile):
            result = purge_check(state, p)
            if result.get('state') == 'broken' or (result.get('state') == 'unknown' and not purge_disk_ready(result)):
                raise RuntimeError('Purge host unresolved or broken; use purge.ps1 -Action host-status')
            return result
        check('purge:' + profile, check_purge)
    if 'desktop' in state['profiles']:
        check('desktop:version', lambda: find_desktop(state['desktopExe'])[1])
    elif 'dsh' in modules_of(state):
        report['checks'].append({'name': 'desktop', 'status': 'not-installed', 'detail': 'Explicit -WebOnly deployment'})
    for skill in ('apk-reverse', 'exe-reverse'):
        if skill.split('-')[0] not in state['sources']:
            continue
        check('skill:' + skill, lambda s=skill: 'complete' if (Path(state['content']) / 'skill' / s / 'scripts/doctor.py').is_file()
              else (_ for _ in ()).throw(RuntimeError('Skill scripts missing')))
    if 'pi' in modules_of(state):
        check('pi:version', lambda: pi_version(state))
        def pi_config():
            agent = Path(state['pi']['agent'])
            settings, mcp = read_json(agent / 'settings.json'), read_json(agent / 'mcp.json')
            marker = read_json(agent / 'workbench-managed.json')
            if not set(marker['extensions']).issubset(settings.get('extensions', [])):
                raise RuntimeError('PI workbench extension is not registered')
            if any(mcp.get('mcpServers', {}).get(k) != v for k, v in marker['servers'].items()):
                raise RuntimeError('PI managed MCP configuration changed')
            return {'agent': str(agent), 'modes': pi_modes(state), 'modelRequest': 'unverified'}
        check('pi:config', pi_config)
        for mode in pi_modes(state):
            def resources(m=mode):
                result = run([state['node'], REPO / 'scripts/probe_pi.mjs',
                              Path(state['root']) / 'active.json', m],
                             env=pi_environment(state, m), capture=True, timeout=180)
                data = json.loads(result.stdout)
                if not data.get('ok'):
                    raise RuntimeError('PI resource loader did not accept the selected skills/extension')
                return data
            check('pi:resources:' + mode, resources)
        if args.probe_mcp:
            check('pi:mcp-list', lambda: pi_mcp_check(state))
    runtime_env = (lambda: environment(state)) if state['profiles'] else (lambda: pi_environment(state, 'all'))
    if args.probe_mcp and 'seep' in state['sources']:
        for name, command, argv, tool in [
            ('seep', state['python'], [str(Path(state['sources']['seep']) / 'Tool/mcp/seep_mcp_server.py')], 'seep_status'),
            ('js-reverse', state['node'], [str(Path(state.get('mcpRuntime') or state['runtime']) / 'node_modules/js-reverse-mcp/build/src/index.js')], None),
        ]:
            def probe(c=command, a=argv, t=tool):
                cmd = [state['python'], REPO / 'scripts/probe_mcp.py', '--cwd', state['sources']['seep']]
                if t:
                    cmd += ['--status-tool', t]
                result = run([*cmd, c, *a], env=runtime_env(), capture=True, timeout=600, check=False)
                if result.returncode:
                    # Only our bounded JSON diagnostic is exposed, not arbitrary server stderr.
                    cause_types = []
                    for line in result.stderr.splitlines():
                        try:
                            diagnostic = json.loads(line)
                        except ValueError:
                            continue
                        if isinstance(diagnostic, dict) and diagnostic.get('ok') is False:
                            cause_types = [item.get('type', 'Unknown') for item in diagnostic.get('causes', [])]
                    raise RuntimeError('MCP handshake failed: ' + ', '.join(cause_types or ['see local server diagnostics']))
                return json.loads(result.stdout.strip().splitlines()[-1])
            check('mcp:' + name, probe)
    if args.deep:
        for skill in ('apk-reverse', 'exe-reverse'):
            if skill.split('-')[0] not in state['sources']:
                continue
            # Their stdout is intentionally local; no provider config is involved.
            check('tools:' + skill, lambda s=skill: run([state['python'], Path(state['content']) / 'skill' / s / 'scripts/doctor.py'],
                                                       env=runtime_env(), timeout=180).returncode)
        if 'seep' in state['sources']:
            check('tools:seep', lambda: run([state['python'], Path(state['sources']['seep']) / 'Tool/mcp/tool_resolver.py',
                                           '--verify', '--json'], env=runtime_env(), timeout=300).returncode)
    report['ok'] = not any(c['status'] in ('fail', 'pending', 'unverified') for c in report['checks'])
    destination = Path(state['root']) / 'reports' / ('doctor-' + time.strftime('%Y%m%d-%H%M%S') + '.json')
    save_json(destination, report)
    print('[report] ' + str(destination), flush=True)
    return 0 if report['ok'] else 1


def start(args):
    state = load_state(args.root)
    if (Path(state['root']) / 'deployment.lock').exists():
        raise RuntimeError('Deployment or recovery is still running; start the host after it completes')
    surface = args.surface
    if surface not in state['profiles']:
        raise RuntimeError(surface + ' was not installed in this deployment')
    env = environment(state, surface)
    if surface == 'desktop':
        find_desktop(state['desktopExe'])
        env.pop('ELECTRON_RUN_AS_NODE', None)
        # Existing Electron instances may ignore the new environment. Close them first.
        subprocess.Popen(desktop_launch(state), env=env, cwd=state['root'])
        print('Desktop launched with DSH_HOME=' + state['dshHome'])
        return 0
    return run([state['node'], state['cli'], '--profile', 'web', *args.app_args], env=env,
               cwd=state['root'], check=False, timeout=None).returncode


def rollback(args):
    state = load_state(args.root)
    with deployment_lock(Path(state['root'])):
        if args.revert_purge:
            for profile in state['profiles']:
                purge_command(state, profile, 'revert')
        folder = Path(args.snapshot or state['snapshot']).resolve()
        if not folder.is_relative_to(Path(state['root']) / 'snapshots'):
            raise RuntimeError('Snapshot must belong to this installation')
        restore_snapshot(folder, state)
    print('[restored] Profile configuration restored. Host patches are reverted only with -RevertPurge.')
    return 0


def capabilities(args):
    state = load_state(args.root)
    if 'seep' not in state['sources']:
        raise RuntimeError('Capability groups require the seep module; select pi,seep or the full DSH workbench')
    components = args.components.split(',')
    allowed = {'aotopsy', 'web', 'android', 'scanners'}
    if components == ['all']:
        components = sorted(allowed)
    if not set(components).issubset(allowed):
        raise RuntimeError('Unknown capability group; use aotopsy,web,android,scanners or all')
    with deployment_lock(Path(state['root'])):
        cmd = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
               REPO / 'scripts/capabilities-driver.ps1', '-SeepRoot', state['sources']['seep'],
               '-ToolboxRoot', Path(state['root']) / 'tools/capabilities',
               '-ComponentsCsv', ','.join(components)]
        if args.check_only:
            cmd += ['-CheckOnly']
        run(cmd, env=environment(state) if state['profiles'] else pi_environment(state, 'all'), timeout=3600)
    print('Selected capability groups processed. Run doctor.ps1 -Deep and check device/driver prerequisites.')
    return 0


def main(argv=None):
    raw = list(sys.argv[1:] if argv is None else argv)
    forwarded = []
    if '--' in raw:
        index = raw.index('--')
        raw, forwarded = raw[:index], raw[index + 1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('install', 'doctor', 'start', 'start-pi', 'rollback', 'purge', 'capabilities'))
    parser.add_argument('--root', default=str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'DSH-Windows-Workbench'))
    parser.add_argument('--dsh-home')
    parser.add_argument('--modules')
    parser.add_argument('--with-pi', action='store_true')
    parser.add_argument('--pi-mode', choices=('coding', 'seep', 'apk', 'exe', 'all'), default='coding')
    parser.add_argument('--project')
    parser.add_argument('--desktop-exe')
    parser.add_argument('--install-desktop', action='store_true')
    parser.add_argument('--web-only', action='store_true')
    parser.add_argument('--apply-purge', action='store_true')
    parser.add_argument('--with-ida', action='store_true')
    parser.add_argument('--with-playwright', action='store_true')
    parser.add_argument('--probe-mcp', action='store_true')
    parser.add_argument('--deep', action='store_true')
    parser.add_argument('--revert-purge', action='store_true')
    parser.add_argument('--snapshot')
    parser.add_argument('--components', default='aotopsy')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--surface', choices=('web', 'desktop'), default='web')
    parser.add_argument('--purge-action', choices=('status', 'apply', 'revert', 'host-status', 'selfcheck'), default='status')
    parser.add_argument('app_args', nargs='*')
    args, extra = parser.parse_known_args(raw)
    if (extra or forwarded) and args.operation not in ('start', 'start-pi'):
        parser.error('unrecognized arguments: ' + ' '.join(extra + forwarded))
    args.app_args += extra + forwarded
    if args.operation == 'purge':
        state = load_state(args.root)
        if args.purge_action in ('apply', 'revert'):
            with deployment_lock(Path(state['root'])):
                return purge_command(state, args.surface, args.purge_action).returncode
        return purge_command(state, args.surface, args.purge_action).returncode
    return {'install': install, 'doctor': doctor, 'start': start, 'start-pi': start_pi, 'rollback': rollback,
            'capabilities': capabilities}[args.operation](args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print('[FAILED] ' + str(exc), file=sys.stderr)
        sys.exit(1)
