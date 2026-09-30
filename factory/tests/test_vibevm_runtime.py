import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
import zipfile

from adaptive_factory.vibevm_runtime import VibeVMError, VibeVMStore, reconcile_boot_block


def archive(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as output:
        for name, content in files.items():
            output.writestr(name, content)
    return stream.getvalue()


def package(name, version, payload, *, dependencies=None, origin="registry.example"):
    return {
        "name": name,
        "version": version,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "origin": origin,
        "dependencies": dependencies or {},
        "qualified": True,
        "revoked": False,
    }


class VibeVMRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = VibeVMStore(self.root, tenant_id="tenant-a", repository_id="owner/project",
                                 allowed_origins={"registry.example"})

    def tearDown(self):
        self.temp.cleanup()

    def assert_code(self, code, operation):
        with self.assertRaises(VibeVMError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def test_resolver_rejects_cycle_constraint_and_ambiguous_override_without_partial_lock(self):
        a_bytes = archive({"a.md": "A"}); b_bytes = archive({"b.md": "B"})
        a = package("a", "1.0.0", a_bytes, dependencies={"b": "1.0.0"})
        b = package("b", "1.0.0", b_bytes, dependencies={"a": "1.0.0"})
        self.assert_code("dependency_cycle:a->b->a", lambda: self.store.resolve([a, b]))
        b["dependencies"] = {}; a["dependencies"] = {"b": "2.0.0"}
        self.assert_code("version_conflict:a->b:2.0.0!=1.0.0", lambda: self.store.resolve([a, b]))
        self.assert_code("ambiguous_override:b", lambda: self.store.resolve([a, b], overrides=["b", "b"]))
        self.assertFalse((self.root / "tenants" / "tenant-a" / "repositories" / "owner_project" / "active").exists())

    def test_immutable_admission_detects_changed_bytes_origin_revocation_and_offline_missing(self):
        payload = archive({"rules/a.md": "canonical"}); item = package("rules", "1.0.0", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        replay = self.store.replay(lock)
        self.assertEqual(replay["rules@1.0.0"], payload)
        object_path = self.store.object_path(item["sha256"])
        object_path.chmod(0o600)
        object_path.write_bytes(b"poison")
        self.assert_code("digest_mismatch:rules@1.0.0", lambda: self.store.replay(lock))
        object_path.write_bytes(payload)
        object_path.chmod(0o400)
        denied = {**item, "origin": "mirror.invalid"}
        self.assert_code("origin_not_allowed:mirror.invalid", lambda: self.store.admit(denied, payload))
        revoked = {**item, "revoked": True}
        self.assert_code("package_revoked:rules@1.0.0", lambda: self.store.admit(revoked, payload))
        object_path.unlink()
        self.assert_code("missing_package:rules@1.0.0", lambda: self.store.replay(lock))

    def test_lock_tampering_and_credential_bearing_configuration_fail_closed(self):
        payload = archive({"rules/a.md": "canonical"}); item = package("rules", "1.0.0", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        tampered = json.loads(json.dumps(lock)); tampered["packages"][0]["version"] = "latest"
        self.assert_code("lock_digest_mismatch", lambda: self.store.replay(tampered))
        tampered = json.loads(json.dumps(lock)); tampered["overrides"] = ["rules"]
        self.assert_code("lock_digest_mismatch", lambda: self.store.replay(tampered))
        self.assert_code("unsafe_configuration", lambda: self.store.publish(
            lock, boot_owner_text="owner\n", boot_block="block", bindings=[],
            configuration={"backend": "native", "registry_url": "https://user:secret@example.invalid"}))

    def test_managed_boot_block_is_idempotent_and_conflicts_fail_before_owner_text_changes(self):
        original = "# Owner instructions\nKeep this byte-for-byte.\n"
        once = reconcile_boot_block(original, "read AGENTS then contracts")
        self.assertEqual(reconcile_boot_block(once, "read AGENTS then contracts"), once)
        self.assertTrue(once.startswith(original))
        updated = reconcile_boot_block(once, "read AGENTS then selected sources")
        self.assertTrue(updated.startswith(original))
        damaged = once.replace("<!-- /adaptive-vibevm -->", "")
        self.assert_code("boot_block_corrupt", lambda: reconcile_boot_block(damaged, "new"))
        duplicated = once + once[len(original):]
        self.assert_code("boot_block_conflict", lambda: reconcile_boot_block(duplicated, "new"))

    def test_semantic_generation_ignores_observation_time_but_binds_backend_flags_and_local_digest(self):
        payload = archive({"rules/a.md": "canonical"}); item = package("rules", "1.0.0", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        base = {"backend": "native", "flags": {"dialect": "markdown"}, "local_digest": "1" * 64,
                "conditions": {"mandatory": "unknown"}}
        first = self.store.semantic_identity(lock, base, observed_at="2026-09-30T10:00:00Z")
        second = self.store.semantic_identity(lock, base, observed_at="2026-09-30T11:00:00Z")
        self.assertEqual(first, second)
        self.assertNotEqual(first, self.store.semantic_identity(lock, {**base, "backend": "vibevm"}))
        self.assertNotEqual(first, self.store.semantic_identity(lock, {**base, "local_digest": "2" * 64}))
        self.assert_code("mandatory_condition_unknown", lambda: self.store.publish(
            lock, boot_owner_text="owner\n", boot_block="block", bindings=[], configuration=base))

    def test_projection_rejects_traversal_symlink_hook_and_bounds_without_writing_active_generation(self):
        cases = {
            "path_escape": archive({"../escape": "x"}),
            "lifecycle_hook_forbidden": archive({"hooks/install.sh": "echo bad"}),
            "file_count_exceeded": archive({"a": "1", "b": "2"}),
        }
        for expected, payload in cases.items():
            with self.subTest(expected=expected):
                store = VibeVMStore(self.root / expected, tenant_id="tenant-a", repository_id="owner/project",
                                    allowed_origins={"registry.example"}, max_files=1)
                item = package("rules", "1.0.0", payload); lock = store.resolve([item]); store.admit(item, payload)
                self.assert_code(expected, lambda: store.publish(lock, boot_owner_text="owner\n",
                                 boot_block="block", bindings=[], configuration={"backend": "native"}))
                self.assertIsNone(store.active_generation())
        symlink_bytes = io.BytesIO()
        with zipfile.ZipFile(symlink_bytes, "w") as output:
            member = zipfile.ZipInfo("escape-link"); member.external_attr = 0o120777 << 16
            output.writestr(member, "../outside")
        payload = symlink_bytes.getvalue(); item = package("link", "1.0.0", payload)
        store = VibeVMStore(self.root / "links", tenant_id="tenant-a", repository_id="owner/project",
                            allowed_origins={"registry.example"})
        lock = store.resolve([item]); store.admit(item, payload)
        self.assert_code("non_regular_member:escape-link", lambda: store.publish(
            lock, boot_owner_text="owner\n", boot_block="block", bindings=[], configuration={"backend": "native"}))

    def test_bindings_remain_mapped_and_native_export_preserves_canonical_facts(self):
        payload = archive({"rules/a.md": "canonical"}); item = package("rules", "1.0.0", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        bindings = [{"criterion_id": "AC-001", "rule_id": "RULE-1", "revision": "7",
                     "source_digest": hashlib.sha256(b"canonical").hexdigest(), "status": "mapped"}]
        snapshot = self.store.publish(lock, boot_owner_text="owner\n", boot_block="block",
                                      bindings=bindings, configuration={"backend": "native"})
        exported = self.store.export_native(snapshot.generation_id)
        self.assertEqual(exported["bindings"], bindings)
        self.assertEqual(exported["sources"][0]["content"], "canonical")
        self.assertNotIn("executed", json.dumps(exported))
        bad = [{**bindings[0], "source_digest": "0" * 64}]
        self.assert_code("binding_source_missing:RULE-1", lambda: self.store.publish(
            lock, boot_owner_text="owner\n", boot_block="block", bindings=bad,
            configuration={"backend": "native"}))

    def test_atomic_compare_and_swap_crash_recovery_frozen_snapshot_and_qualified_rollback(self):
        first_payload = archive({"rules/a.md": "one"}); first_item = package("rules", "1", first_payload)
        first_lock = self.store.resolve([first_item]); self.store.admit(first_item, first_payload)
        first = self.store.publish(first_lock, boot_owner_text="owner\n", boot_block="one", bindings=[],
                                   configuration={"backend": "native"})
        frozen = self.store.open_snapshot(first.generation_id)
        second_payload = archive({"rules/a.md": "two"}); second_item = package("rules", "2", second_payload)
        second_lock = self.store.resolve([second_item]); self.store.admit(second_item, second_payload)
        self.assert_code("simulated_crash", lambda: self.store.publish(second_lock, boot_owner_text="owner\n",
                         boot_block="two", bindings=[], configuration={"backend": "native"},
                         expected_active=first.generation_id, crash_before_switch=True))
        self.assertEqual(self.store.active_generation(), first.generation_id)
        second = self.store.publish(second_lock, boot_owner_text="owner\n", boot_block="two", bindings=[],
                                    configuration={"backend": "native"}, expected_active=first.generation_id)
        self.assertEqual(self.store.active_generation(), second.generation_id)
        self.assertEqual(frozen.native_export["sources"][0]["content"], "one")
        self.assert_code("generation_conflict", lambda: self.store.publish(first_lock,
                         boot_owner_text="owner\n", boot_block="one", bindings=[],
                         configuration={"backend": "native"}, expected_active=first.generation_id))
        self.store.set_generation_status(first.generation_id, qualified=False)
        self.assert_code("rollback_target_unqualified", lambda: self.store.rollback(first.generation_id))
        self.store.set_generation_status(first.generation_id, qualified=True)
        self.store.rollback(first.generation_id)
        self.assertEqual(self.store.active_generation(), first.generation_id)

    def test_generation_identity_binds_boot_and_bindings_and_ids_cannot_escape_store(self):
        payload = archive({"rules/a.md": "canonical"}); item = package("rules", "1", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        binding = [{"criterion_id": "AC-1", "rule_id": "RULE-1", "revision": "1",
                    "source_digest": hashlib.sha256(b"canonical").hexdigest(), "status": "mapped"}]
        first = self.store.publish(lock, boot_owner_text="owner\n", boot_block="one", bindings=binding,
                                   configuration={"backend": "native"})
        second = self.store.publish(lock, boot_owner_text="owner\n", boot_block="two", bindings=binding,
                                    configuration={"backend": "native"}, expected_active=first.generation_id)
        self.assertNotEqual(first.generation_id, second.generation_id)
        for operation in (self.store.export_native, self.store.open_snapshot, self.store.rollback,
                          lambda value: self.store.set_generation_status(value, qualified=True)):
            self.assert_code("invalid_generation_id", lambda operation=operation: operation("../active"))

    def test_scope_encoding_has_no_repository_alias_and_concurrent_publish_has_single_winner(self):
        one = VibeVMStore(self.root, tenant_id="tenant", repository_id="a/b", allowed_origins={"registry.example"})
        two = VibeVMStore(self.root, tenant_id="tenant", repository_id="a_b", allowed_origins={"registry.example"})
        self.assertNotEqual(one.root, two.root)
        payload = archive({"rules/a.md": "canonical"}); item = package("rules", "1", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        base = self.store.publish(lock, boot_owner_text="owner\n", boot_block="base", bindings=[],
                                  configuration={"backend": "native"})
        outcomes = []
        barrier = threading.Barrier(2)
        def publish(block):
            barrier.wait()
            try:
                outcomes.append(self.store.publish(lock, boot_owner_text="owner\n", boot_block=block,
                    bindings=[], configuration={"backend": "native"}, expected_active=base.generation_id).generation_id)
            except VibeVMError as error:
                outcomes.append(error.code)
        threads = [threading.Thread(target=publish, args=(value,)) for value in ("left", "right")]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sum(value == "generation_conflict" for value in outcomes), 1)
        self.assertIn(self.store.active_generation(), outcomes)

    def test_hostile_archives_are_rejected_and_interrupted_candidate_is_retained_for_audit(self):
        hostile = {
            "invalid_archive:rules@1": b"not-a-zip",
            "path_escape": archive({"/absolute": "x"}),
            "path_depth_exceeded": archive({"a/b/c/d": "x"}),
            "expanded_size_exceeded": archive({"large": "x" * 9}),
            "duplicate_member:dup": self._duplicate_archive(),
            "xml_external_entity_forbidden:rules.xml": archive({"rules.xml": '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>'}),
        }
        for expected, payload in hostile.items():
            with self.subTest(expected=expected):
                byte_limit = 1024 if expected.startswith("xml_external") else 8
                store = VibeVMStore(self.root / expected.replace("/", "_"), tenant_id="tenant", repository_id="repo",
                                    allowed_origins={"registry.example"}, max_depth=3, max_bytes=byte_limit)
                item = package("rules", "1", payload); lock = store.resolve([item]); store.admit(item, payload)
                self.assert_code(expected, lambda: store.publish(lock, boot_owner_text="owner\n", boot_block="x",
                                 bindings=[], configuration={"backend": "native"}))
        payload = archive({"a": "x"}); item = package("audit", "1", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        identity = self.store.generation_identity(lock, {"backend": "native"}, "owner\n", "x", [])
        self.assert_code("simulated_crash", lambda: self.store.publish(lock, boot_owner_text="owner\n", boot_block="x",
                         bindings=[], configuration={"backend": "native"}, crash_before_switch=True))
        self.assertTrue((self.store.generations / identity / "native-export.json").is_file())

    @staticmethod
    def _duplicate_archive():
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as output:
            output.writestr("dup", "one"); output.writestr("dup", "two")
        return stream.getvalue()

    def test_fallback_rechecks_generation_status_and_safety(self):
        payload = archive({"a": "x"}); item = package("rules", "1", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        snapshot = self.store.publish(lock, boot_owner_text="owner\n", boot_block="x", bindings=[],
            configuration={"backend": "native", "safety_known": True, "mandatory_rules_complete": True})
        self.store.set_generation_status(snapshot.generation_id, qualified=False)
        self.assert_code("fallback_target_unqualified", lambda: self.store.native_fallback(snapshot.generation_id, adapter_available=False))
        self.store.set_generation_status(snapshot.generation_id, qualified=True, revoked=True)
        self.assert_code("fallback_target_revoked", lambda: self.store.native_fallback(snapshot.generation_id, adapter_available=False))
        self.store.set_generation_status(snapshot.generation_id, qualified=True, revoked=False)
        status = self.store.generations / snapshot.generation_id / "status.json"
        value = json.loads(status.read_text()); value["safety_known"] = False; status.write_text(json.dumps(value))
        self.assert_code("fallback_safety_unknown", lambda: self.store.native_fallback(snapshot.generation_id, adapter_available=False))
        value["safety_known"] = True; value["mandatory_rules_complete"] = False; status.write_text(json.dumps(value))
        self.assert_code("fallback_mandatory_rules_missing", lambda: self.store.native_fallback(snapshot.generation_id, adapter_available=False))

    def test_revoke_racing_rollback_never_leaves_revoked_generation_active(self):
        payload = archive({"a": "x"}); item = package("rules", "1", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        target = self.store.publish(lock, boot_owner_text="owner\n", boot_block="x", bindings=[],
                                    configuration={"backend": "native"})
        barrier = threading.Barrier(2); outcomes = []
        def revoke():
            barrier.wait(); self.store.set_generation_status(target.generation_id, qualified=True, revoked=True)
        def rollback():
            barrier.wait()
            try: self.store.rollback(target.generation_id); outcomes.append("rolled_back")
            except VibeVMError as error: outcomes.append(error.code)
        threads = [threading.Thread(target=revoke), threading.Thread(target=rollback)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertIsNone(self.store.active_generation())
        self.assertIn(outcomes[0], {"rolled_back", "rollback_target_revoked"})

    def test_killed_publisher_keeps_active_generation_and_recovery_removes_partial_stage(self):
        payload = archive({"a": "x"}); item = package("rules", "1", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        active = self.store.publish(lock, boot_owner_text="owner\n", boot_block="base", bindings=[],
                                    configuration={"backend": "native"})
        marker = self.root / "projection-started"
        context = multiprocessing.get_context("fork")
        process = context.Process(target=self._paused_publish,
                                  args=(self.store, lock, active.generation_id, marker))
        process.start()
        for _ in range(100):
            if marker.exists(): break
            time.sleep(0.01)
        self.assertTrue(marker.exists())
        os.kill(process.pid, 9); process.join(5)
        self.assertEqual(self.store.active_generation(), active.generation_id)
        self.assertGreaterEqual(self.store.recover(), 1)
        self.assertFalse(any(path.name.startswith(".generation-") for path in self.store.generations.iterdir()))

    @staticmethod
    def _paused_publish(store, lock, expected, marker):
        original = store._project
        def paused(*args):
            original(*args); marker.write_text("ready"); time.sleep(30)
        store._project = paused
        store.publish(lock, boot_owner_text="owner\n", boot_block="candidate", bindings=[],
                      configuration={"backend": "native"}, expected_active=expected)
    def test_cache_is_tenant_scoped_and_native_core_fallback_does_not_switch_attempt(self):
        payload = archive({"rules/a.md": "canonical"}); item = package("rules", "1", payload)
        lock = self.store.resolve([item]); self.store.admit(item, payload)
        snapshot = self.store.publish(lock, boot_owner_text="owner\n", boot_block="block", bindings=[],
                                      configuration={"backend": "native"})
        other = VibeVMStore(self.root, tenant_id="tenant-b", repository_id="owner/project",
                            allowed_origins={"registry.example"})
        self.assert_code("missing_package:rules@1", lambda: other.replay(lock))
        object_path = self.store.object_path(item["sha256"]); object_path.chmod(0o600)
        object_path.write_bytes(b"poison")
        self.assertEqual(snapshot.native_export["sources"][0]["content"], "canonical")
        fallback = self.store.native_fallback(snapshot.generation_id, adapter_available=False)
        self.assertEqual(fallback["generation_id"], snapshot.generation_id)
        self.assertEqual(self.store.active_generation(), snapshot.generation_id)


if __name__ == "__main__":
    unittest.main()
