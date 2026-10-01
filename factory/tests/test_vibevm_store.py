import hashlib
import io
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
import zipfile

from adaptive_factory.vibevm_store import (
    UPSTREAM_ADAPTER_COMMIT,
    UPSTREAM_ADAPTER_TREE,
    VibeVMStore,
    VibeVMStoreError,
    reconcile_boot_block,
)


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


class VibeVMStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = VibeVMStore(
            self.root,
            tenant_id="tenant-a",
            repository_id="owner/project",
            allowed_origins={"registry.example"},
        )

    def tearDown(self):
        self.temp.cleanup()

    def assert_code(self, code, operation):
        with self.assertRaises(VibeVMStoreError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def test_provenance_is_exact_and_does_not_claim_adapter_execution(self):
        self.assertEqual(UPSTREAM_ADAPTER_COMMIT, "0b63caa86e80ff670dc2a62ff529079b91d08e4d")
        self.assertEqual(UPSTREAM_ADAPTER_TREE, "1ff4963aeea1f3f0a925485437b8dcf7130bf17d")
        self.assertNotIn("adapter", vars(self.store))

    def test_resolve_is_deterministic_and_rejects_invalid_graphs(self):
        a_bytes = archive({"a.md": "A"})
        b_bytes = archive({"b.md": "B"})
        a = package("a", "1", a_bytes, dependencies={"b": "1"})
        b = package("b", "1", b_bytes)
        lock = self.store.resolve([a, b])
        self.assertEqual([item["name"] for item in lock["packages"]], ["b", "a"])
        self.assertEqual(lock, self.store.resolve([b, a]))
        a["dependencies"] = {"b": "2"}
        self.assert_code("version_conflict:a->b:2!=1", lambda: self.store.resolve([a, b]))
        a["dependencies"] = {"b": "1"}
        b["dependencies"] = {"a": "1"}
        self.assert_code("dependency_cycle:a->b->a", lambda: self.store.resolve([a, b]))
        self.assert_code("ambiguous_override:b", lambda: self.store.resolve([a], overrides=["b", "b"]))

    def test_admit_and_replay_are_digest_origin_and_policy_bound(self):
        payload = archive({"rules/a.md": "canonical"})
        item = package("rules", "1", payload)
        lock = self.store.resolve([item])
        path = self.store.admit(item, payload)
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(self.store.replay(lock), {"rules@1": payload})
        self.assertEqual(self.store.admit(item, payload), path)
        self.assert_code("digest_mismatch:rules@1", lambda: self.store.admit(item, b"changed"))
        self.assert_code(
            "origin_not_allowed:mirror.invalid",
            lambda: self.store.admit({**item, "origin": "mirror.invalid"}, payload),
        )
        self.assert_code("package_revoked:rules@1", lambda: self.store.admit({**item, "revoked": True}, payload))
        path.chmod(0o600)
        path.write_bytes(b"poison")
        self.assert_code("digest_mismatch:rules@1", lambda: self.store.replay(lock))

    def test_replay_rejects_tampered_lock_and_is_tenant_scoped(self):
        payload = archive({"rules/a.md": "canonical"})
        item = package("rules", "1", payload)
        lock = self.store.resolve([item])
        self.store.admit(item, payload)
        tampered = {**lock, "overrides": ["rules"]}
        self.assert_code("lock_digest_mismatch", lambda: self.store.replay(tampered))
        other = VibeVMStore(
            self.root,
            tenant_id="tenant-b",
            repository_id="owner/project",
            allowed_origins={"registry.example"},
        )
        self.assert_code("missing_package:rules@1", lambda: other.replay(lock))
        alias = VibeVMStore(
            self.root,
            tenant_id="tenant-a",
            repository_id="owner_project",
            allowed_origins={"registry.example"},
        )
        self.assertNotEqual(self.store.root, alias.root)

    def test_projection_rejects_escape_symlink_hooks_xxe_and_resource_overflow(self):
        hostile = {
            "path_escape": archive({"../escape": "x"}),
            "lifecycle_hook_forbidden": archive({"hooks/install.sh": "bad"}),
            "xml_external_entity_forbidden:rule.xml": archive(
                {"rule.xml": '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>'}
            ),
            "expanded_size_exceeded": archive({"large": "123456789"}),
            "file_count_exceeded": archive({"a": "1", "b": "2"}),
        }
        symlink = io.BytesIO()
        with zipfile.ZipFile(symlink, "w") as output:
            member = zipfile.ZipInfo("link")
            member.external_attr = 0o120777 << 16
            output.writestr(member, "../outside")
        hostile["non_regular_member:link"] = symlink.getvalue()
        for expected, payload in hostile.items():
            with self.subTest(expected=expected):
                store = VibeVMStore(
                    self.root / expected.replace("/", "_"),
                    tenant_id="tenant",
                    repository_id="repo",
                    allowed_origins={"registry.example"},
                    max_files=1,
                    max_bytes=1024 if expected.startswith("xml_") else 8,
                )
                item = package("rules", "1", payload)
                lock = store.resolve([item])
                store.admit(item, payload)
                self.assert_code(expected, lambda: store.materialize(lock, "owner\n", "managed"))
                self.assertIsNone(store.active_generation())

    def test_materialize_is_atomic_idempotent_and_boot_reconciliation_preserves_owner_text(self):
        owner = "# Owner\nKeep this byte-for-byte.\n"
        once = reconcile_boot_block(owner, "managed")
        self.assertEqual(reconcile_boot_block(once, "managed"), once)
        self.assertTrue(once.startswith(owner))
        self.assert_code(
            "boot_block_corrupt",
            lambda: reconcile_boot_block(once.replace("<!-- /adaptive-vibevm -->", ""), "managed"),
        )
        payload = archive({"rules/a.md": "canonical"})
        item = package("rules", "1", payload)
        lock = self.store.resolve([item])
        self.store.admit(item, payload)
        generation = self.store.materialize(lock, owner, "managed")
        self.assertEqual(self.store.active_generation(), generation)
        self.assertEqual(self.store.materialize(lock, owner, "managed"), generation)
        directory = self.store.generations / generation
        self.assertEqual((directory / "boot.md").read_text(), once)
        self.assertEqual((directory / "projection/rules@1/rules/a.md").read_text(), "canonical")

    def test_interrupted_generation_is_not_active_and_reconciliation_removes_staging(self):
        payload = archive({"rules/a.md": "canonical"})
        item = package("rules", "1", payload)
        lock = self.store.resolve([item])
        self.store.admit(item, payload)
        self.assert_code(
            "simulated_crash",
            lambda: self.store.materialize(lock, "owner\n", "managed", crash_before_switch=True),
        )
        self.assertIsNone(self.store.active_generation())
        stale = self.store.generations / ".generation-stale"
        stale.mkdir()
        (stale / "partial").write_text("x")
        self.assertEqual(self.store.reconcile(), 1)
        self.assertFalse(stale.exists())

    def test_concurrent_identical_materialization_converges_on_one_generation(self):
        payload = archive({"rules/a.md": "canonical"})
        item = package("rules", "1", payload)
        lock = self.store.resolve([item])
        self.store.admit(item, payload)
        barrier = threading.Barrier(2)
        outcomes = []
        original_replace = os.replace

        def synchronized_replace(source, destination):
            if Path(source).name.startswith(".generation-"):
                barrier.wait()
            return original_replace(source, destination)

        def materialize():
            try:
                outcomes.append(self.store.materialize(lock, "owner\n", "managed"))
            except Exception as error:  # captured so the assertion reports the race
                outcomes.append(type(error).__name__)

        with mock.patch("adaptive_factory.vibevm_store.os.replace", side_effect=synchronized_replace):
            threads = [threading.Thread(target=materialize) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(len(set(outcomes)), 1, outcomes)
        self.assertEqual(outcomes[0], self.store.active_generation())


if __name__ == "__main__":
    unittest.main()
