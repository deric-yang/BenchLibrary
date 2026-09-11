"""Build an isolated base-first public-export source from a verified prior release.

The prior public release is used only to fill missing ``assets/**`` files. Current
data, site files, hashed index shards, and root indexes are never inherited from
the overlay. Existing base files are never replaced, including byte conflicts.
"""

from __future__ import annotations

import argparse
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
    from scripts.verify_r2_release import (
        RELEASE_ID_PATTERN,
        VerificationError,
        verify_release,
    )
except ModuleNotFoundError:
    from verify_r2_release import (  # type: ignore[no-redef]
        RELEASE_ID_PATTERN,
        VerificationError,
        verify_release,
    )


CHUNK_SIZE = 8 * 1024 * 1024
HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
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
    parser.add_argument("--execute", action="store_true")
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


def summarize_prefixes(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Count selected overlay rows by their first two path components."""
    counts = Counter(
        "/".join(PurePosixPath(str(row["path"])).parts[:2]) for row in rows
    )
    return dict(sorted(counts.items()))


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
    _ = load_object(policy_path, "publication policy")
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
    if not args.execute:
        raise CompositeError("Refusing to build without --execute")
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
