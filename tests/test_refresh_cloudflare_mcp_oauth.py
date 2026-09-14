"""Tests for the native-Keychain Cloudflare MCP OAuth refresh helper."""

from __future__ import annotations

import contextlib
import io
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
from typing import Any
from unittest import mock

from scripts.refresh_cloudflare_mcp_oauth import (
    CONNECT_TIMEOUT_SECONDS,
    DEFAULT_KEYCHAIN_ACCOUNT,
    DEFAULT_KEYCHAIN_SERVICE,
    DEFAULT_PROXY,
    READ_TIMEOUT_SECONDS,
    CredentialRefreshError,
    MacOSKeychainStore,
    NativeKeychainRecord,
    RequestsOAuthTransport,
    SecureRefreshLock,
    cli,
    main,
    parse_args,
    refresh_keychain_credential,
)


NOW = 1_800_000_000.0
OLD_ACCESS_TOKEN = "old-access-token-fixture"
OLD_REFRESH_TOKEN = "old-refresh-token-fixture"
NEW_ACCESS_TOKEN = "new-access-token-fixture"
NEW_REFRESH_TOKEN = "new-refresh-token-fixture"


class FakeKeychainBindings:
    """Keep a fake Generic Password entirely in test-process memory."""

    def __init__(self, payload: bytes, item_ref: int = 731) -> None:
        """Configure the copied bytes and opaque fake native item reference."""
        self.payload = payload
        self.item_ref = item_ref
        self.find_calls: list[tuple[bytes, bytes]] = []
        self.update_calls: list[tuple[int, bytes]] = []
        self.release_calls: list[int] = []

    def find_generic_password(self, service: bytes, account: bytes) -> NativeKeychainRecord:
        """Return the configured payload without touching the real Keychain."""
        self.find_calls.append((service, account))
        return NativeKeychainRecord(payload=self.payload, item_ref=self.item_ref)

    def update_generic_password(self, item_ref: int, payload: bytes) -> None:
        """Record one exact-item replacement in memory."""
        self.update_calls.append((item_ref, payload))
        self.payload = payload

    def release_item(self, item_ref: int) -> None:
        """Record release of the retained fake item reference."""
        self.release_calls.append(item_ref)


class FakeOAuthTransport:
    """Return an injected token response and record secret-bearing calls in memory."""

    def __init__(self, response: dict[str, Any]) -> None:
        """Configure one deterministic refresh response."""
        self.response = response
        self.calls: list[tuple[str, str, str, str]] = []

    def refresh(
        self,
        issuer: str,
        client_id: str,
        refresh_token: str,
        proxy: str,
    ) -> dict[str, Any]:
        """Capture grant inputs and return a copy of the response."""
        self.calls.append((issuer, client_id, refresh_token, proxy))
        return dict(self.response)


