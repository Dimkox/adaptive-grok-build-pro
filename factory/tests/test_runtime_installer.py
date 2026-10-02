"""Factory installer safety contracts using real archives and private temporary roots."""

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


MODULE = Path(__file__).resolve().parents[1] / "runtime" / "setup_manager.py"
SPEC = importlib.util.spec_from_file_location("factory_setup_manager", MODULE)
setup = None
if MODULE.exists():
    setup = importlib.util.module_from_spec(SPEC)
    sys.modules[SPEC.name] = setup
    SPEC.loader.exec_module(setup)


class Runtime:
    """Injected service boundary; files, verification, state, and switches remain real."""

    def __init__(self):
        self.running = set()
        self.healthy = True
        self.available = True
        self.events = []
        self.text = "ready\npass" + "word=se" + "cret token: bearer-" + "secret\nAuthor" + "ization: Bearer private\n"

    def preflight(self, profile, timeout):
        return self.available and profile == "factory-python" and timeout <= 30

    def start(self, release, timeout):
        self.events.append(("start", release.name))
        self.running.add(release.name)

    def stop(self, release, timeout):
        self.events.append(("stop", release.name))
        self.running.discard(release.name)

    def health(self, release, timeout):
        self.events.append(("health", release.name))
        return self.healthy and release.name in self.running

    def status(self, release, timeout):
        return release.name in self.running

    def logs(self, release, lines, maximum_bytes, timeout):
        return self.text


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(setup, "Factory setup manager has not been implemented")
        self.temp = tempfile.TemporaryDirectory(prefix="factory-installer-")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "installation"
        self.runtime = Runtime()
        self.manager = setup.SetupManager(self.root, self.runtime)

    def package(self, version="1.0.0", schema=1, entries=None, manifest_edit=None):
        entries = entries or [("app/main.py", b"print('" + version.encode() + b"')\n", stat.S_IFREG | 0o644)]
        archive = self.parent / (version + ".zip")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for path, content, mode in entries:
                info = zipfile.ZipInfo(path)
                info.create_system = 3
                info.external_attr = mode << 16
                handle.writestr(info, content)
        manifest = {
            "schema_version": "factory-release/v1", "product_version": version,
            "profile": "factory-python", "data_schema": schema,
            "files": [{"path": path, "size": len(content),
                       "sha256": hashlib.sha256(content).hexdigest(),
                       "mode": stat.S_IMODE(mode)} for path, content, mode in entries],
        }
        if manifest_edit:
            manifest_edit(manifest)
        manifest_path = self.parent / (version + ".json")
        manifest_path.write_text(json.dumps(manifest))
        return dict(archive=archive, manifest=manifest_path,
                    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest())

    def install(self, version="1.0.0"):
        package = self.package(version)
        release = self.manager.install(**package)
        return release, package

    def evidence(self, candidate, current):
        backup = self.root / "backups" / "verified.snapshot"
        backup.write_bytes(b"retained operational snapshot")
        return setup.TransitionEvidence(
            root=str(self.root), prior=current, candidate=candidate,
            data_schema=1, backup=backup,
            backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
        )

    def test_install_switches_after_health_and_release_bytes_are_readonly(self):
        release, _ = self.install()
        self.assertEqual(os.readlink(self.root / "current"), "releases/" + release)
        self.assertEqual(self.manager.status()["current"], release)
        self.assertEqual(self.manager.status()["phase"], "ready")
        payload = self.root / "releases" / release / "app/main.py"
        self.assertEqual(payload.read_bytes(), b"print('1.0.0')\n")
        self.assertEqual(stat.S_IMODE(payload.stat().st_mode), 0o444)
        self.assertEqual(self.runtime.events[:2], [("start", release), ("health", release)])

    def test_tampered_archive_or_external_manifest_digest_has_zero_effects(self):
        for field in ("archive_sha256", "manifest_sha256"):
            with self.subTest(field=field):
                package = self.package()
                package[field] = "0" * 64
                with self.assertRaises(setup.InstallerError):
                    self.manager.install(**package)
                self.assertFalse(self.root.exists())
                self.assertEqual(self.runtime.events, [])

    def test_inventory_hash_missing_and_extra_files_are_rejected_before_mutation(self):
        edits = [lambda m: m["files"][0].update(sha256="0" * 64),
                 lambda m: m.update(files=[]),
                 lambda m: m["files"].append(dict(m["files"][0], path="absent.py"))]
        for edit in edits:
            with self.subTest(edit=edit):
                with self.assertRaises(setup.InstallerError):
                    self.manager.install(**self.package(manifest_edit=edit))
                self.assertFalse(self.root.exists())

    def test_traversal_alias_links_special_files_and_reserved_paths_are_rejected(self):
        cases = [("../escaped", stat.S_IFREG | 0o644),
                 ("/absolute", stat.S_IFREG | 0o644),
                 ("app/../escaped", stat.S_IFREG | 0o644),
                 ("app//main.py", stat.S_IFREG | 0o644),
                 ("app\\main.py", stat.S_IFREG | 0o644),
                 ("link", stat.S_IFLNK | 0o777), ("fifo", stat.S_IFIFO | 0o644),
                 (".factory-release.json", stat.S_IFREG | 0o644)]
        for path, mode in cases:
            with self.subTest(path=path):
                with self.assertRaises(setup.InstallerError):
                    self.manager.install(**self.package(entries=[(path, b"bad", mode)]))
                self.assertFalse(self.root.exists())

    def test_duplicate_archive_names_and_manifest_keys_are_rejected(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            package = self.package(entries=[("app.py", b"one", stat.S_IFREG | 0o644),
                                            ("app.py", b"two", stat.S_IFREG | 0o644)])
        with self.assertRaises(setup.InstallerError):
            self.manager.install(**package)
        package = self.package()
        content = package["manifest"].read_bytes().replace(b'"profile":', b'"profile":"factory-python","profile":')
        package["manifest"].write_bytes(content)
        package["manifest_sha256"] = hashlib.sha256(content).hexdigest()
        with self.assertRaises(setup.InstallerError):
            self.manager.install(**package)
        self.assertFalse(self.root.exists())

    def test_resource_limits_and_unsupported_profile_fail_readonly(self):
        for edit in (lambda m: m.update(profile="liqvera-compose"),
                     lambda m: m["files"][0].update(size=setup.MAX_FILE_BYTES + 1)):
            with self.assertRaises(setup.InstallerError):
                self.manager.install(**self.package(manifest_edit=edit))
            self.assertFalse(self.root.exists())
        with self.assertRaises(setup.InstallerError):
            setup.preflight(self.root, platform_name="Windows")
        with self.assertRaises(setup.InstallerError):
            setup.preflight(self.root, minimum_free_bytes=10**30)
        self.assertFalse(self.root.exists())

    def test_preflight_rejects_darwin_with_exact_unsupported_host_reason(self):
        with self.assertRaisesRegex(setup.InstallerError, "^UNSUPPORTED_HOST$"):
            setup.preflight(
                self.root,
                platform_name="Darwin",
                minimum_free_bytes=0,
                minimum_memory_bytes=0,
            )
        self.assertFalse(self.root.exists())

    def test_preflight_rejects_exact_home_root_by_explicit_home_guard(self):
        control = setup.preflight(
            self.root,
            platform_name="Linux",
            minimum_free_bytes=0,
            minimum_memory_bytes=0,
        )
        self.assertTrue(control["ready"])
        with patch.object(setup.Path, "home", return_value=self.root), patch.object(
            setup.Path, "cwd", return_value=self.parent / "controlled-cwd"
        ), self.assertRaisesRegex(setup.InstallerError, "^UNSAFE_ROOT$"):
            setup.preflight(
                self.root,
                platform_name="Linux",
                minimum_free_bytes=0,
                minimum_memory_bytes=0,
            )
        self.assertFalse(self.root.exists())

    def test_port_and_missing_adapter_fail_before_root_creation(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            with self.assertRaises(setup.InstallerError):
                setup.preflight(self.root, ports=[listener.getsockname()[1]])
        self.runtime.available = False
        with self.assertRaises(setup.InstallerError):
            self.manager.install(**self.package())
        self.assertFalse(self.root.exists())
        self.assertEqual(self.runtime.events, [])

    def test_unsafe_root_and_symlink_parent_or_managed_directory_are_rejected(self):
        for root in (Path("/"), self.parent / ".." / "escape"):
            with self.assertRaises(setup.InstallerError):
                setup.preflight(root)
        alias = self.parent / "alias"
        alias.symlink_to(self.parent, target_is_directory=True)
        with self.assertRaises(setup.InstallerError):
            setup.preflight(alias / "installation")
        self.install()
        config = self.root / "config"
        config.rmdir()
        config.symlink_to(self.parent, target_is_directory=True)
        with self.assertRaises(setup.InstallerError):
            self.manager.remove()
        self.assertEqual(self.runtime.events[-1][0], "health")

    def test_same_release_replay_is_idempotent_and_other_release_needs_update(self):
        first, package = self.install()
        events = list(self.runtime.events)
        self.assertEqual(self.manager.install(**package), first)
        self.assertEqual(self.runtime.events, events)
        with self.assertRaises(setup.InstallerError):
            self.manager.install(**self.package("2.0.0"))
        self.assertEqual(self.manager.status()["current"], first)

    def test_health_failure_leaves_current_unchanged_and_stops_candidate(self):
        self.runtime.healthy = False
        with self.assertRaises(setup.InstallerError):
            self.manager.install(**self.package())
        self.assertFalse((self.root / "current").exists())
        self.assertEqual(self.runtime.running, set())
        self.assertEqual(self.manager.status()["phase"], "failed")

    def test_update_without_backup_or_wrong_schema_never_starts_candidate(self):
        first, _ = self.install()
        package = self.package("2.0.0")
        with self.assertRaises(setup.InstallerError):
            self.manager.update(**package)
        release = setup.verify_release(**package).identity
        evidence = self.evidence(release, first)
        evidence.backup.write_bytes(b"changed")
        with self.assertRaises(setup.InstallerError):
            self.manager.update(**package, evidence=evidence)
        incompatible = self.package("3.0.0", schema=2)
        with self.assertRaises(setup.InstallerError):
            self.manager.update(**incompatible, evidence=self.evidence(setup.verify_release(**incompatible).identity, first))
        self.assertEqual(self.manager.status()["current"], first)
        self.assertEqual(len([e for e in self.runtime.events if e[0] == "start"]), 1)

    def test_update_and_reverse_require_exact_backup_binding(self):
        first, _ = self.install()
        package = self.package("2.0.0")
        second = setup.verify_release(**package).identity
        self.manager.update(**package, evidence=self.evidence(second, first))
        self.assertEqual(self.manager.status()["current"], second)
        self.assertEqual(self.manager.status()["previous"], first)
        with self.assertRaises(setup.InstallerError):
            self.manager.reverse(first)
        self.manager.reverse(first, evidence=self.evidence(first, second))
        self.assertEqual(self.manager.status()["current"], first)

    def test_update_health_failure_retains_prior_release_and_persistent_data(self):
        first, _ = self.install()
        data = self.root / "data" / "keep"
        data.write_text("persistent")
        package = self.package("2.0.0")
        second = setup.verify_release(**package).identity
        self.runtime.healthy = False
        with self.assertRaises(setup.InstallerError):
            self.manager.update(**package, evidence=self.evidence(second, first))
        self.assertEqual(os.readlink(self.root / "current"), "releases/" + first)
        self.assertEqual(data.read_text(), "persistent")
        self.assertNotIn(second, self.runtime.running)

    def test_release_tampering_is_rejected_before_runtime_start(self):
        release, _ = self.install()
        self.manager.stop()
        payload = self.root / "releases" / release / "app/main.py"
        payload.chmod(0o644)
        payload.write_text("tampered")
        before = list(self.runtime.events)
        with self.assertRaises(setup.InstallerError):
            self.manager.start()
        self.assertEqual(self.runtime.events, before)

    def test_status_absent_root_is_readonly_start_stop_are_idempotent(self):
        self.assertEqual(self.manager.status()["phase"], "absent")
        self.assertFalse(self.root.exists())
        release, _ = self.install()
        self.manager.start()
        self.manager.stop()
        self.manager.stop()
        self.assertEqual(self.runtime.events.count(("start", release)), 1)
        self.assertEqual(self.runtime.events.count(("stop", release)), 1)
        self.manager.start()
        self.assertEqual(self.runtime.events.count(("start", release)), 2)

    def test_status_reports_observed_runtime_without_changing_persisted_state(self):
        release, _ = self.install()
        before = (self.root / "state/install.json").read_bytes()
        self.runtime.running.discard(release)
        self.assertIs(self.manager.status()["running"], False)
        self.assertEqual((self.root / "state/install.json").read_bytes(), before)

    def test_logs_are_bounded_and_secret_lines_are_redacted(self):
        self.install()
        self.runtime.text += "x" * 10000
        result = self.manager.logs(lines=2, maximum_bytes=512)
        self.assertLessEqual(len(result.encode()), 512)
        self.assertNotIn("secret", result)
        self.assertNotIn("private", result)
        for kwargs in ({"lines": 0}, {"lines": 1001}, {"maximum_bytes": 65537}):
            with self.assertRaises(setup.InstallerError):
                self.manager.logs(**kwargs)

    def test_logs_redact_multiline_private_material_and_carriage_return_controls(self):
        self.install()
        self.runtime.text = (
            "ready\n-----BEGIN PRIVATE " + "KEY-----\nprivatebody\n-----END PRIVATE "
            + "KEY-----\npass" + "word=x\rhidden\n"
        )
        result = self.manager.logs()
        self.assertNotIn("privatebody", result)
        self.assertNotIn("hidden", result)
        self.assertNotIn("\r", result)

    def test_removal_preserves_data_config_backups_logs_and_is_idempotent(self):
        self.install()
        for folder in ("data", "config", "backups", "logs"):
            (self.root / folder / "keep").write_text(folder)
        self.manager.remove()
        self.manager.remove()
        self.assertEqual(self.manager.status()["phase"], "removed")
        self.assertFalse((self.root / "current").exists())
        for folder in ("data", "config", "backups", "logs"):
            self.assertEqual((self.root / folder / "keep").read_text(), folder)

    def test_purge_token_is_target_generation_bound_and_invalid_token_has_zero_effects(self):
        self.install()
        token = self.manager.purge_token()
        before = list(self.runtime.events)
        invalid_value = "purge-" + "anything"
        with self.assertRaises(setup.InstallerError):
            self.manager.remove(purge=True, token=invalid_value)
        self.assertEqual(self.runtime.events, before)
        self.manager.stop()
        with self.assertRaises(setup.InstallerError):
            self.manager.remove(purge=True, token=token)
        (self.root / "data" / "keep").write_text("erase only explicitly")
        self.manager.remove(purge=True, token=self.manager.purge_token())
        self.assertFalse((self.root / "data").exists())
        self.assertTrue((self.root / "state").is_dir())

    def test_lock_contention_prevents_service_and_state_effects(self):
        import fcntl
        self.install()
        before = list(self.runtime.events)
        with (self.root / "state/lock").open("rb") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(setup.InstallerError):
                self.manager.stop()
        self.assertEqual(self.runtime.events, before)

    def test_interrupted_operation_requires_reconciliation_without_restart(self):
        first, _ = self.install()
        state_path = self.root / "state/install.json"
        state = json.loads(state_path.read_text())
        state["phase"] = "starting"
        state["operation"] = {"id": "a" * 32, "candidate": first, "prior": first}
        state_path.write_text(json.dumps(state))
        with self.assertRaises(setup.InstallerError):
            self.manager.start()
        before = len([e for e in self.runtime.events if e[0] == "start"])
        self.manager.reconcile()
        self.assertEqual(len([e for e in self.runtime.events if e[0] == "start"]), before)
        self.assertEqual(self.manager.status()["current"], first)

    def test_pointer_escape_and_state_root_mismatch_fail_closed(self):
        self.install()
        pointer = self.root / "current"
        pointer.unlink()
        pointer.symlink_to(self.parent)
        with self.assertRaises(setup.InstallerError):
            self.manager.status()
        pointer.unlink()
        state_path = self.root / "state/install.json"
        state = json.loads(state_path.read_text())
        state["root"] = str(self.parent)
        state_path.write_text(json.dumps(state))
        with self.assertRaises(setup.InstallerError):
            self.manager.remove()

    def test_readonly_preflight_rejects_occupied_unowned_installation(self):
        self.root.mkdir(mode=0o700)
        (self.root / "foreign-file").write_text("belongs to operator")
        before = sorted(self.root.iterdir())
        with self.assertRaises(setup.InstallerError):
            setup.preflight(self.root)
        self.assertEqual(sorted(self.root.iterdir()), before)

    def test_hidden_metadata_and_empty_directory_tampering_cannot_evade_inventory(self):
        release, _ = self.install()
        self.manager.stop()
        path = self.root / "releases" / release
        path.chmod(0o755)
        extra = path / "undeclared"
        extra.mkdir(mode=0o555)
        with self.assertRaises(setup.InstallerError):
            self.manager.start()

    def test_start_journal_preserves_previous_release_identity(self):
        first, _ = self.install()
        package = self.package("2.0.0")
        second = setup.verify_release(**package).identity
        self.manager.update(**package, evidence=self.evidence(second, first))
        self.manager.stop()
        self.manager.start()
        self.assertEqual(self.manager.status()["previous"], first)

    def test_interruption_after_pointer_switch_reconciles_without_replaying_start(self):
        from unittest.mock import patch
        package = self.package()
        real_save = self.manager._save

        def crash_after_switch(state, phase, **fields):
            if phase == "switched":
                raise KeyboardInterrupt("simulated power loss")
            return real_save(state, phase, **fields)

        with patch.object(self.manager, "_save", side_effect=crash_after_switch):
            with self.assertRaises(KeyboardInterrupt):
                self.manager.install(**package)
        self.assertEqual(self.manager.status()["phase"], "healthy")
        count = len([event for event in self.runtime.events if event[0] == "start"])
        self.manager.reconcile()
        self.assertEqual(self.manager.status()["phase"], "ready")
        self.assertEqual(len([event for event in self.runtime.events if event[0] == "start"]), count)

    def test_interrupted_removal_reconciles_without_deleting_persistent_data(self):
        from unittest.mock import patch
        self.install()
        data = self.root / "data" / "keep"
        data.write_text("persistent")
        real_save = self.manager._save

        def crash_before_final_state(state, phase, **fields):
            if phase == "removed":
                raise KeyboardInterrupt("simulated power loss")
            return real_save(state, phase, **fields)

        with patch.object(self.manager, "_save", side_effect=crash_before_final_state):
            with self.assertRaises(KeyboardInterrupt):
                self.manager.remove()
        self.manager.reconcile()
        self.assertEqual(self.manager.status()["phase"], "removed")
        self.assertEqual(data.read_text(), "persistent")

    def test_purge_token_is_bound_to_installation_inode_and_inventory(self):
        self.install()
        token = self.manager.purge_token()
        (self.root / "data" / "new-target").write_text("appeared later")
        with self.assertRaises(setup.InstallerError):
            self.manager.remove(purge=True, token=token)
        self.assertTrue((self.root / "data/new-target").exists())

    def test_removed_installation_cannot_reinitialize_retained_data_schema(self):
        self.install()
        self.manager.remove()
        with self.assertRaises(setup.InstallerError):
            self.manager.install(**self.package("2.0.0", schema=2))
        self.assertEqual(self.manager.status()["data_schema"], 1)

    def test_initial_journal_crash_can_retry_only_the_pristine_partial_topology(self):
        from unittest.mock import patch
        package = self.package()
        original = setup._atomic_json

        def crash_initial_state(path, value):
            if path.name == "install.json":
                raise KeyboardInterrupt("power loss before initial journal")
            return original(path, value)

        with patch.object(setup, "_atomic_json", side_effect=crash_initial_state):
            with self.assertRaises(KeyboardInterrupt):
                self.manager.install(**package)
        self.assertTrue((self.root / "state").is_dir())
        self.assertFalse((self.root / "state/install.json").exists())
        before = self.root.stat().st_mtime_ns
        setup.preflight(self.root)
        self.assertEqual(self.root.stat().st_mtime_ns, before)
        identity = self.manager.install(**package)
        self.assertEqual(self.manager.status()["current"], identity)

    def test_partial_initialization_with_persistent_data_or_unknown_files_fails_closed(self):
        self.root.mkdir(mode=0o700)
        (self.root / "state").mkdir(mode=0o700)
        (self.root / "data").mkdir(mode=0o700)
        (self.root / "data/keep").write_text("real data, not pristine")
        with self.assertRaises(setup.InstallerError):
            self.manager.install(**self.package())
        self.assertEqual((self.root / "data/keep").read_text(), "real data, not pristine")
        self.assertFalse((self.root / "state/install.json").exists())
        self.assertEqual(self.runtime.events, [])

    def test_each_empty_initialization_prefix_can_reconcile_before_install(self):
        package = self.package()
        for count in range(len(setup.DIRECTORIES) + 1):
            with self.subTest(count=count):
                root = self.parent / ("partial-" + str(count))
                root.mkdir(mode=0o700)
                for name in setup.DIRECTORIES[:count]:
                    (root / name).mkdir(mode=0o700)
                manager = setup.SetupManager(root, self.runtime)
                manager.reconcile()
                self.assertEqual(manager.status()["phase"], "stopped")
                identity = manager.install(**package)
                self.assertEqual(manager.status()["current"], identity)

    def test_corrupt_retained_transition_record_blocks_further_effects(self):
        self.install()
        path = self.root / "state/install.json"
        state = json.loads(path.read_text())
        state["last_transition"]["health"] = False
        path.write_text(json.dumps(state))
        before = list(self.runtime.events)
        with self.assertRaises(setup.InstallerError):
            self.manager.stop()
        self.assertEqual(self.runtime.events, before)

    def test_missing_operation_identity_fails_as_closed_json_error(self):
        from contextlib import redirect_stdout
        self.install()
        path = self.root / "state/install.json"
        state = json.loads(path.read_text())
        state["operation"] = {"candidate": state["current"], "prior": state["current"]}
        path.write_text(json.dumps(state))
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(setup.main(["status", "--root", str(self.root)]), 1)
        self.assertEqual(json.loads(output.getvalue())["error"], "INVALID_STATE")

    def test_update_keeps_bounded_last_success_backup_compatibility_and_health_evidence(self):
        first, _ = self.install()
        package = self.package("2.0.0")
        second = setup.verify_release(**package).identity
        evidence = self.evidence(second, first)
        self.manager.update(**package, evidence=evidence)
        state = json.loads((self.root / "state/install.json").read_text())
        self.assertIsNone(state["operation"])
        retained = state["last_transition"]
        self.assertRegex(retained["id"], r"^[0-9a-f]{32}$")
        self.assertEqual(retained["prior"], first)
        self.assertEqual(retained["candidate"], second)
        self.assertEqual(retained["backup"], {"path": "backups/verified.snapshot", "sha256": evidence.backup_sha256})
        self.assertEqual(retained["compatibility"], "same-schema")
        self.assertIs(retained["health"], True)
        self.assertIs(retained["runtime_preflight"], True)
        self.assertEqual(retained["schema_prior"], 1)
        self.assertEqual(retained["schema_candidate"], 1)
        self.assertLess(len(json.dumps(retained)), 4096)
        self.manager.stop()
        self.manager.start()
        self.assertEqual(self.manager.status()["last_transition"], retained)

    def test_interrupted_update_reconciles_with_the_original_operation_and_backup_record(self):
        from unittest.mock import patch
        first, _ = self.install()
        package = self.package("2.0.0")
        second = setup.verify_release(**package).identity
        evidence = self.evidence(second, first)
        original = self.manager._save

        def crash_final_state(state, phase, **fields):
            if phase == "ready":
                raise KeyboardInterrupt("power loss before final success")
            return original(state, phase, **fields)

        with patch.object(self.manager, "_save", side_effect=crash_final_state):
            with self.assertRaises(KeyboardInterrupt):
                self.manager.update(**package, evidence=evidence)
        pending = self.manager.status()["operation"]
        self.manager.reconcile()
        retained = self.manager.status()["last_transition"]
        self.assertEqual(retained["id"], pending["id"])
        self.assertEqual(retained["backup"]["sha256"], evidence.backup_sha256)
        self.assertIs(retained["health"], True)

    def test_interrupted_purge_never_replays_deletion(self):
        from unittest.mock import patch
        self.install()
        (self.root / "data/keep").write_text("survives incomplete purge")
        token = self.manager.purge_token()
        with patch.object(setup.shutil, "rmtree", side_effect=KeyboardInterrupt("power loss during purge")):
            with self.assertRaises(KeyboardInterrupt):
                self.manager.remove(purge=True, token=token)
        self.assertEqual(self.manager.status()["phase"], "purging")
        with self.assertRaises(setup.InstallerError) as error:
            self.manager.reconcile()
        self.assertEqual(error.exception.code, "RECOVERY_REQUIRED")
        self.assertEqual((self.root / "data/keep").read_text(), "survives incomplete purge")

    def test_cli_update_and_reverse_have_no_implicit_adapter_or_backup_authority(self):
        from contextlib import redirect_stdout
        first, _ = self.install()
        package = self.package("2.0.0")
        arguments = ["--root", str(self.root), "--archive", str(package["archive"]),
                     "--manifest", str(package["manifest"]), "--archive-sha256", package["archive_sha256"],
                     "--manifest-sha256", package["manifest_sha256"]]
        before = (self.root / "state/install.json").read_bytes()
        for argv, expected in ((["update"] + arguments, "ADAPTER_REQUIRED"),
                               (["reverse", "--root", str(self.root), "--release", first], "BACKUP_COMPATIBILITY_REQUIRED")):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(setup.main(argv), 1)
            self.assertEqual(json.loads(output.getvalue())["error"], expected)
            self.assertEqual((self.root / "state/install.json").read_bytes(), before)

    def test_durable_provenance_pins_upstream_identity_and_explicit_authorization_scope(self):
        path = MODULE.with_name("setup_manager.provenance.json")
        self.assertTrue(path.is_file(), "durable provenance record is missing")
        record = json.loads(path.read_text())
        self.assertEqual(record["upstream_commit"], "e3df6833e8916d01f55028e63d4db1632a805a75")
        self.assertEqual(record["reference_sha256"], {
            "scripts/verify-liqvera-installer.py": "72e22cda1930d859be8093e3ec875ae5e673c842a41da849644147ae6b9fb207",
            "installer/lib/runtime.py": "8ffdc2be7c350fb1d529beeaa9de6326e9942bc9edf520ce194f87372de7a8f4",
            "installer/lib/lifecycle.py": "0fb33e0405f02784a871569a785f92e8d7acc2978c2effd400a507ce926d054b",
        })
        self.assertEqual(record["authorization"]["date"], "2026-09-30")
        self.assertEqual(record["authorization"]["authority"], "explicit-user-direction-recorded-by-coordinator")
        self.assertIn("Factory Linux setup manager", record["authorization"]["scope"])
        self.assertIs(record["upstream_open_license_claim"], False)

    def test_cli_status_and_error_are_json_and_cli_has_no_activation_adapter(self):
        from contextlib import redirect_stdout
        output = io.StringIO()
        with redirect_stdout(output):
            code = setup.main(["status", "--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["phase"], "absent")
        package = self.package()
        output = io.StringIO()
        argv = ["install", "--root", str(self.root), "--archive", str(package["archive"]),
                "--manifest", str(package["manifest"]), "--archive-sha256", package["archive_sha256"],
                "--manifest-sha256", package["manifest_sha256"]]
        with redirect_stdout(output):
            code = setup.main(argv)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["error"], "ADAPTER_REQUIRED")
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
