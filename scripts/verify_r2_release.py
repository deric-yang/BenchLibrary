#!/usr/bin/env python3
"""Verify a complete R2 release inventory against ``public_manifest.json``.

The inventory is an offline JSON snapshot produced by the authenticated listing
step. It must have this fail-closed shape::

    {
      "schema_version": 1,
      "complete": true,
      "prefix": "releases/<release-id>/",
      "objects": [
        {
          "key": "releases/<release-id>/data/catalog.json",
          "size": 123,
          "custom_metadata": {"sha256": "..."}
        }
      ]
    }

This script never accepts, reads, or transmits Cloudflare credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


RELEASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
MAX_REPORTED_KEYS = 20


class VerificationError(RuntimeError):
    """Report an invalid input or a complete-inventory mismatch."""


@dataclass(frozen=True)
class ObjectIdentity:
    """Describe the integrity fields required for one immutable R2 object."""

    key: str
    size: int
    sha256: str
    content_type: str
    cache_control: str
    content_encoding: str
    content_disposition: str


@dataclass(frozen=True)
class ExpectedRelease:
    """Hold the expected release prefix and object identities."""

    release_id: str
    prefix: str
    objects: dict[str, ObjectIdentity]


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    """Read one UTF-8 JSON object with a useful validation error."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"Cannot read valid {label} JSON from {path}: {error}") from error
    if not isinstance(payload, dict):
        raise VerificationError(f"{label} must be a JSON object")
    return payload


def _nonnegative_integer(value: Any, label: str) -> int:
    """Return a non-negative integer while rejecting booleans and coercion."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VerificationError(f"{label} must be a non-negative integer")
    return value


def _sha256(value: Any, label: str) -> str:
    """Return a canonical lowercase SHA-256 digest."""
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value.lower()) is None:
        raise VerificationError(f"{label} must be a 64-character SHA-256 digest")
    return value.lower()


def _safe_relative_path(value: Any, label: str) -> str:
    """Validate one canonical release-relative object path."""
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise VerificationError(f"{label} is not a safe relative path")
    pure_path = PurePosixPath(value)
    if pure_path.is_absolute() or pure_path.as_posix() != value:
        raise VerificationError(f"{label} is not a canonical relative path")
    if any(part in {"", ".", ".."} for part in pure_path.parts):
        raise VerificationError(f"{label} is not a safe relative path")
    if pure_path.parts[0] not in {"site", "data", "assets"}:
        raise VerificationError(f"{label} is outside the public release surface")
    return value


def _default_cache_control(path: str) -> str:
    """Mirror the upload client's conservative metadata defaults."""
    if path == "data/catalog.json" or path.endswith("_index.json") or path.endswith(
        "public_manifest.json"
    ):
        return "public, max-age=300, must-revalidate"
    if path.startswith("site/"):
        return "public, max-age=300, must-revalidate"
    if path.endswith(".html"):
        return "no-store"
    return "public, max-age=31536000, immutable"


def _manifest_http_metadata(raw: dict[str, Any], path: str) -> tuple[str, str, str, str]:
    """Resolve the exact HTTP metadata that the upload client will store."""
    content_type = str(
        raw.get("content_type")
        or mimetypes.guess_type(path)[0]
        or "application/octet-stream"
    )
    cache_control = str(raw.get("cache_control") or _default_cache_control(path))
    return (
        content_type,
        cache_control,
        str(raw.get("content_encoding") or ""),
        str(raw.get("content_disposition") or ""),
    )


def _inventory_http_metadata(raw: dict[str, Any], key: str) -> tuple[str, str, str, str]:
    """Load a complete normalized R2 HTTP metadata record."""
    metadata = raw.get("http_metadata")
    if metadata is None:
        metadata = raw.get("httpMetadata")
    if not isinstance(metadata, dict):
        raise VerificationError(f"R2 object is missing HTTP metadata: {key}")
    fields = (
        "content_type",
        "cache_control",
        "content_encoding",
        "content_disposition",
    )
    values = tuple(metadata.get(field, "") for field in fields)
    if any(not isinstance(value, str) for value in values):
        raise VerificationError(f"R2 object has invalid HTTP metadata: {key}")
    return values


