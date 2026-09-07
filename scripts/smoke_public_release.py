#!/usr/bin/env python3
"""Run fail-closed, anonymous HTTP smoke checks against a public release.

The checks intentionally use only GET requests without cookies, credentials, or
Cloudflare APIs. They validate the release pointer, representative task data,
published originals and previews, and the pinned handling of known upstream
object anomalies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlsplit

import requests


RANGE_BYTES = 32
DEFAULT_TIMEOUT_SECONDS = 60.0
FORBIDDEN_UI_MARKERS = (
    "Contributor Key",
    "contributor_key",
    "HF Token",
    "HF_TOKEN",
    "Hugging Face Token",
    "Authorization: Bearer",
    "needs_input",
    "/api/jobs",
    "/mnt/data/",
    "10.25.66.233",
    "localhost:8913",
    "127.0.0.1:8913",
    "登录",
)
PRIVATE_PATHS = (
    "/login",
    "/ingestion",
    "/api/jobs",
    "/_kwbl-upload/v1/health",
)


class SmokeFailure(RuntimeError):
    """Report one public-release behavior that failed closed."""


@dataclass(frozen=True)
class ObjectProbe:
    """Describe one public object whose body and HTTP metadata are fixed."""

    label: str
    path: str
    size: int
    sha256: str
    content_type: str
    magic: bytes
    require_preview_csp: bool = False


@dataclass(frozen=True)
class AnomalyProbe:
    """Describe one pinned upstream anomaly exposed only as an attachment."""

    label: str
    path: str
    sha256: str
    content_type: str
    magic: bytes
    integrity_handling: str
    task_id: str
    size: int = 32 * 1024 * 1024


@dataclass(frozen=True)
class TaskProbe:
    """Bind a representative task to its original and preview paths."""

    label: str
    benchmark_id: str
    expected_records: int
    task_id: str
    mirror_path: str
    preview_path: str


@dataclass(frozen=True)
class VariantCount:
    """Describe one expected task variant and unit-kind count."""

    benchmark_id: str
    variant_id: str
    unit_kind: str
    count: int


@dataclass(frozen=True)
class ReleaseSpec:
    """Hold the auditable acceptance contract for a public release family."""

    policy_id: str
    catalog_benchmarks: int
    expanded_benchmarks: int
    full_records: int
    task_probes: tuple[TaskProbe, ...]
    variant_counts: tuple[VariantCount, ...]
    object_probes: tuple[ObjectProbe, ...]
    anomaly_probes: tuple[AnomalyProbe, ...]


GDPVAL_XLSX = (
    "assets/mirrors/gdpval/reference/reference_files/"
    "9b3ff362d6764c61c29298ab132685ab/AR_Accrual-1.xlsx"
)
GDPVAL_PREVIEW = (
    "assets/previews/documents/c1/"
    "c1f3ab8ce2914468eed1474179d6d483c822aeae35277358812f78886f7290d1.pdf"
)
OFFICEQA_FULL_PDF = (
    "assets/mirrors/officeqa/full/treasury_bulletin_pdfs/"
    "treasury_bulletin_1998_06.pdf"
)
OFFICEQA_PRO_PDF = (
    "assets/mirrors/officeqa/pro_v2/pdfs/"
    "combined_statement__modern__2015__outlay.pdf"
)
WORKBUDDY_XLSX = (
    "assets/mirrors/workbuddybench-office/input/expanded/expanded/"
    "wb-bench-office-v1.0.tar.gz/wb-bench-office-v1.0/tasks/"
    "analyst-forecast-extract-L3-018/environment/workspace.tar.gz/"
    "input/company_dictionary.xlsx"
)
WORKBUDDY_PREVIEW = (
    "assets/previews/documents/79/"
    "797f87dda8a4760291170721b5a92466f0b0c196c749e36881b2712447f7b8f9.pdf"
)
ARTIFACTS_SOURCE = (
    "assets/mirrors/artifactsbench/candidate/official_candidates/"
    "claude-sonnet-4/task-0002.html.source.txt"
)
ARTIFACTS_PREVIEW = (
    "assets/previews/html/artifactsbench/"
    "fc8264dc616f0d9857e9/task-0002.html"
)


DEFAULT_SPEC = ReleaseSpec(
    policy_id="kw-bench-library-public-v2",
    catalog_benchmarks=31,
    expanded_benchmarks=29,
    full_records=10021,
    task_probes=(
        TaskProbe(
            "GDPval",
            "gdpval",
            220,
            "ee09d943-5a11-430a-b7a2-971b4e9b01b5",
            GDPVAL_XLSX,
            GDPVAL_PREVIEW,
        ),
        TaskProbe(
            "OfficeQA Full",
            "officeqa",
            340,
            "officeqa-full-uid0065",
            OFFICEQA_FULL_PDF,
            OFFICEQA_FULL_PDF,
        ),
        TaskProbe(
            "OfficeQA Pro V2",
            "officeqa",
            340,
            "officeqa-pro-v2-007",
            OFFICEQA_PRO_PDF,
            OFFICEQA_PRO_PDF,
        ),
        TaskProbe(
            "WorkBuddy Bench Office",
            "workbuddybench-office",
            50,
            "analyst-forecast-extract-L3-018",
            WORKBUDDY_XLSX,
            WORKBUDDY_PREVIEW,
        ),
        TaskProbe(
            "ArtifactsBench",
            "artifactsbench",
            1825,
            "artifactsbench-0002",
            ARTIFACTS_SOURCE,
            ARTIFACTS_PREVIEW,
        ),
    ),
    variant_counts=(
        VariantCount("officeqa", "full", "question", 246),
        VariantCount("officeqa", "pro_v2", "question", 90),
        VariantCount("officeqa", "protocol", "experiment_mode", 4),
    ),
    object_probes=(
        ObjectProbe(
            "GDPval XLSX original",
            GDPVAL_XLSX,
            9686,
            "c1f3ab8ce2914468eed1474179d6d483c822aeae35277358812f78886f7290d1",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            b"PK\x03\x04",
        ),
        ObjectProbe(
            "GDPval PDF preview",
            GDPVAL_PREVIEW,
            12582,
            "c97f7f9588c580a42af53b158dc44bd21a00f29b7b97dd2e91915e2cd31803a3",
            "application/pdf",
            b"%PDF-",
        ),
        ObjectProbe(
            "OfficeQA Full PDF",
            OFFICEQA_FULL_PDF,
            691540,
            "fc5e92b6f57950d14b2f46871845cf3648acc83617157620b86d8e94a3d59080",
            "application/pdf",
            b"%PDF-",
        ),
        ObjectProbe(
            "OfficeQA Pro V2 PDF",
            OFFICEQA_PRO_PDF,
            13009,
            "e915394d880a395dadff8b50329708a46ad527ea27c0bc69e5f6a7b78d3acb67",
            "application/pdf",
            b"%PDF-",
        ),
        ObjectProbe(
            "WorkBuddy XLSX original",
            WORKBUDDY_XLSX,
            6203,
            "797f87dda8a4760291170721b5a92466f0b0c196c749e36881b2712447f7b8f9",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            b"PK\x03\x04",
        ),
        ObjectProbe(
            "WorkBuddy PDF preview",
            WORKBUDDY_PREVIEW,
            33973,
            "59efe873454d957100ff00d5d8b1e984cb2841534ae41b39c7c35db8a7718bd1",
            "application/pdf",
            b"%PDF-",
        ),
        ObjectProbe(
            "ArtifactsBench inert HTML source",
            ARTIFACTS_SOURCE,
            29298,
            "6e8771321d366140896c80bfb0419baf7dc44c135eb98baa47232a1df91df46f",
            "text/plain; charset=utf-8",
            b"<html",
        ),
        ObjectProbe(
            "ArtifactsBench sandboxed HTML preview",
            ARTIFACTS_PREVIEW,
            29672,
            "2c75020e8cd7e080a95ebdd79077d45ca2ec1507782ec9212dcc6e1381ae1f86",
            "text/html; charset=utf-8",
            b"<html",
            require_preview_csp=True,
        ),
    ),
    anomaly_probes=(
        AnomalyProbe(
            "GDPval opaque ZIP",
            "assets/mirrors/gdpval/gold/deliverable_files/"
            "226c5ad480d4f5095cba55dbc1651caf/PrivateCrypMixV2.zip",
            "1a89088bcc431a2baae08a197a4f1be5337ba68d2f37f6c9c8a4dd9eef1888fe",
            "application/zip",
            b"PK\x03\x04",
            "opaque_archive_download",
            "0e386e32-df20-4d1f-b536-7159bc409ad5",
        ),
        AnomalyProbe(
            "GDPval truncated drum WAV",
            "assets/mirrors/gdpval/reference/reference_files/"
            "028fb83486152124cfecf2667c3cef37/DRUM REFERENCE TRACK.wav",
            "6d290de658f620fccd714a3406601fcf5a296e940f9f1a9f0bc2cee4399ce234",
            "audio/x-wav",
            b"RIFF",
            "truncated_media_download",
            "38889c3b-e3d4-49c8-816a-3cc8e5313aba",
        ),
        AnomalyProbe(
            "GDPval truncated bass WAV",
            "assets/mirrors/gdpval/reference/reference_files/"
            "073946a18125717bdad58178466039fd/State of Affairs_STEM_BASS.wav",
            "157c0500975f01c5256d7b8288d9c29096e69ca3f925b4b274249e57425009fa",
            "audio/x-wav",
            b"RIFF",
            "truncated_media_download",
            "4b894ae3-1f23-4560-b13d-07ed1132074e",
        ),
        AnomalyProbe(
            "GDPval truncated acoustic-guitar WAV",
            "assets/mirrors/gdpval/reference/reference_files/"
            "48836e54ef271e8fd1a301d3e20ea470/State of Affairs_STEM_ACGTRS.wav",
            "151356e97565977d9633140f8165f8c12f06f444f4c8b250716537ac818fb4ef",
            "audio/x-wav",
            b"RIFF",
            "truncated_media_download",
            "4b894ae3-1f23-4560-b13d-07ed1132074e",
        ),
    ),
)


def _require(condition: bool, message: str) -> None:
    """Raise a smoke failure unless one acceptance condition is true."""
    if not condition:
        raise SmokeFailure(message)


def _json_object(response: requests.Response, label: str) -> dict[str, Any]:
    """Decode one response as a JSON object with a scoped error."""
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError) as error:
        raise SmokeFailure(f"{label} did not return valid JSON: {error}") from error
    _require(isinstance(payload, dict), f"{label} JSON must be an object")
    return payload


def _record_paths(record: dict[str, Any]) -> set[str]:
    """Collect every exact public path carried by one index record."""
    paths = {
        value
        for field in (
            "view_path",
            "source_view_path",
            "preview_url",
            "pdf_url",
            "object_path",
        )
        if isinstance((value := record.get(field)), str) and value
    }
    deploy_paths = record.get("deploy_paths")
    if isinstance(deploy_paths, list):
        paths.update(value for value in deploy_paths if isinstance(value, str))
    return paths


class AnonymousClient:
    """Issue credential-free requests to one HTTPS origin."""

    def __init__(
        self,
        base_url: str,
        timeout: float,
        proxy: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """Validate the origin and initialize an empty HTTP session."""
        parsed = urlsplit(base_url)
        _require(parsed.scheme == "https", "Public smoke base URL must use HTTPS")
        _require(bool(parsed.netloc), "Public smoke base URL must include a host")
        _require(parsed.username is None and parsed.password is None, "Base URL must not contain credentials")
        _require(not parsed.query and not parsed.fragment, "Base URL must not contain a query or fragment")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_bust = str(time.time_ns())
        self.session = session or requests.Session()
        self.session.cookies.clear()
        self.session.headers.update(
            {
                "Accept-Encoding": "identity",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "User-Agent": "kw-bench-library-public-smoke/1",
            }
        )
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def get(self, path: str, headers: dict[str, str] | None = None) -> requests.Response:
        """Fetch one absolute public path without redirects, cookies, or auth."""
        _require(path.startswith("/"), f"Smoke path must be absolute: {path}")
        encoded_path = quote(path, safe="/._-~")
        self.session.cookies.clear()
        try:
            response = self.session.get(
                f"{self.base_url}{encoded_path}?kwbl_smoke={self.cache_bust}",
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.RequestException as error:
            raise SmokeFailure(f"GET {path} failed: {error}") from error
        _require(response.headers.get("WWW-Authenticate") is None, f"GET {path} requested authentication")
        return response

    def json(self, path: str, label: str) -> dict[str, Any]:
        """Fetch one successful JSON object."""
        response = self.get(path)
        _require(response.status_code == 200, f"{label} returned HTTP {response.status_code}")
        _require("set-cookie" not in response.headers, f"{label} attempted to set a cookie")
        return _json_object(response, label)


class PublicReleaseSmoke:
    """Execute the complete anonymous public-release acceptance contract."""

    def __init__(
        self,
        client: AnonymousClient,
        expected_release_id: str,
        spec: ReleaseSpec = DEFAULT_SPEC,
    ) -> None:
        """Keep the immutable expected release pointer and validation spec."""
        _require(bool(expected_release_id), "Expected release ID must not be empty")
        self.client = client
        self.expected_release_id = expected_release_id
        self.spec = spec
        self.json_cache: dict[str, dict[str, Any]] = {}
        self.completed_checks: list[str] = []

    def _json(self, path: str, label: str) -> dict[str, Any]:
        """Fetch and cache one JSON object by path."""
        if path not in self.json_cache:
            self.json_cache[path] = self.client.json(f"/{path}", label)
        return self.json_cache[path]

    def _check_home(self) -> None:
        """Verify that the public UI is anonymous and contains no operator UI."""
        for path, expected_type in (
            ("/", "text/html; charset=utf-8"),
            ("/app.js", "text/javascript; charset=utf-8"),
            ("/public-config.js", "text/javascript; charset=utf-8"),
        ):
            response = self.client.get(path)
            _require(response.status_code == 200, f"Public UI {path} returned HTTP {response.status_code}")
            _require(response.headers.get("Content-Type", "").lower() == expected_type, f"Unexpected MIME for {path}")
            _require("set-cookie" not in response.headers, f"Public UI {path} attempted to set a cookie")
            text = response.content.decode("utf-8", errors="replace")
            for marker in FORBIDDEN_UI_MARKERS:
                _require(marker.casefold() not in text.casefold(), f"Public UI {path} exposes {marker!r}")

        home = self.client.get("/")
        _require(b"<title>KW Bench Library</title>" in home.content, "Public UI title is missing")
        content_security_policy = home.headers.get("Content-Security-Policy", "")
        _require("default-src 'self'" in content_security_policy, "Public UI CSP is missing")

        for path in PRIVATE_PATHS:
            response = self.client.get(path)
            _require(response.status_code == 404, f"Private path {path} returned HTTP {response.status_code}")
            _require("set-cookie" not in response.headers, f"Private path {path} attempted to set a cookie")
        self.completed_checks.append("anonymous public UI")

    def _check_catalog(self) -> dict[str, dict[str, Any]]:
        """Validate release metadata, catalog counts, and benchmark shards."""
        catalog = self._json("data/catalog.json", "catalog")
        totals = catalog.get("totals")
        publication = catalog.get("public_release")
        _require(isinstance(totals, dict), "Catalog totals are missing")
        _require(isinstance(publication, dict), "Catalog public_release is missing")
        expected_totals = {
            "benchmarks": self.spec.catalog_benchmarks,
            "expanded_benchmarks": self.spec.expanded_benchmarks,
            "records": self.spec.full_records,
        }
        for field, expected in expected_totals.items():
            _require(totals.get(field) == expected, f"Catalog {field} is not {expected}")
        _require(
            publication.get("release_id") == self.expected_release_id,
            "Catalog points at an unexpected release",
        )
        _require(publication.get("policy_id") == self.spec.policy_id, "Catalog policy ID is unexpected")
        _require(
            publication.get("full_benchmarks") == self.spec.expanded_benchmarks,
            "Catalog full-benchmark count is unexpected",
        )
        _require(
            publication.get("link_only_benchmarks")
            == self.spec.catalog_benchmarks - self.spec.expanded_benchmarks,
            "Catalog link-only count is unexpected",
        )
        _require(publication.get("metadata_only_benchmarks") == 0, "Catalog metadata-only count is unexpected")
        benchmarks = catalog.get("benchmarks")
        _require(isinstance(benchmarks, list), "Catalog benchmarks must be an array")
        _require(len(benchmarks) == self.spec.catalog_benchmarks, "Catalog benchmark-array length is wrong")

        shards: dict[str, dict[str, Any]] = {}
        expected_by_benchmark: dict[str, int] = {}
        for probe in self.spec.task_probes:
            expected_by_benchmark[probe.benchmark_id] = probe.expected_records
        for benchmark_id, expected_records in expected_by_benchmark.items():
            shard = self._json(f"data/benches/{benchmark_id}.json", f"{benchmark_id} task shard")
            _require(shard.get("benchmark_id") == benchmark_id, f"Wrong benchmark ID in {benchmark_id} shard")
            _require(shard.get("record_count") == expected_records, f"Wrong record count for {benchmark_id}")
            tasks = shard.get("tasks")
            _require(isinstance(tasks, list), f"{benchmark_id} tasks must be an array")
            _require(len(tasks) == expected_records, f"Wrong task-array length for {benchmark_id}")
            shards[benchmark_id] = shard

        for probe in self.spec.task_probes:
            tasks = shards[probe.benchmark_id]["tasks"]
            _require(
                any(isinstance(task, dict) and task.get("id") == probe.task_id for task in tasks),
                f"Representative task is missing: {probe.label} / {probe.task_id}",
            )

        for variant in self.spec.variant_counts:
            tasks = shards[variant.benchmark_id]["tasks"]
            actual = sum(
                isinstance(task, dict)
                and task.get("variant_id") == variant.variant_id
                and task.get("unit_kind") == variant.unit_kind
                for task in tasks
            )
            _require(
                actual == variant.count,
                f"Wrong {variant.benchmark_id}/{variant.variant_id}/{variant.unit_kind} count: {actual}",
            )
        self.completed_checks.append("release and task counts")
        return shards

    def _records_for_task(
        self,
        root_index: dict[str, Any],
        kind: str,
        benchmark_id: str,
        task_id: str,
    ) -> list[dict[str, Any]]:
        """Load root and optional task-shard records for one benchmark task."""
        raw_records = root_index.get("records")
        _require(isinstance(raw_records, list), f"{kind} root records must be an array")
        records = [record for record in raw_records if isinstance(record, dict)]
        record_shards = root_index.get("record_shards", {})
        if not isinstance(record_shards, dict):
            return records
        by_bench = record_shards.get("by_bench", {})
        bench = by_bench.get(benchmark_id, {}) if isinstance(by_bench, dict) else {}
        tasks = bench.get("tasks", {}) if isinstance(bench, dict) else {}
        shard_path = tasks.get(task_id) if isinstance(tasks, dict) else None
        if isinstance(shard_path, str) and shard_path:
            shard = self._json(shard_path, f"{kind} index shard for {benchmark_id}/{task_id}")
            shard_records = shard.get("records")
            _require(isinstance(shard_records, list), f"{kind} task records must be an array")
            records.extend(record for record in shard_records if isinstance(record, dict))
        return records

    @staticmethod
    def _matching_record(
        records: list[dict[str, Any]],
        path: str,
        task_id: str,
    ) -> dict[str, Any] | None:
        """Return the first task-bound index record naming one public path."""
        for record in records:
            task_ids = record.get("task_ids")
            has_task = record.get("task_id") == task_id or (
                isinstance(task_ids, list) and task_id in task_ids
            )
            if has_task and path in _record_paths(record):
                return record
        return None

    def _check_indexes(self) -> None:
        """Verify representative mappings and pinned anomaly presentation."""
        mirror_index = self._json("assets/mirror_index.json", "mirror root index")
        preview_index = self._json("assets/preview_index.json", "preview root index")
        for label, index in (("mirror", mirror_index), ("preview", preview_index)):
            public_release = index.get("public_release")
            _require(isinstance(public_release, dict), f"{label} index public_release is missing")
            _require(
                public_release.get("release_id") == self.expected_release_id,
                f"{label} index points at an unexpected release",
            )

        for probe in self.spec.task_probes:
            mirror_records = self._records_for_task(
                mirror_index,
                "mirror",
                probe.benchmark_id,
                probe.task_id,
            )
            preview_records = self._records_for_task(
                preview_index,
                "preview",
                probe.benchmark_id,
                probe.task_id,
            )
            _require(
                self._matching_record(mirror_records, probe.mirror_path, probe.task_id) is not None,
                f"Mirror index does not bind {probe.label} to its original",
            )
            _require(
                self._matching_record(preview_records, probe.preview_path, probe.task_id) is not None,
                f"Preview index does not bind {probe.label} to its preview",
            )

        mirror_records = [record for record in mirror_index["records"] if isinstance(record, dict)]
        preview_records = [record for record in preview_index["records"] if isinstance(record, dict)]
        for anomaly in self.spec.anomaly_probes:
            mirror_record = self._matching_record(mirror_records, anomaly.path, anomaly.task_id)
            preview_record = self._matching_record(preview_records, anomaly.path, anomaly.task_id)
            _require(mirror_record is not None, f"Mirror warning is missing for {anomaly.label}")
            _require(preview_record is not None, f"Preview warning is missing for {anomaly.label}")
            for label, record in (("mirror", mirror_record), ("preview", preview_record)):
                _require(
                    record.get("integrity_status") == "upstream-anomaly-pinned-v1",
                    f"{label} integrity status is wrong for {anomaly.label}",
                )
                _require(
                    record.get("integrity_handling") == anomaly.integrity_handling,
                    f"{label} integrity handling is wrong for {anomaly.label}",
                )
                _require(bool(record.get("integrity_note_zh")), f"{label} warning is empty for {anomaly.label}")
            _require(
                preview_record.get("preview_kind") == "download_only",
                f"Anomaly is not download-only: {anomaly.label}",
            )
            _require(preview_record.get("source_size") == anomaly.size, f"Wrong anomaly size: {anomaly.label}")
            _require(
                preview_record.get("source_sha256") == anomaly.sha256,
                f"Wrong anomaly SHA in preview index: {anomaly.label}",
            )
        self.completed_checks.append("mirror and preview index mappings")

    def _check_range_response(
        self,
        label: str,
        path: str,
        size: int,
        sha256: str,
        content_type: str,
        magic: bytes,
        require_attachment: bool = False,
        require_preview_csp: bool = False,
    ) -> bytes:
        """Validate one 32-byte response without downloading a large object."""
        response = self.client.get(f"/{path}", headers={"Range": f"bytes=0-{RANGE_BYTES - 1}"})
        _require(response.status_code == 206, f"Range request failed for {label}: HTTP {response.status_code}")
        _require(len(response.content) == RANGE_BYTES, f"Range body length is wrong for {label}")
        _require(response.content.startswith(magic), f"File magic is wrong for {label}")
        _require(
            response.headers.get("Content-Range") == f"bytes 0-{RANGE_BYTES - 1}/{size}",
            f"Content-Range is wrong for {label}",
        )
        _require(response.headers.get("Content-Length") == str(RANGE_BYTES), f"Content-Length is wrong for {label}")
        _require(response.headers.get("Accept-Ranges") == "bytes", f"Accept-Ranges is wrong for {label}")
        _require(
            response.headers.get("X-Content-Type-Options", "").lower() == "nosniff",
            f"nosniff header is missing for {label}",
        )
        _require(
            response.headers.get("Cross-Origin-Resource-Policy", "").lower() == "same-origin",
            f"Cross-Origin-Resource-Policy is wrong for {label}",
        )
        _require(response.headers.get("X-Content-SHA256") == sha256, f"SHA header is wrong for {label}")
        _require(response.headers.get("Content-Type", "").lower() == content_type, f"MIME is wrong for {label}")
        if require_attachment:
            disposition = response.headers.get("Content-Disposition", "").lower()
            _require(disposition.startswith("attachment"), f"Attachment policy is missing for {label}")
        if require_preview_csp:
            content_security_policy = response.headers.get("Content-Security-Policy", "")
            _require("sandbox allow-scripts" in content_security_policy, f"Preview sandbox is missing for {label}")
            _require("connect-src 'none'" in content_security_policy, f"Preview network lock is missing for {label}")
            _require("allow-same-origin" not in content_security_policy, f"Preview allows same-origin for {label}")
        return response.content

    def _check_objects(self) -> None:
        """Validate representative bodies plus range-only anomaly objects."""
        for probe in self.spec.object_probes:
            ranged_body = self._check_range_response(
                probe.label,
                probe.path,
                probe.size,
                probe.sha256,
                probe.content_type,
                probe.magic,
                require_preview_csp=probe.require_preview_csp,
            )
            response = self.client.get(f"/{probe.path}")
            _require(response.status_code == 200, f"Full object request failed for {probe.label}")
            _require(len(response.content) == probe.size, f"Full body size is wrong for {probe.label}")
            _require(response.content.startswith(ranged_body), f"Range body differs from full body for {probe.label}")
            digest = hashlib.sha256(response.content).hexdigest()
            _require(digest == probe.sha256, f"Full body SHA-256 is wrong for {probe.label}")

        for anomaly in self.spec.anomaly_probes:
            self._check_range_response(
                anomaly.label,
                anomaly.path,
                anomaly.size,
                anomaly.sha256,
                anomaly.content_type,
                anomaly.magic,
                require_attachment=True,
            )
        self.completed_checks.append("representative originals and previews")

    def run(self) -> dict[str, Any]:
        """Run all checks and return a machine-readable success summary."""
        self._check_home()
        self._check_catalog()
        self._check_indexes()
        self._check_objects()
        return {
            "ok": True,
            "base_url": self.client.base_url,
            "release_id": self.expected_release_id,
            "checks": self.completed_checks,
            "benchmarks_checked": sorted({probe.benchmark_id for probe in self.spec.task_probes}),
            "representative_tasks": len(self.spec.task_probes),
            "objects_full_hash_checked": len(self.spec.object_probes),
            "upstream_anomalies_checked": len(self.spec.anomaly_probes),
        }


def smoke_public_release(
    base_url: str,
    expected_release_id: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    proxy: str | None = None,
    spec: ReleaseSpec = DEFAULT_SPEC,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Run the anonymous smoke contract against one public origin."""
    _require(timeout > 0, "Timeout must be positive")
    client = AnonymousClient(base_url, timeout, proxy=proxy, session=session)
    return PublicReleaseSmoke(client, expected_release_id, spec=spec).run()


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://benchlibrary.com")
    parser.add_argument("--expected-release-id", required=True)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--proxy", help="Optional explicit HTTP(S) proxy URL")
    return parser


def main() -> int:
    """Run the CLI and return a process exit status."""
    arguments = build_parser().parse_args()
    try:
        result = smoke_public_release(
            arguments.base_url,
            arguments.expected_release_id,
            timeout=arguments.timeout,
            proxy=arguments.proxy,
        )
    except SmokeFailure as error:
        print(f"Public release smoke failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
