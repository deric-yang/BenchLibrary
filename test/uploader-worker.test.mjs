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
  if (body !== undefined && !finalHeaders.has("Content-Length")) {
    const length = typeof body === "string" ? Buffer.byteLength(body) : body.byteLength;
    finalHeaders.set("Content-Length", String(length));
  }
  return new Request(`https://upload.example.test${path}`, { method, body, headers: finalHeaders });
}

function environment(inventoryPages = new Map(), fixture = {}) {
  const calls = [];
  const objects = new Map();
  const uploads = new Map();
  let uploadSequence = 0;
  const bucket = {
    async head(key) {
      calls.push(["head", key]);
      return objects.get(key) || null;
    },
    async get(key, options = {}) {
      calls.push(["get", key, options]);
      const stored = objects.get(key) || null;
      if (!stored) {
        return null;
      }
      if (options.onlyIf?.etagMatches && options.onlyIf.etagMatches !== stored.etag) {
        const { body: _body, ...metadata } = stored;
        return metadata;
      }
      if (fixture.getReturnsMetadataOnly) {
        return { ...stored, body: undefined };
      }
      return stored;
    },
    async put(key, body, options) {
      const data = new Uint8Array(await new Response(body).arrayBuffer());
      calls.push(["put", key, data.byteLength, options]);
      const stored = {
        body: data,
        etag: "stored",
        size: data.byteLength,
        httpEtag: '"stored"',
        customMetadata: options.customMetadata,
        httpMetadata: fixture.directHttpMetadataOverride ?? options.httpMetadata,
      };
      objects.set(key, stored);
      return stored;
    },
    async list(options) {
      calls.push(["list", options]);
      const cursor = options.cursor || "";
      return inventoryPages.get(cursor) || { objects: [], truncated: false };
    },
    async createMultipartUpload(key, options) {
      const uploadId = `upload-${++uploadSequence}`;
      calls.push(["multipart-init", key, options, uploadId]);
      uploads.set(uploadId, { key, options, parts: new Map() });
      return { uploadId };
    },
    resumeMultipartUpload(key, uploadId) {
      calls.push(["multipart-resume", key, uploadId]);
      const state = uploads.get(uploadId);
      if (!state || state.key !== key) {
        throw new Error("The specified multipart upload does not exist. (10024)");
      }
      return {
        async uploadPart(partNumber, body) {
          const data = new Uint8Array(await new Response(body).arrayBuffer());
          const etag = `etag-${partNumber}`;
          state.parts.set(partNumber, { etag, size: data.byteLength });
          calls.push(["multipart-part", key, uploadId, partNumber, data.byteLength]);
          return { partNumber, etag };
        },
        async complete(parts) {
          calls.push(["multipart-complete", key, uploadId, parts]);
          for (const part of parts) {
            const uploaded = state.parts.get(part.partNumber);
            if (!uploaded || uploaded.etag !== part.etag) {
              throw new Error("completion referenced a part that was not uploaded");
            }
          }
          const uploadedSize = parts.reduce(
            (total, part) => total + state.parts.get(part.partNumber).size,
            0,
          );
          const stored = {
            size: fixture.multipartObjectSizeOverride ?? uploadedSize,
            httpEtag: '"multipart-stored"',
            customMetadata: state.options.customMetadata,
            httpMetadata: state.options.httpMetadata,
          };
          objects.set(key, stored);
          uploads.delete(uploadId);
          if (fixture.completeThrowsAfterStore) {
            throw new Error("simulated lost completion response");
          }
          return stored;
        },
        async abort() {
          calls.push(["multipart-abort", key, uploadId]);
          uploads.delete(uploadId);
        },
      };
    },
  };
  return {
    calls,
    objects,
    env: {
      PUBLIC_CORPUS: bucket,
      UPLOAD_KEY_SHA256: uploadHash,
      UPLOAD_PREFIX: "releases/release-20260906/",
      COPY_SOURCE_PREFIX: fixture.copySourcePrefix,
    },
  };
}

