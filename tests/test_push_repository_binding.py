"""Issue #58: a `git push` must be authorized by the grant of the repository it
actually resolves in - not by the grant of whichever repository the harness happened
to recognise as the policy root.

Two independent resolution paths disagree today:

* `.grok/hooks/_lib.py` discovers the command root by walking **up** to the nearest
  `.grok-stack` directory, so a nested clone inside the tree is mistaken for the
  outer project, and the Bash tool's own `directory` parameter is not read at all.
* `git` discovers the repository by walking **up** to the nearest `.git`.

The delegated production grant is bound to `repository` + `git_head` +
`grant_binding_digest` of the policy root, so whenever the two disagree the grant
authorizes a ref write in a repository it was never minted for.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from typing import Iterator
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok import _policy_legacy as legacy  # noqa: E402
from adaptive_grok.policy import evaluate_pre_tool  # noqa: E402
from adaptive_grok.router import build_route  # noqa: E402
from adaptive_grok.state import add_approval, set_active_route  # noqa: E402
from tests._support import project_copy, run_hook  # noqa: E402

REMOTE = 'git@github.com:Dimkox/adaptive-grok-build-pro.git'
FOREIGN_REMOTE = 'git@github.com:example/foreign-repository.git'
LOOTED_REMOTE = 'git@github.com:example/looted.git'
UNRESOLVED = 'cannot be read from the command line'
UNRESOLVED_COMPOSITION = 'composes a push with syntax'


def _git(repository: Path, *args: str) -> None:
    subprocess.run(['git', *args], cwd=repository, check=True, capture_output=True)


def _repository(path: Path, remote: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, 'init', '-q')
    _git(path, 'config', 'user.name', 'Test')
    _git(path, 'config', 'user.email', 'test@example.com')
    _git(path, 'commit', '-q', '--allow-empty', '-m', 'seed')
    _git(path, 'remote', 'add', 'origin', remote)
    return path


@contextlib.contextmanager
def delegating_project() -> Iterator[tuple[Path, Path, Path]]:
    """A bound repository holding a live `git-push-branch` grant.

    Yields ``(root, nested, foreign)``: ``nested`` is a *different* repository inside
    the tree, ``foreign`` is a different repository outside it. The grant is minted
    last because the binding digest covers untracked paths.
    """
    with project_copy(git=True) as root:
        _git(root, 'remote', 'add', 'origin', REMOTE.replace('git@github.com/', 'git@github.com:'))
        nested = _repository(root / 'vendor' / 'embedded-service', FOREIGN_REMOTE)
        foreign = _repository(root.parent / 'foreign-checkout', FOREIGN_REMOTE)
        del nested  # bound name keeps the directory alive for readers of the tuple
        set_active_route(root, build_route(root, 'Исправить PHP баг', 'push-binding').to_dict())
        add_approval(root, 'production', 'delegated publication', 5, actions=['git-push-branch'])
        yield root, root / 'vendor' / 'embedded-service', foreign


def bash(command: str, directory: str | None = None) -> dict:
    tool_input: dict = {'command': command}
    if directory is not None:
        tool_input['directory'] = directory
    return {'tool_name': 'Bash', 'tool_input': tool_input}


class PushRepositoryBindingTest(unittest.TestCase):
    def test_grant_actually_covers_a_plain_session_root_push(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(root, bash('git push origin feature'))
            self.assertTrue(allowed, reason)

    def test_cd_into_nested_repository_cannot_borrow_the_outer_grant(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            command = f'cd {nested.relative_to(root)} && git push origin HEAD:refs/heads/x'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, command)
            self.assertIn(str(nested), reason or '')

    def test_absolute_cd_into_nested_repository_cannot_borrow_the_outer_grant(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            allowed, reason = evaluate_pre_tool(root, bash(f'cd {nested} && git push origin feature'))
            self.assertFalse(allowed, reason)

    def test_dash_c_into_nested_repository_cannot_borrow_the_outer_grant(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            allowed, reason = evaluate_pre_tool(root, bash(f'git -C {nested} push origin feature'))
            self.assertFalse(allowed, reason)

    def test_relative_dash_c_into_nested_repository_cannot_borrow_the_outer_grant(self) -> None:
        # The absolute `-C` case does not lock this spelling. Applying `-C` only when the operand
        # is absolute still denies that test and lets a relative operand push the nested repository.
        with delegating_project() as (root, nested, _foreign):
            relative = nested.relative_to(root)
            command = f'git -C {relative} push origin feature'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)
            self.assertIn(str(nested), reason or '')

    def test_git_dir_override_into_nested_repository_cannot_borrow_the_outer_grant(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            allowed, reason = evaluate_pre_tool(
                root, bash(f'git --git-dir={nested}/.git push origin feature')
            )
            self.assertFalse(allowed, reason)

    def test_bash_directory_parameter_cannot_borrow_the_session_grant(self) -> None:
        with delegating_project() as (root, _nested, foreign):
            allowed, reason = evaluate_pre_tool(
                root, bash('git push origin feature', directory=str(foreign))
            )
            self.assertFalse(allowed, reason)

    def test_bash_directory_parameter_pointing_at_a_nested_repository_is_denied(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            allowed, reason = evaluate_pre_tool(
                root, bash('git push origin feature', directory=str(nested))
            )
            self.assertFalse(allowed, reason)

    def test_dynamic_cd_target_before_a_push_fails_closed(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(
                root, bash('cd "$CHECKOUT" && git push origin feature')
            )
            self.assertFalse(allowed, reason)

    def test_literal_shell_payload_with_cd_and_push_is_bound_to_a_repository(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            command = f'bash -lc "cd {nested} && git push origin feature"'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)

    def test_cd_into_a_plain_subdirectory_stays_in_the_bound_repository(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(root, bash('cd vendor && git push origin feature'))
            self.assertTrue(allowed, reason)

    def test_dry_run_push_is_not_blocked_by_the_binding_guard(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            command = f'cd {nested} && git push --dry-run origin HEAD:refs/heads/x'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertTrue(allowed, reason)

    def test_non_push_commands_in_a_nested_repository_are_unaffected(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            for command in (
                f'cd {nested} && git status --short',
                f'cd {nested} && git log --oneline -1',
                f'cd {nested} && ls',
            ):
                allowed, reason = evaluate_pre_tool(root, bash(command))
                self.assertTrue(allowed, f'{command}: {reason}')

    def test_command_that_only_mentions_a_push_is_not_blocked(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(
                root, bash('echo "git push origin main" && cd "$CHECKOUT"')
            )
            self.assertTrue(allowed, reason)

    def test_dry_run_push_with_an_unresolved_cd_is_allowed(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(
                root, bash('cd "$CHECKOUT" && git push --dry-run origin HEAD:refs/heads/x')
            )
            self.assertTrue(allowed, reason)

    def test_unreadable_composition_is_refused_even_with_only_a_dry_run_push(self) -> None:
        # The dry-run exemption is for a line the walk can read. A group it cannot classify at
        # all may be running a write next to the dry run, so the flag does not save it.
        with delegating_project() as (root, nested, _foreign):
            command = f'(cd {nested} && git push --dry-run origin HEAD:refs/heads/x)'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)
            self.assertIn(UNRESOLVED_COMPOSITION, reason or '')

    def test_unparseable_line_that_names_a_push_fails_closed(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(root, bash('git push origin "feature'))
            self.assertFalse(allowed, reason)

    def test_incident_shape_is_denied_for_the_wrong_repository_not_the_flag(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            command = (
                f'cd {nested} && git push --force-with-lease origin HEAD:refs/heads/perf/x 2>&1 | tail -1 '
                f'|| git push origin {nested}:refs/heads/perf/x'
            )
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, command)
            self.assertIn(str(nested), reason or '')

    def test_relative_git_dir_override_into_a_nested_repository_is_denied(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(
                root, bash('env GIT_DIR=vendor/embedded-service/.git git push origin feature')
            )
            self.assertFalse(allowed, reason)

    def test_working_tree_override_pointing_at_a_nested_repository_is_denied(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            allowed, reason = evaluate_pre_tool(
                root, bash(f'git --work-tree={nested} --git-dir={nested}/.git push origin feature')
            )
            self.assertFalse(allowed, reason)

    # --- the fail-closed arms that a green suite used to hide ------------------------------
    # Reviewer mutants M9 and M7b survived the original 20 cases: the per-push `unresolved`
    # branch could be deleted, and `.grok/hooks/_lib.py` could keep ignoring `directory`, with
    # every test still passing. Each arm below is a case that fails when its branch goes away.

    def test_push_with_an_unresolved_dash_c_target_fails_closed(self) -> None:
        # `_policy_legacy.py` refuses a push whose own -C value it cannot read. Deleting that
        # branch turns this exact command from deny into allow while every other case holds.
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(root, bash('git -C "$CHECKOUT" push origin feature'))
            self.assertFalse(allowed, reason)
            self.assertIn(UNRESOLVED, reason or '')
            self.assertIn('push <remote> <commit-ish>:<ref>', reason or '')

    def test_unresolved_git_dir_and_work_tree_operands_fail_closed(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            for command in (
                'git --git-dir="$GITDIR" push origin feature',
                'git --work-tree="$TREE" push origin feature',
                'env GIT_DIR=$GITDIR git push origin feature',
            ):
                allowed, reason = evaluate_pre_tool(root, bash(command))
                self.assertFalse(allowed, f'{command}: {reason}')
                self.assertIn(UNRESOLVED, reason or '', command)

    def test_tilde_operand_is_refused_instead_of_raising(self) -> None:
        # `str.expanduser()` does not exist: before the fix these lines raised AttributeError out
        # of evaluate_pre_tool, and the hook's own exception path decides the verdict, not policy.
        with delegating_project() as (root, _nested, _foreign):
            for command in (
                'cd ~/definitely-not-this-repository && git push origin feature',
                'git -C ~/definitely-not-this-repository push origin feature',
                'git --git-dir=~/definitely-not-this-repository/.git push origin feature',
                'GIT_DIR=~/definitely-not-this-repository/.git git push origin feature',
            ):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertFalse(allowed, f'{command}: {reason}')

    # --- push shapes a reviewer constructed against the unmutated guard --------------------
    # Every one of these returned ALLOW at the delivered head, in a scratch tree where the push
    # resolved in a foreign or nested repository.

    def test_unquoted_command_substitution_after_dash_c_fails_closed(self) -> None:
        # `$(echo /a /b)` splits into two words, so the parser used to collect no push at all
        # while git pushed in the repository the substitution named.
        with delegating_project() as (root, _nested, foreign):
            command = f'git -C $(echo {foreign}) push origin feature'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)
            self.assertIn(UNRESOLVED, reason or '')

    def test_subshell_cannot_hide_a_push_from_the_binding_guard(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            command = f'(cd {nested} && git push origin feature)'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)

    def test_brace_group_cannot_hide_a_push_from_the_binding_guard(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            command = f'{{ cd {nested}; git push origin feature; }}'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)

    def test_line_break_before_a_push_keeps_its_cd_in_force(self) -> None:
        # A newline used to be rewritten to `&&` with no spaces, fusing two groups and deleting
        # the `cd` between them, so this multiline form pushed from the nested repository.
        with delegating_project() as (root, nested, _foreign):
            command = f'cd {nested}\ngit push origin feature'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)
            self.assertIn(str(nested), reason or '')

    def test_zero_whitespace_control_operator_keeps_the_cd_in_force(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            for command in (
                f'cd {nested}&&git push origin feature',
                f'pushd {nested}&&git push origin feature',
                f'GIT_DIR={nested}/.git&&git push origin feature',
            ):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertFalse(allowed, f'{command}: {reason}')
                    self.assertIn(str(nested), reason or '')

    def test_nested_shell_payload_is_followed_into_the_repository(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            command = f'bash -lc "bash -lc \'cd {nested} && git push origin feature\'"'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)
            self.assertIn(str(nested), reason or '')

    def test_shell_nesting_beyond_the_followed_depth_fails_closed(self) -> None:
        # The walk follows `_PUSH_SHELL_DEPTH` payload levels and refuses to assume past them.
        # Nothing inside was collected as a write, so this is the arm that has to decide.
        with delegating_project() as (root, _nested, _foreign):
            payload = 'cd /nonexistent-anyway && git push origin feature'
            for _ in range(legacy._PUSH_SHELL_DEPTH + 1):
                payload = f'bash -lc {json.dumps(payload)}'
            allowed, reason = evaluate_pre_tool(root, bash(payload))
            self.assertFalse(allowed, reason)
            self.assertIn(UNRESOLVED_COMPOSITION, reason or '')

    def test_env_option_cannot_swallow_the_git_executable(self) -> None:
        # The wrapper loop consumed `-u` but not its operand, so `LC_ALL` stood where `git`
        # belongs and the push was never attributed to any directory.
        with delegating_project() as (root, nested, _foreign):
            command = f'env -u LC_ALL git -C {nested} push origin feature'
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)
            self.assertIn(str(nested), reason or '')

    def test_env_chdir_into_a_nested_repository_cannot_borrow_the_grant(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            for command in (f'env -C {nested} git push origin feature',
                            f'env --chdir={nested} git push origin feature'):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertFalse(allowed, f'{command}: {reason}')
                    self.assertIn(str(nested), reason or '')

    def test_xargs_dispatched_push_cannot_hide_its_repository(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            command = f"printf 'origin\\n' | xargs -I{{}} git -C {nested} push {{}} feature"
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertFalse(allowed, reason)

    def test_exported_git_dir_cannot_borrow_the_grant(self) -> None:
        # The push runs in the granted directory, so every directory test passes, while git
        # writes the ref into another repository because the shell exported GIT_DIR first.
        with delegating_project() as (root, nested, foreign):
            for target in (foreign, nested):
                command = f'export GIT_DIR={target}/.git && git push origin feature'
                allowed, reason = evaluate_pre_tool(root, bash(command))
                self.assertFalse(allowed, f'{command}: {reason}')
                self.assertIn(str(target), reason or '')

    def test_unset_git_dir_returns_the_push_to_the_bound_repository(self) -> None:
        # The environment walk has to model shell state, not refuse anything that mentions it.
        with delegating_project() as (root, _nested, foreign):
            command = (
                f'export GIT_DIR={foreign}/.git && unset GIT_DIR && git push origin feature'
            )
            allowed, reason = evaluate_pre_tool(root, bash(command))
            self.assertTrue(allowed, reason)

    def test_inherited_git_dir_outside_the_repository_is_denied(self) -> None:
        # Driven at the guard predicate on purpose: GIT_DIR is process state, and patching it
        # around `evaluate_pre_tool` would also move the grant's own tree fingerprint.
        with delegating_project() as (root, _nested, foreign):
            with mock.patch.dict(os.environ, {'GIT_DIR': str(foreign / '.git')}):
                reason = legacy.push_repository_mismatch(root, 'git push origin feature', {})
            self.assertIsNotNone(reason)
            self.assertIn(str(foreign), reason or '')

    def test_inherited_git_dir_inside_the_repository_stays_allowed(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            with mock.patch.dict(os.environ, {'GIT_DIR': str(root / '.git')}):
                reason = legacy.push_repository_mismatch(root, 'git push origin feature', {})
            self.assertIsNone(reason)

    # --- the destination the push writes to ------------------------------------------------
    # Binding the local repository is only half the question: the grant covers ref writes in the
    # repository it names, and `git push <url> <ref>` spends it on some other repository.

    def test_push_to_a_destination_that_is_not_a_remote_of_the_grant_is_denied(self) -> None:
        with delegating_project() as (root, _nested, foreign):
            for destination in (
                LOOTED_REMOTE,
                'https://github.com/example/looted.git',
                str(foreign),
                'unconfigured-remote',
                # A single operand is a destination to git, not a refspec shortcut: measured,
                # `git push HEAD:refs/heads/x` tries to resolve the host "HEAD".
                'HEAD:refs/heads/x',
            ):
                command = f'git push {destination} main'
                allowed, reason = evaluate_pre_tool(root, bash(command))
                self.assertFalse(allowed, f'{command}: {reason}')
                self.assertIn('destination', reason or '')
                self.assertIn(str(root), reason or '')

    def test_every_refusal_states_the_single_pinned_form(self) -> None:
        # AC-005 across all four refusal arms, not just the one that first shipped with it.
        guidance = 'git -C '
        with delegating_project() as (root, nested, foreign):
            for command in (
                f'cd {nested} && git push origin feature',                    # wrong repository
                'git -C "$CHECKOUT" push origin feature',                      # unreadable operand
                'cd "$CHECKOUT" && git push "$BRANCH"',                        # unresolvable line
                f'git push {LOOTED_REMOTE} main',                              # foreign destination
                f'(cd {nested} && git push origin feature)',                   # obstructed group
            ):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertFalse(allowed, f'{command}: {reason}')
                    self.assertIn(guidance, reason or '')
                    self.assertIn(str(root), reason or '')

    def test_push_to_a_remote_the_bound_repository_configures_is_allowed(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            for command in (
                'git push origin feature',
                f'git push {REMOTE} feature',
                f'git push {root} feature',
                'git push -u origin feature',
            ):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertTrue(allowed, f'{command}: {reason}')

    def test_push_destination_options_cannot_hide_a_foreign_destination(self) -> None:
        with delegating_project() as (root, _nested, foreign):
            for command in (
                f'git push --repo={foreign}',
                f'git push --repo {foreign}',
                f'git push --receive-pack=git-receive-pack {foreign} feature',
                f'git push --push-option=ci.skip {foreign} feature',
            ):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertFalse(allowed, f'{command}: {reason}')
                    self.assertIn('destination', reason or '')

    def test_inline_push_value_options_keep_a_configured_remote_allowed(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            for command in (
                'git push --repo=origin feature',
                'git push --repo origin feature',
                'git push --receive-pack=git-receive-pack origin feature',
                'git push --push-option=ci.skip origin feature',
                'git push --receive-pack git-receive-pack origin feature',
                'git push --push-option ci.skip origin feature',
                'git -c protocol.version=2 push origin feature',
            ):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertTrue(allowed, f'{command}: {reason}')

    def test_command_scoped_git_configuration_cannot_redirect_origin(self) -> None:
        with delegating_project() as (root, _nested, foreign):
            commands = (
                'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.url '
                f'GIT_CONFIG_VALUE_0={foreign} git push origin feature',
                f'git -c remote.origin.url={foreign} push origin feature',
                f'git -c remote.origin.pushurl={foreign} push origin feature',
                f'git -c url.{foreign}.insteadOf=origin push origin feature',
                f'REDIRECT={foreign} git --config-env=remote.origin.url=REDIRECT '
                'push origin feature',
                'export GIT_CONFIG_COUNT=1 && git push origin feature',
            )
            for command in commands:
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertFalse(allowed, f'{command}: {reason}')

    def test_inherited_git_configuration_environment_is_not_trusted(self) -> None:
        with delegating_project() as (root, _nested, foreign):
            redirected = {
                'GIT_CONFIG_COUNT': '1',
                'GIT_CONFIG_KEY_0': 'remote.origin.url',
                'GIT_CONFIG_VALUE_0': str(foreign),
            }
            with mock.patch.dict(os.environ, redirected):
                reason = legacy.push_repository_mismatch(root, 'git push origin feature', {})
            self.assertIsNotNone(reason)

    def test_split_global_value_options_cannot_hide_the_repository_or_the_push(self) -> None:
        # Git 2.43 takes the next word as the value of `--namespace` and `--attr-source`. A scan
        # that treats each dashed token as one flag stops on that word, so a later `-C` is ignored.
        with delegating_project() as (root, _nested, foreign):
            for command in (
                f'git --namespace foo -C {foreign} push origin feature',
                f'git --attr-source HEAD -C {foreign} push --force origin feature',
            ):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertFalse(allowed, f'{command}: {reason}')
                    self.assertIn(str(foreign), reason or '')

    def test_namespace_force_push_is_classified_as_git_push_branch(self) -> None:
        # No grant is consulted: `git --namespace foo push --force` never reached the push word,
        # so it was not a production action and the destructive form needed no grant at all.
        self.assertEqual(
            legacy.production_action('git --namespace foo push --force'),
            'git-push-branch',
        )
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(
                root, bash('git --namespace foo push --force origin feature'),
            )
            self.assertFalse(allowed, reason)
            self.assertIn('destructive', reason or '')

    def test_configured_pushurl_is_not_the_accepted_remote_url(self) -> None:
        # `remote.origin.url` is the accepted destination. `pushurl` is what git actually pushes
        # to when it is set, and accepting the remote name ignores that override.
        with delegating_project() as (root, _nested, _foreign):
            _git(root, 'config', 'remote.origin.pushurl', LOOTED_REMOTE)
            allowed, reason = evaluate_pre_tool(root, bash('git push origin feature'))
            self.assertFalse(allowed, reason)
            self.assertIn('destination', reason or '')
            self.assertIn('pushurl', reason or '')

    def test_destructive_push_forms_are_denied_after_git_global_options(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            for command in (
                f'git -C {root} push --force origin feature',
                f'git -C {root} push --force-with-lease origin feature',
                f'git -C {root} push --force-with-lease=feature:deadbeef origin feature',
                f'git -C {root} push -f origin feature',
                f'git -C {root} push origin +feature:refs/heads/feature',
                f'git -C {root} push --mirror origin',
                f'git -C {root} push --delete origin feature',
                f'git -C {root} push -d origin feature',
                f'git -C {root} push --prune origin',
            ):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(root, bash(command))
                    self.assertFalse(allowed, f'{command}: {reason}')
                    self.assertIn('destructive', reason or '')

    def test_repository_config_read_is_bounded_and_rejects_symlinks(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            config = root / '.git' / 'config'
            original = config.read_bytes()
            config.write_bytes(original + b'\n#' + b'x' * 300_000)
            start = time.perf_counter()
            allowed, reason = evaluate_pre_tool(root, bash('git push origin feature'))
            self.assertFalse(allowed, reason)
            self.assertLess(time.perf_counter() - start, 2.0)

        if hasattr(os, 'mkfifo'):
            with delegating_project() as (root, _nested, _foreign):
                config = root / '.git' / 'config'
                config.unlink()
                os.mkfifo(config)
                start = time.perf_counter()
                allowed, reason = evaluate_pre_tool(root, bash('git push origin feature'))
                self.assertFalse(allowed, reason)
                self.assertLess(time.perf_counter() - start, 2.0)

        with delegating_project() as (root, _nested, _foreign):
            config = root / '.git' / 'config'
            target = root.parent / 'redirected-git-config'
            target.write_bytes(config.read_bytes())
            config.unlink()
            try:
                config.symlink_to(target)
            except OSError as exc:  # pragma: no cover - host without symlink support
                self.skipTest(f'symlinks unavailable: {exc}')
            allowed, reason = evaluate_pre_tool(root, bash('git push origin feature'))
            self.assertFalse(allowed, reason)

    # --- the guard must stay cheap and stay out of the way ---------------------------------

    def test_oversized_line_that_names_a_push_fails_closed_quickly(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            command = 'git push origin ' + 'x' * (legacy._PUSH_SCAN_LIMIT * 2)
            start = time.perf_counter()
            allowed, reason = evaluate_pre_tool(root, bash(command))
            elapsed = time.perf_counter() - start
            self.assertFalse(allowed, reason)
            self.assertLess(elapsed, 2.0, f'{elapsed:.3f}s to decide one Bash command')

    def test_symlinked_root_spelling_still_resolves_to_the_bound_repository(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            link = root.parent / 'linked-to-bound'
            try:
                link.symlink_to(root, target_is_directory=True)
            except OSError as exc:  # pragma: no cover - host without symlink support
                self.skipTest(f'symlinks unavailable: {exc}')
            for command in ('git push origin feature', 'cd vendor && git push origin feature'):
                with self.subTest(command=command):
                    allowed, reason = evaluate_pre_tool(link, bash(command))
                    self.assertTrue(allowed, f'{command}: {reason}')

    def test_declared_directory_conflicting_only_by_spelling_is_not_an_ambiguity(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            allowed, reason = evaluate_pre_tool(
                root,
                {
                    'tool_name': 'Bash',
                    'tool_input': {
                        'command': 'git push origin feature',
                        'directory': str(root),
                        'workdir': str(root) + '/',
                    },
                },
            )
            self.assertTrue(allowed, reason)

    def test_guard_reads_one_command_root_alias_list_for_both_surfaces(self) -> None:
        # The guard used to keep its own copy of the aliases and the hook kept another, so a
        # parameter added on one surface stayed invisible on the other.
        sys.path.insert(0, str(ROOT / '.grok' / 'hooks'))
        try:
            import _lib as hook_lib  # noqa: PLC0415
        finally:
            sys.path.remove(str(ROOT / '.grok' / 'hooks'))
        self.assertIs(hook_lib._COMMAND_ROOT_ALIASES, legacy.COMMAND_ROOT_ALIASES)
        self.assertIn('directory', legacy.COMMAND_ROOT_ALIASES)


class PushRepositoryBindingHookTest(unittest.TestCase):
    @staticmethod
    def _decision(data: dict) -> object:
        return (data.get('hookSpecificOutput') or {}).get('permissionDecision', data.get('decision'))

    def test_hook_denies_zero_one_and_two_space_control_operators(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            for spacing in ('', ' ', '  '):
                command = f'cd {nested}{spacing}&&{spacing}git push origin feature'
                with self.subTest(spacing=len(spacing)):
                    _, data, stderr = run_hook(root, 'pre_tool_use.py', {
                        'cwd': str(root),
                        'session_id': f'push-spacing-{len(spacing)}',
                        'tool_name': 'Bash',
                        'tool_input': {'command': command},
                    })
                    self.assertEqual(self._decision(data), 'deny', f'{data} {stderr[-400:]}')

    def test_hook_denies_destination_config_and_destructive_escapes(self) -> None:
        with delegating_project() as (root, _nested, foreign):
            commands = (
                f'git push --repo={foreign}',
                f'git push --receive-pack=git-receive-pack {foreign} feature',
                'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.url '
                f'GIT_CONFIG_VALUE_0={foreign} git push origin feature',
                f'git -C {root} push --force-with-lease origin feature',
                f'git -C {root} push origin +feature:refs/heads/feature',
            )
            for index, command in enumerate(commands):
                with self.subTest(command=command):
                    _, data, stderr = run_hook(root, 'pre_tool_use.py', {
                        'cwd': str(root),
                        'session_id': f'push-escape-{index}',
                        'tool_name': 'Bash',
                        'tool_input': {'command': command},
                    })
                    self.assertEqual(self._decision(data), 'deny', f'{data} {stderr[-400:]}')

    def test_hook_allows_supported_push_options_for_a_configured_remote(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            for index, command in enumerate((
                'git push --repo=origin feature',
                'git push --receive-pack=git-receive-pack origin feature',
                'git push --push-option=ci.skip origin feature',
            )):
                with self.subTest(command=command):
                    _, data, stderr = run_hook(root, 'pre_tool_use.py', {
                        'cwd': str(root),
                        'session_id': f'push-option-control-{index}',
                        'tool_name': 'Bash',
                        'tool_input': {'command': command},
                    })
                    self.assertEqual(self._decision(data), 'allow', f'{data} {stderr[-400:]}')

    def test_hook_denies_a_push_whose_directory_is_a_foreign_repository(self) -> None:
        with delegating_project() as (root, _nested, foreign):
            _, data, stderr = run_hook(root, 'pre_tool_use.py', {
                'cwd': str(root),
                'session_id': 'push-directory',
                'tool_name': 'Bash',
                'tool_input': {
                    'command': 'git push origin feature',
                    'directory': str(foreign),
                },
            })
            self.assertEqual(self._decision(data), 'deny', f'{data} {stderr[-400:]}')

    def test_hook_still_allows_a_push_declared_at_the_session_root(self) -> None:
        with delegating_project() as (root, _nested, _foreign):
            _, data, stderr = run_hook(root, 'pre_tool_use.py', {
                'cwd': str(root),
                'session_id': 'push-session-root',
                'tool_name': 'Bash',
                'tool_input': {
                    'command': 'git push origin feature',
                    'directory': str(root),
                },
            })
            self.assertEqual(self._decision(data), 'allow', f'{data} {stderr[-400:]}')


class CommandRootAliasHookTest(unittest.TestCase):
    """The `directory` alias has to re-root every cwd-resolving action, not only pushes.

    `gh pr merge` picks the repository it merges from the working directory, so while the hook
    listed only `workdir`/`cwd`/`working_directory`/`workingDirectory`, a Bash tool call that
    declared `directory` kept consuming the *session* repository's delegated grant. The push
    guard could not have caught this: it is a push-only guard.
    """

    def _grant(self, root: Path, action: str) -> None:
        subprocess.run(
            ['git', 'remote', 'add', 'origin', REMOTE],
            cwd=root, check=True, capture_output=True,
        )
        set_active_route(root, build_route(root, 'Review exact local operation', 'alias-hook').to_dict())
        add_approval(
            root, 'production', 'root authority regression fixture', 5,
            actions=[action], source='explicit-user-consent',
        )

    @staticmethod
    def _decision(data: dict) -> object:
        return (data.get('hookSpecificOutput') or {}).get('permissionDecision', data.get('decision'))

    def test_directory_cannot_borrow_a_pull_request_merge_grant(self) -> None:
        with project_copy(git=True) as session_root, project_copy(git=True) as command_root:
            self._grant(session_root, 'pull-request-merge')
            _, data, stderr = run_hook(session_root, 'pre_tool_use.py', {
                'cwd': str(session_root),
                'session_id': 'directory-merge',
                'tool_name': 'Bash',
                'tool_input': {'command': 'gh pr merge 7 --squash', 'directory': str(command_root)},
            })
            self.assertEqual(self._decision(data), 'deny', f'{data} {stderr[-400:]}')
            self.assertIn('root', str(data.get('reason', data)).lower())

    def test_directory_inside_the_session_repository_still_lets_the_merge_through(self) -> None:
        with project_copy(git=True) as session_root:
            self._grant(session_root, 'pull-request-merge')
            subdir = session_root / 'src'
            subdir.mkdir()
            _, data, stderr = run_hook(session_root, 'pre_tool_use.py', {
                'cwd': str(session_root),
                'session_id': 'directory-merge-local',
                'tool_name': 'Bash',
                'tool_input': {'command': 'gh pr merge 7 --squash', 'directory': str(subdir)},
            })
            self.assertEqual(self._decision(data), 'allow', f'{data} {stderr[-400:]}')


if __name__ == '__main__':
    unittest.main()
