from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok import verification as verification_module
from adaptive_grok.verification import CheckResult, _python, _docs_state_scope_check, verify
from adaptive_grok.verification_scope import (
    DOCS_STATE_PROFILE,
    FORCE_FULL_VARIABLE,
    FOCUSED_SKIPPED_CHECKS,
    FOCUSED_TEST_TARGETS,
    FULL_PROFILE,
    focused_command,
    select_docs_state_scope,
)
from tests._support import project_copy

# The inventory of the v2.0.19 release sync and its artifact child, reduced to the path
# classes they actually contain. This is the case issue 205 is about.
RELEASE_SYNC_INVENTORY = [
    'AGENTS.md',
    'CHANGELOG.md',
    'DARK_FACTORY_ROADMAP.md',
    'GROK_BUILD_HANDOFF.md',
    'PROJECT_STATE.json',
    'README.md',
    'START_HERE.md',
    'VERSION',
    'decisions.md',
    'engineering/changes/20260924-example/change-spec.yaml',
    'engineering/changes/20260924-example/state.json',
    'engineering/reviews/l5-delivery-stack.json',
    'engineering/runbooks/l5-production-runtime.md',
    'mistakes.md',
    'packages/adaptive-grok-build-pro-v2.0.19.zip',
    'packages/adaptive-grok-build-pro-v2.0.19.zip.sha256',
    'packages/README.md',
    *FOCUSED_TEST_TARGETS,
]

# Every one of these can move an executed product statement, change a machine contract,
# or silence a check, so none of them may ride the focused lane.
FULL_PATH_ONLY_CHANGES = [
    '.grok-stack/adaptive_grok/verification.py',
    '.grok-stack/adaptive_grok/verification_scope.py',
    'scripts/grok_verify.py',
    'trust-ci/src/trust_ci/api.py',
    'trust-ci/config/policy.example.json',
    'factory/src/adaptive_factory/service.py',
    'factory/tests/test_service.py',
    'pilot/l5_runtime/host.py',
    'pre_tool_use.py',
    'stop_gate.py',
    'Makefile',
    'ruff.toml',
    'bandit.yaml',
    '.coveragerc',
    '.gitignore',
    'architecture/system.yaml',
    'architecture/rules.yaml',
    'architecture/generated/views.md',
    'schemas/change-spec.schema.json',
    'engineering/contracts/openapi/execution-v2.yaml',
    'governance/rules/index.json',
    'examples/contracts/example.json',
    'side-projects/seo-landings/winston-wolfe/index.html',
    '.github/CODEOWNERS',
    '.qwen/settings.json',
    'delivery/ledger.json',
    'tests/test_verification_doctor.py',
    'tests/test_python_test_runner.py',
    'tests/support/fixtures.json',
    'README/oversight.md',
    'VERSION.bak',
    'PROJECT_STATE.json.tmp',
]

_TRIVIAL_TEST = (
    'import unittest\n'
    '\n'
    'class OkTests(unittest.TestCase):\n'
    '    def test_ok(self) -> None:\n'
    '        self.assertTrue(True)\n'
)


def _statuses(paths: list[str], status: str = 'M') -> list[dict[str, str]]:
    return [{'status': status, 'path': path} for path in paths]


