"""Build an isolated base-first public-export source from a verified prior release.

The prior public release is used only to fill missing ``assets/**`` files. Current
data, site files, hashed index shards, and root indexes are never inherited from
the overlay. Verified inline bindings for those exact supplement files may be
merged into regenerated root indexes. Existing base files are never replaced,
including byte conflicts.
"""

from __future__ import annotations

import argparse
import copy
import errno
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from scripts.export_public_release import (
        STRICT_REFERENCE_KEYS,
        iter_local_reference_candidates,
        sanitize_json,
    )
    from scripts.export_public_release import (
        SecurityError as ExportSecurityError,
    )
    from scripts.verify_r2_release import (
        RELEASE_ID_PATTERN,
        VerificationError,
        verify_release,
    )
except ModuleNotFoundError:
    from export_public_release import (  # type: ignore[no-redef]
        STRICT_REFERENCE_KEYS,
        iter_local_reference_candidates,
        sanitize_json,
    )
    from export_public_release import (  # type: ignore[no-redef]
        SecurityError as ExportSecurityError,
    )
    from verify_r2_release import (  # type: ignore[no-redef]
        RELEASE_ID_PATTERN,
        VerificationError,
        verify_release,
    )


CHUNK_SIZE = 8 * 1024 * 1024
HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
BENCH_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")
BASE_SECURITY_CONTRACT = {
    "publish_mode": "allowlist_only",
    "raw_executable_mirrors": "forbidden",
    "switch_mode": "validated_versioned_release",
}
ROOT_INDEXES = frozenset(
    {
        "assets/mirror_index.json",
        "assets/preview_index.json",
        "assets/verifier_source_index.json",
    }
)
RECOVERABLE_INDEXES = {
    "mirror": "assets/mirror_index.json",
    "preview": "assets/preview_index.json",
}
GDPVAL_ASSET_ID = re.compile(r"gdpval:asset-[0-9a-f]{16}")
TRANSFER_FALLBACK_ERRORS = frozenset(
    {
        errno.EACCES,
        errno.EPERM,
        errno.EXDEV,
        errno.ENOTSUP,
    }
)


