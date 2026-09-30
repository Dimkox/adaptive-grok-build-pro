"""Deterministic bounded observation-only prediction pilot for Factory v1.5."""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from .contracts import ContractError, canonical_digest
from .prediction_contracts import PredictionExplanationV1, PredictionObservationV1
from .v15_contracts import identity, sha, timestamp


MAX_EXAMPLES = 4096
MAX_FEATURES = 32
MAX_ITERATIONS = 256
_PRODUCT_LABELS = {'product_failure', 'product_pass'}
_OTHER_LABELS = {'infrastructure_abort', 'pending', 'unavailable'}


def _finite(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ContractError('invalid_number', name)
    return float(value)


def _sigmoid(value):
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    direct = math.exp(value)
    return direct / (1.0 + direct)


def _product_label(outcome):
    return 1.0 if outcome == 'product_failure' else 0.0


def _validate(rows, split_at):
    if not isinstance(rows, list) or not rows or len(rows) > MAX_EXAMPLES:
        raise ContractError('invalid_collection', 'history')
    cutoff = timestamp(split_at)
    feature_names = None
    partitions = defaultdict(set)
    qualified = []
    excluded = Counter()
    canonical_rows = []
    for source in rows:
        required = {'change_id', 'attempt_id', 'repository_id', 'candidate_sha', 'observed_at',
                    'first_check_started_at', 'outcome_observed_at', 'outcome', 'features'}
        optional = {'feature_observed_at'}
        if not isinstance(source, dict) or not required <= set(source) or set(source) - required - optional:
            raise ContractError('closed_object_required')
        change_id = identity(source['change_id'])
        attempt_id = identity(source['attempt_id'])
        repository_id = identity(source['repository_id'])
        sha(source['candidate_sha'])
        observed = timestamp(source['observed_at'])
        check_started = timestamp(source['first_check_started_at'])
        outcome_observed = timestamp(source['outcome_observed_at'])
        feature_at = timestamp(source.get('feature_observed_at', source['observed_at']))
        if feature_at > observed or observed >= check_started:
            raise ContractError('feature_leakage')
        if outcome_observed < check_started:
            raise ContractError('label_time_invalid')
        partition = 'train' if outcome_observed < cutoff else 'test'
        partitions[change_id].add(partition)
        if len(partitions[change_id]) > 1:
            raise ContractError('change_split_leakage')
        outcome = source['outcome']
        if outcome not in _PRODUCT_LABELS and outcome not in _OTHER_LABELS:
            raise ContractError('invalid_label_status')
        features = source['features']
        if not isinstance(features, dict) or not features or len(features) > MAX_FEATURES:
            raise ContractError('invalid_collection', 'features')
        names = tuple(sorted(features))
        if feature_names is None:
            feature_names = names
        if names != feature_names:
            raise ContractError('feature_schema_mismatch')
        values = {name: _finite(features[name], name) for name in names}
        item = dict(change_id=change_id, attempt_id=attempt_id, repository_id=repository_id,
                    candidate_sha=source['candidate_sha'], observed_at=source['observed_at'],
                    first_check_started_at=source['first_check_started_at'],
                    outcome_observed_at=source['outcome_observed_at'], outcome=outcome,
                    features=values, partition=partition)
        canonical_rows.append(item)
        if outcome in _PRODUCT_LABELS:
            qualified.append(item)
        else:
            excluded[outcome] += 1
    # The first independent check defines the label; multiple attempts of one change
    # cannot silently overweight the model.
    first_by_change = {}
    for item in sorted(qualified, key=lambda value: (value['first_check_started_at'], value['attempt_id'])):
        first_by_change.setdefault(item['change_id'], item)
    return list(first_by_change.values()), dict(sorted(excluded.items())), tuple(feature_names), canonical_rows


def binary_metrics(labels, probabilities):
    if not isinstance(labels, list) or not isinstance(probabilities, list) or len(labels) != len(probabilities):
        raise ContractError('invalid_metric_input')
    if any(label not in (0.0, 1.0) for label in labels):
        raise ContractError('invalid_metric_input')
    if any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1 for value in probabilities):
        raise ContractError('invalid_metric_input')
    if not labels:
        return {'auc': None, 'brier': None}
    brier = sum((prediction - label) ** 2 for label, prediction in zip(labels, probabilities)) / len(labels)
    positives = [index for index, label in enumerate(labels) if label == 1.0]
    negatives = [index for index, label in enumerate(labels) if label == 0.0]
    auc = None
    if positives and negatives:
        score = 0.0
        for positive in positives:
            for negative in negatives:
                score += 1.0 if probabilities[positive] > probabilities[negative] else 0.5 if probabilities[positive] == probabilities[negative] else 0.0
        auc = score / (len(positives) * len(negatives))
    return {'auc': auc, 'brier': brier}


