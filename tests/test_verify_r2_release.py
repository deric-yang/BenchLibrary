"""Tests for complete post-upload R2 inventory verification."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.verify_r2_release import VerificationError, verify_release


class R2ReleaseVerificationTest(unittest.TestCase):
    """Exercise exact inventory matching and fail-closed input checks."""

    def setUp(self) -> None:
        """Create one manifest whose self object is not in its files array."""
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.manifest_path = self.root / "public_manifest.json"
        self.inventory_path = self.root / "inventory.json"
        self.release_id = "release-test"
        self.prefix = f"releases/{self.release_id}/"
        self.catalog_bytes = b"{}\n"
        self.catalog_hash = hashlib.sha256(self.catalog_bytes).hexdigest()
        self.manifest = {
            "release_id": self.release_id,
            "files": [
                {
                    "cache_control": "public, max-age=300, must-revalidate",
                    "content_type": "application/json; charset=utf-8",
                    "path": "data/catalog.json",
                    "r2_key": f"{self.prefix}data/catalog.json",
                    "sha256": self.catalog_hash,
                    "size": len(self.catalog_bytes),
                }
            ],
            "self": {
                "path": "data/public_manifest.json",
                "r2_key": f"{self.prefix}data/public_manifest.json",
            },
            "totals": {
                "files": 1,
                "logical_bytes": len(self.catalog_bytes),
            },
        }
        self._write_manifest()

    def tearDown(self) -> None:
        """Remove the isolated fixture directory."""
        self.temporary_directory.cleanup()

    def _write_manifest(self) -> None:
        """Serialize the mutable manifest fixture deterministically."""
        self.manifest_path.write_text(
            json.dumps(self.manifest, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _inventory(self) -> dict[str, Any]:
        """Build an exact complete R2 inventory for the current manifest bytes."""
        manifest_bytes = self.manifest_path.read_bytes()
        objects = [
            {
                "key": f"{self.prefix}data/catalog.json",
                "size": len(self.catalog_bytes),
                "custom_metadata": {"sha256": self.catalog_hash},
                "http_metadata": {
                    "cache_control": "public, max-age=300, must-revalidate",
                    "content_disposition": "",
                    "content_encoding": "",
                    "content_type": "application/json; charset=utf-8",
                },
            },
            {
                "key": f"{self.prefix}data/public_manifest.json",
                "size": len(manifest_bytes),
                "customMetadata": {"sha256": hashlib.sha256(manifest_bytes).hexdigest()},
                "http_metadata": {
                    "cache_control": "public, max-age=300, must-revalidate",
                    "content_disposition": "",
                    "content_encoding": "",
                    "content_type": "application/json; charset=utf-8",
                },
            },
        ]
        return {
            "schema_version": 1,
            "complete": True,
            "prefix": self.prefix,
            "count": len(objects),
            "bytes": sum(item["size"] for item in objects),
            "objects": objects,
        }

    def _write_inventory(self, payload: dict[str, Any]) -> None:
        """Write one inventory snapshot for verification."""
        self.inventory_path.write_text(json.dumps(payload), encoding="utf-8")

    def test_accepts_exact_complete_inventory_including_manifest_self(self) -> None:
        """All expected objects, bytes, and hashes produce a success summary."""
        inventory = self._inventory()
        self._write_inventory(inventory)

        result = verify_release(self.manifest_path, self.inventory_path)

        self.assertTrue(result["ok"])
        self.assertEqual(result["files"], 2)
        self.assertEqual(result["bytes"], inventory["bytes"])
        self.assertEqual(result["prefix"], self.prefix)

    def test_rejects_inventory_not_marked_complete(self) -> None:
        """A partial page cannot accidentally pass as a complete inventory."""
        inventory = self._inventory()
        inventory["complete"] = False
        self._write_inventory(inventory)

        with self.assertRaisesRegex(VerificationError, "not marked complete"):
            verify_release(self.manifest_path, self.inventory_path)

    def test_rejects_missing_and_unexpected_keys(self) -> None:
        """The object-key set must match the manifest exactly."""
        inventory = self._inventory()
        inventory.pop("count")
        inventory.pop("bytes")
        inventory["objects"][0]["key"] = f"{self.prefix}assets/unexpected.bin"
        self._write_inventory(inventory)

        with self.assertRaisesRegex(VerificationError, "missing 1 keys"):
            verify_release(self.manifest_path, self.inventory_path)

    def test_rejects_size_mismatch(self) -> None:
        """An object with the right key but wrong byte length must fail."""
        inventory = self._inventory()
        inventory.pop("bytes")
        inventory["objects"][0]["size"] += 1
        self._write_inventory(inventory)

        with self.assertRaisesRegex(VerificationError, "size mismatches"):
            verify_release(self.manifest_path, self.inventory_path)

    def test_rejects_sha256_custom_metadata_mismatch(self) -> None:
        """An object body identity mismatch cannot be hidden by key and size."""
        inventory = self._inventory()
        inventory["objects"][0]["custom_metadata"]["sha256"] = "0" * 64
        self._write_inventory(inventory)

        with self.assertRaisesRegex(VerificationError, "SHA-256 metadata mismatches"):
            verify_release(self.manifest_path, self.inventory_path)

    def test_rejects_content_disposition_mismatch(self) -> None:
        """A lost download-only attachment policy cannot pass final verification."""
        self.manifest["files"][0]["content_disposition"] = "attachment"
        self._write_manifest()
        inventory = self._inventory()
        self._write_inventory(inventory)

        with self.assertRaisesRegex(VerificationError, "HTTP metadata mismatches"):
            verify_release(self.manifest_path, self.inventory_path)

    def test_rejects_duplicate_inventory_key(self) -> None:
        """Duplicate listing records cannot distort count or byte totals."""
        inventory = self._inventory()
        inventory.pop("count")
        inventory.pop("bytes")
        inventory["objects"].append(dict(inventory["objects"][0]))
        self._write_inventory(inventory)

        with self.assertRaisesRegex(VerificationError, "duplicate key"):
            verify_release(self.manifest_path, self.inventory_path)

    def test_rejects_manifest_totals_that_do_not_match_files(self) -> None:
        """A malformed expected count must fail before the R2 snapshot is trusted."""
        self.manifest["totals"]["files"] = 2
        self._write_manifest()
        self._write_inventory(self._inventory())

        with self.assertRaisesRegex(VerificationError, "totals.files"):
            verify_release(self.manifest_path, self.inventory_path)


if __name__ == "__main__":
    unittest.main()
