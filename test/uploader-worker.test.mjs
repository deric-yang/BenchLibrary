import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import uploaderWorker from "../ops/uploader-worker.mjs";


const uploadKey = "u".repeat(64);
const uploadHash = createHash("sha256").update(uploadKey).digest("hex");

function encodedKey(value) {
  return Buffer.from(value, "utf8").toString("base64url");
}

function request(path, { method = "GET", key = "", body, headers = {} } = {}) {
  const finalHeaders = new Headers(headers);
  finalHeaders.set("X-KWBL-Upload-Key", uploadKey);
  if (key) {
    finalHeaders.set("X-KWBL-Object-Key", encodedKey(key));
  }
  return new Request(`https://upload.example.test${path}`, { method, body, headers: finalHeaders });
}

function environment(inventoryPages = new Map()) {
  const calls = [];
  const bucket = {
    async head(key) {
      calls.push(["head", key]);
      return null;
    },
    async put(key, body, options) {
      const data = new Uint8Array(await new Response(body).arrayBuffer());
      calls.push(["put", key, data.byteLength, options]);
      return { size: data.byteLength, httpEtag: '"stored"' };
    },
    async list(options) {
      calls.push(["list", options]);
      const cursor = options.cursor || "";
      return inventoryPages.get(cursor) || { objects: [], truncated: false };
    },
  };
  return {
    calls,
    env: {
      PUBLIC_CORPUS: bucket,
      UPLOAD_KEY_SHA256: uploadHash,
      UPLOAD_PREFIX: "releases/release-20260906/",
    },
  };
}

test("hides uploader routes when authorization is missing", async () => {
  const { env } = environment();
  const response = await uploaderWorker.fetch(
    new Request("https://upload.example.test/_kwbl-upload/v1/health"),
    env,
  );
  assert.equal(response.status, 404);
});

test("does not expose inventory without the one-time key", async () => {
  const { calls, env } = environment();
  const response = await uploaderWorker.fetch(
    new Request("https://upload.example.test/_kwbl-upload/v1/inventory"),
    env,
  );
  assert.equal(response.status, 404);
  assert.equal(calls.length, 0);
});

test("reports only the configured immutable prefix on health", async () => {
  const { env } = environment();
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/health"), env);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true, prefix: "releases/release-20260906/" });
  assert.equal(response.headers.get("cache-control"), "no-store");
});

test("lists only the configured prefix with integrity metadata and pagination", async () => {
  const prefix = "releases/release-20260906/";
  const inventoryPages = new Map([
    ["", {
      objects: [{
        key: `${prefix}assets/first.bin`,
        size: 3,
        customMetadata: { sha256: "a".repeat(64), private: "not-returned" },
        httpMetadata: { contentType: "application/octet-stream" },
        etag: "not-returned",
      }],
      truncated: true,
      cursor: "next-page",
    }],
    ["next-page", {
      objects: [{
        key: `${prefix}data/catalog.json`,
        size: 7,
        customMetadata: { sha256: "b".repeat(64) },
      }],
      truncated: false,
    }],
  ]);
  const { calls, env } = environment(inventoryPages);

  const firstResponse = await uploaderWorker.fetch(request("/_kwbl-upload/v1/inventory"), env);
  assert.equal(firstResponse.status, 200);
  assert.deepEqual(await firstResponse.json(), {
    ok: true,
    prefix,
    objects: [{
      key: `${prefix}assets/first.bin`,
      size: 3,
      custom_metadata: { sha256: "a".repeat(64) },
    }],
    cursor: "next-page",
    truncated: true,
  });
  assert.deepEqual(calls[0], ["list", {
    prefix,
    limit: 1000,
    include: ["customMetadata", "httpMetadata"],
  }]);

  const secondResponse = await uploaderWorker.fetch(
    request("/_kwbl-upload/v1/inventory?cursor=next-page"),
    env,
  );
  assert.equal(secondResponse.status, 200);
  assert.deepEqual(await secondResponse.json(), {
    ok: true,
    prefix,
    objects: [{
      key: `${prefix}data/catalog.json`,
      size: 7,
      custom_metadata: { sha256: "b".repeat(64) },
    }],
    cursor: null,
    truncated: false,
  });
  assert.deepEqual(calls[1], ["list", {
    prefix,
    limit: 1000,
    include: ["customMetadata", "httpMetadata"],
    cursor: "next-page",
  }]);
});

test("rejects an empty inventory cursor before listing R2", async () => {
  const { calls, env } = environment();
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/inventory?cursor="), env);
  assert.equal(response.status, 400);
  assert.equal(calls.length, 0);
});

test("streams a validated public object into the release prefix", async () => {
  const { calls, env } = environment();
  const payload = new TextEncoder().encode("catalog");
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/object", {
    method: "PUT",
    key: "data/catalog.json",
    body: payload,
    headers: {
      "Cache-Control": "public, max-age=300",
      "Content-Length": String(payload.byteLength),
      "Content-Disposition": "attachment; filename=\"catalog.json\"",
      "Content-Encoding": "gzip",
      "Content-Type": "application/json",
      "X-KWBL-SHA256": createHash("sha256").update(payload).digest("hex"),
    },
  }), env);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).ok, true);
  assert.equal(calls[0][1], "releases/release-20260906/data/catalog.json");
  assert.equal(calls[1][0], "put");
  assert.equal(calls[1][2], payload.byteLength);
  assert.equal(calls[1][3].sha256, createHash("sha256").update(payload).digest("hex"));
  assert.equal(calls[1][3].httpMetadata.contentEncoding, "gzip");
  assert.equal(calls[1][3].httpMetadata.contentDisposition, "attachment; filename=\"catalog.json\"");
});

test("rejects paths outside the public release surface", async () => {
  const { env } = environment();
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/object", {
    method: "PUT",
    key: "private/jobs.json",
    body: "x",
    headers: {
      "Content-Length": "1",
      "Content-Type": "application/json",
      "X-KWBL-SHA256": "a".repeat(64),
    },
  }), env);
  assert.equal(response.status, 403);
});