async function uploadMultipartParts(env, key, headers, uploadId, lengths) {
  const parts = [];
  for (let index = 0; index < lengths.length; index += 1) {
    const length = lengths[index];
    const partResponse = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/part", {
      method: "PUT",
      key,
      body: new Uint8Array(length),
      headers: {
        ...headers,
        "Content-Length": String(length),
        "X-KWBL-Part-Number": String(index + 1),
        "X-KWBL-Upload-Id": uploadId,
      },
    }), env);
    assert.equal(partResponse.status, 200);
    const part = await partResponse.json();
    parts.push({ partNumber: part.partNumber, etag: part.etag });
  }
  return parts;
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

test("reports the fixed prior-release prefix only to an authenticated client", async () => {
  const { env } = environment(new Map(), {
    copySourcePrefix: "releases/release-20260905/",
  });
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/health"), env);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    ok: true,
    prefix: "releases/release-20260906/",
    copy_source_prefix: "releases/release-20260905/",
  });
});

test("lists only the configured prefix with integrity metadata and pagination", async () => {
  const prefix = "releases/release-20260906/";
  const inventoryPages = new Map([
    ["", {
      objects: [{
        key: `${prefix}assets/first.bin`,
        size: 3,
        customMetadata: { sha256: "a".repeat(64), private: "not-returned" },
        httpMetadata: {
          cacheControl: "public, max-age=31536000, immutable",
          contentDisposition: "attachment",
          contentType: "application/octet-stream",
        },
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
      http_metadata: {
        cache_control: "public, max-age=31536000, immutable",
        content_disposition: "attachment",
        content_encoding: "",
        content_type: "application/octet-stream",
      },
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
      http_metadata: {
        cache_control: "",
        content_disposition: "",
        content_encoding: "",
        content_type: "",
      },
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
      "X-KWBL-Cache-Control": "public, max-age=300",
      "Content-Length": String(payload.byteLength),
      "X-KWBL-Content-Disposition": "attachment; filename=\"catalog.json\"",
      "X-KWBL-Content-Encoding": "gzip",
      "X-KWBL-Content-Type": "application/json",
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

test("rejects a direct object when R2 loses its declared HTTP metadata", async () => {
  const { env } = environment(new Map(), { directHttpMetadataOverride: {} });
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/object", {
    method: "PUT",
    key: "assets/metadata.bin",
    body: "abc",
    headers: {
      "Content-Length": "3",
      "X-KWBL-Cache-Control": "public, max-age=3600",
      "X-KWBL-Content-Disposition": "attachment",
      "X-KWBL-Content-Type": "application/octet-stream",
      "X-KWBL-SHA256": "a".repeat(64),
    },
  }), env);
  assert.equal(response.status, 500);
  assert.deepEqual(await response.json(), { ok: false, error: "Upload operation failed" });
});

test("copies an exact prior-release object without client retransmission", async () => {
  const copySourcePrefix = "releases/release-20260905/";
  const { calls, env, objects } = environment(new Map(), { copySourcePrefix });
  const payload = new TextEncoder().encode("unchanged artifact");
  const sha256 = createHash("sha256").update(payload).digest("hex");
  objects.set(`${copySourcePrefix}assets/unchanged.bin`, {
    body: payload,
    etag: "source-etag",
    httpEtag: '"source-etag"',
    size: payload.byteLength,
    customMetadata: { sha256 },
    httpMetadata: { contentType: "old/type", cacheControl: "old-cache" },
  });

  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/copy", {
    method: "POST",
    key: "assets/unchanged.bin",
    headers: {
      "X-KWBL-Object-Size": String(payload.byteLength),
      "X-KWBL-SHA256": sha256,
      "X-KWBL-Content-Type": "application/octet-stream",
      "X-KWBL-Cache-Control": "public, max-age=31536000, immutable",
    },
  }), env);

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    ok: true,
    copied: true,
    skipped: false,
    size: payload.byteLength,
    sha256,
  });
  assert.deepEqual(calls.slice(0, 3), [
    ["head", "releases/release-20260906/assets/unchanged.bin"],
    ["head", "releases/release-20260905/assets/unchanged.bin"],
    ["get", "releases/release-20260905/assets/unchanged.bin", {
      onlyIf: { etagMatches: "source-etag" },
    }],
  ]);
  const copied = objects.get("releases/release-20260906/assets/unchanged.bin");
  assert.deepEqual(copied.body, payload);
  assert.equal(copied.customMetadata.sha256, sha256);
  assert.equal(copied.httpMetadata.contentType, "application/octet-stream");
});

