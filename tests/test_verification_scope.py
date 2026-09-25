from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok import verification as verification_module
from adaptive_grok import util as util_module
from adaptive_grok.verification import CheckResult, _python, _docs_state_scope_check, verify
from adaptive_grok.verification_scope import (
    DOCS_STATE_PROFILE,
    DOCUMENT_FILES,
    DOCUMENT_PREFIXES,
    DOCUMENT_ROOT_FILES,
    FORCE_FULL_VARIABLE,
    FOCUSED_SKIPPED_CHECKS,
    FOCUSED_TEST_TARGETS,
    FULL_PROFILE,
    SAFE_FILE_STATUSES,
    SHIPPED_EXECUTED_FILES,
    _classify_path,
    focused_command,
    is_immutable_historical_evidence,
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
    # Documentation directories are not documentation roles. These live under an admitted
    # prefix but are shipped-and-executed product or declared-immutable evidence.
    'docs/bitrix-local-AGENTS.md',
    'engineering/changes/20260913-l5-split-g-current-base-offline-recovery-and-com-352913/evidence/historical-qwen-probe.json',
    'engineering/changes/20260913-l5-split-g-final-base-offline-recovery-and-assem-2a890b/evidence/historical-qwen-probe.json',
    'engineering/changes/20260921-fix-the-combined-source-delivery-of-issue165-int-8b2ee0/evidence/historical-shared-handoffs.json',
    'engineering/changes/20260924-example/evidence/historical-future-bundle.json',
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


def _full_suite_marker_source(root: Path) -> str:
    """A suite member that records that full discovery actually reached it."""
    return (
        'import unittest\n'
        '\n'
        'class FullSuiteMarker(unittest.TestCase):\n'
        '    def test_marker(self) -> None:\n'
        '        from pathlib import Path\n'
        f'        Path({str(root)!r}).joinpath("full-suite-executed.marker").write_text("ran")\n'
    )


def _init_repo(root: Path):
    """Create a throwaway git repository and return its `git` runner."""
    def git(*args: str) -> None:
        subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)

    git('init', '-q', '-b', 'main')
    git('config', 'user.name', 'Test')
    git('config', 'user.email', 'test@example.invalid')
    git('config', 'commit.gpgSign', 'false')
    # Runtime state and probe side effects must not be swept in by `git add .`, or the
    # synthetic inventory carries paths the real repository keeps untracked.
    (root / '.gitignore').write_text(
        '.grok-stack/runtime/\n__pycache__/\n.coverage\nfull-suite-executed.marker\n',
        encoding='utf-8',
    )
    return git


