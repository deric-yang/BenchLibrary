"""Tests for resumable public-release upload preparation."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.upload_public_release import (
    PublicReleaseUploader,
    ReleaseFile,
    ReleaseManifest,
    UploadFailure,
    finalize_verified_upload,
    load_manifest,
    safe_source_path,
    validate_uploader_prefix,
)


class FakeInventoryUploader(PublicReleaseUploader):
    """Return deterministic inventory pages without opening a network connection."""

    def __init__(self, pages: dict[str | None, dict[str, Any]]) -> None:
        """Store pages by the cursor used to request them."""
        self.pages = pages
        self.requested_cursors: list[str | None] = []

    def inventory_page(self, cursor: str | None = None) -> dict[str, Any]:
        """Return the fixture page associated with one cursor."""
        self.requested_cursors.append(cursor)
        return self.pages[cursor]


class UploadManifestTest(unittest.TestCase):
    """Ensure the manifest publishes and authenticates its own description."""

    def test_load_manifest_appends_self_with_computed_hash(self) -> None:
        """The non-recursive files list still results in uploading the manifest itself."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            data_directory = root / "data"
            data_directory.mkdir()
            catalog = data_directory / "catalog.json"
            catalog.write_text("{}\n", encoding="utf-8")
            catalog_bytes = catalog.read_bytes()
            manifest = data_directory / "public_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "release_id": "test-release",
                        "files": [
                            {
                                "path": "data/catalog.json",
                                "r2_key": "releases/test-release/data/catalog.json",
                                "sha256": hashlib.sha256(catalog_bytes).hexdigest(),
                                "size": len(catalog_bytes),
                            }
                        ],
                        "self": {
                            "path": "data/public_manifest.json",
                            "r2_key": "releases/test-release/data/public_manifest.json",
                        },
                    }
                ),
                encoding="utf-8",
            )

            loaded = load_manifest(manifest, root)
            by_path = {item.path: item for item in loaded.files}
            self.assertEqual(loaded.prefix, "releases/test-release/")
            self.assertEqual(set(by_path), {"data/catalog.json", "data/public_manifest.json"})
            self.assertEqual(
                by_path["data/public_manifest.json"].sha256,
                hashlib.sha256(manifest.read_bytes()).hexdigest(),
            )

    def test_rejects_manifest_r2_key_outside_release_prefix(self) -> None:
        """Every object destination must be derived from the manifest release ID."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            data_directory = root / "data"
            data_directory.mkdir()
            catalog = data_directory / "catalog.json"
            catalog.write_text("{}\n", encoding="utf-8")
            manifest = data_directory / "public_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "release_id": "right-release",
                        "files": [
                            {
                                "path": "data/catalog.json",
                                "r2_key": "releases/wrong-release/data/catalog.json",
                                "sha256": hashlib.sha256(catalog.read_bytes()).hexdigest(),
                                "size": catalog.stat().st_size,
                            }
                        ],
                        "self": {
                            "path": "data/public_manifest.json",
                            "r2_key": "releases/right-release/data/public_manifest.json",
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(UploadFailure, "R2 key"):
                load_manifest(manifest, root)

    def test_rejects_uploader_bound_to_another_release(self) -> None:
        """Health must identify the same immutable prefix as the loaded manifest."""
        loaded = ReleaseManifest("right-release", "releases/right-release/", ())
        with self.assertRaisesRegex(UploadFailure, "prefix mismatch"):
            validate_uploader_prefix({"prefix": "releases/wrong-release/"}, loaded)

    def test_rejects_symlinked_parent_directory(self) -> None:
        """A parent symlink cannot redirect upload reads outside the release root."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            root = base / "release"
            outside = base / "outside"
            (root / "assets").mkdir(parents=True)
            outside.mkdir()
            payload = outside / "payload.bin"
            payload.write_bytes(b"safe")
            (root / "assets" / "escape").symlink_to(outside, target_is_directory=True)
            item = ReleaseFile(
                "assets/escape/payload.bin",
                payload.stat().st_size,
                hashlib.sha256(payload.read_bytes()).hexdigest(),
                "application/octet-stream",
                "public, max-age=3600",
            )

            with self.assertRaisesRegex(UploadFailure, "Symlink"):
                safe_source_path(root, item)

    def test_resume_skip_still_rehashes_local_content(self) -> None:
        """A same-size mutation cannot be hidden by a prior local state record."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            assets = root / "assets"
            assets.mkdir()
            payload = assets / "payload.bin"
            payload.write_bytes(b"good")
            expected_hash = hashlib.sha256(payload.read_bytes()).hexdigest()
            item = ReleaseFile(
                "assets/payload.bin",
                4,
                expected_hash,
                "application/octet-stream",
                "public, max-age=3600",
            )
            state = root / "state.jsonl"
            state.write_text(
                json.dumps({"path": item.path, "sha256": expected_hash}) + "\n",
                encoding="utf-8",
            )
            uploader = PublicReleaseUploader("https://example.invalid", "x" * 32, None, state)
            payload.write_bytes(b"evil")

            with self.assertRaisesRegex(UploadFailure, "SHA-256 mismatch"):
                uploader.upload(root, item)

    def test_collects_every_inventory_page_before_marking_complete(self) -> None:
        """A truncated first page must be followed through its opaque cursor."""
        prefix = "releases/release-test/"
        uploader = FakeInventoryUploader({
            None: {
                "ok": True,
                "prefix": prefix,
                "objects": [{"key": f"{prefix}assets/a", "size": 2}],
                "cursor": "next-page",
                "truncated": True,
            },
            "next-page": {
                "ok": True,
                "prefix": prefix,
                "objects": [{"key": f"{prefix}data/b", "size": 3}],
                "cursor": None,
                "truncated": False,
            },
        })

        inventory = uploader.fetch_complete_inventory(prefix)

        self.assertEqual(uploader.requested_cursors, [None, "next-page"])
        self.assertTrue(inventory["complete"])
        self.assertEqual(inventory["count"], 2)
        self.assertEqual(inventory["bytes"], 5)

    def test_rejects_truncated_inventory_without_next_cursor(self) -> None:
        """An incomplete listing can never become a complete snapshot."""
        prefix = "releases/release-test/"
        uploader = FakeInventoryUploader({
            None: {
                "ok": True,
                "prefix": prefix,
                "objects": [],
                "cursor": None,
                "truncated": True,
            },
        })

        with self.assertRaisesRegex(UploadFailure, "did not return a cursor"):
            uploader.fetch_complete_inventory(prefix)

    def test_incomplete_inventory_keeps_one_time_token(self) -> None:
        """Pagination failure must leave the key available for a safe retry."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            _root, manifest_path, manifest, _catalog_hash = self._release_fixture(base)
            token_path = base / "upload.key"
            token_path.write_text("x" * 64, encoding="utf-8")
            inventory_path = base / "inventory.json"
            uploader = FakeInventoryUploader({
                None: {
                    "ok": True,
                    "prefix": manifest.prefix,
                    "objects": [],
                    "cursor": None,
                    "truncated": True,
                },
            })

            with self.assertRaisesRegex(UploadFailure, "did not return a cursor"):
                finalize_verified_upload(
                    uploader,
                    manifest,
                    manifest_path,
                    inventory_path,
                    token_path,
                    True,
                )

            self.assertTrue(token_path.is_file())
            self.assertFalse(inventory_path.exists())

    def test_failed_inventory_verification_keeps_one_time_token(self) -> None:
        """A missing R2 object must retain the key so the same upload can resume."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            root, manifest_path, manifest, catalog_hash = self._release_fixture(base)
            token_path = base / "upload.key"
            token_path.write_text("x" * 64, encoding="utf-8")
            inventory_path = base / "inventory.json"
            uploader = FakeInventoryUploader({
                None: {
                    "ok": True,
                    "prefix": manifest.prefix,
                    "objects": [{
                        "key": f"{manifest.prefix}data/catalog.json",
                        "size": 3,
                        "custom_metadata": {"sha256": catalog_hash},
                    }],
                    "cursor": None,
                    "truncated": False,
                },
            })

            with self.assertRaisesRegex(UploadFailure, "inventory verification failed"):
                finalize_verified_upload(
                    uploader,
                    manifest,
                    manifest_path,
                    inventory_path,
                    token_path,
                    True,
                )

            self.assertTrue(token_path.is_file())
            self.assertTrue(inventory_path.is_file())
            self.assertTrue(json.loads(inventory_path.read_text(encoding="utf-8"))["complete"])
            self.assertTrue(root.is_dir())

    def test_successful_inventory_verification_deletes_one_time_token(self) -> None:
        """The one-time key is removed only after exact R2 verification succeeds."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            _root, manifest_path, manifest, catalog_hash = self._release_fixture(base)
            token_path = base / "upload.key"
            token_path.write_text("x" * 64, encoding="utf-8")
            inventory_path = base / "inventory.json"
            manifest_bytes = manifest_path.read_bytes()
            uploader = FakeInventoryUploader({
                None: {
                    "ok": True,
                    "prefix": manifest.prefix,
                    "objects": [
                        {
                            "key": f"{manifest.prefix}data/catalog.json",
                            "size": 3,
                            "custom_metadata": {"sha256": catalog_hash},
                        },
                        {
                            "key": f"{manifest.prefix}data/public_manifest.json",
                            "size": len(manifest_bytes),
                            "custom_metadata": {
                                "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                            },
                        },
                    ],
                    "cursor": None,
                    "truncated": False,
                },
            })

            result = finalize_verified_upload(
                uploader,
                manifest,
                manifest_path,
                inventory_path,
                token_path,
                True,
            )

            self.assertTrue(result["ok"])
            self.assertFalse(token_path.exists())
            self.assertEqual(result["files"], 2)

    @staticmethod
    def _release_fixture(base: Path) -> tuple[Path, Path, ReleaseManifest, str]:
        """Create one minimal immutable release accepted by both upload and verification."""
        root = base / "release"
        data_directory = root / "data"
        data_directory.mkdir(parents=True)
        catalog = data_directory / "catalog.json"
        catalog.write_text("{}\n", encoding="utf-8")
        catalog_hash = hashlib.sha256(catalog.read_bytes()).hexdigest()
        manifest_path = data_directory / "public_manifest.json"
        manifest_path.write_text(
            json.dumps({
                "release_id": "release-test",
                "files": [{
                    "path": "data/catalog.json",
                    "r2_key": "releases/release-test/data/catalog.json",
                    "sha256": catalog_hash,
                    "size": catalog.stat().st_size,
                }],
                "self": {
                    "path": "data/public_manifest.json",
                    "r2_key": "releases/release-test/data/public_manifest.json",
                },
                "totals": {
                    "files": 1,
                    "logical_bytes": catalog.stat().st_size,
                },
            }),
            encoding="utf-8",
        )
        return root, manifest_path, load_manifest(manifest_path, root), catalog_hash


if __name__ == "__main__":
    unittest.main()
