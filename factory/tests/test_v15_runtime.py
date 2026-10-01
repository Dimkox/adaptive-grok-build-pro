import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from adaptive_factory.contracts import canonical_digest
from adaptive_factory.v15_runtime_config import load_v15_runtime_config


class MemoryStore:
    def __init__(self):
        self.body = None

    def record_v15_runtime_evaluation(self, body):
        if self.body is not None:
            return self.body == body
        self.body = body
        return True

    def v15_runtime_evaluation(self, task_id):
        return self.body if self.body and self.body["task_id"] == task_id else None


class V15RuntimeTests(unittest.TestCase):
    @staticmethod
    def private_json(path, value):
        raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        path.write_bytes(raw)
        path.chmod(0o600)
        return hashlib.sha256(raw).hexdigest()

    def test_exact_binding_composes_adapters_and_persists_observation(self):
        from adaptive_factory.v15_runtime import V15RuntimeEvaluator

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fpf_body = {
                "tenant_id": "owner/project", "repository_id": "owner/project",
                "source_revision": "a" * 40, "package": "ai.lev/fpf", "package_version": "1",
                "license_id": "CC-BY-4.0", "generator_id": "factory-fpf-1",
                "fragments": [{"pattern_id": "root", "locator": "patterns/root.md", "text": "safe",
                               "sha256": hashlib.sha256(b"safe").hexdigest(), "required": [], "optional": []}],
            }
            fpf = root / "fpf.json"
            fpf_digest = self.private_json(fpf, fpf_body)
            vibevm_body = {"schema_version": 1, "tenant_id": "owner/project", "repository_id": "owner/project",
                           "candidate_sha": "a" * 40, "generation_id": "b" * 64,
                           "qualified": True, "revoked": False, "native_export_digest": "c" * 64}
            vibevm = root / "vibevm.json"
            vibevm_digest = self.private_json(vibevm, vibevm_body)
            prediction_body = {"status": "not_qualified", "authority_effect": "none"}
            prediction = root / "prediction.json"
            prediction_digest = self.private_json(prediction, prediction_body)
            config_body = {"schema_version": 1, "bindings": [{
                "tenant_id": "owner/project", "repository_id": "owner/project", "exact_head_sha": "a" * 40,
                "fpf": {"enabled": True, "path": str(fpf), "digest": fpf_digest},
                "vibevm": {"enabled": True, "path": str(vibevm), "digest": vibevm_digest},
                "prediction": {"enabled": True, "path": str(prediction), "digest": prediction_digest},
            }]}
            config_path = root / "config.json"
            self.private_json(config_path, config_body)
            store = MemoryStore()
            evaluator = V15RuntimeEvaluator(store, load_v15_runtime_config(config_path))
            task = SimpleNamespace(task_id="00000000-0000-0000-0000-000000000001", repository_id="owner/project")
            result = evaluator.evaluate(task, candidate_sha="a" * 40)
        self.assertEqual(result["fpf_status"], "supported")
        self.assertEqual(result["vibevm_status"], "supported")
        self.assertEqual(result["prediction_status"], "not_qualified")
        self.assertEqual(result["qualification"]["status"], "not_evaluated")
        self.assertEqual(
            [case["case_id"] for case in result["qualification"]["cases"]],
            [f"F24-{index:03d}" for index in range(1, 13)],
        )
        self.assertEqual(
            [case["domain"] for case in result["qualification"]["cases"]],
            ["pump_selector"] * 4 + ["factory"] * 4 + ["cross_component"] * 4,
        )
        self.assertEqual({case["status"] for case in result["qualification"]["cases"]}, {"not_evaluated"})
        self.assertEqual(result["evidence_digest"], canonical_digest({k: v for k, v in result.items() if k != "evidence_digest"}))
        self.assertEqual(store.body, result)

    def test_missing_mismatched_or_invalid_binding_falls_back_without_persistence(self):
        from adaptive_factory.v15_runtime import V15RuntimeEvaluator
        from adaptive_factory.v15_runtime_config import V15RuntimeConfig

        task = SimpleNamespace(task_id="00000000-0000-0000-0000-000000000001", repository_id="owner/project")
        store = MemoryStore()
        result = V15RuntimeEvaluator(store, V15RuntimeConfig((), "d" * 64)).evaluate(
            task, candidate_sha="a" * 40
        )
        self.assertEqual(result, {"fpf_status": "not_evaluated", "vibevm_status": "not_evaluated",
                                  "prediction_status": "not_qualified"})
        self.assertIsNone(store.body)

    def test_artifact_mutation_or_symlink_after_config_load_is_rejected_without_persistence(self):
        from adaptive_factory.v15_runtime import V15RuntimeEvaluator

        for replacement in ("mutated", "symlink"):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                artifact = root / "prediction.json"
                artifact_digest = self.private_json(
                    artifact, {"status": "not_qualified", "authority_effect": "none"}
                )
                disabled = {"enabled": False, "path": None, "digest": None}
                config_path = root / "config.json"
                self.private_json(config_path, {"schema_version": 1, "bindings": [{
                    "tenant_id": "owner/project", "repository_id": "owner/project",
                    "exact_head_sha": "a" * 40, "fpf": disabled, "vibevm": disabled,
                    "prediction": {"enabled": True, "path": str(artifact), "digest": artifact_digest},
                }]})
                config = load_v15_runtime_config(config_path)
                if replacement == "mutated":
                    artifact.write_text('{"status":"qualified"}', encoding="utf-8")
                    artifact.chmod(0o600)
                else:
                    target = root / "replacement.json"
                    self.private_json(target, {"status": "not_qualified", "authority_effect": "none"})
                    artifact.unlink()
                    artifact.symlink_to(target)
                store = MemoryStore()
                task = SimpleNamespace(
                    task_id="00000000-0000-0000-0000-000000000001",
                    repository_id="owner/project",
                )
                result = V15RuntimeEvaluator(store, config).evaluate(task, candidate_sha="a" * 40)
                self.assertEqual(result["prediction_status"], "unavailable")
                self.assertIsNone(store.body)

    def test_qualification_service_invokes_runtime_after_existing_access_check(self):
        from adaptive_factory.qualification import FactoryV15QualificationService

        task = SimpleNamespace(task_id="00000000-0000-0000-0000-000000000001", repository_id="owner/project")
        calls = []

        class Factory:
            store = SimpleNamespace(v15_candidate_sha=lambda task_id: "a" * 40)

            def get_task(self, task_id, *, actor):
                calls.append((task_id, actor))
                return task

        evaluator = SimpleNamespace(evaluate=lambda observed, candidate_sha: {
            "fpf_status": "supported", "vibevm_status": "unavailable",
            "prediction_status": "not_qualified", "candidate_sha": candidate_sha,
        })
        service = FactoryV15QualificationService(Factory(), lambda _task: {}, runtime_evaluator=evaluator)
        result = service.get_qualification(task.task_id, actor="reader").to_dict()
        self.assertEqual(calls, [(task.task_id, "reader")])
        self.assertEqual(result["fpf_status"], "supported")
        self.assertEqual(result["vibevm_status"], "unavailable")

    def test_qualification_rejects_cross_sha_evidence_before_runtime_persistence(self):
        from adaptive_factory.qualification import FactoryV15QualificationService
        from factory.tests.test_qualification import qualification_evidence

        task = SimpleNamespace(task_id="00000000-0000-0000-0000-000000000001", repository_id="owner/project")
        factory = SimpleNamespace(
            store=SimpleNamespace(v15_candidate_sha=lambda _task_id: "3" * 40),
            get_task=lambda _task_id, actor: task,
        )
        evaluator = SimpleNamespace(evaluate=lambda *_args, **_kwargs: self.fail("runtime invoked"))
        service = FactoryV15QualificationService(factory, lambda _task: qualification_evidence(), runtime_evaluator=evaluator)
        with self.assertRaisesRegex(Exception, "qualification_candidate_authority_mismatch"):
            service.get_qualification(task.task_id, actor="reader")
