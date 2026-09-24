"""Private local publication fixtures; grants are synthetic data, never authority."""

from contextlib import ExitStack
from contextlib import closing
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import io
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from adaptive_delivery.landing_filesystem import FilesystemLandingPublisher, private_root
from adaptive_delivery.landing_publication import LandingPublicationCoordinator, PublicationStore
from adaptive_delivery.landing_publication_contracts import (
    PublicationBundle, PublicationError, PublicationRequestV1, PublicationTargetV1,
)
from adaptive_factory import landing_publication_cli
from scripts import grok_landing_publish
from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_artifact import ExactGitLandingArtifactSource, LandingArtifactPackager
from factory.tests.test_landing_artifact import candidate_fixture


class LandingPublicationBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="publication-boundary-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.target_root = self.root / "target"
        self.target_root.mkdir(mode=0o700)
        state = self.root / "intent-state"
        state.mkdir(mode=0o700)
        lock = self.target_root / ".publication.lock"
        lock.touch(mode=0o600)
        metadata = self.target_root.stat()
        self.target = PublicationTargetV1(
            1, "test-target", str(self.target_root), "https://therealaidarkfactory.online",
            os.geteuid(), metadata.st_dev, metadata.st_ino,
        )
        self.store = PublicationStore(state)
        self.addCleanup(self.store.close)
        self.addCleanup(self.unfreeze)
        with candidate_fixture() as (source, candidate, attempt, evaluation):
            output = self.root / "artifacts"
            output.mkdir(mode=0o700)
            retained = LandingArtifactPackager(ExactGitLandingArtifactSource(source)).seal(
                candidate, attempt, evaluation, output,
            )
            self.bundle = PublicationBundle(canonical_json(retained.artifact.to_dict()), retained.manifest_bytes,
                                            retained.zip_path.read_bytes(), retained.member_names)
        self.adapter = FilesystemLandingPublisher(self.target)
        self.coordinator = LandingPublicationCoordinator(self.store, self.adapter, lambda reference: self.bundle)
        self.reference = {"tenant_id": "test-tenant", "repository_id": "test-repository", "job_id": "test-job"}

    def unfreeze(self):
        for directory, _names, files in os.walk(self.target_root):
            Path(directory).chmod(0o700)
            for name in files:
                path = Path(directory) / name
                if not path.is_symlink():
                    path.chmod(0o600)

    def prepare(self, action="stage", request_id="test-stage"):
        return self.coordinator.prepare(request_id=request_id, action=action, artifact_ref=self.reference)

    def test_changed_archive_or_manifest_cannot_reach_authority_or_filesystem(self):
        saved = self.prepare()
        original = self.bundle
        for changed in (replace(original, archive=original.archive + b"tamper"),
                        replace(original, manifest_json=original.manifest_json + b" ")):
            with self.subTest(changed_archive=changed.archive != original.archive):
                self.bundle = changed
                with self.assertRaises(PublicationError):
                    self.coordinator.apply(saved["request"]["request_digest"],
                                           lambda request: self.fail("tampered bundle reached authority"))
                self.assertEqual("prepared", self.store.get(saved["request"]["request_digest"])["phase"])
                self.assertFalse((self.target_root / "releases").exists())

    def test_tenant_and_repository_reference_mismatch_is_rejected_before_state_read(self):
        config = {"tenant_id": "test-tenant", "repository_id": "test-repository"}
        for field in ("tenant_id", "repository_id"):
            with self.subTest(field=field), self.assertRaisesRegex(PublicationError, "publication_artifact_scope"):
                landing_publication_cli._bundle(config, self.target, {**self.reference, field: "other"})

    def test_stage_observation_verifies_files_and_rejects_symlink_or_hardlink_replacement(self):
        saved = self.prepare()
        staged = self.coordinator.apply(saved["request"]["request_digest"], lambda request: "a" * 64)
        self.assertEqual("staged", staged["phase"])
        release = self.bundle.artifact_digest
        site = self.target_root / "releases" / release / "site"
        original = site / "index.html"
        body = original.read_bytes()
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                site.chmod(0o700)
                original.unlink()
                target = self.root / ("replacement-" + kind)
                target.write_bytes(body)
                target.chmod(0o400)
                if kind == "symlink":
                    original.symlink_to(target)
                else:
                    os.link(target, original)
                site.chmod(0o500)
                with self.assertRaises((PublicationError, OSError)):
                    self.adapter.observe(release)

    def test_pointer_failure_records_ambiguity_and_never_replays_on_reconcile(self):
        saved = self.prepare()
        self.assertEqual("staged", self.coordinator.apply(saved["request"]["request_digest"], lambda request: "a" * 64)["phase"])
        activation = self.prepare("activate", "test-activate")
        digest = activation["request"]["request_digest"]
        with patch("adaptive_delivery.landing_filesystem.os.replace", side_effect=OSError("pointer interrupted")):
            result = self.coordinator.apply(digest, lambda request: "b" * 64)
        self.assertEqual("needs_human", result["phase"])
        self.assertEqual("effect_ambiguous_no_replay", result["reason"])
        self.assertFalse((self.target_root / "current").exists())
        with patch.object(self.adapter, "activate", side_effect=AssertionError("reconcile replayed mutation")):
            self.assertEqual("needs_human", self.coordinator.reconcile(digest)["phase"])

    def test_committed_stage_and_activation_reconcile_after_store_restart_without_replay(self):
        for action, phase in (("stage", "staged"), ("activate", "activated")):
            with self.subTest(action=action):
                saved = self.prepare(action, "restart-" + action)
                digest = saved["request"]["request_digest"]
                effect = getattr(self.adapter, action)

                def interrupted_effect(*args):
                    effect(*args)
                    raise KeyboardInterrupt("effect committed before observation")

                with patch.object(self.adapter, action, side_effect=interrupted_effect):
                    with self.assertRaisesRegex(KeyboardInterrupt, "effect committed"):
                        self.coordinator.apply(digest, lambda request: "a" * 64)
                self.assertEqual("inflight", self.store.get(digest)["phase"])
                state = self.store.root
                self.store.close()
                self.store = PublicationStore(state)
                self.addCleanup(self.store.close)
                self.assertEqual("inflight", self.store.get(digest)["phase"])
                self.coordinator = LandingPublicationCoordinator(self.store, self.adapter, lambda reference: self.bundle)
                with (
                    patch.object(self.adapter, "stage", side_effect=AssertionError("stage replay")),
                    patch.object(self.adapter, "activate", side_effect=AssertionError("activate replay")),
                ):
                    result = self.coordinator.apply(digest, lambda request: self.fail("reconciliation requested authority"))
                self.assertEqual(phase, result["phase"])
                self.assertEqual("effect_observed", result["reason"])
                self.assertEqual("a" * 64, result["grant_digest"])
                self.assertFalse(result["http_origin_verified"])

    def test_restore_to_empty_baseline_requires_activated_lineage_and_exact_authority(self):
        staged = self.prepare()
        stage_digest = staged["request"]["request_digest"]
        self.coordinator.apply(stage_digest, lambda request: "a" * 64)
        with self.assertRaisesRegex(PublicationError, "publication_restore_chain"):
            self.coordinator.prepare(request_id="invalid-restore", action="restore", restore_from=stage_digest)
        activation = self.prepare("activate", "activate-before-restore")
        activation_digest = activation["request"]["request_digest"]
        self.coordinator.apply(activation_digest, lambda request: "b" * 64)
        restore = self.coordinator.prepare(request_id="restore-empty", action="restore", restore_from=activation_digest)
        request = PublicationRequestV1.from_dict(restore["request"])
        self.assertIsNone(request.desired_release)
        self.assertEqual(self.bundle.artifact_digest, request.baseline_release)
        seen = []

        def authority(value):
            seen.append(value.resource)
            return "c" * 64

        result = self.coordinator.apply(request.request_digest, authority)
        self.assertEqual([request.resource], seen)
        self.assertEqual("restored", result["phase"])
        self.assertIsNone(self.adapter.observe()["release_id"])
        self.assertFalse((self.target_root / "current").is_symlink())
        with self.assertRaisesRegex(PublicationError, "publication_restore_chain"):
            self.coordinator.prepare(request_id="stale-restore", action="restore", restore_from=activation_digest)

    def test_restore_returns_to_prior_release_and_rejects_stale_lineage(self):
        from adaptive_factory.landing_contracts import StaticLandingSpecV1
        from factory.tests.test_landing_renderer import landing_spec

        def apply(action, request_id):
            saved = self.prepare(action, request_id)
            return self.coordinator.apply(saved["request"]["request_digest"], lambda request: "a" * 64)

        first_release = self.bundle.artifact_digest
        apply("stage", "first-stage")
        first_activation = apply("activate", "first-activate")
        facts = landing_spec().to_dict()
        facts.pop("spec_digest")
        second_spec = StaticLandingSpecV1.from_facts({**facts, "title": "Second independently sealed release"})
        with patch("factory.tests.test_landing_artifact.landing_spec", return_value=second_spec):
            with candidate_fixture() as (source, candidate, attempt, evaluation):
                output = self.root / "second-artifacts"
                output.mkdir(mode=0o700)
                retained = LandingArtifactPackager(ExactGitLandingArtifactSource(source)).seal(
                    candidate, attempt, evaluation, output,
                )
                self.bundle = PublicationBundle(canonical_json(retained.artifact.to_dict()), retained.manifest_bytes,
                                                retained.zip_path.read_bytes(), retained.member_names)
        self.assertNotEqual(first_release, self.bundle.artifact_digest)
        apply("stage", "second-stage")
        second_activation = apply("activate", "second-activate")
        with self.assertRaisesRegex(PublicationError, "publication_restore_chain"):
            self.coordinator.prepare(request_id="wrong-release-restore", action="restore",
                                     restore_from=first_activation["request"]["request_digest"])
        restore = self.coordinator.prepare(request_id="restore-first", action="restore",
                                           restore_from=second_activation["request"]["request_digest"])
        self.assertEqual(first_release, restore["request"]["desired_release"])
        result = self.coordinator.apply(restore["request"]["request_digest"], lambda request: "b" * 64)
        self.assertEqual("restored", result["phase"])
        self.assertEqual(first_release, self.adapter.observe()["release_id"])
        self.assertTrue((self.target_root / "releases" / self.bundle.artifact_digest).is_dir())

    def test_synthetic_stale_foreign_and_duplicate_grants_cannot_advance_intent(self):
        saved = self.prepare()
        request = PublicationRequestV1.from_dict(saved["request"])
        config = {"route_id": "test-route", "change_id": "test-change"}
        now = datetime.now(timezone.utc)
        grant = {
            "schema_version": 2, "authorization": "delegated-local-grant",
            "repository": "Dimkox/adaptive-grok-build-pro", **config,
            "git_head": "c" * 40, "tree_fingerprint": "d" * 64,
            "scope": "external-write", "actions": ["external-write"], "resources": [request.resource],
            "source": "explicit-user-consent", "id": "e" * 16,
            "created_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(minutes=1)).isoformat(),
        }
        from adaptive_grok.state import SCOPE_ACTIONS
        self.assertEqual(set(grant["actions"]), SCOPE_ACTIONS[grant["scope"]])
        cases = [[{**grant, "expires_at": (now - timedelta(seconds=1)).isoformat()}],
                 [{**grant, "repository": "another/repository"}], [{**grant, "tree_fingerprint": "f" * 64}],
                 [{**grant, "resources": ["foreign-resource"]}], [grant, grant],
                 [{**grant, "scope": "production"}], [{**grant, "actions": ["external-write", "publish"]}],
                 [{**grant, "route_id": "other-route"}], [{**grant, "git_head": "f" * 40}],
                 [{**grant, "created_at": (now + timedelta(minutes=1)).isoformat()}],
                 [{**grant, "expires_at": (now + timedelta(days=2)).isoformat()}]]
        with ExitStack() as stack:
            stack.enter_context(patch("adaptive_grok.state.get_active_route", return_value=config))
            stack.enter_context(patch("adaptive_grok.state.get_active_change", return_value={"change_id": "test-change"}))
            stack.enter_context(patch("adaptive_grok.util.git_head", return_value="c" * 40))
            stack.enter_context(patch("adaptive_grok.util.git_output", return_value="https://github.com/Dimkox/adaptive-grok-build-pro.git"))
            stack.enter_context(patch("adaptive_grok.util.tree_fingerprint", return_value="d" * 64))
            with patch.object(grok_landing_publish, "read_private_file", return_value=json.dumps([grant]).encode()):
                self.assertEqual(64, len(grok_landing_publish._authority(config, self.root, request)))
            current_grant = {**grant, "grant_binding_digest": grant["tree_fingerprint"]}
            current_grant.pop("tree_fingerprint")
            with patch.object(grok_landing_publish, "read_private_file", return_value=json.dumps([current_grant]).encode()):
                self.assertEqual(64, len(grok_landing_publish._authority(config, self.root, request)))
            for grants in cases:
                with self.subTest(grants=grants), patch.object(
                    grok_landing_publish, "read_private_file", return_value=json.dumps(grants).encode(),
                ):
                    with self.assertRaisesRegex(PublicationError, "publication_exact_grant_unavailable"):
                        self.coordinator.apply(request.request_digest,
                                               lambda value: grok_landing_publish._authority(config, self.root, value))
                self.assertEqual("prepared", self.store.get(request.request_digest)["phase"])
                self.assertFalse((self.target_root / "releases").exists())

            for malformed in (
                {**current_grant, "grant_binding_digest": ""},
                {**current_grant, "grant_binding_digest": "not-a-digest", "tree_fingerprint": "d" * 64},
            ):
                with self.subTest(malformed=malformed), patch.object(
                    grok_landing_publish, "read_private_file", return_value=json.dumps([malformed]).encode(),
                ):
                    with self.assertRaisesRegex(PublicationError, "publication_exact_grant_unavailable"):
                        grok_landing_publish._authority(config, self.root, request)

    def test_direct_apply_requires_injected_authority_before_config_or_state_access(self):
        for authority in (None, "not-a-callback", object()):
            output = io.StringIO()
            with self.subTest(authority=authority), patch.object(
                landing_publication_cli, "_config", side_effect=AssertionError("config was accessed"),
            ), redirect_stdout(output):
                self.assertEqual(2, landing_publication_cli.main(
                    ["apply", "--live", "--config", "unused"], authority=authority,
                ))
            self.assertEqual("publication_authority_unavailable", json.loads(output.getvalue())["reason"])

    def test_authority_rejects_unavailable_control_identity_before_grant_read(self):
        request = PublicationRequestV1.from_dict(self.prepare()["request"])
        config = {"route_id": "test-route", "change_id": "test-change"}
        with ExitStack() as stack:
            stack.enter_context(patch("adaptive_grok.state.get_active_route", return_value=config))
            stack.enter_context(patch("adaptive_grok.state.get_active_change", return_value=config))
            stack.enter_context(patch("adaptive_grok.util.git_output", return_value="https://github.com/Dimkox/adaptive-grok-build-pro.git"))
            stack.enter_context(patch.object(grok_landing_publish, "read_private_file", side_effect=AssertionError("grant read before identity")))
            for head, fingerprint in ((None, "d" * 64), ("c" * 40, ""), ("invalid", "d" * 64)):
                with self.subTest(head=head, fingerprint=fingerprint), patch(
                    "adaptive_grok.util.git_head", return_value=head
                ), patch("adaptive_grok.util.tree_fingerprint", return_value=fingerprint):
                    with self.assertRaisesRegex(PublicationError, "publication_control_identity"):
                        grok_landing_publish._authority(config, self.root, request)

    def test_authority_rejects_github_suffix_hosts_and_accepts_exact_remote_forms(self):
        request = PublicationRequestV1.from_dict(self.prepare()["request"])
        config = {"route_id": "test-route", "change_id": "test-change"}
        with ExitStack() as stack:
            stack.enter_context(patch("adaptive_grok.state.get_active_route", return_value=config))
            stack.enter_context(patch("adaptive_grok.state.get_active_change", return_value=config))
            stack.enter_context(patch("adaptive_grok.util.git_head", return_value="c" * 40))
            stack.enter_context(patch("adaptive_grok.util.tree_fingerprint", return_value="d" * 64))
            stack.enter_context(patch.object(grok_landing_publish, "read_private_file", return_value=b"[]"))
            for prefix, expected in (
                ("https://github.com/", "publication_exact_grant_unavailable"),
                ("git@github.com:", "publication_exact_grant_unavailable"),
                ("ssh://git@github.com/", "publication_exact_grant_unavailable"),
                ("https://evilgithub.com/", "publication_control_repository"),
                ("https://github.com@evilgithub.com/", "publication_control_repository"),
            ):
                with self.subTest(prefix=prefix), patch("adaptive_grok.util.git_output", return_value=prefix + "Dimkox/adaptive-grok-build-pro.git"):
                    with self.assertRaisesRegex(PublicationError, expected):
                        grok_landing_publish._authority(config, self.root, request)

            with patch("adaptive_grok.util.git_output", return_value="https://github.com/Dimkox/adaptive-grok-build-pro.git.git"):
                with self.assertRaisesRegex(PublicationError, "publication_control_repository"):
                    grok_landing_publish._authority(config, self.root, request)

    def test_publication_paths_reject_double_slash_alias_before_read_or_open(self):
        alias = Path("/" + str(self.target_root))
        with self.assertRaisesRegex(PublicationError, "publication_target"):
            replace(self.target, root=str(alias))
        try:
            descriptor = private_root(alias)
        except PublicationError:
            pass
        else:
            os.close(descriptor)
            self.fail("private_root accepted ambiguous anchor")
        control = self.root / "control"
        control.mkdir(mode=0o700)
        config = {
            "schema_version": 1, "control_repository": str(control), "route_id": "route", "change_id": "change",
            "publication_state_root": str(self.root / "intent-state"), "landing_state_root": str(self.root / "landing-state"),
            "tenant_id": "tenant", "repository_id": "repository", "target": self.target.__dict__,
        }
        path = self.root / "config.json"
        path.write_bytes(canonical_json(config))
        path.chmod(0o600)
        for field in ("publication_state_root", "landing_state_root", "control_repository", "config_path"):
            changed = dict(config)
            selected_path, selected_control = path, control
            if field == "config_path":
                selected_path = Path("/" + str(path))
            else:
                changed[field] = "/" + changed[field]
                if field == "control_repository":
                    selected_control = Path(changed[field])
            path.write_bytes(canonical_json(changed))
            with self.subTest(field=field), self.assertRaises(PublicationError):
                landing_publication_cli._config(selected_path, selected_control)

    def test_repository_entrypoint_injects_authority_into_real_cli(self):
        saved = self.prepare()
        config = {"publication_state_root": str(self.root / "intent-state")}
        output = io.StringIO()
        with patch.object(landing_publication_cli, "_config", return_value=(config, self.target)), patch.object(
            landing_publication_cli, "_bundle", return_value=self.bundle
        ), patch("adaptive_delivery.landing_publication.PublicationStore", return_value=self.store), patch.object(
            grok_landing_publish, "_authority", return_value="a" * 64
        ), redirect_stdout(output):
            self.assertEqual(0, grok_landing_publish.main([
                "apply", "--live", "--config", "synthetic-config", "--request-digest", saved["request"]["request_digest"],
            ]))
        self.assertEqual("staged", json.loads(output.getvalue())["phase"])

    def test_sqlite_uri_roundtrip_preserves_special_characters_and_readonly_does_not_create(self):
        path = self.root / "state space%?#é"
        path.mkdir(mode=0o700)
        with self.assertRaisesRegex(PublicationError, "publication_state_unavailable"):
            PublicationStore(path, readonly=True)
        self.assertFalse((path / "publication.sqlite3").exists())
        self.assertFalse((path / ".intent-writer.lock").exists())
        store = PublicationStore(path)
        request = PublicationRequestV1.from_dict(self.prepare()["request"])
        store.prepare(request)
        store.close()
        reopened = PublicationStore(path, readonly=True)
        self.addCleanup(reopened.close)
        self.assertEqual(request.to_dict(), reopened.get(request.request_digest)["request"])