class CompositeError(RuntimeError):
    """Report a fail-closed composite-source construction error."""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--base-manifest", type=Path)
    parser.add_argument("--overlay-root", type=Path, required=True)
    parser.add_argument("--overlay-manifest", type=Path)
    parser.add_argument("--overlay-inventory", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--plan", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one regular file using bounded reads."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path, label: str) -> dict[str, Any]:
    """Load one non-symlink JSON object."""
    if path.is_symlink() or not path.is_file():
        raise CompositeError(f"{label} must be a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CompositeError(f"Cannot read {label}: {path}") from error
    if not isinstance(payload, dict):
        raise CompositeError(f"{label} must contain a JSON object: {path}")
    return payload


def safe_relative_path(value: Any, label: str) -> str:
    """Return one canonical release-relative POSIX path."""
    if not isinstance(value, str):
        raise CompositeError(f"Unsafe {label}: {value!r}")
    relative = value
    pure = PurePosixPath(relative)
    if (
        not relative
        or "\x00" in relative
        or "\\" in relative
        or pure.is_absolute()
        or relative != pure.as_posix()
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise CompositeError(f"Unsafe {label}: {relative!r}")
    return relative


def require_regular_below(root: Path, relative: str, label: str) -> Path:
    """Resolve a regular file below a trusted root without following symlinks."""
    current = root
    for part in PurePosixPath(relative).parts:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError as error:
            raise CompositeError(f"Missing {label}: {relative}") from error
        if stat.S_ISLNK(mode):
            raise CompositeError(f"Symlink is forbidden in {label}: {relative}")
    resolved = current.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise CompositeError(f"{label} escapes its root: {relative}") from error
    if not resolved.is_file():
        raise CompositeError(f"{label} is not a regular file: {relative}")
    return resolved


def validate_root(path: Path, label: str, must_exist: bool) -> Path:
    """Validate one non-live, non-symlink input or output root."""
    lexical = path.absolute()
    if lexical.is_symlink():
        raise CompositeError(f"{label} cannot be a symlink: {lexical}")
    if must_exist:
        resolved = lexical.resolve(strict=True)
        if not resolved.is_dir():
            raise CompositeError(f"{label} must be a directory: {resolved}")
    else:
        resolved = lexical
        if resolved.exists():
            raise CompositeError(f"{label} already exists: {resolved}")
        parent = resolved.parent.resolve(strict=True)
        resolved = parent / resolved.name
    if resolved == Path("/var/www") or Path("/var/www") in resolved.parents:
        raise CompositeError(f"{label} cannot be below /var/www: {resolved}")
    if not must_exist and (
        resolved.name in {"current", "live"}
        or "current" in resolved.parts
        or "live" in resolved.parts
        or "releases" in resolved.parts
        or "public-releases" in resolved.parts
    ):
        raise CompositeError(f"{label} cannot be a live/current/release path: {resolved}")
    return resolved


def validate_separation(base: Path, overlay: Path, output: Path) -> None:
    """Require the new output to be disjoint from both immutable inputs."""
    for source, label in ((base, "base"), (overlay, "overlay")):
        if output == source or output in source.parents or source in output.parents:
            raise CompositeError(f"Output root cannot nest with {label} root")


def validate_tree_has_no_symlinks(root: Path, label: str) -> None:
    """Allow only regular files and directories in a source tree."""
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        parent = Path(directory)
        for name in directory_names:
            candidate = parent / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise CompositeError(
                    f"{label} contains a non-directory tree entry: {candidate}"
                )
        for name in file_names:
            candidate = parent / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                raise CompositeError(
                    f"{label} contains a non-regular file: {candidate}"
                )


def exact_manifest_path(
    root: Path,
    supplied: Path | None,
    expected_relative: str,
    label: str,
) -> Path:
    """Require a manifest argument to resolve to its fixed path below its root."""
    expected = require_regular_below(root, expected_relative, label)
    if supplied is None:
        return expected
    if supplied.is_symlink():
        raise CompositeError(f"{label} cannot be a symlink")
    supplied_path = supplied.resolve(strict=True)
    if supplied_path != expected:
        raise CompositeError(
            f"{label} must be {expected_relative} below its declared root"
        )
    return supplied_path


def strict_nonnegative_int(value: Any, label: str) -> int:
    """Return a non-negative integer while rejecting booleans."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CompositeError(f"Invalid {label}: {value!r}")
    return value


def indexed_rows(
    manifest: dict[str, Any],
    path_key: str,
    size_key: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    """Index unique file-manifest rows after validating path, size, and digest."""
    raw_rows = manifest.get("files")
    if not isinstance(raw_rows, list):
        raise CompositeError(f"{label} has no files array")
    rows: dict[str, dict[str, Any]] = {}
    for raw_row in raw_rows:
        if not isinstance(raw_row, dict):
            raise CompositeError(f"{label} contains a non-object file row")
        relative = safe_relative_path(raw_row.get(path_key), f"{label} path")
        strict_nonnegative_int(
            raw_row.get(size_key),
            f"{label} size for {relative}",
        )
        digest = raw_row.get("sha256")
        if not isinstance(digest, str) or HEX_SHA256.fullmatch(digest) is None:
            raise CompositeError(f"Invalid {label} SHA-256: {relative}")
        if relative in rows:
            raise CompositeError(f"Duplicate {label} path: {relative}")
        rows[relative] = raw_row
    return rows


def validate_base_manifest(
    manifest: dict[str, Any], rows: dict[str, dict[str, Any]]
) -> None:
    """Validate the immutable base release-manifest envelope."""
    if manifest.get("schema_version") != 1:
        raise CompositeError("Unsupported base release-manifest schema")
    if strict_nonnegative_int(
        manifest.get("file_count"), "base release-manifest file count"
    ) != len(rows):
        raise CompositeError("Base release-manifest file count mismatch")
    total = sum(int(row["size_bytes"]) for row in rows.values())
    if strict_nonnegative_int(
        manifest.get("total_bytes"), "base release-manifest byte count"
    ) != total:
        raise CompositeError("Base release-manifest byte count mismatch")
    if manifest.get("security_contract") != BASE_SECURITY_CONTRACT:
        raise CompositeError("Base release-manifest security contract mismatch")


def validate_base_payload_closure(
    base_root: Path,
    manifest_path: Path,
    rows: dict[str, dict[str, Any]],
) -> None:
    """Require the canonical base tree and manifest payload to match exactly."""
    manifest_relative = manifest_path.relative_to(base_root).as_posix()
    if manifest_relative != "release_manifest.json":
        raise CompositeError("Base release manifest is not at its fixed path")
    if manifest_relative in rows:
        raise CompositeError("Base release manifest cannot list itself as payload")
    expected = set(rows) | {manifest_relative}
    actual: set[str] = set()
    for directory, _, file_names in os.walk(base_root, followlinks=False):
        parent = Path(directory)
        for name in file_names:
            relative = (parent / name).relative_to(base_root).as_posix()
            actual.add(safe_relative_path(relative, "base tree path"))
    missing = set(rows) - actual
    extra = actual - expected
    if missing:
        raise CompositeError(f"Base manifest payload is missing: {sorted(missing)[:3]}")
    if extra:
        raise CompositeError(f"Base tree contains unmanifested payload: {sorted(extra)[:3]}")
    for relative, row in sorted(rows.items()):
        path = require_regular_below(base_root, relative, "base manifest payload")
        verify_identity(
            path,
            int(row["size_bytes"]),
            str(row["sha256"]),
            "base manifest payload",
        )


def validate_overlay_manifest(
    manifest: dict[str, Any],
    rows: dict[str, dict[str, Any]],
    overlay_root: Path,
) -> None:
    """Validate the prior public-release manifest envelope."""
    if manifest.get("schema_version") != 1:
        raise CompositeError("Unsupported public overlay manifest schema")
    totals = manifest.get("totals")
    if not isinstance(totals, dict):
        raise CompositeError("Public overlay manifest has no totals object")
    if strict_nonnegative_int(
        totals.get("files"), "public overlay manifest file count"
    ) != len(rows):
        raise CompositeError("Public overlay manifest file count mismatch")
    total = sum(int(row["size"]) for row in rows.values())
    if strict_nonnegative_int(
        totals.get("logical_bytes"), "public overlay manifest byte count"
    ) != total:
        raise CompositeError("Public overlay manifest byte count mismatch")
    release_id = manifest.get("release_id")
    source = manifest.get("source")
    policy = manifest.get("policy")
    if not isinstance(release_id, str) or not release_id:
        raise CompositeError("Public overlay manifest has no release id")
    if RELEASE_ID_PATTERN.fullmatch(release_id) is None:
        raise CompositeError("Public overlay manifest has an invalid release id")
    if release_id != overlay_root.name:
        raise CompositeError("Public overlay release id does not match its root")
    if not isinstance(source, dict) or not source.get("immutable_directory"):
        raise CompositeError("Public overlay manifest has no source provenance")
    if not isinstance(policy, dict) or not policy.get("id") or not policy.get("sha256"):
        raise CompositeError("Public overlay manifest has no policy provenance")
    if HEX_SHA256.fullmatch(str(policy.get("sha256") or "")) is None:
        raise CompositeError("Public overlay policy SHA-256 is invalid")
    manifest_self = manifest.get("self")
    expected_self = {
        "path": "data/public_manifest.json",
        "r2_key": f"releases/{release_id}/data/public_manifest.json",
    }
    if manifest_self != expected_self:
        raise CompositeError("Public overlay manifest self identity mismatch")
    if expected_self["path"] in rows:
        raise CompositeError("Public overlay manifest cannot list itself as a payload file")
    prefix = f"releases/{release_id}/"
    for relative, row in rows.items():
        if row.get("r2_key") != f"{prefix}{relative}":
            raise CompositeError(f"Public overlay R2 key mismatch: {relative}")


def exact_inventory_path(overlay_root: Path, supplied: Path) -> Path:
    """Require the saved R2 inventory beside the matching public release."""
    expected = overlay_root.parent / f".{overlay_root.name}.r2-inventory.json"
    if supplied.is_symlink():
        raise CompositeError("Overlay R2 inventory cannot be a symlink")
    inventory = supplied.resolve(strict=True)
    if inventory != expected or not inventory.is_file():
        raise CompositeError(f"Overlay R2 inventory must be the fixed sibling: {expected}")
    return inventory


def validate_r2_inventory(
    inventory_path: Path,
    overlay_manifest_path: Path,
    overlay_manifest: dict[str, Any],
    overlay_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Run the canonical full R2 verifier and return its provenance summary."""
    if len(overlay_rows) != int((overlay_manifest["totals"])["files"]):
        raise CompositeError("Overlay rows changed before R2 verification")
    try:
        result = verify_release(overlay_manifest_path, inventory_path)
    except VerificationError as error:
        raise CompositeError(f"Overlay R2 inventory verification failed: {error}") from error
    if (
        result.get("ok") is not True
        or result.get("release_id") != overlay_manifest["release_id"]
    ):
        raise CompositeError("Canonical R2 verifier returned an inconsistent result")
    return {
        "bytes": result["bytes"],
        "complete": True,
        "count": result["files"],
        "full_http_metadata_verified": True,
        "path": str(inventory_path),
        "prefix": result["prefix"],
        "sha256": sha256_file(inventory_path),
        "verifier": "scripts.verify_r2_release.verify_release",
    }


def overlay_path_allowed(relative: str) -> bool:
    """Allow only non-index assets from the verified prior public closure."""
    return (
        relative.startswith(
            (
                "assets/mirrors/",
                "assets/previews/",
                "assets/verifiers/",
            )
        )
        and not relative.startswith("assets/index_shards/")
        and relative not in ROOT_INDEXES
    )


def verify_identity(path: Path, size: int, digest: str, label: str) -> None:
    """Require one physical file to match its manifest identity."""
    if path.stat().st_size != size:
        raise CompositeError(f"{label} size mismatch: {path}")
    actual = sha256_file(path)
    if actual != digest:
        raise CompositeError(f"{label} SHA-256 mismatch: {path}")


def clone_file(source: str, destination: str) -> str:
    """Hard-link one base file, falling back to a byte copy across filesystems."""
    try:
        os.link(source, destination)
    except OSError as error:
        if error.errno not in TRANSFER_FALLBACK_ERRORS:
            raise
        shutil.copy2(source, destination)
    return destination


def install_file(source: Path, destination: Path) -> str:
    """Install one absent overlay file without replacing an existing destination."""
    if destination.exists() or destination.is_symlink():
        raise CompositeError(f"Overlay destination unexpectedly exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError as error:
        if error.errno not in TRANSFER_FALLBACK_ERRORS:
            raise
    shutil.copy2(source, destination)
    return "copy"


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write one deterministic JSON report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def json_bytes(payload: dict[str, Any]) -> bytes:
    """Serialize one JSON object exactly as ``atomic_json`` writes it."""
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return (rendered + "\n").encode("utf-8")


def record_digest(record: dict[str, Any]) -> str:
    """Return a stable digest for one recovered index record."""
    compact = json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(compact).hexdigest()


def digest_strings(values: set[str]) -> str:
    """Hash one sorted set of strings with an unambiguous length prefix."""
    digest = hashlib.sha256()
    for value in sorted(values):
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def verified_json_from_manifest(
    root: Path,
    rows: dict[str, dict[str, Any]],
    relative: str,
    size_key: str,
    label: str,
) -> dict[str, Any]:
    """Load a JSON object only after its physical bytes match its manifest row."""
    row = rows.get(relative)
    if row is None:
        raise CompositeError(f"{label} is absent from its manifest: {relative}")
    size = strict_nonnegative_int(row.get(size_key), f"{label} size")
    digest = str(row["sha256"])
    path = require_regular_below(root, relative, label)
    verify_identity(path, size, digest, label)
    return load_object(path, label)


def publication_full_benches(policy: dict[str, Any]) -> set[str]:
    """Return the policy full allowlist after validating its minimal envelope."""
    if policy.get("schema_version") != 1:
        raise CompositeError("Unsupported publication policy schema")
    full = policy.get("full")
    if not isinstance(full, dict):
        raise CompositeError("Publication policy full must be an object")
    result: set[str] = set()
    for bench_id, rule in full.items():
        if (
            not isinstance(bench_id, str)
            or not bench_id
            or BENCH_ID.fullmatch(bench_id) is None
            or ".." in bench_id
            or not isinstance(rule, dict)
        ):
            raise CompositeError("Publication policy contains an invalid full entry")
        relative = safe_relative_path(
            f"data/benches/{bench_id}.json",
            "publication policy benchmark",
        )
        if relative != f"data/benches/{bench_id}.json":
            raise CompositeError(f"Unsafe publication policy benchmark: {bench_id!r}")
        result.add(bench_id)
    return result


def canonical_task_ids(
    base_root: Path,
    base_rows: dict[str, dict[str, Any]],
    bench_id: str,
) -> set[str]:
    """Load the canonical task identities from one verified current bench shard."""
    relative = f"data/benches/{bench_id}.json"
    shard = verified_json_from_manifest(
        base_root,
        base_rows,
        relative,
        "size_bytes",
        f"base task shard for {bench_id}",
    )
    if shard.get("benchmark_id") != bench_id:
        raise CompositeError(f"Base task shard benchmark mismatch: {bench_id}")
    tasks = shard.get("tasks")
    if not isinstance(tasks, list):
        raise CompositeError(f"Base task shard has no tasks array: {bench_id}")
    task_ids: set[str] = set()
    for task in tasks:
        task_id = task.get("id") if isinstance(task, dict) else None
        if not isinstance(task_id, str) or not task_id:
            raise CompositeError(f"Base task shard contains an invalid task: {bench_id}")
        if task_id in task_ids:
            raise CompositeError(f"Base task shard contains a duplicate task: {task_id}")
        task_ids.add(task_id)
    declared = shard.get("record_count")
    if declared is not None and strict_nonnegative_int(
        declared,
        f"base task shard record count for {bench_id}",
    ) != len(task_ids):
        raise CompositeError(f"Base task shard record count mismatch: {bench_id}")
    return task_ids


def exporter_record_references(record: dict[str, Any]) -> set[tuple[str, str]]:
    """Discover references with the public exporter's exact recursive parser."""
    sanitized = sanitized_recovery_record(record)
    try:
        return set(iter_local_reference_candidates(sanitized))
    except ExportSecurityError as error:
        raise CompositeError(f"Unsafe recovered record reference: {error}") from error


def classify_record_paths(
    record: dict[str, Any],
    supplements: set[str],
    existing_payloads: set[str],
) -> tuple[set[str], set[str], set[str]]:
    """Classify exporter references as supplement, forbidden, or ignored prose."""
    selected: set[str] = set()
    outside: set[str] = set()
    ignored: set[str] = set()
    for relative, parent_key in exporter_record_references(record):
        if relative in supplements:
            selected.add(relative)
        elif (
            parent_key in STRICT_REFERENCE_KEYS
            or parent_key.endswith("_url")
            or relative in existing_payloads
        ):
            outside.add(relative)
        else:
            # This is the same non-strict, physically absent prose/provenance case
            # that PublicReleaseExporter._enqueue_references intentionally ignores.
            ignored.add(relative)
    return selected, outside, ignored


def validated_base_record_paths(
    record: dict[str, Any],
    existing_payloads: set[str],
) -> set[str]:
    """Return existing base references and reject any strict missing reference."""
    paths: set[str] = set()
    for relative, parent_key in exporter_record_references(record):
        if relative in existing_payloads:
            paths.add(relative)
        elif parent_key in STRICT_REFERENCE_KEYS or parent_key.endswith("_url"):
            raise CompositeError(f"Base index contains a missing strict reference: {relative}")
    return paths


def scoped_path_benchmark(relative: str) -> str | None:
    """Return a benchmark identity encoded by one benchmark-owned asset path."""
    parts = PurePosixPath(relative).parts
    if len(parts) >= 3 and parts[:2] == ("assets", "mirrors"):
        return parts[2]
    if len(parts) >= 4 and parts[:3] == ("assets", "previews", "html"):
        return parts[3]
    return None


def _without_object_paths(value: Any) -> Any:
    """Deep-copy JSON-like data while dropping every internal object_path key."""
    if isinstance(value, dict):
        return {
            key: _without_object_paths(child)
            for key, child in value.items()
            if key != "object_path"
        }
    if isinstance(value, list):
        return [_without_object_paths(child) for child in value]
    return copy.deepcopy(value)


def sanitized_recovery_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return the exact record the exporter may safely serialize later."""
    without_object_paths = _without_object_paths(record)
    result, _ = sanitize_json(without_object_paths)
    if not isinstance(result, dict):
        raise CompositeError("Recovered record sanitization changed its object shape")
    return result


def validate_recovery_binding(
    record: dict[str, Any],
    canonical: dict[str, set[str]],
) -> str:
    """Validate one current task binding or the narrow GDPval asset exception."""
    bench_id = record.get("bench_id")
    task_id = record.get("task_id")
    task_ids = record.get("task_ids")
    if not isinstance(bench_id, str) or bench_id not in canonical:
        raise CompositeError("Recovered record has no canonical full benchmark")
    if not isinstance(task_id, str) or task_ids != [task_id]:
        raise CompositeError("Recovered record must have one exact task identity")
    if task_id in canonical[bench_id]:
        return "task"
    if (
        bench_id == "gdpval"
        and GDPVAL_ASSET_ID.fullmatch(task_id) is not None
        and record.get("role") in {"catalog", "reference"}
    ):
        return "benchmark_asset"
    raise CompositeError(
        f"Recovered record refers to a non-current task: {bench_id}/{task_id}"
    )


def recompute_summary(
    kind: str,
    summary: Any,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Recompute every standard count-bearing summary field deterministically."""
    result = copy.deepcopy(summary) if isinstance(summary, dict) else {}
    ready = [record for record in records if record.get("status") == "ready"]
    result["records"] = len(records)
    result["ready_records"] = len(ready)
    result["error_records"] = len(records) - len(ready)
    result["bench_counts"] = dict(
        sorted(Counter(str(record.get("bench_id") or "") for record in records).items())
    )
    if "role_counts" in result:
        result["role_counts"] = dict(
            sorted(
                Counter(str(record.get("role") or "unknown") for record in records).items()
            )
        )
    if "kind_counts" in result:
        result["kind_counts"] = dict(
            sorted(
                Counter(
                    str(record.get("preview_kind") or "unknown")
                    for record in ready
                ).items()
            )
        )
    if kind == "mirror":
        objects: dict[str, int] = {}
        for record in ready:
            digest = record.get("sha256") or record.get("source_sha256")
            size = record.get("size")
            if size is None:
                size = record.get("source_size")
            if digest is None or size is None:
                continue
            if not isinstance(digest, str) or HEX_SHA256.fullmatch(digest) is None:
                raise CompositeError("Recovered mirror record has an invalid digest")
            size_value = strict_nonnegative_int(size, "recovered mirror record size")
            previous = objects.setdefault(digest, size_value)
            if previous != size_value:
                raise CompositeError(f"Recovered mirror object size conflicts: {digest}")
        result["unique_objects"] = len(objects)
        result["unique_bytes"] = sum(objects.values())
    return result


def verified_index_records(
    root: Path,
    rows: dict[str, dict[str, Any]],
    root_index: dict[str, Any],
    kind: str,
    size_key: str,
    label: str,
) -> list[dict[str, Any]]:
    """Reconstruct unique records from one verified current root and its shards."""
    raw_records = root_index.get("records")
    if not isinstance(raw_records, list):
        raise CompositeError(f"{label} records must be an array")
    records: dict[str, dict[str, Any]] = {}

    def add_records(values: list[Any], source_label: str) -> None:
        """Add unique record objects from one verified source."""
        for value in values:
            if not isinstance(value, dict):
                raise CompositeError(f"{source_label} contains a non-object record")
            digest = record_digest(value)
            records.setdefault(digest, value)

    add_records(raw_records, label)
    record_shards = root_index.get("record_shards")
    if not isinstance(record_shards, dict):
        raise CompositeError(f"{label} record_shards must be an object")
    by_bench = record_shards.get("by_bench")
    if not isinstance(by_bench, dict):
        raise CompositeError(f"{label} record_shards.by_bench must be an object")
    shard_paths: set[str] = set()
    for bench_id, definition in by_bench.items():
        if not isinstance(bench_id, str) or not isinstance(definition, dict):
            raise CompositeError(f"{label} has an invalid benchmark shard definition")
        common_url = definition.get("common_url")
        if common_url is not None:
            shard_paths.add(safe_relative_path(common_url, f"{label} common shard"))
        tasks = definition.get("tasks")
        if not isinstance(tasks, dict):
            raise CompositeError(f"{label} task shard map must be an object: {bench_id}")
        for task_id, shard_path in tasks.items():
            if not isinstance(task_id, str) or not task_id:
                raise CompositeError(f"{label} contains an invalid task shard identity")
            shard_paths.add(safe_relative_path(shard_path, f"{label} task shard"))
    expected_prefix = f"assets/index_shards/{kind}/"
    for relative in sorted(shard_paths):
        if not relative.startswith(expected_prefix):
            raise CompositeError(f"{label} references an out-of-scope shard: {relative}")
        shard = verified_json_from_manifest(
            root,
            rows,
            relative,
            size_key,
            f"{label} shard",
        )
        shard_records = shard.get("records")
        if not isinstance(shard_records, list):
            raise CompositeError(f"{label} shard has no records array: {relative}")
        add_records(shard_records, f"{label} shard {relative}")
    return [records[digest] for digest in sorted(records)]


def plan_recovered_indexes(
    base_root: Path,
    base_rows: dict[str, dict[str, Any]],
    overlay_root: Path,
    overlay_rows: dict[str, dict[str, Any]],
    additions: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Plan deterministic root-index recovery without writing to either tree."""
    full = publication_full_benches(policy)
    supplement_paths = {str(row["path"]) for row in additions}
    recoverable_supplements = {
        path
        for path in supplement_paths
        if path.startswith(("assets/mirrors/", "assets/previews/"))
    }
    existing_payloads = set(base_rows) | set(overlay_rows)
    canonical: dict[str, set[str]] = {}
    recovered_paths: set[str] = set()
    plans: dict[str, dict[str, Any]] = {}
    mirror_sha256: str | None = None
    for kind, relative in RECOVERABLE_INDEXES.items():
        base_index = verified_json_from_manifest(
            base_root,
            base_rows,
            relative,
            "size_bytes",
            f"base {kind} root index",
        )
        overlay_index = verified_json_from_manifest(
            overlay_root,
            overlay_rows,
            relative,
            "size",
            f"overlay {kind} root index",
        )
        if base_index.get("schema_version") != 1:
            raise CompositeError(f"Unsupported base {kind} root index schema")
        if overlay_index.get("schema_version") != 1:
            raise CompositeError(f"Unsupported overlay {kind} root index schema")
        base_records = verified_index_records(
            base_root,
            base_rows,
            base_index,
            kind,
            "size_bytes",
            f"base {kind} index",
        )
        base_digests = {record_digest(record) for record in base_records}
        base_paths = {
            path
            for record in base_records
            for path in validated_base_record_paths(record, set(base_rows))
        }
        raw_overlay_records = overlay_index.get("records")
        if not isinstance(raw_overlay_records, list):
            raise CompositeError(f"Overlay {kind} root records must be an array")
        recovered: list[dict[str, Any]] = []
        binding_counts: Counter[str] = Counter()
        benchmark_asset_ids: set[str] = set()
        kind_recovered_paths: set[str] = set()
        ignored_non_strict_paths: set[str] = set()
        for raw_record in raw_overlay_records:
            if not isinstance(raw_record, dict):
                raise CompositeError(f"Overlay {kind} root contains a non-object record")
            paths, outside, ignored = classify_record_paths(
                raw_record,
                recoverable_supplements,
                existing_payloads,
            )
            if not paths:
                continue
            bench_id = raw_record.get("bench_id")
            if not isinstance(bench_id, str) or bench_id not in full:
                raise CompositeError(
                    f"Recovered {kind} record is outside policy full: {bench_id!r}"
                )
            if raw_record.get("status") != "ready":
                raise CompositeError(f"Recovered {kind} record is not ready")
            if outside:
                raise CompositeError(
                    f"Recovered {kind} record points outside supplements: {sorted(outside)}"
                )
            cross_bench = {
                path
                for path in paths
                if scoped_path_benchmark(path) not in {None, bench_id}
            }
            if cross_bench:
                raise CompositeError(
                    f"Recovered {kind} record crosses benchmark scope: {sorted(cross_bench)}"
                )
            if paths & base_paths:
                raise CompositeError(
                    f"Recovered {kind} record conflicts with a base path: {sorted(paths & base_paths)}"
                )
            if bench_id not in canonical:
                canonical[bench_id] = canonical_task_ids(
                    base_root,
                    base_rows,
                    bench_id,
                )
            record = sanitized_recovery_record(raw_record)
            binding = validate_recovery_binding(record, canonical)
            digest = record_digest(record)
            if digest in base_digests:
                raise CompositeError(f"Recovered {kind} record duplicates a base record")
            recovered.append(record)
            binding_counts[binding] += 1
            recovered_paths.update(paths)
            kind_recovered_paths.update(paths)
            ignored_non_strict_paths.update(ignored)
            if binding == "benchmark_asset":
                benchmark_asset_ids.add(str(record["task_id"]))
        recovered.sort(
            key=lambda record: (
                str(record.get("bench_id") or ""),
                str(record.get("task_id") or ""),
                str(record.get("role") or ""),
                record_digest(record),
            )
        )
        recovered_digests = {record_digest(record) for record in recovered}
        if len(recovered_digests) != len(recovered):
            raise CompositeError(f"Overlay {kind} root contains duplicate recovery records")
        merged = copy.deepcopy(base_index)
        merged["records"] = copy.deepcopy(base_index["records"]) + recovered
        merged["summary"] = recompute_summary(
            kind,
            base_index.get("summary"),
            base_records + recovered,
        )
        merged["composite_recovery"] = {
            "base_index_sha256": str(base_rows[relative]["sha256"]),
            "benchmark_asset_ids": sorted(benchmark_asset_ids),
            "benchmark_asset_records": binding_counts["benchmark_asset"],
            "ignored_non_strict_missing_path_sha256": digest_strings(
                ignored_non_strict_paths
            ),
            "ignored_non_strict_missing_paths": len(ignored_non_strict_paths),
            "overlay_index_sha256": str(overlay_rows[relative]["sha256"]),
            "record_sha256": digest_strings(recovered_digests),
            "records": len(recovered),
            "schema_version": 1,
            "supplement_path_sha256": digest_strings(kind_recovered_paths),
            "supplement_paths": len(kind_recovered_paths),
            "task_records": binding_counts["task"],
        }
        if kind == "preview":
            if mirror_sha256 is None:
                raise CompositeError("Preview recovery was planned before mirror recovery")
            merged["mirror_index_sha256"] = mirror_sha256
        content = json_bytes(merged)
        digest = hashlib.sha256(content).hexdigest()
        if kind == "mirror":
            mirror_sha256 = digest
        plans[kind] = {
            "content": content,
            "payload": merged,
            "sha256": digest,
            "stats": copy.deepcopy(merged["composite_recovery"]),
        }
    missing_coverage = recoverable_supplements - recovered_paths
    if missing_coverage:
        raise CompositeError(
            "Supplement assets are not covered by recovered records: "
            f"{sorted(missing_coverage)[:3]}"
        )
    return plans


def summarize_prefixes(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Count selected overlay rows by their first two path components."""
    counts = Counter(
        "/".join(PurePosixPath(str(row["path"])).parts[:2]) for row in rows
    )
    return dict(sorted(counts.items()))


def plan_composite(
    base_root: Path,
    base_manifest_path: Path,
    overlay_root: Path,
    overlay_manifest_path: Path,
    overlay_inventory_path: Path,
    policy_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Validate both releases and return a deterministic, write-free build plan."""
    base_root = validate_root(base_root, "base root", True)
    overlay_root = validate_root(overlay_root, "overlay root", True)
    output_root = validate_root(output_root, "output root", False)
    validate_separation(base_root, overlay_root, output_root)
    base_manifest_path = exact_manifest_path(
        base_root,
        base_manifest_path,
        "release_manifest.json",
        "base manifest",
    )
    overlay_manifest_path = exact_manifest_path(
        overlay_root,
        overlay_manifest_path,
        "data/public_manifest.json",
        "overlay manifest",
    )
    overlay_inventory_path = exact_inventory_path(
        overlay_root,
        overlay_inventory_path,
    )
    validate_tree_has_no_symlinks(base_root, "base root")
    validate_tree_has_no_symlinks(overlay_root, "overlay root")
    base_manifest = load_object(base_manifest_path, "base release manifest")
    overlay_manifest = load_object(overlay_manifest_path, "public overlay manifest")
    policy = load_object(policy_path, "publication policy")
    base_rows = indexed_rows(
        base_manifest,
        "path",
        "size_bytes",
        "base release manifest",
    )
    overlay_rows = indexed_rows(
        overlay_manifest,
        "path",
        "size",
        "public overlay manifest",
    )
    validate_base_manifest(base_manifest, base_rows)
    validate_base_payload_closure(base_root, base_manifest_path, base_rows)
    validate_overlay_manifest(overlay_manifest, overlay_rows, overlay_root)
    inventory_summary = validate_r2_inventory(
        overlay_inventory_path,
        overlay_manifest_path,
        overlay_manifest,
        overlay_rows,
    )
    additions: list[dict[str, Any]] = []
    identical = 0
    identical_bytes = 0
    conflicts: list[dict[str, Any]] = []
    for relative, overlay_row in sorted(overlay_rows.items()):
        if not overlay_path_allowed(relative):
            continue
        base_row = base_rows.get(relative)
        if base_row is None:
            additions.append(overlay_row)
            continue
        base_size = int(base_row["size_bytes"])
        overlay_size = int(overlay_row["size"])
        base_digest = str(base_row["sha256"])
        overlay_digest = str(overlay_row["sha256"])
        if base_size == overlay_size and base_digest == overlay_digest:
            identical += 1
            identical_bytes += base_size
            continue
        base_path = require_regular_below(base_root, relative, "base conflict file")
        overlay_path = require_regular_below(
            overlay_root,
            relative,
            "overlay conflict file",
        )
        verify_identity(base_path, base_size, base_digest, "base conflict file")
        verify_identity(
            overlay_path,
            overlay_size,
            overlay_digest,
            "overlay conflict file",
        )
        conflicts.append(
            {
                "base_sha256": base_digest,
                "base_size": base_size,
                "decision": "base_retained",
                "overlay_sha256": overlay_digest,
                "overlay_size": overlay_size,
                "path": relative,
            }
        )
    recovery = plan_recovered_indexes(
        base_root,
        base_rows,
        overlay_root,
        overlay_rows,
        additions,
        policy,
    )
    return {
        "_private": {
            "base_manifest": base_manifest,
            "base_rows": base_rows,
            "overlay_manifest": overlay_manifest,
            "overlay_rows": overlay_rows,
            "recovery": recovery,
        },
        "additions": additions,
        "base_manifest_path": base_manifest_path,
        "base_root": base_root,
        "conflicts": conflicts,
        "identical_bytes": identical_bytes,
        "identical_files": identical,
        "inventory_summary": inventory_summary,
        "output_root": output_root,
        "overlay_inventory_path": overlay_inventory_path,
        "overlay_manifest_path": overlay_manifest_path,
        "overlay_root": overlay_root,
        "policy_path": policy_path,
        "recovery": {
            kind: {
                "sha256": item["sha256"],
                "size": len(item["content"]),
                "stats": item["stats"],
            }
            for kind, item in recovery.items()
        },
    }


def build_composite(
    base_root: Path,
    base_manifest_path: Path,
    overlay_root: Path,
    overlay_manifest_path: Path,
    overlay_inventory_path: Path,
    policy_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Construct one isolated composite and return its complete provenance."""
    plan = plan_composite(
        base_root,
        base_manifest_path,
        overlay_root,
        overlay_manifest_path,
        overlay_inventory_path,
        policy_path,
        output_root,
    )
    base_root = plan["base_root"]
    base_manifest_path = plan["base_manifest_path"]
    overlay_root = plan["overlay_root"]
    overlay_manifest_path = plan["overlay_manifest_path"]
    overlay_inventory_path = plan["overlay_inventory_path"]
    policy_path = plan["policy_path"]
    output_root = plan["output_root"]
    additions = plan["additions"]
    conflicts = plan["conflicts"]
    identical = plan["identical_files"]
    identical_bytes = plan["identical_bytes"]
    inventory_summary = plan["inventory_summary"]
    overlay_manifest = plan["_private"]["overlay_manifest"]
    recovery = plan["_private"]["recovery"]

    partial = output_root.with_name(f".{output_root.name}.partial-{os.getpid()}")
    if partial.exists() or partial.is_symlink():
        raise CompositeError(f"Partial composite already exists: {partial}")
    transfer_counts: Counter[str] = Counter()
    installed_rows: list[dict[str, Any]] = []
    try:
        shutil.copytree(base_root, partial, copy_function=clone_file)
        for overlay_row in additions:
            relative = str(overlay_row["path"])
            size = int(overlay_row["size"])
            digest = str(overlay_row["sha256"])
            source = require_regular_below(overlay_root, relative, "overlay addition")
            verify_identity(source, size, digest, "overlay addition")
            destination = partial.joinpath(*PurePosixPath(relative).parts)
            transfer = install_file(source, destination)
            verify_identity(destination, size, digest, "installed overlay addition")
            transfer_counts[transfer] += 1
            installed_rows.append(
                {
                    "path": relative,
                    "sha256": digest,
                    "size": size,
                    "transfer": transfer,
                }
            )
        for kind, recovery_plan in recovery.items():
            relative = RECOVERABLE_INDEXES[kind]
            destination = partial.joinpath(*PurePosixPath(relative).parts)
            atomic_json(destination, recovery_plan["payload"])
            expected_size = len(recovery_plan["content"])
            verify_identity(
                destination,
                expected_size,
                str(recovery_plan["sha256"]),
                f"generated {kind} root index",
            )
        provenance = {
            "base": {
                "manifest_path": str(base_manifest_path),
                "manifest_sha256": sha256_file(base_manifest_path),
                "release_id": base_root.name,
                "root": str(base_root),
            },
            "complete": True,
            "conflicts": conflicts,
            "output_root": str(output_root),
            "overlay": {
                "public_manifest_totals": {
                    "files": int((overlay_manifest["totals"])["files"]),
                    "logical_bytes": int(
                        (overlay_manifest["totals"])["logical_bytes"]
                    ),
                },
                "manifest_path": str(overlay_manifest_path),
                "manifest_sha256": sha256_file(overlay_manifest_path),
                "policy": overlay_manifest["policy"],
                "publication": overlay_manifest.get("publication"),
                "release_id": overlay_manifest["release_id"],
                "r2_inventory": inventory_summary,
                "root": str(overlay_root),
                "source": overlay_manifest["source"],
            },
            "policy": {
                "path": str(policy_path),
                "sha256": sha256_file(policy_path),
            },
            "index_recovery": plan["recovery"],
            "schema_version": 1,
            "selection": {
                "added_bytes": sum(int(row["size"]) for row in additions),
                "added_files": len(additions),
                "base_retained_conflicts": len(conflicts),
                "existing_identical_bytes": identical_bytes,
                "existing_identical_files": identical,
                "overlay_not_inherited": {
                    "data": True,
                    "hashed_index_shards": True,
                    "other_asset_namespaces": True,
                    "root_indexes": sorted(ROOT_INDEXES),
                    "site": True,
                },
                "prefix_counts": summarize_prefixes(additions),
                "regenerated_root_indexes": sorted(RECOVERABLE_INDEXES.values()),
            },
            "supplements": installed_rows,
            "transfer_counts": dict(sorted(transfer_counts.items())),
        }
        atomic_json(partial / ".kwbl-composite-provenance.json", provenance)
        partial.rename(output_root)
        return provenance
    except Exception:
        # A failed partial is intentionally retained for forensic inspection.
        print(f"Composite build failed; retained partial at {partial}", file=sys.stderr)
        raise


def main() -> int:
    """Validate arguments, build the composite, and print its provenance summary."""
    args = parse_args()
    base_root = validate_root(args.base_root, "base root", True)
    overlay_root = validate_root(args.overlay_root, "overlay root", True)
    output_root = validate_root(args.output_root, "output root", False)
    validate_separation(base_root, overlay_root, output_root)
    base_manifest = exact_manifest_path(
        base_root,
        args.base_manifest,
        "release_manifest.json",
        "base manifest",
    )
    overlay_manifest = exact_manifest_path(
        overlay_root,
        args.overlay_manifest,
        "data/public_manifest.json",
        "overlay manifest",
    )
    overlay_inventory = exact_inventory_path(overlay_root, args.overlay_inventory)
    policy = args.policy.resolve(strict=True)
    if args.plan:
        plan = plan_composite(
            base_root,
            base_manifest,
            overlay_root,
            overlay_manifest,
            overlay_inventory,
            policy,
            output_root,
        )
        result = {
            "complete": True,
            "conflicts": len(plan["conflicts"]),
            "mode": "plan",
            "output_created": False,
            "output_root": str(plan["output_root"]),
            "recovery": plan["recovery"],
            "selection": {
                "added_bytes": sum(int(row["size"]) for row in plan["additions"]),
                "added_files": len(plan["additions"]),
                "base_retained_conflicts": len(plan["conflicts"]),
                "existing_identical_bytes": plan["identical_bytes"],
                "existing_identical_files": plan["identical_files"],
                "prefix_counts": summarize_prefixes(plan["additions"]),
            },
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    provenance = build_composite(
        base_root,
        base_manifest,
        overlay_root,
        overlay_manifest,
        overlay_inventory,
        policy,
        output_root,
    )
    result = {
        "complete": provenance["complete"],
        "conflicts": len(provenance["conflicts"]),
        "output_root": provenance["output_root"],
        "selection": provenance["selection"],
        "transfer_counts": provenance["transfer_counts"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