def _not_qualified(*, rows, excluded, names, required_history, split_at, seed, iterations, reason):
    feature_schema = {'schema_version': 1, 'features': list(names), 'value_type': 'finite_number'}
    body = {
        'schema_version': 1, 'status': 'not_qualified', 'reason': reason,
        'authority_effect': 'none', 'dataset_digest': canonical_digest(rows),
        'dataset_manifest': rows, 'training_manifest': [], 'training_digest': canonical_digest([]),
        'dataset_definition': {'schema_version': 1, 'target': 'first_independent_product_check_failure',
                               'unit': 'change', 'excluded_outcomes': sorted(_OTHER_LABELS)},
        'feature_schema': feature_schema, 'feature_schema_digest': canonical_digest(feature_schema),
        'split': {'kind': 'temporal_v1', 'at': split_at, 'train_change_ids': [], 'test_change_ids': []},
        'preprocessing': None, 'model': None, 'metrics': None,
        'excluded_labels': excluded, 'required_history_count': required_history,
        'observed_history_count': len(rows),
        'bounds': {'examples': len(rows), 'features': len(names), 'iterations': iterations, 'seed': seed},
    }
    body['split_digest'] = canonical_digest(body['split'])
    body['artifact_digest'] = canonical_digest(body)
    return body


def train_pilot(rows, *, split_at, required_history=8, seed=0, iterations=96):
    """Fit a small fixed arithmetic logistic pilot; never changes workflow authority."""
    if type(required_history) is not int or not 2 <= required_history <= MAX_EXAMPLES:
        raise ContractError('invalid_integer', 'required_history')
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ContractError('invalid_integer', 'seed')
    if type(iterations) is not int or not 1 <= iterations <= MAX_ITERATIONS:
        raise ContractError('invalid_integer', 'iterations')
    qualified, excluded, names, source_rows = _validate(rows, split_at)
    train = [item for item in qualified if item['partition'] == 'train']
    test = [item for item in qualified if item['partition'] == 'test']
    if len(qualified) < required_history or len(train) < 2 or not test:
        return _not_qualified(rows=source_rows, excluded=excluded, names=names,
                              required_history=required_history, split_at=split_at, seed=seed,
                              iterations=iterations, reason='insufficient_temporal_history')
    train_labels = [_product_label(item['outcome']) for item in train]
    if len(set(train_labels)) < 2:
        return _not_qualified(rows=source_rows, excluded=excluded, names=names,
                              required_history=required_history, split_at=split_at, seed=seed,
                              iterations=iterations, reason='single_class_training_data')
    means = {name: sum(item['features'][name] for item in train) / len(train) for name in names}
    scales = {}
    for name in names:
        variance = sum((item['features'][name] - means[name]) ** 2 for item in train) / len(train)
        scales[name] = math.sqrt(variance) or 1.0
    positive_rate = sum(train_labels) / len(train_labels)
    intercept = math.log(positive_rate / (1.0 - positive_rate))
    weights = {name: 0.0 for name in names}
    learning_rate = 0.2
    for _ in range(iterations):
        intercept_gradient = 0.0
        gradients = {name: 0.0 for name in names}
        for item, label in zip(train, train_labels):
            normalized = {name: (item['features'][name] - means[name]) / scales[name] for name in names}
            probability = _sigmoid(intercept + sum(weights[name] * normalized[name] for name in names))
            error = probability - label
            intercept_gradient += error
            for name in names:
                gradients[name] += error * normalized[name]
        intercept -= learning_rate * intercept_gradient / len(train)
        for name in names:
            weights[name] -= learning_rate * (gradients[name] / len(train) + 0.01 * weights[name])
    model = {'schema_version': 1, 'kind': 'bounded_logistic_v1', 'output_space': 'log_odds',
             'feature_names': list(names), 'intercept': intercept, 'weights': weights,
             'seed': seed, 'iterations': iterations}
    preprocessing = {'schema_version': 1, 'kind': 'standardize_v1', 'means': means, 'scales': scales}
    model_digest = canonical_digest(model)
    preprocessing_digest = canonical_digest(preprocessing)
    baseline_probability = positive_rate
    test_labels = [_product_label(item['outcome']) for item in test]
    probabilities = []
    for item in test:
        score = intercept + sum(weights[name] * ((item['features'][name] - means[name]) / scales[name]) for name in names)
        probabilities.append(_sigmoid(score))
    projects = {}
    for repository in sorted({item['repository_id'] for item in test}):
        indices = [index for index, item in enumerate(test) if item['repository_id'] == repository]
        projects[repository] = {
            'baseline': binary_metrics([test_labels[index] for index in indices], [baseline_probability] * len(indices)),
            'model': binary_metrics([test_labels[index] for index in indices], [probabilities[index] for index in indices]),
        }
    feature_schema = {'schema_version': 1, 'features': list(names), 'value_type': 'finite_number'}
    body = {
        'schema_version': 1, 'status': 'qualified', 'reason': None, 'authority_effect': 'none',
        'dataset_digest': canonical_digest(source_rows),
        'dataset_manifest': source_rows, 'training_manifest': train, 'training_digest': canonical_digest(train),
        'dataset_definition': {'schema_version': 1, 'target': 'first_independent_product_check_failure',
                               'unit': 'change', 'excluded_outcomes': sorted(_OTHER_LABELS)},
        'feature_schema': feature_schema, 'feature_schema_digest': canonical_digest(feature_schema),
        'split': {'kind': 'temporal_v1', 'at': split_at,
                  'train_change_ids': sorted(item['change_id'] for item in train),
                  'test_change_ids': sorted(item['change_id'] for item in test)},
        'preprocessing': preprocessing, 'preprocessing_digest': preprocessing_digest,
        'model': model, 'model_digest': model_digest,
        'metrics': {'baseline': binary_metrics(test_labels, [baseline_probability] * len(test_labels)),
                    'model': binary_metrics(test_labels, probabilities), 'by_project': projects},
        'excluded_labels': excluded, 'required_history_count': required_history,
        'observed_history_count': len(qualified),
        'bounds': {'examples': len(rows), 'features': len(names), 'iterations': iterations, 'seed': seed},
    }
    body['split_digest'] = canonical_digest(body['split'])
    body['artifact_digest'] = canonical_digest(body)
    return body


