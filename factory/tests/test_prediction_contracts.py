from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from adaptive_factory.contracts import ContractError


SCHEMAS = Path(__file__).parents[1] / "contracts" / "jsonschema"


def prediction_facts(**changes):
    value = {
        "schema_version": 1,
        "prediction_id": "pred-1",
        "repository_id": "owner/project",
        "change_id": "change-1",
        "candidate_sha": "1" * 40,
        "context_digest": "2" * 64,
        "spec_digest": "3" * 64,
        "profile_digest": "4" * 64,
        "feature_schema_version": "features-v1",
        "feature_schema_digest": "5" * 64,
        "dataset_version": "dataset-v1",
        "dataset_digest": "6" * 64,
        "split_digest": "7" * 64,
        "model_version": "baseline-v1",
        "model_digest": "8" * 64,
        "preprocessing_version": "preprocessing-v1",
        "preprocessing_digest": "9" * 64,
        "deterministic_evidence_digest": "a" * 64,
        "seed": 7,
        "predicted_at": "2026-09-30T11:59:00Z",
        "first_check_started_at": "2026-09-30T12:00:00Z",
        "train_before": "2026-09-29T00:00:00Z",
        "test_after": "2026-09-29T00:00:00Z",
        "train_change_ids": ["old-1"],
        "test_change_ids": ["change-1"],
        "features": [
            {"name": "changed_lines", "value": 12, "observed_at": "2026-09-30T11:58:00Z"}
        ],
        "required_history_count": 100,
        "observed_history_count": 0,
        "label_status": "unknown",
        "predicted_value": None,
        "output_space": "probability",
        "authority_effect": "none",
    }
    value.update(changes)
    return value


def explanation_facts(prediction, **changes):
    value = {
        "schema_version": 1,
        "prediction_digest": prediction.record_digest,
        "model_version": "baseline-v1",
        "model_digest": "8" * 64,
        "background_dataset_version": "background-v1",
        "background_dataset_digest": "b" * 64,
        "explainer_version": "shap-v1",
        "explainer_options_digest": "c" * 64,
        "deterministic_evidence_digest": "d" * 64,
        "output_space": "probability",
        "base_value": 0.2,
        "contributions": [{"name": "changed_lines", "value": 0.5}],
        "tolerance": 0.000001,
        "authority_effect": "none",
    }
    value.update(changes)
    return value


class PredictionContractTests(unittest.TestCase):
    def module(self):
        from adaptive_factory import prediction_contracts

        return prediction_contracts

    def test_insufficient_history_is_not_qualified_and_cannot_gain_authority(self):
        module = self.module()
        facts = prediction_facts()
        record = module.PredictionObservationV1.from_dict(facts)
        self.assertEqual(record.status, "not_qualified")
        self.assertEqual(record.to_dict()["authority_effect"], "none")
        for key in ("routing", "budget", "permissions", "m8", "checks"):
            changed = deepcopy(facts)
            changed[key] = "changed"
            with self.subTest(key=key), self.assertRaises(ContractError):
                module.PredictionObservationV1.from_dict(changed)
        with self.assertRaisesRegex(ContractError, "authority_effect"):
            module.PredictionObservationV1.from_dict(prediction_facts(authority_effect="route"))

    def test_prediction_binds_candidate_context_spec_profile_versions_and_evidence(self):
        module = self.module()
        record = module.PredictionObservationV1.from_dict(prediction_facts())
        self.assertEqual(record.to_dict(), prediction_facts())
        for key, invalid in (
            ("candidate_sha", "1" * 39),
            ("context_digest", "2" * 63),
            ("spec_digest", "3" * 63),
            ("profile_digest", "4" * 63),
            ("feature_schema_version", ""),
            ("dataset_version", "bad version"),
            ("model_version", ""),
            ("preprocessing_version", ""),
            ("deterministic_evidence_digest", "a" * 63),
        ):
            with self.subTest(key=key), self.assertRaises(ContractError):
                module.PredictionObservationV1.from_dict(prediction_facts(**{key: invalid}))

    def test_leakage_split_replay_and_unknown_labels_fail_closed(self):
        module = self.module()
        mutations = {
            "late_feature": {"features": [{"name": "changed_lines", "value": 12, "observed_at": "2026-09-30T12:01:00Z"}]},
            "late_prediction": {"predicted_at": "2026-09-30T12:00:00Z"},
            "same_change": {"train_change_ids": ["change-1"]},
            "duplicate_train": {"train_change_ids": ["old-1", "old-1"]},
            "missing_candidate_change": {"test_change_ids": ["other-1"]},
            "late_train": {"train_before": "2026-09-30T00:00:00Z"},
            "label": {"label_status": "pass"},
            "nan": {"features": [{"name": "changed_lines", "value": float("nan"), "observed_at": "2026-09-30T11:58:00Z"}]},
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), self.assertRaises(ContractError):
                module.PredictionObservationV1.from_dict(prediction_facts(**mutation))

    def test_prediction_digest_is_deterministic_and_every_binding_changes_it(self):
        module = self.module()
        original = module.PredictionObservationV1.from_dict(prediction_facts())
        reordered = dict(reversed(list(prediction_facts().items())))
        self.assertEqual(original.record_digest, module.PredictionObservationV1.from_dict(reordered).record_digest)
        for key, value in (
            ("candidate_sha", "f" * 40),
            ("context_digest", "f" * 64),
            ("spec_digest", "e" * 64),
            ("profile_digest", "d" * 64),
            ("dataset_version", "dataset-v2"),
            ("model_version", "baseline-v2"),
            ("deterministic_evidence_digest", "c" * 64),
        ):
            changed = module.PredictionObservationV1.from_dict(prediction_facts(**{key: value}))
            self.assertNotEqual(original.record_digest, changed.record_digest, key)

    def test_explanation_requires_available_prediction_and_full_additive_vector(self):
        module = self.module()
        unavailable = module.PredictionObservationV1.from_dict(prediction_facts())
        with self.assertRaisesRegex(ContractError, "explanation_unavailable"):
            module.PredictionExplanationV1.from_dict(explanation_facts(unavailable), prediction=unavailable)

        prediction = module.PredictionObservationV1.from_dict(
            prediction_facts(observed_history_count=100, label_status="product_failure", predicted_value=0.7)
        )
        explanation = explanation_facts(prediction)
        parsed = module.PredictionExplanationV1.from_dict(explanation, prediction=prediction)
        self.assertEqual(parsed.to_dict()["authority_effect"], "none")
        invalid = (
            ("contributions", []),
            ("base_value", 0.1),
            ("output_space", "log_odds"),
            ("tolerance", 1),
            ("model_digest", "f" * 64),
            ("model_version", "baseline-v2"),
            ("prediction_digest", "f" * 64),
            ("authority_effect", "merge"),
        )
        for key, value in invalid:
            changed = deepcopy(explanation)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                module.PredictionExplanationV1.from_dict(changed, prediction=prediction)

    def test_public_schemas_are_closed_bounded_and_match_parser_examples(self):
        module = self.module()
        prediction = module.PredictionObservationV1.from_dict(prediction_facts())
        examples = {
            "prediction-observation.v1.schema.json": prediction.to_dict(),
            "prediction-explanation.v1.schema.json": explanation_facts(
                module.PredictionObservationV1.from_dict(
                    prediction_facts(observed_history_count=100, label_status="product_pass", predicted_value=0.7)
                )
            ),
        }
        for name, example in examples.items():
            with self.subTest(name=name):
                schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(schema["properties"]["schema_version"], {"const": 1})
                Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(example)

