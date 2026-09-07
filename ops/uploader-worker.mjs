const AUTH_HEADER = "X-KWBL-Upload-Key";
const KEY_HEADER = "X-KWBL-Object-Key";
const SHA_HEADER = "X-KWBL-SHA256";
const CONTENT_TYPE_HEADER = "X-KWBL-Content-Type";
const CACHE_CONTROL_HEADER = "X-KWBL-Cache-Control";
const CONTENT_ENCODING_HEADER = "X-KWBL-Content-Encoding";
const CONTENT_DISPOSITION_HEADER = "X-KWBL-Content-Disposition";
const MAX_DIRECT_BYTES = 32 * 1024 * 1024;
const MIN_PART_BYTES = 5 * 1024 * 1024;
const MAX_PART_BYTES = 32 * 1024 * 1024;
const MAX_MULTIPART_PARTS = 10000;
const MAX_COMPLETION_BYTES = 8 * 1024 * 1024;
// R2 single-part writes are capped at 5 GiB minus 5 MiB. Larger unchanged
// objects must use the existing client multipart path instead of stream copy.
const MAX_COPY_BYTES = 5 * 1024 * 1024 * 1024 - 5 * 1024 * 1024;
const INVENTORY_PAGE_SIZE = 1000;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/_kwbl-upload/v1/")) {
      return response(404, "Not found");
    }
    if (!(await isAuthorized(request, env.UPLOAD_KEY_SHA256))) {
      return response(404, "Not found");
    }

    try {
      if (url.pathname === "/_kwbl-upload/v1/health" && request.method === "GET") {
        const payload = { ok: true, prefix: env.UPLOAD_PREFIX };
        const copySourcePrefix = configuredCopySourcePrefix(env.COPY_SOURCE_PREFIX, env.UPLOAD_PREFIX);
        if (copySourcePrefix) {
          payload.copy_source_prefix = copySourcePrefix;
        }
        return json(payload);
      }
      if (url.pathname === "/_kwbl-upload/v1/inventory") {
        if (request.method !== "GET") {
          return response(405, "Method not allowed", { Allow: "GET" });
        }
        return await listInventory(url, env.PUBLIC_CORPUS, env.UPLOAD_PREFIX);
      }

      const relativeKey = decodeKey(request.headers.get(KEY_HEADER));
      const objectKey = validateObjectKey(relativeKey, env.UPLOAD_PREFIX);

      if (url.pathname === "/_kwbl-upload/v1/object" && request.method === "PUT") {
        return await putObject(request, env.PUBLIC_CORPUS, objectKey);
      }
      if (url.pathname === "/_kwbl-upload/v1/copy" && request.method === "POST") {
        const copySourcePrefix = configuredCopySourcePrefix(env.COPY_SOURCE_PREFIX, env.UPLOAD_PREFIX);
        if (!copySourcePrefix) {
          throw new ClientError(503, "Copy source is not configured");
        }
        return await copyObject(
          request,
          env.PUBLIC_CORPUS,
          relativeKey,
          objectKey,
          copySourcePrefix,
        );
      }
      if (url.pathname === "/_kwbl-upload/v1/multipart/init" && request.method === "POST") {
        return await initializeMultipart(request, env.PUBLIC_CORPUS, objectKey);
      }
      if (url.pathname === "/_kwbl-upload/v1/multipart/part" && request.method === "PUT") {
        return await uploadPart(request, env.PUBLIC_CORPUS, objectKey);
      }
      if (url.pathname === "/_kwbl-upload/v1/multipart/complete" && request.method === "POST") {
        return await completeMultipart(request, env.PUBLIC_CORPUS, objectKey);
      }
      if (url.pathname === "/_kwbl-upload/v1/multipart/abort" && request.method === "POST") {
        return await abortMultipart(request, env.PUBLIC_CORPUS, objectKey);
      }
      return response(405, "Method not allowed", { Allow: "GET, PUT, POST" });
    }
    catch (error) {
      const status = error instanceof ClientError ? error.status : 500;
      const message = status >= 500 ? "Upload operation failed" : error.message;
      const payload = { ok: false, error: message };
      if (error instanceof ClientError && error.code) {
        payload.code = error.code;
      }
      return json(payload, status);
    }
  },
};

