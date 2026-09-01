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
        for expected in (
            ".grok-stack/adaptive_grok/governance.py",
            ".grok-stack/templates/change/architecture.md",
            ".grok-stack/templates/change/requirements.md",
            "scripts/grok_governance.py",
            "schemas/canonical-example.schema.json",
            "schemas/debt-entry.schema.json",
            "schemas/governance-handoff-v1.schema.json",
            "schemas/governance-rule.schema.json",
            "factory/README.md",
            "factory/compose.yaml",
            "factory/contracts/openapi/factory-control.v1.json",
            "factory/pyproject.toml",
            "factory/uv.lock",
            "factory/src/adaptive_factory/store.py",
            "factory/src/adaptive_factory/admin.py",
            "factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql",
            "factory/src/adaptive_factory/resources/008_allocation_release_authority.sql",
            "factory/src/adaptive_factory/resources/009_authority_audit_and_history_indexes.sql",
            "factory/src/adaptive_factory/resources/010_authority_accounting_and_cleanup.sql",
            "factory/tests/run_disposable_exit.py",
            "factory/tests/postgres_restart_probe.py",
            "factory/tests/test_postgres_integration.py",
        ):
            self.assertIn(expected, generic_paths)
        self.assertEqual(
            {path for path in generic_paths if path.startswith("factory/tests/")},
            {
                "factory/tests/__init__.py",
                "factory/tests/postgres_restart_probe.py",
                "factory/tests/run_disposable_exit.py",
                "factory/tests/test_api.py",
                "factory/tests/test_contracts.py",
                "factory/tests/test_migrations.py",
                "factory/tests/test_postgres_integration.py",
                "factory/tests/test_server.py",
                "factory/tests/test_service.py",
                "factory/tests/test_state.py",
            },
        )
        self.assertFalse(any("__pycache__" in path for path in generic_paths))
        self.assertFalse(set(MODULE.TARGET_OWNED_GOVERNANCE) & set(generic_paths))
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
            (*MODULE.MANAGED_FILES, "governance/rules/index.json"),
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
                "governance/rules/index.json",
                "governance/debt/index.json",
                "governance/canonical-examples/index.json",
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

    def test_materialize_new_rejects_ancestor_swaps_during_parent_binding(self) -> None:
        for boundary in ("intermediate ancestor", "final parent"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                anchor = root / "anchor"
                container = anchor / "container"
                parent = container / "parent"
                parent.mkdir(parents=True)
                outside_container = root / "outside-container"
                outside_parent = outside_container / "parent"
                outside_parent.mkdir(parents=True)
                outside_sentinel = outside_parent / "sentinel.txt"
                outside_sentinel.write_bytes(b"outside unchanged\n")
                relocated = root / "relocated"
                target = parent / "target"
                real_open = os.open
                swapped = False

                def swap_before_open(path, flags, *args, **kwargs):
                    nonlocal swapped
                    component = os.fsdecode(path)
                    old_full_parent_open = Path(component) == parent
                    if not swapped and (
                        old_full_parent_open
                        or boundary == "intermediate ancestor"
                        and component == "container"
                        or boundary == "final parent"
                        and component == "parent"
                    ):
                        swapped = True
                        if boundary == "intermediate ancestor":
                            container.rename(relocated)
                            container.symlink_to(
                                outside_container,
                                target_is_directory=True,
                            )
                        else:
                            parent.rename(relocated)
                            parent.symlink_to(outside_parent, target_is_directory=True)
                    return real_open(path, flags, *args, **kwargs)

                with patch.object(MODULE.os, "open", side_effect=swap_before_open):
                    with self.assertRaises(MODULE.UnsafeInstallTarget):
                        MODULE.materialize_new(ROOT, target)
                self.assertTrue(swapped)
                self.assertEqual(outside_sentinel.read_bytes(), b"outside unchanged\n")
                self.assertFalse((outside_parent / "target").exists())
                self.assertEqual(_stage_names(outside_parent), [])
                self.assertEqual(_stage_names(relocated), [])

    def test_plan_rejects_symlinked_target_ancestry_without_mutation(self) -> None:
        for boundary in ("intermediate ancestor", "final parent"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                anchor = root / "anchor"
                anchor.mkdir()
                outside = root / "outside"
                outside.mkdir()
                if boundary == "intermediate ancestor":
                    (outside / "container").mkdir()
                    (anchor / "link").symlink_to(outside, target_is_directory=True)
                    target = anchor / "link/container/target"
                else:
                    (anchor / "parent").symlink_to(outside, target_is_directory=True)
                    target = anchor / "parent/target"
                before = _snapshot(outside)
                plan = MODULE.plan_install(ROOT, target)
                self.assertEqual(plan["target_state"], "unsafe")
                self.assertEqual(_snapshot(outside), before)
                self.assertEqual(_stage_names(anchor), [])

    def test_source_inventory_rejects_bound_root_or_managed_dir_relocation(self) -> None:
        for boundary in ("source root", "managed directory"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "source"
                managed = source / ".grok"
                managed.mkdir(parents=True)
                (source / "AGENTS.md").write_text("managed agents\n", encoding="utf-8")
                (managed / "required.md").write_text("required\n", encoding="utf-8")
                target = root / "target"
                relocated = root / "relocated"
                outside = root / "outside.txt"
                outside.write_bytes(b"outside unchanged\n")
                real_init = MODULE._SourceTree.__init__
                swapped = False

                def bind_then_relocate(tree, source_path):
                    nonlocal swapped
                    real_init(tree, source_path)
                    if swapped:
                        return
                    swapped = True
                    if boundary == "source root":
                        source.rename(relocated)
                        source.mkdir()
                        (source / ".grok").mkdir()
                    else:
                        managed.rename(relocated)
                        managed.mkdir()

                with (
                    patch.object(MODULE, "MANAGED_DIRS", (".grok",)),
                    patch.object(MODULE, "MANAGED_FILES", ()),
                    patch.object(MODULE._SourceTree, "__init__", bind_then_relocate),
                ):
                    with self.assertRaises(MODULE.UnsafeInstallTarget):
                        MODULE._materialize_new(
                            source,
                            target,
                            include_dependencies=False,
                            include_optional=False,
                        )
                self.assertTrue(swapped)
                self.assertFalse(os.path.lexists(target))
                self.assertEqual(_stage_names(root), [])
                self.assertEqual(outside.read_bytes(), b"outside unchanged\n")

    def test_source_reads_are_nofollow_and_bounded_at_the_descriptor(self) -> None:
        cases = ("managed", "agents", "bitrix", "toolchain")
        for family in cases:
            with self.subTest(family=family), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "source"
                source.mkdir()
                (source / "AGENTS.md").write_text("managed agents\n", encoding="utf-8")
                guidance = source / "docs/bitrix-local-AGENTS.md"
                guidance.parent.mkdir(parents=True)
                guidance.write_text("bitrix guidance\n", encoding="utf-8")
                payload = source / "payload.bin"
                payload.write_bytes(b"managed payload\n")
                toolchain = source / ".grok-stack/config/toolchain.json"
                toolchain.parent.mkdir(parents=True)
                toolchain.write_text('{"tools": []}\n', encoding="utf-8")
                victim = {
                    "managed": payload,
                    "agents": source / "AGENTS.md",
                    "bitrix": guidance,
                    "toolchain": toolchain,
                }[family]
                outside = root / "outside.bin"
                outside.write_bytes(
                    b'{"tools": [], "padding": "xxxxxxxxxxxxxxxxxxxxxxxx"}\n'
                    if family == "toolchain"
                    else b"x" * 34
                )
                saved = root / "saved-source"
                swapped = False
                path_bytes_read = 0
                real_open = os.open
                real_read_bytes = Path.read_bytes
                real_read_text = Path.read_text

                def swap() -> None:
                    nonlocal swapped
                    if swapped:
                        return
                    swapped = True
                    victim.rename(saved)
                    victim.symlink_to(outside)

                def race_descriptor_open(path, flags, *args, **kwargs):
                    parent_fd = kwargs.get("dir_fd")
                    if parent_fd is not None:
                        parent = Path(os.readlink(f"/proc/self/fd/{parent_fd}"))
                        if parent / os.fsdecode(path) == victim:
                            swap()
                    return real_open(path, flags, *args, **kwargs)

                def race_path_bytes(path: Path) -> bytes:
                    nonlocal path_bytes_read
                    if path == victim:
                        swap()
                        data = real_read_bytes(path)
                        path_bytes_read += len(data)
                        return data
                    return real_read_bytes(path)

                def race_path_text(path: Path, *args, **kwargs) -> str:
                    nonlocal path_bytes_read
                    if path == victim:
                        swap()
                        text = real_read_text(path, *args, **kwargs)
                        path_bytes_read += len(text.encode("utf-8"))
                        return text
                    return real_read_text(path, *args, **kwargs)

                managed_files = ("payload.bin",) if family == "managed" else ()
                if family == "toolchain":

                    def invocation() -> object:
                        return MODULE.plan_install(source, root / "target")

                else:

                    def invocation() -> object:
                        return MODULE.build_payload(
                            source,
                            profile_kind=(
                                "bitrix" if family == "bitrix" else "generic"
                            ),
                        )
                with (
                    patch.object(MODULE, "MANAGED_DIRS", ()),
                    patch.object(MODULE, "MANAGED_FILES", managed_files),
                    patch.object(MODULE, "MAX_SOURCE_FILE_BYTES", 32),
                    patch.object(MODULE, "MAX_TOOLCHAIN_BYTES", 32),
                    patch.object(MODULE.os, "open", side_effect=race_descriptor_open),
                    patch.object(Path, "read_bytes", race_path_bytes),
                    patch.object(Path, "read_text", race_path_text),
                ):
                    with self.assertRaises(MODULE.UnsafeInstallTarget):
                        invocation()
                self.assertTrue(swapped)
                self.assertLessEqual(path_bytes_read, 33)

    def test_known_owned_constructor_failures_remove_every_created_entry(self) -> None:
        for boundary in ("stage fstat", "directory fstat", "file fstat"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as tmp:
                parent = Path(tmp)
                target = parent / "target"
                sentinel = parent / "outside.txt"
                sentinel.write_bytes(b"outside unchanged\n")
                real_fstat = os.fstat
                injected = False

                def fail_fstat(descriptor):
                    nonlocal injected
                    metadata = real_fstat(descriptor)
                    resolved = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
                    stage_gap = (
                        boundary == "stage fstat"
                        and resolved.parent == parent
                        and resolved.name.startswith(".adaptive-install-")
                        and stat.S_ISDIR(metadata.st_mode)
                    )
                    directory_gap = (
                        boundary == "directory fstat"
                        and resolved.name == "engineering"
                        and resolved.parent.name.startswith(".adaptive-install-")
                        and stat.S_ISDIR(metadata.st_mode)
                    )
                    file_gap = (
                        boundary == "file fstat"
                        and ".adaptive-install-" in resolved.as_posix()
                        and stat.S_ISREG(metadata.st_mode)
                    )
                    if (
                        not injected
                        and (stage_gap or directory_gap or file_gap)
                    ):
                        injected = True
                        raise OSError(f"injected {boundary}")
                    return metadata

                with patch.object(MODULE.os, "fstat", side_effect=fail_fstat):
                    with self.assertRaises((OSError, MODULE.UnsafeInstallTarget)):
                        MODULE.materialize_new(ROOT, target)
                self.assertTrue(injected)
                self.assertFalse(os.path.lexists(target))
                self.assertEqual(sentinel.read_bytes(), b"outside unchanged\n")
                self.assertEqual(_stage_names(parent), [])

    def test_constructor_gap_swaps_preserve_unproven_replacements(self) -> None:
        for boundary in ("stage", "nested directory", "file"):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as tmp:
                parent = Path(tmp)
                target = parent / "target"
                outside = parent / "outside.txt"
                outside.write_bytes(b"outside unchanged\n")
                real_open = os.open
                real_stat = os.stat
                real_fstat = os.fstat
                replacement: Path | None = None
                replacement_identity: tuple[int, int, int] | None = None
                original_file_identity: tuple[int, int] | None = None

                def swap_directory(path: Path) -> None:
                    nonlocal replacement, replacement_identity
                    original = path.with_name(f"{path.name}.original-owned")
                    path.rename(original)
                    path.mkdir(mode=0o711)
                    metadata = os.lstat(path)
                    replacement = path
                    replacement_identity = (
                        metadata.st_dev,
                        metadata.st_ino,
                        stat.S_IMODE(metadata.st_mode),
                    )

                def race_stat(path, *args, **kwargs):
                    name = os.fsdecode(path)
                    parent_fd = kwargs.get("dir_fd")
                    if parent_fd is not None and replacement is None:
                        directory_path = Path(os.readlink(f"/proc/self/fd/{parent_fd}"))
                        if (
                            boundary == "stage"
                            and name.startswith(".adaptive-install-")
                            and directory_path == parent
                        ) or (
                            boundary == "nested directory"
                            and name == "engineering"
                            and directory_path.name.startswith(".adaptive-install-")
                        ):
                            swap_directory(directory_path / name)
                            raise OSError(f"injected {boundary} identity failure")
                    return real_stat(path, *args, **kwargs)

                def race_open(path, flags, *args, **kwargs):
                    name = os.fsdecode(path)
                    parent_fd = kwargs.get("dir_fd")
                    if parent_fd is not None and replacement is None:
                        directory_path = Path(os.readlink(f"/proc/self/fd/{parent_fd}"))
                        if (
                            boundary == "stage"
                            and name.startswith(".adaptive-install-")
                            and directory_path == parent
                        ) or (
                            boundary == "nested directory"
                            and name == "engineering"
                            and directory_path.name.startswith(".adaptive-install-")
                        ):
                            swap_directory(directory_path / name)
                            raise OSError(f"injected {boundary} open failure")
                    return real_open(path, flags, *args, **kwargs)

                def race_fstat(descriptor):
                    nonlocal replacement, replacement_identity, original_file_identity
                    metadata = real_fstat(descriptor)
                    resolved = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
                    if (
                        boundary == "file"
                        and stat.S_ISREG(metadata.st_mode)
                        and ".adaptive-install-" in resolved.as_posix()
                    ):
                        identity = (metadata.st_dev, metadata.st_ino)
                        if original_file_identity is None:
                            original_file_identity = identity
                            original = resolved.with_name(
                                f"{resolved.name}.original-owned"
                            )
                            resolved.rename(original)
                            resolved.write_bytes(b"concurrent replacement\n")
                            resolved.chmod(0o640)
                            current = os.lstat(resolved)
                            replacement = resolved
                            replacement_identity = (
                                current.st_dev,
                                current.st_ino,
                                stat.S_IMODE(current.st_mode),
                            )
                        if identity == original_file_identity:
                            raise OSError("injected file identity failure")
                    return metadata

                with (
                    patch.object(MODULE.os, "stat", side_effect=race_stat),
                    patch.object(MODULE.os, "open", side_effect=race_open),
                    patch.object(MODULE.os, "fstat", side_effect=race_fstat),
                ):
                    with self.assertRaises(MODULE.UnsafeInstallTarget) as raised:
                        MODULE.materialize_new(ROOT, target)
                self.assertIsNotNone(replacement)
                self.assertIsNotNone(replacement_identity)
                assert replacement is not None
                self.assertTrue(os.path.lexists(replacement))
                current = os.lstat(replacement)
                self.assertEqual(
                    (
                        current.st_dev,
                        current.st_ino,
                        stat.S_IMODE(current.st_mode),
                    ),
                    replacement_identity,
                )
                if boundary == "file":
                    self.assertEqual(
                        replacement.read_bytes(),
                        b"concurrent replacement\n",
                    )
                self.assertIn("manual cleanup required", str(raised.exception))
                self.assertEqual(outside.read_bytes(), b"outside unchanged\n")
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
            self.assertEqual(default.stdout.count(MODULE.LEGACY_PLAN_NOTICE), 1)
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
