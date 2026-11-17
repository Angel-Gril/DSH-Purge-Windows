// Validate overlays without evaluating !!js or rewriting the user's YAML.
import { createRequire } from 'node:module';
import fs from 'node:fs';
const [runtime, patchFile] = process.argv.slice(2);
const require = createRequire(runtime + '/package.json');
const YAML = require('yaml');
const doc = YAML.parseDocument(fs.readFileSync(patchFile, 'utf8'), {
  customTags: [{ tag: 'tag:yaml.org,2002:js', resolve: value => value }],
});
if (doc.errors.length || !YAML.isSeq(doc.contents)) {
  throw new Error('Profile patch must be one valid YAML sequence: ' + doc.errors.map(e => e.message).join('; '));
}
console.log(JSON.stringify({ ok: true, entries: doc.contents.items.length }));