def _manifest_object(raw: Any, prefix: str, index: int) -> ObjectIdentity:
    """Validate one regular file entry from the public release manifest."""
    if not isinstance(raw, dict):
        raise VerificationError(f"Manifest files[{index}] must be an object")
    path = _safe_relative_path(raw.get("path"), f"Manifest files[{index}].path")
    expected_key = f"{prefix}{path}"
    if raw.get("r2_key") != expected_key:
        raise VerificationError(f"Manifest R2 key does not match release prefix: {path}")
    size = _nonnegative_integer(raw.get("size"), f"Manifest size for {path}")
    digest = _sha256(raw.get("sha256"), f"Manifest SHA-256 for {path}")
    return ObjectIdentity(expected_key, size, digest, *_manifest_http_metadata(raw, path))


def load_expected_release(path: Path) -> ExpectedRelease:
    """Load all expected objects, including the manifest's self record."""
    payload = _load_json_object(path, "public manifest")
    release_id = payload.get("release_id")
    if not isinstance(release_id, str) or RELEASE_ID_PATTERN.fullmatch(release_id) is None:
        raise VerificationError("Manifest has an invalid release_id")
    prefix = f"releases/{release_id}/"
    raw_files = payload.get("files")
    if not isinstance(raw_files, list):
        raise VerificationError("Manifest must contain a files array")

    objects: dict[str, ObjectIdentity] = {}
    regular_bytes = 0
    for index, raw in enumerate(raw_files):
        identity = _manifest_object(raw, prefix, index)
        if identity.key in objects:
            raise VerificationError(f"Manifest contains duplicate R2 key: {identity.key}")
        objects[identity.key] = identity
        regular_bytes += identity.size

    totals = payload.get("totals")
    if not isinstance(totals, dict):
        raise VerificationError("Manifest must contain totals")
    declared_files = _nonnegative_integer(totals.get("files"), "Manifest totals.files")
    declared_bytes = _nonnegative_integer(totals.get("logical_bytes"), "Manifest totals.logical_bytes")
    if declared_files != len(raw_files):
        raise VerificationError("Manifest totals.files does not match files array")
    if declared_bytes != regular_bytes:
        raise VerificationError("Manifest totals.logical_bytes does not match files array")

    self_record = payload.get("self")
    if not isinstance(self_record, dict):
        raise VerificationError("Manifest must contain a self object")
    self_path = _safe_relative_path(self_record.get("path"), "Manifest self.path")
    self_key = f"{prefix}{self_path}"
    if self_record.get("r2_key") != self_key:
        raise VerificationError("Manifest self R2 key does not match release prefix")
    if self_key in objects:
        raise VerificationError("Manifest self object is duplicated in files array")
    manifest_bytes = path.read_bytes()
    objects[self_key] = ObjectIdentity(
        self_key,
        len(manifest_bytes),
        hashlib.sha256(manifest_bytes).hexdigest(),
        "application/json; charset=utf-8",
        "public, max-age=300, must-revalidate",
        "",
        "",
    )
    return ExpectedRelease(release_id, prefix, objects)


def _inventory_object(raw: Any, prefix: str, index: int) -> ObjectIdentity:
    """Validate one R2 listing object and its stored SHA-256 custom metadata."""
    if not isinstance(raw, dict):
        raise VerificationError(f"Inventory objects[{index}] must be an object")
    key = raw.get("key")
    if not isinstance(key, str) or not key.startswith(prefix):
        raise VerificationError(f"Inventory object is outside expected prefix at index {index}")
    size = _nonnegative_integer(raw.get("size"), f"Inventory size for {key}")
    custom_metadata = raw.get("custom_metadata")
    if custom_metadata is None:
        custom_metadata = raw.get("customMetadata")
    if not isinstance(custom_metadata, dict):
        raise VerificationError(f"R2 object is missing custom metadata: {key}")
    digest = _sha256(custom_metadata.get("sha256"), f"R2 sha256 metadata for {key}")
    return ObjectIdentity(key, size, digest, *_inventory_http_metadata(raw, key))


