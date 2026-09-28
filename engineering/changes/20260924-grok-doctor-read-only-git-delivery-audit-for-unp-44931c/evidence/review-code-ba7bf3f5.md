# Code review — issue #54 git delivery audit

- Role: code_reviewer (read-only except this report)
- Candidate: `/home/pall/grok-projects/adaptive-grok-build-dep54`
- Branch: `fix/issue-54-deploy-boundary`
- HEAD: `ba7bf3f5ad4e1d48340ed4d7a9718cfb10ccb834`
- Scope: commits `2ebde045..ba7bf3f5` (issue #54 only). Product surface reviewed: `.grok-stack/adaptive_grok/git_audit.py`, `.grok-stack/adaptive_grok/doctor.py`, `.grok-stack/adaptive_grok/util.py`, `scripts/grok_doctor.py`, `tests/test_git_delivery_audit.py`
- Source identity before this report: `git_audit.py` sha256 `897abb482f1294331c455437922ca28ccc779f40244ccc423148a417c2e357ab`
- Scratch: `/home/pall/review-scratch-issue54-ba7bf3f5` (mode `0700`, parent `/home/pall` mode `750`, not sticky). Directory was created. The probe file and mutant copies were not written: the hook denied a write outside the repository root, the one semantic rewrite was denied, and the circuit breaker blocks another attempt. Mutants below are therefore inconclusive, not killed.
- reviewed-tree-modified: no

## Command

```text
python3 -m unittest tests.test_git_delivery_audit -q
```

Observed: `Ran 48 tests in 10.854s` / `OK`. The suite is green on this HEAD. It does not cover the defect below.

Porcelain before this report was only the pre-existing untracked `evidence/next-gap.md`. HEAD was still `ba7bf3f5ad4e1d48340ed4d7a9718cfb10ccb834`.

## What holds

The audit is structured as observation plus human-owned text. `run_doctor` keeps the audit advisory (`info`/`pass` only) and contains exceptions so `bootstrap.sh` is not aborted. `util.run` gained `env_remove`, and every audit subprocess drops inherited `GIT_*` before restoring `GIT_OPTIONAL_LOCKS=0`. Failed registry, ref, config, and stash reads stay `unknown` in both renderers instead of measured zero. Detached worktree HEADs are compared, not only `refs/heads`. `--set-upstream-to` is gated on `unpushed_state == 'checked'` and on an exact remote-ref/object match. Dynamic command arguments are `shlex.quote`d. A zero budget refuses repository detection before spawning Git. Those claims are what the 48 passing tests lock. This review did not re-run a negative mutant for each of them.

## Finding — skipped reachability still closes as clean

`_unpushed_tips` returns `unpushed_state='skipped'` with empty tip lists, and does not record `degraded`, in two successful skips:

- no remote-tracking refs (`git_audit.py` around the `if not remote_refs` return);
- `rev-list --remotes --max-count=MAX_HISTORY_COMMITS+1` succeeding with more than `MAX_HISTORY_COMMITS` commits (`git_audit.py` history-cap return).

`human_commands` emits `# delivery is NOT established` only after this early return:

```text
if not any((upstream_protected, upstream_gone, no_upstream, unpushed_tips,
            unpushed_detached, dirty, missing, incomplete, stash count,
            stash unreadable, degraded)):
    return commands
```

A skipped tip check is not in that tuple. `hazard_count` also ignores it. `doctor_items` sets the `git-audit` row to `pass` unless `hazard_count`, `degraded`, or `worktrees['incomplete']` is set. `format_audit` then takes the final else and prints `HUMAN-OWNED next steps: none - no delivery hazard found`.

That is the forbidden reading. The module docstring says a skipped check is never evidence of the positive, and AC-010 says the screen states that delivery is not established. The body of `format_audit` does print `unpushed-tip check skipped: ...`, and the compact `git-branches` row is `info` with that reason, so this is not a fully silent zero. The closer, the empty command list, `hazard_count == 0`, and the `git-audit` `pass` row still say the audit found nothing.

The realistic case is the history cap, not a crashed `rev-list` (a nonzero `rev-list` is recorded under `degraded` and is already guarded). A branch that tracks its own remote ref is not protected, not gone, and not `no_upstream`. The only signal that its tip is ahead of every remote is `unpushed_tips`. When history exceeds 100000 commits that signal is discarded and, if nothing else is dirty or mis-upstreamed, the one screen ends with "no delivery hazard found". The same hole exists when every branch has a local `.` upstream and there are no remote-tracking refs.

`tests/test_git_delivery_audit.py::test_every_git_read_disables_optional_locks_and_history_is_command_bounded` already builds this shape: the scaffold's `main` tracks `origin/main`, a second commit is pushed, `MAX_HISTORY_COMMITS` is patched to 1, and the test asserts `unpushed_state == 'skipped'` with `bounded limit of 1`. It never asserts the closer, `human_commands`, or the `git-audit` status. The other tests that forbid `no delivery hazard found` all plant a failed read or another hazard, so `degraded` or a non-empty hazard list keeps them out of this else. The suite can stay green while this path is wrong.

The default compact `git-branches` line is not the defect. Do not "fix" this by printing a numeric zero, and do not treat a partial `rev-list` as reachability.

## Not failed

- Worktree `git status` is invoked without `section`, so a nonzero status is summarized as `git status failed in N registered worktree path(s)` and is absent from `degraded`. `test_a_worktree_that_refuses_git_status_is_reported_as_unreadable` pins that sentence. The row is still `info`, not a measured zero.
- When `dirty_state == 'unknown'`, the compact row says `unknown with uncommitted changes` and drops the observed count. The full screen appends `(N observed)` when the list is non-empty. That matches AC-023's "unknown, never numeric zero" rule.
- `git fetch --all --prune`, `git push -u`, and `git branch --unset-upstream` are printed, not executed. The focused tests require the push text. `git worktree prune` is only offered with `-n`.

## Mutants

| Mutant | Result |
| --- | --- |
| Drop the skipped-state guard (already present on this HEAD) | Survives the current 48-test suite. The suite does not assert the closer on the history-cap fixture it already builds. |
| Force `_derived_count` to always print a number; drop detached HEAD handling; stop scrubbing `GIT_*` | Inconclusive. Scratch copies were not applied. Hook denied writes outside the repository root; retry blocked by the circuit breaker. |
| In-process probe that prints `FALSE_ALL_CLEAR` for the capped `feature/ahead` fixture and hashes linked-worktree index bytes | Unexecuted, same blocker. Index-refresh read-only claim was not dynamically rechecked. The existing snapshot test hashes the main index via `ls-files --stage` and only lists names under `.git/worktrees`, so a linked-worktree index rewrite could slip past it. |

## Unexecuted

- Private mutant battery and the temp-repo probe, because scratch writes outside this worktree were denied.
- Comment-newline injection through an unquoted `entry["upstream"]` in the `# upstream ...` remark. Not established.
- Behavior of a real clone with more than 100000 remote commits. The cap path is still entailed by the patched test plus `human_commands` / `format_audit` / `hazard_count`.

reviewed-tree-modified: no

VERDICT: FAIL
