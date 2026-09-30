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
                    'first_check_started_at', 'outcome', 'features'}
        optional = {'feature_observed_at'}
        if not isinstance(source, dict) or not required <= set(source) or set(source) - required - optional:
            raise ContractError('closed_object_required')
        change_id = identity(source['change_id'])
        attempt_id = identity(source['attempt_id'])
        repository_id = identity(source['repository_id'])
        sha(source['candidate_sha'])
        observed = timestamp(source['observed_at'])
        check_started = timestamp(source['first_check_started_at'])
        feature_at = timestamp(source.get('feature_observed_at', source['observed_at']))
        if observed >= check_started or feature_at >= check_started:
            raise ContractError('feature_leakage')
        partition = 'train' if observed < cutoff else 'test'
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
                    first_check_started_at=source['first_check_started_at'], outcome=outcome,
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


def _metrics(labels, probabilities):
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
        'dataset_definition': {'schema_version': 1, 'target': 'first_independent_product_check_failure',
                               'unit': 'change', 'excluded_outcomes': sorted(_OTHER_LABELS)},
        'feature_schema': feature_schema, 'feature_schema_digest': canonical_digest(feature_schema),
        'split': {'kind': 'temporal_v1', 'at': split_at, 'train_change_ids': [], 'test_change_ids': []},
        'preprocessing': None, 'model': None, 'metrics': None,
        'excluded_labels': excluded, 'required_history_count': required_history,
        'observed_history_count': len(rows),
        'bounds': {'examples': len(rows), 'features': len(names), 'iterations': iterations, 'seed': seed},
    }
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
            'baseline': _metrics([test_labels[index] for index in indices], [baseline_probability] * len(indices)),
            'model': _metrics([test_labels[index] for index in indices], [probabilities[index] for index in indices]),
        }
    feature_schema = {'schema_version': 1, 'features': list(names), 'value_type': 'finite_number'}
    body = {
        'schema_version': 1, 'status': 'qualified', 'reason': None, 'authority_effect': 'none',
        'dataset_digest': canonical_digest(source_rows),
        'dataset_definition': {'schema_version': 1, 'target': 'first_independent_product_check_failure',
                               'unit': 'change', 'excluded_outcomes': sorted(_OTHER_LABELS)},
        'feature_schema': feature_schema, 'feature_schema_digest': canonical_digest(feature_schema),
        'split': {'kind': 'temporal_v1', 'at': split_at,
                  'train_change_ids': sorted(item['change_id'] for item in train),
                  'test_change_ids': sorted(item['change_id'] for item in test)},
        'preprocessing': preprocessing, 'preprocessing_digest': preprocessing_digest,
        'model': model, 'model_digest': model_digest,
        'metrics': {'baseline': _metrics(test_labels, [baseline_probability] * len(test_labels)),
                    'model': _metrics(test_labels, probabilities), 'by_project': projects},
        'excluded_labels': excluded, 'required_history_count': required_history,
        'observed_history_count': len(qualified),
        'bounds': {'examples': len(rows), 'features': len(names), 'iterations': iterations, 'seed': seed},
    }
    body['artifact_digest'] = canonical_digest(body)
    return body


def predict(artifact, *, prediction_id, repository_id, change_id, candidate_sha, predicted_at,
            first_check_started_at, features, feature_observed_at):
    if artifact.get('status') != 'qualified' or not artifact.get('model'):
        raise ContractError('model_not_qualified')
    names = artifact['model']['feature_names']
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
    test_ids = sorted(set(artifact['split']['test_change_ids']) | {change_id})
    observation = PredictionObservationV1.from_dict({
        'schema_version': 1, 'prediction_id': prediction_id, 'repository_id': repository_id,
        'change_id': change_id, 'candidate_sha': candidate_sha,
        'feature_schema_digest': artifact['feature_schema_digest'], 'dataset_digest': artifact['dataset_digest'],
        'split_digest': canonical_digest(artifact['split']), 'model_digest': artifact['model_digest'],
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
        'model_digest': artifact['model_digest'], 'background_digest': artifact['dataset_digest'],
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
    if artifact.get('status') != 'qualified' or not artifact.get('model'):
        return {'status': 'unavailable', 'reason': 'model_not_qualified', 'authority_effect': 'none'}
    try:
        prediction, explanation, envelope = predict(artifact, **kwargs)
        return {'status': 'available', 'prediction': prediction, 'explanation': explanation, **envelope}
    except ContractError as exc:
        return {'status': 'unavailable', 'reason': exc.code, 'authority_effect': 'none'}