def _git_head(root: Path) -> str:
    return subprocess.run(
        ['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


class RealRepositoryInventoryTests(unittest.TestCase):
    """The lane must fire on the shape real PRs have, and still fail on the shape attacks have.

    A committed change package is byte-similar to an older one, so git's copy detection
    reports it as `C0xx` with an original_path. Reading the docs/state status side channel
    with copy detection on would push every evidence-carrying pull request to the full suite,
    leaving the focused profile as dead code that only unit tests ever passed.
    """

    def _repo(self, root: Path):
        def git(*args: str) -> None:
            subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)

        git('init', '-q', '-b', 'main')
        git('config', 'user.name', 'Test')
        git('config', 'user.email', 'test@example.invalid')
        package = root / 'engineering/changes/20260101-old-package'
        package.mkdir(parents=True)
        for name, text in (
            ('requirements.md',
             '# Requirements\n\n## Acceptance criteria\n\n- [x] Given a, when b, then c.\n\n'
             '## Failure and edge cases\n\n- none\n\n## Governance context\n\n'
             'Canonical governance JSON under `governance/`.\n'),
            ('tasks.md',
             '# Tasks\n\n1. Do the bounded work.\n2. Verify it.\n3. Record the evidence.\n'
             '4. Deliver the branch.\n5. Close the package.\n6. Review the result.\n'
             '7. Write the summary.\n8. Archive the state.\n'),
            ('release.md',
             '# Release\n\nRelease readiness for the bounded change.\n\n## Roll forward\n\n'
             'Deliver the branch and re-check.\n\n## Roll back\n\nRevert the single commit.\n'),
        ):
            (package / name).write_text(text, encoding='utf-8')
        (root / 'README.md').write_text('# Project\n\nidentity 1.0.0\n', encoding='utf-8')
        (root / 'PROJECT_STATE.json').write_text('{"version": "1.0.0"}\n', encoding='utf-8')
        git('add', '.')
        git('commit', '-qm', 'baseline')
        return git

    def _scope_after(self, root: Path, base_sha: str) -> dict[str, object]:
        from adaptive_grok.verification import GitRangeBase, _docs_state_status_inventory

        head = _git_head(root)
        selection = verification_module.GitRangeSelection(bases=[GitRangeBase(
            kind='route', source='route.base_commit', target_sha=head, comparison_base_sha=base_sha,
        )])
        records, trusted = _docs_state_status_inventory(root, selection)
        return select_docs_state_scope(
            'pr',
            sorted({str(item['path']) for item in records}),
            range_base_count=1,
            file_statuses=records,
            status_inventory_trusted=trusted,
            available_test_targets=list(FOCUSED_TEST_TARGETS),
        )

    def test_a_scaffolded_package_copy_still_selects_the_focused_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-repo-') as tmp:
            root = Path(tmp)
            git = self._repo(root)
            base = _git_head(root)
            new_package = root / 'engineering/changes/20260924-new-package'
            new_package.mkdir()
            old_package = root / 'engineering/changes/20260101-old-package'
            for name in ('requirements.md', 'tasks.md', 'release.md'):
                shutil.copyfile(old_package / name, new_package / name)
            (root / 'README.md').write_text('# Project\n\nidentity 1.0.1\n', encoding='utf-8')
            (root / 'PROJECT_STATE.json').write_text('{"version": "1.0.1"}\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'docs successor')

            # Prove git really did classify the scaffold as a copy, or this test would pass
            # without ever exercising the thing it exists for.
            detected = subprocess.run(
                ['git', 'diff', '--name-status', '--find-copies-harder', f'{base}..HEAD'],
                cwd=root, capture_output=True, text=True, check=True,
            ).stdout
            self.assertRegex(detected, r'C\d{2,3}\t', 'git reported no copy: the test is vacuous')

            scope = self._scope_after(root, base)

            self.assertTrue(scope['eligible'], scope)
            self.assertEqual(scope['profile'], DOCS_STATE_PROFILE)

    def test_a_source_path_removed_behind_a_docs_name_never_selects_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-repo-') as tmp:
            root = Path(tmp)
            git = self._repo(root)
            source = root / '.grok-stack/adaptive_grok/service.py'
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('VALUE = 1\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'add source')
            base = _git_head(root)
            source.unlink()
            (root / 'docs').mkdir()
            (root / 'docs/service.py.md').write_text('moved to prose\n', encoding='utf-8')
            git('add', '-A')
            git('commit', '-qm', 'docs-shaped replacement')

            scope = self._scope_after(root, base)

            self.assertFalse(scope['eligible'])
            self.assertEqual(scope['reason_code'], 'unsafe-file-status')


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

    def test_prose_only_inventory_still_runs_every_admitted_module(self) -> None:
        # The admitted modules re-derive identity and dated state from the current tree, so they
        # are not conditional on this change having edited them.
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
        unknown_trust = self._scope(inventory, status_inventory_trusted=None)
        not_a_list = self._scope(inventory, file_statuses='README.md')

        self.assertEqual(without_statuses['reason_code'], 'unsafe-file-status')
        self.assertEqual(untrusted['reason_code'], 'file-status-inventory-unavailable')
        # An absent trust signal is not a confirmation: the veto needs a positive True.
        self.assertEqual(unknown_trust['reason_code'], 'file-status-inventory-unavailable')
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
            [
                'tests.test_structure',
                'tests.test_project_state',
                'tests.test_manifest_package',
                'tests.test_workflow_sources',
                'tests.test_repo_router',
            ],
        )

    def test_every_admitted_content_class_is_re_derived_by_a_module_this_lane_runs(self) -> None:
        # Finding 1 of the review of head a08060c1: README's Workflow-sources table and a
        # delivered change package's route record are admitted content whose only machine
        # binding lived outside this lane. They are in it now, so no admitted path is left
        # bound to a check the focused profile does not run.
        self.assertIn('tests/test_workflow_sources.py', FOCUSED_TEST_TARGETS)
        self.assertIn('tests/test_repo_router.py', FOCUSED_TEST_TARGETS)
        self.assertIn('README.md', DOCUMENT_ROOT_FILES)
        self.assertIsNone(
            _classify_path(
                'engineering/changes/20260920-fix-issue-155-guards-inside-the-semantic-bind-re-c4e47e/route.json'
            )
        )
        # The two binding modules really do read that admitted content, or adding them here is
        # theatre: assert on their sources, not on this file's belief about them.
        self.assertIn('README.md', (ROOT / 'tests' / 'test_workflow_sources.py').read_text(encoding='utf-8'))
        self.assertIn(
            'engineering/changes/',
            (ROOT / 'tests' / 'test_repo_router.py').read_text(encoding='utf-8'),
        )


class RoleBasedAdmissionTests(unittest.TestCase):
    """A path is admitted for the role its bytes play, never for the directory it sits in."""

    def _scope(self, files: list[str]) -> dict[str, object]:
        return select_docs_state_scope(
            'pr',
            files,
            range_base_count=1,
            file_statuses=_statuses(files),
            status_inventory_trusted=True,
            available_test_targets=list(FOCUSED_TEST_TARGETS),
        )

    def test_named_prose_files_are_admitted(self) -> None:
        for path in (
            'docs/INVESTOR_DEMO.md',
            'docs/package-status.md',
            'engineering/decisions.md',
            'engineering/mistakes.md',
            'docs/superpowers/plans/2026-08-23-trust-ci-control-plane.md',
            'docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md',
            'engineering/changes/20260924-example/brief.md',
        ):
            with self.subTest(path=path):
                self.assertIsNone(_classify_path(path))
                self.assertTrue(self._scope(['README.md', *FOCUSED_TEST_TARGETS, path])['eligible'])

    def test_shipped_and_executed_content_is_rejected_by_its_own_reason_code(self) -> None:
        # docs/bitrix-local-AGENTS.md is installed verbatim as local/AGENTS.md into every
        # consumer Bitrix install (scripts/install_into.py), so it is agent-executed product.
        self.assertEqual(SHIPPED_EXECUTED_FILES, frozenset({'docs/bitrix-local-AGENTS.md'}))
        for path in sorted(SHIPPED_EXECUTED_FILES):
            with self.subTest(path=path):
                self.assertEqual(_classify_path(path), 'shipped-executed-content')
                scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS, path])
                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], 'shipped-executed-content')
                self.assertIn(path, scope['rejected_files'])

    def test_declared_immutable_historical_evidence_is_rejected_by_its_own_reason_code(self) -> None:
        cases = (
            'engineering/changes/20260913-l5-split-g-current-base-offline-recovery-and-com-352913/evidence/historical-qwen-probe.json',
            'engineering/changes/pkg/evidence/historical-shared-handoffs.json',
            'delivery/pkg/evidence/historical-future-bundle.json',
        )
        for path in cases:
            with self.subTest(path=path):
                self.assertTrue(is_immutable_historical_evidence(path))
                self.assertEqual(_classify_path(path), 'immutable-historical-evidence')
                scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS, path])
                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], 'immutable-historical-evidence')

    def test_a_sibling_of_an_admitted_evidence_name_stays_admitted_by_prefix(self) -> None:
        # Only the immutable bundle is rejected; the rest of a package keeps riding the lane.
        for path in (
            'engineering/changes/pkg/evidence/README.md',
            'engineering/changes/pkg/evidence/history-summary.json',
            'engineering/changes/pkg/route.json',
        ):
            with self.subTest(path=path):
                self.assertFalse(is_immutable_historical_evidence(path))
                self.assertIsNone(_classify_path(path))

    def test_an_undeclared_name_under_an_admitted_directory_is_not_admitted(self) -> None:
        # This is the pin that keeps admission role-based: with a `docs/` prefix restored the
        # shipped Bitrix file would still be refused by its own rule, and only a new prose file
        # would silently ride the lane. Nothing is admitted by directory membership alone.
        cases = (
            ('docs/onboarding-guide.md', 'unallowlisted-path'),
            ('docs/superpowers/notes/2026-09-24-something.md', 'unallowlisted-path'),
            ('docs/package-status.md.bak', 'unallowlisted-path'),
            ('engineering/decisions.md', None),  # admitted as a name, not by a directory
            ('engineering/decisions.md.bak', 'unallowlisted-path'),
            ('engineering/reviews/x/bundle.json', None),  # review artifacts are a prose role
            ('packages/adaptive-grok-build-pro-v2.0.19.zip', None),  # tracked release bytes
        )
        for path, expected in cases:
            with self.subTest(path=path):
                self.assertEqual(_classify_path(path), expected)
                scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS, path])
                self.assertEqual(scope['eligible'], expected is None)

    def test_a_name_outside_every_declared_role_is_not_admitted(self) -> None:
        # Admission is by declared role, never by directory membership: with a wholesale `docs/`
        # prefix restored, the shipped Bitrix file would still be refused by its own earlier rule,
        # so these undeclared names are what notices the widening.
        for path in (
            'docs/bitrix-module-notes.md',
            'engineering/specifications/2026-09-24-design.md',
            'engineering/contracts/execution-v2.yaml',
        ):
            with self.subTest(path=path):
                self.assertEqual(_classify_path(path), 'unallowlisted-path')
                scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS, path])
                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], 'unallowlisted-path')

    def test_documentation_prefixes_are_directory_shaped_only(self) -> None:
        self.assertNotIn('docs/', DOCUMENT_PREFIXES)
        for prefix in DOCUMENT_PREFIXES:
            with self.subTest(prefix=prefix):
                self.assertTrue(prefix.endswith('/'))
                self.assertNotIn(prefix, DOCUMENT_ROOT_FILES | DOCUMENT_FILES)

    def test_a_suffix_glued_sibling_of_an_admitted_log_is_not_admitted(self) -> None:
        for path in (
            'engineering/decisions.md.bak',
            'engineering/decisions.mdanything',
            'engineering/mistakes.mdx',
            'engineering/mistakes.md~',
        ):
            with self.subTest(path=path):
                self.assertEqual(_classify_path(path), 'unallowlisted-path')
                scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS, path])
                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], 'unallowlisted-path')

    def test_an_unnormalized_path_cannot_escape_the_prefix_rules(self) -> None:
        # The inventory validator rejects these today; the classifier must not admit them even
        # if a future caller forgets it, because the allowlist is matched with string prefixes.
        for path in (
            'packages/../../etc/passwd',
            'docs/../../etc/passwd',
            'engineering/changes/../../etc/shadow',
            './README.md',
            '/etc/passwd',
            'README.md/',
            '',
        ):
            with self.subTest(path=path):
                self.assertEqual(_classify_path(path), 'unnormalized-path')

    def test_a_non_lockstep_test_change_reports_its_own_reason_code(self) -> None:
        # Deleting this guard would still keep the full profile (no later rule admits tests/),
        # so the reason code is pinned: the lane must say "test change", not "unknown path".
        for path in ('tests/test_verification_doctor.py', 'tests/test_history.py', 'tests/aux.py'):
            with self.subTest(path=path):
                self.assertEqual(_classify_path(path), 'test-suite-change')
                scope = self._scope(['README.md', *FOCUSED_TEST_TARGETS, path])
                self.assertFalse(scope['eligible'])
                self.assertEqual(scope['reason_code'], 'test-suite-change')

    def test_the_lane_tests_themselves_are_not_admitted(self) -> None:
        # The classifier must never be certified by the change it certifies.
        self.assertEqual(_classify_path('tests/test_verification_scope.py'), 'test-suite-change')
        self.assertFalse(self._scope(['tests/test_verification_scope.py'])['eligible'])


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
        for target in FOCUSED_TEST_TARGETS:
            path = root / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_TRIVIAL_TEST, encoding='utf-8')
        # A suite member that records that full discovery actually reached it.
        (root / 'tests' / 'test_full_suite_only.py').write_text(
            _full_suite_marker_source(root), encoding='utf-8'
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
                'the focused profile executed a suite member outside the admitted modules',
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


class FocusedPythonEmptyTargetTests(unittest.TestCase):
    """`python -m unittest` with no module arguments exits 0 having run zero tests."""

    def test_an_empty_target_list_fails_instead_of_reporting_a_green_zero_test_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-empty-') as tmp:
            root = Path(tmp)
            (root / 'tests').mkdir(parents=True)
            (root / 'tests' / 'test_probe.py').write_text(_TRIVIAL_TEST, encoding='utf-8')
            scope = {'eligible': True, 'profile': DOCS_STATE_PROFILE, 'focused_tests': []}

            checks = {item.name: item for item in _python(root, 'pr', scope)}

            self.assertEqual(checks['python-focused-unittest'].status, 'fail')
            self.assertIsNone(checks['python-focused-unittest'].command)
            self.assertFalse((root / 'full-suite-executed.marker').exists())

    def test_the_replaced_runner_is_named_by_the_caller_not_assumed(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-empty-') as tmp:
            root = Path(tmp)
            (root / 'tests').mkdir(parents=True)
            for target in FOCUSED_TEST_TARGETS:
                path = root / target
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(_TRIVIAL_TEST, encoding='utf-8')
            scope = {
                'eligible': True,
                'profile': DOCS_STATE_PROFILE,
                'focused_tests': list(FOCUSED_TEST_TARGETS),
            }

            checks = {item.name: item for item in _python(root, 'pr', scope)}

            # This tree has no pyproject.toml/requirements.txt/setup.py, so the replaced
            # full-discovery runner is python-unittest and that is the skip that must appear.
            self.assertEqual(checks['python-unittest'].status, 'skip')
            self.assertEqual(checks['python-focused-unittest'].status, 'pass')


class DocsStateStatusInventoryTests(unittest.TestCase):
    """The veto channel must span exactly the path domain of the inventory it guards."""

    def _selection(self, root: Path, base: str) -> verification_module.GitRangeSelection:
        return verification_module.GitRangeSelection(bases=[verification_module.GitRangeBase(
            kind='route', source='route.base_commit',
            target_sha=_git_head(root), comparison_base_sha=base,
        )])

    def _docs_repo(self, root: Path):
        git = _init_repo(root)
        (root / 'docs').mkdir()
        (root / 'docs' / 'package-status.md').write_text('# status\n', encoding='utf-8')
        (root / 'README.md').write_text('# probe\n', encoding='utf-8')
        git('add', '.')
        git('commit', '-qm', 'baseline')
        return git

    def test_untracked_paths_arrive_as_status_records_so_the_veto_covers_them(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-status-') as tmp:
            root = Path(tmp)
            self._docs_repo(root)
            base = _git_head(root)
            (root / 'docs' / 'INVESTOR_DEMO.md').write_text('# demo\n', encoding='utf-8')
            (root / 'docs' / 'package-status.md').write_text('# status\n\nrevised\n', encoding='utf-8')

            records, trusted = verification_module._docs_state_status_inventory(
                root, self._selection(root, base)
            )
            by_path = {str(item['path']): item['status'] for item in records}

            # '??' is in SAFE_FILE_STATUSES only because this channel really can produce it,
            # and every untracked path the changed-file inventory can carry gets a record here.
            self.assertTrue(trusted)
            self.assertIn('??', SAFE_FILE_STATUSES)
            self.assertEqual(by_path.get('docs/INVESTOR_DEMO.md'), '??')
            self.assertEqual(by_path.get('docs/package-status.md'), 'M')
            scope = select_docs_state_scope(
                'pr',
                ['README.md', 'docs/package-status.md', 'docs/INVESTOR_DEMO.md', *FOCUSED_TEST_TARGETS],
                range_base_count=1,
                file_statuses=records,
                status_inventory_trusted=trusted,
                available_test_targets=list(FOCUSED_TEST_TARGETS),
            )
            self.assertTrue(scope['eligible'], scope)

    def test_a_rename_blind_primary_inventory_still_meets_the_status_veto(self) -> None:
        # With rename detection on, `git diff --name-only` collapses a source removal behind a
        # documentation name into one allowlisted path. The side channel reports the deletion
        # and vetoes on its own, which is the property this lane's safety claim rests on.
        with tempfile.TemporaryDirectory(prefix='grok-scope-rename-') as tmp:
            root = Path(tmp)
            git = self._docs_repo(root)
            source = root / '.grok-stack' / 'adaptive_grok' / 'service.py'
            source.parent.mkdir(parents=True)
            source.write_text('PRODUCT STATEMENT = "executed"\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'add source')
            base = _git_head(root)
            self.assertIn('docs/INVESTOR_DEMO.md', DOCUMENT_FILES)
            git('mv', str(source.relative_to(root)), 'docs/INVESTOR_DEMO.md')
            git('commit', '-qm', 'rename source behind an admitted docs name')

            collapsed = subprocess.run(
                ['git', 'diff', '--name-only', f'{base}...HEAD'],
                cwd=root, capture_output=True, text=True, check=True,
            ).stdout.split()
            self.assertEqual(collapsed, ['docs/INVESTOR_DEMO.md'], 'git did not collapse the rename')

            production = util_module.changed_files(root, base)
            self.assertEqual(
                production,
                ['.grok-stack/adaptive_grok/service.py', 'docs/INVESTOR_DEMO.md'],
                'the production inventory no longer reads diffs with --no-renames',
            )

            records, trusted = verification_module._docs_state_status_inventory(
                root, self._selection(root, base)
            )
            self.assertIn('D', {str(item['status']) for item in records})

            vetoed = select_docs_state_scope(
                'pr',
                [*collapsed, *FOCUSED_TEST_TARGETS],
                range_base_count=1,
                file_statuses=records,
                status_inventory_trusted=trusted,
                available_test_targets=list(FOCUSED_TEST_TARGETS),
            )
            self.assertFalse(vetoed['eligible'])
            self.assertEqual(vetoed['reason_code'], 'unsafe-file-status')

    def test_rename_detection_is_disabled_on_every_side_channel_read(self) -> None:
        # Three properties at once, all of them claimed in comments before this arm existed:
        # the side channel must read *both* halves without rename/copy scoring; the shared
        # helper must still score them for the landing lane by default; and a working-tree
        # rename must actually be invisible to the docs/state veto only because the production
        # inventory keeps the deleted path in view.
        with tempfile.TemporaryDirectory(prefix='grok-scope-reads-') as tmp:
            root = Path(tmp)
            git = self._docs_repo(root)
            base = _git_head(root)
            git('mv', 'docs/package-status.md', 'docs/INVESTOR_DEMO.md')

            records, trusted = verification_module._docs_state_status_inventory(
                root, self._selection(root, base)
            )

            # Both halves of the side channel read with rename/copy detection off, so the staged
            # rename arrives as the deletion-plus-addition it is. Reading it with rename scoring
            # would report `R100` plus an `original_path`, and a scaffolded package would report
            # `C0xx`, which is exactly the veto that kept this lane from ever firing.
            self.assertTrue(trusted)
            self.assertEqual(
                {str(item['status']) for item in records}, {'A', 'D'},
                'a working-tree rename reached the docs/state channel as R/C',
            )

            # The landing lane's default read still sees the very same rename as a rename, and the
            # production inventory keeps the deleted path visible instead of collapsing to one name.
            landing = util_module.changed_file_statuses(root)
            self.assertTrue(any(str(item['status']).startswith('R') for item in landing or []))
            self.assertEqual(
                util_module.changed_files(root, base),
                ['docs/INVESTOR_DEMO.md', 'docs/package-status.md'],
            )
            vetoed = select_docs_state_scope(
                'pr',
                ['docs/INVESTOR_DEMO.md', *FOCUSED_TEST_TARGETS],
                range_base_count=1,
                file_statuses=records,
                status_inventory_trusted=trusted,
                available_test_targets=list(FOCUSED_TEST_TARGETS),
            )
            self.assertFalse(vetoed['eligible'])
            self.assertEqual(vetoed['reason_code'], 'unsafe-file-status')

    def test_a_staged_successor_package_is_not_pushed_out_by_copy_detection(self) -> None:
        # The committed half of this channel is pinned by RealRepositoryInventoryTests. The
        # staged half matters just as much: git scores a freshly scaffolded package as a copy of
        # an older one in `diff --cached` too, so with copy detection the worktree/index read
        # would report C0xx plus an original_path and veto every evidence-carrying pull request.
        with tempfile.TemporaryDirectory(prefix='grok-scope-staged-') as tmp:
            root = Path(tmp)
            git = self._docs_repo(root)
            old = root / 'engineering/changes/20260101-old-package'
            old.mkdir(parents=True)
            for name, body in (
                ('requirements.md', '# Requirements\n\n' + 'stable scaffold text\n' * 40 + '\n'),
                ('tasks.md', '# Tasks\n\n' + '1. bounded step\n' * 40 + '\n'),
                ('release.md', '# Release\n\n' + 'roll forward, roll back\n' * 40 + '\n'),
            ):
                (old / name).write_text(body, encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'historical package')
            base = _git_head(root)
            successor = root / 'engineering/changes/20260924-new-package'
            successor.mkdir()
            for name in ('requirements.md', 'tasks.md', 'release.md'):
                shutil.copyfile(old / name, successor / name)
            git('add', 'engineering/changes/20260924-new-package')

            staged = subprocess.run(
                ['git', 'diff', '--cached', '--name-status', '--find-copies-harder'],
                cwd=root, capture_output=True, text=True, check=True,
            ).stdout
            self.assertRegex(staged, r'C\d{2,3}\t', 'git reported no copy: the test is vacuous')

            records, trusted = verification_module._docs_state_status_inventory(
                root, self._selection(root, base)
            )
            statuses = {str(item['status']) for item in records}

            self.assertTrue(trusted)
            self.assertFalse(any(status.startswith(('C', 'R')) for status in statuses))
            self.assertTrue(any(status.startswith('A') for status in statuses))
            scope = select_docs_state_scope(
                'pr',
                sorted({str(item['path']) for item in records}),
                range_base_count=1,
                file_statuses=records,
                status_inventory_trusted=trusted,
                available_test_targets=list(FOCUSED_TEST_TARGETS),
            )
            self.assertTrue(scope['eligible'], scope)

    def test_the_shared_helper_still_reports_renames_and_copies_by_default(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-flags-') as tmp:
            root = Path(tmp)
            git = self._docs_repo(root)
            git('mv', 'docs/package-status.md', 'docs/handbook.md')
            detected = util_module.changed_file_statuses(root)
            withheld = util_module.changed_file_statuses(root, rename_detection=False)

            self.assertIsNotNone(detected)
            self.assertIsNotNone(withheld)
            # Git names a rename `R<score>`, so the assertion is on the status prefix.
            self.assertTrue(any(str(item['status']).startswith('R') for item in detected or []))
            self.assertFalse(any(str(item['status']).startswith('R') for item in withheld or []))
            self.assertEqual(
                {str(item['status']) for item in withheld or []}, {'D', 'A'}
            )


class VerifyDocsStateScopeEndToEndTests(unittest.TestCase):
    """verify() must act on the classification, not merely report that it classified.

    Every arm above calls the pure classifier or ``_python`` directly, so verify() could pass
    an empty available-target list, hard-code the status channel as trusted, or never thread the
    scope into the runner and stay green while the receipt advertises a profile it did not run.
    """

    def _repo(self, root: Path, omit: tuple[str, ...] = ()) -> tuple[object, str]:
        git = _init_repo(root)
        (root / 'tests').mkdir()
        for target in FOCUSED_TEST_TARGETS:
            if target in omit:
                continue
            path = root / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_TRIVIAL_TEST, encoding='utf-8')
        (root / 'tests' / 'test_full_suite_only.py').write_text(
            _full_suite_marker_source(root), encoding='utf-8'
        )
        (root / '.coveragerc').write_text(
            '[run]\nbranch = False\nsource =\n    tests\n\n[report]\nshow_missing = False\n',
            encoding='utf-8',
        )
        (root / 'docs').mkdir()
        (root / 'docs' / 'package-status.md').write_text('# status\n', encoding='utf-8')
        (root / 'README.md').write_text('# probe\n\nidentity 1.0.0\n', encoding='utf-8')
        (root / 'PROJECT_STATE.json').write_text('{"version": "1.0.0"}\n', encoding='utf-8')
        git('add', '.')
        git('commit', '-qm', 'baseline')
        base = _git_head(root)

        from adaptive_grok.router import build_route
        from adaptive_grok.state import set_active_route

        route = build_route(root, 'Refresh release documentation and dated state', 'e2e-205').to_dict()
        route['base_commit'] = base
        route['quality_profiles'] = ['base']
        route['delivery_expected'] = False
        set_active_route(root, route)
        return git, base

    def _checks(self, report: dict[str, object]) -> dict[str, str]:
        return {str(item['name']): str(item['status']) for item in report['checks']}

    def test_verify_selects_and_runs_the_focused_profile_for_a_docs_only_successor(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-verify-') as tmp:
            root = Path(tmp)
            git, _ = self._repo(root)
            (root / 'README.md').write_text('# probe\n\nidentity 1.0.1\n', encoding='utf-8')
            (root / 'docs' / 'package-status.md').write_text('# status\n\nrevised\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'docs successor')

            report = verify(root, mode='pr', record=False)

            scope = report['docs_state_scope']
            self.assertTrue(scope['eligible'], scope)
            self.assertEqual(scope['profile'], DOCS_STATE_PROFILE)
            self.assertEqual(scope['evidence_kind'], f'verification:{DOCS_STATE_PROFILE}')
            checks = self._checks(report)
            self.assertEqual(checks.get('python-focused-unittest'), 'pass')
            self.assertEqual(checks.get('python-unittest'), 'skip')
            self.assertEqual(checks.get('coverage'), 'skip')
            self.assertEqual(checks.get('factory-postgres-exit'), 'skip')
            self.assertEqual(scope['skipped_checks'], list(FOCUSED_SKIPPED_CHECKS))
            self.assertIn('python-unittest', scope['skipped_checks'])
            self.assertFalse(
                (root / 'full-suite-executed.marker').exists(),
                'verify() ran full discovery although it reported the focused profile',
            )

    def test_verify_puts_the_full_suite_back_for_one_committed_source_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-verify-') as tmp:
            root = Path(tmp)
            git, _ = self._repo(root)
            (root / '.grok-stack' / 'adaptive_grok').mkdir(parents=True)
            (root / '.grok-stack' / 'adaptive_grok' / 'service.py').write_text(
                'PRODUCT STATEMENT = 2\n', encoding='utf-8'
            )
            (root / 'README.md').write_text('# probe\n\nidentity 1.0.1\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'source change with prose')

            report = verify(root, mode='pr', record=False)

            scope = report['docs_state_scope']
            self.assertFalse(scope['eligible'])
            self.assertEqual(scope['profile'], FULL_PROFILE)
            self.assertEqual(scope['reason_code'], 'unallowlisted-path')
            checks = self._checks(report)
            self.assertNotIn('python-focused-unittest', checks)
            self.assertIn('python-unittest', checks)
            self.assertTrue(
                (root / 'full-suite-executed.marker').exists(),
                'a source change did not put full discovery back on the critical path',
            )

    def test_verify_refuses_the_lane_when_the_status_channel_is_not_trusted(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-verify-') as tmp:
            root = Path(tmp)
            git, _ = self._repo(root)
            (root / 'README.md').write_text('# probe\n\nidentity 1.0.1\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'docs successor')
            original = verification_module._docs_state_status_inventory
            verification_module._docs_state_status_inventory = lambda *_args, **_kwargs: ([], False)
            try:
                report = verify(root, mode='pr', record=False)
            finally:
                verification_module._docs_state_status_inventory = original

            scope = report['docs_state_scope']
            self.assertFalse(scope['eligible'])
            self.assertEqual(scope['reason_code'], 'file-status-inventory-unavailable')
            self.assertTrue(
                (root / 'full-suite-executed.marker').exists(),
                'an untrusted status channel did not put the full suite back',
            )

    def test_the_status_channel_must_say_it_is_trusted(self) -> None:
        # verify() forwards whatever the side channel reported. A channel that cannot answer is
        # not an answer: treating "unknown" as trusted would drop one of the two status vetoes
        # while the receipt still advertises a classification it derived from nothing.
        with tempfile.TemporaryDirectory(prefix='grok-scope-verify-') as tmp:
            root = Path(tmp)
            git, _ = self._repo(root)
            (root / 'README.md').write_text('# probe\n\nidentity 1.0.1\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'docs successor')
            original = verification_module._docs_state_status_inventory
            verification_module._docs_state_status_inventory = lambda *_args, **_kwargs: ([], None)
            try:
                report = verify(root, mode='pr', record=False)
            finally:
                verification_module._docs_state_status_inventory = original

            scope = report['docs_state_scope']
            self.assertFalse(scope['eligible'])
            self.assertEqual(scope['reason_code'], 'file-status-inventory-unavailable')
            self.assertEqual(scope['profile'], FULL_PROFILE)

    def test_verify_refuses_the_lane_when_an_admitted_module_is_absent_from_the_checkout(self) -> None:
        with tempfile.TemporaryDirectory(prefix='grok-scope-verify-') as tmp:
            root = Path(tmp)
            absent = FOCUSED_TEST_TARGETS[-1]
            git, _ = self._repo(root, omit=(absent,))
            (root / 'README.md').write_text('# probe\n\nidentity 1.0.1\n', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'docs successor')

            report = verify(root, mode='pr', record=False)

            scope = report['docs_state_scope']
            self.assertFalse(scope['eligible'])
            self.assertEqual(scope['reason_code'], 'lockstep-target-unavailable')
            self.assertIn(absent, scope['rejected_files'])
            self.assertTrue(
                (root / 'full-suite-executed.marker').exists(),
                'an absent admitted module did not put the full suite back',
            )


if __name__ == '__main__':
    unittest.main()