def load_complete_inventory(path: Path, expected_prefix: str) -> dict[str, ObjectIdentity]:
    """Load a complete, prefix-scoped R2 inventory snapshot."""
    payload = _load_json_object(path, "R2 inventory")
    if payload.get("schema_version") != 1:
        raise VerificationError("R2 inventory schema_version must be 1")
    if payload.get("complete") is not True:
        raise VerificationError("R2 inventory is not marked complete")
    if payload.get("prefix") != expected_prefix:
        raise VerificationError("R2 inventory prefix does not match manifest release")
    raw_objects = payload.get("objects")
    if not isinstance(raw_objects, list):
        raise VerificationError("R2 inventory must contain an objects array")

    objects: dict[str, ObjectIdentity] = {}
    for index, raw in enumerate(raw_objects):
        identity = _inventory_object(raw, expected_prefix, index)
        if identity.key in objects:
            raise VerificationError(f"R2 inventory contains duplicate key: {identity.key}")
        objects[identity.key] = identity

    if "count" in payload:
        declared_count = _nonnegative_integer(payload["count"], "R2 inventory count")
        if declared_count != len(objects):
            raise VerificationError("R2 inventory count does not match objects array")
    if "bytes" in payload:
        declared_bytes = _nonnegative_integer(payload["bytes"], "R2 inventory bytes")
        if declared_bytes != sum(item.size for item in objects.values()):
            raise VerificationError("R2 inventory bytes does not match objects array")
    return objects


def _sample_keys(keys: set[str]) -> str:
    """Render a deterministic bounded sample of mismatching keys."""
    ordered = sorted(keys)
    suffix = "" if len(ordered) <= MAX_REPORTED_KEYS else f", ... (+{len(ordered) - MAX_REPORTED_KEYS})"
    return ", ".join(ordered[:MAX_REPORTED_KEYS]) + suffix


def verify_release(manifest_path: Path, inventory_path: Path) -> dict[str, Any]:
    """Require exact count, bytes, keys, sizes, and SHA-256 metadata."""
    expected = load_expected_release(manifest_path)
    actual = load_complete_inventory(inventory_path, expected.prefix)
    expected_keys = set(expected.objects)
    actual_keys = set(actual)
    missing = expected_keys - actual_keys
    unexpected = actual_keys - expected_keys
    if missing:
        raise VerificationError(f"R2 inventory is missing {len(missing)} keys: {_sample_keys(missing)}")
    if unexpected:
        raise VerificationError(f"R2 inventory has {len(unexpected)} unexpected keys: {_sample_keys(unexpected)}")

    size_mismatches = {
        key
        for key in expected_keys
        if expected.objects[key].size != actual[key].size
    }
    if size_mismatches:
        raise VerificationError(
            f"R2 inventory has {len(size_mismatches)} size mismatches: {_sample_keys(size_mismatches)}"
        )
    hash_mismatches = {
        key
        for key in expected_keys
        if expected.objects[key].sha256 != actual[key].sha256
    }
    if hash_mismatches:
        raise VerificationError(
            f"R2 inventory has {len(hash_mismatches)} SHA-256 metadata mismatches: "
            f"{_sample_keys(hash_mismatches)}"
        )
    metadata_mismatches = {
        key
        for key in expected_keys
        if (
            expected.objects[key].content_type,
            expected.objects[key].cache_control,
            expected.objects[key].content_encoding,
            expected.objects[key].content_disposition,
        )
        != (
            actual[key].content_type,
            actual[key].cache_control,
            actual[key].content_encoding,
            actual[key].content_disposition,
        )
    }
    if metadata_mismatches:
        raise VerificationError(
            f"R2 inventory has {len(metadata_mismatches)} HTTP metadata mismatches: "
            f"{_sample_keys(metadata_mismatches)}"
        )

    expected_bytes = sum(item.size for item in expected.objects.values())
    actual_bytes = sum(item.size for item in actual.values())
    if len(actual) != len(expected.objects):
        raise VerificationError("R2 inventory object count does not match manifest")
    if actual_bytes != expected_bytes:
        raise VerificationError("R2 inventory byte total does not match manifest")
    return {
        "bytes": actual_bytes,
        "files": len(actual),
        "ok": True,
        "prefix": expected.prefix,
        "release_id": expected.release_id,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse paths for an offline post-upload verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the verifier and emit a compact machine-readable result."""
    args = _parse_args(argv)
    try:
        result = verify_release(args.manifest, args.inventory)
    except VerificationError as error:
        print(json.dumps({"error": str(error), "ok": False}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
