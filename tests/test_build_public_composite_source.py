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
        _write_json(self.policy, {"policy_id": "public-v3"})

    def tearDown(self) -> None:
        """Remove the isolated fixture tree."""
        self.temporary_directory.cleanup()

    def _write_base(self, files: dict[str, bytes]) -> Path:
        """Write base files and their immutable release manifest."""
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

    def _write_overlay(self, files: dict[str, bytes]) -> tuple[Path, Path]:
        """Write prior-public files, public manifest, and saved R2 inventory."""
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
                "assets/mirror_index.json": b"old root index",
                "assets/mirrors/conflict.txt": b"prior",
                "assets/mirrors/new.bin": b"new mirror",
                "assets/mirrors/same.txt": b"same",
                "assets/other/not-allowed.bin": b"other namespace",
                "assets/previews/text/new.txt": b"new preview",
                "assets/verifiers/sources/new.py": b"new verifier",
                "data/catalog.json": b"old catalog",
                "site/app.js": b"old site",
            }
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
            (self.output / "assets/mirrors/new.bin").read_bytes(),
            b"new mirror",
        )
        self.assertFalse((self.output / "assets/index_shards/mirror/old.json").exists())
        self.assertFalse((self.output / "assets/other/not-allowed.bin").exists())
        self.assertEqual((self.output / "data/catalog.json").read_bytes(), b"current catalog")
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
        self.assertEqual(
            (self.output / ".kwbl-composite-provenance.json").stat().st_mode & 0o777,
            0o644,
        )

    def test_tampered_overlay_addition_fails_before_final_output(self) -> None:
        """An overlay file whose bytes drifted from its manifest cannot be installed."""
        base_manifest = self._write_base({"data/catalog.json": b"base"})
        overlay_manifest, overlay_inventory = self._write_overlay(
            {"assets/mirrors/new.bin": b"expected"}
        )
        (self.overlay / "assets/mirrors/new.bin").write_bytes(b"tampered")

        with self.assertRaisesRegex(CompositeError, "overlay addition SHA-256 mismatch"):
            self._build(base_manifest, overlay_manifest, overlay_inventory)
        self.assertFalse(self.output.exists())

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
