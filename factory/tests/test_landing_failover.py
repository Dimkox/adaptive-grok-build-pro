"""Actual caller journal and orchestration with deterministic isolated backend doubles."""

from pathlib import Path
import tempfile
import unittest

from adaptive_factory.landing_http import HttpLandingProfile
from adaptive_factory.landing_renderer import TARGET_BASE_SHA, TARGET_BASE_TREE, TARGET_REPOSITORY_ID
from adaptive_factory.landing_contracts import LandingProviderEvidenceV2, SiteArtifactV1
from adaptive_factory.landing_observation import LandingProviderObservation
from adaptive_factory.landing_service import LandingJobRecord
from adaptive_factory.landing_failover_contracts import attempt_receipt, backend_capability
from factory.tests.test_landing_contracts import provider_facts, artifact_facts
from factory.tests.test_landing_sqlite_store import source


def configuration(root, count=5):
    profiles = ("qwen-intl", "grok-vision", "openai", "anthropic", "openrouter")[:count]
    for name in ("journal", "source", "control", "run", "credentials"):
        (root / name).mkdir(mode=0o700, exist_ok=True)
    return {
        "schema_version": 1, "control_repository": str(root / "control"),
        "source_path": str(root / "source"), "journal_path": str(root / "journal"),
        "actor_id": "tenant-1", "repository_id": TARGET_REPOSITORY_ID,
        "exact_base_sha": TARGET_BASE_SHA, "exact_base_tree": TARGET_BASE_TREE,
        "deadline_seconds": 900, "retention_seconds": 3600,
        "backends": [{"profile_id": item, "socket_path": str(root / "run" / (item + ".sock")),
                      "token_file": str(root / "credentials" / (item + ".token")),
                      "profile_digest": HttpLandingProfile.for_provider(item, available=True).profile_digest}
                     for item in profiles],
    }


class ScriptedBackends:
    def __init__(self, outcomes):
        self.outcomes, self.calls, self.records = outcomes, [], {}

    def factory(self, backend, *, config, **kwargs):
        owner = self
        class Client:
            def capability(self):
                return backend_capability(HttpLandingProfile.for_provider(backend.profile_id, available=True),
                                          config.actor_id, config.repository_id, config.exact_base_sha, config.exact_base_tree)
            def submit(self, child_id, payload, media_type):
                from adaptive_factory.landing_failover_transport import BackendAmbiguous, BackendRejected
                owner.calls.append(backend.profile_id)
                outcome = owner.outcomes[backend.profile_id]
                if outcome == "local_auth":
                    raise BackendRejected("authorization")
                profile = HttpLandingProfile.for_provider(backend.profile_id, available=True)
                item = source(job_id=child_id, payload=payload)
                success = outcome in {"success", "lost_success", "renderer"}
                category = "normalized" if success else outcome
                evidence = LandingProviderEvidenceV2.from_facts(provider_facts(
                    schema_version=2, provider_id=profile.provider_id, model_id=profile.model_id,
                    profile_digest=profile.profile_digest, input_digest=item.input_digest,
                    adapter_id=profile.adapter_id, adapter_version=profile.adapter_version,
                    decoder_digest=profile.decoder_digest,
                    disposition="normalized" if success else "provider_unavailable",
                ))
                observation = LandingProviderObservation(evidence, category, True,
                    "reported" if success else "unavailable", 12 if success else None, 34 if success else None)
                artifact = SiteArtifactV1.from_facts(artifact_facts(
                    source_sha=item.exact_base_sha, source_tree=item.exact_base_tree,
                    input_digest=item.input_digest, profile_digest=profile.profile_digest,
                )) if outcome in {"success", "lost_success"} else None
                state = "artifact_ready" if artifact else "needs_human"
                owner.records[child_id] = attempt_receipt(LandingJobRecord(
                    item, state, artifact, evidence.provider_evidence_digest, observation=observation,
                ))
                if outcome == "lost_success":
                    raise BackendAmbiguous("lost_reply")
            def observe(self, child_id):
                return owner.records[child_id]
            def close(self):
                pass
        return Client()


