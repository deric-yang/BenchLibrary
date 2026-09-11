#!/usr/bin/env python3
"""Create, read, and retire one release-scoped uploader credential safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import secrets
import stat
from dataclasses import dataclass, field
from typing import Sequence


TOKEN_ENTROPY_BYTES = 48
MIN_TOKEN_BYTES = 32
MAX_TOKEN_FILE_BYTES = 4096
ALLOWED_TOKEN_MODE = 0o600


class UploadTokenFileError(RuntimeError):
    """A one-time upload token file failed a local security invariant."""


class UploadTokenUnlinkedSyncError(UploadTokenFileError):
    """The key was removed, but retirement ended through an exceptional path."""

    token_file_unlinked = True
    retry_upload = False

    def __init__(self, message: str, *, parent_fsync_completed: bool = False) -> None:
        """Record whether reconciliation durably persisted the absent key name."""
        super().__init__(message)
        self.parent_fsync_completed = parent_fsync_completed


@dataclass
class UploadTokenFile:
    """Bind a secret value to the exact regular file from which it was read."""

    path: pathlib.Path
    device: int
    inode: int
    value: str = field(repr=False)
    _file_fd: int = field(repr=False, compare=False)
    _parent_fd: int = field(repr=False, compare=False)

    @property
    def closed(self) -> bool:
        """Return whether this credential has released its identity anchors."""
        return self._file_fd < 0 or self._parent_fd < 0

    def close(self) -> None:
        """Release identity anchors without risking a double-close on reused fds."""
        descriptors = (self._file_fd, self._parent_fd)
        self._file_fd = -1
        self._parent_fd = -1
        self.value = ""
        for descriptor in descriptors:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    # Do not retry close(2): after EINTR its state is platform-dependent.
                    pass

    def __enter__(self) -> UploadTokenFile:
        """Keep the validated descriptors open for the credential's lifetime."""
        if self.closed:
            raise UploadTokenFileError("Upload token handle is already closed")
        return self

    def __exit__(self, *_error: object) -> None:
        """Release descriptors when a caller leaves the credential scope."""
        self.close()


def _require_secure_platform() -> None:
    """Fail closed when the host cannot provide the required POSIX primitives."""
    required = ("O_CLOEXEC", "O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK", "getuid")
    missing = [name for name in required if not hasattr(os, name)]
    if os.name != "posix" or missing:
        detail = ", ".join(missing) if missing else os.name
        raise UploadTokenFileError(
            f"Secure upload token files are unsupported on this platform: {detail}"
        )
    if (
        os.open not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
        or os.unlink not in os.supports_dir_fd
        or os.stat not in os.supports_follow_symlinks
    ):
        raise UploadTokenFileError(
            "Secure upload token files require dir-fd and no-follow stat support"
        )


def _validate_open_token(info: os.stat_result, path: pathlib.Path) -> None:
    """Require a private, caller-owned regular file with an owner read bit."""
    if not stat.S_ISREG(info.st_mode):
        raise UploadTokenFileError(f"Upload token path is not a regular file: {path}")
    if info.st_uid != os.getuid():
        raise UploadTokenFileError(f"Upload token file is not owned by the current user: {path}")
    mode = stat.S_IMODE(info.st_mode)
    if mode & ~ALLOWED_TOKEN_MODE:
        raise UploadTokenFileError(
            f"Upload token file permissions must not be wider than 0600: {path}"
        )
    if not mode & stat.S_IRUSR:
        raise UploadTokenFileError(f"Upload token file is not owner-readable: {path}")
    if info.st_nlink != 1:
        raise UploadTokenFileError(f"Upload token file must have exactly one link: {path}")