class FakeResponse:
    """Expose the bounded response surface consumed by RequestsOAuthTransport."""

    def __init__(
        self,
        payload: dict[str, Any],
        *,
        status_code: int = 200,
        history: list[object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Encode one fake JSON body and response metadata."""
        self.body = json.dumps(payload).encode("utf-8")
        self.status_code = status_code
        self.history = history or []
        self.headers = headers or {}
        self.closed = False

    def iter_content(self, chunk_size: int) -> list[bytes]:
        """Split the fake body into deterministic bounded chunks."""
        return [self.body[index : index + chunk_size] for index in range(0, len(self.body), chunk_size)]

    def close(self) -> None:
        """Record response cleanup."""
        self.closed = True


class FakeSession:
    """Return queued fake responses without making network requests."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        """Configure response order and an initially unsafe ambient-env flag."""
        self.responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.trust_env = True

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        """Capture one request and return the next queued response."""
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError("No fake HTTP response remains")
        return self.responses.pop(0)


class FakeProcessLock:
    """Expose lock lifetime to in-memory Keychain and transport test doubles."""

    def __init__(self, events: list[str] | None = None) -> None:
        """Start unlocked with an optional shared event journal."""
        self.events = events if events is not None else []
        self.held = False

    def __enter__(self) -> FakeProcessLock:
        """Acquire the fake lock and record ordering."""
        if self.held:
            raise AssertionError("fake lock already held")
        self.held = True
        self.events.append("lock-enter")
        return self

    def __exit__(self, *_error: object) -> None:
        """Release the fake lock and record ordering."""
        if not self.held:
            raise AssertionError("fake lock not held")
        self.events.append("lock-exit")
        self.held = False


def credential_document(expires_at: object) -> dict[str, Any]:
    """Build one representative Codex MCP Keychain JSON fixture."""
    return {
        "client_id": "public-client-id",
        "expires_at": expires_at,
        "issuer": "https://auth.example.test/oauth",
        "server_name": "cloudflare",
        "server_url": "https://mcp.example.test/mcp",
        "token_response": {
            "access_token": OLD_ACCESS_TOKEN,
            "expires_in": 3600,
            "refresh_token": OLD_REFRESH_TOKEN,
            "scope": "mcp:use",
            "token_type": "Bearer",
            "unknown_existing_token_field": {"preserve": True},
        },
        "unknown_top_level_field": ["preserve", 7],
    }


def encoded_credential(expires_at: object) -> bytes:
    """Serialize one credential fixture as Keychain bytes."""
    return json.dumps(credential_document(expires_at)).encode("utf-8")


class KeychainOAuthRefreshTests(unittest.TestCase):
    """Exercise freshness decisions, token rotation, and safe persistence."""

    def test_fresh_credential_does_not_request_or_update(self) -> None:
        """An access token outside the early-refresh window remains untouched."""
        bindings = FakeKeychainBindings(encoded_credential(NOW + 3600))
        store = MacOSKeychainStore(bindings)
        transport = FakeOAuthTransport({})

        status = refresh_keychain_credential(store, transport, now=NOW)

        self.assertEqual(status.action, "fresh")
        self.assertFalse(status.refresh_needed)
        self.assertFalse(status.updated)
        self.assertEqual(status.seconds_remaining, 3600)
        self.assertEqual(transport.calls, [])
        self.assertEqual(bindings.update_calls, [])
        self.assertEqual(bindings.release_calls, [bindings.item_ref])

    def test_numeric_millisecond_expiration_is_fresh_and_preserved(self) -> None:
        """The real 13-digit Codex Keychain shape is interpreted as Unix milliseconds."""
        expires_at_ms = int((NOW + 3600) * 1000) + 123
        bindings = FakeKeychainBindings(encoded_credential(expires_at_ms))
        transport = FakeOAuthTransport({})

        status = refresh_keychain_credential(
            MacOSKeychainStore(bindings),
            transport,
            now=NOW,
        )

        self.assertEqual(status.action, "fresh")
        self.assertEqual(status.expires_at, expires_at_ms)
        self.assertEqual(status.seconds_remaining, 3600)
        self.assertEqual(transport.calls, [])
        self.assertEqual(bindings.update_calls, [])

    def test_dry_status_never_requests_or_updates_expired_credential(self) -> None:
        """Dry status reports refresh need without network or Keychain mutation."""
        bindings = FakeKeychainBindings(encoded_credential(NOW - 60))
        store = MacOSKeychainStore(bindings)
        transport = FakeOAuthTransport({})

        status = refresh_keychain_credential(
            store,
            transport,
            now=NOW,
            dry_status=True,
        )

        self.assertEqual(status.action, "status")
        self.assertTrue(status.refresh_needed)
        self.assertFalse(status.updated)
        self.assertEqual(status.seconds_remaining, 0)
        self.assertEqual(transport.calls, [])
        self.assertEqual(bindings.update_calls, [])

    def test_refresh_preserves_unknown_fields_and_old_refresh_token(self) -> None:
        """A response without refresh_token rotates access state without dropping data."""
        original = credential_document(NOW + 300)
        bindings = FakeKeychainBindings(json.dumps(original).encode("utf-8"))
        store = MacOSKeychainStore(bindings)
        transport = FakeOAuthTransport(
            {
                "access_token": NEW_ACCESS_TOKEN,
                "expires_in": 7200,
                "scope": "mcp:use refreshed",
                "unknown_new_token_field": "preserve-too",
            }
        )

        status = refresh_keychain_credential(store, transport, now=NOW)

        self.assertEqual(
            transport.calls,
            [
                (
                    "https://auth.example.test/oauth",
                    "public-client-id",
                    OLD_REFRESH_TOKEN,
                    DEFAULT_PROXY,
                )
            ],
        )
        self.assertEqual(status.action, "refreshed")
        self.assertTrue(status.updated)
        self.assertFalse(status.refresh_needed)
        self.assertEqual(status.expires_at, int(NOW + 7200))
        self.assertEqual(len(bindings.update_calls), 1)
        item_ref, serialized = bindings.update_calls[0]
        self.assertEqual(item_ref, bindings.item_ref)
        updated = json.loads(serialized)
        self.assertEqual(updated["unknown_top_level_field"], original["unknown_top_level_field"])
        self.assertEqual(
            updated["token_response"]["unknown_existing_token_field"],
            original["token_response"]["unknown_existing_token_field"],
        )
        self.assertEqual(updated["token_response"]["unknown_new_token_field"], "preserve-too")
        self.assertEqual(updated["token_response"]["access_token"], NEW_ACCESS_TOKEN)
        self.assertEqual(updated["token_response"]["refresh_token"], OLD_REFRESH_TOKEN)
        self.assertEqual(updated["token_response"]["expires_in"], 7200)
        self.assertEqual(updated["expires_at"], int(NOW + 7200))
        rendered_status = json.dumps(status.as_dict())
        for secret in (OLD_ACCESS_TOKEN, OLD_REFRESH_TOKEN, NEW_ACCESS_TOKEN):
            self.assertNotIn(secret, rendered_status)

    def test_refresh_rotates_refresh_token_and_preserves_expiration_shape(self) -> None:
        """Rotated refresh tokens and supported expiration encodings persist atomically."""
        expiration_templates = (
            "2027-01-01T00:00:00Z",
            {
                "secs_since_epoch": int(NOW + 1),
                "nanos_since_epoch": 0,
                "unknown_time_field": "preserve",
            },
            float(NOW + 1),
            float((NOW + 1) * 1000),
            int((NOW + 1) * 1000),
        )
        for template in expiration_templates:
            with self.subTest(template=type(template).__name__):
                bindings = FakeKeychainBindings(encoded_credential(template))
                transport = FakeOAuthTransport(
                    {
                        "access_token": NEW_ACCESS_TOKEN,
                        "expires_in": 3600,
                        "refresh_token": NEW_REFRESH_TOKEN,
                    }
                )

                status = refresh_keychain_credential(
                    MacOSKeychainStore(bindings),
                    transport,
                    now=NOW,
                    refresh_window_seconds=10**9,
                )

                updated = json.loads(bindings.update_calls[0][1])
                self.assertEqual(updated["token_response"]["refresh_token"], NEW_REFRESH_TOKEN)
                if isinstance(template, str):
                    self.assertIsInstance(updated["expires_at"], str)
                    self.assertTrue(updated["expires_at"].endswith("Z"))
                elif isinstance(template, dict):
                    self.assertEqual(
                        updated["expires_at"],
                        {
                            "secs_since_epoch": int(NOW + 3600),
                            "nanos_since_epoch": 0,
                            "unknown_time_field": "preserve",
                        },
                    )
                elif template >= 100_000_000_000:
                    expected = type(template)((NOW + 3600) * 1000)
                    self.assertEqual(updated["expires_at"], expected)
                    self.assertEqual(status.expires_at, expected)
                else:
                    self.assertIsInstance(updated["expires_at"], float)
                self.assertTrue(status.updated)

    def test_status_never_echoes_unknown_expiration_fields(self) -> None:
        """Only normalized time components may leave the process in status JSON."""
        marker = "do-not-echo-this-keychain-value"
        expires_at = {
            "nanos_since_epoch": 123_000_000,
            "secs_since_epoch": int(NOW + 3600),
            "unknown_time_field": marker,
        }
        bindings = FakeKeychainBindings(encoded_credential(expires_at))

        status = refresh_keychain_credential(
            MacOSKeychainStore(bindings),
            FakeOAuthTransport({}),
            now=NOW,
            dry_status=True,
        )

        rendered = json.dumps(status.as_dict())
        self.assertNotIn(marker, rendered)
        self.assertEqual(
            status.expires_at,
            {
                "nanos_since_epoch": 123_000_000,
                "secs_since_epoch": int(NOW + 3600),
            },
        )

    def test_invalid_refresh_response_never_updates_or_echoes_secrets(self) -> None:
        """Malformed server data fails closed using only a stable error code."""
        bindings = FakeKeychainBindings(encoded_credential(NOW - 1))
        transport = FakeOAuthTransport(
            {
                "access_token": NEW_ACCESS_TOKEN,
                "expires_in": "not-an-integer",
                "refresh_token": NEW_REFRESH_TOKEN,
            }
        )

        with self.assertRaises(CredentialRefreshError) as caught:
            refresh_keychain_credential(
                MacOSKeychainStore(bindings),
                transport,
                now=NOW,
            )

        self.assertEqual(caught.exception.code, "oauth_expires_in_invalid")
        self.assertEqual(str(caught.exception), "oauth_expires_in_invalid")
        self.assertEqual(bindings.update_calls, [])
        for secret in (OLD_REFRESH_TOKEN, NEW_ACCESS_TOKEN, NEW_REFRESH_TOKEN):
            self.assertNotIn(secret, str(caught.exception))

    def test_unbounded_expiration_values_fail_with_safe_code(self) -> None:
        """Huge numeric encodings cannot escape validation through float overflow."""
        invalid_values = (
            10**1000,
            {"secs_since_epoch": 10**1000, "nanos_since_epoch": 0},
        )
        for expires_at in invalid_values:
            with self.subTest(kind=type(expires_at).__name__):
                bindings = FakeKeychainBindings(encoded_credential(expires_at))
                with self.assertRaises(CredentialRefreshError) as caught:
                    refresh_keychain_credential(
                        MacOSKeychainStore(bindings),
                        FakeOAuthTransport({}),
                        now=NOW,
                    )
                self.assertEqual(caught.exception.code, "oauth_expires_at_invalid")
                self.assertEqual(bindings.update_calls, [])

    def test_missing_required_credential_fields_fail_before_network(self) -> None:
        """Only the specified issuer, client, and nested refresh token can authorize refresh."""
        invalid_documents = []
        for field in ("issuer", "client_id"):
            document = credential_document(NOW - 1)
            document.pop(field)
            invalid_documents.append(document)
        document = credential_document(NOW - 1)
        document["token_response"].pop("refresh_token")
        invalid_documents.append(document)
        document = credential_document(NOW - 1)
        document.pop("server_name")
        invalid_documents.append(document)

        for document in invalid_documents:
            with self.subTest(fields=sorted(document)):
                bindings = FakeKeychainBindings(json.dumps(document).encode("utf-8"))
                transport = FakeOAuthTransport({})
                with self.assertRaises(CredentialRefreshError):
                    refresh_keychain_credential(
                        MacOSKeychainStore(bindings),
                        transport,
                        now=NOW,
                    )
                self.assertEqual(transport.calls, [])
                self.assertEqual(bindings.update_calls, [])

    def test_keychain_store_uses_exact_locator_and_same_item_reference(self) -> None:
        """Read and update target one Generic Password without enumeration."""
        bindings = FakeKeychainBindings(encoded_credential(NOW + 3600), item_ref=919)
        store = MacOSKeychainStore(bindings)

        with store.open_item(DEFAULT_KEYCHAIN_SERVICE, DEFAULT_KEYCHAIN_ACCOUNT) as item:
            self.assertNotIn(OLD_ACCESS_TOKEN, repr(item))
            replacement = encoded_credential(NOW + 7200)
            item.update(replacement)

        self.assertEqual(
            bindings.find_calls,
            [(DEFAULT_KEYCHAIN_SERVICE.encode(), DEFAULT_KEYCHAIN_ACCOUNT.encode())],
        )
        self.assertEqual(bindings.update_calls, [(919, replacement)])
        self.assertEqual(bindings.release_calls, [919])
        self.assertTrue(item.closed)
        self.assertEqual(item.payload, b"")


class SecureRefreshLockTests(unittest.TestCase):
    """Exercise private inode validation and cross-process exclusion."""

    def test_lock_creates_exact_private_empty_inode_and_excludes_peer(self) -> None:
        """The persistent advisory inode is 0600, empty, single-link, and exclusive."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = pathlib.Path(temporary_directory).resolve() / "private" / "refresh.lock"
            first = SecureRefreshLock(path, create_parent=True)
            with first:
                self.assertTrue(first.acquired)
                info = path.stat()
                self.assertTrue(stat.S_ISREG(info.st_mode))
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
                self.assertEqual(info.st_uid, os.getuid())
                self.assertEqual(info.st_nlink, 1)
                self.assertEqual(info.st_size, 0)
                self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
                with self.assertRaises(CredentialRefreshError) as caught:
                    with SecureRefreshLock(path):
                        pass
                self.assertEqual(caught.exception.code, "refresh_already_running")
            self.assertFalse(first.acquired)
            self.assertTrue(path.is_file())

    def test_lock_excludes_an_independent_process(self) -> None:
        """A second process cannot enter while the current user holds the inode."""
        child_source = (
            "import pathlib,sys\n"
            "from scripts.refresh_cloudflare_mcp_oauth import "
            "CredentialRefreshError,SecureRefreshLock\n"
            "try:\n"
            "    with SecureRefreshLock(pathlib.Path(sys.argv[1])):\n"
            "        result = 'unexpected-entry'\n"
            "except CredentialRefreshError as error:\n"
            "    result = error.code\n"
            "print(result)\n"
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = pathlib.Path(temporary_directory).resolve() / "private" / "refresh.lock"
            with SecureRefreshLock(path, create_parent=True):
                result = subprocess.run(
                    [sys.executable, "-c", child_source, str(path)],
                    cwd=pathlib.Path(__file__).parents[1],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "refresh_already_running")
        self.assertEqual(result.stderr, "")

    def test_lock_rejects_unsafe_parent_and_file_shapes(self) -> None:
        """Wrong modes, symlinks, hardlinks, content, and Git parents fail closed."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = pathlib.Path(temporary_directory).resolve()

            loose_parent = base / "loose"
            loose_parent.mkdir(mode=0o700)
            loose_parent.chmod(0o755)
            with self.assertRaises(CredentialRefreshError) as caught:
                with SecureRefreshLock(loose_parent / "refresh.lock"):
                    pass
            self.assertEqual(caught.exception.code, "refresh_lock_parent_wrong_mode")

            private_parent = base / "private"
            private_parent.mkdir(mode=0o700)
            private_parent.chmod(0o700)
            target = private_parent / "target"
            target.touch(mode=0o600)
            link = private_parent / "symlink.lock"
            link.symlink_to(target)
            with self.assertRaises(CredentialRefreshError) as caught:
                with SecureRefreshLock(link):
                    pass
            self.assertEqual(caught.exception.code, "refresh_lock_file_unavailable")

            broad = private_parent / "broad.lock"
            broad.touch(mode=0o600)
            broad.chmod(0o644)
            with self.assertRaises(CredentialRefreshError) as caught:
                with SecureRefreshLock(broad):
                    pass
            self.assertEqual(caught.exception.code, "refresh_lock_file_wrong_mode")

            original = private_parent / "original.lock"
            original.touch(mode=0o600)
            hardlink = private_parent / "hardlink.lock"
            os.link(original, hardlink)
            with self.assertRaises(CredentialRefreshError) as caught:
                with SecureRefreshLock(original):
                    pass
            self.assertEqual(caught.exception.code, "refresh_lock_file_link_count_invalid")

            nonempty = private_parent / "nonempty.lock"
            nonempty.write_text("non-sensitive metadata is still forbidden", encoding="utf-8")
            nonempty.chmod(0o600)
            with self.assertRaises(CredentialRefreshError) as caught:
                with SecureRefreshLock(nonempty):
                    pass
            self.assertEqual(caught.exception.code, "refresh_lock_file_invalid")

            git_parent = base / "worktree"
            git_parent.mkdir(mode=0o700)
            git_parent.chmod(0o700)
            (git_parent / ".git").mkdir()
            with self.assertRaises(CredentialRefreshError) as caught:
                with SecureRefreshLock(git_parent / "refresh.lock"):
                    pass
            self.assertEqual(caught.exception.code, "refresh_lock_inside_git")


class OAuthTransportTests(unittest.TestCase):
    """Verify proxy, endpoint, redirect, timeout, and response bounds."""

    def test_refresh_discovers_and_posts_with_strict_request_policy(self) -> None:
        """Discovery and refresh use HTTPS, one explicit proxy, and no redirects."""
        metadata = FakeResponse(
            {
                "issuer": "https://auth.example.test/oauth",
                "token_endpoint": "https://auth.example.test/oauth/token",
            }
        )
        token = FakeResponse({"access_token": NEW_ACCESS_TOKEN, "expires_in": 3600})
        session = FakeSession([metadata, token])
        transport = RequestsOAuthTransport(session)  # type: ignore[arg-type]

        result = transport.refresh(
            "https://auth.example.test/oauth/",
            "public-client-id",
            OLD_REFRESH_TOKEN,
            DEFAULT_PROXY,
        )

        self.assertEqual(result["access_token"], NEW_ACCESS_TOKEN)
        self.assertFalse(session.trust_env)
        self.assertEqual(len(session.calls), 2)
        first_method, first_url, first_options = session.calls[0]
        self.assertEqual(first_method, "GET")
        self.assertEqual(
            first_url,
            "https://auth.example.test/.well-known/oauth-authorization-server/oauth",
        )
        self.assertIsNone(first_options["data"])
        second_method, second_url, second_options = session.calls[1]
        self.assertEqual(second_method, "POST")
        self.assertEqual(second_url, "https://auth.example.test/oauth/token")
        self.assertEqual(
            second_options["data"],
            {
                "client_id": "public-client-id",
                "grant_type": "refresh_token",
                "refresh_token": OLD_REFRESH_TOKEN,
            },
        )
        for _method, _url, options in session.calls:
            self.assertFalse(options["allow_redirects"])
            self.assertEqual(
                options["proxies"],
                {"http": DEFAULT_PROXY, "https": DEFAULT_PROXY},
            )
            self.assertTrue(options["stream"])
            self.assertEqual(
                options["timeout"],
                (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
            )
        self.assertNotIn(OLD_REFRESH_TOKEN, first_url)
        self.assertNotIn(OLD_REFRESH_TOKEN, json.dumps(first_options))
        self.assertTrue(metadata.closed)
        self.assertTrue(token.closed)

    def test_token_endpoint_trailing_slash_is_preserved(self) -> None:
        """Validation must not rewrite an OAuth token endpoint's path semantics."""
        metadata = FakeResponse(
            {
                "issuer": "https://auth.example.test/oauth",
                "token_endpoint": "https://auth.example.test/oauth/token/",
            }
        )
        token = FakeResponse({"access_token": NEW_ACCESS_TOKEN, "expires_in": 3600})
        session = FakeSession([metadata, token])

        RequestsOAuthTransport(session).refresh(  # type: ignore[arg-type]
            "https://auth.example.test/oauth",
            "public-client-id",
            OLD_REFRESH_TOKEN,
            DEFAULT_PROXY,
        )

        self.assertEqual(session.calls[1][1], "https://auth.example.test/oauth/token/")

    def test_cross_origin_endpoint_and_redirect_fail_before_secret_post(self) -> None:
        """Untrusted metadata cannot redirect or receive the refresh credential."""
        cases = (
            FakeResponse(
                {
                    "issuer": "https://auth.example.test/oauth",
                    "token_endpoint": "https://capture.example.invalid/token",
                }
            ),
            FakeResponse({}, status_code=302, history=[object()]),
        )
        expected_codes = (
            "oauth_token_endpoint_origin_mismatch",
            "oauth_redirect_forbidden",
        )
        for response, expected_code in zip(cases, expected_codes):
            with self.subTest(expected_code=expected_code):
                session = FakeSession([response])
                transport = RequestsOAuthTransport(session)  # type: ignore[arg-type]
                with self.assertRaises(CredentialRefreshError) as caught:
                    transport.refresh(
                        "https://auth.example.test/oauth",
                        "public-client-id",
                        OLD_REFRESH_TOKEN,
                        DEFAULT_PROXY,
                    )
                self.assertEqual(caught.exception.code, expected_code)
                self.assertEqual(len(session.calls), 1)
                self.assertNotIn(OLD_REFRESH_TOKEN, json.dumps(session.calls[0], default=str))
                self.assertTrue(response.closed)

    def test_proxy_credentials_and_non_https_issuer_are_rejected_without_request(self) -> None:
        """Ambient, cleartext, and credential-bearing network routes fail closed."""
        invalid = (
            ("http://auth.example.test", DEFAULT_PROXY),
            ("https://auth.example.test", "http://user:password@proxy.example.test:8080"),
            ("https://auth.example.test", ""),
        )
        for issuer, proxy in invalid:
            with self.subTest(issuer=issuer, proxy=proxy):
                session = FakeSession([])
                transport = RequestsOAuthTransport(session)  # type: ignore[arg-type]
                with self.assertRaises(CredentialRefreshError):
                    transport.refresh(
                        issuer,
                        "public-client-id",
                        OLD_REFRESH_TOKEN,
                        proxy,
                    )
                self.assertEqual(session.calls, [])


class RefreshCliTests(unittest.TestCase):
    """Check the secret-free command surface and stable JSON output."""

    def test_cli_arguments_contain_no_credential_value_option(self) -> None:
        """Only non-sensitive locators, proxy, and timing policy are accepted."""
        args = parse_args([])
        self.assertEqual(args.service, DEFAULT_KEYCHAIN_SERVICE)
        self.assertEqual(args.account, DEFAULT_KEYCHAIN_ACCOUNT)
        self.assertEqual(args.proxy, DEFAULT_PROXY)
        option_names = set(vars(args))
        self.assertFalse(any("token" in name or "secret" in name for name in option_names))

    def test_main_prints_only_non_sensitive_dry_status(self) -> None:
        """Injected dependencies prove dry CLI operation avoids real services."""
        bindings = FakeKeychainBindings(encoded_credential(NOW + 3600))
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                ["--dry-status"],
                store=MacOSKeychainStore(bindings),
                transport=FakeOAuthTransport({}),
                process_lock=FakeProcessLock(),
                now=NOW,
            )

        self.assertEqual(exit_code, 0)
        status = json.loads(stdout.getvalue())
        self.assertEqual(status["action"], "status")
        self.assertFalse(status["refresh_needed"])
        self.assertFalse(status["updated"])
        for secret in (OLD_ACCESS_TOKEN, OLD_REFRESH_TOKEN):
            self.assertNotIn(secret, stdout.getvalue())

    def test_main_accepts_a_secure_non_sensitive_lock_path_override(self) -> None:
        """The CLI override creates only an empty lock file in a presecured directory."""
        bindings = FakeKeychainBindings(encoded_credential(NOW + 3600))
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as temporary_directory:
            parent = pathlib.Path(temporary_directory).resolve() / "credential-locks"
            parent.mkdir(mode=0o700)
            parent.chmod(0o700)
            lock_path = parent / "refresh.lock"

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    ["--dry-status", "--lock-file", str(lock_path)],
                    store=MacOSKeychainStore(bindings),
                    transport=FakeOAuthTransport({}),
                    now=NOW,
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(lock_path.read_bytes(), b"")
            self.assertEqual(stat.S_IMODE(lock_path.stat().st_mode), 0o600)

    def test_lock_covers_keychain_read_network_update_and_release(self) -> None:
        """The standard entry point holds one lock across the entire rotation cycle."""
        events: list[str] = []
        process_lock = FakeProcessLock(events)

        class GuardedBindings(FakeKeychainBindings):
            """Assert every Keychain operation happens while the process lock is held."""

            def find_generic_password(
                self,
                service: bytes,
                account: bytes,
            ) -> NativeKeychainRecord:
                """Record a guarded read."""
                self._assert_locked("keychain-read")
                return super().find_generic_password(service, account)

            def update_generic_password(self, item_ref: int, payload: bytes) -> None:
                """Record a guarded atomic update."""
                self._assert_locked("keychain-update")
                super().update_generic_password(item_ref, payload)

            def release_item(self, item_ref: int) -> None:
                """Record guarded release of the retained item reference."""
                self._assert_locked("keychain-release")
                super().release_item(item_ref)

            @staticmethod
            def _assert_locked(event: str) -> None:
                """Fail the test if an operation escapes the lock lifetime."""
                if not process_lock.held:
                    raise AssertionError(f"{event} ran without the refresh lock")
                events.append(event)

        class GuardedTransport(FakeOAuthTransport):
            """Assert the refresh request occurs while the same lock is held."""

            def refresh(
                self,
                issuer: str,
                client_id: str,
                refresh_token: str,
                proxy: str,
            ) -> dict[str, Any]:
                """Record one guarded network refresh."""
                if not process_lock.held:
                    raise AssertionError("oauth refresh ran without the refresh lock")
                events.append("oauth-refresh")
                return super().refresh(issuer, client_id, refresh_token, proxy)

        bindings = GuardedBindings(encoded_credential(NOW - 1))
        transport = GuardedTransport(
            {"access_token": NEW_ACCESS_TOKEN, "expires_in": 3600}
        )
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [],
                store=MacOSKeychainStore(bindings),
                transport=transport,
                process_lock=process_lock,
                now=NOW,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            events,
            [
                "lock-enter",
                "keychain-read",
                "oauth-refresh",
                "keychain-update",
                "keychain-release",
                "lock-exit",
            ],
        )
        self.assertFalse(process_lock.held)

    def test_cli_failure_prints_only_safe_code(self) -> None:
        """Even a secret-bearing internal failure cannot reach stderr."""
        stderr = io.StringIO()
        with (
            mock.patch(
                "scripts.refresh_cloudflare_mcp_oauth.main",
                side_effect=CredentialRefreshError("oauth_request_failed"),
            ),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = cli([])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            json.loads(stderr.getvalue()),
            {"code": "oauth_request_failed", "ok": False},
        )

    def test_cli_unexpected_failure_prints_no_exception_detail(self) -> None:
        """Unexpected dependency failures collapse to one non-sensitive code."""
        marker = "do-not-echo-this-secret-bearing-detail"
        stderr = io.StringIO()
        with (
            mock.patch(
                "scripts.refresh_cloudflare_mcp_oauth.main",
                side_effect=RuntimeError(marker),
            ),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = cli([])

        self.assertEqual(exit_code, 2)
        self.assertEqual(
            json.loads(stderr.getvalue()),
            {"code": "credential_refresh_internal_error", "ok": False},
        )
        self.assertNotIn(marker, stderr.getvalue())

    def test_source_has_no_subprocess_or_secret_environment_fallback(self) -> None:
        """A static regression prevents shell-based Keychain and env-token fallbacks."""
        source_path = pathlib.Path(__file__).parents[1] / "scripts/refresh_cloudflare_mcp_oauth.py"
        source = source_path.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("--token", source)
        self.assertNotIn("--secret", source)


if __name__ == "__main__":
    unittest.main()
