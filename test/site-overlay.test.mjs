import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import worker from '../src/index.js';
import overlay from '../src/site-overlay.js';

function environment({ missing = false, corrupt = false } = {}) {
  const calls = [];
  const entry = overlay.objects['site/activities/vibemotion/assets/videos/case1_europe_pop.mp4'];
  const meta = { size: entry.size, customMetadata: { sha256: corrupt ? '0'.repeat(64) : entry.sha256 } };
  return { calls, env: { PUBLIC_RELEASE_ID: overlay.base_release, PUBLIC_CORPUS: {
    async head(key) { calls.push(key); return missing ? null : meta; },
    async get(key, options) { calls.push({ key, options }); return { ...meta, body: new Uint8Array(4) }; },
  } } };
}
const video = 'https://benchlibrary.com/activities/vibemotion/assets/videos/case1_europe_pop.mp4';

test('activity overlay supports video ranges with the existing R2 response policy', async () => {
  const { calls, env } = environment();
  const response = await worker.fetch(new Request(video, { headers: { Range: 'bytes=0-3' } }), env);
  assert.equal(response.status, 206);
  assert.equal(response.headers.get('Content-Type'), 'video/mp4');
  assert.match(response.headers.get('Content-Range'), /^bytes 0-3\//);
  assert.equal(calls[0], `releases/${overlay.release}/site/activities/vibemotion/assets/videos/case1_europe_pop.mp4`);
  assert.deepEqual(calls[1].options, { range: { offset: 0, length: 4 } });
});

test('missing or changed overlay objects fail closed without serving old content', async () => {
  for (const [options, status] of [[{missing: true}, 404], [{corrupt: true}, 503]]) {
    const { calls, env } = environment(options);
    assert.equal((await worker.fetch(new Request(video), env)).status, status);
    assert.equal(calls.length, 1);
  }
});

test('corpus, unlisted site files and other releases never use the overlay', async () => {
  const { calls, env } = environment({ missing: true });
  for (const path of ['data/catalog.json', 'app.js', 'activities/not-listed.html']) {
    await worker.fetch(new Request(`https://benchlibrary.com/${path}`), env);
  }
  assert.deepEqual(calls, ['data/catalog.json', 'site/app.js', 'site/activities/not-listed.html']
    .map(path => `releases/${overlay.base_release}/${path}`));
  env.PUBLIC_RELEASE_ID = 'future-full-release';
  await worker.fetch(new Request(video), env);
  assert.match(calls.at(-1), /^releases\/future-full-release\//);
});

test('all pinned assets match their size and hash, with no remote activity dependencies', async () => {
  for (const [path, expected] of Object.entries(overlay.objects)) {
    const bytes = await readFile(new URL(`../${path}`, import.meta.url));
    assert.equal(bytes.length, expected.size, path);
    assert.equal(createHash('sha256').update(bytes).digest('hex'), expected.sha256, path);
  }
  const page = await readFile(new URL('../site/activities/vibemotion/index.html', import.meta.url), 'utf8');
  assert.doesNotMatch(page, /(?:src|href)=["']https?:|<script>/);
  assert.equal((page.match(/<video /g) || []).length, 5);
  assert.equal((page.match(/data-pg=/g) || []).length, 6);
});