test("declines a prior-release object unless size and SHA-256 both match", async () => {
  const copySourcePrefix = "releases/release-20260905/";
  const { calls, env, objects } = environment(new Map(), { copySourcePrefix });
  objects.set(`${copySourcePrefix}assets/mismatch.bin`, {
    body: new TextEncoder().encode("old"),
    etag: "source-etag",
    size: 3,
    customMetadata: { sha256: "a".repeat(64) },
    httpMetadata: {},
  });
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/copy", {
    method: "POST",
    key: "assets/mismatch.bin",
    headers: {
      "X-KWBL-Object-Size": "3",
      "X-KWBL-SHA256": "b".repeat(64),
    },
  }), env);

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    ok: true,
    copied: false,
    skipped: false,
    source_usable: false,
  });
  assert.deepEqual(calls.map(([operation]) => operation), ["head", "head"]);
});

test("declines copy when the conditional R2 read returns metadata without a body", async () => {
  const copySourcePrefix = "releases/release-20260905/";
  const { calls, env, objects } = environment(new Map(), {
    copySourcePrefix,
    getReturnsMetadataOnly: true,
  });
  const payload = new TextEncoder().encode("changed during copy");
  const sha256 = createHash("sha256").update(payload).digest("hex");
  objects.set(`${copySourcePrefix}assets/raced.bin`, {
    body: payload,
    etag: "source-etag",
    size: payload.byteLength,
    customMetadata: { sha256 },
    httpMetadata: {},
  });

  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/copy", {
    method: "POST",
    key: "assets/raced.bin",
    headers: {
      "X-KWBL-Object-Size": String(payload.byteLength),
      "X-KWBL-SHA256": sha256,
    },
  }), env);

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    ok: true,
    copied: false,
    skipped: false,
    source_usable: false,
  });
  assert.deepEqual(calls.map(([operation]) => operation), ["head", "head", "get"]);
});

test("refuses copy when the source and destination prefixes are identical", async () => {
  const { calls, env } = environment(new Map(), {
    copySourcePrefix: "releases/release-20260906/",
  });
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/copy", {
    method: "POST",
    key: "assets/unsafe.bin",
    headers: {
      "X-KWBL-Object-Size": "1",
      "X-KWBL-SHA256": "a".repeat(64),
    },
  }), env);
  assert.equal(response.status, 500);
  assert.deepEqual(calls, []);
});

test("refuses a stream copy above the R2 single-part upload ceiling", async () => {
  const { calls, env } = environment(new Map(), {
    copySourcePrefix: "releases/release-20260905/",
  });
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/copy", {
    method: "POST",
    key: "assets/too-large.bin",
    headers: {
      "X-KWBL-Object-Size": String(5 * 1024 * 1024 * 1024),
      "X-KWBL-SHA256": "a".repeat(64),
    },
  }), env);
  assert.equal(response.status, 400);
  assert.deepEqual(calls, []);
});

test("requires multipart uploads above the conservative direct request limit", async () => {
  const { calls, env } = environment();
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/object", {
    method: "PUT",
    key: "assets/large.bin",
    body: "x",
    headers: {
      "Content-Length": String(32 * 1024 * 1024 + 1),
      "X-KWBL-SHA256": "a".repeat(64),
    },
  }), env);
  assert.equal(response.status, 413);
  assert.equal(calls.length, 0);
});

