"""Issue #54: the health screen must show the local Git delivery surface, read-only.

This repository keeps 190+ linked worktrees and 200+ local branches. Some worktrees carry
hundreds of uncommitted files, some branches point their upstream at a protected base branch,
and stashes are labelled only by a branch that may no longer exist. ``grok_doctor`` reported
none of it, and a commit held only by a clean detached worktree was invisible to a branch-tip
comparison.

These tests build a small repository that reproduces every hazard, plus a clean control that
must not trip, and pin three boundaries: the audit only reads; a read it could not perform is
never reported as a zero; and a check it skipped is never offered as proof that work was
delivered.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok import doctor, git_audit
from adaptive_grok.doctor import run_doctor
from adaptive_grok.git_audit import (
    _repository_slug,
    audit_git_state,
    doctor_items,
    format_audit,
    hazard_count,
)
from tests._support import project_copy


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ['git', *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    if proc.returncode:
        raise AssertionError(f'git {" ".join(args)} failed: {proc.stderr.strip()}')
    return proc.stdout


def _identity(cwd: Path) -> None:
    _git(cwd, 'config', 'user.name', 'Audit Tester')
    _git(cwd, 'config', 'user.email', 'audit@example.invalid')
    _git(cwd, 'config', 'commit.gpgsign', 'false')


def _current_branch(cwd: Path) -> str:
    return _git(cwd, 'rev-parse', '--abbrev-ref', 'HEAD').strip()


class _GitScaffold(unittest.TestCase):
    """Shared builder for a repository carrying every hazard issue #54 describes."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix='git-delivery-audit-')
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.root = self.base / 'repo'
        _git(self.base, 'init', '-q', '--bare', 'origin.git')
        self.remote = self.base / 'origin.git'
        _git(self.base, 'init', '-q', '-b', 'main', str(self.root))
        _identity(self.root)
        (self.root / 'tracked.txt').write_text('base\n', encoding='utf-8')
        _git(self.root, 'add', 'tracked.txt')
        _git(self.root, 'commit', '-qm', 'base')
        _git(self.root, 'remote', 'add', 'origin', str(self.remote))
        _git(self.root, 'push', '-q', '-u', 'origin', 'main')

    # -- hazard builders -------------------------------------------------------------
    def add_protected_upstream(self) -> None:
        """A feature branch whose upstream is the protected base branch."""
        _git(self.root, 'checkout', '-qb', 'feature/danger')
        (self.root / 'danger.txt').write_text('work\n', encoding='utf-8')
        _git(self.root, 'add', 'danger.txt')
        _git(self.root, 'commit', '-qm', 'feature work')
        _git(self.root, 'branch', '--set-upstream-to=origin/main', 'feature/danger')
        _git(self.root, 'checkout', '-q', 'main')

    add_wrong_upstream = add_protected_upstream

    def add_unpushed_branch(self) -> None:
        _git(self.root, 'checkout', '-qb', 'local/only')
        (self.root / 'only.txt').write_text('local only\n', encoding='utf-8')
        _git(self.root, 'add', 'only.txt')
        _git(self.root, 'commit', '-qm', 'never pushed')
        _git(self.root, 'checkout', '-q', 'main')

    def add_gone_upstream(self) -> None:
        _git(self.root, 'checkout', '-qb', 'feature/gone')
        (self.root / 'gone.txt').write_text('gone\n', encoding='utf-8')
        _git(self.root, 'add', 'gone.txt')
        _git(self.root, 'commit', '-qm', 'pushed once')
        _git(self.root, 'push', '-q', '-u', 'origin', 'feature/gone')
        _git(self.root, 'checkout', '-q', 'main')
        # Delete only the remote-tracking ref: branch.feature/gone.* config survives,
        # which is exactly the orphaned state ``git branch -vv`` shows as ": gone".
        _git(self.root, 'update-ref', '-d', 'refs/remotes/origin/feature/gone')

    def add_dirty_worktree(self, name: str = 'wt-dirty') -> Path:
        path = self.base / name
        _git(self.root, 'worktree', 'add', '-q', '--detach', str(path), 'HEAD')
        (path / 'tracked.txt').write_text('uncommitted edit\n', encoding='utf-8')
        return path

    def add_missing_worktree(self, name: str = 'wt-missing') -> Path:
        path = self.base / name
        _git(self.root, 'worktree', 'add', '-q', '--detach', str(path), 'HEAD')
        shutil.rmtree(path)
        return path

    def add_unreadable_worktree(self, name: str = 'wt-unreadable') -> Path:
        """A registration whose directory is alive but is no longer a worktree.

        `git status` in it exits 128, which is neither "clean" nor "absent": the audit has to say
        it could not look.
        """
        path = self.base / name
        _git(self.root, 'worktree', 'add', '-q', '--detach', str(path), 'HEAD')
        (path / '.git').unlink()
        return path

    def add_detached_unpushed_worktree(self, name: str = 'wt-unpushed') -> str:
        """A clean detached worktree holding the only copy of a commit.

        The commit is on no branch and no remote: `refs/heads` never mentions it, so only the
        worktree registry's HEAD can reveal it.
        """
        _git(self.root, 'checkout', '-qb', 'work/then-deleted')
        (self.root / 'precious.txt').write_text('only here\n', encoding='utf-8')
        _git(self.root, 'add', 'precious.txt')
        _git(self.root, 'commit', '-qm', 'work on no branch')
        sha = _git(self.root, 'rev-parse', 'HEAD').strip()
        _git(self.root, 'checkout', '-q', 'main')
        _git(self.root, 'branch', '-D', 'work/then-deleted')
        _git(self.root, 'worktree', 'add', '-q', '--detach', str(self.base / name), sha)
        return sha

    def add_stash(self) -> None:
        (self.root / 'tracked.txt').write_text('work in progress\n', encoding='utf-8')
        _git(self.root, 'stash', 'push', '-q', '-m', 'rescue before rebase')

    def deliver_every_branch(self) -> None:
        """Clean control: every branch is pushed and tracks its own remote ref."""
        _git(self.root, 'push', '-q', 'origin', 'main')

    def snapshot(self) -> str:
        """Everything the audit could possibly damage, as one comparable string.

        The bare `origin` is included: a push would change it, and the audit must not push. The
        whole local config (not just `branch.*`), the `.git` file listings, the index and the HEAD
        reflog are included because a read-only claim has to be blind to nothing that a Git write
        would leave behind - `git config gc.auto 0` changes none of refs, branch config, stashes,
        the worktree registry or HEAD, and used to pass as read-only.
        """
        gitdir = Path(_git(self.root, 'rev-parse', '--absolute-git-dir').strip())
        return '\n'.join(
            (
                _git(self.root, 'for-each-ref', '--format=%(refname) %(objectname)'),
                _git(self.root, 'config', '--get-regexp', '^branch\\.'),
                _git(self.root, 'config', '--list', '--local'),
                _git(self.root, 'reflog', 'show', '-g', 'HEAD', '--format=%H %gs'),
                _git(self.root, 'ls-files', '--stage'),
                _git(self.root, 'stash', 'list'),
                _git(self.root, 'worktree', 'list', '--porcelain'),
                _git(self.root, 'rev-parse', '--verify', 'HEAD'),
                self._listing(gitdir),
                self._listing(gitdir / 'worktrees'),
                _git(self.remote, 'for-each-ref', '--format=%(refname) %(objectname)'),
            )
        )

    @staticmethod
    def _listing(directory: Path) -> str:
        if not directory.is_dir():
            return f'<absent {directory.name}>'
        return '\n'.join(f'{directory.name}/{entry.name}' for entry in sorted(directory.iterdir()))

    @staticmethod
    def _failing_git(fragment: str, code: int = 128):
        """A `run` stand-in that fails only the Git command containing `fragment`."""
        real = git_audit.run

        def fake(args, **kwargs):
            if fragment in ' '.join(args):
                return subprocess.CompletedProcess(list(args), code, '', 'fatal: simulated failure')
            return real(args, **kwargs)

        return fake

    def rows(self, report) -> dict:
        """`{row name: (status, message)}` for one report."""
        return {name: (status, message) for status, name, message in doctor_items(report)}


