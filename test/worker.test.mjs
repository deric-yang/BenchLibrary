import assert from "node:assert/strict";
import test from "node:test";

import worker, { objectPathFromUrl, parseByteRange, sitePathFromUrl } from "../src/index.js";

const encoder = new TextEncoder();

function metadata(bytes, overrides = {}) {
  const uploaded = overrides.uploaded || new Date("2026-09-06T00:00:00Z");
  return {
    size: bytes.byteLength,
    etag: "abc123",
    httpEtag: '"abc123"',
    customMetadata: { sha256: "a".repeat(64) },
    uploaded,
    writeHttpMetadata(headers) {
      headers.set("Content-Type", overrides.contentType || "application/octet-stream");
    },
  };
}

class MemoryBucket {
  constructor(entries) {
    this.entries = new Map(Object.entries(entries).map(([key, value]) => [key, encoder.encode(value)]));
    this.headCalls = [];
    this.getCalls = [];
  }

  async head(key) {
    this.headCalls.push(key);
    const bytes = this.entries.get(key);
    return bytes ? metadata(bytes) : null;
  }

  async get(key, options = {}) {
    this.getCalls.push({ key, options });
    const original = this.entries.get(key);
    if (!original) {
      return null;
    }
    const range = options.range;
    const bytes = range ? original.slice(range.offset, range.offset + range.length) : original;
    return {
      ...metadata(original),
      body: new Blob([bytes]).stream(),
    };
  }
}

function environment(entries = {}) {
  const bucket = new MemoryBucket(entries);
  return {
    bucket,
    env: {
      PUBLIC_RELEASE_ID: "release-20260906",
      PUBLIC_CORPUS: bucket,
      STATIC_ASSETS: {
        async fetch() {
          return new Response("static", { headers: { "Content-Type": "text/html" } });
        },
      },
    },
  };
}

test("validates public object paths without path escapes", () => {
  assert.equal(objectPathFromUrl("https://benchlibrary.com/data/catalog.json"), "data/catalog.json");
  assert.equal(objectPathFromUrl("https://benchlibrary.com/assets/%5csecret"), null);
  assert.equal(objectPathFromUrl("https://benchlibrary.com/assets/a%2Fb"), null);
  assert.equal(objectPathFromUrl("https://benchlibrary.com/assets//secret"), null);
  assert.equal(objectPathFromUrl("https://benchlibrary.com/private/catalog.json"), null);
});

test("maps safe UI paths into the release site namespace", () => {
  assert.equal(sitePathFromUrl("https://benchlibrary.com/"), "site/index.html");
  assert.equal(sitePathFromUrl("https://benchlibrary.com/help/"), "site/help/index.html");
  assert.equal(sitePathFromUrl("https://benchlibrary.com/app.js"), "site/app.js");
  assert.equal(sitePathFromUrl("https://benchlibrary.com/%5csecret"), null);
  assert.equal(sitePathFromUrl("https://benchlibrary.com/_headers"), null);
});

test("parses single byte ranges", () => {
  assert.deepEqual(parseByteRange("bytes=1-3", 6), { offset: 1, length: 3 });
  assert.deepEqual(parseByteRange("bytes=3-", 6), { offset: 3, length: 3 });
  assert.deepEqual(parseByteRange("bytes=-2", 6), { offset: 4, length: 2 });
  assert.equal(parseByteRange("bytes=10-20", 6), false);
  assert.equal(parseByteRange("bytes=1-2,4-5", 6), false);
});

test("streams a complete R2 object through the immutable release prefix", async () => {
  const key = "releases/release-20260906/data/catalog.json";
  const { bucket, env } = environment({ [key]: "catalog" });
  const response = await worker.fetch(new Request("https://benchlibrary.com/data/catalog.json"), env);

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "catalog");
  assert.deepEqual(bucket.headCalls, [key]);
  assert.deepEqual(bucket.getCalls, [{ key, options: {} }]);
  assert.equal(response.headers.get("etag"), '"abc123"');
  assert.equal(response.headers.get("x-content-sha256"), "a".repeat(64));
  assert.equal(response.headers.get("accept-ranges"), "bytes");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
});