def _validate_qualified_artifact(artifact):
    if not isinstance(artifact, dict):
        raise ContractError('invalid_model_artifact')
    expected = {
        'schema_version', 'status', 'reason', 'authority_effect', 'dataset_digest',
        'dataset_manifest', 'training_manifest', 'training_digest', 'dataset_definition',
        'feature_schema', 'feature_schema_digest', 'split', 'split_digest', 'preprocessing',
        'preprocessing_digest', 'model', 'model_digest', 'metrics', 'excluded_labels',
        'required_history_count', 'observed_history_count', 'bounds', 'artifact_digest',
    }
    if set(artifact) != expected:
        raise ContractError('closed_object_required')
    body = {key: value for key, value in artifact.items() if key != 'artifact_digest'}
    if artifact.get('artifact_digest') != canonical_digest(body):
        raise ContractError('artifact_digest_mismatch')
    if artifact.get('schema_version') != 1 or artifact.get('status') != 'qualified' or artifact.get('authority_effect') != 'none':
        raise ContractError('invalid_model_artifact')
    manifest = artifact.get('dataset_manifest')
    training = artifact.get('training_manifest')
    if not isinstance(manifest, list) or not isinstance(training, list):
        raise ContractError('invalid_model_artifact')
    if artifact.get('dataset_digest') != canonical_digest(manifest):
        raise ContractError('dataset_digest_mismatch')
    if artifact.get('training_digest') != canonical_digest(training):
        raise ContractError('training_digest_mismatch')
    if any(not isinstance(item, dict) or item.get('partition') != 'train' or item.get('outcome') not in _PRODUCT_LABELS for item in training):
        raise ContractError('invalid_training_manifest')
    if any(item not in manifest for item in training):
        raise ContractError('training_manifest_mismatch')
    definition = artifact.get('dataset_definition')
    expected_definition = {'schema_version': 1, 'target': 'first_independent_product_check_failure',
                           'unit': 'change', 'excluded_outcomes': sorted(_OTHER_LABELS)}
    if definition != expected_definition:
        raise ContractError('invalid_dataset_definition')
    feature_schema = artifact.get('feature_schema')
    if not isinstance(feature_schema, dict) or set(feature_schema) != {'schema_version', 'features', 'value_type'}:
        raise ContractError('invalid_feature_schema')
    names = feature_schema.get('features')
    if (feature_schema.get('schema_version'), feature_schema.get('value_type')) != (1, 'finite_number'):
        raise ContractError('invalid_feature_schema')
    if not isinstance(names, list) or not names or len(names) > MAX_FEATURES or any(not isinstance(name, str) for name in names):
        raise ContractError('invalid_feature_schema')
    if names != sorted(set(names)):
        raise ContractError('invalid_feature_schema')
    for name in names:
        identity(name)
    if artifact.get('feature_schema_digest') != canonical_digest(feature_schema):
        raise ContractError('feature_schema_digest_mismatch')
    split = artifact.get('split')
    if not isinstance(split, dict) or set(split) != {'kind', 'at', 'train_change_ids', 'test_change_ids'}:
        raise ContractError('invalid_split')
    if split.get('kind') != 'temporal_v1' or artifact.get('split_digest') != canonical_digest(split):
        raise ContractError('split_digest_mismatch')
    timestamp(split.get('at'))
    train_ids = split.get('train_change_ids')
    test_ids = split.get('test_change_ids')
    if not isinstance(train_ids, list) or not isinstance(test_ids, list):
        raise ContractError('invalid_split')
    if any(not isinstance(change_id, str) for change_id in train_ids + test_ids):
        raise ContractError('invalid_split')
    if set(train_ids) & set(test_ids):
        raise ContractError('invalid_split')
    if len(train_ids) != len(set(train_ids)) or len(test_ids) != len(set(test_ids)):
        raise ContractError('invalid_split')
    for change_id in train_ids + test_ids:
        identity(change_id)
    if sorted(item.get('change_id') for item in training if isinstance(item, dict)) != sorted(train_ids):
        raise ContractError('training_split_mismatch')
    preprocessing = artifact.get('preprocessing')
    model = artifact.get('model')
    if not isinstance(preprocessing, dict) or set(preprocessing) != {'schema_version', 'kind', 'means', 'scales'}:
        raise ContractError('invalid_preprocessing')
    if artifact.get('preprocessing_digest') != canonical_digest(preprocessing):
        raise ContractError('preprocessing_digest_mismatch')
    if (preprocessing.get('schema_version'), preprocessing.get('kind')) != (1, 'standardize_v1'):
        raise ContractError('invalid_preprocessing')
    if not isinstance(preprocessing.get('means'), dict) or not isinstance(preprocessing.get('scales'), dict):
        raise ContractError('preprocessing_shape_mismatch')
    if set(preprocessing['means']) != set(names) or set(preprocessing['scales']) != set(names):
        raise ContractError('preprocessing_shape_mismatch')
    for name in names:
        _finite(preprocessing['means'][name], name)
        if _finite(preprocessing['scales'][name], name) <= 0:
            raise ContractError('invalid_scale')
    if not isinstance(model, dict) or set(model) != {'schema_version', 'kind', 'output_space', 'feature_names', 'intercept', 'weights', 'seed', 'iterations'}:
        raise ContractError('invalid_model')
    if artifact.get('model_digest') != canonical_digest(model):
        raise ContractError('model_digest_mismatch')
    if (model.get('schema_version'), model.get('kind'), model.get('output_space')) != (1, 'bounded_logistic_v1', 'log_odds'):
        raise ContractError('invalid_model')
    if not isinstance(model.get('weights'), dict):
        raise ContractError('model_shape_mismatch')
    if model.get('feature_names') != names or set(model['weights']) != set(names):
        raise ContractError('model_shape_mismatch')
    _finite(model.get('intercept'), 'intercept')
    for name in names:
        _finite(model['weights'][name], name)
    if type(model.get('iterations')) is not int or not 1 <= model['iterations'] <= MAX_ITERATIONS:
        raise ContractError('invalid_model')
    if type(model.get('seed')) is not int or not 0 <= model['seed'] <= 2**32 - 1:
        raise ContractError('invalid_model')
    bounds = artifact.get('bounds')
    if not isinstance(bounds, dict) or set(bounds) != {'examples', 'features', 'iterations', 'seed'}:
        raise ContractError('invalid_bounds')
    if bounds.get('features') != len(names) or bounds.get('iterations') != model['iterations'] or bounds.get('seed') != model['seed']:
        raise ContractError('model_bounds_mismatch')
    if type(bounds.get('examples')) is not int or not 1 <= bounds['examples'] <= MAX_EXAMPLES:
        raise ContractError('invalid_bounds')
    return names


