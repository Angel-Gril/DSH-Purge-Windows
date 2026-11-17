"""Maintainer command: propose new source pins, never install or publish them automatically."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('workbench', Path(__file__).with_name('workbench.py'))
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, help='Separate source cache outside the Git checkout')
    args = parser.parse_args()
    manifest = wb.read_json(wb.REPO / 'sources.lock.json')
    changes = []
    for item in manifest['sources']:
        output = wb.run(['git', 'ls-remote', item['url'], 'refs/heads/' + item['branch']], capture=True).stdout
        matches = [line.split()[0] for line in output.splitlines() if line.strip()]
        if len(matches) != 1:
            raise RuntimeError('Cannot resolve a unique branch for ' + item['id'])
        old = item['commit']
        item['commit'] = matches[0]
        source = wb.source_checkout(Path(args.cache).resolve(), item)
        if item['id'] == 'seep':
            item['version'] = (source / 'VERSION').read_text(encoding='utf-8').strip()
        elif item['id'] == 'purge':
            metadata = wb.read_json(source / 'package.json')
            item['version'], item['package'] = metadata['version'], metadata['name']
        changes.append({'id': item['id'], 'before': old, 'after': item['commit']})
    # Write only a reviewable candidate. Runtime/package-lock and adapters need independent review.
    candidate = wb.REPO / 'sources.candidate.json'
    wb.save_json(candidate, manifest)
    print(json.dumps({'changes': changes, 'candidate': str(candidate),
                      'next': 'Review source changes, versions and adapters; replace sources.lock.json only after isolated tests.'}, indent=2))


if __name__ == '__main__':
    main()