class DocsStateScopeSelectionTests(unittest.TestCase):
    def _scope(self, files: list[object], **kwargs):
        kwargs.setdefault('range_base_count', 1)
        kwargs.setdefault('file_statuses', _statuses([str(item) for item in files if isinstance(item, str)]))
        kwargs.setdefault('status_inventory_trusted', True)
        kwargs.setdefault('available_test_targets', list(FOCUSED_TEST_TARGETS))
        return select_docs_state_scope('pr', files, **kwargs)

    def test_release_sync_inventory_selects_the_focused_profile(self) -> None:
        scope = self._scope(RELEASE_SYNC_INVENTORY)

        self.assertTrue(scope['eligible'])
        self.assertEqual(scope['profile'], DOCS_STATE_PROFILE)
        self.assertEqual(scope['evidence_kind'], f'verification:{DOCS_STATE_PROFILE}')
        self.assertEqual(scope['checked_files'], sorted(RELEASE_SYNC_INVENTORY))
        self.assertEqual(scope['focused_tests'], list(FOCUSED_TEST_TARGETS))
        self.assertEqual(scope['skipped_checks'], list(FOCUSED_SKIPPED_CHECKS))
        self.assertEqual(scope['rejected_files'], [])
        self.assertRegex(str(scope['changed_paths_digest']), r'^[0-9a-f]{64}$')

    def test_prose_only_inventory_still_runs_the_lockstep_trio(self) -> None:
        # The trio re-derives identity and dated state from the current tree, so it is not
        # conditional on this change having edited it.
        scope = self._scope(['README.md'])

        self.assertTrue(scope['eligible'])
        self.assertEqual(scope['focused_tests'], list(FOCUSED_TEST_TARGETS))
        self.assertEqual(scope['changed_lockstep_tests'], [])

    def test_every_executable_or_contract_bearing_path_keeps_the_full_profile(self) -> None:
        for path in FULL_PATH_ONLY_CHANGES:
            with self.subTest(path=path):
                scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS, path])

                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['profile'], FULL_PROFILE)
                self.assertEqual(scope['evidence_kind'], 'verification:full-pr-suite')
                self.assertIn(path, scope['rejected_files'])

    def test_the_shortcut_selectors_own_module_cannot_be_edited_in_focused_scope(self) -> None:
        # Changing the classifier must never be verifiable by the classifier it just changed.
        for path in (
            '.grok-stack/adaptive_grok/verification_scope.py',
            '.grok-stack/adaptive_grok/verification.py',
            'scripts/grok_verify.py',
        ):
            with self.subTest(path=path):
                self.assertFalse(self._scope([path])['eligible'])

    def test_unsafe_paths_are_rejected_as_invalid_inventory_entries(self) -> None:
        for path in (
            '/etc/passwd',
            '../escape/README.md',
            './README.md',
            'nested\x00name',
            'back\\slash.md',
            'packages/../etc/passwd',
        ):
            with self.subTest(path=path):
                scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS, path])

                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], 'invalid-inventory-path')

    def test_non_string_inventory_entries_are_rejected_not_crashed(self) -> None:
        for value in (None, 7, {'path': 'README.md'}, b'README.md'):
            with self.subTest(value=repr(value)):
                scope = self._scope([value])

                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], 'invalid-inventory-path')

    def test_deleted_renamed_copied_and_unmerged_statuses_keep_the_full_profile(self) -> None:
        for status in ('D', 'R', 'C', 'U'):
            with self.subTest(status=status):
                statuses = _statuses(['README.md', *FOCUSED_TEST_TARGETS])
                statuses.append({'status': status, 'path': 'README.md', 'original_path': 'README-old.md'})
                scope = self._scope(
                    ['README.md', *FOCUSED_TEST_TARGETS],
                    file_statuses=statuses,
                )

                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], 'unsafe-file-status')

    def test_a_safe_status_with_an_original_path_is_treated_as_malformed(self) -> None:
        statuses = _statuses(['README.md', *FOCUSED_TEST_TARGETS])
        statuses.append({'status': 'M', 'path': 'README.md', 'original_path': 'README.md'})
        scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS], file_statuses=statuses)

        self.assertFalse(scope['eligible'])
        self.assertEqual(scope['reason_code'], 'unsafe-file-status')

    def test_missing_or_untrusted_status_inventory_fails_closed(self) -> None:
        inventory = ['README.md', *FOCUSED_TEST_TARGETS]

        without_statuses = self._scope(inventory, file_statuses=None)
        untrusted = self._scope(inventory, status_inventory_trusted=False)
        not_a_list = self._scope(inventory, file_statuses='README.md')

        self.assertEqual(without_statuses['reason_code'], 'unsafe-file-status')
        self.assertEqual(untrusted['reason_code'], 'file-status-inventory-unavailable')
        self.assertEqual(not_a_list['reason_code'], 'unsafe-file-status')

    def test_empty_ambiguous_or_unbased_inventories_keep_the_full_profile(self) -> None:
        cases = {
            'unresolved-diff': self._scope([]),
            'comparison-inventory-incomplete': self._scope(
                ['README.md', *FOCUSED_TEST_TARGETS],
                range_findings=[{'severity': 'error', 'code': 'pr-base-unavailable', 'path': 'git', 'message': 'x'}],
            ),
            'comparison-inventory-untrusted': self._scope(
                ['README.md', *FOCUSED_TEST_TARGETS], range_base_count=0
            ),
            'route-unavailable': self._scope(
                ['README.md', *FOCUSED_TEST_TARGETS], route_present=False
            ),
        }

        for expected, scope in cases.items():
            with self.subTest(expected=expected):
                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], expected)

    def test_fast_and_landing_modes_are_not_gated_scopes(self) -> None:
        for mode in ('fast', 'focused-static-seo-landing'):
            with self.subTest(mode=mode):
                scope = select_docs_state_scope(mode, RELEASE_SYNC_INVENTORY)

                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], 'mode-not-gated')

    def test_release_mode_is_gated_and_admissible(self) -> None:
        scope = select_docs_state_scope(
            'release',
            RELEASE_SYNC_INVENTORY,
            range_base_count=1,
            file_statuses=_statuses(RELEASE_SYNC_INVENTORY),
            status_inventory_trusted=True,
            available_test_targets=list(FOCUSED_TEST_TARGETS),
        )

        self.assertTrue(scope['eligible'])

    def test_operator_override_defeats_the_shortcut(self) -> None:
        scope = select_docs_state_scope(
            'pr',
            RELEASE_SYNC_INVENTORY,
            range_base_count=1,
            file_statuses=_statuses(RELEASE_SYNC_INVENTORY),
            status_inventory_trusted=True,
            environment={FORCE_FULL_VARIABLE: '1'},
        )

        self.assertFalse(scope['eligible'])
        self.assertEqual(scope['reason_code'], 'operator-override')

    def test_an_absent_lockstep_target_cannot_be_run_by_the_focused_profile(self) -> None:
        scope = self._scope(
            RELEASE_SYNC_INVENTORY,
            available_test_targets=['tests/test_structure.py', 'tests/test_project_state.py'],
        )

        self.assertFalse(scope['eligible'])
        self.assertEqual(scope['reason_code'], 'lockstep-target-unavailable')
        self.assertIn('tests/test_manifest_package.py', scope['rejected_files'])

    def test_focused_command_names_modules_not_discovery(self) -> None:
        command = focused_command(list(FOCUSED_TEST_TARGETS))

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1:3], ['-m', 'unittest'])
        self.assertNotIn('discover', command)
        self.assertEqual(
            command[3:],
            ['tests.test_structure', 'tests.test_project_state', 'tests.test_manifest_package'],
        )