test("HEAD returns metadata without loading the object body", async () => {
  const key = "releases/release-20260906/assets/report.pdf";
  const { bucket, env } = environment({ [key]: "abcdef" });
  const response = await worker.fetch(new Request("https://benchlibrary.com/assets/report.pdf", { method: "HEAD" }), env);

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("content-length"), "6");
  assert.equal(await response.text(), "");
  assert.equal(bucket.getCalls.length, 0);
});

test("serves bounded and suffix Range requests with 206 metadata", async () => {
  const key = "releases/release-20260906/assets/file.bin";
  const first = environment({ [key]: "abcdef" });
  const bounded = await worker.fetch(new Request("https://benchlibrary.com/assets/file.bin", {
    headers: { Range: "bytes=1-3" },
  }), first.env);
  assert.equal(bounded.status, 206);
  assert.equal(await bounded.text(), "bcd");
  assert.equal(bounded.headers.get("content-range"), "bytes 1-3/6");
  assert.equal(bounded.headers.get("content-length"), "3");

  const second = environment({ [key]: "abcdef" });
  const suffix = await worker.fetch(new Request("https://benchlibrary.com/assets/file.bin", {
    headers: { Range: "bytes=-2" },
  }), second.env);
  assert.equal(suffix.status, 206);
  assert.equal(await suffix.text(), "ef");
});

test("returns 416 for an unsatisfiable or multi-part range", async () => {
  const key = "releases/release-20260906/assets/file.bin";
  const { bucket, env } = environment({ [key]: "abcdef" });
  const response = await worker.fetch(new Request("https://benchlibrary.com/assets/file.bin", {
    headers: { Range: "bytes=99-100" },
  }), env);

  assert.equal(response.status, 416);
  assert.equal(response.headers.get("content-range"), "bytes */6");
  assert.equal(bucket.getCalls.length, 0);
});

test("honors ETag conditions without fetching a body", async () => {
  const key = "releases/release-20260906/data/catalog.json";
  const { bucket, env } = environment({ [key]: "catalog" });
  const response = await worker.fetch(new Request("https://benchlibrary.com/data/catalog.json", {
    headers: { "If-None-Match": 'W/"abc123"' },
  }), env);

  assert.equal(response.status, 304);
  assert.equal(response.headers.get("etag"), '"abc123"');
  assert.equal(bucket.getCalls.length, 0);
});

test("ignores Range when If-Range does not match", async () => {
  const key = "releases/release-20260906/assets/file.bin";
  const { env } = environment({ [key]: "abcdef" });
  const response = await worker.fetch(new Request("https://benchlibrary.com/assets/file.bin", {
    headers: { Range: "bytes=1-2", "If-Range": '"different"' },
  }), env);

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "abcdef");
  assert.equal(response.headers.get("content-range"), null);
});

test("locks executable mirrors to text while allowing isolated preview HTML", async () => {
  const mirrorKey = "releases/release-20260906/assets/mirrors/sample.html";
  const previewKey = "releases/release-20260906/assets/previews/sample.html";
  const { env } = environment({
    [mirrorKey]: "<script>alert(1)</script>",
    [previewKey]: "<h1>preview</h1>",
  });

  const mirror = await worker.fetch(new Request("https://benchlibrary.com/assets/mirrors/sample.html"), env);
  assert.match(mirror.headers.get("content-type"), /^text\/plain/);
  assert.match(mirror.headers.get("content-disposition"), /^attachment/);
  assert.match(mirror.headers.get("content-security-policy"), /sandbox/);

  const preview = await worker.fetch(new Request("https://benchlibrary.com/assets/previews/sample.html"), env);
  assert.match(preview.headers.get("content-security-policy"), /connect-src 'none'/);
  assert.match(preview.headers.get("content-security-policy"), /(?:^|;)\s*sandbox allow-scripts(?:;|$)/);
  assert.doesNotMatch(preview.headers.get("content-security-policy"), /allow-same-origin/);
  assert.equal(preview.headers.get("content-disposition"), null);
});

