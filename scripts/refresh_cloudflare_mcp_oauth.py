#!/usr/bin/env python3
"""Refresh one Codex Cloudflare MCP OAuth credential entirely through Keychain."""

from __future__ import annotations

import argparse
import copy
import ctypes
import ctypes.util
import datetime as dt
import errno
import fcntl
import json
import math
import os
import pathlib
import re
import stat
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence
from urllib.parse import urlsplit, urlunsplit

import requests


DEFAULT_KEYCHAIN_SERVICE = "Codex MCP Credentials"
# This is a non-secret Keychain locator, not an authentication credential.
DEFAULT_KEYCHAIN_ACCOUNT = "cloudflare|2e40c71145c8b601"
DEFAULT_PROXY = "http://agent.baidu.com:8891"
DEFAULT_REFRESH_WINDOW_SECONDS = 15 * 60
CONNECT_TIMEOUT_SECONDS = 10.0
READ_TIMEOUT_SECONDS = 30.0
MAX_KEYCHAIN_PAYLOAD_BYTES = 1024 * 1024
MAX_HTTP_RESPONSE_BYTES = 1024 * 1024
MAX_TOKEN_BYTES = 64 * 1024
MILLISECONDS_EPOCH_THRESHOLD = 100_000_000_000
LOCK_PARENT_MODE = 0o700
LOCK_FILE_MODE = 0o600
ERR_SEC_SUCCESS = 0
ERR_SEC_ITEM_NOT_FOUND = -25300


class CredentialRefreshError(RuntimeError):
    """Expose only a stable, non-sensitive failure code to automation."""

    def __init__(self, code: str) -> None:
        """Create a safe error without retaining secret-bearing input."""
        super().__init__(code)
        self.code = code


class RefreshProcessLock(Protocol):
    """Describe the context-managed lock held across the complete refresh cycle."""

    def __enter__(self) -> RefreshProcessLock:
        """Acquire exclusive ownership or fail closed."""

    def __exit__(self, *_error: object) -> None:
        """Release exclusive ownership."""


def default_lock_file() -> pathlib.Path:
    """Return the current user's dedicated, non-Git macOS refresh lock path."""
    return (
        pathlib.Path.home()
        / "Library/Caches/KWBenchLibrary/credential-locks/cloudflare-mcp-oauth.lock"
    )


def _optional_lstat(path: pathlib.Path) -> os.stat_result | None:
    """Inspect a potential Git marker without following it."""
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError:
        raise CredentialRefreshError("refresh_lock_git_check_failed") from None


def _looks_like_bare_git_repository(path: pathlib.Path) -> bool:
    """Recognize the standard on-disk shape of a bare Git repository."""
    head = _optional_lstat(path / "HEAD")
    config = _optional_lstat(path / "config")
    objects = _optional_lstat(path / "objects")
    refs = _optional_lstat(path / "refs")
    reftable = _optional_lstat(path / "reftable")
    packed_refs = _optional_lstat(path / "packed-refs")
    return bool(
        head is not None
        and config is not None
        and objects is not None
        and (refs is not None or reftable is not None or packed_refs is not None)
    )


def _reject_git_lock_parent(parent: pathlib.Path) -> None:
    """Refuse lock files in visible Git repositories or an active external context."""
    if os.getenv("GIT_DIR") is not None or os.getenv("GIT_WORK_TREE") is not None:
        raise CredentialRefreshError("refresh_lock_git_context_forbidden")
    for candidate in (parent, *parent.parents):
        if _optional_lstat(candidate / ".git") is not None:
            raise CredentialRefreshError("refresh_lock_inside_git")
        if _looks_like_bare_git_repository(candidate):
            raise CredentialRefreshError("refresh_lock_inside_git")