class GitDeliveryAuditTests(_GitScaffold):
    def test_flags_branch_whose_upstream_is_a_protected_base(self) -> None:
        self.add_wrong_upstream()
        report = audit_git_state(self.root)
        pairs = {
            (entry['branch'], entry['upstream'])
            for entry in report['branches']['upstream_protected']
        }
        self.assertIn(('feature/danger', 'origin/main'), pairs)

    def test_own_base_branch_tracking_its_remote_is_not_a_hazard(self) -> None:
        # The control: `main` tracking `origin/main` is correct and must never be listed,
        # otherwise the report buries the real trap in a false positive.
        report = audit_git_state(self.root)
        self.assertEqual(report['branches']['upstream_protected'], [])
        self.assertEqual(report['branches']['upstream_gone'], [])

    def test_flags_upstream_whose_remote_ref_was_deleted(self) -> None:
        self.add_gone_upstream()
        report = audit_git_state(self.root)
        pairs = {
            (entry['branch'], entry['upstream'])
            for entry in report['branches']['upstream_gone']
        }
        self.assertIn(('feature/gone', 'origin/feature/gone'), pairs)

    def test_lists_branches_without_any_upstream(self) -> None:
        self.add_unpushed_branch()
        report = audit_git_state(self.root)
        self.assertIn('local/only', report['branches']['no_upstream'])

    def test_reports_branch_tip_that_no_remote_can_recover(self) -> None:
        self.add_unpushed_branch()
        report = audit_git_state(self.root)
        self.assertEqual(report['branches']['unpushed_state'], 'checked')
        self.assertIn('local/only', report['branches']['unpushed_tips'])
        self.assertNotIn('main', report['branches']['unpushed_tips'])

    def test_without_any_remote_the_tip_check_is_skipped_not_guessed(self) -> None:
        plain = self.base / 'no-remote'
        _git(self.base, 'init', '-q', '-b', 'main', str(plain))
        _identity(plain)
        (plain / 'local.txt').write_text('only here\n', encoding='utf-8')
        _git(plain, 'add', 'local.txt')
        _git(plain, 'commit', '-qm', 'nothing to compare against')
        report = audit_git_state(plain)
        self.assertEqual(report['branches']['remotes'], [])
        self.assertEqual(report['branches']['unpushed_state'], 'skipped')
        self.assertIn('no remote-tracking branches', report['branches']['unpushed_skip_reason'])
        self.assertEqual(report['branches']['unpushed_tips'], [])
        # An empty unpushed list from a skipped check is not proof of delivery. In a repository
        # with no remote it used to produce `git branch --set-upstream-to=origin/main main` -
        # precisely the protected-upstream hazard issue #54 is about.
        commands = report['human_commands']
        self.assertFalse(
            [command for command in commands if '--set-upstream-to=' in command], commands
        )
        self.assertFalse([command for command in commands if command.startswith('git fetch')], commands)
        self.assertTrue(any('NOT established' in command for command in commands), commands)
        screen = format_audit(report)
        self.assertIn('unpushed-tip check skipped: no remote-tracking branches', screen)
        self.assertNotIn('no delivery hazard found', screen)

    def test_reports_dirty_and_vanished_worktrees(self) -> None:
        dirty = self.add_dirty_worktree()
        self.add_missing_worktree()
        report = audit_git_state(self.root)
        self.assertEqual(report['worktrees']['registered'], 3)
        self.assertEqual(
            [entry['path'] for entry in report['worktrees']['dirty']], [str(dirty)]
        )
        self.assertEqual(report['worktrees']['dirty'][0]['changed_files'], 1)
        self.assertEqual(len(report['worktrees']['missing']), 1)
        self.assertEqual(report['worktrees']['missing_count'], 1)
        self.assertIn(
            'non-existent', report['worktrees']['missing'][0]['reason'].lower()
        )
        # The control for the detached rule: this worktree is detached, but it sits on a commit
        # `main` already stands on, so it is not work at risk.
        self.assertEqual(report['branches']['unpushed_detached'], [])

    def test_untracked_only_worktree_is_not_reported_clean(self) -> None:
        path = self.base / 'wt-untracked'
        _git(self.root, 'worktree', 'add', '-q', '--detach', str(path), 'HEAD')
        (path / 'only-untracked.txt').write_text('unsaved\n', encoding='utf-8')

        report = audit_git_state(self.root)

        self.assertEqual(
            report['worktrees']['dirty'],
            [{'path': str(path), 'branch': None, 'changed_files': 1}],
        )

    def test_nested_untracked_files_are_counted_individually(self) -> None:
        path = self.base / 'wt-nested-untracked'
        _git(self.root, 'worktree', 'add', '-q', '--detach', str(path), 'HEAD')
        nested = path / 'new' / 'nested'
        nested.mkdir(parents=True)
        (path / 'new' / 'one.txt').write_text('one\n', encoding='utf-8')
        (nested / 'two.txt').write_text('two\n', encoding='utf-8')
        (nested / 'three.txt').write_text('three\n', encoding='utf-8')

        report = audit_git_state(self.root)

        self.assertEqual(
            report['worktrees']['dirty'],
            [{'path': str(path), 'branch': None, 'changed_files': 3}],
        )

    def test_dirty_submodule_worktree_is_not_reported_clean(self) -> None:
        module = self.base / 'module-source'
        _git(self.base, 'init', '-q', '-b', 'main', str(module))
        _identity(module)
        (module / 'module.txt').write_text('base\n', encoding='utf-8')
        _git(module, 'add', 'module.txt')
        _git(module, 'commit', '-qm', 'module base')
        _git(
            self.root,
            '-c',
            'protocol.file.allow=always',
            'submodule',
            'add',
            '-q',
            str(module),
            'modules/demo',
        )
        _git(self.root, 'commit', '-qam', 'add module')
        (self.root / 'modules' / 'demo' / 'module.txt').write_text(
            'dirty inside module\n', encoding='utf-8'
        )

        report = audit_git_state(self.root)

        self.assertEqual(
            report['worktrees']['dirty'],
            [{'path': str(self.root), 'branch': 'main', 'changed_files': 1}],
        )

    def test_reports_stash_entries_with_their_branch_label(self) -> None:
        self.add_stash()
        report = audit_git_state(self.root)
        self.assertEqual(report['stashes']['count'], 1)
        entry = report['stashes']['entries'][0]
        self.assertEqual(entry['branch'], 'main')
        self.assertIn('rescue before rebase', entry['subject'])

    def test_a_worktree_that_refuses_git_status_is_reported_as_unreadable(self) -> None:
        broken = self.add_unreadable_worktree()
        report = audit_git_state(self.root)
        worktrees = report['worktrees']
        self.assertEqual(worktrees['unreadable_count'], 1)
        self.assertEqual(worktrees['unreadable'], [str(broken)])
        self.assertEqual(worktrees['scanned'], 2)
        self.assertFalse(worktrees['dirty'])
        self.assertEqual(worktrees['dirty_state'], 'unknown')
        self.assertTrue(worktrees['incomplete'])
        self.assertTrue(
            any('git status failed' in cause for cause in worktrees['incomplete_causes']),
            worktrees['incomplete_causes'],
        )
        rows = self.rows(report)
        self.assertEqual(rows['git-worktrees'][0], 'info')
        self.assertIn('1 unreadable', rows['git-worktrees'][1])
        self.assertIn('unknown with uncommitted changes', rows['git-worktrees'][1])
        self.assertNotIn('0 with uncommitted changes', rows['git-worktrees'][1])
        # Counts the screen used to hide: prunable registrations and unreadable paths.
        screen = format_audit(report)
        self.assertIn('1 unreadable', screen)
        self.assertIn('1 prunable', screen)
        self.assertIn('scan incomplete: git status failed in 1 registered worktree path(s)', screen)

    def test_the_audit_budget_is_reported_as_limited_not_clean(self) -> None:
        self.add_dirty_worktree('wt-one')
        self.add_dirty_worktree('wt-two')
        real = git_audit.run
        calls: list[str] = []

        def recording_run(args, **kwargs):
            calls.append(' '.join(args))
            return real(args, **kwargs)

        with mock.patch.object(git_audit, 'run', recording_run):
            report = audit_git_state(self.root, budget_seconds=0.0)

        # Repository detection is part of the same deadline as every later read. With no budget
        # left, even the first Git subprocess is refused and every unmeasured headline is unknown.
        self.assertEqual(calls, [])
        self.assertIn('budget', report['error'])
        self.assertIsNone(report['worktrees']['registered'])
        self.assertIsNone(report['branches']['local'])
        self.assertIsNone(report['stashes']['count'])
        self.assertEqual(report['budget']['refused_reads'], 1)
        self.assertEqual(report['degraded'][0]['section'], 'repository')
        self.assertEqual(report['degraded'][0]['code'], 124)
        self.assertIn('git rev-parse --is-inside-work-tree', report['degraded'][0]['command'])
        self.assertIn('budget', format_audit(report))
        # And the default is bounded, which is the point: `tests.test_verification_doctor` calls
        # run_doctor(ROOT) against this real 195-worktree clone, so without a whole-pass deadline
        # the worst case is 250 scans x the per-command 30 s timeout (~125 min) inside a test of
        # our own module. A caller must get the bound without asking for it.
        self.assertEqual(
            audit_git_state(self.root)['budget']['seconds'], git_audit.AUDIT_BUDGET_SECONDS
        )
        self.assertLessEqual(git_audit.AUDIT_BUDGET_SECONDS, 30.0)

    def test_a_clean_detached_worktree_holding_the_only_copy_is_a_hazard(self) -> None:
        sha = self.add_detached_unpushed_worktree()
        report = audit_git_state(self.root)
        branches = report['branches']
        # A `refs/heads`-only comparison cannot see this commit at all.
        self.assertEqual(branches['unpushed_tips'], [])
        self.assertEqual(branches['unpushed_state'], 'checked')
        records = branches['unpushed_detached']
        self.assertEqual([record['head'] for record in records], [sha])
        self.assertEqual(records[0]['paths'], [str(self.base / 'wt-unpushed')])
        self.assertTrue(records[0]['detached'])
        self.assertGreaterEqual(hazard_count(report), 1)
        rows = self.rows(report)
        self.assertEqual(rows['git-branches'][0], 'info')
        self.assertIn('1 detached worktree tips not reachable either', rows['git-branches'][1])
        screen = format_audit(report)
        self.assertIn(f'detached tips on no remote: {sha[:12]}', screen)
        self.assertIn(str(self.base / 'wt-unpushed'), screen)
        self.assertNotIn('no delivery hazard found', screen)
        self.assertIn(
            f'switch -c delivery-rescue/{sha[:12]}', ' '.join(report['human_commands'])
        )

    def test_a_failing_registry_read_names_itself_instead_of_reporting_zero(self) -> None:
        detached_sha = self.add_detached_unpushed_worktree()
        with mock.patch.object(git_audit, 'run', self._failing_git('worktree list')):
            report = audit_git_state(self.root)
        self.assertIsNone(report['worktrees']['registered'])
        self.assertIsNone(report['worktrees']['detached'])
        self.assertIsNone(report['worktrees']['prunable'])
        self.assertIsNone(report['worktrees']['missing_count'])
        self.assertEqual(report['branches']['unpushed_state'], 'skipped')
        self.assertEqual(report['branches']['unpushed_detached_state'], 'unknown')
        self.assertIn('worktree registry', report['branches']['unpushed_skip_reason'])
        self.assertEqual(report['branches']['unpushed_detached'], [])
        self.assertTrue(report['worktrees']['incomplete'])
        degraded = report['degraded']
        self.assertEqual([item['section'] for item in degraded], ['worktrees'])
        self.assertEqual(degraded[0]['code'], 128)
        self.assertIn('git worktree list --porcelain', degraded[0]['command'])
        rows = self.rows(report)
        self.assertEqual(rows['git-worktrees'][0], 'info')
        self.assertIn('git worktree list --porcelain exited 128', rows['git-worktrees'][1])
        self.assertEqual(rows['git-audit-limited'][0], 'info')
        self.assertIn('could not be trusted', rows['git-audit-limited'][1])
        screen = format_audit(report)
        self.assertIn('worktrees: unknown registered', screen)
        self.assertIn('unknown with uncommitted changes', rows['git-worktrees'][1])
        self.assertIn('detached-tip check skipped: worktree registry', screen)
        self.assertNotIn('detached tips on no remote: none', screen)
        self.assertNotIn(detached_sha[:12], screen)
        self.assertTrue(
            any('rescue advice unavailable' in command for command in report['human_commands']),
            report['human_commands'],
        )
        self.assertIn('limited: git worktree list --porcelain exited 128', screen)
        self.assertNotIn('no delivery hazard found', screen)

    def test_a_failing_branch_read_cannot_report_a_clean_branch_registry(self) -> None:
        self.add_gone_upstream()
        self.add_wrong_upstream()
        with mock.patch.object(git_audit, 'run', self._failing_git('for-each-ref refs/heads')):
            report = audit_git_state(self.root)
        branches = report['branches']
        self.assertIsNone(branches['local'])
        # Nothing was enumerated, so nothing may be claimed: not "gone", not "protected", not
        # "every tip is reachable".
        self.assertEqual(branches['upstream_gone'], [])
        self.assertEqual(branches['upstream_protected'], [])
        self.assertEqual(branches['upstream_protected_state'], 'unknown')
        self.assertEqual(branches['upstream_gone_state'], 'unknown')
        self.assertEqual(branches['no_upstream_state'], 'unknown')
        self.assertEqual(branches['unpushed_tips'], [])
        rows = self.rows(report)
        self.assertEqual(rows['git-branches'][0], 'info')
        self.assertIn('git for-each-ref refs/heads exited 128', rows['git-branches'][1])
        self.assertIn('unknown protected-upstream', rows['git-branches'][1])
        self.assertIn('unknown gone-upstream', rows['git-branches'][1])
        self.assertIn('unknown without upstream', rows['git-branches'][1])
        self.assertIn('unknown not reachable from any remote', rows['git-branches'][1])
        self.assertNotIn('0 not reachable from any remote', rows['git-branches'][1])
        self.assertNotIn('0 protected-upstream', rows['git-branches'][1])
        self.assertIn('limited: git for-each-ref refs/heads exited 128', format_audit(report))
        # The screen must not close with the all-clear while a read it could not perform.
        self.assertNotIn('no delivery hazard found', format_audit(report))

    def test_a_failing_remote_ref_read_is_unknown_not_measured_zero(self) -> None:
        self.add_gone_upstream()
        with mock.patch.object(
            git_audit, 'run', self._failing_git('for-each-ref refs/remotes')
        ):
            report = audit_git_state(self.root)

        branches = report['branches']
        self.assertIsNone(branches['remote_refs'])
        self.assertEqual(branches['unpushed_state'], 'skipped')
        self.assertEqual(branches['upstream_gone_state'], 'unknown')
        self.assertIn('could not be enumerated', branches['unpushed_skip_reason'])
        row = self.rows(report)['git-branches']
        self.assertEqual(row[0], 'info')
        self.assertIn('unknown remote-tracking refs', row[1])
        self.assertIn('unknown gone-upstream', row[1])
        self.assertIn('unknown not reachable from any remote', row[1])
        self.assertNotIn('0 not reachable from any remote', row[1])
        self.assertNotIn('0 gone-upstream', row[1])
        self.assertIn('gone upstreams: unknown', format_audit(report))

    def test_a_timed_out_read_says_timed_out(self) -> None:
        with mock.patch.object(
            git_audit, 'run', self._failing_git('for-each-ref refs/heads', code=124)
        ):
            report = audit_git_state(self.root)
        self.assertEqual(report['degraded'][0]['code'], 124)
        rows = self.rows(report)
        self.assertIn('timed out', rows['git-branches'][1])
        self.assertEqual(rows['git-branches'][0], 'info')

    def test_an_unreadable_stash_list_is_unknown_not_zero(self) -> None:
        self.add_stash()
        with mock.patch.object(git_audit, 'run', self._failing_git('stash list')):
            report = audit_git_state(self.root)
        self.assertTrue(report['stashes']['unreadable'])
        self.assertIsNone(report['stashes']['count'])
        rows = self.rows(report)
        self.assertEqual(rows['git-stashes'][0], 'info')
        self.assertIn('could not be read', rows['git-stashes'][1])
        self.assertIn('stash list could not be read', format_audit(report))

    def test_an_unreadable_upstream_config_is_unknown_not_no_upstream(self) -> None:
        self.add_wrong_upstream()
        with mock.patch.object(
            git_audit, 'run', self._failing_git('config --get-regexp --local')
        ):
            report = audit_git_state(self.root)

        branches = report['branches']
        self.assertEqual(branches['upstream_state'], 'unknown')
        self.assertEqual(branches['upstream_protected_state'], 'unknown')
        self.assertEqual(branches['upstream_gone_state'], 'unknown')
        self.assertEqual(branches['no_upstream_state'], 'unknown')
        self.assertEqual(branches['upstream_protected'], [])
        self.assertEqual(branches['upstream_gone'], [])
        self.assertEqual(branches['no_upstream'], [])
        self.assertEqual(branches['proven_upstreams'], [])
        self.assertIn('unknown protected-upstream', self.rows(report)['git-branches'][1])
        self.assertIn('protected upstreams: unknown', format_audit(report))
        self.assertFalse(
            [command for command in report['human_commands'] if 'upstream' in command],
            report['human_commands'],
        )

    def test_an_unreadable_remote_registry_is_unknown_not_none(self) -> None:
        self.add_unpushed_branch()
        with mock.patch.object(git_audit, 'run', self._failing_git('git remote')):
            report = audit_git_state(self.root)

        branches = report['branches']
        self.assertIsNone(branches['remotes'])
        self.assertEqual(branches['proven_upstreams'], [])
        self.assertIn('remotes: unknown', format_audit(report))
        self.assertFalse(
            [
                command
                for command in report['human_commands']
                if command.startswith(('git fetch', 'git push')) or '--set-upstream-to=' in command
            ],
            report['human_commands'],
        )

    def test_branch_config_from_outside_the_repository_is_not_read_as_ours(self) -> None:
        # The audit is about this repository. A `branch.*` entry in the scanning user's global
        # config must not be able to hand a branch a protected-base upstream it never set.
        self.add_unpushed_branch()
        hostile = self.base / 'hostile.gitconfig'
        hostile.write_text(
            '[branch "local/only"]\n\tremote = origin\n\tmerge = refs/heads/main\n',
            encoding='utf-8',
        )
        with mock.patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(hostile)}):
            report = audit_git_state(self.root)
        self.assertEqual(report['branches']['upstream_protected'], [])
        self.assertIn('local/only', report['branches']['no_upstream'])

    def test_ambient_git_dir_and_work_tree_cannot_redirect_the_audit(self) -> None:
        self.add_unpushed_branch()
        decoy = self.base / 'decoy'
        _git(self.base, 'init', '-q', '-b', 'main', str(decoy))
        _identity(decoy)
        (decoy / 'decoy.txt').write_text('decoy\n', encoding='utf-8')
        _git(decoy, 'add', 'decoy.txt')
        _git(decoy, 'commit', '-qm', 'decoy')

        with mock.patch.dict(
            os.environ,
            {'GIT_DIR': str(decoy / '.git'), 'GIT_WORK_TREE': str(decoy)},
            clear=False,
        ):
            report = audit_git_state(self.root)

        self.assertIsNone(report['error'])
        self.assertEqual(report['branches']['local'], 2)
        self.assertIn('local/only', report['branches']['no_upstream'])

    def test_ambient_git_common_dir_cannot_hide_a_protected_upstream(self) -> None:
        self.add_wrong_upstream()
        decoy = self.base / 'common-decoy'
        _git(self.base, 'init', '-q', '-b', 'main', str(decoy))
        _identity(decoy)
        (decoy / 'tracked.txt').write_text('decoy\n', encoding='utf-8')
        _git(decoy, 'add', 'tracked.txt')
        _git(decoy, 'commit', '-qm', 'decoy')
        _git(decoy, 'config', 'branch.feature/danger.remote', 'origin')
        _git(decoy, 'config', 'branch.feature/danger.merge', 'refs/heads/feature/danger')

        with mock.patch.dict(
            os.environ,
            {'GIT_COMMON_DIR': str(decoy / '.git')},
            clear=False,
        ):
            report = audit_git_state(self.root)

        self.assertEqual(
            [(item['branch'], item['upstream']) for item in report['branches']['upstream_protected']],
            [('feature/danger', 'origin/main')],
        )

    def test_ambient_git_index_file_cannot_hide_a_dirty_tracked_file(self) -> None:
        alternate_index = self.base / 'alternate.index'
        shutil.copy2(self.root / '.git' / 'index', alternate_index)
        hostile_env = dict(os.environ)
        hostile_env['GIT_INDEX_FILE'] = str(alternate_index)
        subprocess.run(
            ['git', 'update-index', '--assume-unchanged', 'tracked.txt'],
            cwd=self.root,
            env=hostile_env,
            text=True,
            capture_output=True,
            check=True,
        )
        (self.root / 'tracked.txt').write_text('hidden edit\n', encoding='utf-8')

        with mock.patch.dict(os.environ, {'GIT_INDEX_FILE': str(alternate_index)}, clear=False):
            report = audit_git_state(self.root)

        self.assertEqual(
            report['worktrees']['dirty'],
            [{'path': str(self.root), 'branch': 'main', 'changed_files': 1}],
        )

    def test_a_bound_scan_is_reported_as_incomplete_not_clean(self) -> None:
        self.add_dirty_worktree('wt-one')
        self.add_dirty_worktree('wt-two')
        report = audit_git_state(self.root, worktree_scan_limit=1)
        self.assertTrue(report['worktrees']['truncated'])
        self.assertEqual(report['worktrees']['dirty_state'], 'unknown')
        row = self.rows(report)['git-worktrees'][1]
        self.assertIn('unknown with uncommitted changes', row)
        self.assertNotIn('0 with uncommitted changes', row)
        self.assertTrue(report['worktrees']['incomplete'])
        self.assertLessEqual(report['worktrees']['scanned'], 1)
        # The cause has to name the real reason, not a generic "capped".
        self.assertEqual(
            report['worktrees']['incomplete_causes'],
            ['scan limit of 1 worktrees reached, 2 not scanned'],
        )
        self.assertEqual(report['worktrees']['over_limit'], 2)
        self.assertIn('scan incomplete: scan limit of 1 worktrees reached', format_audit(report))
        self.assertIn(
            'not everything could be read: scan limit of 1 worktrees reached',
            ' '.join(message for _, _, message in doctor_items(report)),
        )

    def test_the_screen_prints_every_detail_line_it_owns(self) -> None:
        # `format_audit` is the operator's only screen. Each line below is a hazard class the audit
        # exists to surface, and a test that only checks the header would not notice a line going
        # missing. The capped cause is checked for its prefix only: the not-scanned count depends
        # on how many worktrees the scaffold registers.
        self.add_protected_upstream()
        self.add_gone_upstream()
        self.add_stash()
        sha = self.add_detached_unpushed_worktree()
        report = audit_git_state(self.root, worktree_scan_limit=0)
        screen = format_audit(report)
        self.assertIn('upstream is a protected base: feature/danger -> origin/main', screen)
        self.assertIn('upstream ref is gone: feature/gone -> origin/feature/gone', screen)
        self.assertIn('tips on no remote: feature/danger', screen)
        self.assertIn('scan incomplete: scan limit of 0 worktrees reached', screen)
        self.assertIn('stash@{0}: on main: rescue before rebase', screen)
        self.assertIn(f'detached tips on no remote: {sha[:12]}', screen)
        self.assertIn('caveat: every pull request in this repository is squash-merged', screen)
        self.assertIn('HUMAN-OWNED next steps', screen)
        self.assertIn('notice:', screen)
        # The skip reason belongs to a check that could not run; this repository has a remote, so
        # printing it here would be as wrong as printing "none" when the check was skipped.
        self.assertNotIn('unpushed-tip check skipped', format_audit(audit_git_state(self.root)))

    def test_an_ssh_remote_with_a_port_still_names_the_repository(self) -> None:
        self.assertEqual(
            _repository_slug('ssh://git@bitbucket.example:7999/owner/repo.git'), 'owner/repo'
        )
        self.assertEqual(
            _repository_slug('git@github.com:Dimkox/adaptive-grok-build-pro.git'),
            'Dimkox/adaptive-grok-build-pro',
        )
        self.assertEqual(
            _repository_slug('https://github.com/Dimkox/adaptive-grok-build-pro.git'),
            'Dimkox/adaptive-grok-build-pro',
        )
        self.assertIsNone(_repository_slug('file:///srv/git/team/repo.git'))
        self.assertIsNone(_repository_slug('/tmp/x/origin.git'))
        # End to end, because the only consumer is a command printed for a human.
        self.add_unpushed_branch()
        _git(self.root, 'remote', 'set-url', 'origin', 'ssh://git@host.example:7999/owner/repo.git')
        report = audit_git_state(self.root)
        self.assertEqual(report['repository']['slug'], 'owner/repo')
        self.assertTrue(
            any('--repo owner/repo ' in command for command in report['human_commands']),
            report['human_commands'],
        )

    def test_clean_repository_reports_no_hazard(self) -> None:
        self.deliver_every_branch()
        report = audit_git_state(self.root)
        branches = report['branches']
        self.assertEqual(branches['upstream_protected'], [])
        self.assertEqual(branches['upstream_gone'], [])
        self.assertEqual(branches['no_upstream'], [])
        self.assertEqual(branches['unpushed_tips'], [])
        self.assertEqual(report['worktrees']['dirty'], [])
        self.assertEqual(report['worktrees']['missing'], [])
        self.assertEqual(report['stashes']['count'], 0)
        self.assertFalse(report['worktrees']['incomplete'])
        self.assertEqual(
            [status for status, _, _ in doctor_items(report)],
            ['pass', 'pass', 'pass', 'pass'],
        )

    def test_audit_never_changes_the_repository(self) -> None:
        self.add_wrong_upstream()
        self.add_gone_upstream()
        self.add_unpushed_branch()
        self.add_dirty_worktree()
        self.add_missing_worktree()
        self.add_stash()
        sha = self.add_detached_unpushed_worktree()
        before = self.snapshot()
        report = audit_git_state(self.root)
        # A pin comparing nothing to nothing passes for an audit that was removed, so first prove
        # this repository really carries the hazards the snapshot would catch a write in.
        self.assertGreater(hazard_count(report), 0)
        self.assertEqual(len(report['branches']['unpushed_detached']), 1)
        self.assertEqual(report['branches']['unpushed_detached'][0]['head'], sha)
        audit_git_state(self.root)
        audit_git_state(self.root)
        self.assertEqual(before, self.snapshot())

    def test_remediation_stays_a_human_command_never_executed(self) -> None:
        self.add_wrong_upstream()
        self.add_unpushed_branch()
        self.add_missing_worktree()
        report = audit_git_state(self.root)
        self.assertTrue(report['read_only'])
        self.assertIn('never runs', report['notice'])
        self.assertGreater(hazard_count(report), 0)
        commands = report['human_commands']
        self.assertTrue(commands)
        self.assertTrue(all(isinstance(command, str) for command in commands))
        # A prune is offered as a dry run only; anything harsher is the wrong fix.
        prunes = [command for command in commands if 'worktree prune' in command]
        self.assertTrue(prunes)
        self.assertTrue(all('-n' in command.split() for command in prunes))
        self.assertTrue(any('git push' in command for command in commands))
        self.assertTrue(any('protected' in command.lower() for command in commands))
        # No recommended command may point a branch at a protected base, and every push names the
        # branch's own ref - the advice screen is not exempt from the hazard it reports.
        for command in commands:
            self.assertNotIn('set-upstream-to=origin/main', command)
            self.assertNotIn('set-upstream-to=origin/master', command)
            if command.startswith('git push'):
                self.assertIn('feature/danger', command)
        self.assertEqual(report['error'], None)

    def test_remediation_quotes_dynamic_shell_arguments(self) -> None:
        branch = "feature/cost$'quote"
        _git(self.root, 'checkout', '-qb', branch)
        (self.root / 'quoted.txt').write_text('work\n', encoding='utf-8')
        _git(self.root, 'add', 'quoted.txt')
        _git(self.root, 'commit', '-qm', 'quoted branch')
        _git(self.root, 'branch', '--set-upstream-to=origin/main', branch)
        _git(self.root, 'checkout', '-q', 'main')
        dirty = self.add_dirty_worktree("wt dirty's path")

        commands = audit_git_state(self.root)['human_commands']
        joined = '\n'.join(commands)

        self.assertIn(f'git branch --unset-upstream {shlex.quote(branch)}', joined)
        self.assertIn(f'git push -u origin {shlex.quote(branch)}', joined)
        self.assertIn(f'git -C {shlex.quote(str(dirty))} status --short', joined)
        self.assertIn(f'--repo {shlex.quote("<owner>/<repo>")}', joined)

        log_command = next(command for command in commands if command.startswith('git log '))
        completed = subprocess.run(
            shlex.split(log_command.split('  #', 1)[0]),
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('quoted branch', completed.stdout)

    def test_remediation_does_not_assume_delivery_when_the_tip_check_skipped(self) -> None:
        # Same rule as the screen, exercised through the printed advice: with the check skipped, no
        # branch may be offered `--set-upstream-to`, because "not listed as unpushed" was not
        # established.
        self.add_unpushed_branch()
        with mock.patch.object(git_audit, 'run', self._failing_git('rev-list --remotes')):
            report = audit_git_state(self.root)
        self.assertEqual(report['branches']['unpushed_state'], 'skipped')
        row = self.rows(report)['git-branches'][1]
        self.assertIn('unknown not reachable from any remote', row)
        self.assertNotIn('0 not reachable from any remote', row)
        commands = report['human_commands']
        self.assertFalse([command for command in commands if '--set-upstream-to=' in command], commands)
        self.assertTrue(any('NOT established' in command for command in commands), commands)

    def test_github_style_remote_supplies_the_repository_slug(self) -> None:
        self.add_unpushed_branch()
        # `origin` here is a local path with no owner/repo form; the hosted mirror must win.
        _git(self.root, 'remote', 'add', 'mirror', 'https://github.com/Dimkox/adaptive-grok-build-pro.git')
        report = audit_git_state(self.root)
        self.assertEqual(report['repository']['slug'], 'Dimkox/adaptive-grok-build-pro')
        self.assertTrue(
            any('--repo Dimkox/adaptive-grok-build-pro' in command for command in report['human_commands'])
        )

    def test_local_path_remote_keeps_the_placeholder(self) -> None:
        self.add_unpushed_branch()
        report = audit_git_state(self.root)
        self.assertIsNone(report['repository']['slug'])
        self.assertTrue(
            any(
                f'--repo {shlex.quote("<owner>/<repo>")}' in command
                for command in report['human_commands']
            )
        )

    def test_doctor_items_surface_hazards_without_failing_the_gate(self) -> None:
        self.add_wrong_upstream()
        self.add_dirty_worktree()
        self.add_stash()
        report = audit_git_state(self.root)
        items = doctor_items(report)
        names = {name for _, name, _ in items}
        self.assertEqual(
            names,
            {'git-worktrees', 'git-branches', 'git-stashes', 'git-audit'},
        )
        self.assertTrue(all(status in {'pass', 'info'} for status, _, _ in items))
        self.assertTrue(any(status == 'info' for status, _, _ in items))
        messages = ' | '.join(message for _, _, message in items)
        self.assertIn('1 protected', messages)
        self.assertIn('uncommitted', messages)
        self.assertIn('--git-audit', messages)

    def test_a_pushed_branch_without_upstream_is_offered_its_own_ref(self) -> None:
        _git(self.root, 'checkout', '-qb', 'feature/untracked-upstream')
        (self.root / 'upstream-less.txt').write_text('delivered, no upstream\n', encoding='utf-8')
        _git(self.root, 'add', 'upstream-less.txt')
        _git(self.root, 'commit', '-qm', 'pushed without -u')
        _git(self.root, 'push', '-q', 'origin', 'feature/untracked-upstream')
        _git(self.root, 'checkout', '-q', 'main')
        report = audit_git_state(self.root)
        self.assertIn('feature/untracked-upstream', report['branches']['no_upstream'])
        self.assertNotIn('feature/untracked-upstream', report['branches']['unpushed_tips'])
        self.assertTrue(
            any(
                command.startswith('git branch --set-upstream-to=origin/feature/untracked-upstream')
                for command in report['human_commands']
            ),
            report['human_commands'],
        )

    def test_upstream_advice_uses_a_proven_specific_remote_ref(self) -> None:
        _git(self.root, 'remote', 'rename', 'origin', 'mirror')
        _git(self.root, 'checkout', '-qb', 'feature/on-mirror')
        (self.root / 'mirror.txt').write_text('delivered\n', encoding='utf-8')
        _git(self.root, 'add', 'mirror.txt')
        _git(self.root, 'commit', '-qm', 'mirror delivery')
        _git(self.root, 'push', '-q', 'mirror', 'feature/on-mirror')
        _git(self.root, 'checkout', '-q', 'main')

        report = audit_git_state(self.root)

        self.assertIn(
            {'branch': 'feature/on-mirror', 'upstream': 'mirror/feature/on-mirror'},
            report['branches']['proven_upstreams'],
        )
        self.assertTrue(
            any(
                command.startswith(
                    'git branch --set-upstream-to=mirror/feature/on-mirror feature/on-mirror'
                )
                for command in report['human_commands']
            ),
            report['human_commands'],
        )
        self.assertFalse(
            [command for command in report['human_commands'] if 'origin/feature/on-mirror' in command]
        )

    def test_reachable_commit_without_matching_remote_ref_gets_no_upstream_advice(self) -> None:
        _git(self.root, 'branch', 'feature/no-such-remote-ref', 'main')

        report = audit_git_state(self.root)

        self.assertIn('feature/no-such-remote-ref', report['branches']['no_upstream'])
        self.assertNotIn(
            'feature/no-such-remote-ref',
            [entry['branch'] for entry in report['branches']['proven_upstreams']],
        )
        self.assertFalse(
            [
                command
                for command in report['human_commands']
                if '--set-upstream-to=' in command and 'feature/no-such-remote-ref' in command
            ],
            report['human_commands'],
        )

    def test_protected_upstream_repair_uses_its_configured_remote(self) -> None:
        self.add_protected_upstream()
        _git(self.root, 'remote', 'rename', 'origin', 'mirror')

        commands = audit_git_state(self.root)['human_commands']

        self.assertTrue(
            any(command.startswith('git push -u mirror feature/danger') for command in commands),
            commands,
        )
        self.assertFalse([command for command in commands if command.startswith('git push -u origin')])

    def test_expired_budget_refuses_config_and_remote_slug_reads(self) -> None:
        real = git_audit.run
        calls: list[str] = []

        def recording_run(args, **kwargs):
            calls.append(' '.join(args))
            return real(args, **kwargs)

        with mock.patch.object(git_audit, 'run', recording_run):
            report = audit_git_state(self.root, budget_seconds=0.0)

        self.assertEqual(calls, [])
        degraded = [item['command'] for item in report['degraded']]
        self.assertEqual(degraded, ['git rev-parse --is-inside-work-tree'])

    def test_every_git_read_disables_optional_locks_and_history_is_command_bounded(self) -> None:
        (self.root / 'second.txt').write_text('second\n', encoding='utf-8')
        _git(self.root, 'add', 'second.txt')
        _git(self.root, 'commit', '-qm', 'second remote commit')
        _git(self.root, 'push', '-q', 'origin', 'main')
        real = git_audit.run
        calls: list[tuple[list[str], dict]] = []

        def recording_run(args, **kwargs):
            calls.append((list(args), dict(kwargs)))
            return real(args, **kwargs)

        with mock.patch.dict(
            os.environ,
            {
                'GIT_CONFIG_COUNT': '1',
                'GIT_CONFIG_KEY_0': 'core.worktree',
                'GIT_CONFIG_VALUE_0': str(self.base / 'hostile-worktree'),
            },
            clear=False,
        ):
            with mock.patch.object(git_audit, 'MAX_HISTORY_COMMITS', 1):
                with mock.patch.object(git_audit, 'run', recording_run):
                    report = audit_git_state(self.root)

        git_calls = [(args, kwargs) for args, kwargs in calls if args and args[0] == 'git']
        self.assertTrue(git_calls)
        self.assertEqual(git_calls[0][0], ['git', 'rev-parse', '--is-inside-work-tree'])
        self.assertLess(git_calls[0][1]['timeout'], git_audit.GIT_TIMEOUT_SECONDS)
        self.assertTrue(
            all(kwargs.get('env', {}).get('GIT_OPTIONAL_LOCKS') == '0' for _, kwargs in git_calls)
        )
        required_scrubs = {
            'GIT_DIR',
            'GIT_WORK_TREE',
            'GIT_COMMON_DIR',
            'GIT_INDEX_FILE',
            'GIT_OBJECT_DIRECTORY',
            'GIT_ALTERNATE_OBJECT_DIRECTORIES',
            'GIT_NAMESPACE',
            'GIT_SHALLOW_FILE',
            'GIT_GRAFT_FILE',
            'GIT_CONFIG_PARAMETERS',
            'GIT_CONFIG_KEY_0',
            'GIT_CONFIG_VALUE_0',
        }
        self.assertTrue(
            all(required_scrubs <= set(kwargs.get('env_remove', ())) for _, kwargs in git_calls),
            git_calls,
        )
        self.assertIn(
            ['git', 'rev-list', '--remotes', '--max-count=2'],
            [args for args, _ in git_calls],
        )
        self.assertEqual(report['branches']['unpushed_state'], 'skipped')
        self.assertIn('bounded limit of 1', report['branches']['unpushed_skip_reason'])
        # History past the cap is a skipped tip check. With nothing else hazardous it must
        # not close as clean: not the all-clear line, not an empty command list read as
        # success, and not a passing git-audit row.
        self.assertEqual(report['branches']['upstream_protected'], [])
        self.assertEqual(report['branches']['upstream_gone'], [])
        self.assertEqual(report['branches']['no_upstream'], [])
        self.assertEqual(report['branches']['unpushed_tips'], [])
        self.assertEqual(report['branches']['unpushed_detached'], [])
        self.assertEqual(report['worktrees']['dirty'], [])
        self.assertEqual(report['worktrees']['missing'], [])
        self.assertFalse(report['worktrees']['incomplete'])
        self.assertEqual(report['stashes']['count'], 0)
        self.assertEqual(report['degraded'], [])
        screen = format_audit(report)
        self.assertNotIn('no delivery hazard found', screen)
        self.assertTrue(report['human_commands'], 'empty human_commands treated as success')
        self.assertTrue(
            any('NOT established' in command for command in report['human_commands']),
            report['human_commands'],
        )
        self.assertGreater(hazard_count(report), 0)
        self.assertNotEqual(self.rows(report)['git-audit'][0], 'pass')

    def test_a_plain_directory_is_reported_as_unavailable_not_invented(self) -> None:
        plain = self.base / 'not-a-repo'
        plain.mkdir()
        report = audit_git_state(plain)
        self.assertTrue(report['git']['unavailable_reason'])
        self.assertEqual(report['error'], 'not a git repository')
        items = doctor_items(report)
        self.assertEqual([status for status, _, _ in items], ['info'])


class DoctorWiringTests(unittest.TestCase):
    def test_run_doctor_includes_the_delivery_audit(self) -> None:
        with project_copy(git=True) as root:
            _identity(root)
            items = run_doctor(root)
            names = {item.name for item in items}
            self.assertIn('git-branches', names)
            self.assertIn('git-worktrees', names)
            # Wiring means the audit's numbers, not just its row names: this copy has one commit on
            # one branch and no remote, so `1 without upstream` and the skipped tip check are what
            # a real audit must print. Rows named `git-*` with all zeros prove nothing was read.
            branch_row = next(item for item in items if item.name == 'git-branches')
            self.assertEqual(branch_row.status, 'info')
            self.assertIn('1 local;', branch_row.message)
            self.assertIn('1 without upstream', branch_row.message)
            self.assertIn('tip check skipped', branch_row.message)
            worktree_row = next(item for item in items if item.name == 'git-worktrees')
            self.assertIn('1 registered', worktree_row.message)

    def test_doctor_never_fails_because_of_the_delivery_audit(self) -> None:
        with project_copy(git=True) as root:
            _identity(root)
            base = _current_branch(root)
            _git(root, 'checkout', '-qb', 'feature/audit-hazard')
            _git(root, 'branch', f'--set-upstream-to={base}', 'feature/audit-hazard')
            items = run_doctor(root)
            audit = [item for item in items if item.name.startswith('git-')]
            self.assertTrue(audit)
            self.assertEqual([item.status for item in audit if item.status == 'fail'], [])
            messages = ' | '.join(item.message for item in audit)
            # The hazard this issue is about, actually reported through the wiring.
            self.assertIn('1 protected-upstream', messages)

    def test_a_broken_audit_degrades_to_a_row_instead_of_aborting_the_screen(self) -> None:
        # `scripts/bootstrap.sh` runs `grok_doctor.py` under `set -euo pipefail`: an advisory
        # exception escaping here would abort contour bootstrap for the whole workspace.
        with project_copy(git=True) as root:
            _identity(root)
            with mock.patch.object(
                doctor, 'audit_git_state', side_effect=RuntimeError('simulated audit crash')
            ):
                items = run_doctor(root)
            audit = [item for item in items if item.name == 'git-audit']
            self.assertEqual(len(audit), 1)
            self.assertEqual(audit[0].status, 'info')
            self.assertIn('audit error', audit[0].message)
            self.assertIn('simulated audit crash', audit[0].message)
            # The crash replaces the audit rows, it does not take the screen with it.
            self.assertNotIn('git-worktrees', {item.name for item in items})
            self.assertIn('repo-detection', {item.name for item in items})


class DoctorCliTests(unittest.TestCase):
    def test_git_audit_flag_prints_one_screen(self) -> None:
        with project_copy(git=True) as root:
            _identity(root)
            base = _current_branch(root)
            (root / 'hazard.txt').write_text('x\n', encoding='utf-8')
            _git(root, 'add', 'hazard.txt')
            _git(root, 'commit', '-qm', 'second')
            _git(root, 'checkout', '-qb', 'feature/cli-hazard')
            _git(root, 'branch', f'--set-upstream-to={base}', 'feature/cli-hazard')
            _git(root, 'checkout', '-q', base)
            dirty = root.parent / 'cli-dirty'
            _git(root, 'worktree', 'add', '-q', '--detach', str(dirty), 'HEAD')
            (dirty / 'hazard.txt').write_text('uncommitted\n', encoding='utf-8')
            proc = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'grok_doctor.py'), '--git-audit'],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('GIT DELIVERY AUDIT', proc.stdout)
            self.assertIn(str(dirty), proc.stdout)
            self.assertIn('HUMAN-OWNED', proc.stdout)
            # The detail lines, not just the headers: each is a hazard class this screen exists to
            # show, and they are what an operator acts on.
            self.assertIn(f'upstream is a protected base: feature/cli-hazard -> {base}', proc.stdout)
            self.assertIn('dirty:', proc.stdout)
            self.assertIn('unpushed-tip check skipped:', proc.stdout)
            self.assertIn('2 local', proc.stdout)
            self.assertIn('delivery is NOT established here', proc.stdout)

    def test_git_audit_json_is_machine_readable(self) -> None:
        with project_copy(git=True) as root:
            _identity(root)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / 'scripts' / 'grok_doctor.py'),
                    '--git-audit-json',
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads(proc.stdout)
            self.assertTrue(report['read_only'])
            self.assertEqual(report['git']['repository'], True)
            self.assertIn('worktrees', report)
            # The machine consumer gets the audit's real numbers and the fields that carry its
            # limits; an all-zero skeleton must not be able to satisfy this test.
            self.assertEqual(report['branches']['local'], 1)
            self.assertEqual(len(report['branches']['no_upstream']), 1)
            self.assertEqual(report['worktrees']['registered'], 1)
            self.assertEqual(report['worktrees']['scanned'], 1)
            self.assertEqual(report['branches']['unpushed_state'], 'skipped')
            self.assertIn('unpushed_detached', report['branches'])
            self.assertIn('incomplete_causes', report['worktrees'])
            self.assertEqual(report['degraded'], [])
            self.assertIn('seconds', report['budget'])


if __name__ == '__main__':
    unittest.main()
