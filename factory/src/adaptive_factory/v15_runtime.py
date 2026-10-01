"""Normal, observation-only composition for explicitly admitted v1.5 runtimes."""

from __future__ import annotations

import json

from .behavior_qualification import load_frozen_suite
from .contracts import ContractError, canonical_digest
from .fpf_runtime import FrozenFpfSnapshot, FpfRuntimeConfig, open_fpf_runtime
from .prediction_runtime import _validate_qualified_artifact
from .settings import SettingsError, read_private_file
from .v15_runtime_config import AdapterBinding, V15RuntimeConfig


def _json_artifact(binding: AdapterBinding):
    if not binding.enabled or binding.path is None:
        return None
    try:
        value = json.loads(read_private_file(binding.path, 4_194_304))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise SettingsError("v1.5 runtime artifact must be valid JSON") from exc
    if not isinstance(value, dict):
        raise SettingsError("v1.5 runtime artifact must be an object")
    return value


class V15RuntimeEvaluator:
    def __init__(self, store, config: V15RuntimeConfig):
        self.store = store
        self.config = config

    @staticmethod
    def _fpf(binding, tenant_id, repository_id, candidate_sha):
        if not binding.enabled:
            return "not_evaluated"
        try:
            value = _json_artifact(binding)
            expected = {
                "tenant_id", "repository_id", "source_revision", "package", "package_version",
                "license_id", "generator_id", "fragments",
            }
            if set(value) != expected or (
                value["tenant_id"], value["repository_id"], value["source_revision"]
            ) != (tenant_id, repository_id, candidate_sha):
                raise ContractError("fpf_authority_mismatch")
            snapshot = FrozenFpfSnapshot.build(**value)
            open_fpf_runtime(
                FpfRuntimeConfig(enabled=True, profile_id="operator-exact-fpf", qualification="supported"),
                snapshot,
                tenant_id=tenant_id,
            )
            return "supported"
        except (ContractError, SettingsError, TypeError, ValueError):
            return "unavailable"

    @staticmethod
    def _vibevm(binding, tenant_id, repository_id, candidate_sha):
        if not binding.enabled:
            return "not_evaluated"
        try:
            value = _json_artifact(binding)
            if set(value) != {
                "schema_version", "tenant_id", "repository_id", "candidate_sha", "generation_id",
                "qualified", "revoked", "native_export_digest",
            } or (
                value["schema_version"], value["tenant_id"], value["repository_id"], value["candidate_sha"]
            ) != (1, tenant_id, repository_id, candidate_sha):
                return "unavailable"
            for key in ("generation_id", "native_export_digest"):
                if not isinstance(value[key], str) or len(value[key]) != 64 or any(c not in "0123456789abcdef" for c in value[key]):
                    return "unavailable"
            return "supported" if value["qualified"] is True and value["revoked"] is False else "unavailable"
        except (SettingsError, TypeError, ValueError):
            return "unavailable"

    @staticmethod
    def _prediction(binding):
        if not binding.enabled:
            return "not_qualified"
        try:
            value = _json_artifact(binding)
            if value == {"status": "not_qualified", "authority_effect": "none"}:
                return "not_qualified"
            _validate_qualified_artifact(value)
            return "available"
        except (ContractError, SettingsError, TypeError, ValueError):
            return "unavailable"

    def evaluate(self, task, *, candidate_sha: str):
        binding = self.config.resolve(task.repository_id, task.repository_id, candidate_sha)
        if binding is None:
            return {
                "fpf_status": "not_evaluated",
                "vibevm_status": "not_evaluated",
                "prediction_status": "not_qualified",
            }
        body = {
            "schema_version": 1,
            "tenant_id": task.repository_id,
            "repository_id": task.repository_id,
            "task_id": task.task_id,
            "candidate_sha": candidate_sha,
            "config_digest": self.config.config_digest,
            "fpf_status": self._fpf(binding.fpf, task.repository_id, task.repository_id, candidate_sha),
            "vibevm_status": self._vibevm(binding.vibevm, task.repository_id, task.repository_id, candidate_sha),
            "prediction_status": self._prediction(binding.prediction),
            "timing": {"status": "not_evaluated"},
            "qualification": self._qualification(),
        }
        body["evidence_digest"] = canonical_digest(body)
        if not self.store.record_v15_runtime_evaluation(body):
            prior = self.store.v15_runtime_evaluation(task.task_id)
            if prior != body:
                raise ContractError("v15_runtime_evaluation_conflict")
        return body

    @staticmethod
    def _qualification():
        suite = load_frozen_suite()
        return {
            "status": "not_evaluated",
            "suite_digest": suite.record_digest,
            "cases": [
                {"case_id": case["case_id"], "domain": case["domain"], "status": "not_evaluated"}
                for case in suite.to_dict()["cases"]
            ],
        }