def _open_private_lock_parent(path: pathlib.Path, create_parent: bool) -> tuple[pathlib.Path, int]:
    """Open an exact 0700 caller-owned directory without accepting symlink aliases."""
    supplied = path.absolute().parent
    if create_parent:
        try:
            supplied.mkdir(mode=LOCK_PARENT_MODE, parents=True, exist_ok=True)
        except OSError:
            raise CredentialRefreshError("refresh_lock_parent_unavailable") from None
    try:
        resolved = supplied.resolve(strict=True)
    except (OSError, ValueError):
        raise CredentialRefreshError("refresh_lock_parent_unavailable") from None
    if resolved != supplied:
        raise CredentialRefreshError("refresh_lock_parent_symlink_forbidden")
    _reject_git_lock_parent(resolved)
    required = (
        "O_CLOEXEC",
        "O_DIRECTORY",
        "O_NOFOLLOW",
        "O_NONBLOCK",
        "getuid",
    )
    primitives_supported = (
        os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.stat in os.supports_follow_symlinks
    )
    if (
        os.name != "posix"
        or any(not hasattr(os, name) for name in required)
        or not primitives_supported
    ):
        raise CredentialRefreshError("refresh_lock_platform_unsupported")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        parent_fd = os.open(resolved, flags)
    except OSError:
        raise CredentialRefreshError("refresh_lock_parent_unavailable") from None
    try:
        info = os.fstat(parent_fd)
        path_info = os.stat(resolved, follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode):
            raise CredentialRefreshError("refresh_lock_parent_invalid")
        if (path_info.st_dev, path_info.st_ino) != (info.st_dev, info.st_ino):
            raise CredentialRefreshError("refresh_lock_parent_identity_changed")
        if info.st_uid != os.getuid():
            raise CredentialRefreshError("refresh_lock_parent_wrong_owner")
        if stat.S_IMODE(info.st_mode) != LOCK_PARENT_MODE:
            raise CredentialRefreshError("refresh_lock_parent_wrong_mode")
        _reject_git_lock_parent(resolved)
    except BaseException:
        os.close(parent_fd)
        raise
    return resolved, parent_fd


