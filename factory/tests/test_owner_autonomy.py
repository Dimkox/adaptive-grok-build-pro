"""Synthetic offline controls, never empirical M7 or runtime product telemetry."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

from adaptive_factory import owner_autonomy as owner
from adaptive_factory.contracts import ContractError
from tests.json_schema_subset import SchemaValidationError, SubsetValidator

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)


class OwnerAutonomyTests(unittest.TestCase):
    def setUp(self):
        self.policy_data = json.loads((ROOT / "factory/runtime/owner-autonomy-policy.v1.json").read_text())
        self.state = json.loads((ROOT / "PROJECT_STATE.json").read_text())
        self.policy = owner.OwnerPolicyV1.from_dict(self.policy_data)
        self.case = owner.OwnerCaseV1.from_project_state(self.state)
        self.context = owner.OwnerContextV1("Dimkox/adaptive-grok-build-pro", "a" * 64, "b" * 64, "c" * 64)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = owner.OwnerRuntime(Path(self.temp.name) / "runtime")

    def assert_local_authority(self, decision):
        self.assertIs(decision["external_authority"], False)
        self.assertEqual(decision["authority_ceiling"], "L2")

    def test_one_case_qualifies_activates_and_real_consumer_admits_local_test(self):
        result = self.store.activate(self.policy, self.case, self.context, now=NOW)
        self.assert_local_authority(result)
        self.assertEqual((result["allowed"], result["level"]), (True, "L1"))
        self.assertIsNone(self.case.cost_usd_micros)
        admitted = self.store.admit(self.policy, self.case, self.context, "local_test", now=NOW)
        self.assert_local_authority(admitted)
        self.assertEqual((admitted["allowed"], admitted["level"]), (True, "L1"))
        status = self.store.status(self.policy, self.case, self.context, now=NOW)
        self.assert_local_authority(status)
        self.assertEqual(status["level"], "L1")

    def test_initial_activation_refuses_each_wrong_provenance_without_existing_record(self):
        for index, (field, value) in enumerate((("product_repository", "other/product"),
                                                ("product_source_sha", "d" * 40),
                                                ("factory_source_sha", "e" * 40))):
            with self.subTest(field=field):
                runtime = owner.OwnerRuntime(Path(self.temp.name) / f"fresh-{index}")
                result = runtime.activate(self.policy, replace(self.case, **{field: value}), self.context, now=NOW)
                self.assertEqual((result["allowed"], result["level"], result["reason"]),
                                 (False, "L0", "provenance_mismatch"))
                self.assert_local_authority(result)
                self.assertFalse((runtime.path / "activation.json").exists())

    def test_persisted_extreme_future_dates_deny_l0_without_datetime_overflow(self):
        self.store.activate(self.policy, self.case, self.context, now=NOW)
        path = self.store.path / "activation.json"
        value = json.loads(path.read_text())
        value.update(issued_at="9999-12-31T23:00:00Z", expires_at="9999-12-31T23:59:59.999999Z")
        path.write_text(json.dumps(value))
        result = self.store.admit(self.policy, self.case, self.context, "local_test", now=NOW)
        self.assertEqual((result["allowed"], result["level"], result["reason"]),
                         (False, "L0", "activation_expired"))
        self.assert_local_authority(result)

    def test_missing_activation_and_all_external_actions_deny_l0(self):
        self.assertFalse(self.store.admit(self.policy, self.case, self.context, "local_test", now=NOW)["allowed"])
        self.store.activate(self.policy, self.case, self.context, now=NOW)
        for action in ("merge", "production", "provider_call", "external_action", "local_edit", "unknown"):
            with self.subTest(action=action):
                result = self.store.admit(self.policy, self.case, self.context, action, now=NOW)
                self.assert_local_authority(result)
                self.assertEqual((result["allowed"], result["level"]), (False, "L0"))

    def test_each_admission_rechecks_every_binding_and_expiry(self):
        self.store.activate(self.policy, self.case, self.context, now=NOW)
        for field, value in (("source_digest", "d" * 64), ("profile_digest", "d" * 64),
                             ("repository_binding_digest", "d" * 64), ("repository_id", "other/repository")):
            with self.subTest(field=field):
                result = self.store.admit(self.policy, self.case, replace(self.context, **{field: value}), "local_test", now=NOW)
                self.assertEqual((result["allowed"], result["level"]), (False, "L0"))
        for policy, case in ((replace(self.policy, enabled=False), self.case),
                             (replace(self.policy, expires_at=NOW), self.case),
                             (replace(self.policy, policy_id="another-policy"), self.case),
                             (self.policy, replace(self.case, accounting_complete=False)),
                             (self.policy, replace(self.case, human_gate_complete=False)),
                             (self.policy, replace(self.case, accepted=False)),
                             (self.policy, replace(self.case, factory_source_sha="e" * 40))):
            with self.subTest(policy=policy.policy_id, case=case.accepted):
                self.assertFalse(self.store.admit(policy, case, self.context, "local_test", now=NOW)["allowed"])
        self.assertFalse(self.store.admit(self.policy, self.case, self.context, "local_test", now=NOW + timedelta(hours=1))["allowed"])
        self.assertFalse(self.store.admit(self.policy, self.case, self.context, "local_test", now=NOW - timedelta(seconds=1))["allowed"])

    def test_revocation_survives_restart_and_prevents_reactivation(self):
        self.store.activate(self.policy, self.case, self.context, now=NOW)
        revoked = self.store.revoke(self.policy, now=NOW)
        self.assert_local_authority(revoked)
        self.assertFalse(revoked["allowed"])
        restarted = owner.OwnerRuntime(self.store.path)
        self.assertEqual(restarted.status(self.policy, self.case, self.context, now=NOW)["reason"], "revoked")
        self.assertFalse(restarted.activate(self.policy, self.case, self.context, now=NOW)["allowed"])

    def test_closed_contracts_and_authority_escalation_fail(self):
        for field, value in (("unknown", True), ("minimum_accepted_tasks", 0),
                             ("minimum_accepted_tasks", False), ("initial_level", "L2"),
                             ("authority_ceiling", "L3"), ("allowed_actions", ["merge"]),
                             ("activation_ttl_seconds", 0), ("enabled", 1)):
            with self.subTest(field=field):
                data = deepcopy(self.policy_data)
                data[field] = value
                with self.assertRaises(ContractError):
                    owner.OwnerPolicyV1.from_dict(data)
        data = self.case.to_dict()
        data["unknown"] = True
        with self.assertRaises(ContractError):
            owner.OwnerCaseV1.from_dict(data)

    def test_corrupt_activation_or_symlink_denies_without_overwriting(self):
        self.store.activate(self.policy, self.case, self.context, now=NOW)
        activation = self.store.path / "activation.json"
        activation.write_text('{"schema_version":1}')
        self.assertFalse(self.store.status(self.policy, self.case, self.context, now=NOW)["allowed"])
        self.assertFalse(self.store.activate(self.policy, self.case, self.context, now=NOW)["allowed"])
        activation.unlink()
        foreign = Path(self.temp.name) / "foreign"
        foreign.write_text("untouched")
        activation.symlink_to(foreign)
        self.assertFalse(self.store.status(self.policy, self.case, self.context, now=NOW)["allowed"])
        self.assertEqual(foreign.read_text(), "untouched")

    def test_schema_matches_contracts_and_rejects_extra_keys(self):
        schema = json.loads((ROOT / "factory/contracts/jsonschema/owner-autonomy.v1.schema.json").read_text())
        for name, value in (("policy", self.policy.to_dict()), ("case", self.case.to_dict())):
            validator = SubsetValidator({"$ref": "#/$defs/" + name, "$defs": schema["$defs"]})
            validator.validate(value)
            value["unknown"] = True
            with self.assertRaises(SchemaValidationError):
                validator.validate(value)

    def test_state_adapter_requires_explicit_readiness_and_real_provenance(self):
        for name, value in (("accounting_complete", False), ("human_gate_complete", False),
                            ("evidence_kind", "synthetic_telemetry")):
            data = deepcopy(self.state)
            data["milestones"]["M8"]["completed_product_case"]["owner_readiness"][name] = value
            with self.subTest(name=name):
                if name == "evidence_kind":
                    with self.assertRaises(ContractError):
                        owner.OwnerCaseV1.from_project_state(data)
                else:
                    case = owner.OwnerCaseV1.from_project_state(data)
                    self.assertFalse(self.store.activate(self.policy, case, self.context, now=NOW)["allowed"])
        data = deepcopy(self.state)
        del data["milestones"]["M8"]["completed_product_case"]["owner_readiness"]
        with self.assertRaises(ContractError):
            owner.OwnerCaseV1.from_project_state(data)

    def test_cli_full_lifecycle_rechecks_actual_current_source_and_missing_inputs(self):
        root = Path(self.temp.name) / "checkout"
        (root / "scripts").mkdir(parents=True)
        shutil.copy(ROOT / "scripts/grok_m8.py", root / "scripts/grok_m8.py")
        shutil.copytree(ROOT / "factory/src", root / "factory/src", ignore=shutil.ignore_patterns("__pycache__"))
        (root / "factory/runtime").mkdir()
        fixture_policy = dict(self.policy_data, expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
        (root / "factory/runtime/owner-autonomy-policy.v1.json").write_text(json.dumps(fixture_policy))
        (root / "PROJECT_STATE.json").write_text(json.dumps(self.state))
        (root / "VERSION").write_text("2.2.0\n")
        for args in (("init", "--quiet"), ("remote", "add", "origin", "https://github.com/Dimkox/adaptive-grok-build-pro.git"),
                     ("add", "."), ("-c", "user.name=synthetic", "-c", "user.email=synthetic@example.invalid",
                                   "commit", "--quiet", "-m", "synthetic offline context")):
            subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
        def run(*args):
            process = subprocess.run([sys.executable, str(root / "scripts/grok_m8.py"), *args], cwd=root,
                                     capture_output=True, text=True, timeout=10)
            decision = json.loads(process.stdout)
            self.assert_local_authority(decision)
            return process.returncode, decision
        self.assertEqual(run("status")[1]["level"], "L0")
        self.assertEqual(run("activate")[0], 0)
        self.assertEqual(run("admit", "--action", "local_test")[1]["level"], "L1")
        self.assertEqual(run("admit", "--action", "provider_call")[0], 2)
        source = root / "factory/src/adaptive_factory/owner_autonomy.py"
        original = source.read_text()
        source.write_text(original + "\n# synthetic current-source change\n")
        self.assertEqual(run("admit", "--action", "local_test")[1]["reason"], "binding_mismatch")
        source.write_text(original)
        self.assertEqual(run("revoke")[0], 0)
        self.assertEqual(run("admit", "--action", "local_test")[1]["reason"], "revoked")
        (root / "factory/runtime/owner-autonomy-policy.v1.json").unlink()
        self.assertEqual(run("admit", "--action", "local_test")[0], 2)

    def test_activation_schema_and_runtime_deny_extra_keys_and_level_escalation(self):
        self.store.activate(self.policy, self.case, self.context, now=NOW)
        path = self.store.path / "activation.json"
        value = json.loads(path.read_text())
        schema = json.loads((ROOT / "factory/contracts/jsonschema/owner-autonomy.v1.schema.json").read_text())
        validator = SubsetValidator({"$ref": "#/$defs/activation", "$defs": schema["$defs"]})
        validator.validate(value)
        for field, proposed in (("unknown", True), ("level", "L2"), ("policy_digest", "d" * 64)):
            mutated = dict(value, **{field: proposed})
            path.write_text(json.dumps(mutated))
            self.assertFalse(self.store.admit(self.policy, self.case, self.context, "local_test", now=NOW)["allowed"])
            if field != "policy_digest":
                with self.assertRaises(SchemaValidationError):
                    validator.validate(mutated)

    def test_cli_denial_is_structured_nonzero_and_offline(self):
        run = subprocess.run([sys.executable, str(ROOT / "scripts/grok_m8.py"), "admit", "--action", "merge"],
                             cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertEqual((json.loads(run.stdout)["allowed"], json.loads(run.stdout)["level"]), (False, "L0"))


if __name__ == "__main__":
    unittest.main()