def _open_private_parent(path: pathlib.Path) -> tuple[pathlib.Path, int]:
    """Open and anchor a caller-owned directory that is not writable by other users."""
    try:
        parent = path.parent.resolve(strict=True)
    except (OSError, ValueError) as error:
        raise UploadTokenFileError(
            f"Upload token parent directory is unavailable: {path.parent}"
        ) from error
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        parent_fd = os.open(parent, flags)
    except (OSError, ValueError) as error:
        raise UploadTokenFileError(
            f"Upload token parent directory is unavailable: {parent}"
        ) from error
    try:
        info = os.fstat(parent_fd)
        if not stat.S_ISDIR(info.st_mode):
            raise UploadTokenFileError(f"Upload token parent is not a directory: {parent}")
        if info.st_uid != os.getuid():
            raise UploadTokenFileError(
                f"Upload token parent is not owned by the current user: {parent}"
            )
        if stat.S_IMODE(info.st_mode) & 0o022:
            raise UploadTokenFileError(
                f"Upload token parent must not be writable by group or other users: {parent}"
            )
    except BaseException:
        os.close(parent_fd)
        raise
    return parent, parent_fd


def _optional_lstat(path: pathlib.Path) -> os.stat_result | None:
    """Inspect one repository marker without following it, failing closed on I/O errors."""
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise UploadTokenFileError(
            f"Cannot verify that the upload token path is outside Git: {path}"
        ) from error


def _looks_like_bare_git_repository(path: pathlib.Path) -> bool:
    """Recognize a bare repository without invoking Git or repository configuration."""
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


def _reject_git_repository_path(parent: pathlib.Path) -> None:
    """Refuse repository paths and externally declared Git worktree contexts."""
    git_context = [name for name in ("GIT_DIR", "GIT_WORK_TREE") if name in os.environ]
    if git_context:
        joined = ", ".join(git_context)
        raise UploadTokenFileError(
            f"Upload token paths are forbidden while external Git context is set: {joined}"
        )
    for candidate in (parent, *parent.parents):
        if _optional_lstat(candidate / ".git") is not None:
            raise UploadTokenFileError(
                f"Upload token output cannot be inside a Git worktree: {parent}"
            )
        if _looks_like_bare_git_repository(candidate):
            raise UploadTokenFileError(
                f"Upload token output cannot be inside a Git repository: {parent}"
            )


def _read_limited(fd: int) -> bytes:
    """Read a small credential without allowing an unbounded file allocation."""
    payload = bytearray()
    while len(payload) <= MAX_TOKEN_FILE_BYTES:
        remaining = MAX_TOKEN_FILE_BYTES + 1 - len(payload)
        chunk = os.read(fd, min(4096, remaining))
        if not chunk:
            break
        payload.extend(chunk)
    if len(payload) > MAX_TOKEN_FILE_BYTES:
        raise UploadTokenFileError(
            f"Upload token file exceeds {MAX_TOKEN_FILE_BYTES} bytes"
        )
    return bytes(payload)


def read_one_time_upload_key(path: pathlib.Path) -> UploadTokenFile:
    """Read one private token without following its final path component."""
    _require_secure_platform()
    supplied = path.absolute()
    parent, parent_fd = _open_private_parent(supplied)
    target = parent / supplied.name
    try:
        _reject_git_repository_path(parent)
    except BaseException:
        os.close(parent_fd)
        raise
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(target.name, flags, dir_fd=parent_fd)
    except (OSError, ValueError) as error:
        os.close(parent_fd)
        raise UploadTokenFileError(f"Upload token file is missing or unsafe: {target}") from error

    keep_open = False
    try:
        before = os.fstat(fd)
        _validate_open_token(before, target)
        payload = _read_limited(fd)
        after = os.fstat(fd)
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_uid",
            "st_size",
            "st_mtime_ns",
            "st_nlink",
        )
        if any(getattr(before, name) != getattr(after, name) for name in stable_fields):
            raise UploadTokenFileError(f"Upload token file changed while being read: {target}")
        try:
            path_info = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError as error:
            raise UploadTokenFileError(
                f"Upload token file was removed while being read: {target}"
            ) from error
        _validate_open_token(path_info, target)
        if (path_info.st_dev, path_info.st_ino) != (before.st_dev, before.st_ino):
            raise UploadTokenFileError(f"Upload token path changed while being read: {target}")

        try:
            value = payload.decode("ascii").strip()
        except UnicodeDecodeError as error:
            raise UploadTokenFileError("Upload token must contain printable ASCII") from error
        if len(value.encode("ascii")) < MIN_TOKEN_BYTES:
            raise UploadTokenFileError("Upload token file is empty or invalid")
        if any(ord(character) < 33 or ord(character) > 126 for character in value):
            raise UploadTokenFileError(
                "Upload token must contain printable ASCII without whitespace"
            )
        # Re-check after the read so a repository marker introduced while the
        # file was open cannot turn a hand-created token into an accepted input.
        _reject_git_repository_path(parent)
        result = UploadTokenFile(
            target,
            before.st_dev,
            before.st_ino,
            value,
            fd,
            parent_fd,
        )
        keep_open = True
        return result
    except UploadTokenFileError:
        raise
    except OSError as error:
        raise UploadTokenFileError(f"Could not safely read upload token file: {target}") from error
    finally:
        if not keep_open:
            os.close(fd)
            os.close(parent_fd)


