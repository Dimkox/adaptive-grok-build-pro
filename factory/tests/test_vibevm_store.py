import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import stat
import tempfile
import threading
import unittest
from unittest import mock
import warnings
import zipfile

from adaptive_factory.vibevm_store import (
    UPSTREAM_ADAPTER_COMMIT,
    UPSTREAM_ADAPTER_TREE,
    StaticPackageRegistry,
    VibeVMStore,
    VibeVMStoreError,
    reconcile_boot_block,
)


def archive(entries):
    stream = io.BytesIO()
    with warnings.catch_warnings(), zipfile.ZipFile(stream, "w") as output:
        warnings.simplefilter("ignore", UserWarning)
        for name, value in entries:
            output.writestr(value if isinstance(value, zipfile.ZipInfo) else name,
                            b"x" if isinstance(value, zipfile.ZipInfo) else value)
    return stream.getvalue()


def package(name, version, payload, **changes):
    value = {"name": name, "version": version, "sha256": hashlib.sha256(payload).hexdigest(),
             "origin": "registry.example", "dependencies": {}, "qualified": True, "revoked": False}
    value.update(changes)
    return value


def publish_process(root, item, lock, queue):
    store = VibeVMStore(root, tenant_id="tenant-a", repository_id="owner/project",
                        registry=StaticPackageRegistry([item]))
    try:
        queue.put(store.materialize(lock, "owner\n", "managed"))
    except Exception as error:
        queue.put(type(error).__name__)


class CallbackRegistry(StaticPackageRegistry):
    callback = None

    def get_package(self, name, version):
        result = super().get_package(name, version)
        if self.callback is not None:
            callback, self.callback = self.callback, None
            callback()
        return result


class VibeVMStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.registry = CallbackRegistry()
        self.store = VibeVMStore(self.base, tenant_id="tenant-a", repository_id="owner/project",
                                 registry=self.registry)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def trust(self, item):
        self.registry.register(item)
        return item

    def lock(self, item):
        return self.store.resolve([self.trust(item)])

    def assert_code(self, code, operation):
        with self.assertRaises(VibeVMStoreError) as caught:
            operation()
        self.assertEqual(caught.exception.code, code)

    def test_provenance_is_exact_and_data_only(self):
        self.assertEqual(UPSTREAM_ADAPTER_COMMIT, "0b63caa86e80ff670dc2a62ff529079b91d08e4d")
        self.assertEqual(UPSTREAM_ADAPTER_TREE, "1ff4963aeea1f3f0a925485437b8dcf7130bf17d")
        self.assertEqual(self.store.capability, "factory_package_store_v1")
        self.assertFalse(hasattr(self.store, "execute_adapter"))

    def test_resolve_rechecks_authoritative_graph(self):
        a = self.trust(package("a", "1", archive([("a", "A")]), dependencies={"b": "1"}))
        b = self.trust(package("b", "1", archive([("b", "B")])))
        lock = self.store.resolve([a, b])
        self.assertEqual([value["name"] for value in lock["packages"]], ["b", "a"])
        self.assertEqual(lock, self.store.resolve([b, a]))
        self.assert_code("registry_mismatch:a@1", lambda: self.store.resolve([{**a, "sha256": "0" * 64}, b]))
        changed = {**a, "dependencies": {"b": "2"}}
        self.registry.register(changed)
        self.assert_code("version_conflict:a->b:2!=1", lambda: self.store.resolve([changed, b]))
        self.registry.register(a)
        cycled = {**b, "dependencies": {"a": "1"}}
        self.registry.register(cycled)
        self.assert_code("dependency_cycle:a->b->a", lambda: self.store.resolve([a, cycled]))

    def test_replay_rechecks_digest_origin_and_lifecycle_authority(self):
        payload = archive([("rules/a.md", "canonical")])
        item = package("rules", "1", payload)
        lock = self.lock(item)
        path = self.store.admit(item, payload)
        self.assertEqual(self.store.replay(lock), {"rules@1": payload})
        for forged in ({**item, "sha256": "0" * 64}, {**item, "qualified": False}, {**item, "revoked": True}):
            self.assert_code("registry_mismatch:rules@1", lambda forged=forged: self.store.admit(forged, payload))
        self.registry.register({**item, "revoked": True})
        self.assert_code("package_revoked:rules@1", lambda: self.store.replay(lock))
        self.registry.register({**item, "revoked": False, "qualified": False})
        self.assert_code("package_unqualified:rules@1", lambda: self.store.replay(lock))
        self.registry.register(item)
        forged = json.loads(json.dumps(lock))
        forged["packages"][0]["sha256"] = "0" * 64
        graph = {"packages": forged["packages"], "overrides": forged["overrides"]}
        forged["graph_digest"] = hashlib.sha256(
            json.dumps(graph, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        self.assert_code("registry_mismatch:rules@1", lambda: self.store.replay(forged))
        forged = json.loads(json.dumps(lock))
        forged["packages"][0]["qualified"] = True
        graph = {"packages": forged["packages"], "overrides": forged["overrides"]}
        forged["graph_digest"] = hashlib.sha256(
            json.dumps(graph, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        self.assert_code("invalid_lock_package", lambda: self.store.replay(forged))
        path.chmod(0o600)
        path.write_bytes(b"poison")
        self.assert_code("digest_mismatch:rules@1", lambda: self.store.replay(lock))

    def test_boot_marker_injection_and_corruption_fail(self):
        owner = "# Owner\nKeep bytes.\n"
        once = reconcile_boot_block(owner, "managed")
        self.assertEqual(reconcile_boot_block(once, "managed"), once)
        for owner_text, managed, code in (
            (once.replace("<!-- /adaptive-vibevm -->", ""), "x", "boot_block_corrupt"),
            (once + once[len(owner):], "x", "boot_block_conflict"),
            (owner, "<!-- adaptive-vibevm -->", "boot_block_injection"),
            (owner, "<!-- /adaptive-vibevm -->", "boot_block_injection"),
        ):
            self.assert_code(code, lambda o=owner_text, m=managed: reconcile_boot_block(o, m))

    def test_hostile_zip_matrix_preserves_old_active(self):
        good = archive([("rule.md", "ok")])
        good_item = package("good", "1", good)
        good_lock = self.lock(good_item)
        self.store.admit(good_item, good)
        old = self.store.materialize(good_lock, "owner\n", "managed")
        link, fifo = zipfile.ZipInfo("link"), zipfile.ZipInfo("fifo")
        link.external_attr, fifo.external_attr = stat.S_IFLNK << 16, stat.S_IFIFO << 16
        cases = {
            "invalid_archive:bad@1": b"not zip",
            "path_escape": archive([("../escape", "x")]),
            "noncanonical_member": archive([("a\\b", "x")]),
            "member_alias:A": archive([("a", "x"), ("A", "y")]),
            "member_alias:é": archive([("é", "x"), ("é", "y")]),
            "duplicate_member:dup": archive([("dup", "one"), ("dup", "two")]),
            "non_regular_member:link": archive([("link", link)]),
            "non_regular_member:fifo": archive([("fifo", fifo)]),
            "lifecycle_hook_forbidden": archive([("Scripts/BUILD.SH", "x")]),
            "path_depth_exceeded": archive([("a/b/c/d", "x")]),
            "expanded_size_exceeded": archive([("large", "123456789")]),
            "file_count_exceeded": archive([("a", "1"), ("b", "2")]),
            "path_collision:a": archive([("a", "x"), ("a/b", "y")]),
            "invalid_xml:bad.xml": archive([("bad.xml", "<x>")]),
            "xml_dtd_forbidden:dtd.xml": archive([("dtd.xml", "<?xml version='1.0' encoding='UTF-16'?><!DOCTYPE x><x/>".encode("utf-16"))]),
            "xml_entity_forbidden:entity.xml": archive([("entity.xml", "<!DOCTYPE x [<!ENTITY e 'v'>]><x>&e;</x>")]),
        }
        for expected, payload in cases.items():
            with self.subTest(expected=expected):
                item = package("bad", "1", payload)
                self.registry.register(item)
                lock = self.store.resolve([item])
                self.store.admit(item, payload)
                self.store.max_files = 1 if expected == "file_count_exceeded" else 128
                self.store.max_bytes = 8 if expected == "expanded_size_exceeded" else 262_144
                self.store.max_depth = 3 if expected == "path_depth_exceeded" else 12
                self.assert_code(expected, lambda: self.store.materialize(lock, "owner\n", "bad"))
                self.assertEqual(self.store.active_generation(), old)

        for raw_path in ("a//b", "a/./b", "./a"):
            with self.subTest(raw_path=raw_path):
                payload = archive([(raw_path, "x")])
                item = package("raw-alias", hashlib.sha256(raw_path.encode()).hexdigest()[:8], payload)
                self.registry.register(item)
                lock = self.store.resolve([item])
                self.store.admit(item, payload)
                self.assert_code("noncanonical_member", lambda: self.store.materialize(lock, "owner\n", "bad"))
                self.assertEqual(self.store.active_generation(), old)

    def test_crc_and_encrypted_members_fail_closed(self):
        good = archive([("good", "ok")])
        good_item = package("good", "1", good)
        good_lock = self.lock(good_item)
        self.store.admit(good_item, good)
        old = self.store.materialize(good_lock, "owner\n", "old")
        damaged = bytearray(archive([("a", "payload")]))
        damaged[damaged.find(b"payload")] ^= 1
        item = package("crc", "1", bytes(damaged))
        lock = self.lock(item)
        self.store.admit(item, bytes(damaged))
        self.assert_code("archive_crc_mismatch:a", lambda: self.store.materialize(lock, "owner\n", "x"))
        self.assertEqual(self.store.active_generation(), old)
        encrypted = bytearray(archive([("a", "x")]))
        encrypted[6] |= 1
        encrypted[encrypted.find(b"PK\x01\x02") + 8] |= 1
        item = package("encrypted", "1", bytes(encrypted))
        lock = self.lock(item)
        self.store.admit(item, bytes(encrypted))
        self.assert_code("encrypted_member:a", lambda: self.store.materialize(lock, "owner\n", "x"))
        self.assertEqual(self.store.active_generation(), old)

    def test_manifest_tamper_and_generation_symlink_are_rejected(self):
        payload = archive([("rule.md", "ok")])
        item = package("rules", "1", payload)
        lock = self.lock(item)
        self.store.admit(item, payload)
        generation = self.store.materialize(lock, "owner\n", "managed")
        target = self.store.generations / generation
        original_boot = (target / "boot.md").read_bytes()
        (target / "boot.md").write_text("tampered")
        self.assert_code("active_generation_corrupt", lambda: self.store.materialize(lock, "owner\n", "managed"))
        self.assertEqual(self.store.active_path.read_text().strip(), generation)
        (target / "boot.md").write_bytes(original_boot)
        link = self.store.generations / ("f" * 64)
        link.symlink_to(target, target_is_directory=True)
        self.store.active_path.write_text("f" * 64 + "\n")
        self.assert_code("active_generation_corrupt", self.store.active_generation)

    def test_external_hardlinks_in_object_generation_manifest_and_active_fail_closed(self):
        payload = archive([("rule.md", "ok")])
        item = package("rules", "1", payload)
        lock = self.lock(item)
        object_path = self.store.admit(item, payload)
        generation = self.store.materialize(lock, "owner\n", "managed")
        external = self.base / "external-link"
        os.link(object_path, external)
        self.assert_code("object_authority_mismatch:rules@1", lambda: self.store.replay(lock))
        external.unlink()
        generation_file = self.store.generations / generation / "boot.md"
        os.link(generation_file, external)
        self.assert_code("active_generation_corrupt", self.store.active_generation)
        self.assert_code("active_generation_corrupt", lambda: self.store.materialize(lock, "owner\n", "managed"))
        self.assertEqual(self.store.active_path.read_text().strip(), generation)
        external.unlink()
        manifest = self.store.generations / generation / "manifest.json"
        os.link(manifest, external)
        self.assert_code("active_generation_corrupt", self.store.active_generation)
        external.unlink()
        os.link(self.store.active_path, external)
        self.assert_code("active_generation_corrupt", self.store.active_generation)

    def test_registry_callback_cannot_redirect_object_writes_or_reads(self):
        payload = archive([("rule.md", "ok")])
        item = package("rules", "1", payload)
        lock = self.lock(item)
        self.store.admit(item, payload)
        outside = self.base / "outside"
        outside.mkdir(mode=0o700)
        moved = self.base / "objects-moved"

        def swap_objects():
            self.store.objects.rename(moved)
            self.store.objects.symlink_to(outside, target_is_directory=True)

        self.registry.callback = swap_objects
        self.assert_code("store_path_changed", lambda: self.store.replay(lock))
        self.assertEqual(list(outside.iterdir()), [])

    def test_descriptor_lifecycle_close_constructor_rollback_and_hostile_replay_are_bounded(self):
        def descriptor_count():
            return len(list(Path("/proc/self/fd").iterdir()))

        baseline = descriptor_count()
        with VibeVMStore(self.base, tenant_id="context", repository_id="repo", registry=self.registry) as scoped:
            self.assertGreater(descriptor_count(), baseline)
            self.assertIsNone(scoped.active_generation())
        self.assertEqual(descriptor_count(), baseline)
        scoped.close()
        self.assert_code("store_closed", scoped.active_generation)
        self.assert_code("store_closed", lambda: scoped.object_path("0" * 64))

        unsafe = self.base / "partial"
        unsafe.mkdir(mode=0o700)
        outside = self.base / "partial-outside"
        outside.mkdir(mode=0o700)
        (unsafe / "tenants").symlink_to(outside, target_is_directory=True)
        before_failure = descriptor_count()
        self.assert_code(
            "store_path_unsafe",
            lambda: VibeVMStore(unsafe, tenant_id="tenant", repository_id="repo", registry=self.registry),
        )
        self.assertEqual(descriptor_count(), before_failure)

        disappearing = self.base / "disappearing"
        disappearing.mkdir(mode=0o700)
        original_lstat = Path.lstat

        def disappear_after_open(path):
            if path == disappearing / "tenants":
                raise FileNotFoundError(path)
            return original_lstat(path)

        before_disappearance = descriptor_count()
        with mock.patch("adaptive_factory.vibevm_store.Path.lstat", new=disappear_after_open):
            self.assert_code(
                "store_path_missing",
                lambda: VibeVMStore(
                    disappearing, tenant_id="tenant", repository_id="repo", registry=self.registry
                ),
            )
        self.assertEqual(descriptor_count(), before_disappearance)

        payload = archive([("rule.md", "ok")])
        item = package("leak", "1", payload)
        lock = self.lock(item)
        object_path = self.store.admit(item, payload)
        hardlink = self.base / "object-hardlink"
        os.link(object_path, hardlink)
        before_replays = descriptor_count()
        for _ in range(100):
            self.assert_code("object_authority_mismatch:leak@1", lambda: self.store.replay(lock))
        self.assertEqual(descriptor_count(), before_replays)

    def test_restart_and_tenant_repository_symlink_isolation(self):
        payload = archive([("rule.md", "ok")])
        item = package("rules", "1", payload)
        lock = self.lock(item)
        self.store.admit(item, payload)
        generation = self.store.materialize(lock, "owner\n", "managed")
        restarted = VibeVMStore(self.base, tenant_id="tenant-a", repository_id="owner/project", registry=self.registry)
        self.assertEqual(restarted.active_generation(), generation)
        other = VibeVMStore(self.base, tenant_id="tenant-b", repository_id="owner/project", registry=self.registry)
        self.assert_code("missing_package:rules@1", lambda: other.replay(lock))
        alias = VibeVMStore(self.base, tenant_id="tenant-a", repository_id="owner_project", registry=self.registry)
        self.assertNotEqual(alias.root, self.store.root)
        moved = self.base / "moved"
        self.store.root.rename(moved)
        self.store.root.symlink_to(moved, target_is_directory=True)
        self.assert_code("store_path_changed", lambda: self.store.replay(lock))

    def test_root_must_be_owner_pinned_and_not_writable_by_others(self):
        unsafe = self.base / "unsafe"
        unsafe.mkdir(mode=0o700)
        unsafe.chmod(0o777)
        self.assert_code(
            "store_root_unsafe",
            lambda: VibeVMStore(unsafe, tenant_id="tenant", repository_id="repo", registry=self.registry),
        )
        real = self.base / "real"
        real.mkdir(mode=0o700)
        (real / "root").mkdir(mode=0o700)
        alias = self.base / "alias"
        alias.symlink_to(real, target_is_directory=True)
        self.assert_code(
            "store_path_unsafe",
            lambda: VibeVMStore(alias / "root", tenant_id="tenant", repository_id="repo", registry=self.registry),
        )

    def test_exact_archive_bounds_are_admitted(self):
        bounded = VibeVMStore(self.base, tenant_id="bounded", repository_id="repo", registry=self.registry,
                              max_files=1, max_bytes=8, max_depth=3)
        payload = archive([("a/b/c", "12345678")])
        item = package("bounded", "1", payload)
        self.registry.register(item)
        lock = bounded.resolve([item])
        bounded.admit(item, payload)
        self.assertEqual(bounded.active_generation(), None)
        self.assertEqual(bounded.materialize(lock, "owner\n", "managed"), bounded.active_generation())

    def test_thread_and_process_competitors_converge_and_reconcile(self):
        payload = archive([("rule.md", "ok")])
        item = package("rules", "1", payload)
        lock = self.lock(item)
        self.store.admit(item, payload)
        barrier, outcomes, original = threading.Barrier(2), [], os.replace

        def synchronized(source, destination, *args, **kwargs):
            if Path(source).name.startswith(".generation-"):
                barrier.wait()
            return original(source, destination, *args, **kwargs)

        def publish_thread():
            try:
                outcomes.append(self.store.materialize(lock, "owner\n", "managed"))
            except Exception as error:
                outcomes.append(type(error).__name__)

        with mock.patch("adaptive_factory.vibevm_store.os.replace", side_effect=synchronized):
            threads = [threading.Thread(target=publish_thread) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(len(set(outcomes)), 1)
        context, queue = multiprocessing.get_context("fork"), multiprocessing.get_context("fork").Queue()
        processes = [context.Process(target=publish_process, args=(self.base, item, lock, queue)) for _ in range(2)]
        for process in processes:
            process.start()
        process_outcomes = {queue.get(timeout=5), queue.get(timeout=5)}
        for process in processes:
            process.join(5)
            self.assertFalse(process.is_alive())
        self.assertEqual(process_outcomes, {outcomes[0]})
        stale = self.store.generations / ".generation-stale"
        stale.mkdir()
        self.assertEqual(self.store.reconcile(), 1)


if __name__ == "__main__":
    unittest.main()
