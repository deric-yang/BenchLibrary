"""Tests for the immutable base-first public composite-source builder."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.build_public_composite_source import (
    CompositeError,
    build_composite,
    indexed_rows,
    plan_composite,
    validate_root,
    validate_tree_has_no_symlinks,
)


def _sha256(payload: bytes) -> str:
    """Return the SHA-256 digest for fixture bytes."""
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    """Write one JSON fixture and create its parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _json_fixture(payload: Any) -> bytes:
    """Return compact deterministic JSON fixture bytes."""
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _root_index(kind: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return one valid unsharded root index fixture."""
    summary: dict[str, Any] = {
        "bench_counts": {},
        "error_records": 0,
        "ready_records": 0,
        "records": 0,
    }
    if kind == "mirror":
        summary.update({"role_counts": {}, "unique_bytes": 0, "unique_objects": 0})
    else:
        summary["kind_counts"] = {}
    return {
        "generated_at": "2026-09-01T00:00:00+00:00",
        "record_shards": {
            "by_bench": {"full-bench": {"tasks": {}}},
            "schema_version": 1,
        },
        "records": records,
        "schema_version": 1,
        "summary": summary,
    }


class PublicCompositeSourceTest(unittest.TestCase):
    """Exercise fill-only selection, conflict handling, and safety gates."""

    def setUp(self) -> None:
        """Create isolated base, overlay, policy, and output paths."""
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.base = self.root / "immutable-base"
        self.overlay = self.root / "prior-public-v2"
        self.output = self.root / "composite"
        self.policy = self.root / "policy.json"
        self.base.mkdir()
        self.overlay.mkdir()
        _write_json(
            self.policy,
            {
                "full": {"full-bench": {"expected_records": 1}},
                "policy_id": "public-v3",
                "schema_version": 1,
            },
        )

    def tearDown(self) -> None:
        """Remove the isolated fixture tree."""
        self.temporary_directory.cleanup()

    def _write_base(
        self,
        files: dict[str, bytes],
        mirror_records: list[dict[str, Any]] | None = None,
        preview_records: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Write base files and their immutable release manifest."""
        files = dict(files)
        files.setdefault(
            "data/benches/full-bench.json",
            _json_fixture(
                {
                    "benchmark_id": "full-bench",
                    "record_count": 1,
                    "tasks": [{"id": "task-1"}],
                }
            ),
        )
        files.setdefault(
            "assets/mirror_index.json",
            _json_fixture(_root_index("mirror", mirror_records or [])),
        )
        files.setdefault(
            "assets/preview_index.json",
            _json_fixture(_root_index("preview", preview_records or [])),
        )
        rows = []
        for relative, payload in sorted(files.items()):
            path = self.base / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            rows.append(
                {
                    "path": relative,
                    "sha256": _sha256(payload),
                    "size_bytes": len(payload),
                }
            )
        manifest = {
            "file_count": len(rows),
            "files": rows,
            "schema_version": 1,
            "security_contract": {
                "publish_mode": "allowlist_only",
                "raw_executable_mirrors": "forbidden",
                "switch_mode": "validated_versioned_release",
            },
            "total_bytes": sum(row["size_bytes"] for row in rows),
        }
        path = self.base / "release_manifest.json"
        _write_json(path, manifest)
        return path

    def _write_overlay(
        self,
        files: dict[str, bytes],
        mirror_records: list[dict[str, Any]] | None = None,
        preview_records: list[dict[str, Any]] | None = None,
    ) -> tuple[Path, Path]:
        """Write prior-public files, public manifest, and saved R2 inventory."""
        files = dict(files)
        files.setdefault(
            "assets/mirror_index.json",
            _json_fixture(_root_index("mirror", mirror_records or [])),
        )
        files.setdefault(
            "assets/preview_index.json",
            _json_fixture(_root_index("preview", preview_records or [])),
        )
        rows = []
        for relative, payload in sorted(files.items()):
            path = self.overlay / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            rows.append(
                {
                    "cache_control": "public, max-age=31536000, immutable",
                    "content_type": "application/octet-stream",
                    "path": relative,
                    "r2_key": f"releases/prior-public-v2/{relative}",
                    "sha256": _sha256(payload),
                    "size": len(payload),
                }
            )
        manifest = {
            "files": rows,
            "policy": {"id": "public-v2", "sha256": "a" * 64},
            "publication": {"full_records": 1},
            "release_id": "prior-public-v2",
            "schema_version": 1,
            "self": {
                "path": "data/public_manifest.json",
                "r2_key": "releases/prior-public-v2/data/public_manifest.json",
            },
            "source": {"immutable_directory": "prior-immutable"},
            "totals": {
                "files": len(rows),
                "logical_bytes": sum(row["size"] for row in rows),
            },
        }
        manifest_path = self.overlay / "data/public_manifest.json"
        _write_json(manifest_path, manifest)
        manifest_bytes = manifest_path.read_bytes()
        objects = [
            {
                "custom_metadata": {"sha256": row["sha256"]},
                "http_metadata": {
                    "cache_control": row["cache_control"],
                    "content_disposition": "",
                    "content_encoding": "",
                    "content_type": row["content_type"],
                },
                "key": row["r2_key"],
                "size": row["size"],
            }
            for row in rows
        ]
        objects.append(
            {
                "custom_metadata": {"sha256": _sha256(manifest_bytes)},
                "http_metadata": {
                    "cache_control": "public, max-age=300, must-revalidate",
                    "content_disposition": "",
                    "content_encoding": "",
                    "content_type": "application/json; charset=utf-8",
                },
                "key": "releases/prior-public-v2/data/public_manifest.json",
                "size": len(manifest_bytes),
            }
        )
        inventory = {
            "bytes": sum(row["size"] for row in rows) + len(manifest_bytes),
            "complete": True,
            "count": len(objects),
            "objects": objects,
            "prefix": "releases/prior-public-v2/",
            "schema_version": 1,
        }
        inventory_path = self.root / ".prior-public-v2.r2-inventory.json"
        _write_json(inventory_path, inventory)
        return manifest_path, inventory_path

    def _build(
        self,
        base_manifest: Path,
        overlay_manifest: Path,
        overlay_inventory: Path,
    ) -> dict[str, Any]:
        """Build one fixture composite with the production helper."""
        return build_composite(
            self.base.resolve(strict=True),
            base_manifest.resolve(strict=True),
            self.overlay.resolve(strict=True),
            overlay_manifest.resolve(strict=True),
            overlay_inventory.resolve(strict=True),
            self.policy.resolve(strict=True),
            self.output,
        )

    def _plan(
        self,
        base_manifest: Path,
        overlay_manifest: Path,
        overlay_inventory: Path,
    ) -> dict[str, Any]:
        """Plan one fixture composite without writing the output tree."""
        return plan_composite(
            self.base.resolve(strict=True),
            base_manifest.resolve(strict=True),
            self.overlay.resolve(strict=True),
            overlay_manifest.resolve(strict=True),
            overlay_inventory.resolve(strict=True),
            self.policy.resolve(strict=True),
            self.output,
        )

    def test_success_fills_only_allowed_missing_assets_and_keeps_base(self) -> None:
        """Missing approved assets are added while conflicts and excluded paths stay base-first."""
        base_manifest = self._write_base(
            {
                "assets/mirrors/conflict.txt": b"current",
                "assets/mirrors/same.txt": b"same",
                "data/catalog.json": b"current catalog",
            }
        )
        overlay_manifest, overlay_inventory = self._write_overlay(
            {
                "assets/index_shards/mirror/old.json": b"old shard",
                "assets/mirrors/conflict.txt": b"prior",
                "assets/mirrors/full-bench/new.bin": b"new mirror",
                "assets/mirrors/same.txt": b"same",
                "assets/other/not-allowed.bin": b"other namespace",
                "assets/previews/text/new.txt": b"new preview",
                "assets/verifiers/sources/new.py": b"new verifier",
                "data/catalog.json": b"old catalog",
                "site/app.js": b"old site",
            },
            mirror_records=[
                {
                    "bench_id": "full-bench",
                    "object_path": "assets/objects/internal-only",
                    "role": "input",
                    "sha256": _sha256(b"new mirror"),
                    "size": len(b"new mirror"),
                    "status": "ready",
                    "task_id": "task-1",
                    "task_ids": ["task-1"],
                    "view_path": "assets/mirrors/full-bench/new.bin",
                }
            ],
            preview_records=[
                {
                    "bench_id": "full-bench",
                    "deploy_paths": ["assets/previews/text/new.txt"],
                    "preview_kind": "text",
                    "preview_url": "assets/previews/text/new.txt",
                    "role": "input",
                    "source_view_path": "assets/mirrors/full-bench/new.bin",
                    "status": "ready",
                    "task_id": "task-1",
                    "task_ids": ["task-1"],
                }
            ],
        )

        provenance = self._build(
            base_manifest,
            overlay_manifest,
            overlay_inventory,
        )

        self.assertTrue(provenance["complete"])
        self.assertEqual(provenance["selection"]["added_files"], 3)
        self.assertEqual(provenance["selection"]["existing_identical_files"], 1)
        self.assertEqual(provenance["selection"]["base_retained_conflicts"], 1)
        self.assertEqual(
            (self.output / "assets/mirrors/conflict.txt").read_bytes(),
            b"current",
        )
        self.assertEqual(
            (self.output / "assets/mirrors/full-bench/new.bin").read_bytes(),
            b"new mirror",
        )
        self.assertFalse((self.output / "assets/index_shards/mirror/old.json").exists())
        self.assertFalse((self.output / "assets/other/not-allowed.bin").exists())
        self.assertEqual((self.output / "data/catalog.json").read_bytes(), b"current catalog")
        mirror_index = json.loads(
            (self.output / "assets/mirror_index.json").read_text(encoding="utf-8")
        )
        preview_index = json.loads(
            (self.output / "assets/preview_index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(mirror_index["records"]), 1)
        self.assertNotIn("object_path", mirror_index["records"][0])
        self.assertEqual(mirror_index["summary"]["bench_counts"], {"full-bench": 1})
        self.assertEqual(mirror_index["summary"]["unique_objects"], 1)
        self.assertEqual(
            preview_index["mirror_index_sha256"],
            _sha256((self.output / "assets/mirror_index.json").read_bytes()),
        )
        conflict = provenance["conflicts"][0]
        self.assertEqual(conflict["decision"], "base_retained")
        self.assertEqual(conflict["base_sha256"], _sha256(b"current"))
        self.assertEqual(conflict["overlay_sha256"], _sha256(b"prior"))
        stored = json.loads(
            (self.output / ".kwbl-composite-provenance.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(stored["selection"]["overlay_not_inherited"]["data"])
        self.assertEqual(len(stored["supplements"]), 3)
        self.assertEqual(stored["index_recovery"]["mirror"]["stats"]["records"], 1)
        self.assertEqual(stored["index_recovery"]["preview"]["stats"]["records"], 1)
        self.assertEqual(
            (self.output / ".kwbl-composite-provenance.json").stat().st_mode & 0o777,
            0o644,
        )

    def test_tampered_overlay_addition_fails_before_final_output(self) -> None:
        """An overlay file whose bytes drifted from its manifest cannot be installed."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay(
            {"assets/mirrors/full-bench/new.bin": b"expected"},
            mirror_records=[
                {
                    "bench_id": "full-bench",
                    "role": "input",
                    "sha256": _sha256(b"expected"),
                    "size": len(b"expected"),
                    "status": "ready",
                    "task_id": "task-1",
                    "task_ids": ["task-1"],
                    "view_path": "assets/mirrors/full-bench/new.bin",
                }
            ],
        )
        (self.overlay / "assets/mirrors/full-bench/new.bin").write_bytes(b"tampered")

        with self.assertRaisesRegex(CompositeError, "overlay addition SHA-256 mismatch"):
            self._build(base_manifest, overlay_manifest, overlay_inventory)
        self.assertFalse(self.output.exists())

    def test_plan_is_write_free_deterministic_and_matches_execute(self) -> None:
        """Planning exposes stable generated index hashes without creating output."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        mirror_record = {
            "bench_id": "full-bench",
            "role": "input",
            "sha256": _sha256(b"mirror"),
            "size": len(b"mirror"),
            "status": "ready",
            "task_id": "task-1",
            "task_ids": ["task-1"],
            "view_path": "assets/mirrors/full-bench/input.bin",
        }
        preview_record = {
            "bench_id": "full-bench",
            "deploy_paths": ["assets/previews/text/input.txt"],
            "preview_kind": "text",
            "preview_url": "assets/previews/text/input.txt",
            "source_view_path": "assets/mirrors/full-bench/input.bin",
            "status": "ready",
            "task_id": "task-1",
            "task_ids": ["task-1"],
        }
        overlay_manifest, overlay_inventory = self._write_overlay(
            {
                "assets/mirrors/full-bench/input.bin": b"mirror",
                "assets/previews/text/input.txt": b"preview",
            },
            mirror_records=[mirror_record],
            preview_records=[preview_record],
        )

        first = self._plan(base_manifest, overlay_manifest, overlay_inventory)
        second = self._plan(base_manifest, overlay_manifest, overlay_inventory)

        self.assertFalse(self.output.exists())
        self.assertEqual(first["recovery"], second["recovery"])
        provenance = self._build(base_manifest, overlay_manifest, overlay_inventory)
        self.assertEqual(first["recovery"], provenance["index_recovery"])
        for kind, relative in (
            ("mirror", "assets/mirror_index.json"),
            ("preview", "assets/preview_index.json"),
        ):
            self.assertEqual(
                _sha256((self.output / relative).read_bytes()),
                first["recovery"][kind]["sha256"],
            )

    def test_gdpval_benchmark_asset_exception_is_explicit_and_audited(self) -> None:
        """Only the exact GDPval catalog/reference synthetic identity is recoverable."""
        _write_json(
            self.policy,
            {
                "full": {"gdpval": {"expected_records": 0}},
                "policy_id": "public-v3",
                "schema_version": 1,
            },
        )
        base_manifest = self._write_base(
            {
                "data/benches/gdpval.json": _json_fixture(
                    {
                        "benchmark_id": "gdpval",
                        "record_count": 0,
                        "tasks": [],
                    }
                )
            }
        )
        synthetic_id = "gdpval:asset-0123456789abcdef"
        overlay_manifest, overlay_inventory = self._write_overlay(
            {"assets/mirrors/gdpval/catalog/README.md": b"catalog"},
            mirror_records=[
                {
                    "bench_id": "gdpval",
                    "role": "catalog",
                    "sha256": _sha256(b"catalog"),
                    "size": len(b"catalog"),
                    "status": "ready",
                    "task_id": synthetic_id,
                    "task_ids": [synthetic_id],
                    "view_path": "assets/mirrors/gdpval/catalog/README.md",
                }
            ],
        )

        plan = self._plan(base_manifest, overlay_manifest, overlay_inventory)

        stats = plan["recovery"]["mirror"]["stats"]
        self.assertEqual(stats["benchmark_asset_records"], 1)
        self.assertEqual(stats["benchmark_asset_ids"], [synthetic_id])

    def test_unknown_task_binding_is_rejected(self) -> None:
        """A recovered ordinary record must bind an ID in the current task shard."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay(
            {"assets/mirrors/full-bench/input.bin": b"mirror"},
            mirror_records=[
                {
                    "bench_id": "full-bench",
                    "role": "input",
                    "sha256": _sha256(b"mirror"),
                    "size": len(b"mirror"),
                    "status": "ready",
                    "task_id": "not-current",
                    "task_ids": ["not-current"],
                    "view_path": "assets/mirrors/full-bench/input.bin",
                }
            ],
        )
        with self.assertRaisesRegex(CompositeError, "non-current task"):
            self._plan(base_manifest, overlay_manifest, overlay_inventory)

    def test_mixed_supplement_paths_are_rejected(self) -> None:
        """One recovered record cannot mix supplement and non-supplement paths."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay(
            {"assets/mirrors/full-bench/input.bin": b"mirror"},
            mirror_records=[
                {
                    "bench_id": "full-bench",
                    "role": "input",
                    "sha256": _sha256(b"mirror"),
                    "size": len(b"mirror"),
                    "source_view_path": "assets/mirrors/not-a-supplement.bin",
                    "status": "ready",
                    "task_id": "task-1",
                    "task_ids": ["task-1"],
                    "view_path": "assets/mirrors/full-bench/input.bin",
                }
            ],
        )
        with self.assertRaisesRegex(CompositeError, "outside supplements"):
            self._plan(base_manifest, overlay_manifest, overlay_inventory)

    def test_uncovered_supplement_path_is_rejected(self) -> None:
        """Every new mirror or preview file must be bound by a recovered record."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay(
            {"assets/previews/text/orphan.txt": b"orphan"}
        )
        with self.assertRaisesRegex(CompositeError, "not covered"):
            self._plan(base_manifest, overlay_manifest, overlay_inventory)

    def test_tampered_overlay_root_index_is_rejected(self) -> None:
        """Recovered metadata itself must match the R2-verified manifest identity."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay({})
        (self.overlay / "assets/mirror_index.json").write_bytes(b"{}")
        with self.assertRaisesRegex(CompositeError, "overlay mirror root index size mismatch"):
            self._plan(base_manifest, overlay_manifest, overlay_inventory)

    def test_tampered_base_payload_is_rejected(self) -> None:
        """Every base payload must still match its manifest size and digest."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay({})
        (self.base / "data/catalog.json").write_bytes(b"drifted")
        with self.assertRaisesRegex(CompositeError, "base manifest payload size mismatch"):
            self._plan(base_manifest, overlay_manifest, overlay_inventory)

    def test_unmanifested_base_payload_is_rejected(self) -> None:
        """A base tree file outside the manifest closure cannot reach copytree."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay({})
        (self.base / "unlisted.bin").write_bytes(b"not in the manifest")
        with self.assertRaisesRegex(CompositeError, "unmanifested payload"):
            self._plan(base_manifest, overlay_manifest, overlay_inventory)

    def test_exporter_path_normalization_and_nested_collection_are_reused(self) -> None:
        """Encoded, prefixed, relative, leading-slash, and nested paths normalize identically."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        mirror_path = "assets/mirrors/full-bench/input.bin"
        preview_path = "assets/previews/text/input.txt"
        mirror_record = {
            "bench_id": "full-bench",
            "logical_path": "data/nonexistent-provenance.parquet",
            "nested": {
                "object_path": "/bench-monitor/assets/mirrors/never-public.bin"
            },
            "role": "input",
            "sha256": _sha256(b"mirror"),
            "size": len(b"mirror"),
            "status": "ready",
            "task_id": "task-1",
            "task_ids": ["task-1"],
            "view_path": (
                "/bench-monitor/assets%2Fmirrors%2Ffull-bench%2Finput.bin"
            ),
        }
        preview_record = {
            "bench_id": "full-bench",
            "chunks": [{"url": f"./{preview_path}"}],
            "preview_kind": "text",
            "preview_url": f"/{preview_path}",
            "source_view_path": f"bench-monitor/{mirror_path}",
            "status": "ready",
            "task_id": "task-1",
            "task_ids": ["task-1"],
        }
        overlay_manifest, overlay_inventory = self._write_overlay(
            {mirror_path: b"mirror", preview_path: b"preview"},
            mirror_records=[mirror_record],
            preview_records=[preview_record],
        )

        plan = self._plan(base_manifest, overlay_manifest, overlay_inventory)

        mirror_stats = plan["recovery"]["mirror"]["stats"]
        preview_stats = plan["recovery"]["preview"]["stats"]
        self.assertEqual(mirror_stats["supplement_paths"], 1)
        self.assertEqual(preview_stats["supplement_paths"], 2)
        self.assertEqual(mirror_stats["ignored_non_strict_missing_paths"], 1)
        restored = plan["_private"]["recovery"]["mirror"]["payload"]["records"][0]
        self.assertNotIn("object_path", restored["nested"])

    def test_exporter_sanitization_precedes_reference_validation(self) -> None:
        """Ephemeral, credential, and internal strings match exporter semantics."""
        lock_path = (
            "assets/mirrors/full-bench/catalog/folder/"
            ".~lock.golden.xlsx"
        )
        base_record = {
            "bench_id": "full-bench",
            "role": "catalog",
            "status": "ready",
            "task_id": "task-1",
            "task_ids": ["task-1"],
            "view_path": lock_path,
        }
        base_manifest = self._write_base(
            {"data/catalog.json": b"base"},
            mirror_records=[base_record],
        )
        mirror_path = "assets/mirrors/full-bench/input.bin"
        recovered_record = {
            "api_key": "not-a-public-value",
            "bench_id": "full-bench",
            "notes": "source /mnt/data/private/manifest.json",
            "role": "input",
            "sha256": _sha256(b"mirror"),
            "size": len(b"mirror"),
            "status": "ready",
            "task_id": "task-1",
            "task_ids": ["task-1"],
            "view_path": mirror_path,
        }
        overlay_manifest, overlay_inventory = self._write_overlay(
            {mirror_path: b"mirror"},
            mirror_records=[recovered_record],
        )

        plan = self._plan(base_manifest, overlay_manifest, overlay_inventory)

        records = plan["_private"]["recovery"]["mirror"]["payload"]["records"]
        restored = next(record for record in records if record.get("role") == "input")
        self.assertEqual(restored["api_key"], "[REDACTED]")
        self.assertEqual(restored["notes"], "source [INTERNAL LOCATION REDACTED]")

    def test_sensitive_key_cannot_hide_a_supplement_binding(self) -> None:
        """Sanitization cannot turn a credential field into asset coverage."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        mirror_path = "assets/mirrors/full-bench/input.bin"
        overlay_manifest, overlay_inventory = self._write_overlay(
            {mirror_path: b"mirror"},
            mirror_records=[
                {
                    "api_key": mirror_path,
                    "bench_id": "full-bench",
                    "role": "input",
                    "sha256": _sha256(b"mirror"),
                    "size": len(b"mirror"),
                    "status": "ready",
                    "task_id": "task-1",
                    "task_ids": ["task-1"],
                }
            ],
        )

        with self.assertRaisesRegex(CompositeError, "not covered"):
            self._plan(base_manifest, overlay_manifest, overlay_inventory)

    def test_existing_non_strict_path_outside_supplements_is_rejected(self) -> None:
        """A non-strict provenance path becomes binding when its target exists."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        mirror_path = "assets/mirrors/full-bench/input.bin"
        overlay_manifest, overlay_inventory = self._write_overlay(
            {mirror_path: b"mirror"},
            mirror_records=[
                {
                    "bench_id": "full-bench",
                    "logical_path": "data/catalog.json",
                    "role": "input",
                    "sha256": _sha256(b"mirror"),
                    "size": len(b"mirror"),
                    "status": "ready",
                    "task_id": "task-1",
                    "task_ids": ["task-1"],
                    "view_path": mirror_path,
                }
            ],
        )
        with self.assertRaisesRegex(CompositeError, "outside supplements"):
            self._plan(base_manifest, overlay_manifest, overlay_inventory)

    def test_normalized_cross_benchmark_path_is_rejected(self) -> None:
        """A scoped asset cannot cross benchmarks after exporter normalization."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        cross_path = "assets/mirrors/other-bench/input.bin"
        overlay_manifest, overlay_inventory = self._write_overlay(
            {cross_path: b"mirror"},
            mirror_records=[
                {
                    "bench_id": "full-bench",
                    "role": "input",
                    "sha256": _sha256(b"mirror"),
                    "size": len(b"mirror"),
                    "status": "ready",
                    "task_id": "task-1",
                    "task_ids": ["task-1"],
                    "view_path": f"/bench-monitor/{cross_path}",
                }
            ],
        )
        with self.assertRaisesRegex(CompositeError, "crosses benchmark scope"):
            self._plan(base_manifest, overlay_manifest, overlay_inventory)

    def test_unsafe_manifest_path_is_rejected(self) -> None:
        """Manifest paths cannot escape their trusted roots."""
        manifest = {
            "files": [
                {
                    "path": "../escape",
                    "sha256": "a" * 64,
                    "size": 1,
                }
            ]
        }
        with self.assertRaisesRegex(CompositeError, "Unsafe overlay path"):
            indexed_rows(manifest, "path", "size", "overlay")

        for unsafe in ("bad\\name", "bad\x00name"):
            with self.subTest(unsafe=repr(unsafe)):
                manifest["files"][0]["path"] = unsafe
                with self.assertRaisesRegex(CompositeError, "Unsafe overlay path"):
                    indexed_rows(manifest, "path", "size", "overlay")
        for unsafe in (123, True, ["assets/mirrors/file"]):
            with self.subTest(unsafe=repr(unsafe)):
                manifest["files"][0]["path"] = unsafe
                with self.assertRaisesRegex(CompositeError, "Unsafe overlay path"):
                    indexed_rows(manifest, "path", "size", "overlay")

    def test_symlink_tree_is_rejected(self) -> None:
        """A source tree containing a symlink cannot be cloned."""
        target = self.base / "target.txt"
        target.write_bytes(b"target")
        (self.base / "link.txt").symlink_to(target)
        with self.assertRaisesRegex(CompositeError, "non-regular file"):
            validate_tree_has_no_symlinks(self.base, "base")

    def test_special_file_tree_is_rejected(self) -> None:
        """FIFO, socket, and device-like entries cannot enter a source clone."""
        fifo = self.base / "named-pipe"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(CompositeError, "non-regular file"):
            validate_tree_has_no_symlinks(self.base, "base")

    def test_existing_output_is_rejected(self) -> None:
        """The output path must be absent so a prior composite is never overwritten."""
        self.output.mkdir()
        with self.assertRaisesRegex(CompositeError, "already exists"):
            validate_root(self.output, "output", False)

    def test_release_or_live_output_is_rejected(self) -> None:
        """Composite output cannot masquerade as a canonical or live release."""
        releases = self.root / "releases"
        releases.mkdir()
        with self.assertRaisesRegex(CompositeError, "live/current/release path"):
            validate_root(releases / "candidate", "output", False)
        current_parent = self.root / "current"
        current_parent.mkdir()
        with self.assertRaisesRegex(CompositeError, "live/current/release path"):
            validate_root(current_parent / "candidate", "output", False)

    def test_tampered_overlay_conflict_is_rejected(self) -> None:
        """Both sides of a base-retained conflict must match their own manifests."""
        base_manifest = self._write_base(
            {"assets/mirrors/conflict.txt": b"current"}
        )
        overlay_manifest, overlay_inventory = self._write_overlay(
            {"assets/mirrors/conflict.txt": b"prior"}
        )
        (self.overlay / "assets/mirrors/conflict.txt").write_bytes(b"drifted")

        with self.assertRaisesRegex(CompositeError, "overlay conflict file"):
            self._build(base_manifest, overlay_manifest, overlay_inventory)
        self.assertFalse(self.output.exists())

    def test_tampered_r2_inventory_is_rejected(self) -> None:
        """The saved R2 inventory must bind the exact public-manifest closure."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay(
            {"assets/mirrors/new.bin": b"new"}
        )
        inventory = json.loads(overlay_inventory.read_text(encoding="utf-8"))
        inventory["objects"][0]["custom_metadata"]["sha256"] = "b" * 64
        _write_json(overlay_inventory, inventory)
        with self.assertRaisesRegex(CompositeError, "SHA-256 metadata mismatches"):
            self._build(base_manifest, overlay_manifest, overlay_inventory)

    def test_r2_http_metadata_drift_is_rejected(self) -> None:
        """A complete inventory with altered cache or content metadata is invalid."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay(
            {"assets/mirrors/new.bin": b"new"}
        )
        inventory = json.loads(overlay_inventory.read_text(encoding="utf-8"))
        inventory["objects"][0]["http_metadata"]["cache_control"] = "no-store"
        _write_json(overlay_inventory, inventory)
        with self.assertRaisesRegex(CompositeError, "HTTP metadata mismatches"):
            self._build(base_manifest, overlay_manifest, overlay_inventory)

    def test_boolean_size_and_uppercase_digest_are_rejected(self) -> None:
        """Manifest identities require real integers and lowercase hexadecimal digests."""
        row = {"path": "assets/mirrors/file", "sha256": "a" * 64, "size": True}
        with self.assertRaisesRegex(CompositeError, "Invalid overlay size"):
            indexed_rows({"files": [row]}, "path", "size", "overlay")
        row["size"] = 1
        row["sha256"] = "A" * 64
        with self.assertRaisesRegex(CompositeError, "Invalid overlay SHA-256"):
            indexed_rows({"files": [row]}, "path", "size", "overlay")


if __name__ == "__main__":
    unittest.main()
