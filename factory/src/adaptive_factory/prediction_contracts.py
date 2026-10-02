"""Pure observation-only prediction artifacts with no workflow authority."""

import math

from .contracts import ContractError
from .v15_contracts import FrozenWire, closed, digest, identity, integer, sequence, sha, timestamp, version


def _number(value, name):
    if type(value) not in (int, float):
        raise ContractError("invalid_number", name)
    try:
        finite = math.isfinite(value)
    except (OverflowError, ValueError) as exc:
        raise ContractError("invalid_number", name) from exc
    if not finite:
        raise ContractError("invalid_number", name)
    return value


class PredictionObservationV1(FrozenWire):
    """A bounded snapshot made before the first independent check starts."""

    @classmethod
    def from_dict(cls, data):
        closed(
            data,
            (
                "schema_version",
                "prediction_id",
                "repository_id",
                "change_id",
                "candidate_sha",
                "context_digest",
                "spec_digest",
                "profile_digest",
                "feature_schema_version",
                "feature_schema_digest",
                "dataset_version",
                "dataset_digest",
                "split_digest",
                "model_version",
                "model_digest",
                "preprocessing_version",
                "preprocessing_digest",
                "deterministic_evidence_digest",
                "seed",
                "predicted_at",
                "first_check_started_at",
                "train_before",
                "test_after",
                "train_change_ids",
                "test_change_ids",
                "features",
                "required_history_count",
                "observed_history_count",
                "label_status",
                "predicted_value",
                "output_space",
                "authority_effect",
            ),
        )
        version(data)
        for key in (
            "prediction_id",
            "repository_id",
            "change_id",
            "feature_schema_version",
            "dataset_version",
            "model_version",
            "preprocessing_version",
        ):
            identity(data[key])
        sha(data["candidate_sha"])
        for key in (
            "context_digest",
            "spec_digest",
            "profile_digest",
            "feature_schema_digest",
            "dataset_digest",
            "split_digest",
            "model_digest",
            "preprocessing_digest",
            "deterministic_evidence_digest",
        ):
            digest(data[key])
        integer(data["seed"], "seed", 0, 2**32 - 1)

        predicted_at = timestamp(data["predicted_at"])
        first_check_started_at = timestamp(data["first_check_started_at"])
        train_before = timestamp(data["train_before"])
        test_after = timestamp(data["test_after"])
        if not train_before <= test_after <= predicted_at < first_check_started_at:
            raise ContractError("temporal_leakage")

        normalized = dict(data)
        partitions = []
        for key in ("train_change_ids", "test_change_ids"):
            values = sequence(data[key], 1024)
            for item in values:
                identity(item)
            if len(set(values)) != len(values):
                raise ContractError("duplicate_split_identity")
            partitions.append(set(values))
            normalized[key] = sorted(values)
        if partitions[0] & partitions[1] or data["change_id"] not in partitions[1]:
            raise ContractError("split_leakage")

        feature_names = set()
        for feature in sequence(data["features"], 128):
            closed(feature, ("name", "value", "observed_at"))
            identity(feature["name"])
            _number(feature["value"], "feature")
            if feature["name"] in feature_names:
                raise ContractError("duplicate_feature")
            feature_names.add(feature["name"])
            if timestamp(feature["observed_at"]) > predicted_at:
                raise ContractError("feature_leakage")
        if not feature_names:
            raise ContractError("empty_feature_snapshot")
        normalized["features"] = sorted(data["features"], key=lambda feature: feature["name"])

        integer(data["required_history_count"], "required_history_count", 1, 1_000_000)
        integer(data["observed_history_count"], "observed_history_count", 0, 1_000_000)
        if data["label_status"] not in ("unknown", "pending"):
            raise ContractError("invalid_label_status")
        if data["output_space"] not in ("probability", "log_odds"):
            raise ContractError("invalid_output_space")
        if data["predicted_value"] is not None:
            predicted_value = _number(data["predicted_value"], "prediction")
            if data["output_space"] == "probability" and not 0 <= predicted_value <= 1:
                raise ContractError("invalid_probability")
        if data["authority_effect"] != "none":
            raise ContractError("invalid_authority_effect")
        return cls.freeze(normalized)

    @property
    def status(self):
        data = self.to_dict()
        if data["observed_history_count"] < data["required_history_count"]:
            return "not_qualified"
        if data["predicted_value"] is None:
            return "unavailable"
        return "available"


