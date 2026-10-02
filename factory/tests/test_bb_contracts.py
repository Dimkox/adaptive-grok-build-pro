from copy import deepcopy
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

from adaptive_factory.contracts import ContractError
from adaptive_factory.adapters import CodexAdapter, select_adapter


SCHEMAS = Path(__file__).parents[1] / "contracts" / "jsonschema"


def bb_profile(**changes):
    value = {
        "schema_version": 1,
        "profile_id": "bb-unqualified-1",
        "enabled": False,
        "source_commit": None,
        "binary_digest": None,
        "workflows_digest": None,
        "orchestra_digest": None,
        "capabilities": [],
        "max_agents": 1,
        "max_depth": 1,
        "max_cost_usd_micros": 100_000,
        "wall_seconds": 60,
        "lease_seconds": 30,
        "stop_seconds": 10,
    }
    value.update(changes)
    return value


def bb_observation(**changes):
    value = {
        "schema_version": 1,
        "repository_id": "owner/project",
        "task_id": "job-1",
        "run_id": "run-1",
        "attempt_id": "attempt-1",
        "fence": 1,
        "context_digest": "1" * 64,
        "policy_digest": "2" * 64,
        "operation_id": "op-1",
        "command_digest": "3" * 64,
        "acknowledged": True,
        "effect_outcome": "unknown",
        "stop_outcome": "unknown",
        "evidence_digest": None,
    }
    value.update(changes)
    return value


class BBContractTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(
            importlib.util.find_spec("adaptive_factory.bb_contracts"),
            "BB boundary missing",
        )
        return importlib.import_module("adaptive_factory.bb_contracts")

    def test_default_off_keeps_native_without_claiming_live_qualification(self):
        module = self.module()
        profile = module.BBBackendProfileV1.from_dict(bb_profile())
        self.assertEqual(
            module.select_backend(profile),
            {
                "backend": "native",
                "bb_qualification": "not_run",
                "authority_effect": "none",
            },
        )
        with self.assertRaisesRegex(ContractError, "bb_live_profile_unqualified"):
            module.BBBackendProfileV1.from_dict(bb_profile(enabled=True))

    def test_default_off_profile_does_not_replace_existing_native_selection(self):
        before = select_adapter("codex", native_version="0.152.1")
        profile = self.module().BBBackendProfileV1.from_dict(bb_profile())
        self.assertEqual(self.module().select_backend(profile)["backend"], "native")
        after = select_adapter("codex", native_version="0.152.1")
        self.assertIsInstance(before, CodexAdapter)
        self.assertIsInstance(after, CodexAdapter)
        self.assertEqual(before.conformance, after.conformance)

    def test_profile_rejects_unbounded_duplicate_and_incoherent_limits(self):
        module = self.module()
        for key, value in (
            ("max_agents", 0),
            ("max_depth", True),
            ("wall_seconds", float("inf")),
            ("stop_seconds", 1_000_000_001),
        ):
            with self.subTest(key=key), self.assertRaises(ContractError):
                module.BBBackendProfileV1.from_dict(bb_profile(**{key: value}))
        for changes in (
            {"capabilities": ["observe", "observe"]},
            {"capabilities": ["execute"]},
            {"lease_seconds": 61},
            {"stop_seconds": 31},
        ):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                module.BBBackendProfileV1.from_dict(bb_profile(**changes))

    def test_profile_normalizes_every_malformed_json_shape_to_contract_error(self):
        module = self.module()
        mutations = []
        for key in ("source_commit",):
            mutations.extend({key: value} for value in (False, [], "f" * 39, "G" * 40))
        for key in ("binary_digest", "workflows_digest", "orchestra_digest"):
            mutations.extend({key: value} for value in (False, [], "f" * 63, "G" * 64))
        for key in (
            "max_agents",
            "max_depth",
            "max_cost_usd_micros",
            "wall_seconds",
            "lease_seconds",
            "stop_seconds",
        ):
            mutations.extend({key: value} for value in (0, True, 1_000_000_001))
        mutations.extend(
            (
                {"capabilities": [value]}
                for value in (False, 1, [], {}, "execute")
            )
        )
        mutations.append({"profile_id": "x", "extra": True})
        for mutation in mutations:
            facts = bb_profile()
            facts.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                module.BBBackendProfileV1.from_dict(facts)
        for missing in bb_profile():
            facts = bb_profile()
            facts.pop(missing)
            with self.subTest(missing=missing), self.assertRaises(ContractError):
                module.BBBackendProfileV1.from_dict(facts)

    def test_lifecycle_normalizes_every_malformed_json_shape_to_contract_error(self):
        module = self.module()
        mutations = []
        for key in ("repository_id", "task_id", "run_id", "attempt_id", "operation_id"):
            mutations.extend({key: value} for value in (False, [], "", "bad value"))
        for key in ("context_digest", "policy_digest", "command_digest"):
            mutations.extend({key: value} for value in (False, [], "f" * 63, "G" * 64))
        mutations.extend(
            (
                {"fence": 0},
                {"fence": True},
                {"acknowledged": 1},
                {"effect_outcome": []},
                {"effect_outcome": "complete"},
                {"stop_outcome": {}},
                {"stop_outcome": "complete"},
                {"evidence_digest": False},
                {"evidence_digest": []},
                {"evidence_digest": "f" * 63},
                {"evidence_digest": "G" * 64},
                {"repository_id": "other/project", "extra": True},
            )
        )
        for mutation in mutations:
            facts = bb_observation()
            facts.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                module.BBLifecycleObservationV1.from_dict(facts)
        for missing in bb_observation():
            facts = bb_observation()
            facts.pop(missing)
            with self.subTest(missing=missing), self.assertRaises(ContractError):
                module.BBLifecycleObservationV1.from_dict(facts)

    def test_acknowledgement_never_claims_effect_or_stop(self):
        module = self.module()
        record = module.BBLifecycleObservationV1.from_dict(bb_observation())
        self.assertEqual(record.to_dict()["effect_outcome"], "unknown")
        self.assertEqual(record.to_dict()["stop_outcome"], "unknown")
        with self.assertRaisesRegex(ContractError, "effect_evidence_missing"):
            module.BBLifecycleObservationV1.from_dict(
                bb_observation(effect_outcome="observed")
            )
        module.BBLifecycleObservationV1.from_dict(
            bb_observation(effect_outcome="observed", evidence_digest="4" * 64)
        )

    def test_binding_checks_every_authoritative_execution_dimension(self):
        module = self.module()
        first = module.BBLifecycleObservationV1.from_dict(bb_observation())
        expected = {
            key: first.to_dict()[key]
            for key in (
                "repository_id",
                "task_id",
                "run_id",
                "attempt_id",
                "fence",
                "context_digest",
                "policy_digest",
                "operation_id",
                "command_digest",
            )
        }
        first.validate_binding(**expected)
        replacements = {
            "repository_id": "other/project",
            "task_id": "job-2",
            "run_id": "run-2",
            "attempt_id": "attempt-2",
            "fence": 2,
            "context_digest": "a" * 64,
            "policy_digest": "b" * 64,
            "operation_id": "op-2",
            "command_digest": "c" * 64,
        }
        for key, value in replacements.items():
            forged = dict(expected)
            forged[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(
                ContractError, "bb_identity_mismatch"
            ):
                first.validate_binding(**forged)

    def test_replay_binds_operation_identity_request_and_full_body(self):
        module = self.module()
        first = module.BBLifecycleObservationV1.from_dict(bb_observation())
        first.validate_replay(
            module.BBLifecycleObservationV1.from_dict(deepcopy(bb_observation()))
        )
        with self.assertRaisesRegex(ContractError, "bb_idempotency_conflict"):
            first.validate_replay(
                module.BBLifecycleObservationV1.from_dict(
                    bb_observation(command_digest="5" * 64)
                )
            )
        with self.assertRaisesRegex(ContractError, "bb_replay_body_conflict"):
            first.validate_replay(
                module.BBLifecycleObservationV1.from_dict(
                    bb_observation(acknowledged=False)
                )
            )

    def test_replay_rejects_every_mutated_or_missing_operation_identity_field(self):
        module = self.module()
        first = module.BBLifecycleObservationV1.from_dict(bb_observation())
        replacements = {
            "repository_id": "other/project",
            "task_id": "job-2",
            "run_id": "run-2",
            "attempt_id": "attempt-2",
            "fence": 2,
            "context_digest": "a" * 64,
            "policy_digest": "b" * 64,
            "operation_id": "op-2",
        }
        self.assertEqual(set(module.BBLifecycleObservationV1._OPERATION_FIELDS), set(replacements))
        for key, value in replacements.items():
            for missing in (False, True):
                facts = bb_observation()
                if missing:
                    facts.pop(key)
                else:
                    facts[key] = value
                forged = module.BBLifecycleObservationV1.freeze(facts)
                with self.subTest(key=key, missing=missing), self.assertRaisesRegex(
                    ContractError, "bb_idempotency_conflict"
                ):
                    first.validate_replay(forged)

    def test_structural_schemas_accept_canonical_records_but_parser_is_semantic_gate(self):
        module = self.module()
        for name, value in (
            ("bb-backend-profile.v1.schema.json", bb_profile()),
            ("bb-lifecycle-observation.v1.schema.json", bb_observation()),
        ):
            with self.subTest(name=name):
                completed = subprocess.run(
                    ["jsonschema", str(SCHEMAS / name)],
                    input=json.dumps(value),
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
        structurally_valid = bb_profile(lease_seconds=61)
        completed = subprocess.run(
            ["jsonschema", str(SCHEMAS / "bb-backend-profile.v1.schema.json")],
            input=json.dumps(structurally_valid),
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        with self.assertRaisesRegex(ContractError, "invalid_deadlines"):
            module.BBBackendProfileV1.from_dict(structurally_valid)
