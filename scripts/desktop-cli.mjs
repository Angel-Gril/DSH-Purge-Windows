// Run with the selected Electron executable and ELECTRON_RUN_AS_NODE=1 so
// node:fs can see app.asar. Reuse Purge's instance-local layout detection.
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const { resolveDshCli } = await import(pathToFileURL(path.join(process.argv[2], 'lib/instance.js')));
const selected = resolveDshCli({ execPath: process.execPath });
process.stdout.write(JSON.stringify({ command: selected.command, args: selected.args,
  cli: selected.cli, env: { ...selected.env, ELECTRON_RUN_AS_NODE: '1' } }));
