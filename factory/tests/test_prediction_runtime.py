import copy
import unittest

from adaptive_factory.contracts import ContractError, canonical_digest
from adaptive_factory.prediction_contracts import PredictionExplanationV1, PredictionObservationV1


def row(index, *, repository=None, outcome=None, observed=None):
    repository = repository or ('alpha/repo' if index % 2 else 'beta/repo')
    outcome = outcome or ('product_failure' if index % 3 == 0 else 'product_pass')
    day = index + 1
    observed = observed or f'2026-08-{day:02d}T09:00:00Z'
    return {
        'change_id': f'change-{index}', 'attempt_id': f'attempt-{index}',
        'repository_id': repository, 'candidate_sha': f'{index % 10}' * 40,
        'observed_at': observed, 'first_check_started_at': f'2026-08-{day:02d}T10:00:00Z',
        'outcome': outcome,
        'features': {'changed_lines': float(index * 8), 'test_count': float(25 - index)},
    }


class PredictionRuntimeTests(unittest.TestCase):
    def module(self):
        from adaptive_factory import prediction_runtime
        return prediction_runtime

    def history(self):
        return [row(index) for index in range(1, 19)]

    def test_pilot_is_deterministic_versioned_bounded_and_reports_portability(self):
        runtime = self.module()
        first = runtime.train_pilot(self.history(), split_at='2026-08-13T00:00:00Z', required_history=8, seed=17, iterations=64)
        second = runtime.train_pilot(self.history(), split_at='2026-08-13T00:00:00Z', required_history=8, seed=17, iterations=64)
        self.assertEqual(first, second)
        self.assertEqual(first['status'], 'qualified')
        self.assertEqual(first['schema_version'], 1)
        self.assertEqual(first['model']['kind'], 'bounded_logistic_v1')
        self.assertEqual(len(first['artifact_digest']), 64)
        digest_body = {key: value for key, value in first.items() if key != 'artifact_digest'}
        self.assertEqual(first['artifact_digest'], canonical_digest(digest_body))
        self.assertEqual(first['dataset_definition']['target'], 'first_independent_product_check_failure')
        self.assertEqual(first['feature_schema']['schema_version'], 1)
        self.assertEqual(set(first['metrics']), {'baseline', 'model', 'by_project'})
        self.assertEqual(set(first['metrics']['by_project']), {'alpha/repo', 'beta/repo'})
        self.assertEqual(set(first['metrics']['model']), {'auc', 'brier'})
        self.assertEqual(first['authority_effect'], 'none')
        self.assertLessEqual(first['bounds']['examples'], runtime.MAX_EXAMPLES)
        self.assertLessEqual(first['bounds']['iterations'], runtime.MAX_ITERATIONS)

    def test_assembler_rejects_future_features_change_split_and_bad_labels(self):
        runtime = self.module()
        future = self.history()
        future[0]['feature_observed_at'] = future[0]['first_check_started_at']
        with self.assertRaisesRegex(ContractError, 'feature_leakage'):
            runtime.train_pilot(future, split_at='2026-08-13T00:00:00Z')

        split = self.history()
        duplicate = copy.deepcopy(split[0])
        duplicate['attempt_id'] = 'later-attempt'
        duplicate['observed_at'] = '2026-08-14T09:00:00Z'
        duplicate['first_check_started_at'] = '2026-08-14T10:00:00Z'
        with self.assertRaisesRegex(ContractError, 'change_split_leakage'):
            runtime.train_pilot(split + [duplicate], split_at='2026-08-13T00:00:00Z')

        bad = self.history()
        bad[0]['outcome'] = 'success'
        with self.assertRaisesRegex(ContractError, 'invalid_label_status'):
            runtime.train_pilot(bad, split_at='2026-08-13T00:00:00Z')

    def test_non_product_labels_are_counted_not_coerced_and_small_data_is_not_qualified(self):
        runtime = self.module()
        history = self.history()
        history[1]['outcome'] = 'infrastructure_abort'
        history[2]['outcome'] = 'pending'
        history[3]['outcome'] = 'unavailable'
        artifact = runtime.train_pilot(history, split_at='2026-08-13T00:00:00Z', required_history=100)
        self.assertEqual(artifact['status'], 'not_qualified')
        self.assertEqual(artifact['excluded_labels'], {'infrastructure_abort': 1, 'pending': 1, 'unavailable': 1})
        self.assertIsNone(artifact['model'])
        self.assertEqual(artifact['authority_effect'], 'none')

    def test_prediction_and_explanation_are_bound_complete_and_additive(self):
        runtime = self.module()
        artifact = runtime.train_pilot(self.history(), split_at='2026-08-13T00:00:00Z', required_history=8, seed=17)
        prediction, explanation, envelope = runtime.predict(
            artifact,
            prediction_id='prediction-19', repository_id='alpha/repo', change_id='change-19',
            candidate_sha='9' * 40, predicted_at='2026-08-20T09:00:00Z',
            first_check_started_at='2026-08-20T10:00:00Z',
            features={'changed_lines': 152.0, 'test_count': 6.0},
            feature_observed_at='2026-08-20T08:59:00Z',
        )
        self.assertIsInstance(prediction, PredictionObservationV1)
        self.assertIsInstance(explanation, PredictionExplanationV1)
        self.assertEqual(envelope['authority_effect'], 'none')
        self.assertFalse(envelope['causal'])
        facts = prediction.to_dict()
        explained = explanation.to_dict()
        self.assertAlmostEqual(explained['base_value'] + sum(item['value'] for item in explained['contributions']), facts['predicted_value'])
        self.assertEqual({item['name'] for item in explained['contributions']}, {'changed_lines', 'test_count'})
        for forbidden in ('route', 'budget', 'permissions', 'required_tests', 'm8'):
            self.assertNotIn(forbidden, envelope)

    def test_missing_model_returns_unavailable_without_breaking_workflow(self):
        runtime = self.module()
        artifact = runtime.train_pilot(self.history()[:5], split_at='2026-08-04T00:00:00Z', required_history=100)
        result = runtime.predict_or_unavailable(artifact, features={'changed_lines': 1.0, 'test_count': 1.0})
        self.assertEqual(result, {'status': 'unavailable', 'reason': 'model_not_qualified', 'authority_effect': 'none'})


if __name__ == '__main__':
    unittest.main()
