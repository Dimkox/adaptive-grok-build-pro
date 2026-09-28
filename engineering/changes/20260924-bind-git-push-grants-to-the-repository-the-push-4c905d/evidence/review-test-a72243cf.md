# Test review — issue #58 push-grant repository binding

Reviewer role: test_reviewer (read-only except this report).
Candidate: `/home/pall/grok-projects/adaptive-grok-build-pol58`
Branch observed: `fix/issue-58-installed-policy-cli`
HEAD observed: `a72243cf78cd0b49a8105164a0d287cb2940ff4f` (`fix(#58): close push parser review escapes`)
Question: do the tests lock a delegated `git-push-branch` grant to the repository the push actually resolves in?

reviewed-tree-modified: no

Tracked product sources were not edited. The one successful `git status --porcelain=v1` before this report showed only the pre-existing untracked file `engineering/changes/20260924-bind-git-push-grants-to-the-repository-the-push-4c905d/evidence/next-gap.md`, and `git diff --stat HEAD` was empty. A later fingerprint could not be recomputed: after that status command, an unrelated shell invocation was denied (`ambiguous-command-root`), and the following shell invocations were circuit-broken. This report is the only tracked review artifact added.

## Probe execution

Mutation probes were not executed. A private runner was staged at gitignored `build/issue58-review-runner.py` (ignored by the `build/` rule) and was not copied out or deleted, because shell writes and `python3` were refused by the circuit breaker. No scratch directory was created, no mutant was applied, and `tests.test_push_repository_binding` was not run in this review. Kill/survive counts below are from reading the suite against the guard, not from an observed unittest process. Unexecuted dynamic claims are marked as such.

Source inspected:

- `tests/test_push_repository_binding.py` (56 test methods: 49 in `PushRepositoryBindingTest`, 5 in `PushRepositoryBindingHookTest`, 2 in `CommandRootAliasHookTest`)
- `.grok-stack/adaptive_grok/_policy_legacy.py` `push_repository_mismatch` and the `evaluate_pre_tool` call at line 1483
- `.grok/hooks/_lib.py` `_COMMAND_ROOT_ALIASES = COMMAND_ROOT_ALIASES`
- `engineering/changes/20260924-bind-git-push-grants-to-the-repository-the-push-4c905d/evidence/issue-58-reproduction.md`

## What the suite does assert

These claims have a direct assertion in the module. They were not re-run here.

| Claim | Locking test | Assertion |
| --- | --- | --- |
| Relative `cd` into a nested repository cannot borrow the outer grant | `test_cd_into_nested_repository_cannot_borrow_the_outer_grant` | deny, and the reason contains the nested path. Command uses `nested.relative_to(root)`. |
| Absolute `cd`, absolute `git -C`, absolute `--git-dir=` | `test_absolute_cd_into_nested_repository_cannot_borrow_the_outer_grant`, `test_dash_c_into_nested_repository_cannot_borrow_the_outer_grant`, `test_git_dir_override_into_nested_repository_cannot_borrow_the_outer_grant` | deny. The `-C` and `--git-dir=` commands interpolate the absolute `nested` path. |
| Relative `GIT_DIR=` via `env` | `test_relative_git_dir_override_into_a_nested_repository_is_denied` | deny for `env GIT_DIR=vendor/embedded-service/.git`. |
| Tool `directory` absolute, policy and installed hook | `test_bash_directory_parameter_cannot_borrow_the_session_grant`, `test_bash_directory_parameter_pointing_at_a_nested_repository_is_denied`, `test_hook_denies_a_push_whose_directory_is_a_foreign_repository` | deny. Hook control `test_hook_still_allows_a_push_declared_at_the_session_root` allows the same command at the session root. |
| Shared alias list contains `directory` | `test_guard_reads_one_command_root_alias_list_for_both_surfaces` | `assertIs` on the hook and policy tuples, and `'directory'` is a member. |
| Non-push `gh pr merge` cannot borrow via `directory` | `CommandRootAliasHookTest` | forked hook deny outside the session repo, allow for a subdirectory inside it. |
| Fail-closed when the push repository cannot be read | unresolved `-C` / `--git-dir` / `GIT_DIR`, dynamic `cd`, unquoted `$(...)`, subshell, brace group, newline, depth, `env -u`, `env -C`, `xargs`, oversized line | deny, several with `cannot be read from the command line` or `composes a push with syntax`. |
| Zero-whitespace `&&` keeps `cd` / `pushd` / `GIT_DIR=` | `test_zero_whitespace_control_operator_keeps_the_cd_in_force` and `test_hook_denies_zero_one_and_two_space_control_operators` | deny, and the in-process reason names the nested repository. |
| Destination must be a remote of the bound repository | `test_push_to_a_destination_that_is_not_a_remote_of_the_grant_is_denied`, `test_push_destination_options_cannot_hide_a_foreign_destination`, configured-remote allow tests, hook escape/allow pair | deny names `destination`; inline `--repo=` / `--receive-pack=` / `--push-option=` of `origin` stay allowed. |
| Command and inherited `GIT_CONFIG_*`, `-c`, `--config-env` | `test_command_scoped_git_configuration_cannot_redirect_origin`, `test_inherited_git_configuration_environment_is_not_trusted` | deny. The inherited case calls `push_repository_mismatch` directly. |
| Destructive forms after `git -C <bound>` | `test_destructive_push_forms_are_denied_after_git_global_options` and the hook escape case | deny and the reason contains `destructive`. The legacy `DESTRUCTIVE_COMMANDS` regex is `git\s+push`, so it does not cover `git -C … push --force`; these tests are what lock the new parser. |
| Config read bound | `test_repository_config_read_is_bounded_and_rejects_symlinks` | oversized config, fifo, and a symlinked config deny within 2 seconds. |
| Allow controls | plain session-root push, `cd vendor`, dry-run, mention-only text, configured remote, symlink root, same directory spelled twice, `unset GIT_DIR` | allow. |

