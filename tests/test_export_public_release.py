"""Tests for the fail-closed public release exporter."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

from scripts.export_public_release import (
    ExportError,
    PublicReleaseExporter,
    SecurityError,
    _sha256_and_scan,
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


if __name__ == "__main__":
    unittest.main()
