from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("install_into", ROOT / "scripts/install_into.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _snapshot(root: Path) -> tuple[tuple[object, ...], ...]:
    if not os.path.lexists(root):
        return ((".", "absent"),)
    records: list[tuple[object, ...]] = []
    paths = [root, *sorted(root.rglob("*"), key=lambda item: item.as_posix())]
    for path in paths:
        metadata = os.lstat(path)
        relative = "." if path == root else path.relative_to(root).as_posix()
        kind = (
            "symlink"
            if stat.S_ISLNK(metadata.st_mode)
            else "file"
            if stat.S_ISREG(metadata.st_mode)
            else "directory"
            if stat.S_ISDIR(metadata.st_mode)
            else "special"
        )
        content: object = None
        if kind == "file":
            content = path.read_bytes()
        elif kind == "symlink":
            content = os.readlink(path)
        records.append(
            (
                relative,
                kind,
                stat.S_IMODE(metadata.st_mode),
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_size,
                metadata.st_mtime_ns,
                content,
            )
        )
    return tuple(records)


def _stage_names(parent: Path) -> list[str]:
    return sorted(path.name for path in parent.glob(".adaptive-install-*"))


class InstallerTests(unittest.TestCase):
    def test_existing_target_modes_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            nested = target / "existing/data.txt"
            nested.parent.mkdir(parents=True)
            nested.write_bytes(b"keep exactly\n")
            nested.chmod(0o640)
            before = _snapshot(target)
            runner_calls: list[str] = []
            real_open = os.open

            def read_only_open(path, flags, *args, **kwargs):
                write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC
                if flags & write_flags:
                    raise AssertionError(f"planning opened for mutation: {path}")
                return real_open(path, flags, *args, **kwargs)

            invocations = (
                lambda: MODULE.install(
                    ROOT,
                    target,
                    force=False,
                    dry_run=False,
                    runner=lambda command: runner_calls.append(command),
                ),
                lambda: MODULE.plan_install(ROOT, target),
                lambda: MODULE.install(
                    ROOT,
                    target,
                    force=False,
                    dry_run=True,
                    runner=lambda command: runner_calls.append(command),
                ),
            )
            plans = []
            output = io.StringIO()
            with (
                patch.object(MODULE.os, "open", side_effect=read_only_open),
                patch.object(MODULE.os, "mkdir", side_effect=AssertionError("mkdir")),
                patch.object(MODULE.os, "unlink", side_effect=AssertionError("unlink")),
                patch.object(MODULE.os, "rename", side_effect=AssertionError("rename")),
                patch.object(MODULE.os, "replace", side_effect=AssertionError("replace")),
                patch.object(MODULE.os, "chmod", side_effect=AssertionError("chmod")),
                contextlib.redirect_stdout(output),
            ):
                for invoke in invocations:
                    plans.append(invoke())
                    self.assertEqual(_snapshot(target), before)

            self.assertEqual(plans[0], plans[1])
            self.assertEqual(plans[1], plans[2])
            self.assertEqual(plans[0]["version"], 1)
            self.assertEqual(plans[0]["target_state"], "directory")
            entries = plans[0]["entries"]
            self.assertEqual(
                [item["path"].encode("utf-8") for item in entries],
                sorted(item["path"].encode("utf-8") for item in entries),
            )
            self.assertEqual(len({item["path"] for item in entries}), len(entries))
            for item in entries:
                self.assertEqual(len(item["sha256"]), 64)
                self.assertGreaterEqual(item["size"], 0)
            self.assertEqual(runner_calls, [])
            self.assertIn("read-only plan", output.getvalue().lower())

    def test_force_is_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            authority = target / "architecture/system.yaml"
            authority.parent.mkdir(parents=True)
            authority.write_bytes(b"target authority\n")
            before = _snapshot(target)
            with self.assertRaises(SystemExit) as raised:
                MODULE.install(ROOT, target, force=True, dry_run=False)
            self.assertIn("--force", str(raised.exception))
            self.assertIn("no longer supported", str(raised.exception).lower())
            self.assertEqual(_snapshot(target), before)

    def test_payload_is_sorted_safe_duplicate_free_and_profile_explicit(self) -> None:
        generic = MODULE.build_payload(ROOT)
        bitrix = MODULE.build_payload(ROOT, profile_kind="bitrix")
        generic_paths = [entry.path for entry in generic]
        bitrix_paths = [entry.path for entry in bitrix]
        self.assertEqual(
            [path.encode("utf-8") for path in generic_paths],
            sorted(path.encode("utf-8") for path in generic_paths),
        )
        self.assertEqual(len(generic_paths), len(set(generic_paths)))
        self.assertIn("AGENTS.md", generic_paths)
        self.assertNotIn("local/AGENTS.md", generic_paths)
        self.assertIn("local/AGENTS.md", bitrix_paths)
        local_guidance = next(entry for entry in bitrix if entry.path == "local/AGENTS.md")
        self.assertEqual(local_guidance.content, (ROOT / "docs/bitrix-local-AGENTS.md").read_bytes())
        self.assertFalse(set(MODULE.TARGET_OWNED_ARCHITECTURE) & set(generic_paths))
        for entry in generic:
            self.assertEqual(entry.size, len(entry.content))
            self.assertEqual(entry.sha256, hashlib.sha256(entry.content).hexdigest())
        with patch.object(
            MODULE,
            "MANAGED_FILES",
            (*MODULE.MANAGED_FILES, "architecture/system.yaml"),
        ):
            with self.assertRaises(MODULE.UnsafeInstallTarget):
                MODULE.build_payload(ROOT)
        with patch.object(
            MODULE,
            "MANAGED_FILES",
            (*MODULE.MANAGED_FILES, MODULE.MANAGED_FILES[0]),
        ):
            with self.assertRaises(MODULE.UnsafeInstallTarget):
                MODULE.build_payload(ROOT)

    def test_materialize_new_publishes_verified_payload_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            target = parent / "target"
            plan = MODULE.plan_install(ROOT, target)
            old_umask = os.umask(0o077)
            try:
                with patch("subprocess.Popen", side_effect=AssertionError("dependency runner")):
                    result = MODULE.materialize_new(ROOT, target)
            finally:
                os.umask(old_umask)

            self.assertEqual(result, plan)
            self.assertEqual(result["target_state"], "absent")
            for item in result["entries"]:
                installed = target / item["path"]
                self.assertTrue(installed.is_file(), item["path"])
                self.assertEqual(installed.stat().st_size, item["size"])
                self.assertEqual(
                    hashlib.sha256(installed.read_bytes()).hexdigest(), item["sha256"]
                )
                self.assertEqual(stat.S_IMODE(installed.stat().st_mode), item["mode"])
            for relative in (
                "engineering/changes",
                "engineering/adr",
                "engineering/runbooks",
                "engineering/reviews",
                "engineering/contracts/openapi",
                "engineering/contracts/asyncapi",
                "engineering/contracts/schemas",
            ):
                self.assertTrue((target / relative).is_dir(), relative)
            for authority in (
                "architecture/adoption.json",
                "architecture/rules.yaml",
                "architecture/system.yaml",
            ):
                self.assertFalse((target / authority).exists(), authority)
            self.assertEqual(_stage_names(parent), [])
            result = subprocess.run(
                ["python3", "scripts/grok_architecture.py", "--help"],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_materialize_new_rejects_existing_symlink_and_special_targets(self) -> None:
        for kind in ("directory", "symlink", "fifo"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                parent = Path(tmp)
                target = parent / "target"
                outside = parent / "outside"
                outside.mkdir()
                sentinel = outside / "sentinel.txt"
                sentinel.write_bytes(b"outside unchanged\n")
                if kind == "directory":
                    target.mkdir()
                    (target / "owned.txt").write_bytes(b"existing\n")
                elif kind == "symlink":
                    target.symlink_to(outside, target_is_directory=True)
                else:
                    os.mkfifo(target)
                before = _snapshot(target)
                with self.assertRaises(MODULE.UnsafeInstallTarget):
                    MODULE.materialize_new(ROOT, target)
                self.assertEqual(_snapshot(target), before)
                self.assertEqual(sentinel.read_bytes(), b"outside unchanged\n")
                self.assertEqual(_stage_names(parent), [])

    def test_materialize_new_loses_target_creation_race_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            target = parent / "target"
            real_rename = MODULE._rename_noreplace

            def create_target(parent_fd: int, stage_name: str, target_name: str) -> None:
                os.mkdir(target_name, dir_fd=parent_fd)
                target_fd = os.open(
                    target_name,
                    os.O_RDONLY | os.O_DIRECTORY,
                    dir_fd=parent_fd,
                )
                try:
                    descriptor = os.open(
                        "winner.txt",
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o600,
                        dir_fd=target_fd,
                    )
                    try:
                        os.write(descriptor, b"winner\n")
                    finally:
                        os.close(descriptor)
                finally:
                    os.close(target_fd)
                real_rename(parent_fd, stage_name, target_name)

            with patch.object(MODULE, "_rename_noreplace", side_effect=create_target):
                with self.assertRaises(MODULE.UnsafeInstallTarget):
                    MODULE.materialize_new(ROOT, target)
            self.assertEqual((target / "winner.txt").read_bytes(), b"winner\n")
            self.assertEqual(_stage_names(parent), [])

    def test_materialize_new_failure_injections_clean_owned_stage(self) -> None:
        injections = (
            ("write", "_write_all", OSError("write failed")),
            ("manifest", "_verify_stage", MODULE.UnsafeInstallTarget("bad manifest")),
            ("publication", "_rename_noreplace", OSError("publish failed")),
        )
        for label, attribute, failure in injections:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                parent = Path(tmp)
                target = parent / "target"
                sentinel = parent / "outside.txt"
                sentinel.write_bytes(b"outside unchanged\n")
                with patch.object(MODULE, attribute, side_effect=failure):
                    with self.assertRaises((OSError, MODULE.UnsafeInstallTarget)):
                        MODULE.materialize_new(ROOT, target)
                self.assertFalse(os.path.lexists(target))
                self.assertEqual(sentinel.read_bytes(), b"outside unchanged\n")
                self.assertEqual(_stage_names(parent), [])

    def test_materialize_new_fsync_failure_cleans_owned_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            target = parent / "target"
            with patch.object(MODULE.os, "fsync", side_effect=OSError("fsync failed")):
                with self.assertRaises(OSError):
                    MODULE.materialize_new(ROOT, target)
            self.assertFalse(os.path.lexists(target))
            self.assertEqual(_stage_names(parent), [])

    def test_materialize_new_parent_relocation_does_not_touch_outside_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "parent"
            parent.mkdir()
            target = parent / "target"
            sentinel = parent / "outside.txt"
            sentinel.write_bytes(b"outside unchanged\n")
            relocated = root / "relocated"

            def relocate_parent(*_args) -> None:
                parent.rename(relocated)
                parent.mkdir()
                raise MODULE.UnsafeInstallTarget("parent relocated")

            with patch.object(MODULE, "_rename_noreplace", side_effect=relocate_parent):
                with self.assertRaises(MODULE.UnsafeInstallTarget):
                    MODULE.materialize_new(ROOT, target)
            self.assertEqual((relocated / "outside.txt").read_bytes(), b"outside unchanged\n")
            self.assertEqual(_stage_names(relocated), [])
            self.assertEqual(_stage_names(parent), [])
            self.assertFalse(os.path.lexists(target))

    def test_cli_modes_plan_by_default_and_materialize_only_when_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "existing"
            existing.mkdir()
            sentinel = existing / "sentinel.txt"
            sentinel.write_bytes(b"unchanged\n")
            before = _snapshot(existing)
            default = subprocess.run(
                ["python3", "scripts/install_into.py", str(existing)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            explicit = subprocess.run(
                ["python3", "scripts/install_into.py", "--plan", str(existing)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            target = root / "new"
            materialized = subprocess.run(
                ["python3", "scripts/install_into.py", "--materialize-new", str(target)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
            self.assertEqual(explicit.returncode, 0, explicit.stdout + explicit.stderr)
            self.assertEqual(materialized.returncode, 0, materialized.stdout + materialized.stderr)
            self.assertIn("read-only plan", default.stdout.lower())
            self.assertEqual(_snapshot(existing), before)
            self.assertTrue((target / "scripts/grok_verify.py").is_file())
            self.assertFalse((target / ".github/workflows").exists())

    def test_with_ci_remains_forbidden_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.mkdir()
            before = _snapshot(target)
            with self.assertRaises(SystemExit) as raised:
                MODULE.install(
                    ROOT,
                    target,
                    force=False,
                    dry_run=False,
                    with_ci=True,
                )
            self.assertIn("forbidden", str(raised.exception).lower())
            self.assertEqual(_snapshot(target), before)


if __name__ == "__main__":
    unittest.main()
