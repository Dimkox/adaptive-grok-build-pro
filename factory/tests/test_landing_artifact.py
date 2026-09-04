from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import io
import os
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from adaptive_factory.landing_artifact import (
    CONTROL_REPOSITORY_ID,
    DEPLOY_MEMBERS,
    ExactGitLandingArtifactSource,
    LandingArtifactError,
    LandingArtifactPackager,
)
from adaptive_factory.landing_contracts import strict_json_object
from adaptive_factory.landing_coordinator import LandingCoordinator
from adaptive_factory.landing_evaluation import DeterministicLandingEvaluator
from adaptive_factory.landing_renderer import (
    DeterministicLandingRenderer,
    ExactGitLandingWorkspace,
    TARGET_REPOSITORY_ID,
)
from factory.tests.test_landing_renderer import landing_spec, sealed_target


FIXED_TIME = datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc)
PROFILE_DIGEST = "2" * 64
PROHIBITED_MEMBERS = frozenset(
    {
        "ASSETS.md",
        "SERVER-SETUP.md",
        "og-image.jpg",
        "dist",
        "docs",
        "reports",
        "research",
        "tests",
    }
)


@contextmanager
def candidate_fixture():
    with sealed_target() as (target, _sha, _tree), tempfile.TemporaryDirectory(
        prefix="landing-render-scratch-"
    ) as scratch:
        result = LandingCoordinator(
            ExactGitLandingWorkspace(target, scratch_root=Path(scratch)),
            DeterministicLandingRenderer(),
            DeterministicLandingEvaluator(clock=lambda: FIXED_TIME),
            clock=lambda: FIXED_TIME,
        ).run(landing_spec(), profile_digest=PROFILE_DIGEST)
        if result.candidate is None:
            raise AssertionError("sealed fixture did not produce a candidate")
        yield target, result.candidate, result.attempts[-1], result.evaluations[-1]


