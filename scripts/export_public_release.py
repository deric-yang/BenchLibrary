"""Build a fail-closed, hard-linked public KW Bench Library release."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import errno
import gzip
import hashlib
import json
import mimetypes
import os
import re
import stat
import sys
import zipfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator
from urllib.parse import unquote, urlsplit


CHUNK_BYTES = 8 * 1024 * 1024
SCANNER_OVERLAP_BYTES = 4096
MAX_SITE_FILES = 500
MAX_SITE_FILE_BYTES = 25 * 1024 * 1024
MAX_SITE_TOTAL_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_FILES = 250_000
MAX_ARCHIVE_MEMBER_BYTES = 4 * 1024 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 20 * 1024 * 1024 * 1024
PUBLIC_TOP_LEVELS = frozenset({"assets", "data"})
STRICT_REFERENCE_KEYS = frozenset(
    {
        "asset_path",
        "data_url",
        "detail_url",
        "details_url",
        "download_path",
        "local_preview_url",
        "local_url",
        "mirror_url",
        "page_images",
        "pages",
        "path",
        "preview_url",
        "preview_pages",
        "shard_url",
        "source_url",
        "source_view_path",
        "url",
        "view_path",
    }
)
INDEX_SUMMARY_BENCH_KEYS = frozenset(
    {
        "bench_counts",
        "source_code_coverage_by_bench",
        "task_coverage_by_bench",
    }
)
SENSITIVE_KEY_RE = re.compile(
    r"(?:^|[-_])(?:api[-_]?key|access[-_]?token|refresh[-_]?token|authorization|auth[-_]?token|"
    r"password|passwd|secret|private[-_]?key|cookie|credential)(?:$|[-_])",
    re.IGNORECASE,
)
REDACTED_RE = re.compile(r"^\[REDACTED(?:[ _-][^\]]+)?\]$", re.IGNORECASE)
SECRET_PATTERNS_TEXT = (
    re.compile(r"(?<![A-Za-z0-9])hf_[A-Za-z0-9]{20,}(?![A-Za-z0-9])"),
    re.compile(
        r"(?<![A-Za-z0-9])sk-(?=[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-]))"
        r"(?=[A-Za-z0-9_-]*[A-Z0-9_])[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"
    ),
    re.compile(r"(?<![A-Za-z0-9])github_pat_[A-Za-z0-9_]{20,}(?![A-Za-z0-9_])"),
    re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{20,}(?![A-Za-z0-9])"),
    re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{20,}(?![A-Za-z0-9-])"),
    re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
        r"(?![A-Za-z0-9_-])"
    ),
    re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
        re.DOTALL,
    ),
)
SECRET_PATTERNS_BYTES = tuple(
    re.compile(pattern.pattern.encode("ascii"), pattern.flags & ~re.UNICODE)
    for pattern in SECRET_PATTERNS_TEXT
)
SIGNED_QUERY_RE = re.compile(
    r"(?i)(?P<prefix>(?:access[_-]?token|api[_-]?key|secret|signature|credential)=)"
    r"(?P<value>[^&#\s]+)"
)
CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
INTERNAL_LOCATION_PATTERNS = (
    re.compile(r"/mnt/data/[^\s\"']+"),
    re.compile(r"/Users/[^\s\"']+"),
    re.compile(r"/home/[^\s\"']+"),
    re.compile(r"(?i)(?:https?://)?10\.(?:[0-9]{1,3}\.){2}[0-9]{1,3}(?::[0-9]+)?[^\s\"']*"),
)
FORBIDDEN_SITE_MARKERS = (
    b"Contributor Key",
    b"HF Token",
    b":8913",
    b"ingestion.js",
)


class ExportError(RuntimeError):
    """Report a deterministic public-export validation failure."""


class SecurityError(ExportError):
    """Report an unsafe path, symlink, or credential finding."""


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO 8601 form."""
    return datetime.now(timezone.utc).isoformat()


def _json_bytes(value: Any) -> bytes:
    """Serialize generated JSON in a stable, human-readable format."""
    rendered = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    return (rendered + "\n").encode("utf-8")