class PredictionExplanationV1(FrozenWire):
    """A complete additive explanation bound to one available prediction."""

    @classmethod
    def from_dict(cls, data, *, prediction):
        closed(
            data,
            (
                "schema_version",
                "prediction_digest",
                "model_version",
                "model_digest",
                "background_dataset_version",
                "background_dataset_digest",
                "explainer_version",
                "explainer_options_digest",
                "deterministic_evidence_digest",
                "output_space",
                "base_value",
                "contributions",
                "tolerance",
                "authority_effect",
            ),
        )
        version(data)
        for key in ("model_version", "background_dataset_version", "explainer_version"):
            identity(data[key])
        for key in (
            "prediction_digest",
            "model_digest",
            "background_dataset_digest",
            "explainer_options_digest",
            "deterministic_evidence_digest",
        ):
            digest(data[key])

        admitted_prediction = PredictionObservationV1.from_dict(prediction.to_dict())
        facts = admitted_prediction.to_dict()
        if (
            data["prediction_digest"] != admitted_prediction.record_digest
            or data["model_digest"] != facts["model_digest"]
            or data["model_version"] != facts["model_version"]
        ):
            raise ContractError("prediction_binding_mismatch")
        if admitted_prediction.status != "available" or data["output_space"] != facts["output_space"]:
            raise ContractError("explanation_unavailable")

        base_value = _number(data["base_value"], "base_value")
        tolerance = _number(data["tolerance"], "tolerance")
        if not 0 <= tolerance <= 0.000001:
            raise ContractError("excessive_tolerance")
        names = set()
        validated_contributions = []
        for contribution in sequence(data["contributions"], 128):
            closed(contribution, ("name", "value"))
            identity(contribution["name"])
            if contribution["name"] in names:
                raise ContractError("duplicate_contribution")
            names.add(contribution["name"])
            value = _number(contribution["value"], "contribution")
            validated_contributions.append((contribution["name"], value, contribution))
        if names != {feature["name"] for feature in facts["features"]}:
            raise ContractError("incomplete_vector")
        validated_contributions.sort(key=lambda item: item[0])
        try:
            total = math.fsum([base_value, *(item[1] for item in validated_contributions)])
        except (OverflowError, ValueError) as exc:
            raise ContractError("nonadditive_explanation") from exc
        if abs(total - facts["predicted_value"]) > tolerance:
            raise ContractError("nonadditive_explanation")
        if data["authority_effect"] != "none":
            raise ContractError("invalid_authority_effect")
        normalized = dict(data)
        normalized["contributions"] = [item[2] for item in validated_contributions]
        return cls.freeze(normalized)


class PredictionReplayIndex:
    """Process-local validator for an append-only store's prediction-id replay rule."""

    def __init__(self, *, max_entries):
        integer(max_entries, "max_entries", 1, 1_000_000)
        self._max_entries = max_entries
        self._digests = {}

    def admit(self, prediction):
        admitted = PredictionObservationV1.from_dict(prediction.to_dict())
        prediction_id = admitted.to_dict()["prediction_id"]
        previous = self._digests.get(prediction_id)
        if previous is None:
            if len(self._digests) >= self._max_entries:
                raise ContractError("prediction_replay_capacity")
            self._digests[prediction_id] = admitted.record_digest
            return admitted
        if previous != admitted.record_digest:
            raise ContractError("prediction_replay_conflict", prediction_id)
        return admitted