Disabling the guard (`return None`) or removing the `evaluate_pre_tool` call would contradict the deny assertions above. That kill was not re-measured in this review; the assertions are present and specific.

## Finding: relative `git -C` is a documented escape and is not locked

`evidence/issue-58-reproduction.md` records the nested-repository probe, including this shape, as allow before the guard and deny after it:

```text
nested repo via -C relative      $ git -C nested push origin HEAD:refs/heads/x    -> allow
nested repo via -C relative      -> deny  (same shape)
```

The automated `-C` test does not use that shape. It passes the absolute temporary path:

```103:106:tests/test_push_repository_binding.py
    def test_dash_c_into_nested_repository_cannot_borrow_the_outer_grant(self) -> None:
        with delegating_project() as (root, nested, _foreign):
            allowed, reason = evaluate_pre_tool(root, bash(f'git -C {nested} push origin feature'))
            self.assertFalse(allowed, reason)
```

`nested` is `root / 'vendor' / 'embedded-service'` under `tempfile.TemporaryDirectory`, so `{nested}` is absolute. The relative form is what the `cd` test uses (`nested.relative_to(root)`), and that test never goes through `-C`.

In `_collect_push_invocations`, relative and absolute `-C` share the assignment `directory = resolved` only after `_literal_path` succeeds. A one-branch weakening that applies `-C` only when `Path(value).is_absolute()` leaves every current test green:

- absolute `-C` into the nested repo still denies
- `git -C "$CHECKOUT"` still fails closed because `_literal_path` returns `None` before that assignment
- relative `cd` and relative `env GIT_DIR=` use other branches
- no test allows or denies `git -C <relative-nested> push`

The reproduction command `git -C nested push origin HEAD:refs/heads/x` would again resolve in the nested repository and inherit the outer grant. That is the repository-binding hole, not a spelling nit. The suite does not lock it.

The confirming mutant was not executed (shell blocked). The gap does not depend on that run: no assertion in the module mentions a relative `-C` operand.

## Related unpinned spellings (same class, not separately reproduced)

These are absent as commands, so the same style of branch-local "absolute only" edit is not forced red. They are secondary to the relative `-C` finding.

- `git --git-dir=<relative>/.git push` is not a test. The option test uses absolute `--git-dir={nested}/.git`. Relative coverage of this variable is only `env GIT_DIR=vendor/embedded-service/.git`, which is the assignment prefix, not the `--git-dir=` arm.
- Tool `directory=<relative nested>` is not a test. Both policy tests and `test_hook_denies_a_push_whose_directory_is_a_foreign_repository` pass absolute paths. The reproduction's directory probes were also absolute, so this is a narrower hole than relative `-C`.
- Legitimate `git -C <bound> push origin <ref>` with no destructive flag is not an allow test. Every `git -C {root} push` case expects deny because it is `--force`, `--delete`, `--prune`, `--mirror`, or `+refspec`. AC-003's " `-C <bound>` is not refused" is not locked for a non-destructive push.
- `--work-tree=<nested>` without `--git-dir` is not a test. The existing work-tree test always pairs `--work-tree` with `--git-dir`, and the `$TREE` case only locks an unreadable operand. Ignoring `push.work_tree` in `_push_repository_target` would not flip a current assertion. This is a limitation rather than a second ref-write escape: git still writes refs through `GIT_DIR` or discovery from the working directory, not through `--work-tree` alone.

## Unexecuted

- No mutant process, no forked-hook re-run, no timing re-measure of the scan bound or the config cap.
- Numeric `_PUSH_SHELL_DEPTH` is only locked relative to itself (`range(legacy._PUSH_SHELL_DEPTH + 1)`), so a larger constant would not go red. Not treated as a binding failure.
- Named non-goals in `requirements.md` (git aliases, `GIT_SSH_COMMAND`, unknown wrappers, `include`/`includeIf`, origin-slug versus filesystem path) are outside this lock and were not probed.

## Conclusion

Relative `cd`, absolute `-C`, absolute `--git-dir`, relative `GIT_DIR=`, absolute `directory`, destination, destructive forms after global options, and the shared `directory` alias are asserted. The documented nested-repository escape `git -C <relative> push` is not. The tests therefore do not lock the issue #58 push-grant repository binding for every repository-selection form the change itself reproduced.

VERDICT: FAIL
