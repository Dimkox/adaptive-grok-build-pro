from __future__ import annotations

import copy
import unittest

from _support import policy_data
from adaptive_trust_ci.policy import Policy, PolicyCatalog, PolicyError


def catalog_data() -> dict:
    common = policy_data()
    common.pop('allowed_repositories')
    common.pop('commands')
    common.pop('holdout')
    return {
        **common,
        'repository_profiles': [
            {
                'repository': 'Dimkox/adaptive-grok-build-pro',
                'commands': policy_data()['commands'],
                'holdout': {**policy_data(holdout_digest='a' * 64)['holdout'], 'host_path': '/srv/holdouts/adaptive-grok-build-pro'},
            },
            {
                'repository': 'Dimkox/ii-tonya-platform',
                'commands': [
                    {
                        'name': 'platform-unit',
                        'argv': ['pytest', '-q'],
                        'timeout_seconds': 120,
                        'required': True,
                    },
                ],
                'holdout': {**policy_data(holdout_digest='b' * 64)['holdout'], 'host_path': '/srv/holdouts/ii-tonya-platform'},
            },
        ],
    }


class PolicyTests(unittest.TestCase):
    def test_legacy_policy_catalog_preserves_digest_and_check_name(self) -> None:
        legacy = Policy.from_dict(policy_data())
        catalog = PolicyCatalog.from_dict(policy_data())
        self.assertEqual(catalog.mode, 'legacy')
        self.assertEqual(catalog.digest, legacy.digest)
        self.assertEqual(catalog.resolve_repository('Dimkox/adaptive-grok-build-pro').check_name, legacy.check_name)
        self.assertEqual(catalog.profile_count, 1)

    def test_catalog_resolves_exact_isolated_profiles(self) -> None:
        catalog = PolicyCatalog.from_dict(catalog_data())
        a = catalog.resolve_repository('Dimkox/adaptive-grok-build-pro')
        b = catalog.resolve_repository('Dimkox/ii-tonya-platform')
        self.assertNotEqual(a.digest, b.digest)
        self.assertEqual(a.commands[0].name, 'unit')
        self.assertEqual(b.commands[0].name, 'platform-unit')
        with self.assertRaisesRegex(PolicyError, 'not configured'):
            catalog.resolve_repository('dimkox/ii-tonya-platform')

    def test_catalog_digest_is_order_independent_and_profile_changes_are_scoped(self) -> None:
        first = catalog_data()
        original = PolicyCatalog.from_dict(first)
        changed = copy.deepcopy(first)
        changed['repository_profiles'][0]['commands'][0]['name'] = 'unit-v2'
        updated = PolicyCatalog.from_dict(changed)
        self.assertNotEqual(original.resolve_repository('Dimkox/adaptive-grok-build-pro').digest,
                            updated.resolve_repository('Dimkox/adaptive-grok-build-pro').digest)
        self.assertEqual(original.resolve_repository('Dimkox/ii-tonya-platform').digest,
                         updated.resolve_repository('Dimkox/ii-tonya-platform').digest)
        reordered = copy.deepcopy(first)
        reordered['repository_profiles'].reverse()
        self.assertEqual(original.digest, PolicyCatalog.from_dict(reordered).digest)

    def test_catalog_common_change_rotates_all_profiles_and_bound_lookup_is_exact(self) -> None:
        first = PolicyCatalog.from_dict(catalog_data())
        changed = catalog_data()
        changed['max_attempts'] = 4
        second = PolicyCatalog.from_dict(changed)
        for repository in ('Dimkox/adaptive-grok-build-pro', 'Dimkox/ii-tonya-platform'):
            self.assertNotEqual(first.resolve_repository(repository).digest,
                                second.resolve_repository(repository).digest)
        profile = first.resolve_repository('Dimkox/ii-tonya-platform')
        self.assertIs(first.resolve_bound('Dimkox/ii-tonya-platform', profile.digest), profile)
        with self.assertRaisesRegex(PolicyError, 'not active'):
            first.resolve_bound('Dimkox/ii-tonya-platform', first.resolve_repository('Dimkox/adaptive-grok-build-pro').digest)

    def test_catalog_rejects_mixed_legacy_fields(self) -> None:
        data = catalog_data()
        data['commands'] = []
        with self.assertRaisesRegex(PolicyError, 'mixed'):
            PolicyCatalog.from_dict(data)

    def test_catalog_requires_absolute_host_path(self) -> None:
        for value in ('missing', None, '', 'relative/holdout'):
            data = catalog_data()
            if value == 'missing':
                del data['repository_profiles'][0]['holdout']['host_path']
            else:
                data['repository_profiles'][0]['holdout']['host_path'] = value
            with self.assertRaisesRegex(PolicyError, 'host_path'):
                PolicyCatalog.from_dict(data)

    def test_catalog_rejects_invalid_or_trimmed_repository_names(self) -> None:
        for repository in ('bad', ' Dimkox/example', 'Dimkox/example '):
            data = catalog_data()
            data['repository_profiles'][0]['repository'] = repository
            with self.assertRaisesRegex(PolicyError, 'repository profile'):
                PolicyCatalog.from_dict(data)

    def test_catalog_rejects_unknown_profile_keys(self) -> None:
        data = catalog_data()
        data['repository_profiles'][0]['unexpected'] = True
        with self.assertRaisesRegex(PolicyError, 'repository profile keys'):
            PolicyCatalog.from_dict(data)

    def test_catalog_digest_binds_canonical_profile_holdout_paths(self) -> None:
        first = catalog_data()
        second = copy.deepcopy(first)
        second['repository_profiles'][0]['holdout']['path'] = '/opt/adaptive-trust-ci/./holdout'
        second['repository_profiles'][0]['holdout']['host_path'] = '/srv/holdouts/./adaptive-grok-build-pro'
        self.assertEqual(
            PolicyCatalog.from_dict(first).resolve_repository('Dimkox/adaptive-grok-build-pro').digest,
            PolicyCatalog.from_dict(second).resolve_repository('Dimkox/adaptive-grok-build-pro').digest,
        )

    def test_catalog_rejects_duplicate_and_wildcard_repositories(self) -> None:
        for repository in ('Dimkox/adaptive-grok-build-pro', 'Dimkox/*'):
            data = catalog_data()
            data['repository_profiles'][1]['repository'] = repository
            with self.assertRaisesRegex(PolicyError, 'repository'):
                PolicyCatalog.from_dict(data)

    def test_catalog_requires_common_fields(self) -> None:
        for field in ('schema_version', 'status_context', 'pipeline', 'sandbox'):
            data = catalog_data()
            data.pop(field, None)
            with self.assertRaises(PolicyError):
                PolicyCatalog.from_dict(data)

    def test_legacy_digest_and_check_name_remain_exact_without_host_path(self) -> None:
        legacy = Policy.from_dict(policy_data())
        catalog = PolicyCatalog.from_dict(policy_data())
        self.assertEqual(catalog.digest, legacy.digest)
        self.assertEqual(catalog.resolve_repository(legacy.allowed_repositories[0]).check_name, legacy.check_name)
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