class PublicationStoreSchemaTests(unittest.TestCase):
    SCHEMA = """CREATE TABLE publication_intents (
        request_digest TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
        body BLOB NOT NULL, phase TEXT NOT NULL, observation BLOB,
        grant_digest TEXT, reason TEXT, updated_at TEXT NOT NULL
    ) STRICT"""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="publication-schema-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def database(self, name, schema=None, extra=None, identity=(0x4C355055, 1)):
        root = self.root / name
        root.mkdir(mode=0o700)
        path = root / "publication.sqlite3"
        with closing(sqlite3.connect(path)) as connection:
            connection.execute(schema or self.SCHEMA)
            if extra:
                connection.execute(extra)
            connection.execute(f"PRAGMA application_id={identity[0]}")
            connection.execute(f"PRAGMA user_version={identity[1]}")
            connection.commit()
        path.chmod(0o600)
        return root

    def test_supported_schema_reopens_and_unique_request_id_remains_idempotent(self):
        root = self.database("supported")
        request = PublicationRequestV1(
            1, "same-request", "stage", "a" * 64,
            {"tenant_id": "tenant", "repository_id": "repository", "job_id": "job"},
            "b" * 64, "b" * 64, "c" * 64, None, None,
        )
        store = PublicationStore(root)
        self.addCleanup(store.close)
        store.prepare(request)
        self.assertEqual(request.to_dict(), store.prepare(request)["request"])
        with self.assertRaisesRegex(PublicationError, "publication_idempotency_conflict"):
            store.prepare(replace(request, baseline_release="d" * 64, baseline_manifest="e" * 64))
        store.close()
        for readonly in (False, True):
            with self.subTest(readonly=readonly):
                reopened = PublicationStore(root, readonly=readonly)
                self.addCleanup(reopened.close)
                self.assertEqual(request.to_dict(), reopened.find_id(request.request_id)["request"])
                reopened.close()

    def test_conflict_policies_and_obfuscated_declarations_are_unsupported_in_both_modes(self):
        variants = {
            "unique-replace": self.SCHEMA.replace("UNIQUE", "UNIQUE ON CONFLICT REPLACE"),
            "unique-ignore": self.SCHEMA.replace("UNIQUE", "UNIQUE ON CONFLICT IGNORE"),
            "primary-replace": self.SCHEMA.replace("PRIMARY KEY", "PRIMARY KEY ON CONFLICT REPLACE"),
            "primary-ignore": self.SCHEMA.replace("PRIMARY KEY", "PRIMARY KEY ON CONFLICT IGNORE"),
            "block-comment": self.SCHEMA.replace("UNIQUE", "UNIQUE ON/**/CONFLICT REPLACE"),
            "line-comment": self.SCHEMA.replace("UNIQUE", "UNIQUE ON-- clause\n CONFLICT IGNORE"),
            "quoted-identifier": self.SCHEMA.replace("UNIQUE", "UNIQUE ON CONFLICT REPLACE").replace("request_id", '"request_id"'),
            "bracketed-identifier": self.SCHEMA.replace("UNIQUE", "UNIQUE ON CONFLICT IGNORE").replace("request_id", "[request_id]"),
        }
        for name, schema in variants.items():
            root = self.database(name, schema)
            for readonly in (False, True):
                with self.subTest(schema=name, readonly=readonly):
                    with self.assertRaisesRegex(PublicationError, "publication_state_schema"):
                        store = PublicationStore(root, readonly=readonly)
                        self.addCleanup(store.close)
                        store.close()

    def test_supported_declaration_preserves_case_and_whitespace_compatibility(self):
        root = self.database("formatted", self.SCHEMA.lower().replace("\n        ", "\n\t"))
        for readonly in (False, True):
            with self.subTest(readonly=readonly):
                store = PublicationStore(root, readonly=readonly)
                self.addCleanup(store.close)
                store.close()

    def test_changed_request_cannot_replace_an_existing_intent_under_altered_unique_policy(self):
        request = PublicationRequestV1(
            1, "immutable-request", "stage", "a" * 64,
            {"tenant_id": "tenant", "repository_id": "repository", "job_id": "job"},
            "b" * 64, "b" * 64, "c" * 64, None, None,
        )
        original = canonical_json(request.to_dict())
        for policy in ("REPLACE", "IGNORE"):
            with self.subTest(policy=policy):
                root = self.database("immutable-" + policy, self.SCHEMA.replace("UNIQUE", "UNIQUE ON CONFLICT " + policy))
                database = root / "publication.sqlite3"
                with closing(sqlite3.connect(database)) as connection:
                    connection.execute(
                        "INSERT INTO publication_intents (request_digest,request_id,body,phase,updated_at) VALUES (?,?,?,?,?)",
                        (request.request_digest, request.request_id, original, "prepared", "2026-09-13T00:00:00Z"),
                    )
                    connection.commit()
                with self.assertRaisesRegex(PublicationError, "publication_state_schema|publication_idempotency_conflict"):
                    store = PublicationStore(root)
                    self.addCleanup(store.close)
                    try:
                        store.prepare(replace(request, baseline_release="d" * 64, baseline_manifest="e" * 64))
                    finally:
                        store.close()
                with closing(sqlite3.connect(database)) as connection:
                    rows = connection.execute("SELECT request_digest,body,phase FROM publication_intents").fetchall()
                self.assertEqual([(request.request_digest, original, "prepared")], rows)

    def test_weaker_constraints_types_and_unexpected_schema_objects_fail_closed(self):
        cases = {
            "missing-unique": (self.SCHEMA.replace("NOT NULL UNIQUE", "NOT NULL"), None),
            "missing-primary": (self.SCHEMA.replace("TEXT PRIMARY KEY", "TEXT NOT NULL"), None),
            "nullable": (self.SCHEMA.replace("body BLOB NOT NULL", "body BLOB"), None),
            "wrong-type": (self.SCHEMA.replace("body BLOB", "body TEXT"), None),
            "default": (self.SCHEMA.replace("phase TEXT NOT NULL", "phase TEXT NOT NULL DEFAULT 'prepared'"), None),
            "not-strict": (self.SCHEMA.replace(") STRICT", ")"), None),
            "without-rowid": (self.SCHEMA.replace(") STRICT", ") STRICT, WITHOUT ROWID"), None),
            "collation": (self.SCHEMA.replace("NOT NULL UNIQUE", "NOT NULL COLLATE NOCASE UNIQUE"), None),
            "trigger": (self.SCHEMA, "CREATE TRIGGER publication_noop AFTER INSERT ON publication_intents BEGIN SELECT 1; END"),
            "internal-lookalike": (self.SCHEMA, "CREATE TRIGGER sqliteXpublication AFTER INSERT ON publication_intents BEGIN SELECT 1; END"),
            "view": (self.SCHEMA, "CREATE VIEW publication_view AS SELECT request_id FROM publication_intents"),
            "index": (self.SCHEMA, "CREATE INDEX publication_phase ON publication_intents(phase)"),
            "table": (self.SCHEMA, "CREATE TABLE publication_other (value TEXT) STRICT"),
        }
        for name, (schema, extra) in cases.items():
            root = self.database(name, schema, extra)
            for readonly in (False, True):
                with self.subTest(schema=name, readonly=readonly):
                    with self.assertRaisesRegex(PublicationError, "publication_state_schema"):
                        store = PublicationStore(root, readonly=readonly)
                        self.addCleanup(store.close)
                        store.close()

    def test_wrong_application_or_version_rejects_without_migration(self):
        for identity in ((0, 1), (0x4C355055, 0), (0x4C355055, 2)):
            root = self.database(f"identity-{identity[0]}-{identity[1]}", identity=identity)
            for readonly in (False, True):
                with self.subTest(identity=identity, readonly=readonly):
                    with self.assertRaisesRegex(PublicationError, "publication_state_identity"):
                        PublicationStore(root, readonly=readonly)
            with closing(sqlite3.connect(root / "publication.sqlite3")) as connection:
                self.assertEqual(identity, (
                    connection.execute("PRAGMA application_id").fetchone()[0],
                    connection.execute("PRAGMA user_version").fetchone()[0],
                ))


if __name__ == "__main__":
    unittest.main()