class ClientError extends Error {
  constructor(status, message, code = "") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function isAuthorized(request, expectedHash) {
  const supplied = request.headers.get(AUTH_HEADER);
  if (!supplied || !expectedHash || !/^[a-f0-9]{64}$/i.test(expectedHash)) {
    return false;
  }
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(supplied));
  const actual = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return timingSafeEqual(actual.toLowerCase(), expectedHash.toLowerCase());
}

function timingSafeEqual(left, right) {
  if (left.length !== right.length) {
    return false;
  }
  let mismatch = 0;
  for (let index = 0; index < left.length; index += 1) {
    mismatch |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return mismatch === 0;
}

function decodeKey(encoded) {
  if (!encoded || encoded.length > 4096 || !/^[A-Za-z0-9_-]+$/.test(encoded)) {
    throw new ClientError(400, "Missing or invalid object key");
  }
  const padded = encoded.replaceAll("-", "+").replaceAll("_", "/").padEnd(Math.ceil(encoded.length / 4) * 4, "=");
  let binary;
  try {
    binary = atob(padded);
  }
  catch {
    throw new ClientError(400, "Invalid object key encoding");
  }
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  }
  catch {
    throw new ClientError(400, "Object key is not UTF-8");
  }
}

function validateObjectKey(relativeKey, uploadPrefix) {
  validateUploadPrefix(uploadPrefix);
  if (!relativeKey || relativeKey.startsWith("/") || relativeKey.includes("\\") || relativeKey.includes("\0")) {
    throw new ClientError(400, "Unsafe object key");
  }
  const segments = relativeKey.split("/");
  if (segments.some((segment) => !segment || segment === "." || segment === "..")) {
    throw new ClientError(400, "Unsafe object key");
  }
  if (!['site', 'data', 'assets'].includes(segments[0]) && relativeKey !== "public_manifest.json") {
    throw new ClientError(403, "Object is outside the public release surface");
  }
  return `${uploadPrefix}${relativeKey}`;
}

function validateUploadPrefix(uploadPrefix) {
  if (!uploadPrefix || !/^releases\/[A-Za-z0-9][A-Za-z0-9._-]{0,127}\/$/.test(uploadPrefix)) {
    throw new Error("Uploader prefix is not configured safely");
  }
}

function configuredCopySourcePrefix(copySourcePrefix, uploadPrefix) {
  validateUploadPrefix(uploadPrefix);
  if (copySourcePrefix === undefined || copySourcePrefix === null || copySourcePrefix === "") {
    return null;
  }
  validateUploadPrefix(copySourcePrefix);
  if (copySourcePrefix === uploadPrefix) {
    throw new Error("Copy source prefix must differ from the upload prefix");
  }
  return copySourcePrefix;
}

