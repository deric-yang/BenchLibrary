"""Tests for anonymous public-release HTTP smoke validation."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from requests.structures import CaseInsensitiveDict

from scripts.smoke_public_release import (
    DEFAULT_SPEC,
    PRIVATE_PATHS,
    AnonymousClient,
    AnomalyProbe,
    GameCraftProbe,
    ObjectProbe,
    PublicReleaseSmoke,
    ReleaseSpec,
    SmokeFailure,
    TaskProbe,
    VariantCount,
    smoke_public_release,
)


class FakeCookies:
    """Expose the cookie-clear operation used by the anonymous client."""

    def __init__(self) -> None:
        """Initialize a clear-operation counter."""
        self.clear_count = 0

    def clear(self) -> None:
        """Record that no cookies should survive between requests."""
        self.clear_count += 1


class FakeResponse:
    """Provide the small response surface consumed by the smoke runner."""

    def __init__(
        self,
        status_code: int,
        content: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        """Store an immutable fake HTTP response."""
        self.status_code = status_code
        self.content = content
        self.headers = CaseInsensitiveDict(headers or {})

    def json(self) -> Any:
        """Decode the fake response body as JSON."""
        return json.loads(self.content.decode("utf-8"))


class FakeSession:
    """Route anonymous GET requests to deterministic fake responses."""

    def __init__(self) -> None:
        """Initialize headers, cookies, and a path/range response table."""
        self.headers: dict[str, str] = {}
        self.cookies = FakeCookies()
        self.proxies: dict[str, str] = {}
        self.routes: dict[tuple[str, str | None], FakeResponse] = {}
        self.requests: list[tuple[str, str | None]] = []

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        allow_redirects: bool = True,
    ) -> FakeResponse:
        """Return the response registered for the decoded path and range."""
        del timeout
        self.assert_anonymous(headers or {})
        if allow_redirects:
            raise AssertionError("Smoke requests must disable redirects")
        path = unquote(urlsplit(url).path)
        byte_range = (headers or {}).get("Range")
        self.requests.append((path, byte_range))
        try:
            return self.routes[(path, byte_range)]
        except KeyError as error:
            raise AssertionError(f"No fake route for {(path, byte_range)!r}") from error

    def assert_anonymous(self, headers: dict[str, str]) -> None:
        """Fail if the smoke runner attempts to add authentication state."""
        combined = {key.lower(): value for key, value in {**self.headers, **headers}.items()}
        if "authorization" in combined or "cookie" in combined:
            raise AssertionError("Smoke request was not anonymous")


class PublicReleaseSmokeTest(unittest.TestCase):
    """Exercise the complete contract with an isolated HTTP origin."""

    def setUp(self) -> None:
        """Build one small but structurally complete public release."""
        self.release_id = "test-public-release"
        self.original_path = "assets/mirrors/sample/task/original.xlsx"
        self.preview_path = "assets/previews/sample/task/preview.html"
        self.anomaly_path = "assets/mirrors/sample/task/upstream.zip"
        self.original_body = b"PK\x03\x04" + b"o" * 60
        self.preview_body = b"<html" + b"p" * 59
        self.anomaly_range = b"PK\x03\x04" + b"a" * 28
        self.original_sha = hashlib.sha256(self.original_body).hexdigest()
        self.preview_sha = hashlib.sha256(self.preview_body).hexdigest()
        self.anomaly_sha = "a" * 64
        self.spec = ReleaseSpec(
            policy_id="test-policy",
            catalog_benchmarks=1,
            expanded_benchmarks=1,
            full_records=1,
            task_probes=(
                TaskProbe(
                    "Sample Benchmark",
                    "sample",
                    1,
                    "task-1",
                    self.original_path,
                    self.preview_path,
                ),
            ),
            variant_counts=(VariantCount("sample", "full", "question", 1),),
            object_probes=(
                ObjectProbe(
                    "sample original",
                    self.original_path,
                    len(self.original_body),
                    self.original_sha,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    b"PK\x03\x04",
                ),
                ObjectProbe(
                    "sample preview",
                    self.preview_path,
                    len(self.preview_body),
                    self.preview_sha,
                    "text/html; charset=utf-8",
                    b"<html",
                    require_preview_csp=True,
                ),
            ),
            anomaly_probes=(
                AnomalyProbe(
                    "sample anomaly",
                    self.anomaly_path,
                    self.anomaly_sha,
                    "application/zip",
                    b"PK\x03\x04",
                    "opaque_archive_download",
                    "task-1",
                    size=33554432,
                ),
            ),
        )
        self.session = FakeSession()
        self._register_ui()
        self._register_catalog()
        self._register_indexes()
        self._register_objects()

    def _json_response(self, payload: dict[str, Any]) -> FakeResponse:
        """Serialize one compact JSON response."""
        return FakeResponse(
            200,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            {"Content-Type": "application/json; charset=utf-8"},
        )

    def _register_ui(self) -> None:
        """Register the public shell, application code, and hidden paths."""
        home_headers = {
            "Content-Type": "text/html; charset=utf-8",
            "Content-Security-Policy": "default-src 'self'; connect-src 'self'",
        }
        self.session.routes[("/", None)] = FakeResponse(
            200,
            b"<!doctype html><title>KW Bench Library</title>",
            home_headers,
        )
        self.session.routes[("/app.js", None)] = FakeResponse(
            200,
            b"console.log('public catalog');",
            {"Content-Type": "text/javascript; charset=utf-8"},
        )
        self.session.routes[("/public-config.js", None)] = FakeResponse(
            200,
            b"globalThis.BENCH_MONITOR_PUBLIC_MODE = true;",
            {"Content-Type": "text/javascript; charset=utf-8"},
        )
        for path in PRIVATE_PATHS:
            self.session.routes[(path, None)] = FakeResponse(404, b'{"error":"Not found"}')

    def _register_catalog(self) -> None:
        """Register a one-benchmark catalog and its task shard."""
        self.session.routes[("/data/catalog.json", None)] = self._json_response({
            "totals": {"benchmarks": 1, "expanded_benchmarks": 1, "records": 1},
            "public_release": {
                "release_id": self.release_id,
                "policy_id": "test-policy",
                "full_benchmarks": 1,
                "link_only_benchmarks": 0,
                "metadata_only_benchmarks": 0,
            },
            "benchmarks": [{"id": "sample"}],
        })
        self.session.routes[("/data/benches/sample.json", None)] = self._json_response({
            "benchmark_id": "sample",
            "record_count": 1,
            "tasks": [
                {
                    "id": "task-1",
                    "variant_id": "full",
                    "unit_kind": "question",
                }
            ],
        })

    def _register_indexes(self) -> None:
        """Register task-sharded mappings and root anomaly warnings."""
        shard_map = {
            "by_bench": {
                "sample": {
                    "tasks": {"task-1": "assets/index_shards/{kind}/sample-task.json"},
                }
            }
        }
        anomaly_common = {
            "integrity_status": "upstream-anomaly-pinned-v1",
            "integrity_handling": "opaque_archive_download",
            "integrity_note_zh": "上游固定对象异常，仅供下载核验。",
        }
        mirror_root = {
            "public_release": {"release_id": self.release_id},
            "records": [
                {
                    "view_path": self.anomaly_path,
                    "task_id": "task-1",
                    "task_ids": ["task-1"],
                    **anomaly_common,
                }
            ],
            "record_shards": json.loads(json.dumps(shard_map).replace("{kind}", "mirror")),
        }
        preview_root = {
            "public_release": {"release_id": self.release_id},
            "records": [
                {
                    "preview_url": self.anomaly_path,
                    "preview_kind": "download_only",
                    "source_size": 33554432,
                    "source_sha256": self.anomaly_sha,
                    "task_id": "task-1",
                    "task_ids": ["task-1"],
                    **anomaly_common,
                }
            ],
            "record_shards": json.loads(json.dumps(shard_map).replace("{kind}", "preview")),
        }
        self.session.routes[("/assets/mirror_index.json", None)] = self._json_response(mirror_root)
        self.session.routes[("/assets/preview_index.json", None)] = self._json_response(preview_root)
        self.session.routes[("/assets/verifier_source_index.json", None)] = self._json_response({
            "public_release": {"release_id": self.release_id},
            "records": [],
            "record_shards": {},
        })
        self.session.routes[("/assets/index_shards/mirror/sample-task.json", None)] = self._json_response({
            "records": [{"view_path": self.original_path, "task_id": "task-1"}],
        })
        self.session.routes[("/assets/index_shards/preview/sample-task.json", None)] = self._json_response({
            "records": [
                {
                    "source_view_path": self.original_path,
                    "preview_url": self.preview_path,
                    "task_id": "task-1",
                }
            ],
        })

    def _object_headers(
        self,
        size: int,
        sha256: str,
        content_type: str,
        ranged: bool,
        attachment: bool = False,
        preview_csp: bool = False,
    ) -> dict[str, str]:
        """Build exact Worker response headers for one object request."""
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(32 if ranged else size),
            "Content-Type": content_type,
            "X-Content-SHA256": sha256,
            "X-Content-Type-Options": "nosniff",
            "Cross-Origin-Resource-Policy": "same-origin",
        }
        if ranged:
            headers["Content-Range"] = f"bytes 0-31/{size}"
        if attachment:
            headers["Content-Disposition"] = "attachment"
        if preview_csp:
            headers["Content-Security-Policy"] = (
                "sandbox allow-scripts; connect-src 'none'; default-src 'none'"
            )
        return headers

    def _register_regular_object(self, probe: ObjectProbe, body: bytes) -> None:
        """Register full and 32-byte responses for one regular object."""
        range_headers = self._object_headers(
            probe.size,
            probe.sha256,
            probe.content_type,
            True,
            preview_csp=probe.require_preview_csp,
        )
        full_headers = self._object_headers(
            probe.size,
            probe.sha256,
            probe.content_type,
            False,
            preview_csp=probe.require_preview_csp,
        )
        self.session.routes[(f"/{probe.path}", "bytes=0-31")] = FakeResponse(
            206,
            body[:32],
            range_headers,
        )
        self.session.routes[(f"/{probe.path}", None)] = FakeResponse(200, body, full_headers)

    def _register_objects(self) -> None:
        """Register representative bodies and a range-only anomaly."""
        self._register_regular_object(self.spec.object_probes[0], self.original_body)
        self._register_regular_object(self.spec.object_probes[1], self.preview_body)
        anomaly = self.spec.anomaly_probes[0]
        headers = self._object_headers(
            anomaly.size,
            anomaly.sha256,
            anomaly.content_type,
            True,
            attachment=True,
        )
        self.session.routes[(f"/{anomaly.path}", "bytes=0-31")] = FakeResponse(
            206,
            self.anomaly_range,
            headers,
        )

    def _run(self) -> dict[str, Any]:
        """Run the fixture's custom release contract."""
        return smoke_public_release(
            "https://public.example",
            self.release_id,
            timeout=1,
            spec=self.spec,
            session=self.session,
        )

    def test_accepts_complete_anonymous_release(self) -> None:
        """Exact counts, mappings, objects, and anomaly handling pass."""
        result = self._run()

        self.assertTrue(result["ok"])
        self.assertEqual(result["release_id"], self.release_id)
        self.assertEqual(result["representative_tasks"], 1)
        self.assertEqual(result["objects_full_hash_checked"], 2)
        self.assertEqual(result["upstream_anomalies_checked"], 1)
        self.assertGreater(self.session.cookies.clear_count, len(self.session.requests))

    def test_rejects_unexpected_release_pointer(self) -> None:
        """A stale or wrong production release binding fails immediately."""
        with self.assertRaisesRegex(SmokeFailure, "unexpected release"):
            smoke_public_release(
                "https://public.example",
                "different-release",
                timeout=1,
                spec=self.spec,
                session=self.session,
            )

    def test_rejects_exposed_private_route(self) -> None:
        """A login or operator route cannot appear on the public origin."""
        self.session.routes[("/login", None)] = FakeResponse(200, b"login")

        with self.assertRaisesRegex(SmokeFailure, "Private path /login"):
            self._run()

    def test_rejects_operator_marker_in_application(self) -> None:
        """Operator-only credential language cannot leak into the UI bundle."""
        self.session.routes[("/app.js", None)] = FakeResponse(
            200,
            b"const label = 'Contributor Key';",
            {"Content-Type": "text/javascript; charset=utf-8"},
        )

        with self.assertRaisesRegex(SmokeFailure, "Contributor Key"):
            self._run()

    def test_rejects_full_object_body_sha_mismatch(self) -> None:
        """A valid-looking metadata header cannot hide corrupted object bytes."""
        probe = self.spec.object_probes[0]
        corrupted = self.original_body[:-1] + b"x"
        headers = self._object_headers(
            probe.size,
            probe.sha256,
            probe.content_type,
            False,
        )
        self.session.routes[(f"/{probe.path}", None)] = FakeResponse(200, corrupted, headers)

        with self.assertRaisesRegex(SmokeFailure, "Full body SHA-256"):
            self._run()

    def test_rejects_anomaly_without_download_only_index_policy(self) -> None:
        """A pinned anomaly must not silently become an embeddable preview."""
        response = self.session.routes[("/assets/preview_index.json", None)]
        payload = response.json()
        payload["records"][0]["preview_kind"] = "native"
        self.session.routes[("/assets/preview_index.json", None)] = self._json_response(payload)

        with self.assertRaisesRegex(SmokeFailure, "not download-only"):
            self._run()

    def test_rejects_anomaly_without_attachment_header(self) -> None:
        """Known incomplete upstream bytes must remain forced downloads."""
        anomaly = self.spec.anomaly_probes[0]
        headers = self._object_headers(
            anomaly.size,
            anomaly.sha256,
            anomaly.content_type,
            True,
            attachment=False,
        )
        self.session.routes[(f"/{anomaly.path}", "bytes=0-31")] = FakeResponse(
            206,
            self.anomaly_range,
            headers,
        )

        with self.assertRaisesRegex(SmokeFailure, "Attachment policy"):
            self._run()

    def test_rejects_non_https_and_embedded_credentials(self) -> None:
        """The smoke origin cannot downgrade transport or carry user info."""
        with self.assertRaisesRegex(SmokeFailure, "must use HTTPS"):
            smoke_public_release(
                "http://public.example",
                self.release_id,
                spec=self.spec,
                session=self.session,
            )
        with self.assertRaisesRegex(SmokeFailure, "must not contain credentials"):
            smoke_public_release(
                "https://user:password@public.example",
                self.release_id,
                spec=self.spec,
                session=self.session,
            )

    def test_default_spec_covers_requested_public_release(self) -> None:
        """The checked-in production contract names every requested benchmark."""
        benchmarks = {probe.benchmark_id for probe in DEFAULT_SPEC.task_probes}
        gamecraft = DEFAULT_SPEC.gamecraft_probe
        self.assertIsNotNone(gamecraft)
        if gamecraft is not None:
            benchmarks.add(gamecraft.benchmark_id)
        office_variants = {
            (variant.variant_id, variant.unit_kind, variant.count)
            for variant in DEFAULT_SPEC.variant_counts
            if variant.benchmark_id == "officeqa"
        }

        self.assertEqual(
            benchmarks,
            {
                "artifactsbench",
                "gamecraft-bench",
                "gdpval",
                "officeqa",
                "workbuddybench-office",
            },
        )
        self.assertEqual(
            office_variants,
            {
                ("full", "question", 246),
                ("pro_v2", "question", 90),
                ("protocol", "experiment_mode", 4),
            },
        )
        self.assertEqual(len(DEFAULT_SPEC.object_probes), 8)
        self.assertEqual(len(DEFAULT_SPEC.anomaly_probes), 4)
        self.assertEqual(DEFAULT_SPEC.policy_id, "kw-bench-library-public-v3")
        self.assertEqual(DEFAULT_SPEC.catalog_benchmarks, 32)
        self.assertEqual(DEFAULT_SPEC.expanded_benchmarks, 30)
        self.assertEqual(DEFAULT_SPEC.full_records, 10161)
        if gamecraft is not None:
            self.assertEqual(
                gamecraft.source_revision,
                "a43347534374df9a0c1a6c001aa9380862783f6d",
            )
            self.assertEqual(gamecraft.expected_task_directories, 141)
            self.assertEqual(len(gamecraft.expected_family_counts), 15)
            self.assertEqual(sum(dict(gamecraft.expected_family_counts).values()), 140)
            self.assertEqual(gamecraft.expected_title_zh, (("horror-floor-13", "恐怖 13 层"),))
            self.assertEqual(dict(gamecraft.expected_status_counts), {
                "generator_source_only": 98,
                "not_published": 4,
                "repository_files": 38,
            })
            self.assertEqual(len(gamecraft.missing_gold_task_ids), 4)

    def test_anonymous_client_disables_environment_auth_discovery(self) -> None:
        """Netrc credentials and environment proxies cannot enter an anonymous smoke request."""
        self.session.trust_env = True

        AnonymousClient(
            "https://public.example",
            1,
            proxy="http://explicit-proxy.example:8080",
            session=self.session,
        )

        self.assertFalse(self.session.trust_env)
        self.assertEqual(
            self.session.proxies,
            {
                "http": "http://explicit-proxy.example:8080",
                "https": "http://explicit-proxy.example:8080",
            },
        )


