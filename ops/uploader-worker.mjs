const AUTH_HEADER = "X-KWBL-Upload-Key";
const KEY_HEADER = "X-KWBL-Object-Key";
const SHA_HEADER = "X-KWBL-SHA256";
const MAX_DIRECT_BYTES = 80 * 1024 * 1024;
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
        return json({ ok: true, prefix: env.UPLOAD_PREFIX });
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
      return json({ ok: false, error: message }, status);
    }
  },
};

class ClientError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
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
  const contentType = sanitizeMetadataValue(request.headers.get("Content-Type"), 200) || "application/octet-stream";
  const cacheControl = sanitizeMetadataValue(request.headers.get("Cache-Control"), 200) || "public, max-age=3600";
  const contentEncoding = sanitizeMetadataValue(request.headers.get("Content-Encoding"), 100);
  const contentDisposition = sanitizeMetadataValue(request.headers.get("Content-Disposition"), 500);
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
  if (existing && existing.size === length && existing.customMetadata?.sha256 === metadata.sha256) {
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

async function initializeMultipart(request, bucket, objectKey) {
  const metadata = metadataFrom(request);
  const expectedSize = Number(request.headers.get("X-KWBL-Object-Size"));
  if (!Number.isSafeInteger(expectedSize) || expectedSize <= MAX_DIRECT_BYTES) {
    throw new ClientError(400, "Invalid multipart object size");
  }
  const existing = await bucket.head(objectKey);
  if (existing && existing.size === expectedSize && existing.customMetadata?.sha256 === metadata.sha256) {
    return json({ ok: true, skipped: true, size: existing.size, etag: existing.httpEtag });
  }
  const upload = await bucket.createMultipartUpload(objectKey, metadata.options);
  return json({ ok: true, skipped: false, uploadId: upload.uploadId });
}

function resumeMultipart(request, bucket, objectKey) {
  const uploadId = request.headers.get("X-KWBL-Upload-Id");
  if (!uploadId || uploadId.length > 512 || /[\r\n\0]/.test(uploadId)) {
    throw new ClientError(400, "Missing or invalid upload ID");
  }
  return bucket.resumeMultipartUpload(objectKey, uploadId);
}

async function uploadPart(request, bucket, objectKey) {
  const upload = resumeMultipart(request, bucket, objectKey);
  const partNumber = Number(request.headers.get("X-KWBL-Part-Number"));
  const length = Number(request.headers.get("Content-Length"));
  if (!Number.isInteger(partNumber) || partNumber < 1 || partNumber > 10000) {
    throw new ClientError(400, "Invalid part number");
  }
  if (!Number.isSafeInteger(length) || length < 1 || length > MAX_DIRECT_BYTES) {
    throw new ClientError(413, "Invalid part size");
  }
  const part = await upload.uploadPart(partNumber, request.body);
  return json({ ok: true, partNumber: part.partNumber, etag: part.etag });
}

async function completeMultipart(request, bucket, objectKey) {
  const upload = resumeMultipart(request, bucket, objectKey);
  const payload = await request.json();
  const parts = Array.isArray(payload?.parts) ? payload.parts : [];
  if (!parts.length || parts.length > 10000) {
    throw new ClientError(400, "Invalid multipart completion payload");
  }
  for (const part of parts) {
    if (!Number.isInteger(part?.partNumber) || part.partNumber < 1 || typeof part?.etag !== "string") {
      throw new ClientError(400, "Invalid multipart part descriptor");
    }
  }
  const stored = await upload.complete(parts);
  return json({ ok: true, size: stored.size, etag: stored.httpEtag });
}

async function abortMultipart(request, bucket, objectKey) {
  const upload = resumeMultipart(request, bucket, objectKey);
  await upload.abort();
  return json({ ok: true });
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
