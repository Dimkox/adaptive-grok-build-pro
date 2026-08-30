from __future__ import annotations

import json
import unittest
from pathlib import Path

from _support import policy_data
from adaptive_trust_ci.github import GitHubClient
from adaptive_trust_ci.policy import Policy


ROOT = Path(__file__).resolve().parents[2]
APP_ID = 4242


class DisposablePolicyTransitionTests(unittest.TestCase):
    def test_automated_only_cutover_never_opens_merge_and_keeps_one_production_gate(self) -> None:
        checked_in = json.loads((
            ROOT / 'trust-ci/config/policy.example.json'
        ).read_text(encoding='utf-8'))
        self.assertEqual(checked_in['approval_rules'], [])
        source = policy_data()
        source['approval_rules'] = []
        source['promotion'] = {'environments': ['production'], 'max_ttl_seconds': 900}
        policy = Policy.from_dict(source)
        self.assertEqual(policy.approval_rules, ())
        old_context = 'adaptive-trust-ci/verified@old000000000'
        new_context = policy.check_name
        old = {'context': old_context, 'app_id': APP_ID}
        new = {'context': new_context, 'app_id': APP_ID}

        class Transport:
            def __init__(self):
                self.required = [old]
                self.calls = []

            def request(self, method, url, headers, body=None):
                self.calls.append((method, url, body))
                if method == 'GET':
                    return 200, {'required_status_checks': {'strict': True, 'checks': self.required}}
                self.required = list(body['required_status_checks']['checks'])
                return 200, {'required_status_checks': {'strict': True, 'checks': self.required}}

        transport = Transport()

        def merge_allowed(exact_sha_results: dict[str, str]) -> bool:
            return bool(transport.required) and all(
                exact_sha_results.get(check['context']) == 'success' and check['app_id'] == APP_ID
                for check in transport.required
            )

        fake_token = '-'.join(('disposable', 'admin', 'token'))
        client = GitHubClient(token=fake_token, transport=transport, api_url='https://example.test')
        client.cutover_branch_protection(
            'Dimkox/adaptive-grok-build-pro', 'main',
            old_check_name=old_context, old_app_id=APP_ID,
            new_check_name=new_context, new_app_id=APP_ID,
        )
        puts = [body['required_status_checks']['checks'] for method, _url, body in transport.calls if method == 'PUT']
        self.assertEqual(puts, [[old, new], [new]])
        self.assertFalse(merge_allowed({new_context: 'needs_approval'}))
        self.assertTrue(merge_allowed({new_context: 'success'}))

        # The policy carries no dev/PR/merge approval rule. Its only human scope
        # is the separate final production promotion envelope contract.
        promotion_schema = json.loads((
            ROOT / 'engineering/contracts/schemas/promotion-envelope-v1.schema.json'
        ).read_text(encoding='utf-8'))
        self.assertEqual(policy.promotion.environments, ('production',))
        self.assertIn('signature', promotion_schema['required'])
        self.assertNotIn('approval', json.dumps(promotion_schema).lower())


if __name__ == '__main__':
    unittest.main()
