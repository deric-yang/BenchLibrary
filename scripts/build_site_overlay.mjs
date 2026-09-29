// Recompute only the explicitly reviewed site paths; never enumerate the corpus.
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const manifestUrl = new URL('../config/activity_release.json', import.meta.url);
const manifest = JSON.parse(await readFile(manifestUrl, 'utf8'));
for (const path of Object.keys(manifest.objects)) {
  if (!/^site\/(?:index\.html|activities\/[\w/.-]+)$/.test(path) || path.includes('..')) {
    throw new Error(`Unsafe site overlay path: ${path}`);
  }
  const bytes = await readFile(new URL(`../${path}`, import.meta.url));
  manifest.objects[path] = { size: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
}
const json = JSON.stringify(manifest, null, 2);
await writeFile(manifestUrl, `${json}\n`);
await writeFile(new URL('../src/site-overlay.js', import.meta.url),
  `// Generated from config/activity_release.json. Reviewed immutable site objects only.\nexport default ${json};\n`);
console.log(`Pinned ${Object.keys(manifest.objects).length} site objects`);
