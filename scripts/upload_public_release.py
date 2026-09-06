#!/usr/bin/env python3
"""Upload a validated public release through the temporary R2 uploader Worker."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import mimetypes
import os
import pathlib
import random
import re
import stat
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Any

import requests

if __package__:
    from .verify_r2_release import VerificationError, verify_release
else:
    from verify_r2_release import VerificationError, verify_release


DIRECT_LIMIT = 32 * 1024 * 1024
PART_SIZE = 16 * 1024 * 1024
MAX_ATTEMPTS = 6
MAX_INVENTORY_PAGES = 100000
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
ALLOWED_ROOTS = {"site", "data", "assets"}
RELEASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class ReleaseFile:
    """Describe one immutable file and its upload response metadata."""

    path: str
    size: int
    sha256: str
    content_type: str
    cache_control: str
    content_encoding: str = ""
    content_disposition: str = ""


@dataclass(frozen=True)
class ReleaseManifest:
    """Validated manifest metadata and immutable release file list."""

    release_id: str
    prefix: str
    files: tuple[ReleaseFile, ...]


@dataclass(frozen=True)
class MultipartState:
    """Persist enough immutable R2 multipart state to resume after interruption."""

    sha256: str
    size: int
    part_size: int
    metadata_sha256: str
    upload_id: str
    parts: tuple[tuple[int, str], ...]


class UploadFailure(RuntimeError):
    """A bounded upload operation could not be completed."""


class MultipartUploadMissing(UploadFailure):
    """The R2 multipart upload expired or no longer exists."""


def _valid_sha256(value: object) -> bool:
    """Return whether a value is one lowercase hexadecimal SHA-256 digest."""
    return isinstance(value, str) and bool(re.fullmatch(r"[a-f0-9]{64}", value))


def _valid_upload_id(value: object) -> bool:
    """Return whether an opaque R2 upload identifier is header-safe."""
    return (
        isinstance(value, str)
        and 0 < len(value) <= 512
        and all(" " <= character <= "~" for character in value)
    )


def _valid_etag(value: object) -> bool:
    """Return whether an opaque R2 part ETag is safe to persist and resend."""
    return (
        isinstance(value, str)
        and 0 < len(value) <= 512
        and all(" " <= character <= "~" for character in value)
    )


def _metadata_sha256(item: ReleaseFile) -> str:
    """Hash every target HTTP metadata field that is fixed at multipart init."""
    serialized = json.dumps(
        [
            item.content_type,
            item.cache_control,
            item.content_encoding,
            item.content_disposition,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _multipart_state_from_record(
    payload: dict[str, Any],
    line_number: int,
    state_path: pathlib.Path,
) -> MultipartState:
    """Parse one fail-closed multipart checkpoint from an append-only state file."""
    size = payload.get("size")
    part_size = payload.get("part_size")
    upload_id = payload.get("upload_id")
    metadata_sha256 = payload.get("metadata_sha256", "")
    raw_parts = payload.get("parts")
    invalid = (
        isinstance(size, bool)
        or not isinstance(size, int)
        or size < 1
        or isinstance(part_size, bool)
        or not isinstance(part_size, int)
        or part_size < 1
        or not _valid_upload_id(upload_id)
        or (metadata_sha256 != "" and not _valid_sha256(metadata_sha256))
        or not isinstance(raw_parts, list)
    )
    if invalid:
        raise UploadFailure(f"Invalid upload state line {line_number}: {state_path}")
    expected_parts = (size + part_size - 1) // part_size
    if expected_parts < 1 or expected_parts > 10000 or len(raw_parts) > expected_parts:
        raise UploadFailure(f"Invalid upload state line {line_number}: {state_path}")
    parts: list[tuple[int, str]] = []
    for expected_number, part in enumerate(raw_parts, start=1):
        if (
            not isinstance(part, dict)
            or part.get("partNumber") != expected_number
            or not _valid_etag(part.get("etag"))
        ):
            raise UploadFailure(f"Invalid upload state line {line_number}: {state_path}")
        parts.append((expected_number, part["etag"]))
    return MultipartState(
        sha256=str(payload["sha256"]).lower(),
        size=size,
        part_size=part_size,
        metadata_sha256=metadata_sha256,
        upload_id=upload_id,
        parts=tuple(parts),
    )


class PublicReleaseUploader:
    """Upload and inventory one immutable release through a temporary Worker."""

    def __init__(
        self,
        endpoint: str,
        token: str,
        proxy: str | None,
        state_path: pathlib.Path,
        release_prefix: str,
    ) -> None:
        """Initialize authenticated HTTP sessions and resumable local state."""
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.state_path = state_path
        self.release_prefix = release_prefix
        self.state_lock = threading.Lock()
        self.thread_local = threading.local()
        self.completed, self.multipart = self._load_state()

    def _session(self) -> requests.Session:
        """Return one requests session per upload thread."""
        session = getattr(self.thread_local, "session", None)
        if session is None:
            session = requests.Session()
            session.trust_env = False
            self.thread_local.session = session
        return session

    def _load_state(self) -> tuple[dict[str, str], dict[str, MultipartState]]:
        """Load append-only completed and in-flight multipart transfer state."""
        if not self.state_path.exists():
            return {}, {}
        completed: dict[str, str] = {}
        multipart: dict[str, MultipartState] = {}
        with self.state_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as error:
                    raise UploadFailure(
                        f"Invalid upload state line {line_number}: {self.state_path}"
                    ) from error
                if not isinstance(payload, dict) or not isinstance(payload.get("path"), str):
                    raise UploadFailure(f"Invalid upload state line {line_number}: {self.state_path}")
                path = payload["path"]
                event = payload.get("event", "complete")
                sha256 = str(payload.get("sha256", "")).lower()
                if payload.get("prefix") != self.release_prefix or not _valid_sha256(sha256):
                    raise UploadFailure(f"Invalid upload state line {line_number}: {self.state_path}")
                if event == "complete":
                    completed[path] = sha256
                    multipart.pop(path, None)
                elif event == "multipart":
                    multipart[path] = _multipart_state_from_record(payload, line_number, self.state_path)
                    completed.pop(path, None)
                elif event == "abort":
                    multipart.pop(path, None)
                    completed.pop(path, None)
                else:
                    raise UploadFailure(f"Invalid upload state line {line_number}: {self.state_path}")
        return completed, multipart

    def _append_state(self, payload: dict[str, Any]) -> None:
        """Durably append one small state transition while uploads run concurrently."""
        record = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self.state_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{record}\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _save_completed(self, item: ReleaseFile) -> None:
        """Append one successfully persisted object to the resume state."""
        with self.state_lock:
            self.completed[item.path] = item.sha256
            self.multipart.pop(item.path, None)
            self._append_state({
                "event": "complete",
                "path": item.path,
                "prefix": self.release_prefix,
                "sha256": item.sha256,
            })

    def _save_multipart(
        self,
        item: ReleaseFile,
        upload_id: str,
        parts: dict[int, str],
    ) -> None:
        """Checkpoint an R2 upload ID and every acknowledged contiguous part."""
        state = MultipartState(
            sha256=item.sha256,
            size=item.size,
            part_size=PART_SIZE,
            metadata_sha256=_metadata_sha256(item),
            upload_id=upload_id,
            parts=tuple(sorted(parts.items())),
        )
        payload = {
            "event": "multipart",
            "path": item.path,
            "prefix": self.release_prefix,
            "sha256": item.sha256,
            "size": item.size,
            "part_size": PART_SIZE,
            "metadata_sha256": state.metadata_sha256,
            "upload_id": upload_id,
            "parts": [
                {"partNumber": part_number, "etag": etag}
                for part_number, etag in state.parts
            ],
        }
        with self.state_lock:
            self.multipart[item.path] = state
            self._append_state(payload)

    def _clear_multipart(self, item: ReleaseFile) -> None:
        """Record that an explicitly aborted multipart upload is no longer resumable."""
        with self.state_lock:
            self.multipart.pop(item.path, None)
            self._append_state({
                "event": "abort",
                "path": item.path,
                "prefix": self.release_prefix,
                "sha256": item.sha256,
            })

    @staticmethod
    def _encoded_key(path: str) -> str:
        """Encode one UTF-8 object path for a header-safe transfer."""
        return base64.urlsafe_b64encode(path.encode("utf-8")).decode("ascii").rstrip("=")

    def _headers(self, item: ReleaseFile) -> dict[str, str]:
        """Build authenticated object and metadata headers."""
        headers = {
            "X-KWBL-Upload-Key": self.token,
            "X-KWBL-Object-Key": self._encoded_key(item.path),
            "X-KWBL-SHA256": item.sha256,
            "X-KWBL-Content-Type": item.content_type,
            "X-KWBL-Cache-Control": item.cache_control,
        }
        if item.content_encoding:
            headers["X-KWBL-Content-Encoding"] = item.content_encoding
        if item.content_disposition:
            headers["X-KWBL-Content-Disposition"] = item.content_disposition
        return headers

    def health(self) -> dict[str, Any]:
        """Confirm the temporary uploader is reachable with the one-time key."""
        response = self._request_with_retry(
            "GET",
            f"{self.endpoint}/_kwbl-upload/v1/health",
            headers={"X-KWBL-Upload-Key": self.token},
        )
        if response.status_code != 200:
            raise UploadFailure(f"Uploader health check failed with HTTP {response.status_code}")
        return response.json()

    def inventory_page(self, cursor: str | None = None) -> dict[str, Any]:
        """Fetch one authenticated page from the uploader's fixed-prefix inventory."""
        params = {"cursor": cursor} if cursor is not None else None
        response = self._request_with_retry(
            "GET",
            f"{self.endpoint}/_kwbl-upload/v1/inventory",
            headers={"X-KWBL-Upload-Key": self.token},
            params=params,
        )
        try:
            payload = response.json()
        except ValueError as error:
            raise UploadFailure("Uploader inventory returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise UploadFailure("Uploader inventory page must be a JSON object")
        return payload

    def fetch_complete_inventory(self, expected_prefix: str) -> dict[str, Any]:
        """Traverse every inventory cursor and return a complete verifier snapshot."""
        cursor: str | None = None
        seen_cursors: set[str] = set()
        objects: list[dict[str, Any]] = []
        for _page_number in range(1, MAX_INVENTORY_PAGES + 1):
            page = self.inventory_page(cursor)
            if page.get("ok") is not True:
                raise UploadFailure("Uploader inventory page did not report success")
            if page.get("prefix") != expected_prefix:
                raise UploadFailure("Uploader inventory prefix changed during pagination")
            page_objects = page.get("objects")
            if not isinstance(page_objects, list):
                raise UploadFailure("Uploader inventory page has no objects array")
            objects.extend(page_objects)
            truncated = page.get("truncated")
            if not isinstance(truncated, bool):
                raise UploadFailure("Uploader inventory page has no boolean truncated marker")
            next_cursor = page.get("cursor")
            if not truncated:
                if next_cursor not in {None, ""}:
                    raise UploadFailure("Complete inventory page unexpectedly returned a cursor")
                break
            if not isinstance(next_cursor, str) or not next_cursor:
                raise UploadFailure("Truncated inventory page did not return a cursor")
            if next_cursor in seen_cursors:
                raise UploadFailure("Uploader inventory cursor repeated before completion")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        else:
            raise UploadFailure("Uploader inventory exceeded the page safety limit")

        total_bytes = 0
        for index, item in enumerate(objects):
            if not isinstance(item, dict):
                raise UploadFailure(f"Uploader inventory object {index} is not an object")
            size = item.get("size")
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise UploadFailure(f"Uploader inventory object {index} has an invalid size")
            total_bytes += size
        return {
            "schema_version": 1,
            "complete": True,
            "prefix": expected_prefix,
            "count": len(objects),
            "bytes": total_bytes,
            "objects": objects,
        }

    def upload(self, root: pathlib.Path, item: ReleaseFile) -> str:
        """Verify and upload one release object or honor a valid local resume record."""
        source = safe_source_path(root, item)
        verify_source_hash(source, item)
        if self.completed.get(item.path) == item.sha256:
            return "resume-skip"
        if item.size <= DIRECT_LIMIT:
            result = self._put_direct(source, item)
        else:
            result = self._put_multipart(source, item)
        self._save_completed(item)
        return result

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Perform one bounded HTTP operation with fresh streaming bodies on retries."""
        data_factory = kwargs.pop("data_factory", None)
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if data_factory is None:
                    response = self._session().request(
                        method,
                        url,
                        proxies=self.proxies,
                        timeout=(20, 180),
                        **kwargs,
                    )
                else:
                    with data_factory() as payload:
                        response = self._session().request(
                            method,
                            url,
                            proxies=self.proxies,
                            timeout=(20, 180),
                            data=payload,
                            **kwargs,
                        )
                if response.status_code < 400:
                    return response
                if response.status_code == 409:
                    try:
                        error_payload = response.json()
                    except ValueError:
                        error_payload = None
                    if (
                        isinstance(error_payload, dict)
                        and error_payload.get("code") == "multipart_upload_missing"
                    ):
                        raise MultipartUploadMissing("R2 multipart upload no longer exists")
                if response.status_code not in RETRYABLE_STATUS:
                    raise UploadFailure(f"Upload endpoint returned HTTP {response.status_code}")
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else min(12.0, 0.8 * 2**attempt)
                time.sleep(delay + random.random() * 0.25)
            except (requests.RequestException, UploadFailure) as error:
                last_error = error
                if isinstance(error, UploadFailure):
                    raise
                if attempt < MAX_ATTEMPTS:
                    time.sleep(min(12.0, 0.8 * 2**attempt) + random.random() * 0.25)
        raise UploadFailure(f"Upload request failed after {MAX_ATTEMPTS} attempts") from last_error

    def _put_direct(self, source: pathlib.Path, item: ReleaseFile) -> str:
        """Stream one bounded object through the direct upload route."""
        headers = self._headers(item)
        headers["Content-Length"] = str(item.size)
        headers["Content-Type"] = "application/octet-stream"
        response = self._request_with_retry(
            "PUT",
            f"{self.endpoint}/_kwbl-upload/v1/object",
            headers=headers,
            data_factory=lambda: source.open("rb"),
        )
        result = response.json()
        return "remote-skip" if result.get("skipped") else "uploaded"

    def _put_multipart(self, source: pathlib.Path, item: ReleaseFile) -> str:
        """Restart once if R2 has expired a previously checkpointed upload ID."""
        for restart_attempt in range(2):
            try:
                return self._put_multipart_once(source, item)
            except MultipartUploadMissing:
                self._clear_multipart(item)
                if restart_attempt == 1:
                    raise
        raise AssertionError("unreachable multipart restart state")

    def _put_multipart_once(self, source: pathlib.Path, item: ReleaseFile) -> str:
        """Upload or resume a large object in fixed-size R2 multipart chunks."""
        headers = self._headers(item)
        headers["X-KWBL-Object-Size"] = str(item.size)
        headers["X-KWBL-Part-Size"] = str(PART_SIZE)
        expected_parts = (item.size + PART_SIZE - 1) // PART_SIZE
        if expected_parts < 2 or expected_parts > 10000:
            raise UploadFailure(f"Invalid multipart part count for {item.path}: {expected_parts}")
        state = self.multipart.get(item.path)
        if state is not None and not self._state_matches_item(state, item):
            self._abort_multipart(item, state.upload_id)
            state = None
        if state is None:
            initialized = self._request_with_retry(
                "POST",
                f"{self.endpoint}/_kwbl-upload/v1/multipart/init",
                headers=headers,
            ).json()
            if initialized.get("skipped") is True:
                return "remote-skip"
            upload_id = initialized.get("uploadId")
            if not _valid_upload_id(upload_id):
                raise UploadFailure("Multipart upload did not return a valid upload ID")
            parts: dict[int, str] = {}
            self._save_multipart(item, upload_id, parts)
        else:
            upload_id = state.upload_id
            parts = dict(state.parts)

        for part_number in range(1, expected_parts + 1):
            if part_number in parts:
                continue
            offset = (part_number - 1) * PART_SIZE
            expected_length = min(PART_SIZE, item.size - offset)
            with source.open("rb") as stream:
                stream.seek(offset)
                payload = stream.read(expected_length)
            if len(payload) != expected_length:
                raise UploadFailure(f"Could not read multipart source slice for {item.path}")
            part_headers = dict(headers)
            part_headers["X-KWBL-Upload-Id"] = upload_id
            part_headers["X-KWBL-Part-Number"] = str(part_number)
            part_headers["Content-Length"] = str(expected_length)
            part_headers["Content-Type"] = "application/octet-stream"
            result = self._request_with_retry(
                "PUT",
                f"{self.endpoint}/_kwbl-upload/v1/multipart/part",
                headers=part_headers,
                data=payload,
            ).json()
            returned_number = result.get("partNumber") if isinstance(result, dict) else None
            etag = result.get("etag") if isinstance(result, dict) else None
            if returned_number != part_number or not _valid_etag(etag):
                raise UploadFailure("Multipart part endpoint returned an invalid descriptor")
            parts[part_number] = etag
            self._save_multipart(item, upload_id, parts)

        descriptors = [
            {"partNumber": part_number, "etag": parts[part_number]}
            for part_number in range(1, expected_parts + 1)
        ]
        complete_headers = dict(headers)
        complete_headers["X-KWBL-Upload-Id"] = upload_id
        result = self._request_with_retry(
            "POST",
            f"{self.endpoint}/_kwbl-upload/v1/multipart/complete",
            headers=complete_headers,
            json={"parts": descriptors},
        ).json()
        if (
            not isinstance(result, dict)
            or result.get("ok") is not True
            or result.get("size") != item.size
            or result.get("sha256") != item.sha256
        ):
            raise UploadFailure("Multipart completion did not verify the final R2 object")
        return "uploaded"

    @staticmethod
    def _state_matches_item(state: MultipartState, item: ReleaseFile) -> bool:
        """Return whether a checkpoint describes the exact current immutable upload."""
        return (
            state.sha256 == item.sha256
            and state.size == item.size
            and state.part_size == PART_SIZE
            and state.metadata_sha256 == _metadata_sha256(item)
        )

    def _abort_multipart(self, item: ReleaseFile, upload_id: str) -> None:
        """Abort only an explicitly stale checkpoint before starting a replacement."""
        headers = self._headers(item)
        headers["X-KWBL-Upload-Id"] = upload_id
        self._request_with_retry(
            "POST",
            f"{self.endpoint}/_kwbl-upload/v1/multipart/abort",
            headers=headers,
        )
        self._clear_multipart(item)


def safe_source_path(root: pathlib.Path, item: ReleaseFile) -> pathlib.Path:
    """Resolve one manifest file while rejecting every symlink below the release root."""
    relative = pathlib.PurePosixPath(item.path)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise UploadFailure(f"Unsafe manifest path: {item.path}")
    if relative.parts[0] not in ALLOWED_ROOTS and item.path != "public_manifest.json":
        raise UploadFailure(f"Manifest path is outside the public release surface: {item.path}")
    if root.is_symlink() or not root.is_dir():
        raise UploadFailure(f"Release root is missing or unsafe: {root}")
    source = root
    for index, part in enumerate(relative.parts):
        source = source / part
        try:
            mode = source.lstat().st_mode
        except FileNotFoundError as error:
            raise UploadFailure(f"Missing release file: {item.path}") from error
        if stat.S_ISLNK(mode):
            raise UploadFailure(f"Symlink is forbidden in release file path: {item.path}")
        if index < len(relative.parts) - 1 and not stat.S_ISDIR(mode):
            raise UploadFailure(f"Non-directory component in release file path: {item.path}")
    if not stat.S_ISREG(source.lstat().st_mode):
        raise UploadFailure(f"Release path is not a regular file: {item.path}")
    resolved_root = root.resolve(strict=True)
    try:
        source.resolve(strict=True).relative_to(resolved_root)
    except ValueError as error:
        raise UploadFailure(f"Release file escapes its root: {item.path}") from error
    if source.stat().st_size != item.size:
        raise UploadFailure(f"Size changed after manifest creation: {item.path}")
    return source


def verify_source_hash(source: pathlib.Path, item: ReleaseFile) -> None:
    """Recompute content identity before both upload and local resume skips."""
    before = source.stat()
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    after = source.stat()
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise UploadFailure(f"Release file changed while hashing: {item.path}")
    if digest.hexdigest() != item.sha256:
        raise UploadFailure(f"SHA-256 mismatch for release file: {item.path}")


def normalize_file(raw: dict[str, Any], expected_prefix: str) -> ReleaseFile:
    """Validate one file record, including its exact immutable R2 destination."""
    path = str(raw.get("path", ""))
    size = int(raw.get("size", -1))
    sha256 = str(raw.get("sha256", "")).lower()
    if size < 0 or len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
        raise UploadFailure(f"Invalid manifest entry: {path or '<missing path>'}")
    if raw.get("r2_key") != f"{expected_prefix}{path}":
        raise UploadFailure(f"Manifest R2 key does not match release prefix: {path}")
    content_type = str(raw.get("content_type") or mimetypes.guess_type(path)[0] or "application/octet-stream")
    cache_control = str(raw.get("cache_control") or default_cache_control(path))
    content_encoding = str(raw.get("content_encoding") or "")
    content_disposition = str(raw.get("content_disposition") or "")
    return ReleaseFile(
        path,
        size,
        sha256,
        content_type,
        cache_control,
        content_encoding,
        content_disposition,
    )


def default_cache_control(path: str) -> str:
    """Return a conservative cache policy when a manifest entry omits one."""
    if path == "data/catalog.json" or path.endswith("_index.json") or path.endswith("public_manifest.json"):
        return "public, max-age=300, must-revalidate"
    if path.startswith("site/"):
        return "public, max-age=300, must-revalidate"
    if path.endswith(".html"):
        return "no-store"
    return "public, max-age=31536000, immutable"


def load_manifest(path: pathlib.Path, root: pathlib.Path) -> ReleaseManifest:
    """Load and fully validate an immutable public-release manifest."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    release_id = payload.get("release_id") if isinstance(payload, dict) else None
    if not isinstance(release_id, str) or not RELEASE_ID_PATTERN.fullmatch(release_id):
        raise UploadFailure("Manifest has an invalid release_id")
    expected_prefix = f"releases/{release_id}/"
    raw_files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(raw_files, list):
        raise UploadFailure("Manifest must contain a files array")
    raw_files = list(raw_files)
    self_record = payload.get("self") if isinstance(payload, dict) else None
    if isinstance(self_record, dict) and isinstance(self_record.get("path"), str):
        self_path = pathlib.PurePosixPath(self_record["path"])
        if self_path.is_absolute() or ".." in self_path.parts:
            raise UploadFailure("Manifest self path is unsafe")
        expected_manifest = root.joinpath(*self_path.parts).resolve()
        if expected_manifest != path.resolve() or path.is_symlink():
            raise UploadFailure("Manifest self path does not identify the loaded manifest")
        if self_record.get("r2_key") != f"{expected_prefix}{self_path.as_posix()}":
            raise UploadFailure("Manifest self R2 key does not match release prefix")
        payload_bytes = path.read_bytes()
        raw_files.append(
            {
                "path": self_path.as_posix(),
                "size": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
                "content_type": "application/json; charset=utf-8",
                "cache_control": "public, max-age=300, must-revalidate",
                "r2_key": f"{expected_prefix}{self_path.as_posix()}",
            }
        )
    files = [normalize_file(item, expected_prefix) for item in raw_files if isinstance(item, dict)]
    if len(files) != len(raw_files):
        raise UploadFailure("Manifest contains a non-object file entry")
    paths = [item.path for item in files]
    if len(paths) != len(set(paths)):
        raise UploadFailure("Manifest contains duplicate paths")
    ordered = sorted(
        files,
        key=lambda item: (item.path.startswith("data/"), item.path.startswith("site/"), item.path),
    )
    return ReleaseManifest(release_id, expected_prefix, tuple(ordered))


def validate_uploader_prefix(health: dict[str, Any], manifest: ReleaseManifest) -> None:
    """Prevent a valid release from being written beneath the wrong immutable prefix."""
    if health.get("prefix") != manifest.prefix:
        raise UploadFailure(
            f"Uploader prefix mismatch: expected {manifest.prefix!r}, got {health.get('prefix')!r}"
        )


def validate_external_file_path(path: pathlib.Path, root: pathlib.Path, label: str) -> pathlib.Path:
    """Require an operational state file to live outside the immutable release root."""
    target = path.absolute()
    if target.is_symlink():
        raise UploadFailure(f"{label} cannot be a symlink: {target}")
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        return target
    raise UploadFailure(f"{label} must be stored outside the immutable release root")


def write_atomic_inventory(path: pathlib.Path, payload: dict[str, Any]) -> None:
    """Durably replace an inventory snapshot without exposing a partial JSON file."""
    parent = path.parent.resolve(strict=True)
    temporary_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = pathlib.Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o640)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def finalize_verified_upload(
    uploader: PublicReleaseUploader,
    manifest: ReleaseManifest,
    manifest_path: pathlib.Path,
    inventory_path: pathlib.Path,
    token_path: pathlib.Path,
    delete_token_on_success: bool,
) -> dict[str, Any]:
    """Snapshot and verify all R2 objects before optionally deleting the one-time key."""
    inventory = uploader.fetch_complete_inventory(manifest.prefix)
    write_atomic_inventory(inventory_path, inventory)
    try:
        result = verify_release(manifest_path, inventory_path)
    except VerificationError as error:
        raise UploadFailure(f"R2 release inventory verification failed: {error}") from error
    if delete_token_on_success:
        token_path.unlink(missing_ok=True)
    return result


