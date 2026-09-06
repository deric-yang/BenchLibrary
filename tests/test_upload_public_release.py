"""Tests for resumable public-release upload preparation."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import requests

from scripts.upload_public_release import (
    MultipartUploadMissing,
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


class FakeResponse:
    """Expose the minimal successful response surface used by the uploader."""

    def __init__(self, payload: dict[str, Any]) -> None:
        """Keep a deterministic JSON response payload."""
        self.payload = payload

    def json(self) -> dict[str, Any]:
        """Return the configured response payload."""
        return self.payload


class FakeMultipartUploader(PublicReleaseUploader):
    """Emulate multipart protocol responses while retaining local resume state."""

    def __init__(
        self,
        state_path: Path,
        fail_part: int | None = None,
        invalid_complete: bool = False,
        missing_part_once: int | None = None,
    ) -> None:
        """Configure one optional interrupted part or invalid completion response."""
        super().__init__(
            "https://upload.invalid",
            "x" * 64,
            None,
            state_path,
            "releases/test-release/",
        )
        self.fail_part = fail_part
        self.invalid_complete = invalid_complete
        self.missing_part_once = missing_part_once
        self.calls: list[dict[str, Any]] = []

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        """Return deterministic protocol responses without network access."""
        route = url.rsplit("/", maxsplit=1)[-1]
        headers = kwargs.get("headers", {})
        call = {
            "route": route,
            "method": method,
            "part": headers.get("X-KWBL-Part-Number"),
            "upload_id": headers.get("X-KWBL-Upload-Id"),
            "json": kwargs.get("json"),
        }
        self.calls.append(call)
        if route == "init":
            return FakeResponse({"ok": True, "skipped": False, "uploadId": "upload-one"})
        if route == "part":
            part_number = int(headers["X-KWBL-Part-Number"])
            if part_number == self.missing_part_once:
                self.missing_part_once = None
                raise MultipartUploadMissing("simulated expired multipart upload")
            if part_number == self.fail_part:
                raise UploadFailure("simulated interrupted multipart part")
            return FakeResponse({"ok": True, "partNumber": part_number, "etag": f"etag-{part_number}"})
        if route == "complete":
            sha256 = "0" * 64 if self.invalid_complete else headers["X-KWBL-SHA256"]
            return FakeResponse({
                "ok": True,
                "size": int(headers["X-KWBL-Object-Size"]),
                "sha256": sha256,
            })
        if route == "abort":
            return FakeResponse({"ok": True})
        raise AssertionError(f"Unexpected multipart route: {route}")


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
                json.dumps({
                    "path": item.path,
                    "prefix": "releases/test-release/",
                    "sha256": expected_hash,
                }) + "\n",
                encoding="utf-8",
            )
            uploader = PublicReleaseUploader(
                "https://example.invalid",
                "x" * 32,
                None,
                state,
                "releases/test-release/",
            )
            payload.write_bytes(b"evil")

            with self.assertRaisesRegex(UploadFailure, "SHA-256 mismatch"):
                uploader.upload(root, item)

    def test_resume_state_is_bound_to_one_release_prefix(self) -> None:
        """A state file from another immutable release cannot suppress uploads."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = Path(temporary_directory) / "state.jsonl"
            state.write_text(
                json.dumps({
                    "event": "complete",
                    "path": "assets/payload.bin",
                    "prefix": "releases/old-release/",
                    "sha256": "a" * 64,
                }) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(UploadFailure, "Invalid upload state"):
                PublicReleaseUploader(
                    "https://example.invalid",
                    "x" * 32,
                    None,
                    state,
                    "releases/new-release/",
                )

    def test_object_encoding_metadata_is_not_used_as_request_encoding(self) -> None:
        """Gzip metadata stays namespaced so multipart JSON and slices are not decoded."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            uploader = PublicReleaseUploader(
                "https://example.invalid",
                "x" * 32,
                None,
                Path(temporary_directory) / "state.jsonl",
                "releases/test-release/",
            )
            item = ReleaseFile(
                "assets/archive.json.gz",
                12,
                "a" * 64,
                "application/json",
                "public, max-age=31536000, immutable",
                "gzip",
                "attachment; filename=archive.json.gz",
            )

            headers = uploader._headers(item)

            self.assertEqual(headers["X-KWBL-Content-Encoding"], "gzip")
            self.assertEqual(headers["X-KWBL-Content-Type"], "application/json")
            self.assertNotIn("Content-Encoding", headers)
            self.assertNotIn("Content-Type", headers)

    def test_empty_direct_upload_uses_literal_body_without_chunked_encoding(self) -> None:
        """An empty direct object must not combine length zero with a streamed body."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "empty.bin"
            source.write_bytes(b"")
            uploader = PublicReleaseUploader(
                "https://example.invalid",
                "x" * 32,
                None,
                root / "state.jsonl",
                "releases/test-release/",
            )
            item = ReleaseFile(
                "assets/empty.bin",
                0,
                hashlib.sha256(b"").hexdigest(),
                "application/octet-stream",
                "public, max-age=31536000, immutable",
            )
            captured: dict[str, Any] = {}

            def capture_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
                """Capture the direct upload request without opening a connection."""
                captured.update({"method": method, "url": url, **kwargs})
                return FakeResponse({"ok": True, "skipped": False})

            with mock.patch.object(uploader, "_request_with_retry", side_effect=capture_request):
                self.assertEqual(uploader._put_direct(source, item), "uploaded")

            self.assertEqual(captured["data"], b"")
            self.assertNotIn("data_factory", captured)
            prepared = requests.Request(
                captured["method"],
                captured["url"],
                headers=captured["headers"],
                data=captured["data"],
            ).prepare()
            self.assertEqual(prepared.headers["Content-Length"], "0")
            self.assertNotIn("Transfer-Encoding", prepared.headers)

    def test_nonempty_direct_upload_still_uses_reopenable_stream(self) -> None:
        """Non-empty direct uploads retain a fresh file stream for every retry."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "payload.bin"
            source.write_bytes(b"payload")
            uploader = PublicReleaseUploader(
                "https://example.invalid",
                "x" * 32,
                None,
                root / "state.jsonl",
                "releases/test-release/",
            )
            item = ReleaseFile(
                "assets/payload.bin",
                source.stat().st_size,
                hashlib.sha256(source.read_bytes()).hexdigest(),
                "application/octet-stream",
                "public, max-age=31536000, immutable",
            )
            captured: dict[str, Any] = {}

            def capture_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
                """Capture the direct upload request without opening a connection."""
                captured.update({"method": method, "url": url, **kwargs})
                return FakeResponse({"ok": True, "skipped": False})

            with mock.patch.object(uploader, "_request_with_retry", side_effect=capture_request):
                self.assertEqual(uploader._put_direct(source, item), "uploaded")

            self.assertNotIn("data", captured)
            data_factory = captured["data_factory"]
            with data_factory() as first_stream:
                self.assertEqual(first_stream.read(), b"payload")
            with data_factory() as second_stream:
                self.assertEqual(second_stream.read(), b"payload")

    def test_multipart_interruption_resumes_only_missing_parts(self) -> None:
        """Acknowledged part ETags survive a process restart and are not uploaded twice."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, item, state_path = self._multipart_fixture(Path(temporary_directory))
            with mock.patch.multiple(
                "scripts.upload_public_release",
                DIRECT_LIMIT=8,
                PART_SIZE=5,
            ):
                interrupted = FakeMultipartUploader(state_path, fail_part=2)
                with self.assertRaisesRegex(UploadFailure, "interrupted"):
                    interrupted.upload(root, item)
                self.assertNotIn("abort", [call["route"] for call in interrupted.calls])
                checkpoint = json.loads(state_path.read_text(encoding="utf-8").splitlines()[-1])
                self.assertEqual(checkpoint["upload_id"], "upload-one")
                self.assertEqual(checkpoint["parts"], [{"partNumber": 1, "etag": "etag-1"}])
                self.assertRegex(checkpoint["metadata_sha256"], r"^[a-f0-9]{64}$")

                resumed = FakeMultipartUploader(state_path)
                self.assertEqual(resumed.upload(root, item), "uploaded")
                routes = [call["route"] for call in resumed.calls]
                self.assertNotIn("init", routes)
                self.assertEqual(
                    [call["part"] for call in resumed.calls if call["route"] == "part"],
                    ["2", "3"],
                )
                complete = next(call for call in resumed.calls if call["route"] == "complete")
                self.assertEqual(
                    complete["json"]["parts"],
                    [
                        {"partNumber": 1, "etag": "etag-1"},
                        {"partNumber": 2, "etag": "etag-2"},
                        {"partNumber": 3, "etag": "etag-3"},
                    ],
                )
                final_record = json.loads(state_path.read_text(encoding="utf-8").splitlines()[-1])
                self.assertEqual(final_record["event"], "complete")

    def test_multipart_resume_rehashes_before_any_network_request(self) -> None:
        """A same-size local mutation stops a resumed multipart upload before HTTP."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, item, state_path = self._multipart_fixture(Path(temporary_directory))
            with mock.patch.multiple(
                "scripts.upload_public_release",
                DIRECT_LIMIT=8,
                PART_SIZE=5,
            ):
                interrupted = FakeMultipartUploader(state_path, fail_part=2)
                with self.assertRaises(UploadFailure):
                    interrupted.upload(root, item)
                (root / item.path).write_bytes(b"XXXXXXXXXXXX")

                resumed = FakeMultipartUploader(state_path)
                with self.assertRaisesRegex(UploadFailure, "SHA-256 mismatch"):
                    resumed.upload(root, item)
                self.assertEqual(resumed.calls, [])

    def test_invalid_completion_keeps_resumable_parts(self) -> None:
        """A failed final-object check cannot be recorded as a completed object."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, item, state_path = self._multipart_fixture(Path(temporary_directory))
            with mock.patch.multiple(
                "scripts.upload_public_release",
                DIRECT_LIMIT=8,
                PART_SIZE=5,
            ):
                invalid = FakeMultipartUploader(state_path, invalid_complete=True)
                with self.assertRaisesRegex(UploadFailure, "final R2 object"):
                    invalid.upload(root, item)
                record = json.loads(state_path.read_text(encoding="utf-8").splitlines()[-1])
                self.assertEqual(record["event"], "multipart")
                self.assertEqual(len(record["parts"]), 3)

                resumed = FakeMultipartUploader(state_path)
                self.assertEqual(resumed.upload(root, item), "uploaded")
                self.assertEqual([call["route"] for call in resumed.calls], ["complete"])

    def test_expired_multipart_checkpoint_restarts_once(self) -> None:
        """A known-expired R2 upload is tombstoned and replaced without manual cleanup."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, item, state_path = self._multipart_fixture(Path(temporary_directory))
            with mock.patch.multiple(
                "scripts.upload_public_release",
                DIRECT_LIMIT=8,
                PART_SIZE=5,
            ):
                uploader = FakeMultipartUploader(state_path, missing_part_once=2)
                self.assertEqual(uploader.upload(root, item), "uploaded")
                self.assertEqual(
                    [call["route"] for call in uploader.calls],
                    ["init", "part", "part", "init", "part", "part", "part", "complete"],
                )
                events = [
                    json.loads(line)["event"]
                    for line in state_path.read_text(encoding="utf-8").splitlines()
                ]
                self.assertIn("abort", events)
                self.assertEqual(events[-1], "complete")

    def test_stable_worker_conflict_maps_to_missing_upload_signal(self) -> None:
        """The Worker 409 code triggers restart logic instead of a permanent generic failure."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            uploader = PublicReleaseUploader(
                "https://example.invalid",
                "x" * 32,
                None,
                Path(temporary_directory) / "state.jsonl",
                "releases/test-release/",
            )
            response = mock.Mock(
                status_code=409,
                headers={},
            )
            response.json.return_value = {
                "ok": False,
                "code": "multipart_upload_missing",
            }
            session = mock.Mock()
            session.request.return_value = response

            with mock.patch.object(uploader, "_session", return_value=session):
                with self.assertRaises(MultipartUploadMissing):
                    uploader._request_with_retry("PUT", "https://example.invalid/part")

    def test_changed_multipart_metadata_is_aborted_before_replacement(self) -> None:
        """A checkpoint initialized with different HTTP metadata is never resumed."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, item, state_path = self._multipart_fixture(Path(temporary_directory))
            state_path.write_text(
                json.dumps({
                    "event": "multipart",
                    "path": item.path,
                    "prefix": "releases/test-release/",
                    "sha256": item.sha256,
                    "size": item.size,
                    "part_size": 5,
                    "metadata_sha256": "0" * 64,
                    "upload_id": "old-upload",
                    "parts": [],
                }) + "\n",
                encoding="utf-8",
            )
            with mock.patch.multiple(
                "scripts.upload_public_release",
                DIRECT_LIMIT=8,
                PART_SIZE=5,
            ):
                uploader = FakeMultipartUploader(state_path)
                self.assertEqual(uploader.upload(root, item), "uploaded")
                self.assertEqual(
                    [call["route"] for call in uploader.calls],
                    ["abort", "init", "part", "part", "part", "complete"],
                )

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

    @staticmethod
    def _multipart_fixture(base: Path) -> tuple[Path, ReleaseFile, Path]:
        """Create one tiny file whose thresholds can be patched into three parts."""
        root = base / "release"
        assets = root / "assets"
        assets.mkdir(parents=True)
        payload = assets / "payload.bin"
        payload.write_bytes(b"abcdefghijkl")
        sha256 = hashlib.sha256(payload.read_bytes()).hexdigest()
        item = ReleaseFile(
            "assets/payload.bin",
            payload.stat().st_size,
            sha256,
            "application/octet-stream",
            "public, max-age=31536000, immutable",
        )
        return root, item, base / "upload-state.jsonl"


if __name__ == "__main__":
    unittest.main()