test("completes a fixed-layout multipart upload with final metadata verification", async () => {
  const objectSize = 33 * 1024 * 1024;
  const partSize = 16 * 1024 * 1024;
  const sha256 = "b".repeat(64);
  const key = "assets/large.bin";
  const headers = {
    "X-KWBL-Cache-Control": "public, max-age=31536000, immutable",
    "X-KWBL-Content-Disposition": "attachment; filename=\"large.bin\"",
    "X-KWBL-Content-Type": "application/octet-stream",
    "X-KWBL-Object-Size": String(objectSize),
    "X-KWBL-Part-Size": String(partSize),
    "X-KWBL-SHA256": sha256,
  };
  const { calls, env, objects } = environment();
  const initResponse = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/init", {
    method: "POST",
    key,
    headers,
  }), env);
  const uploadId = (await initResponse.json()).uploadId;
  const lengths = [partSize, partSize, objectSize - 2 * partSize];
  const parts = await uploadMultipartParts(env, key, headers, uploadId, lengths);
  const completeResponse = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/complete", {
    method: "POST",
    key,
    body: JSON.stringify({ parts }),
    headers: { ...headers, "X-KWBL-Upload-Id": uploadId },
  }), env);
  assert.equal(completeResponse.status, 200);
  assert.deepEqual(await completeResponse.json(), {
    ok: true,
    size: objectSize,
    etag: '"multipart-stored"',
    sha256,
    recovered: false,
  });
  const stored = objects.get("releases/release-20260906/assets/large.bin");
  assert.equal(stored.customMetadata.sha256, sha256);
  assert.equal(stored.httpMetadata.contentDisposition, "attachment; filename=\"large.bin\"");
  assert.deepEqual(
    calls.filter(([operation]) => operation === "multipart-part").map((call) => call[4]),
    lengths,
  );
});

test("rejects a multipart part whose length does not match its fixed slot", async () => {
  const objectSize = 33 * 1024 * 1024;
  const partSize = 16 * 1024 * 1024;
  const headers = {
    "X-KWBL-Object-Size": String(objectSize),
    "X-KWBL-Part-Size": String(partSize),
    "X-KWBL-SHA256": "c".repeat(64),
  };
  const { calls, env } = environment();
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/part", {
    method: "PUT",
    key: "assets/large.bin",
    body: "x",
    headers: {
      ...headers,
      "Content-Length": String(partSize - 1),
      "X-KWBL-Part-Number": "1",
      "X-KWBL-Upload-Id": "upload-never-resumed",
    },
  }), env);
  assert.equal(response.status, 400);
  assert.equal(calls.length, 0);
});

test("returns a stable conflict when an R2 multipart upload has expired", async () => {
  const objectSize = 33 * 1024 * 1024;
  const partSize = 16 * 1024 * 1024;
  const finalLength = objectSize - 2 * partSize;
  const { env } = environment();
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/part", {
    method: "PUT",
    key: "assets/expired.bin",
    body: new Uint8Array(finalLength),
    headers: {
      "Content-Length": String(finalLength),
      "X-KWBL-Object-Size": String(objectSize),
      "X-KWBL-Part-Number": "3",
      "X-KWBL-Part-Size": String(partSize),
      "X-KWBL-SHA256": "2".repeat(64),
      "X-KWBL-Upload-Id": "expired-upload",
    },
  }), env);
  assert.equal(response.status, 409);
  assert.deepEqual(await response.json(), {
    ok: false,
    error: "Multipart upload no longer exists",
    code: "multipart_upload_missing",
  });
});

test("treats aborting an already expired multipart upload as idempotent success", async () => {
  const { env } = environment();
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/abort", {
    method: "POST",
    key: "assets/expired.bin",
    headers: { "X-KWBL-Upload-Id": "expired-upload" },
  }), env);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true, alreadyMissing: true });
});

