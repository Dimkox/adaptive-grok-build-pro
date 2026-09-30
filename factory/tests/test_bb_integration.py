import tempfile
import hashlib
from pathlib import Path
import unittest

from adaptive_factory.contracts import ContractError
from factory.tests import test_behavior_qualification as harness_tests
from factory.tests import test_runtime_installer as installer_tests


class BBIntegrationTests(unittest.TestCase):
    package = installer_tests.InstallerTests.package

    def test_installer_binding_default_off_and_verified_health_switch(self):
        from adaptive_factory.bb_integration import InstallerBBPayloadLifecycle

        with tempfile.TemporaryDirectory() as directory:
            self.parent = Path(directory)
            runtime = installer_tests.Runtime()
            port = InstallerBBPayloadLifecycle(self.parent / "bb", runtime)
            self.assertFalse(port.status()["enabled"])
            with self.assertRaises(ContractError):
                port.switch("a" * 64)
            self.assertFalse((self.parent / "bb").exists())
            # Explicit synthetic qualification path only; no real upstream activation.
            runtime.synthetic = True
            port = InstallerBBPayloadLifecycle(self.parent / "bb", runtime, synthetic=True)
            artifact = self.package()
            identity = dict(
                archive=str(artifact["archive"]),
                manifest=str(artifact["manifest"]),
                archive_digest=artifact["archive_sha256"],
                manifest_digest=artifact["manifest_sha256"],
                source_commit="1" * 40,
            )
            verified = port.verify_archive(identity)
            self.assertFalse(port.root.exists())
            port.switch(verified["version"])
            self.assertEqual(port.manager.status()["current"], verified["version"])
            self.assertEqual(port.status()["live_qualification"], "not_run")

    def test_native_comparator_binding_preserves_frozen_corpus_and_no_authority(self):
        from adaptive_factory.bb_integration import compare_bb_native

        fixture = harness_tests.BehaviorQualificationTests()
        variants = fixture.variants()
        variants["B"]["backend"] = variants["C"]["backend"] = "bb"
        calls = []

        def executor(*args):
            calls.append(args[0])
            return fixture.executor(*args)

        disabled = compare_bb_native(variants, fixture.config(), executor)
        self.assertEqual(disabled["backend"], "native")
        self.assertEqual(calls, [])
        report = compare_bb_native(variants, fixture.config(), executor, synthetic=True)
        self.assertEqual(len(calls), 36)
        self.assertEqual(report["authority_effect"], "none")
        self.assertEqual(report["external_qualification"]["status"], "not_run")
        self.assertNotEqual(report["verdict"], "pass")

    def test_retained_backup_and_schema_compatible_rollback_revalidate_bytes(self):
        from adaptive_factory.bb_integration import InstallerBBPayloadLifecycle
        from adaptive_factory.bb_profiles import BBRecoverySnapshotV1

        with tempfile.TemporaryDirectory() as directory:
            self.parent = Path(directory)
            runtime = installer_tests.Runtime()
            runtime.synthetic = True
            port = InstallerBBPayloadLifecycle(self.parent / "bb", runtime, synthetic=True)

            def admit(version):
                artifact = self.package(version)
                return port.verify_archive(
                    dict(
                        archive=str(artifact["archive"]),
                        manifest=str(artifact["manifest"]),
                        archive_digest=artifact["archive_sha256"],
                        manifest_digest=artifact["manifest_sha256"],
                        source_commit="1" * 40,
                    )
                )

            def retain(release):
                names = (
                    "data_digest",
                    "config_digest",
                    "mappings_digest",
                    "artifacts_digest",
                    "external_receipts_digest",
                )
                record = BBRecoverySnapshotV1.from_dict(
                    dict(
                        schema_version=1,
                        version=release["version"],
                        source_commit="1" * 40,
                        archive_digest=release["archive_digest"],
                        data_schema_version=1,
                        **{name: hashlib.sha256(name.encode()).hexdigest() for name in names},
                    )
                )
                bundle = port.root / "backups" / record.record_digest
                bundle.mkdir(mode=0o700)
                for name in names:
                    (bundle / name).write_bytes(name.encode())
                    (bundle / name).chmod(0o600)
                port.backup(record)
                return record, bundle

            first = admit("1.0.0")
            port.switch(first["version"])
            saved, bundle = retain(first)
            second = admit("1.0.1")
            port.switch(second["version"])
            retain(second)
            (bundle / "config_digest").write_bytes(b"tampered")
            with self.assertRaises(ContractError):
                port.rollback(saved)
            self.assertEqual(port.manager.status()["current"], second["version"])
            (bundle / "config_digest").write_bytes(b"config_digest")
            result = port.rollback(saved)
            self.assertEqual(result["version"], first["version"])
            self.assertEqual(result["data"], "preserved")
            port.uninstall()
            self.assertTrue((port.root / "data").is_dir())
            self.assertTrue(bundle.is_dir())


if __name__ == "__main__":
    unittest.main()
