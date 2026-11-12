import assert from 'node:assert/strict';
import test from 'node:test';
import worker from '../src/index.js';
test('activity entry URLs redirect to their exact same-origin directory and retain query', async () => {
  for (const path of ['/activities', '/activities/skill-audit']) {
    for (const method of ['GET', 'HEAD']) {
      const result = await worker.fetch(new Request('https://benchlibrary.com'+path+'?view=cases', {method}), {});
      assert.equal(result.status, 308);
      assert.equal(result.headers.get('Location'), 'https://benchlibrary.com'+path+'/?view=cases');
      assert.equal(result.headers.get('X-Content-Type-Options'), 'nosniff');
    }
  }
});
test('activity canonicalization never turns writes into redirects', async () => {
  const result = await worker.fetch(new Request('https://benchlibrary.com/activities', {method:'POST'}), {});
  assert.equal(result.status, 405);
});
test('unlisted activity paths retain normal missing-object behavior', async () => {
  const result = await worker.fetch(new Request('https://benchlibrary.com/activities/unlisted'), {
    PUBLIC_RELEASE_ID:'test-release', PUBLIC_CORPUS:{async head(){return null;}}
  });
  assert.equal(result.status, 404);
});
