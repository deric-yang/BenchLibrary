"""Security tests for release-scoped uploader credential files."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import create_one_time_upload_key as key_module
from scripts.create_one_time_upload_key import (
    UploadTokenFileError,
    UploadTokenUnlinkedSyncError,
    create_one_time_upload_key,
    delete_one_time_upload_key,
    main as create_key_main,
    read_one_time_upload_key,
)
from scripts.upload_public_release import (
    UploadFailure,
    _upload_with_token,
    parse_args as parse_upload_args,
)


class OneTimeUploadKeyTests(unittest.TestCase):
    """Exercise creation, no-follow reads, and identity-bound retirement."""

    @staticmethod
    def _write_token(path: Path, value: bytes = b"x" * 64, mode: int = 0o600) -> None:
        """Create one explicit token fixture independent of the process umask."""
        path.write_bytes(value)
        path.chmod(mode)

    def test_generator_creates_exact_0600_regular_file(self) -> None:
        """The generated secret is durable, private, and hidden from repr."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "upload.key"

            with create_one_time_upload_key(path) as token_file:
                payload = path.read_bytes()
                info = path.stat()
                self.assertTrue(stat.S_ISREG(info.st_mode))
                self.assertEqual(info.st_uid, os.getuid())
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
                self.assertEqual(payload.decode("ascii"), token_file.value)
                self.assertEqual(len(payload), 64)
                self.assertNotIn(token_file.value, repr(token_file))
                self.assertNotIn("_file_fd", repr(token_file))
                self.assertNotIn("_parent_fd", repr(token_file))

            self.assertTrue(path.is_file())
            self.assertTrue(token_file.closed)
            self.assertEqual(token_file.value, "")

    def test_generator_cli_prints_only_path_length_and_sha(self) -> None:
        """Automation metadata never includes the raw uploader credential."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "upload.key"
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                self.assertEqual(create_key_main(["--output", str(path)]), 0)

            raw_token = path.read_text(encoding="ascii")
            output = stdout.getvalue()
            metadata = json.loads(output)
            self.assertEqual(
                metadata,
                {
                    "bytes": len(raw_token.encode("ascii")),
                    "path": str(path.parent.resolve() / path.name),
                    "sha256": hashlib.sha256(raw_token.encode("ascii")).hexdigest(),
                },
            )
            self.assertNotIn(raw_token, output)

    def test_generator_refuses_existing_file_and_symlink(self) -> None:
        """O_EXCL and O_NOFOLLOW prevent overwrite and symlink traversal."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            existing = base / "existing.key"
            self._write_token(existing)
            with self.assertRaisesRegex(UploadTokenFileError, "already exists or is unsafe"):
                create_one_time_upload_key(existing)
            self.assertEqual(existing.read_bytes(), b"x" * 64)

            target = base / "target.key"
            self._write_token(target, b"t" * 64)
            link = base / "linked.key"
            link.symlink_to(target)
            with self.assertRaisesRegex(UploadTokenFileError, "already exists or is unsafe"):
                create_one_time_upload_key(link)
            self.assertEqual(target.read_bytes(), b"t" * 64)

    def test_generator_rejects_git_worktrees_and_bare_repositories(self) -> None:
        """A credential can never be created under a Git-controlled directory."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)

            worktree = base / "worktree"
            (worktree / ".git").mkdir(parents=True)
            linked_worktree = base / "linked-worktree"
            linked_worktree.mkdir()
            (linked_worktree / ".git").write_text(
                "gitdir: ../git-dirs/linked\n",
                encoding="utf-8",
            )
            bare = base / "bare.git"
            (bare / "objects").mkdir(parents=True)
            (bare / "refs").mkdir()
            (bare / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (bare / "config").write_text("[core]\n\tbare = true\n", encoding="ascii")

            for repository in (worktree, linked_worktree, bare):
                with self.subTest(repository=repository.name):
                    destination = repository / "nested" / "upload.key"
                    destination.parent.mkdir()
                    with (
                        mock.patch.object(key_module.secrets, "token_urlsafe") as generate,
                        self.assertRaisesRegex(UploadTokenFileError, "inside a Git"),
                    ):
                        create_one_time_upload_key(destination)
                    generate.assert_not_called()
                    self.assertFalse(destination.exists())

    def test_reader_rejects_manual_token_inside_git_and_closes_parent(self) -> None:
        """A hand-created file cannot bypass the repository boundary."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory) / "worktree"
            (repository / ".git").mkdir(parents=True)
            nested = repository / "nested"
            nested.mkdir()
            path = nested / "upload.key"
            self._write_token(path)
            opened: list[int] = []
            real_open = os.open

            def recording_open(*args: object, **kwargs: object) -> int:
                descriptor = real_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            with (
                mock.patch.object(key_module, "_require_secure_platform"),
                mock.patch.object(key_module.os, "open", side_effect=recording_open),
                self.assertRaisesRegex(UploadTokenFileError, "inside a Git"),
            ):
                read_one_time_upload_key(path)

            self.assertEqual(len(opened), 1)
            with self.assertRaises(OSError):
                os.fstat(opened[0])
            self.assertEqual(path.read_bytes(), b"x" * 64)

    def test_generator_and_reader_reject_external_git_context(self) -> None:
        """GIT_DIR/GIT_WORK_TREE cannot make an unmarked directory a hidden worktree."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            path = base / "upload.key"
            git_environment = {
                "GIT_DIR": str(base / "external-metadata.git"),
                "GIT_WORK_TREE": str(base),
            }
            with (
                mock.patch.dict(os.environ, git_environment, clear=False),
                mock.patch.object(key_module.secrets, "token_urlsafe") as generate,
                self.assertRaisesRegex(UploadTokenFileError, "external Git context"),
            ):
                create_one_time_upload_key(path)
            generate.assert_not_called()
            self.assertFalse(path.exists())

            self._write_token(path)
            with (
                mock.patch.dict(os.environ, git_environment, clear=False),
                self.assertRaisesRegex(UploadTokenFileError, "external Git context"),
            ):
                read_one_time_upload_key(path)
            self.assertEqual(path.read_bytes(), b"x" * 64)

    def test_reader_accepts_only_private_owner_readable_modes(self) -> None:
        """Both 0600 and stricter 0400 files are valid compatibility inputs."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            for mode in (0o600, 0o400):
                with self.subTest(mode=oct(mode)):
                    path = base / f"upload-{mode:o}.key"
                    self._write_token(path, mode=mode)
                    with read_one_time_upload_key(path) as token_file:
                        self.assertEqual(token_file.value, "x" * 64)

            legacy = base / "legacy-newline.key"
            self._write_token(legacy, b"\n" + b"x" * 64 + b"\r\n")
            with read_one_time_upload_key(legacy) as token_file:
                self.assertEqual(token_file.value, "x" * 64)

            for mode in (0o640, 0o644, 0o700, 0o200):
                with self.subTest(mode=oct(mode)):
                    path = base / f"invalid-{mode:o}.key"
                    self._write_token(path, mode=mode)
                    with self.assertRaises(UploadTokenFileError):
                        read_one_time_upload_key(path)

    def test_reader_rejects_wrong_owner(self) -> None:
        """The regular file must belong to the effective local caller."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory).resolve()
            path = base / "upload.key"
            self._write_token(path)
            actual_uid = os.getuid()
            flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
            parent_fd = os.open(base, flags)

            with (
                mock.patch.object(
                    key_module,
                    "_open_private_parent",
                    return_value=(base, parent_fd),
                ),
                mock.patch.object(key_module.os, "getuid", return_value=actual_uid + 1),
                self.assertRaisesRegex(UploadTokenFileError, "not owned by the current user"),
            ):
                read_one_time_upload_key(path)

    def test_reader_rejects_group_writable_parent(self) -> None:
        """The containing directory must exclude untrusted replacement writers."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            path = base / "upload.key"
            self._write_token(path)
            base.chmod(0o770)
            try:
                with self.assertRaisesRegex(UploadTokenFileError, "parent must not be writable"):
                    read_one_time_upload_key(path)
            finally:
                base.chmod(0o700)

    def test_reader_rejects_symlink_directory_fifo_and_hardlink(self) -> None:
        """No-follow and regular single-link checks reject ambiguous objects promptly."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            target = base / "target.key"
            self._write_token(target)
            link = base / "linked.key"
            link.symlink_to(target)
            with self.assertRaises(UploadTokenFileError):
                read_one_time_upload_key(link)
            self.assertEqual(target.read_bytes(), b"x" * 64)

            directory = base / "directory.key"
            directory.mkdir()
            with self.assertRaisesRegex(UploadTokenFileError, "not a regular file"):
                read_one_time_upload_key(directory)

            second_link = base / "hardlink.key"
            os.link(target, second_link)
            with self.assertRaisesRegex(UploadTokenFileError, "exactly one link"):
                read_one_time_upload_key(target)

            if hasattr(os, "mkfifo"):
                fifo = base / "fifo.key"
                os.mkfifo(fifo, mode=0o600)
                real_open = os.open

                def require_nonblocking(*args: object, **kwargs: object) -> int:
                    if args[0] == fifo.name:
                        flags = int(args[1])
                        self.assertTrue(flags & os.O_NONBLOCK)
                        self.assertTrue(flags & os.O_NOFOLLOW)
                    return real_open(*args, **kwargs)

                with (
                    mock.patch.object(key_module, "_require_secure_platform"),
                    mock.patch.object(key_module.os, "open", side_effect=require_nonblocking),
                    self.assertRaisesRegex(UploadTokenFileError, "not a regular file"),
                ):
                    read_one_time_upload_key(fifo)

    def test_reader_rejects_invalid_or_oversized_content(self) -> None:
        """Normalized credentials stay bounded and contain only visible ASCII."""
        fixtures = {
            "short.key": b"x" * 31,
            "unicode.key": b"x" * 40 + b"\xff",
            "space.key": b"x" * 32 + b" " + b"y" * 32,
            "oversized.key": b"x" * (key_module.MAX_TOKEN_FILE_BYTES + 1),
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            for name, value in fixtures.items():
                with self.subTest(name=name):
                    path = base / name
                    self._write_token(path, value)
                    with self.assertRaises(UploadTokenFileError):
                        read_one_time_upload_key(path)

    def test_reader_closes_descriptors_after_validation_error(self) -> None:
        """A failed read does not leak either identity anchor."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "short.key"
            self._write_token(path, b"x" * 8)
            opened: list[int] = []
            real_open = os.open

            def recording_open(*args: object, **kwargs: object) -> int:
                descriptor = real_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            with (
                mock.patch.object(key_module, "_require_secure_platform"),
                mock.patch.object(key_module.os, "open", side_effect=recording_open),
                self.assertRaises(UploadTokenFileError),
            ):
                read_one_time_upload_key(path)

            self.assertEqual(len(opened), 2)
            for descriptor in opened:
                with self.assertRaises(OSError):
                    os.fstat(descriptor)

    def test_reader_closes_parent_descriptor_for_invalid_api_path(self) -> None:
        """A non-shell NUL path cannot strand the already-opened parent fd."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            invalid_path = Path(f"{base}/invalid\x00.key")
            opened: list[int] = []
            real_open = os.open

            def recording_open(*args: object, **kwargs: object) -> int:
                descriptor = real_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            with (
                mock.patch.object(key_module, "_require_secure_platform"),
                mock.patch.object(key_module.os, "open", side_effect=recording_open),
                self.assertRaises(UploadTokenFileError),
            ):
                read_one_time_upload_key(invalid_path)

            self.assertEqual(len(opened), 1)
            with self.assertRaises(OSError):
                os.fstat(opened[0])

    def test_reader_detects_path_replacement_during_read(self) -> None:
        """The open descriptor and anchored directory expose a pathname swap."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "upload.key"
            self._write_token(path, b"a" * 64)
            real_read = key_module._read_limited

            def replace_after_read(descriptor: int) -> bytes:
                payload = real_read(descriptor)
                path.unlink()
                self._write_token(path, b"b" * 64)
                return payload

            with (
                mock.patch.object(key_module, "_read_limited", side_effect=replace_after_read),
                self.assertRaisesRegex(UploadTokenFileError, "changed while being read|path changed"),
            ):
                read_one_time_upload_key(path)

            self.assertEqual(path.read_bytes(), b"b" * 64)

    def test_retirement_deletes_only_the_opened_inode(self) -> None:
        """Verified success retires the exact path and closes both anchors."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "upload.key"
            self._write_token(path)
            token_file = read_one_time_upload_key(path)

            delete_one_time_upload_key(token_file)

            self.assertFalse(path.exists())
            self.assertTrue(token_file.closed)
            self.assertEqual(token_file.value, "")

    def test_retirement_preserves_replacement_file_and_symlink(self) -> None:
        """A path swap fails closed and never unlinks the replacement."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            path = base / "upload.key"
            self._write_token(path, b"a" * 64)
            token_file = read_one_time_upload_key(path)
            path.unlink()
            self._write_token(path, b"b" * 64)

            with self.assertRaises(UploadTokenFileError):
                delete_one_time_upload_key(token_file)

            self.assertEqual(path.read_bytes(), b"b" * 64)
            self.assertTrue(token_file.closed)

            token_file = read_one_time_upload_key(path)
            symlink_target = base / "symlink-target.key"
            self._write_token(symlink_target, b"c" * 64)
            path.unlink()
            path.symlink_to(symlink_target)

            with self.assertRaises(UploadTokenFileError):
                delete_one_time_upload_key(token_file)

            self.assertTrue(path.is_symlink())
            self.assertEqual(symlink_target.read_bytes(), b"c" * 64)
            self.assertTrue(token_file.closed)

    def test_retirement_rejects_closed_handle_and_accepts_missing_path(self) -> None:
        """A closed handle cannot delete; an already absent exact name is retired."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            path = base / "upload.key"
            self._write_token(path)
            token_file = read_one_time_upload_key(path)
            token_file.close()
            with self.assertRaisesRegex(UploadTokenFileError, "already closed"):
                delete_one_time_upload_key(token_file)
            self.assertTrue(path.is_file())

            token_file = read_one_time_upload_key(path)
            path.unlink()
            delete_one_time_upload_key(token_file)
            self.assertTrue(token_file.closed)

    def test_retirement_rejects_renamed_or_hardlinked_original(self) -> None:
        """A missing original name is safe only when the open inode has no links."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            path = base / "upload.key"
            renamed = base / "renamed.key"
            self._write_token(path)
            token_file = read_one_time_upload_key(path)
            path.rename(renamed)

            with self.assertRaisesRegex(UploadTokenFileError, "remains linked"):
                delete_one_time_upload_key(token_file)

            self.assertTrue(renamed.is_file())
            self.assertTrue(token_file.closed)

            renamed.rename(path)
            token_file = read_one_time_upload_key(path)
            hardlink = base / "hardlink.key"
            os.link(path, hardlink)
            path.unlink()

            with self.assertRaisesRegex(UploadTokenFileError, "remains linked"):
                delete_one_time_upload_key(token_file)

            self.assertTrue(hardlink.is_file())
            self.assertTrue(token_file.closed)

    def test_retirement_distinguishes_unlink_from_directory_sync_failure(self) -> None:
        """Every catchable post-unlink interruption becomes a non-retryable state."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            failures = (
                OSError("simulated directory sync failure"),
                KeyboardInterrupt(),
                SystemExit("simulated cancellation"),
            )
            for index, failure in enumerate(failures):
                with self.subTest(failure=type(failure).__name__):
                    path = base / f"upload-{index}.key"
                    self._write_token(path)
                    token_file = read_one_time_upload_key(path)

                    with (
                        mock.patch.object(key_module.os, "fsync", side_effect=failure),
                        self.assertRaises(UploadTokenUnlinkedSyncError) as caught,
                    ):
                        delete_one_time_upload_key(token_file)

                    self.assertTrue(caught.exception.token_file_unlinked)
                    self.assertFalse(caught.exception.parent_fsync_completed)
                    self.assertFalse(caught.exception.retry_upload)
                    self.assertIsInstance(caught.exception.__cause__, type(failure))
                    self.assertFalse(path.exists())
                    self.assertTrue(token_file.closed)
                    self.assertEqual(token_file.value, "")

    def test_retirement_syncs_a_name_removed_by_another_actor(self) -> None:
        """An already-absent anchored inode is not clean until its parent syncs."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "upload.key"
            self._write_token(path)
            token_file = read_one_time_upload_key(path)
            path.unlink()

            with (
                mock.patch.object(
                    key_module.os,
                    "fsync",
                    side_effect=OSError("simulated directory sync failure"),
                ) as sync,
                self.assertRaises(UploadTokenUnlinkedSyncError) as caught,
            ):
                delete_one_time_upload_key(token_file)

            sync.assert_called_once()
            self.assertTrue(caught.exception.token_file_unlinked)
            self.assertFalse(caught.exception.parent_fsync_completed)
            self.assertFalse(caught.exception.retry_upload)
            self.assertFalse(path.exists())
            self.assertTrue(token_file.closed)
            self.assertEqual(token_file.value, "")

    def test_retirement_reconciles_interrupt_raised_after_unlink(self) -> None:
        """An unlink wrapper cannot hide a completed deletion behind cancellation."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            real_unlink = os.unlink
            for index, failure in enumerate((KeyboardInterrupt(), SystemExit("cancelled"))):
                with self.subTest(failure=type(failure).__name__):
                    path = base / f"upload-{index}.key"
                    self._write_token(path)
                    token_file = read_one_time_upload_key(path)

                    def unlink_then_interrupt(*args: object, **kwargs: object) -> None:
                        real_unlink(*args, **kwargs)
                        raise failure

                    with (
                        mock.patch.object(key_module, "_require_secure_platform"),
                        mock.patch.object(
                            key_module.os,
                            "unlink",
                            side_effect=unlink_then_interrupt,
                        ),
                        self.assertRaises(UploadTokenUnlinkedSyncError) as caught,
                    ):
                        delete_one_time_upload_key(token_file)

                    self.assertTrue(caught.exception.token_file_unlinked)
                    self.assertTrue(caught.exception.parent_fsync_completed)
                    self.assertFalse(caught.exception.retry_upload)
                    self.assertIs(caught.exception.__cause__, failure)
                    self.assertFalse(path.exists())
                    self.assertTrue(token_file.closed)
                    self.assertEqual(token_file.value, "")

    def test_creation_failure_removes_the_partial_file(self) -> None:
        """An interrupted secure create does not strand a partial credential."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "upload.key"
            with (
                mock.patch.object(key_module.os, "fchmod", side_effect=OSError("simulated")),
                self.assertRaises(UploadTokenFileError),
            ):
                create_one_time_upload_key(path)
            self.assertFalse(path.exists())

    def test_initial_file_stat_failure_removes_the_created_entry(self) -> None:
        """A signal-like failure immediately after O_EXCL cannot strand an empty key."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "upload.key"
            real_fstat = os.fstat
            calls = 0

            def fail_first_file_stat(descriptor: int) -> os.stat_result:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated initial file fstat failure")
                return real_fstat(descriptor)

            with (
                mock.patch.object(key_module.os, "fstat", side_effect=fail_first_file_stat),
                self.assertRaises(UploadTokenFileError),
            ):
                create_one_time_upload_key(path)

            self.assertGreaterEqual(calls, 3)
            self.assertFalse(path.exists())

    def test_entropy_failure_closes_parent_descriptor(self) -> None:
        """A failure before file creation still releases the anchored directory."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "upload.key"
            opened: list[int] = []
            real_open = os.open

            def recording_open(*args: object, **kwargs: object) -> int:
                descriptor = real_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            with (
                mock.patch.object(key_module, "_require_secure_platform"),
                mock.patch.object(key_module.os, "open", side_effect=recording_open),
                mock.patch.object(
                    key_module.secrets,
                    "token_urlsafe",
                    side_effect=OSError("simulated entropy failure"),
                ),
                self.assertRaises(UploadTokenFileError),
            ):
                create_one_time_upload_key(path)

            self.assertEqual(len(opened), 1)
            with self.assertRaises(OSError):
                os.fstat(opened[0])
            self.assertFalse(path.exists())

    def test_upload_cli_defaults_to_retirement_and_accepts_legacy_flag(self) -> None:
        """Successful retirement is mandatory while the old positive flag still parses."""
        common = [
            "--root",
            "/tmp/release",
            "--endpoint",
            "https://upload.invalid",
            "--token-file",
            "/tmp/upload.key",
        ]
        self.assertTrue(parse_upload_args(common).delete_token_on_success)
        self.assertTrue(
            parse_upload_args([*common, "--delete-token-on-success"]).delete_token_on_success
        )

    def test_upload_rejects_state_or_inventory_aliasing_the_token(self) -> None:
        """Operational JSON cannot read from or replace the credential path."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            root = base / "release"
            root.mkdir()
            for colliding_option, message in (
                ("--state-file", "Upload state cannot replace"),
                ("--inventory-file", "inventory snapshot cannot replace"),
            ):
                with self.subTest(colliding_option=colliding_option):
                    token_path = base / f"{colliding_option[2:]}.key"
                    state_path = base / f"{colliding_option[2:]}.state.jsonl"
                    inventory_path = base / f"{colliding_option[2:]}.inventory.json"
                    arguments = [
                        "--root",
                        str(root),
                        "--endpoint",
                        "https://upload.invalid",
                        "--token-file",
                        str(token_path),
                        "--state-file",
                        str(state_path),
                        "--inventory-file",
                        str(inventory_path),
                        colliding_option,
                        str(token_path),
                    ]
                    args = parse_upload_args(arguments)
                    with create_one_time_upload_key(token_path) as token_file:
                        with self.assertRaisesRegex(UploadFailure, message):
                            _upload_with_token(
                                args,
                                root,
                                root / "data/public_manifest.json",
                                token_file,
                            )
                    self.assertTrue(token_path.is_file())


if __name__ == "__main__":
    unittest.main()