async function listInventory(url, bucket, uploadPrefix) {
  validateUploadPrefix(uploadPrefix);
  const cursor = url.searchParams.get("cursor");
  if (cursor !== null && (!cursor || cursor.length > 4096 || /[\r\n\0]/.test(cursor))) {
    throw new ClientError(400, "Invalid inventory cursor");
  }
  const options = {
    prefix: uploadPrefix,
    limit: INVENTORY_PAGE_SIZE,
    include: ["customMetadata", "httpMetadata"],
  };
  if (cursor !== null) {
    options.cursor = cursor;
  }
  const listing = await bucket.list(options);
  const truncated = listing.truncated === true;
  const nextCursor = truncated ? listing.cursor : null;
  if (truncated && (typeof nextCursor !== "string" || !nextCursor)) {
    throw new Error("R2 returned a truncated inventory without a cursor");
  }
  const objects = listing.objects.map((object) => {
    if (typeof object.key !== "string" || !object.key.startsWith(uploadPrefix)) {
      throw new Error("R2 returned an object outside the configured prefix");
    }
    return {
      key: object.key,
      size: object.size,
      custom_metadata: {
        sha256: typeof object.customMetadata?.sha256 === "string"
          ? object.customMetadata.sha256
          : "",
      },
      http_metadata: {
        cache_control: typeof object.httpMetadata?.cacheControl === "string"
          ? object.httpMetadata.cacheControl
          : "",
        content_disposition: typeof object.httpMetadata?.contentDisposition === "string"
          ? object.httpMetadata.contentDisposition
          : "",
        content_encoding: typeof object.httpMetadata?.contentEncoding === "string"
          ? object.httpMetadata.contentEncoding
          : "",
        content_type: typeof object.httpMetadata?.contentType === "string"
          ? object.httpMetadata.contentType
          : "",
      },
    };
  });
  return json({
    ok: true,
    prefix: uploadPrefix,
    objects,
    cursor: nextCursor,
    truncated,
  });
}

function metadataFrom(request) {
  const sha256 = request.headers.get(SHA_HEADER) || "";
  if (!/^[a-f0-9]{64}$/i.test(sha256)) {
    throw new ClientError(400, "Missing or invalid SHA-256");
  }
  const contentType = sanitizeMetadataValue(request.headers.get(CONTENT_TYPE_HEADER), 200)
    || "application/octet-stream";
  const cacheControl = sanitizeMetadataValue(request.headers.get(CACHE_CONTROL_HEADER), 200)
    || "public, max-age=3600";
  const contentEncoding = sanitizeMetadataValue(request.headers.get(CONTENT_ENCODING_HEADER), 100);
  const contentDisposition = sanitizeMetadataValue(request.headers.get(CONTENT_DISPOSITION_HEADER), 500);
  const httpMetadata = { contentType, cacheControl };
  if (contentEncoding) {
    httpMetadata.contentEncoding = contentEncoding;
  }
  if (contentDisposition) {
    httpMetadata.contentDisposition = contentDisposition;
  }
  return {
    sha256: sha256.toLowerCase(),
    options: {
      httpMetadata,
      customMetadata: { sha256: sha256.toLowerCase() },
    },
  };
}

function sanitizeMetadataValue(value, maximumLength) {
  if (!value) {
    return "";
  }
  if (value.length > maximumLength || /[\r\n\0]/.test(value)) {
    throw new ClientError(400, "Invalid metadata header");
  }
  return value;
}

async function putObject(request, bucket, objectKey) {
  const length = Number(request.headers.get("Content-Length"));
  if (!Number.isSafeInteger(length) || length < 0 || length > MAX_DIRECT_BYTES) {
    throw new ClientError(413, "Use multipart upload for this object");
  }
  const metadata = metadataFrom(request);
  const existing = await bucket.head(objectKey);
  if (storedObjectMatches(existing, length, metadata)) {
    return json({ ok: true, skipped: true, size: existing.size, etag: existing.httpEtag });
  }
  const body = length === 0 ? new Uint8Array(0) : request.body;
  const stored = await bucket.put(objectKey, body, {
    ...metadata.options,
    sha256: metadata.sha256,
  });
  if (stored === null || stored.size !== length) {
    throw new Error("R2 did not persist the complete object");
  }
  return json({ ok: true, skipped: false, size: stored.size, etag: stored.httpEtag });
}