class LandingArtifactTests(unittest.TestCase):
    def test_same_candidate_seals_reproducibly_with_exact_deploy_inventory(self):
        with candidate_fixture() as (target, candidate, attempt, evaluation):
            with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
                packager = LandingArtifactPackager(
                    ExactGitLandingArtifactSource(target)
                )
                first_result = packager.seal(
                    candidate, attempt, evaluation, Path(first)
                )
                second_result = packager.seal(
                    candidate, attempt, evaluation, Path(second)
                )
                first_zip_bytes = first_result.zip_path.read_bytes()
                second_zip_bytes = second_result.zip_path.read_bytes()

        self.assertEqual(first_result.zip_path.name, second_result.zip_path.name)
        self.assertEqual(first_zip_bytes, second_zip_bytes)
        self.assertEqual(first_result.sidecar_bytes, second_result.sidecar_bytes)
        self.assertEqual(first_result.manifest_bytes, second_result.manifest_bytes)
        self.assertEqual(tuple(sorted(DEPLOY_MEMBERS)), first_result.member_names)
        self.assertEqual(19, len(first_result.member_names))
        self.assertTrue(PROHIBITED_MEMBERS.isdisjoint(first_result.member_names))
        self.assertEqual(
            f"{first_result.artifact.zip_sha256.upper()}  {first_result.zip_path.name}\n".encode(),
            first_result.sidecar_bytes,
        )
        self.assertEqual(
            hashlib.sha256(first_result.sidecar_bytes).hexdigest(),
            first_result.artifact.sidecar_sha256,
        )

        with zipfile.ZipFile(io.BytesIO(first_zip_bytes)) as archive:
            self.assertEqual(list(first_result.member_names), archive.namelist())
            self.assertEqual(b"", archive.comment)
            for member in archive.infolist():
                with self.subTest(member=member.filename):
                    self.assertEqual((2000, 1, 1, 0, 0, 0), member.date_time)
                    self.assertEqual(3, member.create_system)
                    self.assertEqual(0o100644, member.external_attr >> 16)
                    self.assertEqual(b"", member.extra)
                    self.assertEqual(b"", member.comment)
                    self.assertEqual(zipfile.ZIP_DEFLATED, member.compress_type)

    def test_manifest_binds_both_repositories_and_every_member_provenance(self):
        with candidate_fixture() as (target, candidate, attempt, evaluation):
            with tempfile.TemporaryDirectory() as output:
                result = LandingArtifactPackager(
                    ExactGitLandingArtifactSource(target)
                ).seal(candidate, attempt, evaluation, Path(output))
                zip_bytes = result.zip_path.read_bytes()

        manifest = strict_json_object(result.manifest_bytes)
        self.assertEqual(1, manifest["schema_version"])
        self.assertEqual(CONTROL_REPOSITORY_ID, manifest["control_repository_id"])
        self.assertEqual(TARGET_REPOSITORY_ID, manifest["target_repository_id"])
        self.assertEqual(candidate.source_sha, manifest["source_sha"])
        self.assertEqual(candidate.source_tree, manifest["source_tree"])
        self.assertEqual(candidate.candidate_sha, manifest["candidate_sha"])
        self.assertEqual(candidate.candidate_tree, manifest["candidate_tree"])
        self.assertEqual(["content.css", "index.html"], manifest["changed_paths"])
        self.assertEqual(list(result.member_names), [item["path"] for item in manifest["members"]])
        self.assertEqual(
            ["content.css", "index.html"],
            [item["path"] for item in manifest["members"] if item["provenance"] == "candidate"],
        )
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            for item in manifest["members"]:
                body = archive.read(item["path"])
                self.assertEqual("0644", item["archive_mode"])
                self.assertEqual(len(body), item["size_bytes"])
                self.assertEqual(hashlib.sha256(body).hexdigest(), item["sha256"])

    def test_invalid_snapshot_paths_modes_identity_and_delta_fail_closed(self):
        with candidate_fixture() as (target, candidate, attempt, evaluation):
            packager = LandingArtifactPackager(ExactGitLandingArtifactSource(target))
            first = candidate.candidate_members[0]
            cases = {
                "path_traversal": replace(
                    candidate,
                    candidate_members=(replace(first, path="../escape"),)
                    + candidate.candidate_members[1:],
                ),
                "backslash": replace(
                    candidate,
                    candidate_members=(replace(first, path="bad\\path"),)
                    + candidate.candidate_members[1:],
                ),
                "absolute_path": replace(
                    candidate,
                    candidate_members=(replace(first, path="/absolute"),)
                    + candidate.candidate_members[1:],
                ),
                "duplicate_path": replace(
                    candidate,
                    candidate_members=candidate.candidate_members + (first,),
                ),
                "case_collision": replace(
                    candidate,
                    candidate_members=candidate.candidate_members
                    + (replace(first, path=first.path.upper()),),
                ),
                "special_mode": replace(
                    candidate,
                    candidate_members=(replace(first, mode="120000"),)
                    + candidate.candidate_members[1:],
                ),
                "wrong_tree": replace(candidate, candidate_tree="0" * 40),
                "wrong_commit": replace(candidate, candidate_sha="0" * 40),
                "wrong_delta": replace(candidate, changed_paths=("index.html",)),
            }
            for code, invalid in cases.items():
                with self.subTest(code=code), tempfile.TemporaryDirectory() as output:
                    with self.assertRaises(LandingArtifactError):
                        packager.seal(invalid, attempt, evaluation, Path(output))

    def test_source_symlink_hardlink_special_and_executable_inputs_are_rejected(self):
        mutations = ("symlink", "hardlink", "special", "executable")
        for mutation in mutations:
            with self.subTest(mutation=mutation), candidate_fixture() as (
                target,
                candidate,
                attempt,
                evaluation,
            ), tempfile.TemporaryDirectory() as output:
                path = target / "privacy.html"
                original = path.read_bytes()
                path.unlink()
                if mutation == "symlink":
                    path.symlink_to("terms.html")
                elif mutation == "hardlink":
                    os.link(target / "terms.html", path)
                elif mutation == "special":
                    os.mkfifo(path)
                else:
                    path.write_bytes(original)
                    path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
                with self.assertRaises(LandingArtifactError):
                    LandingArtifactPackager(
                        ExactGitLandingArtifactSource(target)
                    ).seal(candidate, attempt, evaluation, Path(output))

    def test_output_pair_is_no_replace_and_product_package_is_unchanged(self):
        product_paths = tuple(sorted(Path("packages").glob("adaptive-grok-build-pro-v2.0.13*")))
        product_before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest() for path in product_paths
        }
        with candidate_fixture() as (target, candidate, attempt, evaluation):
            with tempfile.TemporaryDirectory() as output:
                packager = LandingArtifactPackager(ExactGitLandingArtifactSource(target))
                result = packager.seal(candidate, attempt, evaluation, Path(output))
                original = (result.zip_path.read_bytes(), result.sidecar_path.read_bytes())
                inodes = (result.zip_path.stat().st_ino, result.sidecar_path.stat().st_ino)
                replay = packager.seal(candidate, attempt, evaluation, Path(output))
                self.assertEqual(result.artifact, replay.artifact)
                self.assertEqual(
                    inodes,
                    (replay.zip_path.stat().st_ino, replay.sidecar_path.stat().st_ino),
                )
                self.assertEqual(original[0], result.zip_path.read_bytes())
                self.assertEqual(original[1], result.sidecar_path.read_bytes())
                self.assertEqual([], list(Path(output).glob(".landing-*")))
        self.assertEqual(
            product_before,
            {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in product_paths},
        )

    def test_exact_orphan_zip_is_completed_on_retry_without_replacement(self):
        with candidate_fixture() as (target, candidate, attempt, evaluation):
            with tempfile.TemporaryDirectory() as output:
                packager = LandingArtifactPackager(
                    ExactGitLandingArtifactSource(target)
                )
                first = packager.seal(candidate, attempt, evaluation, Path(output))
                zip_bytes = first.zip_path.read_bytes()
                sidecar_bytes = first.sidecar_path.read_bytes()
                zip_inode = first.zip_path.stat().st_ino
                first.sidecar_path.unlink()

                recovered = packager.seal(
                    candidate, attempt, evaluation, Path(output)
                )

                self.assertEqual(recovered.zip_path.read_bytes(), zip_bytes)
                self.assertEqual(recovered.sidecar_path.read_bytes(), sidecar_bytes)
                self.assertEqual(recovered.artifact, first.artifact)
                self.assertEqual(zip_inode, recovered.zip_path.stat().st_ino)
                replay = packager.seal(candidate, attempt, evaluation, Path(output))
                self.assertEqual(recovered.artifact, replay.artifact)
                recovered.sidecar_path.write_bytes(b"mismatch\n")
                with self.assertRaisesRegex(LandingArtifactError, "artifact_exists"):
                    packager.seal(candidate, attempt, evaluation, Path(output))
                self.assertEqual(zip_bytes, recovered.zip_path.read_bytes())

    def test_artifact_rejects_nonpassing_or_unbound_evaluation(self):
        with candidate_fixture() as (target, candidate, attempt, evaluation):
            packager = LandingArtifactPackager(ExactGitLandingArtifactSource(target))
            for invalid in (
                replace(evaluation, decision="needs_human"),
                replace(evaluation, candidate_head_sha="0" * 40),
                replace(attempt, exact_head_sha="0" * 40),
            ):
                with self.subTest(value=type(invalid).__name__), tempfile.TemporaryDirectory() as output:
                    if type(invalid) is type(attempt):
                        bad_attempt, bad_evaluation = invalid, evaluation
                    else:
                        bad_attempt, bad_evaluation = attempt, invalid
                    with self.assertRaises(LandingArtifactError):
                        packager.seal(
                            candidate,
                            bad_attempt,
                            bad_evaluation,
                            Path(output),
                        )


if __name__ == "__main__":
    unittest.main()
