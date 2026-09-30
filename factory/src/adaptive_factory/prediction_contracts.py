"""Observation artifacts only. No model fitting, policy decision or routing hook."""
import math
from .contracts import ContractError
from .v15_contracts import FrozenWire, closed, version, identity, digest, sha, timestamp, integer, sequence


def number(value, name):
    if type(value) not in (int, float) or not math.isfinite(value): raise ContractError('invalid_number', name)
    return value


class PredictionObservationV1(FrozenWire):
    @classmethod
    def from_dict(cls, data):
        closed(data, ('schema_version', 'prediction_id', 'repository_id', 'change_id', 'candidate_sha',
            'feature_schema_digest', 'dataset_digest', 'split_digest', 'model_digest', 'preprocessing_digest',
            'seed', 'predicted_at', 'first_check_started_at', 'train_before', 'test_after',
            'train_change_ids', 'test_change_ids', 'features', 'required_history_count',
            'observed_history_count', 'label_status', 'predicted_value', 'output_space'))
        version(data)
        for key in ('prediction_id', 'repository_id', 'change_id'): identity(data[key])
        sha(data['candidate_sha'])
        for key in ('feature_schema_digest', 'dataset_digest', 'split_digest', 'model_digest', 'preprocessing_digest'): digest(data[key])
        integer(data['seed'], 'seed', 0, 2**32-1)
        predicted = timestamp(data['predicted_at']); check = timestamp(data['first_check_started_at'])
        train_end = timestamp(data['train_before']); test_start = timestamp(data['test_after'])
        if not train_end <= test_start <= predicted < check: raise ContractError('temporal_leakage')
        partitions = []
        for key in ('train_change_ids', 'test_change_ids'):
            ids = sequence(data[key], 1024)
            for item in ids: identity(item)
            if len(set(ids)) != len(ids): raise ContractError('duplicate_split_identity')
            partitions.append(set(ids))
        if partitions[0] & partitions[1] or data['change_id'] not in partitions[1]: raise ContractError('split_leakage')
        names = set()
        for feature in sequence(data['features'], 128):
            closed(feature, ('name', 'value', 'observed_at')); identity(feature['name']); number(feature['value'], 'feature')
            if feature['name'] in names: raise ContractError('duplicate_feature')
            names.add(feature['name'])
            if timestamp(feature['observed_at']) > predicted: raise ContractError('feature_leakage')
        if not names: raise ContractError('empty_feature_snapshot')
        integer(data['required_history_count'], 'required_history_count', 1, 1000000)
        integer(data['observed_history_count'], 'observed_history_count', 0, 1000000)
        if data['label_status'] not in ('unknown', 'product_failure', 'product_pass', 'infrastructure_abort', 'pending'):
            raise ContractError('invalid_label_status')
        if data['output_space'] not in ('probability', 'log_odds'): raise ContractError('invalid_output_space')
        if data['predicted_value'] is not None:
            value = number(data['predicted_value'], 'prediction')
            if data['output_space'] == 'probability' and not 0 <= value <= 1: raise ContractError('invalid_probability')
        return cls.freeze(data)

    @property
    def status(self):
        data = self.to_dict()
        if data['observed_history_count'] < data['required_history_count']: return 'not_qualified'
        if data['predicted_value'] is None: return 'unavailable'
        return 'available'


class PredictionExplanationV1(FrozenWire):
    @classmethod
    def from_dict(cls, data, *, prediction):
        closed(data, ('schema_version', 'prediction_digest', 'model_digest', 'background_digest',
                     'explainer_digest', 'output_space', 'base_value', 'contributions', 'tolerance'))
        version(data)
        for key in ('prediction_digest', 'model_digest', 'background_digest', 'explainer_digest'): digest(data[key])
        prediction = PredictionObservationV1.from_dict(prediction.to_dict()); facts = prediction.to_dict()
        if data['prediction_digest'] != prediction.record_digest or data['model_digest'] != facts['model_digest']:
            raise ContractError('prediction_binding_mismatch')
        if prediction.status != 'available' or data['output_space'] != facts['output_space']:
            raise ContractError('explanation_unavailable')
        base = number(data['base_value'], 'base_value'); tolerance = number(data['tolerance'], 'tolerance')
        if not 0 <= tolerance <= 0.000001: raise ContractError('excessive_tolerance')
        names = set(); total = base
        for contribution in sequence(data['contributions'], 128):
            closed(contribution, ('name', 'value')); identity(contribution['name'])
            if contribution['name'] in names: raise ContractError('duplicate_contribution')
            names.add(contribution['name']); total += number(contribution['value'], 'contribution')
        if names != {f['name'] for f in facts['features']}: raise ContractError('incomplete_vector')
        if abs(total-facts['predicted_value']) > tolerance: raise ContractError('nonadditive_explanation')
        return cls.freeze(data)