async function copyObject(request, bucket, relativeKey, objectKey, copySourcePrefix) {
  const expectedSize = Number(request.headers.get("X-KWBL-Object-Size"));
  if (!Number.isSafeInteger(expectedSize) || expectedSize < 0 || expectedSize > MAX_COPY_BYTES) {
    throw new ClientError(400, "Invalid copy object size");
  }
  const metadata = metadataFrom(request);
  const existing = await bucket.head(objectKey);
  if (storedObjectMatches(existing, expectedSize, metadata)) {
    return json({
      ok: true,
      copied: false,
      skipped: true,
      size: existing.size,
      sha256: metadata.sha256,
    });
  }

  const sourceKey = validateObjectKey(relativeKey, copySourcePrefix);
  const source = await bucket.head(sourceKey);
  if (!storedContentMatches(source, expectedSize, metadata.sha256) || !validEtag(source.etag)) {
    return json({ ok: true, copied: false, skipped: false, source_usable: false });
  }
  const sourceBody = await bucket.get(sourceKey, { onlyIf: { etagMatches: source.etag } });
  if (
    !storedContentMatches(sourceBody, expectedSize, metadata.sha256)
    || !(sourceBody && "body" in sourceBody)
    || sourceBody.body === undefined
    || sourceBody.body === null
  ) {
    return json({ ok: true, copied: false, skipped: false, source_usable: false });
  }

  const stored = await bucket.put(objectKey, sourceBody.body, {
    ...metadata.options,
    sha256: metadata.sha256,
  });
  if (!storedObjectMatches(stored, expectedSize, metadata)) {
    throw new Error("R2 copy failed its final metadata verification");
  }
  return json({
    ok: true,
    copied: true,
    skipped: false,
    size: stored.size,
    sha256: metadata.sha256,
  });
}

async function initializeMultipart(request, bucket, objectKey) {
  const metadata = metadataFrom(request);
  const { expectedSize } = multipartLayoutFrom(request);
  const existing = await bucket.head(objectKey);
  if (storedObjectMatches(existing, expectedSize, metadata)) {
    return json({ ok: true, skipped: true, size: existing.size, etag: existing.httpEtag });
  }
  const upload = await bucket.createMultipartUpload(objectKey, metadata.options);
  return json({ ok: true, skipped: false, uploadId: upload.uploadId });
}

function resumeMultipart(request, bucket, objectKey) {
  const uploadId = request.headers.get("X-KWBL-Upload-Id");
  if (!uploadId || uploadId.length > 512 || !/^[\x20-\x7e]+$/.test(uploadId)) {
    throw new ClientError(400, "Missing or invalid upload ID");
  }
  return bucket.resumeMultipartUpload(objectKey, uploadId);
}

async function uploadPart(request, bucket, objectKey) {
  const { expectedParts, expectedSize, partSize } = multipartLayoutFrom(request);
  const partNumber = Number(request.headers.get("X-KWBL-Part-Number"));
  const length = Number(request.headers.get("Content-Length"));
  if (!Number.isInteger(partNumber) || partNumber < 1 || partNumber > expectedParts) {
    throw new ClientError(400, "Invalid part number");
  }
  const expectedLength = partNumber === expectedParts
    ? expectedSize - partSize * (expectedParts - 1)
    : partSize;
  if (length !== expectedLength) {
    throw new ClientError(400, "Multipart part length does not match its declared layout");
  }
  let part;
  try {
    const upload = resumeMultipart(request, bucket, objectKey);
    part = await upload.uploadPart(partNumber, request.body);
  }
  catch (error) {
    if (isMissingMultipartUpload(error)) {
      throw new ClientError(409, "Multipart upload no longer exists", "multipart_upload_missing");
    }
    throw error;
  }
  if (part?.partNumber !== partNumber || !validEtag(part?.etag)) {
    throw new Error("R2 returned an invalid uploaded-part descriptor");
  }
  return json({ ok: true, partNumber: part.partNumber, etag: part.etag });
}