test("rejects incomplete or out-of-order multipart completion descriptors", async () => {
  const objectSize = 33 * 1024 * 1024;
  const partSize = 16 * 1024 * 1024;
  const headers = {
    "X-KWBL-Object-Size": String(objectSize),
    "X-KWBL-Part-Size": String(partSize),
    "X-KWBL-SHA256": "d".repeat(64),
    "X-KWBL-Upload-Id": "upload-never-resumed",
  };
  const { calls, env } = environment();
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/complete", {
    method: "POST",
    key: "assets/large.bin",
    body: JSON.stringify({
      parts: [
        { partNumber: 1, etag: "etag-1" },
        { partNumber: 3, etag: "etag-3" },
        { partNumber: 2, etag: "etag-2" },
      ],
    }),
    headers,
  }), env);
  assert.equal(response.status, 400);
  assert.equal(calls.length, 0);
});

test("recovers an idempotent multipart completion after a lost response", async () => {
  const objectSize = 33 * 1024 * 1024;
  const partSize = 16 * 1024 * 1024;
  const sha256 = "e".repeat(64);
  const key = "assets/recovered.bin";
  const headers = {
    "X-KWBL-Cache-Control": "public, max-age=31536000, immutable",
    "X-KWBL-Content-Type": "application/octet-stream",
    "X-KWBL-Object-Size": String(objectSize),
    "X-KWBL-Part-Size": String(partSize),
    "X-KWBL-SHA256": sha256,
  };
  const { env } = environment(new Map(), {
    completeThrowsAfterStore: true,
  });
  const initialized = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/init", {
    method: "POST",
    key,
    headers,
  }), env);
  const uploadId = (await initialized.json()).uploadId;
  const parts = await uploadMultipartParts(
    env,
    key,
    headers,
    uploadId,
    [partSize, partSize, objectSize - 2 * partSize],
  );
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/complete", {
    method: "POST",
    key,
    body: JSON.stringify({ parts }),
    headers: { ...headers, "X-KWBL-Upload-Id": uploadId },
  }), env);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).recovered, true);
});

test("fails completion when the final R2 object does not match its declared size", async () => {
  const objectSize = 33 * 1024 * 1024;
  const headers = {
    "X-KWBL-Content-Type": "application/octet-stream",
    "X-KWBL-Object-Size": String(objectSize),
    "X-KWBL-Part-Size": String(16 * 1024 * 1024),
    "X-KWBL-SHA256": "1".repeat(64),
  };
  const key = "assets/truncated.bin";
  const { env } = environment(new Map(), { multipartObjectSizeOverride: objectSize - 1 });
  const initialized = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/init", {
    method: "POST",
    key,
    headers,
  }), env);
  const uploadId = (await initialized.json()).uploadId;
  const partSize = 16 * 1024 * 1024;
  const parts = await uploadMultipartParts(
    env,
    key,
    headers,
    uploadId,
    [partSize, partSize, objectSize - 2 * partSize],
  );
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/complete", {
    method: "POST",
    key,
    body: JSON.stringify({ parts }),
    headers: { ...headers, "X-KWBL-Upload-Id": uploadId },
  }), env);
  assert.equal(response.status, 500);
  assert.deepEqual(await response.json(), { ok: false, error: "Upload operation failed" });
});

test("aborts only the authenticated upload ID under the fixed release key", async () => {
  const objectSize = 33 * 1024 * 1024;
  const headers = {
    "X-KWBL-Object-Size": String(objectSize),
    "X-KWBL-Part-Size": String(16 * 1024 * 1024),
    "X-KWBL-SHA256": "f".repeat(64),
  };
  const key = "assets/to-abort.bin";
  const { calls, env } = environment();
  const initialized = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/init", {
    method: "POST",
    key,
    headers,
  }), env);
  const uploadId = (await initialized.json()).uploadId;
  const response = await uploaderWorker.fetch(request("/_kwbl-upload/v1/multipart/abort", {
    method: "POST",
    key,
    headers: { "X-KWBL-Upload-Id": uploadId },
  }), env);
  assert.equal(response.status, 200);
  assert.deepEqual(calls.at(-1), [
    "multipart-abort",
    "releases/release-20260906/assets/to-abort.bin",
    uploadId,
  ]);
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