def parse_args() -> argparse.Namespace:
    """Parse upload, resume, and post-upload verification arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--token-file", type=pathlib.Path, required=True)
    parser.add_argument("--state-file", type=pathlib.Path)
    parser.add_argument("--inventory-file", type=pathlib.Path)
    parser.add_argument("--proxy")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--delete-token-on-success", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Upload one release, verify its complete R2 inventory, then retire its key."""
    args = parse_args()
    supplied_root = args.root.absolute()
    if supplied_root.is_symlink():
        raise UploadFailure(f"Release root cannot be a symlink: {supplied_root}")
    root = supplied_root.resolve(strict=True)
    manifest_path = (args.manifest or root / "data/public_manifest.json").resolve()
    token_path = args.token_file.resolve()
    requested_state_path = (
        args.state_file.absolute()
        if args.state_file
        else root.parent / f".{root.name}.upload-state.jsonl"
    )
    requested_inventory_path = (
        args.inventory_file.absolute()
        if args.inventory_file
        else root.parent / f".{root.name}.r2-inventory.json"
    )
    state_path = validate_external_file_path(requested_state_path, root, "Upload state")
    inventory_path = validate_external_file_path(requested_inventory_path, root, "R2 inventory snapshot")
    if inventory_path.resolve(strict=False) == token_path:
        raise UploadFailure("R2 inventory snapshot cannot replace the upload token file")
    if inventory_path.resolve(strict=False) == state_path.resolve(strict=False):
        raise UploadFailure("R2 inventory snapshot and upload state must use different paths")
    token = token_path.read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise UploadFailure("Upload token file is empty or invalid")
    manifest = load_manifest(manifest_path, root)
    files = manifest.files
    total_bytes = sum(item.size for item in files)
    uploader = PublicReleaseUploader(
        endpoint=args.endpoint,
        token=token,
        proxy=args.proxy,
        state_path=state_path,
        release_prefix=manifest.prefix,
    )
    health = uploader.health()
    validate_uploader_prefix(health, manifest)
    print(
        f"Uploader ready for prefix {manifest.prefix}; {len(files):,} files, {total_bytes:,} bytes",
        flush=True,
    )

    started = time.monotonic()
    finished_files = 0
    finished_bytes = 0
    result_counts: dict[str, int] = {}
    lock = threading.Lock()

    def perform(item: ReleaseFile) -> tuple[ReleaseFile, str]:
        """Upload one item and preserve it for progress accounting."""
        return item, uploader.upload(root, item)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.workers, 32))) as executor:
        futures = {executor.submit(perform, item): item for item in files}
        for future in concurrent.futures.as_completed(futures):
            item, result = future.result()
            with lock:
                finished_files += 1
                finished_bytes += item.size
                result_counts[result] = result_counts.get(result, 0) + 1
                if finished_files == 1 or finished_files % 250 == 0 or finished_files == len(files):
                    elapsed = max(time.monotonic() - started, 0.001)
                    rate = finished_bytes / elapsed
                    remaining = (total_bytes - finished_bytes) / rate if rate else 0
                    print(
                        f"progress {finished_files:,}/{len(files):,} files; "
                        f"{finished_bytes:,}/{total_bytes:,} bytes; ETA {remaining / 60:.1f} min",
                        flush=True,
                    )

    print(f"Upload transfer complete: {json.dumps(result_counts, sort_keys=True)}", flush=True)
    verified = finalize_verified_upload(
        uploader,
        manifest,
        manifest_path,
        inventory_path,
        token_path,
        args.delete_token_on_success,
    )
    print(
        f"R2 inventory verified: {verified['files']:,} files, {verified['bytes']:,} bytes; "
        f"snapshot={inventory_path}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