class DocsStateScopeCheckRenderingTests(unittest.TestCase):
    def test_eligible_check_names_every_admitted_path_and_each_skip(self) -> None:
        scope = select_docs_state_scope(
            'pr',
            ['README.md', 'PROJECT_STATE.json', *FOCUSED_TEST_TARGETS],
            range_base_count=1,
            file_statuses=_statuses(['README.md', 'PROJECT_STATE.json', *FOCUSED_TEST_TARGETS]),
            status_inventory_trusted=True,
            available_test_targets=list(FOCUSED_TEST_TARGETS),
        )
        result = _docs_state_scope_check(scope)

        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.name, 'docs-state-scope')
        self.assertEqual(result.status, 'pass')
        self.assertIn(DOCS_STATE_PROFILE, result.summary)
        self.assertIn('verification:docs-state-focused', result.summary)
        reported = {item['path'] for item in result.details}
        self.assertIn('README.md', reported)
        self.assertIn('PROJECT_STATE.json', reported)
        for skipped in FOCUSED_SKIPPED_CHECKS:
            self.assertIn(skipped, reported)
            self.assertIn('is not measured', ' '.join(
                item['message'] for item in result.details if item['path'] == skipped
            ))

    def test_ineligible_check_reports_the_blocking_path_and_is_not_a_failure(self) -> None:
        scope = select_docs_state_scope(
            'pr',
            ['README.md', 'factory/src/adaptive_factory/service.py'],
            range_base_count=1,
            file_statuses=_statuses(['README.md', 'factory/src/adaptive_factory/service.py']),
            status_inventory_trusted=True,
        )
        result = _docs_state_scope_check(scope)

        self.assertEqual(result.status, 'pass')
        self.assertIn(FULL_PROFILE, result.summary)
        self.assertIn('factory/src/adaptive_factory/service.py', {item['path'] for item in result.details})
        self.assertIn('skipped=none', result.summary)