def _sync_retired_parent(parent_fd: int) -> None:
    """Durably persist an absent token name and make that state non-retryable."""
    try:
        os.fsync(parent_fd)
    except BaseException as error:
        # Once unlink has happened, even cancellation must become a classified
        # result; otherwise a supervisor may replay an already-finished upload.
        raise UploadTokenUnlinkedSyncError(
            "Upload token was unlinked, but its parent directory did not fsync; "
            "do not retry the upload with this credential"
        ) from error


def _raise_if_interrupted_unlink_completed(
    token_file: UploadTokenFile,
    original_error: BaseException,
) -> None:
    """Classify an interrupted unlink by reconciling the still-open inode."""
    try:
        original = os.fstat(token_file._file_fd)
    except BaseException:
        return
    if (
        (original.st_dev, original.st_ino) != (token_file.device, token_file.inode)
        or original.st_nlink != 0
    ):
        return
    try:
        current = os.stat(
            token_file.path.name,
            dir_fd=token_file._parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        current = None
    except BaseException:
        return
    if current is not None and (current.st_dev, current.st_ino) == (
        token_file.device,
        token_file.inode,
    ):
        return

    parent_fsync_completed = False
    try:
        os.fsync(token_file._parent_fd)
        parent_fsync_completed = True
    except BaseException:
        pass
    if parent_fsync_completed:
        message = (
            "Upload token was unlinked and its parent directory was reconciled, "
            "but retirement was interrupted; do not retry the upload with this credential"
        )
    else:
        message = (
            "Upload token was unlinked during an interrupted retirement, but its parent "
            "directory did not fsync; do not retry the upload with this credential"
        )
    raise UploadTokenUnlinkedSyncError(
        message,
        parent_fsync_completed=parent_fsync_completed,
    ) from original_error


def delete_one_time_upload_key(token_file: UploadTokenFile) -> None:
    """Delete only the same directory entry that supplied the in-memory token."""
    _require_secure_platform()
    if token_file.closed:
        raise UploadTokenFileError("Upload token handle is already closed")
    retirement_started = False
    try:
        original = os.fstat(token_file._file_fd)
        if (original.st_dev, original.st_ino) != (token_file.device, token_file.inode):
            raise UploadTokenFileError("Upload token handle identity changed")
        try:
            current = os.stat(
                token_file.path.name,
                dir_fd=token_file._parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            after_removal = os.fstat(token_file._file_fd)
            if after_removal.st_nlink != 0:
                raise UploadTokenFileError(
                    "Upload token path is missing but the original file remains linked; "
                    "refusing to claim retirement"
                )
            # Another actor removed the same anchored inode. Persist that
            # already-absent directory entry before claiming clean retirement.
            retirement_started = True
            _sync_retired_parent(token_file._parent_fd)
            return
        _validate_open_token(current, token_file.path)
        if (current.st_dev, current.st_ino) != (token_file.device, token_file.inode):
            raise UploadTokenFileError(
                f"Upload token path now identifies a different file; refusing deletion: {token_file.path}"
            )
        # POSIX has no atomic compare-and-unlink operation. The private parent
        # directory invariant prevents an untrusted writer from exploiting the
        # necessarily small fstatat(2)-to-unlinkat(2) window.
        retirement_started = True
        os.unlink(token_file.path.name, dir_fd=token_file._parent_fd)
        _sync_retired_parent(token_file._parent_fd)
    except UploadTokenFileError:
        raise
    except BaseException as error:
        if retirement_started:
            _raise_if_interrupted_unlink_completed(token_file, error)
        if isinstance(error, OSError):
            raise UploadTokenFileError(
                f"Could not safely retire upload token file: {token_file.path}"
            ) from error
        raise
    finally:
        token_file.close()


def create_one_time_upload_key(path: pathlib.Path) -> UploadTokenFile:
    """Atomically create one 0600 token file and durably persist its directory entry."""
    _require_secure_platform()
    supplied = path.absolute()
    parent, parent_fd = _open_private_parent(supplied)
    target = parent / supplied.name

    created_identity: tuple[int, int] | None = None
    file_fd: int | None = None
    try:
        _reject_git_repository_path(parent)
        token = secrets.token_urlsafe(TOKEN_ENTROPY_BYTES)
        payload = token.encode("ascii")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
        try:
            file_fd = os.open(target.name, flags, ALLOWED_TOKEN_MODE, dir_fd=parent_fd)
        except OSError as error:
            raise UploadTokenFileError(
                f"Upload token output already exists or is unsafe: {target}"
            ) from error
        initial = os.fstat(file_fd)
        created_identity = (initial.st_dev, initial.st_ino)
        if not stat.S_ISREG(initial.st_mode) or initial.st_uid != os.getuid():
            raise UploadTokenFileError(f"Created upload token file failed validation: {target}")
        os.fchmod(file_fd, ALLOWED_TOKEN_MODE)
        written = 0
        while written < len(payload):
            count = os.write(file_fd, payload[written:])
            if count <= 0:
                raise UploadTokenFileError(f"Could not write upload token file: {target}")
            written += count
        os.fsync(file_fd)
        info = os.fstat(file_fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != ALLOWED_TOKEN_MODE
            or info.st_size != len(payload)
            or info.st_nlink != 1
            or (info.st_dev, info.st_ino) != created_identity
        ):
            raise UploadTokenFileError(f"Created upload token file failed validation: {target}")
        path_info = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
        _validate_open_token(path_info, target)
        if stat.S_IMODE(path_info.st_mode) != ALLOWED_TOKEN_MODE:
            raise UploadTokenFileError(f"Created upload token file failed validation: {target}")
        if (path_info.st_dev, path_info.st_ino) != created_identity:
            raise UploadTokenFileError(f"Upload token output changed during creation: {target}")
        _reject_git_repository_path(parent)
        os.fsync(parent_fd)
        result = UploadTokenFile(
            target,
            info.st_dev,
            info.st_ino,
            token,
            file_fd,
            parent_fd,
        )
        file_fd = None
        parent_fd = -1
        return result
    except BaseException as error:
        cleanup_identity = created_identity
        if cleanup_identity is None and file_fd is not None:
            try:
                cleanup_info = os.fstat(file_fd)
                cleanup_identity = (cleanup_info.st_dev, cleanup_info.st_ino)
            except OSError:
                pass
        if cleanup_identity is not None:
            try:
                current = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == cleanup_identity:
                    os.unlink(target.name, dir_fd=parent_fd)
                    os.fsync(parent_fd)
            except (FileNotFoundError, OSError):
                pass
        if not isinstance(error, Exception) or isinstance(error, UploadTokenFileError):
            raise
        raise UploadTokenFileError(
            f"Could not safely create upload token file: {target}"
        ) from error
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if parent_fd >= 0:
            os.close(parent_fd)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the explicit destination for a new release-scoped key."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Create a key while exposing only its path, length, and digest."""
    args = parse_args(argv)
    with create_one_time_upload_key(args.output) as token_file:
        payload = {
            "bytes": len(token_file.value.encode("ascii")),
            "path": str(token_file.path),
            "sha256": hashlib.sha256(token_file.value.encode("ascii")).hexdigest(),
        }
        print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UploadTokenFileError as error:
        raise SystemExit(str(error)) from error