class CallerRoutingTests(unittest.TestCase):
    def run_script(self, outcomes):
        from adaptive_factory.landing_failover import FailoverCoordinator
        from adaptive_factory.landing_failover_config import FailoverConfig
        from adaptive_factory.landing_failover_journal import CallerJournal
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        config = FailoverConfig.from_dict(configuration(Path(temporary.name)))
        journal = CallerJournal(config)
        self.addCleanup(journal.close)
        script = ScriptedBackends(outcomes)
        caller = FailoverCoordinator(config, journal, backend_factory=script.factory)
        return caller.submit("parent-1", b"A bounded brief", "text/plain"), caller, script

    def test_primary_success_and_lost_success_both_select_original_artifact_without_fallback(self):
        for outcome in ("success", "lost_success"):
            with self.subTest(outcome=outcome):
                result, caller, script = self.run_script({"qwen-intl": outcome})
                self.assertEqual("artifact_ready", result["state"])
                self.assertEqual("qwen", result["winner"]["provider_id"])
                self.assertEqual(["qwen-intl"], script.calls)
                self.assertEqual(result, caller.submit("parent-1", b"A bounded brief", "text/plain"))
                self.assertEqual(["qwen-intl"], script.calls)

    def test_each_confirmed_availability_failure_permits_one_next_provider(self):
        for category in ("authentication", "rate_limit", "unavailable", "transport", "deadline"):
            with self.subTest(category=category):
                result, _, script = self.run_script({"qwen-intl": category, "grok-vision": "success"})
                self.assertEqual("artifact_ready", result["state"])
                self.assertEqual(["qwen-intl", "grok-vision"], script.calls)
                self.assertEqual("grok", result["winner"]["provider_id"])
                self.assertEqual({"known_input_units": 12, "known_output_units": 34,
                                  "unknown_attempts": 1, "complete": False,
                                  "cost_usd": None, "cache_breakdown": None}, result["usage"])
                sources = [item["receipt"]["source"] for item in result["attempts"]]
                self.assertNotEqual(sources[0]["input_digest"], sources[1]["input_digest"])
                self.assertEqual(sources[0]["content_sha256"], sources[1]["content_sha256"])

    def test_full_chain_has_five_attempts_and_retains_the_actual_openrouter_winner(self):
        result, _, script = self.run_script({"qwen-intl": "unavailable", "grok-vision": "authentication",
                                             "openai": "rate_limit", "anthropic": "deadline", "openrouter": "success"})
        self.assertEqual(["qwen-intl", "grok-vision", "openai", "anthropic", "openrouter"], script.calls)
        self.assertEqual("openrouter", result["winner"]["provider_id"])
        self.assertEqual("google/gemini-3.1-flash-lite", result["winner"]["model_id"])
        self.assertEqual(4, result["usage"]["unknown_attempts"])

    def test_policy_accounting_renderer_and_local_authorization_never_fall_back(self):
        for outcome in ("policy", "accounting", "protocol", "draft", "input", "renderer", "local_auth"):
            with self.subTest(outcome=outcome):
                result, _, script = self.run_script({"qwen-intl": outcome})
                self.assertEqual("stopped", result["state"])
                self.assertIsNone(result["winner"])
                self.assertEqual(["qwen-intl"], script.calls)

    def test_reused_parent_with_changed_content_conflicts_before_any_new_call(self):
        from adaptive_factory.settings import SettingsError
        _, caller, script = self.run_script({"qwen-intl": "success"})
        with self.assertRaisesRegex(SettingsError, "idempotency conflict"):
            caller.submit("parent-1", b"changed brief", "text/plain")
        self.assertEqual(["qwen-intl"], script.calls)

    def test_absent_backends_consume_each_slot_once_and_replay_has_no_io(self):
        from adaptive_factory.landing_failover import FailoverCoordinator
        from adaptive_factory.landing_failover_config import FailoverConfig
        from adaptive_factory.landing_failover_journal import CallerJournal
        from adaptive_factory.landing_failover_transport import BackendUnavailable

        calls = []
        class Absent:
            def __init__(self, backend, **kwargs):
                self.backend = backend
            def capability(self):
                calls.append(self.backend.profile_id)
                raise BackendUnavailable("not_connected")
            def close(self):
                pass
        with tempfile.TemporaryDirectory() as temporary:
            config = FailoverConfig.from_dict(configuration(Path(temporary)))
            with CallerJournal(config) as journal:
                caller = FailoverCoordinator(config, journal, backend_factory=Absent)
                result = caller.submit("parent-1", b"A bounded brief", "text/plain")
                self.assertEqual("exhausted", result["state"])
                self.assertEqual(["qwen-intl", "grok-vision", "openai", "anthropic", "openrouter"], calls)
                self.assertEqual(5, len(result["attempts"]))
                self.assertEqual(result, caller.submit("parent-1", b"A bounded brief", "text/plain"))
                self.assertEqual(5, len(calls))

    def test_restart_after_durable_intent_observes_without_resubmitting(self):
        from adaptive_factory.landing_failover import FailoverCoordinator
        from adaptive_factory.landing_failover_config import FailoverConfig
        from adaptive_factory.landing_failover_journal import CallerJournal
        from adaptive_factory.landing_failover_transport import BackendAmbiguous
        from adaptive_factory.landing_failover_contracts import backend_capability

        calls = []
        class Lost:
            def __init__(self, backend, **kwargs):
                self.backend = backend
            def capability(self):
                profile = HttpLandingProfile.for_provider(self.backend.profile_id, available=True)
                return backend_capability(profile, "tenant-1", TARGET_REPOSITORY_ID, TARGET_BASE_SHA, TARGET_BASE_TREE)
            def submit(self, child_id, payload, media_type):
                calls.append(("submit", child_id))
                raise BackendAmbiguous("reply_lost")
            def observe(self, child_id):
                calls.append(("observe", child_id))
                raise BackendAmbiguous("not_found")
            def close(self):
                pass
        with tempfile.TemporaryDirectory() as temporary:
            config = FailoverConfig.from_dict(configuration(Path(temporary)))
            with CallerJournal(config) as journal:
                result = FailoverCoordinator(config, journal, backend_factory=Lost).submit("parent-1", b"brief", "text/plain")
                self.assertEqual("needs_human", result["state"])
            with CallerJournal(config) as journal:
                result = FailoverCoordinator(config, journal, backend_factory=Lost).resume("parent-1")
                self.assertEqual("needs_human", result["state"])
            self.assertEqual(1, sum(kind == "submit" for kind, _ in calls))
            self.assertEqual(1, len({child for _, child in calls}))


if __name__ == "__main__":
    unittest.main()