class GameCraftContractTest(unittest.TestCase):
    """Exercise the GameCraft-specific semantic and dynamic-object contract."""

    @staticmethod
    def _artifact(task_id: str, relative_path: str, role: str) -> dict[str, Any]:
        """Return one ready task artifact plus a sandboxed HTML preview."""
        digest = hashlib.sha256(f"{task_id}:{relative_path}".encode()).hexdigest()
        source = f"assets/mirrors/sample/{role}/{task_id}/{digest}/{relative_path.rsplit('/', 1)[-1]}"
        preview = f"assets/previews/html/{digest}/index.html"
        return {
            "filename": relative_path.rsplit("/", 1)[-1],
            "repository_path": f"tasks/{task_id}/{relative_path}",
            "role": role,
            "mirror_status": "ready",
            "url": source,
            "size_bytes": 64,
            "sha256": digest,
            "preview": {
                "status": "ready",
                "preview_url": preview,
                "preview_kind": "html",
                "size_bytes": 96,
                "sha256": hashlib.sha256(f"preview:{digest}".encode()).hexdigest(),
            },
        }

    @staticmethod
    def _verifier_sources(task_id: str) -> dict[str, dict[str, Any]]:
        """Return ready code and config records for one fixture task."""
        result = {}
        for kind in ("code", "config"):
            digest = hashlib.sha256(f"{task_id}:{kind}".encode()).hexdigest()
            result[kind] = {
                "status": "ready",
                "url": f"assets/verifiers/{kind}/sample/{digest}.txt",
                "size_bytes": 72,
                "sha256": digest,
            }
        return result

    def _task(
        self,
        task_id: str,
        status: str,
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return one exactly translated GameCraft-like task record."""
        availability_label = "官方未发布实际 Gold。" if status == "not_published" else "可用性说明"
        return {
            "id": task_id,
            "original_language": "en",
            "title_zh": "中文标题",
            "task_prompt_zh_exact": "完整中文题面",
            "title_translation_status": "exact",
            "translation_status": "exact",
            "gold_availability": {"status": status, "label_zh": availability_label},
            "artifacts": {"files": artifacts},
            "verifier": {
                "checks": [
                    {
                        "title_zh": "检查标题",
                        "description_zh": "检查内容",
                        "title_translation_status": "exact",
                        "description_translation_status": "exact",
                    }
                ],
                "sources": self._verifier_sources(task_id),
            },
        }

    def setUp(self) -> None:
        """Build a three-state GameCraft shard without requiring HTTP routes."""
        self.gold_task_id = "platformer-gold"
        self.generator_task_id = "puzzle-generator"
        self.missing_task_id = "sports-missing"
        gold_artifacts = [
            self._artifact(self.gold_task_id, "solution/files/project.godot", "gold"),
            self._artifact(self.gold_task_id, "solution/files/main.gd", "gold"),
            self._artifact(self.gold_task_id, "solution/solve.sh", "reference"),
        ]
        generator_artifacts = [
            self._artifact(self.generator_task_id, "solution/solve.sh", "reference"),
        ]
        missing_artifacts = [
            self._artifact(self.missing_task_id, "solution/solve.sh", "attachment"),
        ]
        self.shard = {
            "benchmark_id": "sample",
            "record_count": 3,
            "repository_task_census": {
                "source_revision": "a" * 40,
                "task_directories": 4,
                "official_tasks": 3,
                "excluded_examples": ["tasks/example"],
                "family_counts": {"Fixture": 3},
                "reviewed_full_release": True,
            },
            "tasks": [
                self._task(self.gold_task_id, "repository_files", gold_artifacts),
                self._task(self.generator_task_id, "generator_source_only", generator_artifacts),
                self._task(self.missing_task_id, "not_published", missing_artifacts),
            ],
        }
        spec = ReleaseSpec(
            policy_id="sample-v3",
            catalog_benchmarks=1,
            expanded_benchmarks=1,
            full_records=3,
            task_probes=(),
            variant_counts=(),
            object_probes=(),
            anomaly_probes=(),
            gamecraft_probe=GameCraftProbe(
                benchmark_id="sample",
                source_revision="a" * 40,
                expected_task_directories=4,
                expected_family_counts=(("Fixture", 3),),
                expected_status_counts=(
                    ("repository_files", 1),
                    ("generator_source_only", 1),
                    ("not_published", 1),
                ),
                missing_gold_task_ids=(self.missing_task_id,),
                expected_title_zh=((self.gold_task_id, "中文标题"),),
            ),
        )
        client = AnonymousClient("https://public.example", 1, session=FakeSession())
        self.smoke = PublicReleaseSmoke(client, "release-v3", spec=spec)

    def test_registers_gold_generator_verifier_and_godot_previews(self) -> None:
        """Representative objects and all semantic Gold states are registered."""
        self.smoke._check_gamecraft_contract({"sample": self.shard})

        self.assertEqual(len(self.smoke.declared_object_probes), 8)
        self.assertEqual(len(self.smoke.index_bindings), 8)
        labels = {probe.label for probe in self.smoke.declared_object_probes}
        self.assertIn("GameCraft real Gold project original", labels)
        self.assertIn("GameCraft Gold GDScript preview", labels)
        self.assertIn("GameCraft generator solve.sh original", labels)
        self.assertIn("GameCraft Verifier code", labels)
        self.assertIn("GameCraft Verifier config", labels)

    def test_rejects_missing_gold_task_presented_as_reference(self) -> None:
        """An empty Oracle placeholder cannot be relabeled as a reference or Gold."""
        missing_task = self.shard["tasks"][2]
        missing_task["artifacts"]["files"][0]["role"] = "reference"

        with self.assertRaisesRegex(SmokeFailure, "empty solve.sh placeholder"):
            self.smoke._check_gamecraft_contract({"sample": self.shard})

    def test_rejects_untranslated_verifier_bullet(self) -> None:
        """Every GameCraft rubric bullet must retain an exact Chinese translation."""
        check = self.shard["tasks"][0]["verifier"]["checks"][0]
        check["description_translation_status"] = "missing"

        with self.assertRaisesRegex(SmokeFailure, "verifier description is not exact"):
            self.smoke._check_gamecraft_contract({"sample": self.shard})

    def test_rejects_exact_status_without_chinese_verifier_text(self) -> None:
        """An exact status cannot mask missing Chinese verifier content."""
        check = self.shard["tasks"][0]["verifier"]["checks"][0]
        check["description_zh"] = "English only"

        with self.assertRaisesRegex(SmokeFailure, "description_zh has no meaningful Chinese"):
            self.smoke._check_gamecraft_contract({"sample": self.shard})

    def test_rejects_unreviewed_source_revision(self) -> None:
        """A truthful reviewed flag cannot replace the exact source commit check."""
        self.shard["repository_task_census"]["source_revision"] = "b" * 40

        with self.assertRaisesRegex(SmokeFailure, "reviewed commit"):
            self.smoke._check_gamecraft_contract({"sample": self.shard})

    def test_rejects_family_census_drift(self) -> None:
        """A 140-task shard still fails when the reviewed family distribution drifts."""
        self.shard["repository_task_census"]["family_counts"] = {"Fixture": 2, "New": 1}

        with self.assertRaisesRegex(SmokeFailure, "family census"):
            self.smoke._check_gamecraft_contract({"sample": self.shard})

    def test_rejects_mixed_language_pinned_title(self) -> None:
        """A known mixed-language title regression fails even if its status claims exact."""
        self.shard["tasks"][0]["title_zh"] = "Horror 13层"

        with self.assertRaisesRegex(SmokeFailure, "exact Chinese title"):
            self.smoke._check_gamecraft_contract({"sample": self.shard})


class CheckedInPolicyTest(unittest.TestCase):
    """Keep the v3 publication policy aligned with the public smoke contract."""

    def test_gamecraft_is_full_and_deferred_benchmarks_remain_excluded(self) -> None:
        """GameCraft is public while today's three development-only additions remain private."""
        root = Path(__file__).resolve().parents[1]
        policy = json.loads((root / "config/publication_policy.json").read_text(encoding="utf-8"))

        self.assertEqual(policy["policy_id"], "kw-bench-library-public-v3")
        self.assertEqual(policy["expected_full_record_count"], 10161)
        self.assertEqual(policy["full"]["gamecraft-bench"]["expected_records"], 140)
        self.assertEqual(sum(item["expected_records"] for item in policy["full"].values()), 10161)
        self.assertEqual(len(policy["full"]), 30)
        self.assertTrue({
            "m3-bench-omnidiagram",
            "mcp-atlas",
            "toolathlon",
        }.issubset(policy["exclude"]))


if __name__ == "__main__":
    unittest.main()