async function completeMultipart(request, bucket, objectKey) {
  const metadata = metadataFrom(request);
  const { expectedParts, expectedSize } = multipartLayoutFrom(request);
  const payload = await multipartCompletionPayload(request);
  const parts = Array.isArray(payload?.parts) ? payload.parts : [];
  if (parts.length !== expectedParts) {
    throw new ClientError(400, "Invalid multipart completion payload");
  }
  for (let index = 0; index < parts.length; index += 1) {
    const part = parts[index];
    if (part?.partNumber !== index + 1 || !validEtag(part?.etag)) {
      throw new ClientError(400, "Invalid multipart part descriptor");
    }
  }
  let recovered = false;
  try {
    const upload = resumeMultipart(request, bucket, objectKey);
    await upload.complete(parts);
  }
  catch (error) {
    const existing = await bucket.head(objectKey);
    if (!storedObjectMatches(existing, expectedSize, metadata)) {
      if (isMissingMultipartUpload(error)) {
        throw new ClientError(409, "Multipart upload no longer exists", "multipart_upload_missing");
      }
      throw error;
    }
    recovered = true;
  }
  const stored = await bucket.head(objectKey);
  if (!storedObjectMatches(stored, expectedSize, metadata)) {
    throw new Error("R2 multipart completion failed its final metadata verification");
  }
  return json({
    ok: true,
    size: stored.size,
    etag: stored.httpEtag,
    sha256: metadata.sha256,
    recovered,
  });
}

async function abortMultipart(request, bucket, objectKey) {
  try {
    const upload = resumeMultipart(request, bucket, objectKey);
    await upload.abort();
    return json({ ok: true, alreadyMissing: false });
  }
  catch (error) {
    if (isMissingMultipartUpload(error)) {
      return json({ ok: true, alreadyMissing: true });
    }
    throw error;
  }
}

function multipartLayoutFrom(request) {
  const expectedSize = Number(request.headers.get("X-KWBL-Object-Size"));
  const partSize = Number(request.headers.get("X-KWBL-Part-Size"));
  if (!Number.isSafeInteger(expectedSize) || expectedSize <= MAX_DIRECT_BYTES) {
    throw new ClientError(400, "Invalid multipart object size");
  }
  if (!Number.isSafeInteger(partSize) || partSize < MIN_PART_BYTES || partSize > MAX_PART_BYTES) {
    throw new ClientError(400, "Invalid multipart part size");
  }
  const expectedParts = Math.ceil(expectedSize / partSize);
  if (expectedParts < 2 || expectedParts > MAX_MULTIPART_PARTS) {
    throw new ClientError(400, "Invalid multipart part count");
  }
  return { expectedParts, expectedSize, partSize };
}

function validEtag(value) {
  return typeof value === "string" && value.length > 0 && value.length <= 512 && /^[\x20-\x7e]+$/.test(value);
}

function isMissingMultipartUpload(error) {
  const code = error && typeof error === "object" ? error.code : undefined;
  const name = error && typeof error === "object" ? error.name : undefined;
  const message = error instanceof Error ? error.message : String(error || "");
  return code === 10024
    || code === "10024"
    || name === "NoSuchUpload"
    || /(?:^|\D)10024(?:\D|$)/.test(message);
}

async function multipartCompletionPayload(request) {
  const length = Number(request.headers.get("Content-Length"));
  if (!Number.isSafeInteger(length) || length < 2 || length > MAX_COMPLETION_BYTES) {
    throw new ClientError(413, "Invalid multipart completion body size");
  }
  try {
    return await request.json();
  }
  catch {
    throw new ClientError(400, "Invalid multipart completion JSON");
  }
}

function storedObjectMatches(stored, expectedSize, metadata) {
  if (!storedContentMatches(stored, expectedSize, metadata.sha256)) {
    return false;
  }
  const actual = stored.httpMetadata || {};
  const expected = metadata.options.httpMetadata;
  return actual.contentType === expected.contentType
    && actual.cacheControl === expected.cacheControl
    && (actual.contentEncoding || "") === (expected.contentEncoding || "")
    && (actual.contentDisposition || "") === (expected.contentDisposition || "");
}

function storedContentMatches(stored, expectedSize, expectedSha256) {
  return Boolean(
    stored
    && stored.size === expectedSize
    && stored.customMetadata?.sha256 === expectedSha256,
  );
}

function response(status, body, extraHeaders = {}) {
  return new Response(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "text/plain; charset=utf-8",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
      ...extraHeaders,
    },
  });
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "application/json; charset=utf-8",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