def _load_json_file(path: Path) -> Any:
    """Load one UTF-8 JSON file and wrap decoding failures with its path."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"Cannot read valid JSON from {path}: {exc}") from exc


def _redact_string(value: str) -> tuple[str, int]:
    """Remove strong credential shapes and signed URL query values from a string."""
    if REDACTED_RE.fullmatch(value.strip()):
        return value, 0
    result, redactions = CONTROL_CHARACTER_RE.subn("", value)
    normalized_slashes = result.replace("\\", "/")
    if (value.startswith("assets/") or value.startswith("data/")) and "/.~lock." in normalized_slashes:
        return "[EPHEMERAL LOCK FILE EXCLUDED]", 1
    for pattern in SECRET_PATTERNS_TEXT:
        result, count = pattern.subn("[REDACTED]", result)
        redactions += count
    if "?" in result or "&" in result:
        result, count = SIGNED_QUERY_RE.subn(r"\g<prefix>[REDACTED]", result)
        redactions += count
    for pattern in INTERNAL_LOCATION_PATTERNS:
        result, count = pattern.subn("[INTERNAL LOCATION REDACTED]", result)
        redactions += count
    return result, redactions


def sanitize_json(value: Any, parent_key: str = "") -> tuple[Any, int]:
    """Recursively redact sensitive JSON fields and credential-shaped strings."""
    if parent_key and SENSITIVE_KEY_RE.search(parent_key):
        if value is None or isinstance(value, bool):
            return value, 0
        if isinstance(value, str) and REDACTED_RE.fullmatch(value.strip()):
            return value, 0
        return "[REDACTED]", 1
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        count = 0
        for key, child in value.items():
            safe_child, child_count = sanitize_json(child, str(key))
            result[str(key)] = safe_child
            count += child_count
        return result, count
    if isinstance(value, list):
        result_list: list[Any] = []
        count = 0
        for child in value:
            safe_child, child_count = sanitize_json(child, parent_key)
            result_list.append(safe_child)
            count += child_count
        return result_list, count
    if isinstance(value, str):
        return _redact_string(value)
    return value, 0


def _normalize_reference(value: str) -> str | None:
    """Return a safe release-relative data/assets path or None for non-local text."""
    candidate = value.strip()
    if not candidate or "\x00" in candidate:
        if "\x00" in candidate and candidate.lower().startswith(("assets/", "data/")):
            raise SecurityError(f"Unsafe local-looking path: {value!r}")
        return None
    if "\\" in candidate:
        if candidate.lower().startswith(("assets\\", "data\\")):
            raise SecurityError(f"Unsafe local-looking path: {value!r}")
        return None
    lowered = candidate.lower()
    if lowered.startswith(("http://", "https://", "data:", "blob:", "mailto:")):
        return None
    path_text = unquote(urlsplit(candidate).path)
    for prefix in ("/bench-monitor/", "bench-monitor/", "./"):
        if path_text.startswith(prefix):
            path_text = path_text[len(prefix):]
    if path_text.startswith("/"):
        path_text = path_text[1:]
    if not any(path_text.startswith(f"{top}/") for top in PUBLIC_TOP_LEVELS):
        return None
    pure_path = PurePosixPath(path_text)
    if pure_path.is_absolute() or any(part in {"", ".", ".."} for part in pure_path.parts):
        raise SecurityError(f"Unsafe release path reference: {value!r}")
    if len(pure_path.parts) < 2:
        return None
    return pure_path.as_posix()


def iter_local_reference_candidates(value: Any, parent_key: str = "") -> Iterator[tuple[str, str]]:
    """Yield local path candidates together with the JSON key that carried each value."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_local_reference_candidates(child, str(key))
        return
    if isinstance(value, list):
        for child in value:
            yield from iter_local_reference_candidates(child, parent_key)
        return
    if isinstance(value, str):
        normalized = _normalize_reference(value)
        if normalized is not None:
            yield normalized, parent_key


def _is_sensitive_match(chunk: bytes) -> bool:
    """Return whether bytes contain a strong credential or private-key shape."""
    return any(pattern.search(chunk) is not None for pattern in SECRET_PATTERNS_BYTES)


def _iter_file_chunks(path: Path) -> Iterator[bytes]:
    """Stream a file in bounded chunks."""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_BYTES)
            if not chunk:
                return
            yield chunk


def _scan_chunks(chunks: Iterable[bytes], label: str) -> None:
    """Fail when a stream contains a credential spanning one or more chunks."""
    tail = b""
    for chunk in chunks:
        sample = tail + chunk
        if _is_sensitive_match(sample):
            raise SecurityError(f"Credential-shaped content remains in {label}")
        tail = sample[-SCANNER_OVERLAP_BYTES:]


def _bounded_chunks(handle: Any, maximum_bytes: int, label: str) -> Iterator[bytes]:
    """Read a decompression stream without allowing an unbounded archive expansion."""
    total = 0
    while True:
        chunk = handle.read(CHUNK_BYTES)
        if not chunk:
            return
        total += len(chunk)
        if total > maximum_bytes:
            raise SecurityError(f"Compressed content exceeds scan limit in {label}")
        yield chunk


def _scan_zip_contents(path: Path, relative_path: str) -> None:
    """Scan ZIP and Office-package members without extracting or executing them."""
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > MAX_ARCHIVE_FILES:
                raise SecurityError(f"Archive has too many members: {relative_path}")
            total_size = sum(member.file_size for member in members if not member.is_dir())
            if total_size > MAX_ARCHIVE_TOTAL_BYTES:
                raise SecurityError(f"Archive expands beyond scan limit: {relative_path}")
            for member in members:
                if member.is_dir():
                    continue
                member_path = PurePosixPath(member.filename.replace("\\", "/"))
                if (
                    member_path.is_absolute()
                    or ".." in member_path.parts
                    or "\x00" in member.filename
                ):
                    raise SecurityError(f"Unsafe member path in archive: {relative_path}")
                if member.flag_bits & 0x1:
                    raise SecurityError(f"Encrypted archive member cannot be scanned: {relative_path}")
                if member.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                    raise SecurityError(f"Archive member exceeds scan limit: {relative_path}")
                label = f"{relative_path}!/{member.filename}"
                with archive.open(member, "r") as handle:
                    _scan_chunks(_bounded_chunks(handle, member.file_size, label), label)
    except SecurityError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ExportError(f"Cannot safely scan archive {relative_path}: {exc}") from exc


def _scan_compressed_contents(path: Path, relative_path: str) -> None:
    """Inspect compressed payloads that can conceal credential-shaped content."""
    suffix = path.suffix.lower()
    zip_suffixes = {
        ".docm",
        ".docx",
        ".epub",
        ".jar",
        ".odf",
        ".odg",
        ".odp",
        ".ods",
        ".odt",
        ".pptm",
        ".pptx",
        ".xlsm",
        ".xlsx",
        ".zip",
    }
    if suffix in zip_suffixes:
        _scan_zip_contents(path, relative_path)
    elif suffix == ".gz" or relative_path.lower().endswith(".tgz"):
        try:
            with gzip.open(path, "rb") as handle:
                chunks = _bounded_chunks(handle, MAX_ARCHIVE_TOTAL_BYTES, relative_path)
                _scan_chunks(chunks, f"{relative_path} (decompressed)")
        except OSError as exc:
            raise ExportError(f"Invalid gzip payload in {relative_path}: {exc}") from exc