class FocusedPythonExecutionTests(unittest.TestCase):
    """Mutation probe: the same tree, and only the scope input decides what executes."""

    def _tree(self, root: Path) -> None:
        (root / 'tests').mkdir(parents=True, exist_ok=True)
        (root / '.coveragerc').write_text(
            '[run]\nbranch = False\nsource =\n    tests\n\n[report]\nshow_missing = False\n',
            encoding='utf-8',
        )
        for name in ('test_structure', 'test_project_state', 'test_manifest_package'):
            (root / 'tests' / f'{name}.py').write_text(_TRIVIAL_TEST, encoding='utf-8')
        # A suite member that records that full discovery actually reached it.
        (root / 'tests' / 'test_full_suite_only.py').write_text(
            'import unittest\n'
            '\n'
            'class FullSuiteMarker(unittest.TestCase):\n'
            '    def test_marker(self) -> None:\n'
            '        from pathlib import Path\n'
            f'        Path({str(root)!r}).joinpath("full-suite-executed.marker").write_text("ran")\n',
            encoding='utf-8',
        )
        (root / 'README.md').write_text('# probe\n', encoding='utf-8')

    def _scope(self, changed: list[str], root: Path) -> dict[str, object]:
        return select_docs_state_scope(
            'pr',
            changed,
            range_base_count=1,
            file_statuses=_statuses(changed),
            status_inventory_trusted=True,
            available_test_targets=[
                target for target in FOCUSED_TEST_TARGETS if (root / target).is_file()
            ],
        )

    def _run(self, root: Path, scope: dict[str, object]) -> dict[str, CheckResult]:
        return {item.name: item for item in _python(root, 'pr', scope)}

    def test_admitted_inventory_never_executes_full_suite_discovery(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-probe-') as tmp:
            root = Path(tmp)
            self._tree(root)
            scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS], root)
            self.assertTrue(scope['eligible'])

            checks = self._run(root, scope)

            self.assertIn('python-focused-unittest', checks)
            self.assertEqual(checks['python-focused-unittest'].status, 'pass')
            self.assertEqual(checks['python-unittest'].status, 'skip')
            self.assertEqual(checks['coverage'].status, 'skip')
            self.assertEqual(checks['factory-postgres-exit'].status, 'skip')
            self.assertNotIn('discover', json.dumps(checks['python-focused-unittest'].command))
            self.assertFalse(
                (root / 'full-suite-executed.marker').exists(),
                'the focused profile executed a suite member outside the lockstep trio',
            )

    def test_mutating_one_source_path_flips_the_same_tree_to_full_discovery(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-probe-') as tmp:
            root = Path(tmp)
            self._tree(root)
            (root / '.grok-stack').mkdir(parents=True, exist_ok=True)
            (root / '.grok-stack' / 'adaptive_grok').mkdir(parents=True, exist_ok=True)
            (root / '.grok-stack' / 'adaptive_grok' / 'service.py').write_text('VALUE = 1\n', encoding='utf-8')
            source_path = '.grok-stack/adaptive_grok/service.py'

            focused = self._scope(['README.md', *FOCUSED_TEST_TARGETS], root)
            mutated = self._scope(['README.md', source_path, *FOCUSED_TEST_TARGETS], root)

            self.assertTrue(focused['eligible'])
            self.assertFalse(mutated['eligible'])
            self.assertEqual(mutated['reason_code'], 'unallowlisted-path')

            checks = self._run(root, mutated)

            self.assertNotIn('python-focused-unittest', checks)
            self.assertIn('python-unittest', checks)
            self.assertTrue(
                (root / 'full-suite-executed.marker').exists(),
                'a source change must put the full suite back on the critical path',
            )
            coverage = checks.get('coverage')
            self.assertIsNotNone(coverage)
            self.assertNotEqual(getattr(coverage, 'status', None), 'skip')

    def test_operator_override_on_an_identical_inventory_restores_the_suite(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-probe-') as tmp:
            root = Path(tmp)
            self._tree(root)
            inventory = ['README.md', *FOCUSED_TEST_TARGETS]
            forced = select_docs_state_scope(
                'pr',
                inventory,
                range_base_count=1,
                file_statuses=_statuses(inventory),
                status_inventory_trusted=True,
                available_test_targets=list(FOCUSED_TEST_TARGETS),
                environment={FORCE_FULL_VARIABLE: 'true'},
            )

            checks = self._run(root, forced)

            self.assertFalse(forced['eligible'])
            self.assertNotIn('python-focused-unittest', checks)
            self.assertTrue((root / 'full-suite-executed.marker').exists())


class VerifyReportScopeFieldTests(unittest.TestCase):
    def test_report_always_carries_the_scope_decision_and_its_evidence_kind(self) -> None:
        with project_copy(git=True) as root:
            from adaptive_grok.router import build_route
            from adaptive_grok.state import set_active_route

            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)

            report = verify(root, mode='fast', record=False)

            scope = report['docs_state_scope']
            self.assertEqual(scope['profile'], FULL_PROFILE)
            self.assertEqual(scope['evidence_kind'], 'verification:full-pr-suite')
            self.assertEqual(scope['reason_code'], 'mode-not-gated')
            self.assertIn('docs-state-scope', [item['name'] for item in report['checks']])


if __name__ == '__main__':
    unittest.main()
