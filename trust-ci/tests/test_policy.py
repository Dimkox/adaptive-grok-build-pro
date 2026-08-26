from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from _support import policy_data
from adaptive_trust_ci.policy import Policy, PolicyError


class PolicyTests(unittest.TestCase):
    def test_digest_is_stable_for_equivalent_objects(self) -> None:
        first = policy_data()
        second = copy.deepcopy(first)
        second['allowed_repositories'] = list(reversed(second['allowed_repositories']))
        self.assertEqual(Policy.from_dict(first).digest, Policy.from_dict(second).digest)

    def test_policy_change_changes_digest_and_required_check_name(self) -> None:
        first = Policy.from_dict(policy_data())
        changed = policy_data()
        changed['max_attempts'] = 4
        second = Policy.from_dict(changed)
        self.assertNotEqual(first.digest, second.digest)
        self.assertNotEqual(first.check_name, second.check_name)

    def test_required_check_name_is_bound_to_policy_epoch(self) -> None:
        policy = Policy.from_dict(policy_data())
        self.assertEqual(
            policy.check_name,
            f'adaptive-trust-ci/verified@{policy.digest[:12]}',
        )

    def test_status_context_must_be_an_unversioned_prefix(self) -> None:
        data = policy_data()
        data['status_context'] = 'adaptive-trust-ci/verified@manual'
        with self.assertRaisesRegex(PolicyError, 'epoch'):
            Policy.from_dict(data)

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

    def test_required_scopes_preserve_exact_unusual_git_paths(self) -> None:
        policy = Policy.from_dict(policy_data())
        for path in ('trust-ci/файл.txt', 'trust-ci/line\nbreak.txt', 'trust-ci/tab\tname.txt', 'trust-ci/back\\slash.txt'):
            with self.subTest(path=path):
                self.assertEqual(policy.required_scopes((path,)), {'governance'})
        self.assertEqual(policy.required_scopes(('trust-ci/данные.sql',)), {'governance', 'database'})

    def test_approval_globs_preserve_exact_repo_relative_identity(self) -> None:
        policy = Policy.from_dict(policy_data())
        governance = next(rule for rule in policy.approval_rules if rule.scope == 'governance')
        self.assertIn('.grok-stack/**', governance.globs)
        self.assertIn('.grok/**', governance.globs)
        self.assertIn('.github/**', governance.globs)
        self.assertIn('.coveragerc', governance.globs)
        self.assertIn('literal\\target.txt', governance.globs)
        self.assertIn('exact/юникод.txt', governance.globs)
        self.assertIn('exact/line\nname.txt', governance.globs)
        self.assertIn('exact/tab\tname.txt', governance.globs)
        for path in (
            '.grok-stack/runtime/active-route.json',
            '.grok/prompt\nname.md',
            '.github/tab\tname.yml',
            '.coveragerc',
            'literal\\target.txt',
            'exact/юникод.txt',
            'exact/line\nname.txt',
            'exact/tab\tname.txt',
        ):
            with self.subTest(path=path):
                self.assertEqual(policy.required_scopes((path,)), {'governance'})

    def test_approval_globs_reject_unsafe_patterns_without_rewriting(self) -> None:
        for pattern in (
            '/absolute/**',
            '../outside/**',
            'safe/../outside',
            './safe/**',
            'safe//name',
            'nul\0name',
            'carriage\rreturn',
            'surrogate\ud800name',
            7,
        ):
            with self.subTest(pattern=repr(pattern)):
                data = policy_data()
                data['approval_rules'] = [{'scope': 'governance', 'globs': [pattern]}]
                with self.assertRaises(PolicyError):
                    Policy.from_dict(data)

    def test_policy_file_with_invalid_utf8_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'policy.json'
            path.write_bytes(b'{"approval_rules":["bad-\xff"]}')
            with self.assertRaisesRegex(PolicyError, 'cannot load policy'):
                Policy.load(path)

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