def _sha256_and_scan(path: Path, relative_path: str) -> str:
    """Hash a file and fail if its public bytes contain a strong credential."""
    digest = hashlib.sha256()

    def hashing_chunks() -> Iterator[bytes]:
        """Update the digest while yielding each file chunk to the scanner."""
        for chunk in _iter_file_chunks(path):
            digest.update(chunk)
            yield chunk

    _scan_chunks(hashing_chunks(), relative_path)
    _scan_compressed_contents(path, relative_path)
    return digest.hexdigest()


def _hash_release_file(item: tuple[str, Path]) -> str:
    """Hash and scan one manifest item for bounded parallel execution."""
    relative_path, path = item
    return _sha256_and_scan(path, relative_path)


def _content_metadata(relative_path: str) -> dict[str, str]:
    """Derive upload and HTTP metadata for one public object."""
    guessed_type, guessed_encoding = mimetypes.guess_type(relative_path)
    suffix = Path(relative_path).suffix.lower()
    content_type = guessed_type or "application/octet-stream"
    raw_source = relative_path.startswith(("assets/mirrors/", "assets/verifiers/"))
    if suffix in {".py", ".sh", ".sql"} or (raw_source and suffix in {".js", ".ts", ".tsx", ".jsx"}):
        content_type = "text/plain; charset=utf-8"
    elif suffix in {".md", ".txt", ".csv", ".log"}:
        content_type = f"{content_type}; charset=utf-8"
    elif suffix == ".json" or relative_path.endswith(".json.gz"):
        content_type = "application/json; charset=utf-8"
    metadata = {"content_type": content_type}
    if guessed_encoding:
        metadata["content_encoding"] = guessed_encoding
    if relative_path.endswith((".html", ".htm")):
        metadata["cache_control"] = "no-store"
    elif relative_path.startswith("data/") or relative_path in {
        "assets/mirror_index.json",
        "assets/preview_index.json",
        "assets/verifier_source_index.json",
    }:
        metadata["cache_control"] = "public, max-age=300, must-revalidate"
    else:
        metadata["cache_control"] = "public, max-age=31536000, immutable"
    raw_executable = suffix in {".html", ".htm", ".js", ".mjs", ".svg"}
    if raw_source and raw_executable:
        metadata["content_disposition"] = "attachment"
        if suffix in {".html", ".htm", ".svg"}:
            metadata["content_type"] = "text/plain; charset=utf-8"
    return metadata


def _is_preview_bundle_entry(relative_path: str) -> bool:
    """Return whether a preview entry safely identifies one content-addressed bundle."""
    pure_path = PurePosixPath(relative_path)
    if not relative_path.startswith("assets/previews/"):
        return False
    if re.fullmatch(r"[0-9a-f]{64}", pure_path.parent.name, re.IGNORECASE) is None:
        return False
    lowered_name = pure_path.name.lower()
    is_html = lowered_name.endswith((".html", ".htm"))
    is_manifest = "manifest" in lowered_name and lowered_name.endswith(".json")
    return is_html or is_manifest


def _is_forbidden(relative_path: str, policy: dict[str, Any]) -> bool:
    """Return whether a path is outside the public export allow-scope."""
    if relative_path in set(policy.get("forbidden_exact_paths", [])):
        return True
    return any(relative_path.startswith(prefix) for prefix in policy.get("forbidden_path_prefixes", []))


def _validate_policy(policy: dict[str, Any]) -> tuple[set[str], set[str], set[str], set[str]]:
    """Validate publication categories and return their benchmark identifier sets."""
    if policy.get("schema_version") != 1:
        raise ExportError("Publication policy schema_version must be 1")
    categories = []
    for name in ("full", "metadata_only", "link_only", "exclude"):
        value = policy.get(name)
        if not isinstance(value, dict):
            raise ExportError(f"Publication policy {name!r} must be an object")
        categories.append(set(value))
    for index, category in enumerate(categories):
        for other in categories[index + 1:]:
            overlap = category & other
            if overlap:
                raise ExportError(f"Benchmark categories overlap: {sorted(overlap)}")
    full, metadata_only, link_only, excluded = categories
    expected_total = sum(int(policy["full"][bench_id]["expected_records"]) for bench_id in full)
    if expected_total != int(policy.get("expected_full_record_count", -1)):
        raise ExportError("expected_full_record_count does not match per-benchmark counts")
    return full, metadata_only, link_only, excluded


