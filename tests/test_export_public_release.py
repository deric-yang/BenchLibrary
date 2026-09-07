"""Tests for the fail-closed public release exporter."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

from scripts.export_public_release import (
    ExportError,
    PublicReleaseExporter,
    SecurityError,
    _sha256_and_scan,
    _text_line_count,
    sanitize_json,
)


def _write_json(path: Path, value: Any) -> None:
    """Write compact fixture JSON and create its parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class PublicReleaseExporterTest(unittest.TestCase):
    """Exercise policy filtering, dependency export, and security invariants."""

    def setUp(self) -> None:
        """Create an isolated source release, policy, and public UI fixture."""
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "immutable-release"
        self.destination = self.root / "public-release"
        self.site = self.root / "public-site"
        self.policy_path = self.root / "policy.json"
        self.preview_object_id = "a" * 64
        self.source.mkdir()
        self.site.mkdir()
        self.site.joinpath("index.html").write_text("<h1>KW Bench Library</h1>", encoding="utf-8")
        self.site.joinpath("app.js").write_text("globalThis.PUBLIC_MODE = true;", encoding="utf-8")
        self.policy = {
            "schema_version": 1,
            "policy_id": "fixture-public-v1",
            "expected_full_record_count": 1,
            "full": {
                "full-bench": {
                    "expected_records": 1,
                    "reason_zh": "fixture full",
                }
            },
            "metadata_only": {"metadata-bench": {"reason_zh": "fixture metadata"}},
            "link_only": {"link-bench": {"reason_zh": "fixture link"}},
            "exclude": {"closed-bench": {"reason_zh": "fixture excluded"}},
            "required_root_indexes": [
                "assets/mirror_index.json",
                "assets/preview_index.json",
                "assets/verifier_source_index.json",
            ],
            "optional_public_metadata": [
                "data/kw_coverage.json",
                "data/mirror_manifest.json",
            ],
            "upstream_integrity_exceptions": {},
            "forbidden_path_prefixes": ["corpus/", "ingestion/", "work/"],
            "forbidden_exact_paths": ["assets/deploy_manifest.json", "data/source_manifest.json"],
        }
        _write_json(self.policy_path, self.policy)
        self._write_source_release()
        self._refresh_policy_pins()

    def tearDown(self) -> None:
        """Remove the temporary fixture tree."""
        self.temporary_directory.cleanup()

    def _catalog_entry(self, bench_id: str, count: int) -> dict[str, Any]:
        """Return one realistic-enough catalog entry for a fixture benchmark."""
        return {
            "catalog_scope": {"unit": "tasks"},
            "coverage": {"tracked_tasks": count},
            "id": bench_id,
            "license": "fixture-license",
            "name": bench_id,
            "record_count": count,
            "references": [{"url": f"https://example.test/{bench_id}"}],
            "shard_url": f"data/benches/{bench_id}.json",
            "stats": {"tracked_tasks": count},
            "summary": f"Summary for {bench_id}",
        }

    def _root_index(self, kind: str, dependency: str) -> dict[str, Any]:
        """Return a root index containing allowed and disallowed routing entries."""
        return {
            "generated_at": "2026-09-01T00:00:00+00:00",
            "record_shards": {
                "by_bench": {
                    "closed-bench": {"tasks": {"closed": "assets/private/closed.json"}},
                    "full-bench": {"tasks": {"task-1": dependency}},
                    "metadata-bench": {"tasks": {"hidden": "assets/private/metadata.json"}},
                },
                "schema_version": 1,
            },
            "records": [
                {"bench_id": "full-bench", "task_id": "task-1"},
                {"bench_id": "metadata-bench", "task_id": "hidden"},
            ],
            "schema_version": 1,
            "source_index_sha256": "stale",
            "summary": {
                "bench_counts": {
                    "closed-bench": 99,
                    "full-bench": 1,
                    "metadata-bench": 99,
                },
                "kind_counts": {kind: 199},
                "records": 199,
            },
        }

    def _write_source_release(self) -> None:
        """Populate the immutable fixture with catalog, indexes, and referenced artifacts."""
        entries = [
            self._catalog_entry("full-bench", 1),
            self._catalog_entry("metadata-bench", 8),
            self._catalog_entry("link-bench", 9),
            self._catalog_entry("closed-bench", 10),
        ]
        _write_json(
            self.source / "data/catalog.json",
            {
                "benchmarks": entries,
                "generated_at": "2026-09-01T00:00:00+00:00",
                "schema_version": "2.1",
                "source_manifest_url": "data/source_manifest.json",
                "totals": {"benchmarks": 4, "expanded_benchmarks": 4, "records": 28},
            },
        )
        _write_json(
            self.source / "data/benches/full-bench.json",
            {
                "benchmark_id": "full-bench",
                "record_count": 1,
                "tasks": [
                    {
                        "api_key": "fixture-secret-value",
                        "artifact_url": "assets/mirrors/full-bench/task-1/result.txt",
                        "internal_location": "/mnt/data/private/task-1",
                        "task_id": "task-1",
                    }
                ],
            },
        )
        mirror_shard = "assets/index_shards/mirror/full-bench/tasks-0000.json"
        preview_shard = "assets/index_shards/preview/full-bench/tasks-0000.json"
        verifier_shard = "assets/index_shards/verifier/full-bench/tasks-0000.json"
        _write_json(
            self.source / "assets/mirror_index.json",
            self._root_index("input", mirror_shard),
        )
        _write_json(
            self.source / "assets/preview_index.json",
            self._root_index("html", preview_shard),
        )
        _write_json(
            self.source / "assets/verifier_source_index.json",
            self._root_index("source", verifier_shard),
        )
        _write_json(
            self.source / mirror_shard,
            {"records": [{"view_path": "assets/mirrors/full-bench/task-1/result.txt"}]},
        )
        _write_json(
            self.source / preview_shard,
            {
                "records": [
                    {
                        "preview_url": (
                            "assets/previews/full-bench/"
                            f"{self.preview_object_id}/index.html"
                        )
                    }
                ]
            },
        )
        _write_json(
            self.source / verifier_shard,
            {"records": [{"source_url": "assets/verifiers/full-bench/task-1/check.py"}]},
        )
        artifact = self.source / "assets/mirrors/full-bench/task-1/result.txt"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("public fixture artifact", encoding="utf-8")
        preview = self.source / f"assets/previews/full-bench/{self.preview_object_id}"
        preview.mkdir(parents=True)
        preview.joinpath("index.html").write_text("<link rel='stylesheet' href='style.css'>", encoding="utf-8")
        preview.joinpath("style.css").write_text("body { color: black; }", encoding="utf-8")
        verifier = self.source / "assets/verifiers/full-bench/task-1/check.py"
        verifier.parent.mkdir(parents=True)
        verifier.write_text("def check():\n    return True\n", encoding="utf-8")
        _write_json(self.source / "data/kw_coverage.json", {"items": []})
        _write_json(
            self.source / "data/mirror_manifest.json",
            {
                "benchmarks": [{"id": entry["id"]} for entry in entries],
                "integrity": {"base_manifest_sha256": "stale"},
            },
        )

    def _refresh_policy_pins(self) -> None:
        """Pin the fixture policy to its exact allowed source shards and indexes."""
        paths = {
            "data/catalog.json",
            "data/benches/full-bench.json",
            *self.policy["required_root_indexes"],
        }
        self.policy["pinned_source_sha256"] = {
            relative_path: hashlib.sha256((self.source / relative_path).read_bytes()).hexdigest()
            for relative_path in sorted(paths)
        }
        _write_json(self.policy_path, self.policy)

    def _add_text_preview_bundle(self) -> tuple[str, bytes, bytes, str, str]:
        """Add a two-schema text bundle containing two JWT-shaped fixture strings."""
        object_id = "b" * 64
        bundle_path = f"assets/previews/text/{object_id[:2]}/{object_id}"
        first_chunk_path = f"{bundle_path}/chunk-00001.txt"
        second_chunk_path = f"{bundle_path}/chunk-00002.txt"
        first_token = f"eyJ{'A' * 12}.{'B' * 12}.{'C' * 12}"
        second_token = f"eyJ{'D' * 12}.{'E' * 12}.{'F' * 12}"
        first_payload = f"first\n{first_token}\n{second_token}\nlast\n".encode()
        second_payload = "alpha\r\nbeta\r\n".encode()
        first_chunk = self.source / first_chunk_path
        first_chunk.parent.mkdir(parents=True)
        first_chunk.write_bytes(first_payload)
        (self.source / second_chunk_path).write_bytes(second_payload)
        manifest = {
            "chunks": [
                {"bytes": len(first_payload), "index": 0, "lines": 4, "url": first_chunk_path},
                {"bytes": len(second_payload), "index": 1, "lines": 2, "url": second_chunk_path},
            ],
            "preview_kind": "text_chunks",
            "schema_version": 1,
            "text_chunks": [
                {
                    "bytes": len(first_payload),
                    "end_line": 4,
                    "start_line": 1,
                    "url": first_chunk_path,
                },
                {
                    "bytes": len(second_payload),
                    "end_line": 6,
                    "start_line": 5,
                    "url": second_chunk_path,
                },
            ],
            "total_chunks": 2,
            "total_lines": 6,
        }
        _write_json(self.source / bundle_path / "manifest.json", manifest)
        preview_shard = self.source / "assets/index_shards/preview/full-bench/tasks-0000.json"
        preview_index = json.loads(preview_shard.read_text(encoding="utf-8"))
        preview_index["records"].append(
            {
                "preview_url": f"{bundle_path}/manifest.json",
                "text_chunks": copy.deepcopy(manifest["text_chunks"]),
                "total_chunks": 2,
                "total_lines": 6,
            }
        )
        _write_json(preview_shard, preview_index)
        return bundle_path, first_payload, second_payload, first_token, second_token

    def _export(self) -> dict[str, Any]:
        """Run the fixture export and return its in-memory manifest."""
        exporter = PublicReleaseExporter(
            self.source,
            self.destination,
            self.policy_path,
            "fixture-release",
            site_dir=self.site,
        )
        return exporter.run()

    def _reference_full_dependency(self, relative_path: str) -> None:
        """Reference one strict dependency from the full fixture shard and refresh its pin."""
        shard_path = self.source / "data/benches/full-bench.json"
        shard = json.loads(shard_path.read_text(encoding="utf-8"))
        shard["tasks"][0]["catalog_url"] = relative_path
        _write_json(shard_path, shard)
        self._refresh_policy_pins()

    def test_exports_filtered_public_release_with_hardlinks(self) -> None:
        """Full data is linked, restricted benches are stubs, and indexes are filtered."""
        manifest = self._export()
        catalog = json.loads((self.destination / "data/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in catalog["benchmarks"]], [
            "full-bench",
            "metadata-bench",
            "link-bench",
        ])
        self.assertEqual(catalog["totals"], {"benchmarks": 3, "expanded_benchmarks": 1, "records": 1})
        for bench_id in ("metadata-bench", "link-bench"):
            shard = json.loads((self.destination / f"data/benches/{bench_id}.json").read_text(encoding="utf-8"))
            self.assertEqual(shard["tasks"], [])
            self.assertEqual(shard["record_count"], 0)
        full_shard = json.loads(
            (self.destination / "data/benches/full-bench.json").read_text(encoding="utf-8")
        )
        self.assertEqual(full_shard["tasks"][0]["api_key"], "[REDACTED]")
        self.assertEqual(full_shard["tasks"][0]["internal_location"], "[INTERNAL LOCATION REDACTED]")
        for index_name in ("mirror_index", "preview_index", "verifier_source_index"):
            index = json.loads((self.destination / f"assets/{index_name}.json").read_text(encoding="utf-8"))
            self.assertEqual(set(index["record_shards"]["by_bench"]), {"full-bench"})
            self.assertEqual(index["summary"]["bench_counts"], {"full-bench": 1})
            self.assertNotIn("source_index_sha256", index)
        artifact_source = self.source / "assets/mirrors/full-bench/task-1/result.txt"
        artifact_public = self.destination / "assets/mirrors/full-bench/task-1/result.txt"
        self.assertEqual(os.stat(artifact_source).st_ino, os.stat(artifact_public).st_ino)
        preview_css = self.destination / f"assets/previews/full-bench/{self.preview_object_id}/style.css"
        self.assertTrue(preview_css.is_file())
        self.assertTrue((self.destination / "site/index.html").is_file())
        self.assertEqual(manifest["publication"]["full_records"], 1)
        self.assertGreaterEqual(manifest["totals"]["redactions"], 2)
        self.assertEqual(manifest["totals"]["site_files"], 2)
        manifest_paths = {item["path"] for item in manifest["files"]}
        self.assertIn("site/app.js", manifest_paths)
        self.assertNotIn("assets/private/closed.json", manifest_paths)

    def test_exports_valid_json_lines_named_json_without_rewriting(self) -> None:
        """A JSON-suffixed JSON Lines dependency is exported byte-for-byte when clean."""
        relative_path = "assets/mirrors/full-bench/catalog/records.json"
        source_path = self.source / relative_path
        source_path.parent.mkdir(parents=True)
        payload = b'{"id":1,"label":"first"}\n\n{"id":2,"label":"second"}\n'
        source_path.write_bytes(payload)
        self._reference_full_dependency(relative_path)

        self._export()

        public_path = self.destination / relative_path
        self.assertEqual(public_path.read_bytes(), payload)
        self.assertEqual(public_path.stat().st_ino, source_path.stat().st_ino)

    def test_redacts_json_lines_credentials_with_copy_on_write(self) -> None:
        """Every JSON Lines value is sanitized and credential-bearing bytes are replaced."""
        relative_path = "assets/mirrors/full-bench/catalog/credentials.json"
        source_path = self.source / relative_path
        source_path.parent.mkdir(parents=True)
        token = "hf_" + "x" * 32
        source_payload = (
            '{"api_key":"fixture-secret","id":1}\n'
            f'{{"id":2,"note":"temporary {token}"}}\n'
        ).encode()
        source_path.write_bytes(source_payload)
        source_inode = source_path.stat().st_ino
        self._reference_full_dependency(relative_path)

        manifest = self._export()

        public_path = self.destination / relative_path
        public_payload = public_path.read_bytes()
        public_values = [json.loads(line) for line in public_payload.splitlines()]
        self.assertEqual(source_path.read_bytes(), source_payload)
        self.assertEqual(source_path.stat().st_ino, source_inode)
        self.assertNotEqual(public_path.stat().st_ino, source_inode)
        self.assertEqual(public_values[0]["api_key"], "[REDACTED]")
        self.assertEqual(public_values[1]["note"], "temporary [REDACTED]")
        self.assertNotIn(token.encode(), public_payload)
        self.assertGreaterEqual(manifest["totals"]["redactions"], 4)

    def test_rejects_malformed_json_lines_dependency(self) -> None:
        """An invalid non-empty JSON Lines row fails instead of becoming a raw public file."""
        relative_path = "assets/mirrors/full-bench/catalog/malformed.json"
        source_path = self.source / relative_path
        source_path.parent.mkdir(parents=True)
        source_path.write_text('{"id":1}\nnot-json\n', encoding="utf-8")
        self._reference_full_dependency(relative_path)

        with self.assertRaisesRegex(ExportError, "JSON Lines.*line 2"):
            self._export()

        self.assertFalse(self.destination.exists())

    def test_validate_closure_discovers_references_inside_json_lines(self) -> None:
        """Closure validation follows local artifact references from every JSON Lines row."""
        baseline = PublicReleaseExporter(
            self.source,
            self.destination,
            self.policy_path,
            "fixture-release",
        ).validate_closure()
        jsonl_path = "assets/mirrors/full-bench/catalog/references.json"
        nested_path = "assets/mirrors/full-bench/task-1/from-json-lines.txt"
        source_jsonl = self.source / jsonl_path
        source_jsonl.parent.mkdir(parents=True)
        source_jsonl.write_text(
            '{"id":1}\n'
            f'{{"id":2,"view_path":"{nested_path}"}}\n',
            encoding="utf-8",
        )
        nested = self.source / nested_path
        nested.parent.mkdir(parents=True, exist_ok=True)
        nested.write_text("discovered through JSON Lines", encoding="utf-8")
        self._reference_full_dependency(jsonl_path)

        result = PublicReleaseExporter(
            self.source,
            self.destination,
            self.policy_path,
            "fixture-release",
        ).validate_closure()

        self.assertEqual(result["closure_files"], baseline["closure_files"] + 2)
        self.assertEqual(result["closure_json_files"], baseline["closure_json_files"] + 1)

    def test_redacts_text_preview_copy_on_write_and_synchronizes_manifest(self) -> None:
        """Strong preview credentials are redacted without changing source inode bytes."""
        bundle_path, first_source_bytes, second_source_bytes, first_token, second_token = (
            self._add_text_preview_bundle()
        )
        source_chunk = self.source / bundle_path / "chunk-00001.txt"
        source_manifest = self.source / bundle_path / "manifest.json"
        source_preview_shard = self.source / "assets/index_shards/preview/full-bench/tasks-0000.json"
        source_chunk_inode = source_chunk.stat().st_ino
        source_manifest_bytes = source_manifest.read_bytes()
        source_preview_shard_bytes = source_preview_shard.read_bytes()

        release_manifest = self._export()

        public_chunk = self.destination / bundle_path / "chunk-00001.txt"
        public_second_chunk = self.destination / bundle_path / "chunk-00002.txt"
        public_manifest_path = self.destination / bundle_path / "manifest.json"
        public_bytes = public_chunk.read_bytes()
        self.assertEqual(source_chunk.read_bytes(), first_source_bytes)
        self.assertEqual(source_chunk.stat().st_ino, source_chunk_inode)
        self.assertEqual(source_manifest.read_bytes(), source_manifest_bytes)
        self.assertEqual(source_preview_shard.read_bytes(), source_preview_shard_bytes)
        self.assertNotEqual(public_chunk.stat().st_ino, source_chunk.stat().st_ino)
        self.assertNotEqual(public_manifest_path.stat().st_ino, source_manifest.stat().st_ino)
        self.assertNotIn(first_token.encode(), public_bytes)
        self.assertNotIn(second_token.encode(), public_bytes)
        self.assertEqual(public_bytes.count(b"[REDACTED]"), 2)
        self.assertEqual(public_second_chunk.read_bytes(), second_source_bytes)
        self.assertEqual(
            public_second_chunk.stat().st_ino,
            (self.source / bundle_path / "chunk-00002.txt").stat().st_ino,
        )

        bundle_manifest = json.loads(public_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(bundle_manifest["chunks"][0]["bytes"], len(public_bytes))
        self.assertEqual(bundle_manifest["chunks"][0]["lines"], 4)
        self.assertEqual(bundle_manifest["chunks"][1]["bytes"], len(second_source_bytes))
        self.assertEqual(bundle_manifest["chunks"][1]["lines"], 2)
        self.assertEqual(bundle_manifest["text_chunks"][0]["bytes"], len(public_bytes))
        self.assertEqual(bundle_manifest["text_chunks"][0]["lines"], 4)
        self.assertEqual(bundle_manifest["text_chunks"][0]["start_line"], 1)
        self.assertEqual(bundle_manifest["text_chunks"][0]["end_line"], 4)
        self.assertEqual(bundle_manifest["text_chunks"][1]["start_line"], 5)
        self.assertEqual(bundle_manifest["text_chunks"][1]["end_line"], 6)
        self.assertEqual(bundle_manifest["total_chunks"], 2)
        self.assertEqual(bundle_manifest["total_lines"], 6)
        notice = bundle_manifest["public_release"]["text_preview_redaction"]
        self.assertEqual(notice["redacted_chunk_count"], 1)
        self.assertEqual(notice["redaction_count"], 2)
        public_preview_shard_path = (
            self.destination / "assets/index_shards/preview/full-bench/tasks-0000.json"
        )
        self.assertNotEqual(public_preview_shard_path.stat().st_ino, source_preview_shard.stat().st_ino)
        public_preview_shard = json.loads(public_preview_shard_path.read_text(encoding="utf-8"))
        preview_record = public_preview_shard["records"][-1]
        self.assertEqual(preview_record["text_chunks"][0]["bytes"], len(public_bytes))
        self.assertEqual(preview_record["text_chunks"][0]["lines"], 4)
        self.assertEqual(preview_record["text_chunks"][0]["start_line"], 1)
        self.assertEqual(preview_record["text_chunks"][0]["end_line"], 4)
        self.assertEqual(preview_record["text_chunks"][1]["start_line"], 5)
        self.assertEqual(preview_record["text_chunks"][1]["end_line"], 6)
        self.assertEqual(preview_record["total_chunks"], 2)
        self.assertEqual(preview_record["total_lines"], 6)

        manifest_entry = next(
            item for item in release_manifest["files"] if item["path"] == f"{bundle_path}/chunk-00001.txt"
        )
        self.assertEqual(
            manifest_entry["sha256"],
            _sha256_and_scan(public_chunk, manifest_entry["path"]),
        )
        self.assertEqual(manifest_entry["size"], len(public_bytes))
        self.assertGreaterEqual(release_manifest["totals"]["redactions"], 4)

    def test_text_preview_line_count_has_stable_newline_semantics(self) -> None:
        """Empty, CRLF, and legacy-encoded chunks retain deterministic line counts."""
        self.assertEqual(_text_line_count(b"", "empty.txt"), 0)
        self.assertEqual(_text_line_count(b"one\n", "trailing.txt"), 1)
        self.assertEqual(_text_line_count(b"one\r\ntwo\r\n", "crlf.txt"), 2)
        self.assertEqual(_text_line_count(b"caf\xe9\r\nnext\r\n", "latin-1.txt"), 2)

    def test_rejects_credential_spanning_adjacent_text_chunks(self) -> None:
        """Manifest-ordered overlap scanning catches a JWT split across two files."""
        bundle_path, _, _, _, _ = self._add_text_preview_bundle()
        token = f"eyJ{'Q' * 12}.{'R' * 12}.{'S' * 12}".encode()
        split_at = len(token) // 2
        payloads = [b"prefix " + token[:split_at], token[split_at:] + b" suffix"]
        chunk_paths = [
            f"{bundle_path}/chunk-00001.txt",
            f"{bundle_path}/chunk-00002.txt",
        ]
        for relative_path, payload in zip(chunk_paths, payloads):
            (self.source / relative_path).write_bytes(payload)

        manifest_path = self.source / bundle_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field_name in ("chunks", "text_chunks"):
            line_cursor = 1
            for index, entry in enumerate(manifest[field_name]):
                line_count = _text_line_count(payloads[index], chunk_paths[index])
                entry["bytes"] = len(payloads[index])
                entry["lines"] = line_count
                if "start_line" in entry or "end_line" in entry:
                    entry["start_line"] = line_cursor
                    entry["end_line"] = line_cursor + line_count - 1
                line_cursor += line_count
        manifest["total_lines"] = sum(
            _text_line_count(payload, relative_path)
            for payload, relative_path in zip(payloads, chunk_paths)
        )
        _write_json(manifest_path, manifest)

        preview_shard = self.source / "assets/index_shards/preview/full-bench/tasks-0000.json"
        preview_index = json.loads(preview_shard.read_text(encoding="utf-8"))
        preview_record = preview_index["records"][-1]
        preview_record["text_chunks"] = copy.deepcopy(manifest["text_chunks"])
        preview_record["total_lines"] = manifest["total_lines"]
        _write_json(preview_shard, preview_index)
        source_bytes = [self.source.joinpath(path).read_bytes() for path in chunk_paths]

        with self.assertRaisesRegex(SecurityError, "logical text preview bundle"):
            self._export()

        self.assertFalse(self.destination.exists())
        self.assertEqual(
            [self.source.joinpath(path).read_bytes() for path in chunk_paths],
            source_bytes,
        )

    def test_redacts_text_chunks_only_manifest_schema(self) -> None:
        """A bundle declaring only text_chunks receives the same synchronized metadata."""
        bundle_path, _, _, _, _ = self._add_text_preview_bundle()
        source_manifest = self.source / bundle_path / "manifest.json"
        manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
        manifest.pop("chunks")
        _write_json(source_manifest, manifest)

        self._export()

        public_manifest = json.loads(
            (self.destination / bundle_path / "manifest.json").read_text(encoding="utf-8")
        )
        first_chunk = (self.destination / bundle_path / "chunk-00001.txt").read_bytes()
        self.assertNotIn("chunks", public_manifest)
        self.assertEqual(public_manifest["text_chunks"][0]["bytes"], len(first_chunk))
        self.assertEqual(public_manifest["text_chunks"][0]["lines"], 4)
        self.assertEqual(public_manifest["total_chunks"], 2)
        self.assertEqual(public_manifest["total_lines"], 6)

    def test_duplicate_preview_shard_chunk_reference_fails_closed(self) -> None:
        """The same changed chunk cannot be declared twice in one shard chunk list."""
        bundle_path, first_source_bytes, _, _, _ = self._add_text_preview_bundle()
        preview_shard = self.source / "assets/index_shards/preview/full-bench/tasks-0000.json"
        preview_index = json.loads(preview_shard.read_text(encoding="utf-8"))
        text_chunks = preview_index["records"][-1]["text_chunks"]
        text_chunks.append(copy.deepcopy(text_chunks[0]))
        _write_json(preview_shard, preview_index)

        with self.assertRaisesRegex(ExportError, "Duplicate text preview chunk"):
            self._export()

        self.assertFalse(self.destination.exists())
        self.assertEqual(
            (self.source / bundle_path / "chunk-00001.txt").read_bytes(),
            first_source_bytes,
        )

    def test_conflicting_preview_shard_chunk_paths_fail_closed(self) -> None:
        """Disagreeing url/path fields cannot redirect a changed chunk metadata update."""
        bundle_path, first_source_bytes, _, _, _ = self._add_text_preview_bundle()
        preview_shard = self.source / "assets/index_shards/preview/full-bench/tasks-0000.json"
        preview_index = json.loads(preview_shard.read_text(encoding="utf-8"))
        preview_index["records"][-1]["text_chunks"][0]["path"] = (
            f"{bundle_path}/chunk-00002.txt"
        )
        _write_json(preview_shard, preview_index)

        with self.assertRaisesRegex(ExportError, "Conflicting text chunk references"):
            self._export()

        self.assertFalse(self.destination.exists())
        self.assertEqual(
            (self.source / bundle_path / "chunk-00001.txt").read_bytes(),
            first_source_bytes,
        )

    def test_copy_on_write_replacement_allows_generated_file_without_source(self) -> None:
        """Generated export files can be atomically replaced without a source counterpart."""
        exporter = PublicReleaseExporter(
            self.source,
            self.destination,
            self.policy_path,
            "fixture-release",
        )
        exporter._prepare_destination()
        relative_path = "assets/generated-only.txt"
        target = exporter._destination_path(relative_path)
        target.write_bytes(b"before")
        exporter.exported.add(relative_path)
        exporter.generated_files = 1

        exporter._replace_exported_file(relative_path, b"after")

        self.assertEqual(target.read_bytes(), b"after")
        self.assertEqual(exporter.generated_files, 1)
        self.assertEqual(exporter.hardlinked_files, 0)

    def test_generated_json_replaces_existing_hardlink_copy_on_write(self) -> None:
        """Regenerating an exported JSON file cannot write through to its source inode."""
        relative_path = "data/existing-generated.json"
        source_path = self.source / relative_path
        original_payload = b'{"source":"immutable"}\n'
        source_path.write_bytes(original_payload)
        exporter = PublicReleaseExporter(
            self.source,
            self.destination,
            self.policy_path,
            "fixture-release",
        )
        exporter._prepare_destination()
        exporter._hardlink(relative_path, source_path)

        exporter._write_generated_json(relative_path, {"generated": True}, discover=False)

        target = exporter.partial / relative_path
        self.assertEqual(source_path.read_bytes(), original_payload)
        self.assertNotEqual(target.stat().st_ino, source_path.stat().st_ino)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"generated": True})
        self.assertEqual(exporter.generated_files, 1)
        self.assertEqual(exporter.hardlinked_files, 0)

    def test_referenced_source_public_manifest_is_reserved_and_unchanged(self) -> None:
        """A source self-manifest reference resolves to the newly generated public manifest."""
        source_manifest = self.source / "data/public_manifest.json"
        _write_json(source_manifest, {"sentinel": "immutable-source-manifest"})
        full_shard_path = self.source / "data/benches/full-bench.json"
        full_shard = json.loads(full_shard_path.read_text(encoding="utf-8"))
        full_shard["tasks"][0]["manifest_url"] = "data/public_manifest.json"
        _write_json(full_shard_path, full_shard)
        self._refresh_policy_pins()
        source_bytes = source_manifest.read_bytes()
        source_inode = source_manifest.stat().st_ino

        manifest = self._export()

        public_manifest_path = self.destination / "data/public_manifest.json"
        public_manifest = json.loads(public_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(source_manifest.read_bytes(), source_bytes)
        self.assertEqual(source_manifest.stat().st_ino, source_inode)
        self.assertNotEqual(public_manifest_path.stat().st_ino, source_inode)
        self.assertEqual(public_manifest["release_id"], "fixture-release")
        self.assertEqual(public_manifest["self"]["path"], "data/public_manifest.json")
        self.assertNotIn("sentinel", public_manifest)
        self.assertNotIn("data/public_manifest.json", {item["path"] for item in manifest["files"]})
        self.assertEqual(manifest["totals"]["files"], len(manifest["files"]))
        self.assertEqual(
            manifest["totals"]["files"],
            manifest["totals"]["generated_files"] + manifest["totals"]["hardlinked_files"],
        )

    def test_manifest_process_pool_preserves_sorted_path_digest_binding(self) -> None:
        """Out-of-order worker results still produce sorted correctly paired manifest entries."""
        with (
            mock.patch("scripts.export_public_release.os.cpu_count", return_value=64),
            mock.patch(
                "scripts.export_public_release.concurrent.futures.ProcessPoolExecutor"
            ) as process_pool,
        ):
            executor = process_pool.return_value.__enter__.return_value

            def reversed_results(function: Any, items: Any, chunksize: int) -> list[Any]:
                """Simulate process completions arriving in reverse input order."""
                del chunksize
                return [function(item) for item in reversed(list(items))]

            executor.map.side_effect = reversed_results
            manifest = self._export()

        process_pool.assert_called_once_with(max_workers=4)
        manifest_paths = [item["path"] for item in manifest["files"]]
        self.assertEqual(manifest_paths, sorted(manifest_paths))
        for entry in manifest["files"]:
            public_path = self.destination.joinpath(*Path(entry["path"]).parts)
            self.assertEqual(entry["sha256"], hashlib.sha256(public_path.read_bytes()).hexdigest())

    def test_rejects_symlinked_dependency(self) -> None:
        """A referenced symlink cannot escape or alias the immutable release tree."""
        artifact = self.source / "assets/mirrors/full-bench/task-1/result.txt"
        artifact.unlink()
        artifact.symlink_to(self.root / "outside.txt")
        self.root.joinpath("outside.txt").write_text("outside", encoding="utf-8")
        with self.assertRaises(SecurityError):
            self._export()

    def test_rejects_internal_ingestion_ui(self) -> None:
        """The public UI bundle cannot carry the internal ingestion client or API endpoint."""
        self.site.joinpath("app.js").write_text("fetch('http://host:8913/v1/jobs')", encoding="utf-8")
        with self.assertRaises(SecurityError):
            self._export()

    def test_rejects_cross_benchmark_dependency(self) -> None:
        """A full shard cannot smuggle an excluded benchmark artifact into the release."""
        closed_artifact = self.source / "assets/mirrors/closed-bench/private.txt"
        closed_artifact.parent.mkdir(parents=True)
        closed_artifact.write_text("closed", encoding="utf-8")
        full_shard_path = self.source / "data/benches/full-bench.json"
        full_shard = json.loads(full_shard_path.read_text(encoding="utf-8"))
        full_shard["tasks"][0]["artifact_url"] = "assets/mirrors/closed-bench/private.txt"
        _write_json(full_shard_path, full_shard)
        self._refresh_policy_pins()

        with self.assertRaisesRegex(SecurityError, "crosses into non-full benchmark"):
            self._export()

    def test_missing_ui_view_path_fails_closed(self) -> None:
        """A primary local path consumed by the UI cannot silently disappear."""
        full_shard_path = self.source / "data/benches/full-bench.json"
        full_shard = json.loads(full_shard_path.read_text(encoding="utf-8"))
        full_shard["tasks"][0]["view_path"] = "assets/mirrors/full-bench/missing.pdf"
        _write_json(full_shard_path, full_shard)
        self._refresh_policy_pins()

        with self.assertRaisesRegex(ExportError, "missing"):
            self._export()

    def test_validate_selection_writes_nothing(self) -> None:
        """Validation-only mode checks counts without creating an output directory."""
        exporter = PublicReleaseExporter(
            self.source,
            self.destination,
            self.policy_path,
            "fixture-release",
        )
        result = exporter.validate_selection()
        self.assertEqual(result["full_records"], 1)
        self.assertFalse(self.destination.exists())

    def test_token_scanner_does_not_rewrite_risk_filename(self) -> None:
        """The sk- token prefix cannot start in the middle of an ordinary filename word."""
        path = "assets/mirrors/jobbench/loan-risk-assessment-template.xls"
        sanitized, redactions = sanitize_json(path)
        self.assertEqual(sanitized, path)
        self.assertEqual(redactions, 0)

    def test_token_scanner_does_not_match_lowercase_url_slug(self) -> None:
        """A long sk-prefixed prose slug is not an OpenAI-shaped random credential."""
        url = "https://example.test/archive/sk-supercomputer-cluster-reaches-new-milestone"
        sanitized, redactions = sanitize_json(url)
        self.assertEqual(sanitized, url)
        self.assertEqual(redactions, 0)

    def test_excludes_ephemeral_office_lock_file(self) -> None:
        """An Office lock file is neither a benchmark artifact nor a required public dependency."""
        path = "assets/mirrors/example/catalog/folder/.~lock.example.xlsx"
        sanitized, redactions = sanitize_json(path)
        self.assertEqual(sanitized, "[EPHEMERAL LOCK FILE EXCLUDED]")
        self.assertEqual(redactions, 1)

    def test_removes_pdf_extraction_control_characters(self) -> None:
        """Invisible C0 bytes from PDF text extraction do not become path errors or public JSON."""
        sanitized, redactions = sanitize_json("formula \x14 x \x00 y\nkept")
        self.assertEqual(sanitized, "formula  x  y\nkept")
        self.assertEqual(redactions, 2)

    def test_scans_credentials_inside_office_zip_packages(self) -> None:
        """Compressed Office XML cannot conceal a credential from publication checks."""
        package = self.root / "credential.docx"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", "hf_" + "a" * 32)

        with self.assertRaisesRegex(SecurityError, "Credential-shaped content"):
            _sha256_and_scan(package, "assets/mirrors/full-bench/credential.docx")

    def test_exact_invalid_upstream_zip_can_be_download_only(self) -> None:
        """One hash-pinned invalid upstream ZIP remains downloadable without being unpacked."""
        path = "assets/mirrors/full-bench/task-1/upstream.zip"
        package = self.source / path
        package.parent.mkdir(parents=True, exist_ok=True)
        package.write_bytes(b"PK\x03\x04upstream-object-without-central-directory")
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        full_shard_path = self.source / "data/benches/full-bench.json"
        full_shard = json.loads(full_shard_path.read_text(encoding="utf-8"))
        full_shard["tasks"][0]["download_path"] = path
        _write_json(full_shard_path, full_shard)
        self.policy["upstream_integrity_exceptions"] = {
            path: {
                "handling": "opaque_archive_download",
                "reason_zh": "fixture upstream bytes",
                "sha256": digest,
                "size_bytes": package.stat().st_size,
            }
        }
        self._refresh_policy_pins()

        manifest = self._export()

        record = next(item for item in manifest["files"] if item["path"] == path)
        self.assertEqual(record["sha256"], digest)
        self.assertEqual(record["content_disposition"], "attachment")
        self.assertEqual(record["archive_scan"], "opaque-upstream-bytes-pinned-v1")
        full_shard = json.loads(
            (self.destination / "data/benches/full-bench.json").read_text(encoding="utf-8")
        )
        artifact = full_shard["tasks"][0]
        self.assertEqual(artifact["integrity_status"], "upstream-anomaly-pinned-v1")
        self.assertEqual(artifact["integrity_note_zh"], "fixture upstream bytes")

    def test_opaque_archive_exception_cannot_bypass_member_security(self) -> None:
        """A valid ZIP exception never bypasses path or credential checks inside members."""
        package = self.root / "credential.zip"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("payload.txt", "hf_" + "a" * 32)
        digest = hashlib.sha256(package.read_bytes()).hexdigest()

        with self.assertRaisesRegex(SecurityError, "Credential-shaped content"):
            _sha256_and_scan(package, "assets/mirrors/full-bench/credential.zip", digest)


if __name__ == "__main__":
    unittest.main()
