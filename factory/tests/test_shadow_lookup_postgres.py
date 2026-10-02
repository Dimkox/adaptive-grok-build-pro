"""M7.1 SQL evidence tests; only the exact bound disposable PostgreSQL is allowed."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
import unittest
import uuid

from adaptive_factory import admin, store
from adaptive_factory.migrations import PostgresMigrator
from adaptive_factory.shadow_contracts import (
    MANUAL_HANDOFF_INSTRUCTIONS, OperatorHandoffProposalV1, ReadyForPrBundleV1, ShadowTaskEvidenceV1,
)
from adaptive_factory.shadow_lookup import (
    M7BundleRegistrationV1, M7LookupRequestV1, M7OutcomeObservationV1,
    M7CheckObservationV1, M7GitHubContextV1, M7EpochContextV1,
)
from factory.tests import test_postgres_integration as producer
from factory.tests.postgres_restart_probe import _assert_disposable_target
from factory.tests.test_shadow_lookup import measurements

DATABASE_URL = os.environ.get("FACTORY_TEST_DATABASE_URL")
TABLES = ("m7_bundles", "m7_outcomes", "m7_checks", "m7_contexts", "m7_command_results", "m7_source_bindings")


def assert_disposable():
    _assert_disposable_target(DATABASE_URL, os.environ.get("FACTORY_TEST_POSTGRES_CONTAINER", ""),
                             os.environ.get("FACTORY_TEST_POSTGRES_CONTAINER_ID", ""),
                             os.environ.get("FACTORY_TEST_POSTGRES_NONCE", ""))


def registration_from_producer(facts):
    published = facts["published"]
    binding = published.binding
    common = {name: getattr(binding, name) for name in ("task_id", "run_id", "owner", "role", "fence")}
    m5 = {
        "schema_version": 1, **common,
        **{name: getattr(binding, name) for name in (
            "repository_id", "legacy_intent_digest", "task_packet_digest", "run_manifest_digest",
            "workspace_snapshot_digest", "workspace_result_digest")},
        "authority_exact_head_sha": binding.input_head_sha, "snapshot_input_head_sha": binding.input_head_sha,
        "snapshot_result_head_sha": binding.exact_head_sha, "result_exact_head_sha": binding.exact_head_sha,
    }
    m6 = {
        "schema_version": 1, **common,
        **{name: m5[name] for name in ("repository_id", "legacy_intent_digest", "task_packet_digest",
                                      "run_manifest_digest", "workspace_snapshot_digest", "workspace_result_digest")},
        "binding_input_head_sha": binding.input_head_sha, "binding_exact_head_sha": binding.exact_head_sha,
        "subject_exact_head_sha": published.subject.exact_head_sha,
        "envelope_digest": published.envelope_digest, "binding_digest": binding.digest,
        "validation_inputs_digest": published.validation_inputs.digest, "subject_digest": published.subject.digest,
        "evidence_set_digest": facts["verdict_record"]["evidence_set_digest"],
        "verdict_digest": facts["verdict"].digest, "verdict": facts["verdict"].to_dict(),
    }
    evidence = ShadowTaskEvidenceV1.from_dict({
        "schema_version": 1,
        "m4": {"schema_version": 1, **common, "intent_digest": binding.legacy_intent_digest,
               "lease_packet_digest": binding.legacy_intent_digest}, "m5": m5, "m6": m6,
    })
    handoff = OperatorHandoffProposalV1.from_dict({
        "schema_version": 1, "subject_digest": evidence.digest, "external_capability": "absent",
        "recommended_action": "human_review", "instructions": list(MANUAL_HANDOFF_INSTRUCTIONS),
    })
    return M7BundleRegistrationV1(1, facts["task"].generation,
                                ReadyForPrBundleV1.from_components(evidence=evidence, operator_handoff=handoff), None)


@unittest.skipUnless(DATABASE_URL, "requires exact disposable PostgreSQL")
class M7AMigrationPostgresTests(unittest.TestCase):
    def test_populated_025_upgrade_idempotence_and_checksum_drift_refusal(self):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        from unittest.mock import patch
        from adaptive_factory.migrations import discover_migrations, MigrationError
        assert_disposable()
        name = "factory_m7_upgrade_" + str(os.getpid())
        available = discover_migrations()
        self.assertEqual(available[-1].version,26)
        owner = psycopg.connect(DATABASE_URL,autocommit=True)
        owner.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        url = make_conninfo(**{**conninfo_to_dict(DATABASE_URL),"dbname":name})
        try:
            migrator = PostgresMigrator(url)
            with patch("adaptive_factory.migrations.discover_migrations",return_value=available[:25]):
                self.assertEqual(len(migrator.apply()),25)
            with psycopg.connect(url) as connection:
                connection.execute("INSERT INTO factory.intake_identities VALUES('upgrade/repository','manual','preserved')")
            old = tuple((row.version,row.name,row.sha256) for row in migrator.status())
            self.assertEqual([row.version for row in migrator.apply()],[26])
            self.assertEqual(migrator.apply(),())
            self.assertEqual(tuple((row.version,row.name,row.sha256) for row in migrator.status()[:25]),old)
            with psycopg.connect(url) as connection:
                self.assertEqual(connection.execute("SELECT source_id FROM factory.intake_identities").fetchone()[0],"preserved")
                self.assertEqual(connection.execute("SELECT count(*) FROM factory.m7_source_bindings").fetchone()[0],0)
                connection.execute("UPDATE factory.schema_migrations SET sha256=%s WHERE version=26",("0" * 64,))
            with self.assertRaisesRegex(MigrationError,"drift"):
                migrator.apply()
        finally:
            assert_disposable()
            owner.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
            owner.close()

    def test_026_relations_and_isolated_roles_are_installed(self):
        import psycopg
        assert_disposable()
        PostgresMigrator(DATABASE_URL).apply()
        with psycopg.connect(DATABASE_URL) as connection:
            for name in TABLES:
                self.assertIsNotNone(connection.execute("SELECT to_regclass(%s)", ("factory." + name,)).fetchone()[0])
            rows = connection.execute("SELECT rolname,rolcanlogin,rolinherit FROM pg_roles WHERE rolname LIKE 'factory_m7_%' ORDER BY rolname").fetchall()
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(not row[1] and not row[2] for row in rows))

    def test_definers_are_owned_by_an_isolated_nonlogin_role(self):
        import psycopg
        assert_disposable()
        PostgresMigrator(DATABASE_URL).apply()
        with psycopg.connect(DATABASE_URL) as connection:
            rows = connection.execute("""SELECT r.rolname,r.rolcanlogin,r.rolsuper,p.proconfig,
                EXISTS(SELECT 1 FROM pg_catalog.aclexplode(p.proacl) a WHERE a.grantee=0)
                FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
                JOIN pg_catalog.pg_roles r ON r.oid=p.proowner
                WHERE n.nspname='factory' AND p.proname LIKE 'm7_%' AND p.prosecdef""").fetchall()
            self.assertTrue(rows)
            for owner, login, superuser, config, public in rows:
                self.assertEqual(owner, "factory_evidence_owner")
                self.assertFalse(login or superuser or public)
                self.assertIn("search_path=pg_catalog, factory, pg_temp", config)


@unittest.skipUnless(DATABASE_URL, "requires exact disposable PostgreSQL")
class M7LookupPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert_disposable()
        producer.PostgresFactoryTests.setUpClass()
        cls.logins = {}
        cls.urls = {}
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        for kind in ("registry", "outcome", "check_context", "reader"):
            login = "m7_" + kind + "_" + str(os.getpid())
            password = "synthetic-" + uuid.uuid4().hex
            admin.provision_m7_login(DATABASE_URL, login, password, capability_kind=kind)
            cls.logins[kind] = login
            cls.urls[kind] = make_conninfo(**{**conninfo_to_dict(DATABASE_URL), "user": login, "password": password})

    @classmethod
    def tearDownClass(cls):
        import psycopg
        from psycopg import sql
        with psycopg.connect(DATABASE_URL) as connection:
            for login in cls.logins.values():
                connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(login)))
        producer.PostgresFactoryTests.tearDownClass()

    def setUp(self):
        import psycopg
        self.producer = producer.PostgresFactoryTests("test_semantic_subject_publish_is_exact_replay_safe_and_role_isolated")
        self.producer.setUp()
        self.repository_id = "owner/repository"
        with psycopg.connect(DATABASE_URL) as connection:
            self.now = connection.execute("SELECT clock_timestamp()").fetchone()[0]
        self.configure_sources()
        self.registry = store.PostgresM7RegistryStore(self.urls["registry"], source_id="synthetic-registry", repository_id=self.repository_id)
        self.observer = store.PostgresM7OutcomeObserverStore(self.urls["outcome"], source_id="synthetic-human_outcome", repository_id=self.repository_id)
        self.reader = store.PostgresM7LookupStore(self.urls["reader"])

    def configure_sources(self):
        for source_kind, capability in (("registry", "registry"), ("human_outcome", "outcome"),
                                        ("signed_ci", "check_context"), ("github_current", "check_context"), ("deployed_epoch", "check_context")):
            for login_kind, bound_capability in ((capability, capability), ("reader", "reader")):
                admin.configure_m7_source(
                    DATABASE_URL, login=self.logins[login_kind], repository_id=self.repository_id,
                    source_id="synthetic-" + source_kind, capability_kind=bound_capability,
                    source_kind=source_kind, mode="synthetic", trust_config_digest="9" * 64,
                    valid_until=self.now + timedelta(hours=2), max_age_seconds=3600,
                )

    def register_completed(self, suffix="one"):
        facts = self.producer.semantic_repair_fixture(
            namespace="m7-" + suffix, source_id="m7-source-" + suffix,
            result_head_sha="4" * 40, semantic_pass=True,
        )
        self.assertEqual(facts["verdict"].decision, "pass")
        registration = registration_from_producer(facts)
        registered = self.registry.register_bundle(registration, idempotency_key="register-" + suffix)
        self.assertEqual(registered, registration)
        binding = facts["published"].binding
        request = M7LookupRequestV1.from_dict({
            "schema_version": 1, "repository_id": self.repository_id, "task_id": binding.task_id,
            "run_id": binding.run_id, "generation": registration.generation,
            "bundle_digest": registration.bundle.digest, "profile_digest": None,
            "pr_number": 7, "base_sha": binding.exact_base_sha, "head_sha": binding.exact_head_sha,
            "app_id": 7, "check_name": "synthetic-check", "policy_digest": "7" * 64, "holdout_digest": "8" * 64,
        })
        return registration, request

    def provenance(self, kind, revision=1, previous=None):
        return {"schema_version": 1, "source_id": "synthetic-" + kind, "source_kind": kind,
                "adapter_version": "synthetic-v1", "source_event_id": "event-" + str(revision),
                "source_revision": revision, "predecessor_digest": previous,
                "source_issued_at": self.now.isoformat(), "observed_at": self.now.isoformat(),
                "valid_until": (self.now + timedelta(hours=1)).isoformat(),
                "trust_config_digest": "9" * 64, "evidence_ref": "synthetic:evidence", "verifier_id": "synthetic-verifier"}

    def outcome(self, request, **overrides):
        return M7OutcomeObservationV1.from_dict({
            "schema_version": 1, "repository_id": self.repository_id, "bundle_digest": request.bundle_digest,
            "result_head_sha": request.head_sha, "decision": "accepted", "outcome": None,
            "profile": None, "measurements": measurements(), "provenance": self.provenance("human_outcome"), **overrides,
        })

    def test_completed_bundle_registration_replays_after_active_lease_clears(self):
        import psycopg
        registration, request = self.register_completed()
        with psycopg.connect(DATABASE_URL) as connection:
            active = connection.execute("SELECT current_run_id,current_fence FROM factory.tasks WHERE task_id=%s", (request.task_id,)).fetchone()
            self.assertEqual(active, (None, None))
        self.assertEqual(self.registry.register_bundle(registration, idempotency_key="register-one"), registration)
        self.assertEqual(self.reader.lookup(request).registration, registration)

    def test_partial_acceptance_exact_replay_and_conflicting_body(self):
        import psycopg
        _registration, request = self.register_completed()
        observation = self.outcome(request)
        self.assertEqual(self.observer.record_outcome(observation, idempotency_key="accept"), observation)
        self.assertEqual(self.observer.record_outcome(observation, idempotency_key="accept"), observation)
        result = self.reader.lookup(request)
        self.assertEqual(result.acceptance, "accepted")
        self.assertIsNone(result.outcome.outcome)
        self.assertEqual(result.coverage["measurements"], "unknown")
        changed = M7OutcomeObservationV1.from_dict({**observation.to_dict(), "decision": "rejected"})
        with self.assertRaises(store.IntegrityError):
            self.observer.record_outcome(changed, idempotency_key="accept")
        with psycopg.connect(DATABASE_URL) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM factory.m7_outcomes").fetchone()[0], 1)

    def test_wrong_generation_result_subject_and_runtime_direct_writes_fail(self):
        import psycopg
        registration, request = self.register_completed()
        changed = M7BundleRegistrationV1.from_dict({**registration.to_dict(), "generation": registration.generation + 1})
        with self.assertRaises(store.IntegrityError):
            self.registry.register_bundle(changed, idempotency_key="wrong-generation")
        wrong = self.outcome(request, result_head_sha="f" * 40)
        with self.assertRaises(store.IntegrityError):
            self.observer.record_outcome(wrong, idempotency_key="wrong-result")
        with self.producer.store._connect() as connection:
            for table in TABLES:
                with self.assertRaises(psycopg.errors.InsufficientPrivilege), connection.transaction():
                    connection.execute("DELETE FROM factory." + table)

    def test_source_and_repository_scope_are_checked_before_replay(self):
        registration, request = self.register_completed()
        observation = self.outcome(request)
        self.observer.record_outcome(observation, idempotency_key="accept")
        impostor = store.PostgresM7OutcomeObserverStore(self.urls["reader"], source_id=observation.provenance.source_id, repository_id=self.repository_id)
        with self.assertRaises(store.StoreError):
            impostor.record_outcome(observation, idempotency_key="accept")
        other = store.PostgresM7OutcomeObserverStore(self.urls["outcome"], source_id="other-source", repository_id=self.repository_id)
        with self.assertRaises(store.StoreError):
            other.record_outcome(observation, idempotency_key="accept")
        cross = store.PostgresM7RegistryStore(self.urls["registry"], source_id="synthetic-registry", repository_id="other/repository")
        with self.assertRaises(store.StoreError):
            cross.register_bundle(registration, idempotency_key="register-one")

    def context_store(self, kind):
        return store.PostgresM7CheckContextObserverStore(self.urls["check_context"],
            source_id="synthetic-" + kind, repository_id=self.repository_id)

    def check(self, request, **overrides):
        return M7CheckObservationV1.from_dict({"schema_version": 1, "repository_id": self.repository_id,
            **{key: getattr(request, key) for key in ("pr_number", "base_sha", "head_sha", "policy_digest", "holdout_digest")},
            "external_job_id": "synthetic-job", "attestation_digest": "a" * 64, "signer_key_id": "synthetic-signer",
            "result": "passed", "provenance": self.provenance("signed_ci"), **overrides})

    def github(self, request, **overrides):
        return M7GitHubContextV1.from_dict({"schema_version": 1, "repository_id": self.repository_id,
            **{key: getattr(request, key) for key in ("pr_number", "base_sha", "head_sha", "app_id", "check_name")},
            "external_job_id": "synthetic-job", "check_id": 71, "check_state": "completed",
            "check_conclusion": "success", "revoked": False, "provenance": self.provenance("github_current"), **overrides})

    def epoch(self, request, **overrides):
        return M7EpochContextV1.from_dict({"schema_version": 1, "repository_id": self.repository_id,
            **{key: getattr(request, key) for key in ("policy_digest", "holdout_digest", "app_id", "check_name")},
            "revoked": False, "provenance": self.provenance("deployed_epoch"), **overrides})

    def all_green(self, request):
        outcome, check, github, epoch = self.outcome(request), self.check(request), self.github(request), self.epoch(request)
        self.observer.record_outcome(outcome)
        self.context_store("signed_ci").record_check(check)
        self.context_store("github_current").record_context(github)
        self.context_store("deployed_epoch").record_context(epoch)
        result = self.reader.lookup(request)
        self.assertEqual((result.acceptance, result.signed_check, result.currentness), ("accepted", "valid", "current"))
        self.assertEqual(result.to_dict()["authority_effect"], "none")
        self.assertEqual(result.to_dict()["m8_qualification"], "not_evaluated")
        return outcome, check, github, epoch

    def test_latest_context_selected_before_requested_old_green_tuple(self):
        _registration, request = self.register_completed()
        _outcome, _check, github, epoch = self.all_green(request)
        changed = self.epoch(request, policy_digest="b" * 64,
                             provenance=self.provenance("deployed_epoch", 2, epoch.digest))
        self.context_store("deployed_epoch").record_context(changed)
        result = self.reader.lookup(request)
        self.assertEqual(result.epoch, changed)
        self.assertEqual(result.currentness, "stale")
        moved = self.github(request, head_sha="f" * 40, base_sha="e" * 40,
                            provenance=self.provenance("github_current", 2, github.digest))
        self.context_store("github_current").record_context(moved)
        result = self.reader.lookup(request)
        self.assertEqual(result.github.head_sha, "f" * 40)
        self.assertEqual(result.currentness, "stale")

    def test_latest_selector_metadata_corruption_never_falls_back(self):
        import psycopg
        _registration, request = self.register_completed()
        _outcome, _check, github, _epoch = self.all_green(request)
        moved = self.github(request, head_sha="f" * 40,
            provenance=self.provenance("github_current", 2, github.digest))
        self.context_store("github_current").record_context(moved)
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("ALTER TABLE factory.m7_contexts DISABLE TRIGGER m7_contexts_immutable")
            connection.execute("UPDATE factory.m7_contexts SET pr_number=8 WHERE observation_digest=%s", (moved.digest,))
            connection.execute("ALTER TABLE factory.m7_contexts ENABLE TRIGGER m7_contexts_immutable")
        result = self.reader.lookup(request)
        self.assertIsNone(result.github)
        self.assertIn("github_corrupt", result.unavailable_reasons)

    def test_withdrawal_check_revocation_and_exact_old_replay_never_restore_green(self):
        _registration, request = self.register_completed()
        outcome, check, _github, _epoch = self.all_green(request)
        withdrawn = self.outcome(request, decision="withdrawn", provenance=self.provenance("human_outcome", 2, outcome.digest))
        revoked = self.check(request, result="revoked", provenance=self.provenance("signed_ci", 2, check.digest))
        self.observer.record_outcome(withdrawn)
        self.context_store("signed_ci").record_check(revoked)
        self.assertEqual(self.observer.record_outcome(outcome), outcome)
        self.assertEqual(self.context_store("signed_ci").record_check(check), check)
        result = self.reader.lookup(request)
        self.assertEqual((result.acceptance, result.signed_check, result.currentness), ("withdrawn", "invalid", "stale"))
        self.assertIn("check_revoked", result.unavailable_reasons)

    def test_source_stream_conflicts_are_atomic_and_ordered_under_concurrency(self):
        import psycopg
        _registration, request = self.register_completed()
        original = self.outcome(request)
        changed = self.outcome(request, decision="rejected")
        def attempt(value):
            try:
                return self.observer.record_outcome(value, idempotency_key="race")
            except store.IntegrityError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, (original, changed)))
        self.assertEqual(sum(value is not None for value in results), 1)
        with psycopg.connect(DATABASE_URL) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM factory.m7_outcomes").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT count(*) FROM factory.m7_command_results WHERE operation='human_outcome'").fetchone()[0], 1)
        for provenance in (self.provenance("human_outcome", 3, original.digest), self.provenance("human_outcome", 2, "f" * 64)):
            with self.assertRaises(store.IntegrityError):
                self.observer.record_outcome(self.outcome(request, provenance=provenance))

    def test_latest_expired_observation_does_not_fall_back_to_older_green(self):
        _registration, request = self.register_completed()
        _outcome, _check, _github, epoch = self.all_green(request)
        # Advance the database time, keeping source order monotonic; the newest record is already expired.
        expired_provenance = {**self.provenance("deployed_epoch", 2, epoch.digest),
                              "valid_until": (self.now + timedelta(microseconds=1)).isoformat()}
        expired = self.epoch(request, provenance=expired_provenance)
        self.context_store("deployed_epoch").record_context(expired)
        result = self.reader.lookup(request)
        self.assertIsNone(result.epoch)
        self.assertEqual(result.currentness, "unavailable")
        self.assertIn("epoch_expired", result.unavailable_reasons)

    def test_disable_source_and_same_name_recreated_login_cannot_reuse_scope(self):
        import psycopg
        from psycopg import sql
        _registration, request = self.register_completed()
        self.all_green(request)
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("UPDATE factory.m7_source_bindings SET enabled=false WHERE capability_kind='check_context' AND source_kind='deployed_epoch'")
        self.assertEqual(self.reader.lookup(request).currentness, "unavailable")
        login = "m7_oid_probe_" + str(os.getpid())
        password = "synthetic-" + uuid.uuid4().hex
        admin.provision_m7_login(DATABASE_URL, login, password, capability_kind="outcome")
        admin.configure_m7_source(DATABASE_URL, login=login, repository_id=self.repository_id, source_id="oid-source",
            capability_kind="outcome", source_kind="human_outcome", mode="synthetic", trust_config_digest="9" * 64,
            valid_until=self.now + timedelta(hours=1), max_age_seconds=3600)
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(login)))
        admin.provision_m7_login(DATABASE_URL, login, password, capability_kind="outcome")
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        url = make_conninfo(**{**conninfo_to_dict(DATABASE_URL), "user": login, "password": password})
        impostor = store.PostgresM7OutcomeObserverStore(url, source_id="oid-source", repository_id=self.repository_id)
        try:
            observation = self.outcome(request, provenance={**self.provenance("human_outcome"), "source_id": "oid-source"})
            with self.assertRaises(store.StoreError):
                impostor.record_outcome(observation)
        finally:
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(login)))

    def test_interrupted_observation_transaction_leaves_no_row_or_replay(self):
        import psycopg
        _registration, request = self.register_completed()
        observation = self.outcome(request)
        with self.observer._connect() as connection:
            connection.execute("SELECT factory.m7_observe(%s,%s,%s,%s,%s)",
                (self.observer.source_id, self.repository_id, "interrupted", "human_outcome", self.observer._canonical(observation)))
            connection.rollback()
        with psycopg.connect(DATABASE_URL) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM factory.m7_outcomes").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT count(*) FROM factory.m7_command_results WHERE operation='human_outcome'").fetchone()[0], 0)
        self.assertEqual(self.observer.record_outcome(observation, idempotency_key="interrupted"), observation)

    def test_corrupted_stored_observation_digest_cannot_become_acceptance(self):
        import psycopg
        _registration, request = self.register_completed()
        self.observer.record_outcome(self.outcome(request, decision="rejected"))
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("ALTER TABLE factory.m7_outcomes DISABLE TRIGGER m7_outcomes_immutable")
            connection.execute("UPDATE factory.m7_outcomes SET body=jsonb_set(body,'{decision}','\"accepted\"')")
            connection.execute("ALTER TABLE factory.m7_outcomes ENABLE TRIGGER m7_outcomes_immutable")
        result = self.reader.lookup(request)
        self.assertEqual(result.acceptance, "unavailable")
        self.assertIn("outcome_corrupt", result.unavailable_reasons)

    def test_direct_sql_rejects_closed_contract_forgery_and_unsafe_capability(self):
        import psycopg
        _registration, request = self.register_completed()
        observation = self.outcome(request)
        for changes in ({"schema_version": True}, {"caller_is_trusted": True},
                        {"measurements": {**measurements(), "intervention_count": 0}}):
            with self.assertRaises(psycopg.errors.RaiseException), self.observer._connect() as connection:
                connection.execute("SELECT factory.m7_observe(%s,%s,%s,%s,%s)",
                    (self.observer.source_id, self.repository_id, "forged", "human_outcome",
                     json.dumps({**observation.to_dict(), **changes}, sort_keys=True, separators=(",", ":"))))
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("GRANT SELECT ON factory.m7_outcomes TO factory_m7_outcome")
        try:
            with self.assertRaises(store.StoreError):
                self.observer.record_outcome(observation)
        finally:
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute("REVOKE SELECT ON factory.m7_outcomes FROM factory_m7_outcome")

    def test_superseded_task_invalidates_registered_material_and_late_outcome(self):
        import psycopg
        _registration, request = self.register_completed()
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("UPDATE factory.tasks SET state='superseded',generation=generation+1 WHERE task_id=%s", (request.task_id,))
        result = self.reader.lookup(request)
        self.assertIsNone(result.registration)
        self.assertIn("producer_stale", result.unavailable_reasons)
        with self.assertRaises(store.IntegrityError):
            self.observer.record_outcome(self.outcome(request))

    def test_scope_conflict_imported_sources_and_lookup_indexes(self):
        import psycopg
        _registration, request = self.register_completed()
        self.all_green(request)
        admin.configure_m7_source(DATABASE_URL, login=self.logins["reader"], repository_id=self.repository_id,
            source_id="second-epoch", capability_kind="reader", source_kind="deployed_epoch", mode="synthetic",
            trust_config_digest="9" * 64, valid_until=self.now + timedelta(hours=1), max_age_seconds=3600)
        result = self.reader.lookup(request)
        self.assertEqual(result.currentness, "conflict")
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("DELETE FROM factory.m7_source_bindings WHERE source_id='second-epoch'")
            connection.execute("UPDATE factory.m7_source_bindings SET mode='imported' WHERE source_kind='human_outcome'")
            connection.execute("SET enable_seqscan=off")
            plan = connection.execute("EXPLAIN SELECT body FROM factory.m7_contexts WHERE repository_id=%s AND pr_number=7 AND source_kind='github_current' AND source_id='synthetic-github_current' ORDER BY source_revision DESC LIMIT 1", (self.repository_id,)).fetchall()
            self.assertIn("m7_context_latest", " ".join(row[0] for row in plan))
        self.assertEqual(self.reader.lookup(request).acceptance, "unavailable")

    def test_outcome_write_serializes_with_cancellation(self):
        import psycopg
        _registration, request = self.register_completed()
        observation = self.outcome(request)
        with self.observer._connect() as pending:
            pending.execute("SELECT factory.m7_observe(%s,%s,%s,%s,%s)",
                (self.observer.source_id, self.repository_id, "cancel-race", "human_outcome", self.observer._canonical(observation)))
            with self.assertRaises(psycopg.errors.LockNotAvailable), psycopg.connect(DATABASE_URL) as cancellation:
                cancellation.execute("SET lock_timeout='30ms'")
                cancellation.execute("UPDATE factory.tasks SET state='cancelled' WHERE task_id=%s", (request.task_id,))
            pending.rollback()
        with psycopg.connect(DATABASE_URL) as cancellation:
            cancellation.execute("UPDATE factory.tasks SET state='cancelled' WHERE task_id=%s", (request.task_id,))
        with self.assertRaises(store.IntegrityError):
            self.observer.record_outcome(observation, idempotency_key="cancel-race")

    def test_corrupt_m4_intent_body_invalidates_completed_registry(self):
        import psycopg
        _registration, request = self.register_completed()
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("UPDATE factory.accepted_intents SET body=jsonb_set(body,'{request_id}','\"synthetic-corrupt\"') WHERE intent_id=(SELECT intent_id FROM factory.tasks WHERE task_id=%s)", (request.task_id,))
        self.assertIsNone(self.reader.lookup(request).registration)

    def test_sql_registry_recomputes_terminal_proposal_before_replay(self):
        import psycopg
        registration, request = self.register_completed()
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("UPDATE factory.execution_proposals SET body=jsonb_set(body,'{summary}','\"synthetic-corrupt\"') WHERE run_id=%s AND proposal_kind='terminal'", (request.run_id,))
        with self.assertRaises(psycopg.errors.RaiseException), self.registry._connect() as connection:
            connection.execute("SELECT factory.m7_register(%s,%s,%s,%s)",
                (self.registry.source_id, self.repository_id, "register-one", self.registry._canonical(registration)))

    def test_lookup_base_sha_is_bound_to_the_completed_producer(self):
        _registration, request = self.register_completed()
        wrong = M7LookupRequestV1.from_dict({**request.to_dict(), "base_sha": "f" * 40})
        self.assertIsNone(self.reader.lookup(wrong).registration)

    def test_sql_unicode_digest_and_atomic_decomposed_refusal(self):
        import psycopg
        from adaptive_factory.contracts import ContractError
        from adaptive_factory.shadow_lookup import canonical_m7_bytes, m7_digest
        _registration, request = self.register_completed()
        request = M7LookupRequestV1.from_dict({**request.to_dict(), "check_name": "caf\u00e9"})
        self.all_green(request)
        original = self.github(request)
        canonical = canonical_m7_bytes(original.to_dict()).decode("utf-8")
        with psycopg.connect(DATABASE_URL) as connection:
            digest = connection.execute("SELECT factory.m7_hash(%s,%s::text)",
                (original.DOMAIN, canonical)).fetchone()[0]
            self.assertEqual(digest, m7_digest(original.DOMAIN, original.to_dict()))
            before = connection.execute("SELECT count(*) FROM factory.m7_contexts").fetchone()[0]
        for invalid in ("cafe\u0301", "x\u007f", "x\u0085", "\u00e9" * 129):
            wire = {**original.to_dict(), "check_name": invalid}
            with self.subTest(invalid=invalid[:8]):
                with self.assertRaises(ContractError):
                    M7GitHubContextV1.from_dict(wire)
                with self.assertRaises(psycopg.errors.RaiseException), self.context_store("github_current")._connect() as connection:
                    connection.execute("SELECT factory.m7_observe(%s,%s,%s,%s,%s)",
                        (original.provenance.source_id, self.repository_id, "unicode-refusal", "github_current",
                         json.dumps(wire,sort_keys=True,separators=(",", ":"),ensure_ascii=False)))
        with psycopg.connect(DATABASE_URL) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM factory.m7_contexts").fetchone()[0],before)
        for references in (["z", "a"],["a", "a"]):
            wire = self.outcome(request).to_dict()
            wire["measurements"].update(intervention_coverage="partial",intervention_count=0,
                intervention_source_refs=references)
            with self.subTest(references=references), self.assertRaises(psycopg.errors.RaiseException), self.observer._connect() as connection:
                connection.execute("SELECT factory.m7_observe(%s,%s,%s,%s,%s)",
                    (self.observer.source_id,self.repository_id,"reference-refusal","human_outcome",
                     json.dumps(wire,sort_keys=True,separators=(",", ":"),ensure_ascii=False)))

    def test_writer_binding_ambiguity_is_refused(self):
        import psycopg
        from psycopg import sql
        _registration, request = self.register_completed()
        self.all_green(request)
        login = "m7_ambiguous_" + str(os.getpid())
        admin.provision_m7_login(DATABASE_URL,login,"synthetic-ambiguity-password",capability_kind="check_context")
        try:
            admin.configure_m7_source(DATABASE_URL,login=login,repository_id=self.repository_id,
                source_id="synthetic-deployed_epoch",capability_kind="check_context",source_kind="deployed_epoch",
                mode="synthetic",trust_config_digest="9" * 64,valid_until=self.now+timedelta(hours=1),max_age_seconds=3600)
            result = self.reader.lookup(request)
            self.assertIsNone(result.epoch)
            self.assertEqual(result.lookup_outcome,"ambiguous")
        finally:
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(login)))

    def test_repository_qualifies_source_event_and_replay_identity(self):
        import psycopg
        _registration, request = self.register_completed()
        first = self.epoch(request)
        self.context_store("deployed_epoch").record_context(first,idempotency_key="same-replay")
        repository = "second/repository"
        for capability, login_kind in (("check_context","check_context"),("reader","reader")):
            admin.configure_m7_source(DATABASE_URL,login=self.logins[login_kind],repository_id=repository,
                source_id=first.provenance.source_id,capability_kind=capability,source_kind="deployed_epoch",mode="synthetic",
                trust_config_digest="9" * 64,valid_until=self.now+timedelta(hours=1),max_age_seconds=3600)
        second = M7EpochContextV1.from_dict({**first.to_dict(),"repository_id":repository})
        observer = store.PostgresM7CheckContextObserverStore(self.urls["check_context"],
            source_id=first.provenance.source_id,repository_id=repository)
        self.assertEqual(observer.record_context(second,idempotency_key="same-replay"),second)
        self.assertEqual(observer.record_context(second,idempotency_key="same-replay"),second)
        self.assertEqual(self.context_store("deployed_epoch").record_context(first,idempotency_key="same-replay"),first)
        with psycopg.connect(DATABASE_URL) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM factory.m7_contexts").fetchone()[0],2)
            self.assertEqual(connection.execute("SELECT count(*) FROM factory.m7_command_results WHERE operation='deployed_epoch'").fetchone()[0],2)

    def test_canonical_latest_index_with_populated_history(self):
        import psycopg
        _registration, request = self.register_completed()
        previous = None
        observer = self.context_store("deployed_epoch")
        for revision in range(1,81):
            value = self.epoch(request, provenance=self.provenance("deployed_epoch",revision,previous))
            observer.record_context(value)
            previous = value.digest
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("ANALYZE factory.m7_contexts")
            plan = connection.execute("""EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT body FROM factory.m7_contexts
                WHERE lookup_repository=%s AND lookup_pr=0 AND lookup_kind='deployed_epoch'
                  AND lookup_source='synthetic-deployed_epoch' ORDER BY lookup_revision DESC LIMIT 1""",(self.repository_id,)).fetchone()[0][0]
            self.assertIn("m7_context_canonical_latest",json.dumps(plan))
            self.assertLessEqual(plan["Plan"]["Actual Rows"],1)
            print("M7 populated EXPLAIN:",json.dumps(plan,sort_keys=True))
        for kind, relation, value_builder, method, index, condition, arguments in (
            ("human_outcome","m7_outcomes",self.outcome,self.observer.record_outcome,"m7_outcome_canonical_latest",
             "lookup_repository=%s AND lookup_bundle=%s AND lookup_source='synthetic-human_outcome'",(self.repository_id,request.bundle_digest)),
            ("signed_ci","m7_checks",self.check,self.context_store("signed_ci").record_check,"m7_check_canonical_latest",
             "lookup_repository=%s AND lookup_pr=7 AND lookup_source='synthetic-signed_ci'",(self.repository_id,)),
        ):
            previous = None
            for revision in range(1,41):
                value = value_builder(request,provenance=self.provenance(kind,revision,previous))
                method(value)
                previous = value.digest
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute("ANALYZE factory."+relation)
                plan = connection.execute("EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT body FROM factory."+
                    relation+" WHERE "+condition+" ORDER BY lookup_revision DESC LIMIT 1",arguments).fetchone()[0][0]
                self.assertIn(index,json.dumps(plan))
                self.assertEqual(plan["Plan"]["Actual Rows"],1)
                print("M7 populated EXPLAIN:",json.dumps(plan,sort_keys=True))

    def test_each_selected_metadata_field_and_replay_body_is_bound(self):
        import psycopg
        from psycopg import sql
        _registration, request = self.register_completed()
        original = self.outcome(request)
        self.observer.record_outcome(original,idempotency_key="metadata")
        changes = {"source_event_id":"substituted", "source_revision":2, "predecessor_digest":"f" * 64,
                   "source_mode":"imported", "stream_key":"wrong-stream", "binding_digest":"f" * 64,
                   "repository_id":"wrong/repository", "observed_at":self.now+timedelta(seconds=10),
                   "valid_until":self.now+timedelta(hours=2), "selector_digest":"f" * 64}
        with psycopg.connect(DATABASE_URL) as connection:
            for field, changed in changes.items():
                with self.subTest(field=field):
                    query = sql.SQL("UPDATE factory.m7_outcomes SET {}=%s WHERE observation_digest=%s").format(sql.Identifier(field))
                    previous = connection.execute(sql.SQL("SELECT {} FROM factory.m7_outcomes WHERE observation_digest=%s").format(sql.Identifier(field)),(original.digest,)).fetchone()[0]
                    connection.execute("ALTER TABLE factory.m7_outcomes DISABLE TRIGGER m7_outcomes_immutable")
                    connection.execute(query,(changed,original.digest))
                    connection.commit()
                    result = self.reader.lookup(request)
                    self.assertIsNone(result.outcome)
                    self.assertEqual(result.lookup_outcome,"invalid")
                    connection.execute(query,(previous,original.digest))
                    connection.execute("ALTER TABLE factory.m7_outcomes ENABLE TRIGGER m7_outcomes_immutable")
                    connection.commit()
            connection.execute("ALTER TABLE factory.m7_command_results DISABLE TRIGGER m7_command_results_immutable")
            connection.execute("UPDATE factory.m7_command_results SET response_body=jsonb_set(response_body,'{decision}','\"accepted\"'),response_canonical='{}' WHERE operation='human_outcome'")
            connection.execute("ALTER TABLE factory.m7_command_results ENABLE TRIGGER m7_command_results_immutable")
        with self.assertRaises(store.IntegrityError):
            self.observer.record_outcome(original,idempotency_key="metadata")
