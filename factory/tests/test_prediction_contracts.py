from copy import deepcopy
import importlib
import importlib.util
import unittest
from adaptive_factory.contracts import ContractError


def prediction_facts():
    return dict(schema_version=1, prediction_id='pred-1', repository_id='owner/project', change_id='change-1',
        candidate_sha='1'*40, feature_schema_digest='2'*64, dataset_digest='3'*64, split_digest='4'*64,
        model_digest='5'*64, preprocessing_digest='6'*64, seed=7,
        predicted_at='2026-09-30T11:59:00Z', first_check_started_at='2026-09-30T12:00:00Z',
        train_before='2026-09-29T00:00:00Z', test_after='2026-09-29T00:00:00Z',
        train_change_ids=['old-1'], test_change_ids=['change-1'],
        features=[dict(name='changed_lines', value=12, observed_at='2026-09-30T11:58:00Z')],
        required_history_count=100, observed_history_count=0, label_status='unknown',
        predicted_value=None, output_space='probability')


class PredictionContractTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('adaptive_factory.prediction_contracts'), 'observation contract missing')
        return importlib.import_module('adaptive_factory.prediction_contracts')

    def test_insufficient_history_is_not_qualified_and_has_no_authority_fields(self):
        module = self.module(); facts = prediction_facts(); record = module.PredictionObservationV1.from_dict(facts)
        self.assertEqual(record.status, 'not_qualified')
        for key in ('routing', 'budget', 'permissions', 'm8', 'checks'):
            changed = deepcopy(facts); changed[key] = 'changed'
            with self.assertRaises(ContractError): module.PredictionObservationV1.from_dict(changed)

    def test_leakage_temporal_split_and_unknown_labels_fail_closed(self):
        module = self.module()
        for mutation in ('late_feature', 'late_prediction', 'same_change', 'late_train', 'label', 'nan'):
            facts = prediction_facts()
            if mutation == 'late_feature': facts['features'][0]['observed_at'] = '2026-09-30T12:01:00Z'
            if mutation == 'late_prediction': facts['predicted_at'] = facts['first_check_started_at']
            if mutation == 'same_change': facts['train_change_ids'] = ['change-1']
            if mutation == 'late_train': facts['train_before'] = '2026-09-30T00:00:00Z'
            if mutation == 'label': facts['label_status'] = 'pass'
            if mutation == 'nan': facts['features'][0]['value'] = float('nan')
            with self.subTest(mutation=mutation), self.assertRaises(ContractError): module.PredictionObservationV1.from_dict(facts)

    def test_explanation_requires_full_additive_vector_and_bound_output_space(self):
        module = self.module(); facts = prediction_facts()
        facts.update(observed_history_count=100, label_status='product_failure', predicted_value=0.7)
        prediction = module.PredictionObservationV1.from_dict(facts)
        self.assertEqual(prediction.status, 'available')
        explanation = dict(schema_version=1, prediction_digest=prediction.record_digest, model_digest='5'*64,
            background_digest='7'*64, explainer_digest='8'*64, output_space='probability',
            base_value=0.2, contributions=[dict(name='changed_lines', value=0.5)], tolerance=0.000001)
        module.PredictionExplanationV1.from_dict(explanation, prediction=prediction)
        for key, value in [('contributions',[]), ('base_value',0.1), ('output_space','log_odds'), ('tolerance',1), ('model_digest','9'*64)]:
            changed = deepcopy(explanation); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError): module.PredictionExplanationV1.from_dict(changed, prediction=prediction)
