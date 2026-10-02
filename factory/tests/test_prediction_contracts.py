from copy import deepcopy
import json
from pathlib import Path
import unittest

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
            "late_product_outcome": {"label_status": "product_failure"},
            "nan": {"features": [{"name": "changed_lines", "value": float("nan"), "observed_at": "2026-09-30T11:58:00Z"}]},
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), self.assertRaises(ContractError):
                module.PredictionObservationV1.from_dict(prediction_facts(**mutation))

    def test_unordered_set_like_inputs_are_canonicalized_without_mutating_callers(self):
        module = self.module()
        facts = prediction_facts(
            train_change_ids=["old-2", "old-1"],
            test_change_ids=["other-1", "change-1"],
            features=[
                {"name": "z_feature", "value": 2, "observed_at": "2026-09-30T11:58:00Z"},
                {"name": "a_feature", "value": 1, "observed_at": "2026-09-30T11:57:00Z"},
            ],
            observed_history_count=100,
            predicted_value=0.7,
        )
        original = deepcopy(facts)
        prediction = module.PredictionObservationV1.from_dict(facts)
        self.assertEqual(facts, original)
        self.assertEqual(prediction.to_dict()["train_change_ids"], ["old-1", "old-2"])
        self.assertEqual(prediction.to_dict()["test_change_ids"], ["change-1", "other-1"])
        self.assertEqual([item["name"] for item in prediction.to_dict()["features"]], ["a_feature", "z_feature"])
        reordered = deepcopy(facts)
        reordered["train_change_ids"].reverse()
        reordered["test_change_ids"].reverse()
        reordered["features"].reverse()
        self.assertEqual(prediction.record_digest, module.PredictionObservationV1.from_dict(reordered).record_digest)

        explanation = explanation_facts(
            prediction,
            base_value=0.2,
            contributions=[{"name": "z_feature", "value": 0.3}, {"name": "a_feature", "value": 0.2}],
        )
        first = module.PredictionExplanationV1.from_dict(explanation, prediction=prediction)
        reordered_explanation = deepcopy(explanation)
        reordered_explanation["contributions"].reverse()
        second = module.PredictionExplanationV1.from_dict(reordered_explanation, prediction=prediction)
        self.assertEqual(first.record_digest, second.record_digest)
        self.assertEqual([item["name"] for item in first.to_dict()["contributions"]], ["a_feature", "z_feature"])

    def test_additivity_uses_canonical_fsum_for_adversarial_permutations(self):
        module = self.module()
        prediction = module.PredictionObservationV1.from_dict(
            prediction_facts(
                observed_history_count=100,
                predicted_value=1.0,
                features=[
                    {"name": "a_large", "value": 1, "observed_at": "2026-09-30T11:58:00Z"},
                    {"name": "b_cancel", "value": 1, "observed_at": "2026-09-30T11:58:00Z"},
                    {"name": "c_small", "value": 1, "observed_at": "2026-09-30T11:58:00Z"},
                ],
            )
        )
        contributions = [
            {"name": "a_large", "value": 1e16},
            {"name": "b_cancel", "value": -1e16},
            {"name": "c_small", "value": 1.0},
        ]
        records = [
            module.PredictionExplanationV1.from_dict(
                explanation_facts(prediction, base_value=0.0, contributions=values), prediction=prediction
            )
            for values in (contributions, list(reversed(contributions)))
        ]
        self.assertEqual(records[0].record_digest, records[1].record_digest)

    def test_additivity_overflow_fails_closed_as_unavailable_explanation(self):
        module = self.module()
        prediction = module.PredictionObservationV1.from_dict(
            prediction_facts(
                observed_history_count=100,
                predicted_value=1.0,
                features=[
                    {"name": "a_large", "value": 1, "observed_at": "2026-09-30T11:58:00Z"},
                    {"name": "b_large", "value": 1, "observed_at": "2026-09-30T11:58:00Z"},
                ],
            )
        )
        explanation = explanation_facts(
            prediction,
            base_value=0.0,
            contributions=[
                {"name": "a_large", "value": 1e308},
                {"name": "b_large", "value": 1e308},
            ],
        )
        with self.assertRaisesRegex(ContractError, "^nonadditive_explanation$"):
            module.PredictionExplanationV1.from_dict(explanation, prediction=prediction)

    def test_huge_integer_numbers_fail_closed_without_raw_overflow(self):
        module = self.module()
        huge = 10**400
        prediction_cases = (
            (
                "feature",
                prediction_facts(
                    features=[
                        {"name": "changed_lines", "value": huge, "observed_at": "2026-09-30T11:58:00Z"}
                    ]
                ),
            ),
            ("prediction", prediction_facts(observed_history_count=100, predicted_value=huge)),
        )
        for name, payload in prediction_cases:
            with self.subTest(name=name), self.assertRaisesRegex(ContractError, f"^invalid_number: {name}$"):
                module.PredictionObservationV1.from_dict(payload)

        prediction = module.PredictionObservationV1.from_dict(
            prediction_facts(observed_history_count=100, predicted_value=0.7)
        )
        explanation_cases = (
            ("base_value", {"base_value": huge}),
            ("tolerance", {"tolerance": huge}),
            ("contribution", {"contributions": [{"name": "changed_lines", "value": huge}]}),
        )
        for name, changes in explanation_cases:
            with self.subTest(name=name), self.assertRaisesRegex(ContractError, f"^invalid_number: {name}$"):
                module.PredictionExplanationV1.from_dict(
                    explanation_facts(prediction, **changes), prediction=prediction
                )

    def test_replay_index_accepts_same_canonical_body_and_rejects_identity_reuse(self):
        module = self.module()
        replay = module.PredictionReplayIndex(max_entries=2)
        first = module.PredictionObservationV1.from_dict(
            prediction_facts(train_change_ids=["old-2", "old-1"])
        )
        same = module.PredictionObservationV1.from_dict(
            prediction_facts(train_change_ids=["old-1", "old-2"])
        )
        admitted = replay.admit(first)
        self.assertIsNot(first, admitted)
        self.assertEqual(first, admitted)
        self.assertIsNot(same, replay.admit(same))
        with self.assertRaisesRegex(ContractError, "prediction_replay_conflict"):
            replay.admit(module.PredictionObservationV1.from_dict(prediction_facts(context_digest="f" * 64)))
        with self.assertRaisesRegex(ContractError, "prediction_replay_conflict"):
            replay.admit(
                module.PredictionObservationV1.from_dict(
                    prediction_facts(repository_id="other/project", candidate_sha="f" * 40)
                )
            )

    def test_replay_index_is_bounded_fail_closed_and_detaches_duck_input(self):
        module = self.module()

        class MutableWire:
            def __init__(self, payload):
                self.payload = payload

            def to_dict(self):
                return self.payload

        with self.assertRaises(ContractError):
            module.PredictionReplayIndex(max_entries=0)
        replay = module.PredictionReplayIndex(max_entries=1)
        payload = prediction_facts()
        admitted = replay.admit(MutableWire(payload))
        payload["context_digest"] = "f" * 64
        self.assertEqual(admitted.to_dict()["context_digest"], "2" * 64)
        self.assertEqual(admitted, replay.admit(module.PredictionObservationV1.from_dict(prediction_facts())))
        with self.assertRaisesRegex(ContractError, "prediction_replay_capacity"):
            replay.admit(
                module.PredictionObservationV1.from_dict(
                    prediction_facts(prediction_id="pred-2", change_id="change-2", test_change_ids=["change-2"])
                )
            )

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
            prediction_facts(observed_history_count=100, predicted_value=0.7)
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
                    prediction_facts(observed_history_count=100, predicted_value=0.7)
                )
            ),
        }
        for name, example in examples.items():
            with self.subTest(name=name):
                schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(schema["properties"]["schema_version"], {"const": 1})
                self.assertEqual(set(schema["required"]), set(example))

    def test_field_complete_parser_mutation_matrix_fails_closed(self):
        module = self.module()
        invalid = {
            "prediction_id": "bad id",
            "repository_id": "",
            "change_id": "bad id",
            "candidate_sha": "f" * 39,
            "context_digest": "f" * 63,
            "spec_digest": "f" * 63,
            "profile_digest": "f" * 63,
            "feature_schema_version": "bad version",
            "feature_schema_digest": "f" * 63,
            "dataset_version": "bad version",
            "dataset_digest": "f" * 63,
            "split_digest": "f" * 63,
            "model_version": "bad version",
            "model_digest": "f" * 63,
            "preprocessing_version": "bad version",
            "preprocessing_digest": "f" * 63,
            "deterministic_evidence_digest": "f" * 63,
            "seed": -1,
            "predicted_at": "not-a-time",
            "first_check_started_at": "not-a-time",
            "train_before": "not-a-time",
            "test_after": "not-a-time",
            "train_change_ids": "old-1",
            "test_change_ids": [],
            "features": [],
            "required_history_count": 0,
            "observed_history_count": -1,
            "label_status": "product_pass",
            "predicted_value": float("inf"),
            "output_space": "percent",
            "authority_effect": "route",
        }
        for key, value in invalid.items():
            with self.subTest(key=key), self.assertRaises(ContractError):
                module.PredictionObservationV1.from_dict(prediction_facts(**{key: value}))

    def test_schema_and_parser_reject_missing_extra_types_bounds_and_nested_shapes(self):
        module = self.module()
        schema = json.loads((SCHEMAS / "prediction-observation.v1.schema.json").read_text(encoding="utf-8"))
        cases = []
        missing = prediction_facts()
        missing.pop("model_digest")
        cases.append(("missing", missing))
        cases.append(("extra", prediction_facts(unexpected=True)))
        cases.append(("type", prediction_facts(seed=True)))
        cases.append(("bound", prediction_facts(seed=2**32)))
        nested_extra = prediction_facts()
        nested_extra["features"][0]["unexpected"] = True
        cases.append(("nested_extra", nested_extra))
        nested_missing = prediction_facts()
        nested_missing["features"][0].pop("observed_at")
        cases.append(("nested_missing", nested_missing))
        for name, payload in cases:
            with self.subTest(name=name):
                with self.assertRaises((ContractError, KeyError)):
                    module.PredictionObservationV1.from_dict(payload)

    def test_explanation_field_matrix_and_schema_parser_structural_parity(self):
        module = self.module()
        prediction = module.PredictionObservationV1.from_dict(
            prediction_facts(observed_history_count=100, predicted_value=0.7)
        )
        invalid = {
            "prediction_digest": "f" * 63,
            "model_version": "bad version",
            "model_digest": "f" * 63,
            "background_dataset_version": "bad version",
            "background_dataset_digest": "f" * 63,
            "explainer_version": "bad version",
            "explainer_options_digest": "f" * 63,
            "deterministic_evidence_digest": "f" * 63,
            "output_space": "percent",
            "base_value": float("nan"),
            "contributions": [{"name": "changed_lines", "value": float("inf")}],
            "tolerance": -1,
            "authority_effect": "route",
        }
        for key, value in invalid.items():
            with self.subTest(key=key), self.assertRaises(ContractError):
                module.PredictionExplanationV1.from_dict(
                    explanation_facts(prediction, **{key: value}), prediction=prediction
                )

        schema = json.loads((SCHEMAS / "prediction-explanation.v1.schema.json").read_text(encoding="utf-8"))
        missing = explanation_facts(prediction)
        missing.pop("background_dataset_digest")
        nested = explanation_facts(prediction)
        nested["contributions"][0]["unexpected"] = True
        cases = (
            missing,
            explanation_facts(prediction, unexpected=True),
            explanation_facts(prediction, tolerance="small"),
            explanation_facts(prediction, tolerance=0.000002),
            nested,
        )
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises((ContractError, KeyError)):
                    module.PredictionExplanationV1.from_dict(payload, prediction=prediction)
