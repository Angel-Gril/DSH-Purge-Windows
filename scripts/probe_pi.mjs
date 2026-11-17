// Validate the real PI resource loader without credentials or model requests.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [stateFile, mode = 'all'] = process.argv.slice(2);
const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
const manifest = JSON.parse(fs.readFileSync(path.join(state.content, 'sources.json'), 'utf8'));
const selected = mode === 'coding' ? [] : mode === 'all' || mode === 'seep'
  ? Object.values(manifest.skills) : [manifest.skills[mode + '-reverse']];
const { DefaultResourceLoader } = await import(pathToFileURL(path.join(
  state.pi.runtime, 'node_modules/@earendil-works/pi-coding-agent/dist/index.js')));
const loader = new DefaultResourceLoader({cwd: path.join(state.root, 'pi'),
  agentDir: state.pi.agent, noSkills: true, noContextFiles: true,
  additionalSkillPaths: selected});
await loader.reload();
const skills = loader.getSkills(), extensions = loader.getExtensions();
const missing = selected.filter(dir => !skills.skills.some(s => path.resolve(s.baseDir) === path.resolve(dir)));
const expectedExtension = path.join(state.generation, 'pi-workbench.mjs');
const workbenchLoaded = extensions.extensions.some(e => path.resolve(e.resolvedPath) === path.resolve(expectedExtension));
if (extensions.errors.length || missing.length || !workbenchLoaded) {
  process.stdout.write(JSON.stringify({ok: false, extensionErrors: extensions.errors.length, missing, workbenchLoaded}));
  process.exitCode = 1;
} else {
  process.stdout.write(JSON.stringify({ok: true, mode, skills: skills.skills.map(s => s.name),
    extensions: extensions.extensions.length, diagnostics: skills.diagnostics.length}));
}