test("forces unclassified active content to download as inert text", async () => {
  const key = "releases/release-20260906/assets/other/report.xhtml";
  const { env } = environment({ [key]: "<script>alert(1)</script>" });
  env.PUBLIC_CORPUS.head = async (requestedKey) => {
    const bytes = env.PUBLIC_CORPUS.entries.get(requestedKey);
    return bytes ? metadata(bytes, { contentType: "application/xhtml+xml" }) : null;
  };
  env.PUBLIC_CORPUS.get = async (requestedKey) => {
    const bytes = env.PUBLIC_CORPUS.entries.get(requestedKey);
    return bytes ? { ...metadata(bytes, { contentType: "application/xhtml+xml" }), body: new Blob([bytes]).stream() } : null;
  };

  const response = await worker.fetch(new Request("https://benchlibrary.com/assets/other/report.xhtml"), env);
  assert.match(response.headers.get("content-type"), /^text\/plain/);
  assert.match(response.headers.get("content-disposition"), /^attachment/);
  assert.match(response.headers.get("content-security-policy"), /sandbox/);
});

test("falls back to static assets outside public object routes", async () => {
  const { bucket, env } = environment();
  const response = await worker.fetch(new Request("https://benchlibrary.com/"), env);

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "static");
  assert.equal(bucket.headCalls.length, 0);
  assert.equal(response.headers.get("referrer-policy"), "no-referrer");
});

test("serves UI from the same R2 release when STATIC_ASSETS is unavailable", async () => {
  const key = "releases/release-20260906/site/index.html";
  const { bucket, env } = environment({ [key]: "<main>KW Bench Library</main>" });
  delete env.STATIC_ASSETS;

  const response = await worker.fetch(new Request("https://benchlibrary.com/"), env);
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "<main>KW Bench Library</main>");
  assert.deepEqual(bucket.headCalls, [key]);
  assert.match(response.headers.get("content-type"), /^text\/html/);
  assert.match(response.headers.get("content-security-policy"), /script-src 'self'/);
});

test("prefers STATIC_ASSETS over the R2 UI copy when the binding exists", async () => {
  const key = "releases/release-20260906/site/index.html";
  const { bucket, env } = environment({ [key]: "R2 UI" });

  const response = await worker.fetch(new Request("https://benchlibrary.com/"), env);
  assert.equal(await response.text(), "static");
  assert.equal(bucket.headCalls.length, 0);
});

test("rejects writes and refuses an unpublished release", async () => {
  const { bucket, env } = environment();
  const writeResponse = await worker.fetch(new Request("https://benchlibrary.com/data/catalog.json", {
    method: "POST",
  }), env);
  assert.equal(writeResponse.status, 405);
  assert.equal(writeResponse.headers.get("allow"), "GET, HEAD");

  env.PUBLIC_RELEASE_ID = "unpublished";
  const unpublished = await worker.fetch(new Request("https://benchlibrary.com/data/catalog.json"), env);
  assert.equal(unpublished.status, 503);
  assert.equal(bucket.headCalls.length, 0);
});

test("redirects plain HTTP to the same HTTPS URL", async () => {
  const { env } = environment();
  const response = await worker.fetch(new Request("http://benchlibrary.com/data/catalog.json?source=test"), env);
  assert.equal(response.status, 308);
  assert.equal(response.headers.get("location"), "https://benchlibrary.com/data/catalog.json?source=test");
});

test("does not expose R2 failures to clients", async () => {
  const { env } = environment();
  env.PUBLIC_CORPUS.head = async () => {
    throw new Error("internal storage failure detail");
  };
  const response = await worker.fetch(new Request("https://benchlibrary.com/data/catalog.json"), env);

  assert.equal(response.status, 500);
  assert.deepEqual(await response.json(), { error: "Internal server error" });
});