def predict(artifact, *, prediction_id, repository_id, change_id, candidate_sha, predicted_at,
            first_check_started_at, features, feature_observed_at):
    if not isinstance(artifact, dict) or artifact.get('status') != 'qualified' or not artifact.get('model'):
        raise ContractError('model_not_qualified')
    names = _validate_qualified_artifact(artifact)
    if not isinstance(features, dict) or sorted(features) != names:
        raise ContractError('feature_schema_mismatch')
    values = {name: _finite(features[name], name) for name in names}
    if timestamp(feature_observed_at) > timestamp(predicted_at):
        raise ContractError('feature_leakage')
    if timestamp(predicted_at) >= timestamp(first_check_started_at):
        raise ContractError('temporal_leakage')
    preprocessing = artifact['preprocessing']
    model = artifact['model']
    normalized = {name: (values[name] - preprocessing['means'][name]) / preprocessing['scales'][name] for name in names}
    contributions = [{'name': name, 'value': model['weights'][name] * normalized[name]} for name in names]
    score = model['intercept'] + sum(item['value'] for item in contributions)
    if not math.isfinite(score):
        raise ContractError('invalid_prediction')
    test_ids = sorted(set(artifact['split']['test_change_ids']) | {change_id})
    observation = PredictionObservationV1.from_dict({
        'schema_version': 1, 'prediction_id': prediction_id, 'repository_id': repository_id,
        'change_id': change_id, 'candidate_sha': candidate_sha,
        'feature_schema_digest': artifact['feature_schema_digest'], 'dataset_digest': artifact['dataset_digest'],
        'split_digest': artifact['split_digest'], 'model_digest': artifact['model_digest'],
        'preprocessing_digest': artifact['preprocessing_digest'], 'seed': artifact['bounds']['seed'],
        'predicted_at': predicted_at, 'first_check_started_at': first_check_started_at,
        'train_before': artifact['split']['at'], 'test_after': artifact['split']['at'],
        'train_change_ids': artifact['split']['train_change_ids'], 'test_change_ids': test_ids,
        'features': [{'name': name, 'value': values[name], 'observed_at': feature_observed_at} for name in names],
        'required_history_count': artifact['required_history_count'],
        'observed_history_count': artifact['observed_history_count'], 'label_status': 'pending',
        'predicted_value': score, 'output_space': 'log_odds',
    })
    explanation = PredictionExplanationV1.from_dict({
        'schema_version': 1, 'prediction_digest': observation.record_digest,
        'model_digest': artifact['model_digest'], 'background_digest': artifact['training_digest'],
        'explainer_digest': canonical_digest({'kind': 'linear_log_odds_v1', 'model_digest': artifact['model_digest']}),
        'output_space': 'log_odds', 'base_value': model['intercept'],
        'contributions': contributions, 'tolerance': 0.000000001,
    }, prediction=observation)
    return observation, explanation, {
        'status': 'available', 'authority_effect': 'none', 'causal': False,
        'model_digest': artifact['model_digest'], 'prediction_digest': observation.record_digest,
        'explanation_digest': explanation.record_digest,
    }


def predict_or_unavailable(artifact, **kwargs):
    if not isinstance(artifact, dict) or artifact.get('status') != 'qualified' or not artifact.get('model'):
        return {'status': 'unavailable', 'reason': 'model_not_qualified', 'authority_effect': 'none'}
    try:
        prediction, explanation, envelope = predict(artifact, **kwargs)
        return {'status': 'available', 'prediction': prediction, 'explanation': explanation, **envelope}
    except ContractError as exc:
        return {'status': 'unavailable', 'reason': exc.code, 'authority_effect': 'none'}
