from __future__ import annotations

import copy
import unittest

from _support import policy_data
from adaptive_trust_ci.policy import Policy, PolicyError


class PolicyTests(unittest.TestCase):
    def test_digest_is_stable_for_equivalent_objects(self) -> None:
        first = policy_data()
        second = copy.deepcopy(first)
        second['allowed_repositories'] = list(reversed(second['allowed_repositories']))
        self.assertEqual(Policy.from_dict(first).digest, Policy.from_dict(second).digest)

    def test_policy_change_changes_digest(self) -> None:
        first = Policy.from_dict(policy_data())
        changed = policy_data()
        changed['max_attempts'] = 4
        self.assertNotEqual(first.digest, Policy.from_dict(changed).digest)

    def test_holdout_digest_changes_policy_digest(self) -> None:
        first = Policy.from_dict(policy_data(holdout_digest='d' * 64))
        second = Policy.from_dict(policy_data(holdout_digest='e' * 64))
        self.assertNotEqual(first.digest, second.digest)

    def test_optional_command_is_rejected(self) -> None:
        data = policy_data()
        data['commands'][0]['required'] = False
        with self.assertRaisesRegex(PolicyError, 'mandatory'):
            Policy.from_dict(data)

    def test_optional_holdout_command_is_rejected(self) -> None:
        data = policy_data()
        data['holdout']['commands'][0]['required'] = False
        with self.assertRaisesRegex(PolicyError, 'mandatory'):
            Policy.from_dict(data)

    def test_external_holdout_is_mandatory(self) -> None:
        data = policy_data()
        del data['holdout']
        with self.assertRaisesRegex(PolicyError, 'holdout'):
            Policy.from_dict(data)

    def test_holdout_path_must_be_absolute(self) -> None:
        data = policy_data(holdout_path='repo/holdout')
        with self.assertRaisesRegex(PolicyError, 'absolute'):
            Policy.from_dict(data)

    def test_mutable_image_tag_is_rejected(self) -> None:
        data = policy_data()
        data['sandbox']['image'] = 'runner:latest'
        with self.assertRaisesRegex(PolicyError, 'immutable'):
            Policy.from_dict(data)

    def test_host_execution_is_rejected(self) -> None:
        data = policy_data()
        data['sandbox']['runtime'] = 'host'
        with self.assertRaisesRegex(PolicyError, 'docker or podman'):
            Policy.from_dict(data)

    def test_command_name_must_be_unique(self) -> None:
        data = policy_data()
        data['commands'][1]['name'] = 'unit'
        with self.assertRaisesRegex(PolicyError, 'unique'):
            Policy.from_dict(data)

    def test_command_names_are_unique_across_repository_and_holdout(self) -> None:
        data = policy_data()
        data['holdout']['commands'][0]['name'] = 'unit'
        with self.assertRaisesRegex(PolicyError, 'globally unique'):
            Policy.from_dict(data)

    def test_required_scopes_are_derived_from_actual_paths(self) -> None:
        policy = Policy.from_dict(policy_data())
        self.assertEqual(
            policy.required_scopes(['trust-ci/src/a.py', 'trust-ci/sql/001_schema.sql']),
            {'governance', 'database'},
        )

    def test_directory_glob_matches_directory_itself(self) -> None:
        policy = Policy.from_dict(policy_data())
        self.assertEqual(policy.required_scopes(['trust-ci']), {'governance'})

    def test_unmatched_paths_need_no_approval(self) -> None:
        policy = Policy.from_dict(policy_data())
        self.assertEqual(policy.required_scopes(['docs/readme.md']), set())

    def test_repository_allowlist_is_exact(self) -> None:
        policy = Policy.from_dict(policy_data())
        self.assertTrue(policy.allows_repository('Dimkox/adaptive-grok-build-pro'))
        self.assertFalse(policy.allows_repository('dimkox/adaptive-grok-build-pro'))


if __name__ == '__main__':
    unittest.main()
