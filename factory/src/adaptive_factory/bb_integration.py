"""BB source bindings: synthetic qualification only, never live activation authority.

The admitted generic installer owns archive/pointer/health/rollback logic. The shared
paired harness owns corpus, baseline, oracle and budget accounting. No upstream BB
endpoint or provider behavior is invented here.
"""

import hashlib
import os
from pathlib import Path
import stat

from .bb_profiles import BBRecoverySnapshotV1, validate_recovery
from .behavior_qualification import make_comparator_profile, native_comparator_profile, run_comparison
from .contracts import ContractError
from .settings import read_private_file
from .v15_contracts import closed, digest, sha


def compare_bb_native(variants, config, executor, *, synthetic=False):
    if synthetic is not True:
        return dict(backend="native", bb_qualification="not_run", authority_effect="none")
    if (
        not isinstance(variants, dict)
        or set(variants) != {"A", "B", "C"}
        or variants["A"].get("backend") != "native"
        or any(variants[m].get("backend") != "bb" for m in ("B", "C"))
    ):
        raise ContractError("bb_native_comparator_variants")
    native = native_comparator_profile()
    profile = make_comparator_profile("factory-bb-native-v1", native.suite, native.baseline, native.oracle_id)
    return run_comparison(profile, variants, config, executor).to_dict()


class InstallerBBPayloadLifecycle:
    """Default-off port. Explicit synthetic mode cannot activate real upstream BB.

    `backup` verifies an operator-retained private snapshot bundle, not an unsafe
    hot copy of a running SQLite database. External receipts must remain reconciled;
    incompatible schema/effect changes require independent operator recovery.
    """

    def __init__(self, root, adapter=None, *, synthetic=False):
        from factory.runtime import setup_manager

        self.setup = setup_manager
        self.root = Path(root)
        self.enabled = synthetic is True and getattr(adapter, "synthetic", False) is True
        self.manager = setup_manager.SetupManager(self.root, adapter)
        self.archives = {}
        self.snapshots = {}

    def _enabled(self):
        if not self.enabled:
            raise ContractError("bb_payload_lifecycle_unavailable")

    def status(self):
        if not self.enabled:
            return dict(status="unavailable", enabled=False, backend="native", authority_effect="none")
        return dict(status=self.manager.status(), enabled=True, live_qualification="not_run", authority_effect="none")

    def verify_archive(self, archive_identity):
        self._enabled()
        closed(archive_identity, ("archive", "manifest", "archive_digest", "manifest_digest", "source_commit"))
        for name in ("archive_digest", "manifest_digest"):
            digest(archive_identity[name])
        sha(archive_identity["source_commit"])
        artifact = dict(
            archive=Path(archive_identity["archive"]),
            manifest=Path(archive_identity["manifest"]),
            archive_sha256=archive_identity["archive_digest"],
            manifest_sha256=archive_identity["manifest_digest"],
        )
        release = self.setup.verify_release(**artifact)
        if len(self.archives) >= 16 and release.identity not in self.archives:
            raise ContractError("bb_payload_inventory_limit")
        self.archives[release.identity] = (artifact, dict(archive_identity), release.manifest)
        return dict(
            version=release.identity,
            product_version=release.manifest["product_version"],
            archive_digest=release.archive_sha256,
            source_commit=archive_identity["source_commit"],
            authority_effect="none",
        )

    def backup(self, snapshot):
        self._enabled()
        snapshot = BBRecoverySnapshotV1.from_dict(snapshot.to_dict())
        data = snapshot.to_dict()
        state = self.manager.status()
        archive = self.archives.get(data["version"])
        if (
            state["current"] != data["version"]
            or archive is None
            or data["archive_digest"] != archive[1]["archive_digest"]
            or data["source_commit"] != archive[1]["source_commit"]
            or data["data_schema_version"] != state["data_schema"]
        ):
            raise ContractError("bb_backup_identity_mismatch")
        path = self._read_backup(snapshot)
        self.snapshots[data["version"]] = (snapshot, path)
        return dict(snapshot_digest=snapshot.record_digest, status="verified_retained_backup", authority_effect="none")

    def _read_backup(self, snapshot):
        directory = self.root / "backups" / snapshot.record_digest
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ContractError("bb_backup_private_directory_required")
        restored = {}
        for name in ("data_digest", "config_digest", "mappings_digest", "artifacts_digest", "external_receipts_digest"):
            restored[name] = hashlib.sha256(read_private_file(directory / name, 16 * 1024 * 1024)).hexdigest()
        validate_recovery(
            snapshot, compatible_schema_versions=[self.manager.status()["data_schema"]], restored_digests=restored
        )
        return directory / "data_digest"

    def _transition(self, candidate):
        state = self.manager.status()
        retained = self.snapshots.get(state["current"])
        if retained is None:
            raise ContractError("bb_verified_backup_required")
        snapshot, path = retained
        self._read_backup(snapshot)
        return self.setup.TransitionEvidence(
            str(self.root), state["current"], candidate, state["data_schema"], path, snapshot.to_dict()["data_digest"]
        )

    def switch(self, version):
        self._enabled()
        archive = self.archives.get(version)
        if archive is None:
            raise ContractError("bb_verified_archive_required")
        state = self.manager.status()
        if state["current"] is None:
            identity = self.manager.install(**archive[0])
        else:
            identity = self.manager.update(evidence=self._transition(version), **archive[0])
        return dict(version=identity, authority_effect="none", live_qualification="not_run")

    def rollback(self, snapshot):
        self._enabled()
        data = BBRecoverySnapshotV1.from_dict(snapshot.to_dict()).to_dict()
        prior = self.snapshots.get(data["version"])
        current = self.snapshots.get(self.manager.status()["current"])
        if (
            prior is None
            or current is None
            or prior[0].record_digest != snapshot.record_digest
            or data["external_receipts_digest"] != current[0].to_dict()["external_receipts_digest"]
            or data["data_schema_version"] != current[0].to_dict()["data_schema_version"]
        ):
            raise ContractError("bb_recovery_incompatible_or_unreconciled")
        self._read_backup(snapshot)
        identity = self.manager.reverse(data["version"], evidence=self._transition(data["version"]))
        return dict(version=identity, data="preserved", authority_effect="none", live_qualification="not_run")

    def uninstall(self):
        """The generic installer confirms stop and retains operational data by default."""
        self._enabled()
        self.manager.remove()
        return dict(status="uninstalled", data="preserved", authority_effect="none")