class SecureRefreshLock:
    """Hold a private, empty lock inode across Keychain read, network, and update."""

    def __init__(self, path: pathlib.Path, *, create_parent: bool = False) -> None:
        """Configure one non-sensitive lock path without opening it yet."""
        self.path = path.absolute()
        self.create_parent = create_parent
        self._file_fd = -1
        self._parent_fd = -1

    @property
    def acquired(self) -> bool:
        """Return whether both anchored descriptors are currently held."""
        return self._file_fd >= 0 and self._parent_fd >= 0

    def __enter__(self) -> SecureRefreshLock:
        """Create or validate the lock inode and acquire it without waiting."""
        if self.acquired:
            raise CredentialRefreshError("refresh_lock_already_acquired")
        parent, parent_fd = _open_private_lock_parent(self.path, self.create_parent)
        target = parent / self.path.name
        base_flags = os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        created = False
        try:
            try:
                file_fd = os.open(
                    target.name,
                    base_flags | os.O_CREAT | os.O_EXCL,
                    LOCK_FILE_MODE,
                    dir_fd=parent_fd,
                )
                created = True
            except FileExistsError:
                try:
                    file_fd = os.open(target.name, base_flags, dir_fd=parent_fd)
                except OSError:
                    raise CredentialRefreshError("refresh_lock_file_unavailable") from None
            except OSError:
                raise CredentialRefreshError("refresh_lock_file_unavailable") from None
            try:
                if created:
                    try:
                        os.fchmod(file_fd, LOCK_FILE_MODE)
                        os.fsync(file_fd)
                        os.fsync(parent_fd)
                    except OSError:
                        raise CredentialRefreshError("refresh_lock_file_setup_failed") from None
                self._validate_file(file_fd, parent_fd, target)
                try:
                    fcntl.flock(file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as error:
                    if error.errno in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                        raise CredentialRefreshError("refresh_already_running") from None
                    raise CredentialRefreshError("refresh_lock_acquire_failed") from None
                self._validate_file(file_fd, parent_fd, target)
                _reject_git_lock_parent(parent)
            except BaseException:
                os.close(file_fd)
                raise
        except BaseException:
            os.close(parent_fd)
            raise
        self._file_fd = file_fd
        self._parent_fd = parent_fd
        return self

    @staticmethod
    def _validate_file(file_fd: int, parent_fd: int, target: pathlib.Path) -> None:
        """Bind an empty exact 0600 regular single-link file to its directory entry."""
        try:
            info = os.fstat(file_fd)
        except OSError:
            raise CredentialRefreshError("refresh_lock_file_unavailable") from None
        if not stat.S_ISREG(info.st_mode) or info.st_size != 0:
            raise CredentialRefreshError("refresh_lock_file_invalid")
        if info.st_uid != os.getuid():
            raise CredentialRefreshError("refresh_lock_file_wrong_owner")
        if stat.S_IMODE(info.st_mode) != LOCK_FILE_MODE:
            raise CredentialRefreshError("refresh_lock_file_wrong_mode")
        if info.st_nlink != 1:
            raise CredentialRefreshError("refresh_lock_file_link_count_invalid")
        try:
            path_info = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError:
            raise CredentialRefreshError("refresh_lock_file_unavailable") from None
        if not stat.S_ISREG(path_info.st_mode) or (
            path_info.st_dev,
            path_info.st_ino,
        ) != (info.st_dev, info.st_ino):
            raise CredentialRefreshError("refresh_lock_file_identity_changed")

    def __exit__(self, *_error: object) -> None:
        """Release the advisory lock and both identity anchors without unlinking it."""
        file_fd = self._file_fd
        parent_fd = self._parent_fd
        self._file_fd = -1
        self._parent_fd = -1
        try:
            if file_fd >= 0:
                try:
                    fcntl.flock(file_fd, fcntl.LOCK_UN)
                except OSError:
                    # Closing the descriptor below also releases flock(2).
                    pass
                try:
                    os.close(file_fd)
                except OSError:
                    pass
        finally:
            if parent_fd >= 0:
                try:
                    os.close(parent_fd)
                except OSError:
                    pass


@dataclass(frozen=True)
class NativeKeychainRecord:
    """Hold copied Keychain bytes and the retained native item reference."""

    payload: bytes = field(repr=False)
    item_ref: int = field(repr=False)


class KeychainBindings(Protocol):
    """Describe the small native Security.framework surface used by the helper."""

    def find_generic_password(self, service: bytes, account: bytes) -> NativeKeychainRecord:
        """Return one exact Generic Password item and a retained item reference."""

    def update_generic_password(self, item_ref: int, payload: bytes) -> None:
        """Replace the data of the same retained Generic Password item."""

    def release_item(self, item_ref: int) -> None:
        """Release one retained Security.framework item reference."""


class SecurityFrameworkBindings:
    """Call macOS Security.framework directly without invoking a subprocess."""

    def __init__(self) -> None:
        """Load and type the native APIs used for exact-item read and update."""
        if sys.platform != "darwin":
            raise CredentialRefreshError("macos_keychain_required")
        security_path = ctypes.util.find_library("Security")
        core_foundation_path = ctypes.util.find_library("CoreFoundation")
        if not security_path or not core_foundation_path:
            raise CredentialRefreshError("security_framework_unavailable")
        try:
            self._security = ctypes.CDLL(security_path)
            self._core_foundation = ctypes.CDLL(core_foundation_path)
        except OSError:
            raise CredentialRefreshError("security_framework_unavailable") from None

        self._security.SecKeychainFindGenericPassword.argtypes = (
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
        )
        self._security.SecKeychainFindGenericPassword.restype = ctypes.c_int32
        self._security.SecKeychainItemModifyAttributesAndData.argtypes = (
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
        )
        self._security.SecKeychainItemModifyAttributesAndData.restype = ctypes.c_int32
        self._security.SecKeychainItemFreeContent.argtypes = (
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        self._security.SecKeychainItemFreeContent.restype = ctypes.c_int32
        self._core_foundation.CFRelease.argtypes = (ctypes.c_void_p,)
        self._core_foundation.CFRelease.restype = None

    def find_generic_password(self, service: bytes, account: bytes) -> NativeKeychainRecord:
        """Read an exact Generic Password and retain its item reference for update."""
        password_length = ctypes.c_uint32()
        password_data = ctypes.c_void_p()
        item_ref = ctypes.c_void_p()
        status = self._security.SecKeychainFindGenericPassword(
            None,
            len(service),
            service,
            len(account),
            account,
            ctypes.byref(password_length),
            ctypes.byref(password_data),
            ctypes.byref(item_ref),
        )
        if status != ERR_SEC_SUCCESS:
            if password_data.value:
                self._security.SecKeychainItemFreeContent(None, password_data)
            if item_ref.value:
                self.release_item(int(item_ref.value))
            if status == ERR_SEC_ITEM_NOT_FOUND:
                raise CredentialRefreshError("keychain_item_not_found")
            raise CredentialRefreshError("keychain_read_failed")
        try:
            if not item_ref.value:
                raise CredentialRefreshError("keychain_read_failed")
            if password_length.value > MAX_KEYCHAIN_PAYLOAD_BYTES:
                raise CredentialRefreshError("keychain_payload_too_large")
            if password_length.value and not password_data.value:
                raise CredentialRefreshError("keychain_read_failed")
            payload = ctypes.string_at(password_data.value, password_length.value)
            return NativeKeychainRecord(payload=payload, item_ref=int(item_ref.value))
        except BaseException:
            if item_ref.value:
                self.release_item(int(item_ref.value))
            raise
        finally:
            if password_data.value:
                self._security.SecKeychainItemFreeContent(None, password_data)

    def update_generic_password(self, item_ref: int, payload: bytes) -> None:
        """Atomically replace only the data of the retained Generic Password item."""
        if not payload or len(payload) > MAX_KEYCHAIN_PAYLOAD_BYTES:
            raise CredentialRefreshError("keychain_payload_invalid")
        buffer = ctypes.create_string_buffer(payload)
        status = self._security.SecKeychainItemModifyAttributesAndData(
            ctypes.c_void_p(item_ref),
            None,
            len(payload),
            ctypes.cast(buffer, ctypes.c_void_p),
        )
        if status != ERR_SEC_SUCCESS:
            raise CredentialRefreshError("keychain_update_failed")

    def release_item(self, item_ref: int) -> None:
        """Release one item reference obtained from the find call."""
        self._core_foundation.CFRelease(ctypes.c_void_p(item_ref))


class KeychainItem:
    """Keep the exact Keychain item open from read through in-place update."""

    def __init__(self, bindings: KeychainBindings, record: NativeKeychainRecord) -> None:
        """Retain the binding, copied payload, and opaque item reference."""
        self._bindings = bindings
        self._item_ref = record.item_ref
        self.payload = record.payload

    @property
    def closed(self) -> bool:
        """Return whether the native item reference has been released."""
        return self._item_ref == 0

    def update(self, payload: bytes) -> None:
        """Replace this exact item's data with one Security.framework operation."""
        if self.closed:
            raise CredentialRefreshError("keychain_item_closed")
        self._bindings.update_generic_password(self._item_ref, payload)
        self.payload = payload

    def close(self) -> None:
        """Release the native item reference and discard the copied payload reference."""
        item_ref = self._item_ref
        self._item_ref = 0
        self.payload = b""
        if item_ref:
            self._bindings.release_item(item_ref)

    def __enter__(self) -> KeychainItem:
        """Return the still-open exact item."""
        if self.closed:
            raise CredentialRefreshError("keychain_item_closed")
        return self

    def __exit__(self, *_error: object) -> None:
        """Release the item when credential processing finishes."""
        self.close()

    def __repr__(self) -> str:
        """Never expose copied Keychain bytes through debugging output."""
        return f"KeychainItem(closed={self.closed})"


class KeychainStore(Protocol):
    """Open one exact Generic Password item without enumerating other secrets."""

    def open_item(self, service: str, account: str) -> KeychainItem:
        """Return a context-managed exact Keychain item."""


class MacOSKeychainStore:
    """Access one macOS Generic Password through an injectable native binding."""

    def __init__(self, bindings: KeychainBindings | None = None) -> None:
        """Use native Security.framework unless a test binding is injected."""
        self._bindings = bindings if bindings is not None else SecurityFrameworkBindings()

    def open_item(self, service: str, account: str) -> KeychainItem:
        """Open an exact service/account locator and retain its item reference."""
        service_bytes = _encode_locator(service, "keychain_service_invalid")
        account_bytes = _encode_locator(account, "keychain_account_invalid")
        record = self._bindings.find_generic_password(service_bytes, account_bytes)
        return KeychainItem(self._bindings, record)


class OAuthTransport(Protocol):
    """Refresh OAuth tokens without exposing them to the orchestration layer."""

    def refresh(
        self,
        issuer: str,
        client_id: str,
        refresh_token: str,
        proxy: str,
    ) -> dict[str, Any]:
        """Discover the token endpoint and perform a refresh-token grant."""


class RequestsOAuthTransport:
    """Perform bounded OAuth discovery and refresh through an explicit proxy."""

    def __init__(self, session: requests.Session | None = None) -> None:
        """Create or accept one session and disable ambient environment settings."""
        self._session = session if session is not None else requests.Session()
        self._session.trust_env = False

    def refresh(
        self,
        issuer: str,
        client_id: str,
        refresh_token: str,
        proxy: str,
    ) -> dict[str, Any]:
        """Use RFC 8414 metadata, then post one public-client refresh grant."""
        issuer_url = _validate_https_url(issuer, "oauth_issuer_invalid")
        proxy_url = _validate_proxy_url(proxy)
        metadata_url = _oauth_metadata_url(issuer_url)
        metadata = self._request_json("GET", metadata_url, proxy_url)
        discovered_issuer = metadata.get("issuer")
        if not isinstance(discovered_issuer, str) or _canonical_url(
            discovered_issuer
        ) != _canonical_url(issuer_url):
            raise CredentialRefreshError("oauth_metadata_issuer_mismatch")
        token_endpoint = metadata.get("token_endpoint")
        if not isinstance(token_endpoint, str):
            raise CredentialRefreshError("oauth_token_endpoint_missing")
        token_endpoint = _validate_https_url(token_endpoint, "oauth_token_endpoint_invalid")
        if _url_origin(token_endpoint) != _url_origin(issuer_url):
            raise CredentialRefreshError("oauth_token_endpoint_origin_mismatch")
        return self._request_json(
            "POST",
            token_endpoint,
            proxy_url,
            data={
                "client_id": client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )

    def _request_json(
        self,
        method: str,
        url: str,
        proxy: str,
        *,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Return one size-bounded JSON object without following redirects."""
        try:
            response = self._session.request(
                method,
                url,
                allow_redirects=False,
                data=data,
                headers={"Accept": "application/json"},
                proxies={"http": proxy, "https": proxy},
                stream=True,
                timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
            )
        except requests.RequestException:
            raise CredentialRefreshError("oauth_request_failed") from None
        try:
            if getattr(response, "history", None):
                raise CredentialRefreshError("oauth_redirect_forbidden")
            if not 200 <= response.status_code < 300:
                raise CredentialRefreshError("oauth_http_error")
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    if int(content_length) > MAX_HTTP_RESPONSE_BYTES:
                        raise CredentialRefreshError("oauth_response_too_large")
                except ValueError:
                    raise CredentialRefreshError("oauth_response_invalid") from None
            payload = bytearray()
            for chunk in response.iter_content(chunk_size=16 * 1024):
                if not isinstance(chunk, bytes):
                    raise CredentialRefreshError("oauth_response_invalid")
                payload.extend(chunk)
                if len(payload) > MAX_HTTP_RESPONSE_BYTES:
                    raise CredentialRefreshError("oauth_response_too_large")
            try:
                decoded = json.loads(payload)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                raise CredentialRefreshError("oauth_response_invalid") from None
            if not isinstance(decoded, dict):
                raise CredentialRefreshError("oauth_response_invalid")
            return decoded
        except requests.RequestException:
            raise CredentialRefreshError("oauth_response_failed") from None
        finally:
            try:
                response.close()
            except Exception:
                # Cleanup failure must not surface a response object or payload.
                pass


@dataclass(frozen=True)
class RefreshStatus:
    """Contain only non-sensitive state suitable for stdout or a supervisor."""

    action: str
    expires_at: int | float | str | dict[str, Any] | None
    refresh_needed: bool
    seconds_remaining: int | None
    updated: bool

    def as_dict(self) -> dict[str, Any]:
        """Serialize a stable status without credential identifiers or tokens."""
        return {
            "action": self.action,
            "expires_at": self.expires_at,
            "ok": True,
            "refresh_needed": self.refresh_needed,
            "seconds_remaining": self.seconds_remaining,
            "updated": self.updated,
        }


def _encode_locator(value: str, error_code: str) -> bytes:
    """Encode one non-secret Keychain locator without NUL or control bytes."""
    if not value or len(value) > 1024 or any(ord(character) < 32 for character in value):
        raise CredentialRefreshError(error_code)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise CredentialRefreshError(error_code) from None
    if b"\x00" in encoded:
        raise CredentialRefreshError(error_code)
    return encoded


def _canonical_url(value: str) -> str:
    """Normalize only an optional trailing slash for exact issuer comparison."""
    try:
        validated = _validate_https_url(value, "oauth_url_invalid")
    except CredentialRefreshError:
        return ""
    parsed = urlsplit(validated)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def _validate_https_url(value: str, error_code: str) -> str:
    """Require a clean ASCII HTTPS URL without userinfo, query, or fragment."""
    if value != value.strip() or any(not 33 <= ord(character) <= 126 for character in value):
        raise CredentialRefreshError(error_code)
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        raise CredentialRefreshError(error_code) from None
    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "\\" in value
        or not re.fullmatch(r"[A-Za-z0-9.:[\]-]+", parsed.netloc)
    ):
        raise CredentialRefreshError(error_code)
    return urlunsplit(("https", parsed.netloc, parsed.path, "", ""))


def _validate_proxy_url(value: str) -> str:
    """Require an explicit non-credentialed HTTP(S) proxy URL."""
    if value != value.strip() or any(not 33 <= ord(character) <= 126 for character in value):
        raise CredentialRefreshError("oauth_proxy_invalid")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        raise CredentialRefreshError("oauth_proxy_invalid") from None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"[A-Za-z0-9.:[\]-]+", parsed.netloc)
    ):
        raise CredentialRefreshError("oauth_proxy_invalid")
    return value.rstrip("/")


def _url_origin(url: str) -> tuple[str, str, int]:
    """Return a canonical origin tuple for token-endpoint confinement."""
    parsed = urlsplit(url)
    port = parsed.port or 443
    return parsed.scheme.lower(), str(parsed.hostname).lower(), port


def _oauth_metadata_url(issuer: str) -> str:
    """Build the RFC 8414 metadata URL, including an issuer path suffix."""
    parsed = urlsplit(issuer)
    suffix = parsed.path.rstrip("/")
    path = f"/.well-known/oauth-authorization-server{suffix}"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _validate_secret(value: object, error_code: str) -> str:
    """Validate a bounded opaque token without including its value in errors."""
    if not isinstance(value, str) or not value:
        raise CredentialRefreshError(error_code)
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError:
        raise CredentialRefreshError(error_code) from None
    if len(encoded) > MAX_TOKEN_BYTES:
        raise CredentialRefreshError(error_code)
    if any(byte < 33 or byte > 126 for byte in encoded):
        raise CredentialRefreshError(error_code)
    return value


def _validate_client_id(value: object) -> str:
    """Validate the public OAuth client identifier."""
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise CredentialRefreshError("oauth_client_id_invalid")
    if any(ord(character) < 33 or ord(character) > 126 for character in value):
        raise CredentialRefreshError("oauth_client_id_invalid")
    return value


def _parse_expires_at(value: object) -> float | None:
    """Accept numeric, RFC 3339, or serde SystemTime expiration encodings."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise CredentialRefreshError("oauth_expires_at_invalid")
    if isinstance(value, (int, float)):
        try:
            numeric = float(value)
        except (OverflowError, ValueError):
            raise CredentialRefreshError("oauth_expires_at_invalid") from None
        if not math.isfinite(numeric) or numeric <= 0:
            raise CredentialRefreshError("oauth_expires_at_invalid")
        if numeric >= MILLISECONDS_EPOCH_THRESHOLD:
            numeric /= 1000
        return numeric
    if isinstance(value, str):
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = dt.datetime.fromisoformat(normalized)
        except (OSError, OverflowError, ValueError):
            raise CredentialRefreshError("oauth_expires_at_invalid") from None
        if parsed.tzinfo is None:
            raise CredentialRefreshError("oauth_expires_at_invalid")
        try:
            expiration = parsed.timestamp()
        except (OSError, OverflowError, ValueError):
            raise CredentialRefreshError("oauth_expires_at_invalid") from None
        if not math.isfinite(expiration) or expiration <= 0:
            raise CredentialRefreshError("oauth_expires_at_invalid")
        return expiration
    if isinstance(value, dict):
        seconds = value.get("secs_since_epoch")
        nanoseconds = value.get("nanos_since_epoch", 0)
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, int)
            or seconds <= 0
            or isinstance(nanoseconds, bool)
            or not isinstance(nanoseconds, int)
            or not 0 <= nanoseconds < 1_000_000_000
        ):
            raise CredentialRefreshError("oauth_expires_at_invalid")
        try:
            expiration = seconds + nanoseconds / 1_000_000_000
        except OverflowError:
            raise CredentialRefreshError("oauth_expires_at_invalid") from None
        if not math.isfinite(expiration):
            raise CredentialRefreshError("oauth_expires_at_invalid")
        return expiration
    raise CredentialRefreshError("oauth_expires_at_invalid")


def _encode_expires_at(template: object, expiration: float) -> int | float | str | dict[str, Any]:
    """Preserve the existing expiration representation when rotating the token."""
    if isinstance(template, str):
        value = dt.datetime.fromtimestamp(expiration, tz=dt.timezone.utc)
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")
    if isinstance(template, dict):
        seconds = int(expiration)
        nanoseconds = int((expiration - seconds) * 1_000_000_000)
        encoded = copy.deepcopy(template)
        encoded["secs_since_epoch"] = seconds
        encoded["nanos_since_epoch"] = nanoseconds
        return encoded
    if isinstance(template, float):
        if template >= MILLISECONDS_EPOCH_THRESHOLD:
            return float(expiration * 1000)
        return float(expiration)
    if isinstance(template, int) and template >= MILLISECONDS_EPOCH_THRESHOLD:
        return int(expiration * 1000)
    return int(expiration)


def _decode_credential(payload: bytes) -> dict[str, Any]:
    """Decode a bounded Keychain JSON object without echoing invalid content."""
    if not payload or len(payload) > MAX_KEYCHAIN_PAYLOAD_BYTES:
        raise CredentialRefreshError("keychain_payload_invalid")
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        raise CredentialRefreshError("keychain_payload_invalid") from None
    if not isinstance(document, dict):
        raise CredentialRefreshError("keychain_payload_invalid")
    server_name = document.get("server_name")
    if server_name != "cloudflare":
        raise CredentialRefreshError("keychain_item_not_cloudflare")
    return document


def _credential_fields(
    document: dict[str, Any],
) -> tuple[str, str, str, dict[str, Any], float | None]:
    """Extract exactly the fields required for freshness and a refresh grant."""
    issuer = document.get("issuer")
    if not isinstance(issuer, str):
        raise CredentialRefreshError("oauth_issuer_missing")
    issuer = _validate_https_url(issuer, "oauth_issuer_invalid")
    client_id = _validate_client_id(document.get("client_id"))
    token_response = document.get("token_response")
    if not isinstance(token_response, dict):
        raise CredentialRefreshError("oauth_token_response_invalid")
    refresh_token = _validate_secret(
        token_response.get("refresh_token"),
        "oauth_refresh_token_missing",
    )
    expires_at = _parse_expires_at(document.get("expires_at"))
    return issuer, client_id, refresh_token, token_response, expires_at


def _validated_refresh_response(response: dict[str, Any]) -> tuple[str, int, str | None]:
    """Validate rotating fields without retaining them in an exception."""
    access_token = _validate_secret(response.get("access_token"), "oauth_access_token_missing")
    expires_in = response.get("expires_in")
    if (
        isinstance(expires_in, bool)
        or not isinstance(expires_in, int)
        or expires_in <= 0
        or expires_in > 365 * 24 * 60 * 60
    ):
        raise CredentialRefreshError("oauth_expires_in_invalid")
    refresh_token = None
    if "refresh_token" in response:
        refresh_token = _validate_secret(
            response["refresh_token"],
            "oauth_rotated_refresh_token_invalid",
        )
    return access_token, expires_in, refresh_token


def _safe_status(
    action: str,
    expires_template: object,
    expires_epoch: float | None,
    refresh_needed: bool,
    now: float,
    updated: bool,
) -> RefreshStatus:
    """Build non-sensitive status fields from expiration metadata only."""
    seconds_remaining = None
    if expires_epoch is not None:
        seconds_remaining = max(0, int(expires_epoch - now))
    expires_at = None
    if expires_epoch is not None:
        if updated:
            expires_at = _encode_expires_at(expires_template, expires_epoch)
        else:
            expires_at = copy.deepcopy(expires_template)
        if isinstance(expires_at, dict):
            expires_at = {
                "nanos_since_epoch": expires_at.get("nanos_since_epoch", 0),
                "secs_since_epoch": expires_at["secs_since_epoch"],
            }
    return RefreshStatus(
        action=action,
        expires_at=expires_at,
        refresh_needed=refresh_needed,
        seconds_remaining=seconds_remaining,
        updated=updated,
    )


def refresh_keychain_credential(
    store: KeychainStore,
    transport: OAuthTransport,
    *,
    service: str = DEFAULT_KEYCHAIN_SERVICE,
    account: str = DEFAULT_KEYCHAIN_ACCOUNT,
    proxy: str = DEFAULT_PROXY,
    refresh_window_seconds: int = DEFAULT_REFRESH_WINDOW_SECONDS,
    dry_status: bool = False,
    now: float | None = None,
) -> RefreshStatus:
    """Refresh one exact Cloudflare MCP credential only when it is near expiry."""
    if (
        isinstance(refresh_window_seconds, bool)
        or not isinstance(refresh_window_seconds, int)
        or refresh_window_seconds < 0
    ):
        raise CredentialRefreshError("refresh_window_invalid")
    current_time = time.time() if now is None else now
    if not math.isfinite(current_time) or current_time <= 0:
        raise CredentialRefreshError("clock_invalid")
    _validate_proxy_url(proxy)

    with store.open_item(service, account) as item:
        document = _decode_credential(item.payload)
        issuer, client_id, refresh_token, token_response, expires_epoch = _credential_fields(
            document
        )
        access_token = token_response.get("access_token")
        access_token_valid = False
        if access_token is not None:
            _validate_secret(access_token, "oauth_access_token_invalid")
            access_token_valid = True
        refresh_needed = (
            not access_token_valid
            or expires_epoch is None
            or expires_epoch - current_time <= refresh_window_seconds
        )
        if dry_status:
            return _safe_status(
                "status",
                document.get("expires_at"),
                expires_epoch,
                refresh_needed,
                current_time,
                False,
            )
        if not refresh_needed:
            return _safe_status(
                "fresh",
                document.get("expires_at"),
                expires_epoch,
                False,
                current_time,
                False,
            )

        response = transport.refresh(issuer, client_id, refresh_token, proxy)
        access_token, expires_in, rotated_refresh_token = _validated_refresh_response(response)
        updated = copy.deepcopy(document)
        updated_token_response = copy.deepcopy(token_response)
        updated_token_response.update(response)
        updated_token_response["access_token"] = access_token
        updated_token_response["expires_in"] = expires_in
        if rotated_refresh_token is None:
            updated_token_response["refresh_token"] = refresh_token
        else:
            updated_token_response["refresh_token"] = rotated_refresh_token
        expiration = current_time + expires_in
        expires_template = document.get("expires_at")
        updated["token_response"] = updated_token_response
        updated["expires_at"] = _encode_expires_at(expires_template, expiration)
        try:
            serialized = json.dumps(
                updated,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError):
            raise CredentialRefreshError("keychain_payload_invalid") from None
        if len(serialized) > MAX_KEYCHAIN_PAYLOAD_BYTES:
            raise CredentialRefreshError("keychain_payload_too_large")
        item.update(serialized)
        return _safe_status(
            "refreshed",
            expires_template,
            expiration,
            False,
            current_time,
            True,
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse only non-sensitive Keychain locators and refresh policy controls."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default=DEFAULT_KEYCHAIN_SERVICE)
    parser.add_argument("--account", default=DEFAULT_KEYCHAIN_ACCOUNT)
    parser.add_argument("--proxy", default=DEFAULT_PROXY)
    parser.add_argument(
        "--lock-file",
        type=pathlib.Path,
        help="Existing-parent override for the non-sensitive advisory lock file.",
    )
    parser.add_argument(
        "--refresh-window-seconds",
        type=int,
        default=DEFAULT_REFRESH_WINDOW_SECONDS,
    )
    parser.add_argument(
        "--dry-status",
        action="store_true",
        help="Report freshness without network access or Keychain modification.",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    store: KeychainStore | None = None,
    transport: OAuthTransport | None = None,
    process_lock: RefreshProcessLock | None = None,
    now: float | None = None,
) -> int:
    """Refresh if necessary and emit one non-sensitive JSON status object."""
    args = parse_args(argv)
    active_store = store if store is not None else MacOSKeychainStore()
    active_transport = transport if transport is not None else RequestsOAuthTransport()
    active_lock = process_lock
    if active_lock is None:
        lock_path = args.lock_file if args.lock_file is not None else default_lock_file()
        active_lock = SecureRefreshLock(
            lock_path,
            create_parent=args.lock_file is None,
        )
    with active_lock:
        status = refresh_keychain_credential(
            active_store,
            active_transport,
            service=args.service,
            account=args.account,
            proxy=args.proxy,
            refresh_window_seconds=args.refresh_window_seconds,
            dry_status=args.dry_status,
            now=now,
        )
    print(json.dumps(status.as_dict(), sort_keys=True))
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    """Convert safe failures to stable JSON without printing exception details."""
    try:
        return main(argv)
    except CredentialRefreshError as error:
        print(json.dumps({"code": error.code, "ok": False}, sort_keys=True), file=sys.stderr)
        return 2
    except Exception:
        print(
            json.dumps(
                {"code": "credential_refresh_internal_error", "ok": False},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
