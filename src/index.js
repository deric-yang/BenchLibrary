"use strict";

const PUBLIC_PATH_PREFIXES = ["/data/", "/assets/"];
const RELEASE_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const HASHED_ASSET_PATTERN = /(?:^|[/_.-])[a-f0-9]{32,}(?:[/_.-]|$)/i;

const BASE_SECURITY_HEADERS = Object.freeze({
  "Cross-Origin-Resource-Policy": "same-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  "Referrer-Policy": "no-referrer",
  "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "SAMEORIGIN",
});

const PREVIEW_CSP = [
  "sandbox allow-scripts",
  "default-src 'none'",
  "img-src 'self' data: blob:",
  "media-src 'self' data: blob:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:",
  "connect-src 'none'",
  "worker-src blob:",
  "frame-src 'none'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "navigate-to 'none'",
  "frame-ancestors 'self'",
].join("; ");

const APPLICATION_CSP = [
  "default-src 'self'",
  "img-src 'self' data: blob:",
  "media-src 'self' data: blob:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  "script-src 'self'",
  "connect-src 'self'",
  "frame-src 'self' blob:",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'self'",
].join("; ");

const CONTENT_TYPES = new Map([
  ["css", "text/css; charset=utf-8"],
  ["csv", "text/csv; charset=utf-8"],
  ["gif", "image/gif"],
  ["htm", "text/html; charset=utf-8"],
  ["html", "text/html; charset=utf-8"],
  ["jpeg", "image/jpeg"],
  ["jpg", "image/jpeg"],
  ["js", "text/javascript; charset=utf-8"],
  ["json", "application/json; charset=utf-8"],
  ["md", "text/markdown; charset=utf-8"],
  ["mp3", "audio/mpeg"],
  ["mp4", "video/mp4"],
  ["pdf", "application/pdf"],
  ["png", "image/png"],
  ["svg", "image/svg+xml"],
  ["txt", "text/plain; charset=utf-8"],
  ["webm", "video/webm"],
  ["webp", "image/webp"],
  ["woff", "font/woff"],
  ["woff2", "font/woff2"],
  ["xls", "application/vnd.ms-excel"],
  ["xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
  ["ppt", "application/vnd.ms-powerpoint"],
  ["pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"],
  ["doc", "application/msword"],
  ["docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
  ["zip", "application/zip"],
]);

function jsonError(status, error) {
  const headers = new Headers({
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
  });
  applySecurityHeaders(headers);
  return Response.json({ error }, { status, headers });
}

function applySecurityHeaders(headers) {
  for (const [name, value] of Object.entries(BASE_SECURITY_HEADERS)) {
    headers.set(name, value);
  }
}

function isPublicObjectPath(pathname) {
  return PUBLIC_PATH_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function objectPathFromUrl(input) {
  let pathname;
  try {
    pathname = new URL(input).pathname;
  } catch {
    return null;
  }

  if (!isPublicObjectPath(pathname) || /%(?:00|2f|5c)/i.test(pathname)) {
    return null;
  }

  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return null;
  }

  if (decoded.includes("\\") || decoded.includes("\0") || decoded.includes("//")) {
    return null;
  }

  const segments = decoded.slice(1).split("/");
  if (segments.length < 2 || segments.some((segment) => !segment || segment === "." || segment === "..")) {
    return null;
  }
  return decoded.slice(1);
}

export function sitePathFromUrl(input) {
  let pathname;
  try {
    pathname = new URL(input).pathname;
  } catch {
    return null;
  }
  if (/%(?:00|2f|5c)/i.test(pathname)) {
    return null;
  }

  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return null;
  }
  if (decoded.includes("\\") || decoded.includes("\0") || decoded.includes("//")) {
    return null;
  }

  const segments = decoded.split("/").filter(Boolean);
  if (segments.some((segment) => segment === "." || segment === ".." || segment.startsWith("."))) {
    return null;
  }
  if (segments.at(-1) === "_headers" || segments.at(-1) === "_redirects") {
    return null;
  }
  if (decoded.endsWith("/")) {
    segments.push("index.html");
  }
  return `site/${segments.join("/")}`;
}

function releaseId(env) {
  const value = typeof env.PUBLIC_RELEASE_ID === "string" ? env.PUBLIC_RELEASE_ID.trim() : "";
  return RELEASE_ID_PATTERN.test(value) ? value : null;
}

function httpEtag(object) {
  if (typeof object.httpEtag === "string" && object.httpEtag) {
    return object.httpEtag;
  }
  return typeof object.etag === "string" && object.etag ? `"${object.etag}"` : null;
}

function weakEtag(value) {
  return value.trim().replace(/^W\//i, "");
}

function etagListMatches(headerValue, etag, weak) {
  if (!headerValue || !etag) {
    return false;
  }
  return headerValue.split(",").some((candidate) => {
    const trimmed = candidate.trim();
    if (trimmed === "*") {
      return true;
    }
    return weak ? weakEtag(trimmed) === weakEtag(etag) : trimmed === etag && !/^W\//i.test(trimmed);
  });
}

function validHttpDate(value) {
  if (!value) {
    return null;
  }
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? null : timestamp;
}

function objectTimestamp(object) {
  if (!(object.uploaded instanceof Date)) {
    return null;
  }
  return Math.floor(object.uploaded.getTime() / 1000) * 1000;
}

function preconditionStatus(request, object) {
  const etag = httpEtag(object);
  const ifMatch = request.headers.get("If-Match");
  if (ifMatch && !etagListMatches(ifMatch, etag, false)) {
    return 412;
  }

  const uploadedAt = objectTimestamp(object);
  const ifUnmodifiedSince = validHttpDate(request.headers.get("If-Unmodified-Since"));
  if (!ifMatch && ifUnmodifiedSince !== null && uploadedAt !== null && uploadedAt > ifUnmodifiedSince) {
    return 412;
  }

  const ifNoneMatch = request.headers.get("If-None-Match");
  if (ifNoneMatch && etagListMatches(ifNoneMatch, etag, true)) {
    return 304;
  }

  const ifModifiedSince = validHttpDate(request.headers.get("If-Modified-Since"));
  if (!ifNoneMatch && ifModifiedSince !== null && uploadedAt !== null && uploadedAt <= ifModifiedSince) {
    return 304;
  }
  return null;
}

function shouldHonorRange(request, object) {
  const ifRange = request.headers.get("If-Range");
  if (!ifRange) {
    return true;
  }
  if (/^(?:W\/)?"/.test(ifRange.trim())) {
    return !/^W\//i.test(ifRange.trim()) && ifRange.trim() === httpEtag(object);
  }
  const ifRangeDate = validHttpDate(ifRange);
  const uploadedAt = objectTimestamp(object);
  return ifRangeDate !== null && uploadedAt !== null && uploadedAt <= ifRangeDate;
}

export function parseByteRange(headerValue, size) {
  if (!headerValue) {
    return null;
  }
  const match = /^bytes=(\d*)-(\d*)$/i.exec(headerValue.trim());
  if (!match || (!match[1] && !match[2]) || !Number.isSafeInteger(size) || size < 0) {
    return false;
  }

  if (!match[1]) {
    const suffixLength = Number(match[2]);
    if (!Number.isSafeInteger(suffixLength) || suffixLength <= 0 || size === 0) {
      return false;
    }
    const length = Math.min(suffixLength, size);
    return { offset: size - length, length };
  }

  const start = Number(match[1]);
  const requestedEnd = match[2] ? Number(match[2]) : size - 1;
  if (
    !Number.isSafeInteger(start)
    || !Number.isSafeInteger(requestedEnd)
    || start >= size
    || requestedEnd < start
  ) {
    return false;
  }
  const end = Math.min(requestedEnd, size - 1);
  return { offset: start, length: end - start + 1 };
}

function extension(path) {
  const basename = path.slice(path.lastIndexOf("/") + 1);
  const dot = basename.lastIndexOf(".");
  return dot === -1 ? "" : basename.slice(dot + 1).toLowerCase();
}

function isPreviewHtml(path) {
  return path.startsWith("assets/previews/") && ["htm", "html"].includes(extension(path));
}

function isUnsafeMirrorSource(path) {
  return path.startsWith("assets/mirrors/") && [
    "cjs", "htm", "html", "js", "mjs", "svg", "svgz", "xht", "xhtml",
  ].includes(extension(path));
}

function isVerifierSource(path) {
  return path.startsWith("assets/verifiers/");
}

function cacheControl(path) {
  if (path.startsWith("site/")) {
    return ["htm", "html"].includes(extension(path))
      ? "public, max-age=0, must-revalidate"
      : "public, max-age=300, must-revalidate";
  }
  if (isPreviewHtml(path)) {
    return "no-store";
  }
  if (path.startsWith("data/") || path.endsWith(".json") || path.endsWith(".json.gz")) {
    return "public, max-age=300, stale-while-revalidate=86400";
  }
  if (HASHED_ASSET_PATTERN.test(path)) {
    return "public, max-age=31536000, immutable";
  }
  return "public, max-age=86400, stale-while-revalidate=604800";
}

function filenameFromPath(path) {
  return path.slice(path.lastIndexOf("/") + 1).replace(/[\r\n"]/g, "_");
}

function objectHeaders(object, path, contentLength) {
  const headers = new Headers();
  if (typeof object.writeHttpMetadata === "function") {
    object.writeHttpMetadata(headers);
  }

  const inferredContentType = CONTENT_TYPES.get(extension(path));
  if (path.startsWith("site/") && inferredContentType) {
    headers.set("Content-Type", inferredContentType);
  } else if (!headers.has("Content-Type")) {
    headers.set("Content-Type", CONTENT_TYPES.get(extension(path)) || "application/octet-stream");
  }
  const etag = httpEtag(object);
  if (etag) {
    headers.set("ETag", etag);
  }
  if (object.uploaded instanceof Date) {
    headers.set("Last-Modified", object.uploaded.toUTCString());
  }
  if (/^[a-f0-9]{64}$/i.test(object.customMetadata?.sha256 || "")) {
    headers.set("X-Content-SHA256", object.customMetadata.sha256.toLowerCase());
  }
  headers.set("Accept-Ranges", "bytes");
  headers.set("Cache-Control", cacheControl(path));
  headers.set("Content-Length", String(contentLength));
  applySecurityHeaders(headers);

  if (path.startsWith("site/") && ["htm", "html"].includes(extension(path))) {
    headers.set("Content-Security-Policy", APPLICATION_CSP);
  } else if (isPreviewHtml(path)) {
    headers.set("Content-Type", "text/html; charset=utf-8");
    headers.set("Content-Security-Policy", PREVIEW_CSP);
  } else if (isUnsafeMirrorSource(path)) {
    headers.set("Content-Type", "text/plain; charset=utf-8");
    headers.set("Content-Disposition", `attachment; filename="${filenameFromPath(path)}"`);
    headers.set("Content-Security-Policy", "default-src 'none'; sandbox");
  } else if (isVerifierSource(path)) {
    headers.set("Content-Type", "text/plain; charset=utf-8");
    headers.set("Content-Security-Policy", "default-src 'none'; sandbox");
  } else if (/^(?:text\/html|application\/(?:xhtml\+xml|javascript)|image\/svg\+xml)\b/i.test(headers.get("Content-Type") || "")) {
    headers.set("Content-Type", "text/plain; charset=utf-8");
    headers.set("Content-Disposition", `attachment; filename="${filenameFromPath(path)}"`);
    headers.set("Content-Security-Policy", "default-src 'none'; sandbox");
  }
  return headers;
}

function emptyObjectResponse(status, object, path) {
  const headers = objectHeaders(object, path, object.size);
  headers.delete("Content-Length");
  return new Response(null, { status, headers });
}

async function serveR2Object(request, env, path) {
  const currentReleaseId = releaseId(env);
  if (!currentReleaseId || currentReleaseId === "unpublished") {
    return jsonError(503, "Public release is not configured");
  }

  const key = `releases/${currentReleaseId}/${path}`;
  const object = await env.PUBLIC_CORPUS.head(key);
  if (object === null) {
    return jsonError(404, "Not found");
  }

  const conditionStatus = preconditionStatus(request, object);
  if (conditionStatus !== null) {
    return emptyObjectResponse(conditionStatus, object, path);
  }

  if (request.method === "HEAD") {
    return new Response(null, { status: 200, headers: objectHeaders(object, path, object.size) });
  }

  const requestedRange = request.headers.get("Range");
  const range = requestedRange && shouldHonorRange(request, object)
    ? parseByteRange(requestedRange, object.size)
    : null;
  if (range === false) {
    const headers = objectHeaders(object, path, object.size);
    headers.set("Content-Range", `bytes */${object.size}`);
    headers.delete("Content-Length");
    return new Response(null, { status: 416, headers });
  }

  const bodyObject = range
    ? await env.PUBLIC_CORPUS.get(key, { range })
    : await env.PUBLIC_CORPUS.get(key);
  if (bodyObject === null || !("body" in bodyObject) || bodyObject.body === null) {
    return jsonError(404, "Not found");
  }

  const responseLength = range ? range.length : object.size;
  const headers = objectHeaders(bodyObject, path, responseLength);
  if (range) {
    headers.set("Content-Range", `bytes ${range.offset}-${range.offset + range.length - 1}/${object.size}`);
  }
  return new Response(bodyObject.body, { status: range ? 206 : 200, headers });
}

async function handleRequest(request, env) {
  const url = new URL(request.url);
  if (url.protocol !== "https:") {
    url.protocol = "https:";
    return new Response(null, {
      status: 308,
      headers: {
        Location: url.toString(),
        "Cache-Control": "public, max-age=86400",
      },
    });
  }
  if (request.method !== "GET" && request.method !== "HEAD") {
    const response = jsonError(405, "Method not allowed");
    response.headers.set("Allow", "GET, HEAD");
    return response;
  }

  if (!isPublicObjectPath(url.pathname)) {
    if (env.STATIC_ASSETS && typeof env.STATIC_ASSETS.fetch === "function") {
      const response = await env.STATIC_ASSETS.fetch(request);
      const headers = new Headers(response.headers);
      applySecurityHeaders(headers);
      if (headers.get("Content-Type")?.toLowerCase().includes("text/html")) {
        headers.set("Content-Security-Policy", APPLICATION_CSP);
      }
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    }

    const sitePath = sitePathFromUrl(request.url);
    return sitePath ? serveR2Object(request, env, sitePath) : jsonError(400, "Invalid site path");
  }

  const path = objectPathFromUrl(request.url);
  if (!path) {
    return jsonError(400, "Invalid object path");
  }
  return serveR2Object(request, env, path);
}

export default {
  async fetch(request, env) {
    try {
      return await handleRequest(request, env);
    } catch (error) {
      console.error(JSON.stringify({
        message: "request failed",
        error: error instanceof Error ? error.message : String(error),
        method: request.method,
        path: new URL(request.url).pathname,
      }));
      return jsonError(500, "Internal server error");
    }
  },
};