class PublicReleaseExporter:
    """Create a public release from one immutable internal release directory."""

    def __init__(
        self,
        source: Path,
        destination: Path,
        policy_path: Path,
        release_id: str,
        site_dir: Path | None = None,
    ) -> None:
        """Initialize paths, policy, and export accounting."""
        self.source = source.resolve(strict=True)
        self.destination = destination.absolute()
        self.policy_path = policy_path.resolve(strict=True)
        self.release_id = release_id
        self.site_dir = site_dir.resolve(strict=True) if site_dir is not None else None
        self.policy = _load_json_file(self.policy_path)
        self.full, self.metadata_only, self.link_only, self.excluded = _validate_policy(self.policy)
        self.public_benchmarks = self.full | self.metadata_only | self.link_only
        self.partial = self.destination.with_name(f"{self.destination.name}.partial-{os.getpid()}")
        self.queue: deque[str] = deque()
        self.queued: set[str] = set()
        self.exported: set[str] = set()
        self.expanded_preview_directories: set[str] = set()
        self.generated_files = 0
        self.hardlinked_files = 0
        self.redactions = 0
        self.site_files = 0
        self.source_catalog: dict[str, Any] = {}

    def run(self) -> dict[str, Any]:
        """Build the export in a partial directory and atomically publish it."""
        self._validate_pinned_sources()
        self._prepare_destination()
        self._export_catalog_and_benches()
        self._export_root_indexes()
        self._export_optional_metadata()
        self._drain_dependencies()
        self._export_site()
        manifest = self._build_manifest()
        self._write_generated_json("data/public_manifest.json", manifest, discover=False)
        self.partial.rename(self.destination)
        return manifest

    def validate_selection(self) -> dict[str, Any]:
        """Validate catalog coverage and expected record counts without writing files."""
        self._validate_pinned_sources()
        catalog = self._source_json("data/catalog.json")
        benchmarks = catalog.get("benchmarks")
        if not isinstance(benchmarks, list):
            raise ExportError("data/catalog.json must contain a benchmarks list")
        by_id = {str(item.get("id")): item for item in benchmarks if isinstance(item, dict)}
        self._validate_catalog_partition(set(by_id))
        total = 0
        for bench_id in sorted(self.full):
            shard = self._source_json(f"data/benches/{bench_id}.json")
            total += self._validate_full_shard(bench_id, shard)
        return {
            "catalog_benchmarks": len(self.public_benchmarks),
            "excluded_benchmarks": len(self.excluded),
            "full_benchmarks": len(self.full),
            "full_records": total,
            "release_id": self.release_id,
            "source": str(self.source),
        }

    def _validate_pinned_sources(self) -> None:
        """Pin the policy decision to exact catalog, full shards, and routing indexes."""
        pins = self.policy.get("pinned_source_sha256")
        if not isinstance(pins, dict):
            raise ExportError("Publication policy must define pinned_source_sha256")
        required_paths = {
            "data/catalog.json",
            *(f"data/benches/{bench_id}.json" for bench_id in self.full),
            *self.policy.get("required_root_indexes", []),
        }
        missing = required_paths - set(pins)
        if missing:
            raise ExportError(f"Publication policy is missing source pins: {sorted(missing)}")
        for relative_path, expected in sorted(pins.items()):
            if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
                raise ExportError(f"Invalid pinned SHA-256 for {relative_path}")
            digest = hashlib.sha256()
            for chunk in _iter_file_chunks(self._source_path(relative_path)):
                digest.update(chunk)
            if digest.hexdigest() != expected:
                raise ExportError(f"Pinned source changed: {relative_path}")

    def validate_closure(self) -> dict[str, Any]:
        """Resolve the full public reference closure without linking, copying, or hashing artifacts."""
        selection = self.validate_selection()
        for bench_id in sorted(self.full):
            shard = self._source_json(f"data/benches/{bench_id}.json")
            sanitized, _ = sanitize_json(shard)
            self._enqueue_references(sanitized)
        for relative_path in self.policy.get("required_root_indexes", []):
            source_index = self._source_json(relative_path)
            filtered = self._filtered_root_index(source_index)
            self._enqueue_references(filtered)
        seen: set[str] = set()
        logical_bytes = 0
        json_files = 0
        while self.queue:
            relative_path = self.queue.popleft()
            if relative_path in seen:
                continue
            source_path = self._source_path(relative_path)
            seen.add(relative_path)
            logical_bytes += source_path.stat().st_size
            if _is_preview_bundle_entry(relative_path):
                self._enqueue_directory(PurePosixPath(relative_path).parent.as_posix())
            if relative_path.endswith(".json"):
                json_files += 1
                value = _load_json_file(source_path)
                sanitized, _ = sanitize_json(value)
                self._enqueue_references(sanitized)
        selection.update(
            {
                "closure_files": len(seen),
                "closure_json_files": json_files,
                "closure_logical_bytes": logical_bytes,
            }
        )
        return selection

    def _prepare_destination(self) -> None:
        """Create a new empty partial directory without touching existing exports."""
        if not self.source.is_dir():
            raise ExportError(f"Source release is not a directory: {self.source}")
        if self.destination.exists() or self.destination.is_symlink():
            raise ExportError(f"Destination already exists: {self.destination}")
        if self.partial.exists() or self.partial.is_symlink():
            raise ExportError(f"Partial destination already exists: {self.partial}")
        destination_parent = self.destination.parent.resolve(strict=True)
        try:
            destination_parent.relative_to(self.source)
        except ValueError:
            pass
        else:
            raise ExportError("Destination cannot be created inside the immutable source release")
        self.partial.mkdir(mode=0o750)

    def _source_path(self, relative_path: str, allow_directory: bool = False) -> Path:
        """Resolve a data/assets path while rejecting symlinks and path escapes."""
        normalized = _normalize_reference(relative_path)
        if normalized is None or normalized != relative_path:
            raise SecurityError(f"Path is not canonical release-relative data/assets: {relative_path!r}")
        if _is_forbidden(normalized, self.policy):
            raise SecurityError(f"Forbidden public path requested: {normalized}")
        current = self.source
        for part in PurePosixPath(normalized).parts:
            current = current / part
            try:
                mode = current.lstat().st_mode
            except FileNotFoundError as exc:
                raise ExportError(f"Referenced source path is missing: {normalized}") from exc
            if stat.S_ISLNK(mode):
                raise SecurityError(f"Symlink is forbidden in public source path: {normalized}")
        if allow_directory and current.is_dir():
            return current
        if not current.is_file():
            raise ExportError(f"Referenced source path is not a regular file: {normalized}")
        return current

    def _destination_path(self, relative_path: str) -> Path:
        """Return a canonical path inside the partial export directory."""
        normalized = _normalize_reference(relative_path)
        if relative_path.startswith("site/"):
            if "\x00" in relative_path or "\\" in relative_path:
                raise SecurityError(f"Unsafe destination path: {relative_path!r}")
            pure_path = PurePosixPath(relative_path)
            if pure_path.is_absolute() or any(part in {"", ".", ".."} for part in pure_path.parts):
                raise SecurityError(f"Unsafe destination path: {relative_path!r}")
            normalized = relative_path
        if normalized is None or normalized != relative_path:
            raise SecurityError(f"Unsafe destination path: {relative_path!r}")
        target = self.partial.joinpath(*PurePosixPath(relative_path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def _source_json(self, relative_path: str) -> dict[str, Any]:
        """Load a source JSON object through the safe path resolver."""
        value = _load_json_file(self._source_path(relative_path))
        if not isinstance(value, dict):
            raise ExportError(f"Expected a JSON object in {relative_path}")
        return value

    def _validate_catalog_partition(self, catalog_ids: set[str]) -> None:
        """Ensure every source benchmark has exactly one fail-closed publication decision."""
        policy_ids = self.public_benchmarks | self.excluded
        missing_policy = catalog_ids - policy_ids
        missing_catalog = policy_ids - catalog_ids
        if missing_policy:
            raise ExportError(f"Catalog benchmarks missing from publication policy: {sorted(missing_policy)}")
        if missing_catalog:
            raise ExportError(f"Policy benchmarks missing from source catalog: {sorted(missing_catalog)}")

    def _validate_full_shard(self, bench_id: str, shard: dict[str, Any]) -> int:
        """Verify a full-public benchmark shard against its pinned policy count."""
        tasks = shard.get("tasks")
        if not isinstance(tasks, list):
            raise ExportError(f"Full benchmark {bench_id} has no tasks list")
        expected = int(self.policy["full"][bench_id]["expected_records"])
        declared = int(shard.get("record_count", -1))
        if declared != expected or len(tasks) != expected:
            raise ExportError(
                f"Full benchmark {bench_id} expected {expected} records, "
                f"found declared={declared}, tasks={len(tasks)}"
            )
        return expected

    def _public_catalog_entry(self, source_entry: dict[str, Any], mode: str) -> dict[str, Any]:
        """Annotate one catalog entry and zero non-redistributable task counts."""
        entry = copy.deepcopy(source_entry)
        bench_id = str(entry["id"])
        policy_entry = self.policy[mode][bench_id]
        entry["public_release"] = {
            "mode": mode,
            "reason_zh": policy_entry["reason_zh"],
            "tasks_included": mode == "full",
        }
        if mode != "full":
            entry["record_count"] = 0
            entry["expanded_from_official_source"] = False
            entry["stats"] = {"tracked_rows": 0, "tracked_tasks": 0}
            entry["coverage"] = {
                "mode": mode,
                "tracked_rows": 0,
                "tracked_tasks": 0,
            }
            entry["catalog_scope"] = {
                "mode": mode,
                "note": policy_entry["reason_zh"],
                "official_public_count": source_entry.get("record_count", 0),
                "unit": source_entry.get("catalog_scope", {}).get("unit", "tasks"),
            }
            entry.pop("repository_mirror", None)
        return entry

    def _metadata_stub(self, catalog_entry: dict[str, Any], mode: str) -> dict[str, Any]:
        """Build a zero-task shard containing only descriptive and provenance metadata."""
        allowed_fields = (
            "catalog_scope",
            "id",
            "license",
            "license_note",
            "license_url",
            "name",
            "references",
            "repository",
            "revision",
            "source_refs",
            "summary",
            "tags",
        )
        stub = {key: copy.deepcopy(catalog_entry[key]) for key in allowed_fields if key in catalog_entry}
        bench_id = str(catalog_entry["id"])
        stub.update(
            {
                "benchmark_id": bench_id,
                "benchmark_name": catalog_entry.get("name", bench_id),
                "generated_at": _utc_now(),
                "public_release": {
                    "mode": mode,
                    "reason_zh": self.policy[mode][bench_id]["reason_zh"],
                    "tasks_included": False,
                },
                "record_count": 0,
                "schema_version": "public-1.0",
                "tasks": [],
            }
        )
        return stub

    def _export_catalog_and_benches(self) -> None:
        """Generate the filtered catalog and enqueue full-public benchmark shards."""
        catalog = self._source_json("data/catalog.json")
        self.source_catalog = catalog
        source_entries = catalog.get("benchmarks")
        if not isinstance(source_entries, list):
            raise ExportError("data/catalog.json must contain a benchmarks list")
        by_id = {str(item.get("id")): item for item in source_entries if isinstance(item, dict)}
        self._validate_catalog_partition(set(by_id))
        public_entries = []
        full_records = 0
        for source_entry in source_entries:
            bench_id = str(source_entry.get("id"))
            if bench_id in self.excluded:
                continue
            if bench_id in self.full:
                mode = "full"
                shard = self._source_json(f"data/benches/{bench_id}.json")
                full_records += self._validate_full_shard(bench_id, shard)
                self._enqueue(f"data/benches/{bench_id}.json")
            elif bench_id in self.metadata_only:
                mode = "metadata_only"
                self._write_generated_json(
                    f"data/benches/{bench_id}.json",
                    self._metadata_stub(source_entry, mode),
                    discover=False,
                )
            else:
                mode = "link_only"
                self._write_generated_json(
                    f"data/benches/{bench_id}.json",
                    self._metadata_stub(source_entry, mode),
                    discover=False,
                )
            public_entries.append(self._public_catalog_entry(source_entry, mode))
        expected_total = int(self.policy["expected_full_record_count"])
        if full_records != expected_total:
            raise ExportError(f"Expected {expected_total} full-public records, found {full_records}")
        public_catalog = copy.deepcopy(catalog)
        public_catalog["benchmarks"] = public_entries
        public_catalog["generated_at"] = _utc_now()
        public_catalog["loading"] = {
            "note": "Public release uses lazy benchmark shards and content-addressed R2 artifacts.",
            "strategy": "index-first, benchmark shards on demand, long lists rendered incrementally",
        }
        public_catalog["public_release"] = {
            "excluded_benchmarks": len(self.excluded),
            "full_benchmarks": len(self.full),
            "link_only_benchmarks": len(self.link_only),
            "metadata_only_benchmarks": len(self.metadata_only),
            "policy_id": self.policy["policy_id"],
            "release_id": self.release_id,
        }
        public_catalog.pop("source_manifest_url", None)
        public_catalog["totals"] = {
            "benchmarks": len(public_entries),
            "expanded_benchmarks": len(self.full),
            "records": full_records,
        }
        self._write_generated_json("data/catalog.json", public_catalog, discover=False)

    def _filter_summary(self, summary: Any) -> dict[str, Any]:
        """Keep only by-benchmark summary facts that remain true after filtering."""
        if not isinstance(summary, dict):
            return {}
        result: dict[str, Any] = {}
        for key, value in summary.items():
            if key in INDEX_SUMMARY_BENCH_KEYS and isinstance(value, dict):
                result[key] = {bench_id: value[bench_id] for bench_id in sorted(self.full) if bench_id in value}
        bench_counts = result.get("bench_counts", {})
        if isinstance(bench_counts, dict):
            total = sum(int(value) for value in bench_counts.values())
            result["benches"] = len(bench_counts)
            result["records"] = total
            result["ready_records"] = total
        result["scope"] = "public-full-benchmarks-only"
        return result

    def _filtered_root_index(self, source_index: dict[str, Any]) -> dict[str, Any]:
        """Filter root records, per-benchmark shard routing, and summary metadata."""
        result = copy.deepcopy(source_index)
        records = source_index.get("records", [])
        if isinstance(records, list):
            result["records"] = [
                copy.deepcopy(record)
                for record in records
                if isinstance(record, dict) and str(record.get("bench_id")) in self.full
            ]
        shards = source_index.get("record_shards", {})
        by_bench = shards.get("by_bench", {}) if isinstance(shards, dict) else {}
        if not isinstance(by_bench, dict):
            raise ExportError("Root index record_shards.by_bench must be an object")
        result["record_shards"] = {
            "by_bench": {
                bench_id: copy.deepcopy(by_bench[bench_id])
                for bench_id in sorted(self.full)
                if bench_id in by_bench
            },
            "schema_version": shards.get("schema_version", 1),
        }
        missing = self.full - set(result["record_shards"]["by_bench"])
        if missing:
            raise ExportError(f"Root index is missing full-public benchmarks: {sorted(missing)}")
        result["summary"] = self._filter_summary(source_index.get("summary"))
        result["generated_at"] = _utc_now()
        result["public_release"] = {
            "policy_id": self.policy["policy_id"],
            "release_id": self.release_id,
        }
        for stale_key in (
            "mirror_index_sha256",
            "source_index_sha256",
            "source_manifest",
            "source_manifest_sha256",
        ):
            result.pop(stale_key, None)
        return result

    def _export_root_indexes(self) -> None:
        """Generate filtered routing indexes and discover their task-level shards."""
        for relative_path in self.policy.get("required_root_indexes", []):
            source_index = self._source_json(relative_path)
            filtered = self._filtered_root_index(source_index)
            self._write_generated_json(relative_path, filtered, discover=True)

    def _filtered_mirror_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Remove excluded benchmark policy and stale integrity data from mirror metadata."""
        result = copy.deepcopy(manifest)
        benchmarks = manifest.get("benchmarks", [])
        if not isinstance(benchmarks, list):
            raise ExportError("data/mirror_manifest.json benchmarks must be a list")
        result["benchmarks"] = [
            copy.deepcopy(item)
            for item in benchmarks
            if isinstance(item, dict) and str(item.get("id")) in self.public_benchmarks
        ]
        result["generated_at"] = _utc_now()
        result["integrity"] = {"benchmark_count": len(result["benchmarks"])}
        result["purpose"] = "Public KW Bench Library mirror and redistribution policy."
        result["public_release"] = {
            "policy_id": self.policy["policy_id"],
            "release_id": self.release_id,
        }
        return result

    def _export_optional_metadata(self) -> None:
        """Export explicitly allowed small metadata files, with manifest-specific filtering."""
        for relative_path in self.policy.get("optional_public_metadata", []):
            try:
                value = self._source_json(relative_path)
            except ExportError as exc:
                if "missing" in str(exc).lower():
                    continue
                raise
            if relative_path == "data/mirror_manifest.json":
                value = self._filtered_mirror_manifest(value)
            self._write_generated_json(relative_path, value, discover=False)

    def _enqueue(self, relative_path: str) -> None:
        """Queue one validated path for dependency export."""
        normalized = _normalize_reference(relative_path)
        if normalized is None:
            return
        if _is_forbidden(normalized, self.policy):
            raise SecurityError(f"JSON references forbidden path: {normalized}")
        scoped_benchmark = self._scoped_benchmark(normalized)
        if scoped_benchmark is not None and scoped_benchmark not in self.full:
            raise SecurityError(
                f"Full-public dependency crosses into non-full benchmark {scoped_benchmark!r}: "
                f"{normalized}"
            )
        if normalized not in self.queued and normalized not in self.exported:
            self.queue.append(normalized)
            self.queued.add(normalized)

    def _scoped_benchmark(self, relative_path: str) -> str | None:
        """Identify benchmark-owned path layouts that must remain in the full allowlist."""
        parts = PurePosixPath(relative_path).parts
        candidate = None
        if len(parts) >= 3 and parts[:2] == ("data", "benches"):
            candidate = PurePosixPath(parts[2]).stem
        elif len(parts) >= 3 and parts[:2] == ("data", "bench_details"):
            candidate = parts[2]
        elif len(parts) >= 4 and parts[:2] == ("assets", "index_shards"):
            candidate = parts[3]
        elif len(parts) >= 3 and parts[:2] == ("assets", "mirrors"):
            candidate = parts[2]
        elif len(parts) >= 4 and parts[:2] == ("assets", "verifiers"):
            candidate = parts[3]
        elif len(parts) >= 4 and parts[:3] == ("assets", "previews", "html"):
            candidate = parts[3]
        known_benchmarks = self.public_benchmarks | self.excluded
        return candidate if candidate in known_benchmarks else None

    def _enqueue_references(self, value: Any) -> None:
        """Queue real local references while ignoring missing logical filenames in task prose."""
        for relative_path, parent_key in iter_local_reference_candidates(value):
            try:
                self._source_path(relative_path)
            except SecurityError:
                raise
            except ExportError:
                if parent_key in STRICT_REFERENCE_KEYS or parent_key.endswith("_url"):
                    raise
                continue
            self._enqueue(relative_path)

    def _enqueue_directory(self, relative_directory: str) -> None:
        """Queue every regular file below a preview bundle directory."""
        if relative_directory in self.expanded_preview_directories:
            return
        self.expanded_preview_directories.add(relative_directory)
        directory = self._source_path(relative_directory, allow_directory=True)
        for root, directory_names, file_names in os.walk(directory, followlinks=False):
            root_path = Path(root)
            for name in sorted(directory_names):
                if (root_path / name).is_symlink():
                    raise SecurityError(f"Symlink is forbidden in preview bundle: {root_path / name}")
            for name in sorted(file_names):
                file_path = root_path / name
                if file_path.is_symlink():
                    raise SecurityError(f"Symlink is forbidden in preview bundle: {file_path}")
                if not file_path.is_file():
                    raise SecurityError(f"Non-regular file is forbidden in preview bundle: {file_path}")
                relative_path = file_path.relative_to(self.source).as_posix()
                self._enqueue(relative_path)

    def _write_generated_json(self, relative_path: str, value: Any, discover: bool) -> None:
        """Write sanitized generated JSON without ever modifying a hard-linked source file."""
        sanitized, count = sanitize_json(value)
        payload = _json_bytes(sanitized)
        if _is_sensitive_match(payload):
            raise SecurityError(f"Credential-shaped content survived JSON sanitization: {relative_path}")
        target = self._destination_path(relative_path)
        target.write_bytes(payload)
        os.chmod(target, 0o640)
        self.exported.add(relative_path)
        self.generated_files += 1
        self.redactions += count
        if discover:
            self._enqueue_references(sanitized)

    def _hardlink(self, relative_path: str, source_path: Path) -> None:
        """Hard-link one unchanged source file and fail instead of copying across filesystems."""
        target = self._destination_path(relative_path)
        try:
            os.link(source_path, target, follow_symlinks=False)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                raise ExportError("Source and destination must be on the same filesystem for hard-link export") from exc
            raise
        self.exported.add(relative_path)
        self.hardlinked_files += 1

    def _export_dependency(self, relative_path: str) -> None:
        """Export one referenced file, recursively sanitizing JSON and expanding preview bundles."""
        if relative_path in self.exported:
            return
        source_path = self._source_path(relative_path)
        if _is_preview_bundle_entry(relative_path):
            self._enqueue_directory(PurePosixPath(relative_path).parent.as_posix())
        if relative_path.endswith(".json"):
            value = _load_json_file(source_path)
            sanitized, count = sanitize_json(value)
            self._enqueue_references(sanitized)
            if count:
                self.redactions += count
                self._write_generated_json(relative_path, sanitized, discover=False)
            else:
                self._hardlink(relative_path, source_path)
        else:
            self._hardlink(relative_path, source_path)

    def _drain_dependencies(self) -> None:
        """Resolve every queued metadata and artifact dependency exactly once."""
        while self.queue:
            relative_path = self.queue.popleft()
            self._export_dependency(relative_path)

    def _export_site(self) -> None:
        """Copy an optional, bounded public UI bundle into the release under site/."""
        if self.site_dir is None:
            return
        if not self.site_dir.is_dir():
            raise ExportError(f"Public site directory is not a directory: {self.site_dir}")
        total_bytes = 0
        for path in sorted(self.site_dir.rglob("*")):
            if path.is_symlink():
                raise SecurityError(f"Symlink is forbidden in public site bundle: {path}")
            if not path.is_file():
                continue
            relative_site_path = path.relative_to(self.site_dir).as_posix()
            if PurePosixPath(relative_site_path).name == "ingestion.js":
                raise SecurityError("The public site bundle cannot contain ingestion.js")
            payload = path.read_bytes()
            if len(payload) > MAX_SITE_FILE_BYTES:
                raise ExportError(f"Public site file exceeds 25 MiB: {relative_site_path}")
            total_bytes += len(payload)
            self.site_files += 1
            if self.site_files > MAX_SITE_FILES or total_bytes > MAX_SITE_TOTAL_BYTES:
                raise ExportError("Public site bundle exceeds its 500-file or 64-MiB safety bound")
            for marker in FORBIDDEN_SITE_MARKERS:
                if marker.lower() in payload.lower():
                    label = marker.decode("ascii")
                    raise SecurityError(f"Forbidden internal UI marker {label!r} in site/{relative_site_path}")
            if _is_sensitive_match(payload):
                raise SecurityError(f"Credential-shaped content in public site file: {relative_site_path}")
            target_path = f"site/{relative_site_path}"
            target = self._destination_path(target_path)
            target.write_bytes(payload)
            os.chmod(target, 0o640)
            self.exported.add(target_path)
            self.generated_files += 1

    def _iter_partial_files(self) -> Iterator[tuple[str, Path]]:
        """Yield safe regular files in deterministic release-relative order."""
        for path in sorted(self.partial.rglob("*")):
            if path.is_symlink():
                raise SecurityError(f"Symlink appeared in partial export: {path}")
            if path.is_file():
                yield path.relative_to(self.partial).as_posix(), path

    def _build_manifest(self) -> dict[str, Any]:
        """Hash and security-scan every exported object and build upload metadata."""
        files = []
        total_bytes = 0
        paths = list(self._iter_partial_files())
        worker_count = min(4, max(1, os.cpu_count() or 1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            digests = executor.map(_hash_release_file, paths)
            hashed_paths = zip(paths, digests)
            for (relative_path, path), digest in hashed_paths:
                file_size = path.stat().st_size
                r2_key = f"releases/{self.release_id}/{relative_path}"
                if len(r2_key.encode("utf-8")) > 1024:
                    raise ExportError(f"R2 object key exceeds 1,024 UTF-8 bytes: {relative_path}")
                entry: dict[str, Any] = {
                    "path": relative_path,
                    "r2_key": r2_key,
                    "sha256": digest,
                    "size": file_size,
                }
                entry.update(_content_metadata(relative_path))
                files.append(entry)
                total_bytes += file_size
        policy_sha256 = hashlib.sha256(self.policy_path.read_bytes()).hexdigest()
        return {
            "files": files,
            "generated_at": _utc_now(),
            "policy": {
                "id": self.policy["policy_id"],
                "sha256": policy_sha256,
            },
            "publication": {
                "catalog_benchmarks": len(self.public_benchmarks),
                "excluded_benchmarks": sorted(self.excluded),
                "full_benchmarks": len(self.full),
                "full_records": int(self.policy["expected_full_record_count"]),
                "link_only_benchmarks": len(self.link_only),
                "metadata_only_benchmarks": len(self.metadata_only),
            },
            "release_id": self.release_id,
            "schema_version": 1,
            "self": {
                "path": "data/public_manifest.json",
                "r2_key": f"releases/{self.release_id}/data/public_manifest.json",
            },
            "source": {
                "catalog_generated_at": self.source_catalog.get("generated_at"),
                "immutable_directory": self.source.name,
            },
            "totals": {
                "files": len(files),
                "generated_files": self.generated_files,
                "hardlinked_files": self.hardlinked_files,
                "logical_bytes": total_bytes,
                "redactions": self.redactions,
                "site_files": self.site_files,
            },
        }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for validation or export."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Immutable internal release directory")
    parser.add_argument("--destination", type=Path, help="New same-filesystem public release directory")
    parser.add_argument("--policy", type=Path, required=True, help="Publication policy JSON")
    parser.add_argument("--release-id", required=True, help="Version used in R2 object keys")
    parser.add_argument(
        "--site-dir",
        type=Path,
        help="Optional bounded public UI directory copied into the release under site/",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate policy, catalog partition, and full benchmark counts without writing",
    )
    parser.add_argument(
        "--validate-closure",
        action="store_true",
        help="Additionally resolve every public data/assets reference without writing or hashing artifacts",
    )
    args = parser.parse_args(argv)
    if args.validate_only and args.validate_closure:
        parser.error("Choose only one of --validate-only and --validate-closure")
    if not (args.validate_only or args.validate_closure) and args.destination is None:
        parser.error("--destination is required unless a validation mode is used")
    return args


def main(argv: list[str] | None = None) -> int:
    """Run the public release exporter and print a non-sensitive JSON summary."""
    args = _parse_args(argv)
    destination = args.destination or Path.cwd() / ".unused-public-export"
    exporter = PublicReleaseExporter(
        args.source,
        destination,
        args.policy,
        args.release_id,
        site_dir=args.site_dir,
    )
    try:
        if args.validate_closure:
            result = exporter.validate_closure()
        elif args.validate_only:
            result = exporter.validate_selection()
        else:
            manifest = exporter.run()
            result = {
                "destination": str(exporter.destination),
                "publication": manifest["publication"],
                "release_id": manifest["release_id"],
                "totals": manifest["totals"],
            }
    except ExportError as exc:
        print(f"public export failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
