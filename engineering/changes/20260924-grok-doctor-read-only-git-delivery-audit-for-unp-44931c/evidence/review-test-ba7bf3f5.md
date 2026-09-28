# Test review — issue #54 read-only git delivery audit

- Role: test_reviewer (read-only except this report)
- Candidate: `/home/pall/grok-projects/adaptive-grok-build-dep54`
- Branch: `fix/issue-54-deploy-boundary`
- HEAD: `ba7bf3f5ad4e1d48340ed4d7a9718cfb10ccb834`
- Git tree: `121751accb36ddafd51d6eae168b3b4e3fa87569`
- Question: do `tests/test_git_delivery_audit.py` lock the read-only delivery audit (AC-001 … AC-023), including "a skipped check is not proof of delivery"?

## Source identity

`python3` `tree_fingerprint()` was not run. The shell circuit breaker blocked that invocation after an earlier ambiguous `git show` denial, and the retry was not repeated.

Pre-probe porcelain was only untracked `evidence/next-gap.md`. Product bytes before and after the probes:

| File | sha256 |
| --- | --- |
| `.grok-stack/adaptive_grok/git_audit.py` | `897abb482f1294331c455437922ca28ccc779f40244ccc423148a417c2e357ab` |
| `.grok-stack/adaptive_grok/doctor.py` | `fa19c48a20a692b2bd962f0223be04186936f992eac46059d95b4b1162aee4a5` |
| `.grok-stack/adaptive_grok/util.py` | `d901911be757f3e3afbdb4d4ecf641fbe6bedd7d302839ab3912cc305b2bc22a` |
| `scripts/grok_doctor.py` | `5d0b070a563e171d337e9fa0a17bf3e46489cc3c2917ee908894ed1a69a0d620` |
| `tests/test_git_delivery_audit.py` | `edf5b7115bd8d9306e79e2ed4fef432c686552f7badf2d36f3a1154baeba6da6` |

`util.py` was hashed from the scratch pristine copy taken at the start and matched the worktree afterward. During this review an unrelated untracked file appeared: `evidence/review-code-ba7bf3f5.md`. It was not in the scratch snapshot. This reviewer did not write it. Product hashes above did not change.

Scratch: `/home/pall/.cache/review-scratch-parents/issue54-ba7bf3f5` (mode `0700`). Parent `/home/pall/.cache` is mode `700`. `/home/pall` is mode `750` and is not sticky. Copies live under `snapshot/`, `m3/`, `m6/`, `m8/`, `m9/`, `m10b/`, `m14/`, `m15/`, `m19/`.

reviewed-tree-modified: no

## Baseline

Command, cwd = reviewed worktree:

```text
python3 -m unittest tests.test_git_delivery_audit -q
```

Observed: `Ran 48 tests in 11.122s` / `OK`.

## Mutants

Each mutant was applied only under the scratch tree named below, then:

```text
cd <scratch-tree>
python3 -m unittest <tests> -q
```

| Mutant | Edit | Tests | Observed | Outcome |
| --- | --- | --- | --- | --- |
| M4 flag `main -> origin/main` as protected | scratch snapshot, drop `and branch not in PROTECTED_BASE_BRANCHES` | `GitDeliveryAuditTests.test_own_base_branch_tracking_its_remote_is_not_a_hazard` | `AssertionError`: `upstream_protected` is `[{'branch': 'main', 'upstream': 'origin/main', 'remote': 'origin'}]` | killed |
| M6 fold a failed `worktree list` into exit 0 | `m6`, `return [], code` → `return [], 0` | `test_a_failing_registry_read_names_itself_instead_of_reporting_zero` | `AssertionError: 0 is not None` on `worktrees.registered` | killed |
| M9 count a nested untracked directory as one line | `m9`, `--untracked-files=all` → `normal` | `test_nested_untracked_files_are_counted_individually` | `changed_files` `1 != 3` | killed |
| M14 drop the protected-base screen line | `m14`, that `format_audit` line becomes `upstream omitted` | `test_the_screen_prints_every_detail_line_it_owns` and `DoctorCliTests.test_git_audit_flag_prints_one_screen` | both missing `upstream is a protected base: ...` (`feature/danger -> origin/main`, and CLI `feature/cli-hazard -> master`) | killed |
| M15 protected branch row fails the gate | `m15`, `git-branches` status literal `info` → `fail` | `DoctorWiringTests.test_doctor_never_fails_because_of_the_delivery_audit` | `AssertionError: ['fail'] != []` | killed |
| M19 audit exception escapes `run_doctor` | `m19`, contained handler replaced with `raise` | `test_a_broken_audit_degrades_to_a_row_instead_of_aborting_the_screen` | `RuntimeError: simulated audit crash` from `doctor.py` | killed |
| M3 drop `--local` on `git config --get-regexp` | `m3` | hostile-global test alone, then the full module | hostile-global test `OK` (0.097s). Full module `FAILED (failures=1)`: `test_an_unreadable_upstream_config_is_unknown_not_no_upstream` got `upstream_state` `checked` instead of `unknown`, because the failure double matches the fragment `config --get-regexp --local` | killed by the suite, not by the hostile-global test |
| M10b delete `--ignore-submodules=none` | `m10b` line removed; status remains `--porcelain=v1 --untracked-files=all` | full module | `Ran 48 tests in 11.378s` / `OK` on git 2.43.0 | survived |

M10b is an explicit limitation, not the fail below. On this host's default Git config the planted dirty submodule is still one status line, so the AC-013 outcome stays true without the flag. The suite does not plant `diff.ignoreSubmodules=all`, so that config is unexecuted. Deleting the flag is observationally equivalent for the fixture the tests build.

## Finding — capped skip still closes as "no delivery hazard found"

The test module's own header says a skipped check is never reported as delivery. AC-010 says the screen states that delivery is not established. That is locked only when some other hazard or a degraded read is also present.

`test_every_git_read_disables_optional_locks_and_history_is_command_bounded` already builds the hole: `main` tracks `origin/main`, one more commit is pushed, `MAX_HISTORY_COMMITS` is patched to 1, and the test stops at:

```text
self.assertEqual(report['branches']['unpushed_state'], 'skipped')
self.assertIn('bounded limit of 1', report['branches']['unpushed_skip_reason'])
```

It does not assert `format_audit`, `human_commands`, `hazard_count`, or the `git-audit` row. The shipped suite is green on this code (baseline above).

Source of the closer, on this HEAD:

- `_unpushed_tips` returns `skipped` with empty tip lists and does not record `degraded` when `rev-list` succeeds but exceeds `MAX_HISTORY_COMMITS` (`git_audit.py` history-cap return).
- `human_commands` returns `[]` immediately unless protected, gone, no-upstream, unpushed tips, detached tips, dirty, missing, incomplete, stashes, or `degraded` is set. A skipped tip check is not in that tuple (`git_audit.py` around the `if not any(...)` return).
- `hazard_count` does not count a skip.
- `doctor_items` sets `git-audit` to `pass` unless `hazard_count`, `degraded`, or `worktrees['incomplete']` is set.
- `format_audit` then prints `HUMAN-OWNED next steps: none - no delivery hazard found`.

The no-remote test and the failed-`rev-list` test do forbid that sentence, but both also plant `no_upstream` or a degraded read, so they never enter this else. A clean tracking repository whose remote history is only capped can still end the one screen with the all-clear while the tip check was skipped. The compact `git-branches` row stays `info` because of the skip reason; the defect is the closer, the empty command list, `hazard_count == 0`, and `git-audit: pass`.

A scratch-only assertion `self.assertNotIn("no delivery hazard found", format_audit(report))` on that existing test was not executed: `sed` inserting it was denied by the circuit breaker as a rewrite of an already blocked objective, and it was not retried. The missing assertion in the shipped test, and the baseline pass, are executed facts. The negative run of that assertion is unexecuted.

## Killed claims (executed)

- Own base `main -> origin/main` is not a protected-upstream hazard (M4).
- A failed worktree registry is not a measured zero (M6). The old "return code 0" mutant is no longer equivalent: `registered is None` is asserted.
- Nested untracked files are counted one by one (M9).
- The operator screen and `--git-audit` both print `upstream is a protected base:` (M14).
- A protected upstream does not make a `fail` row (M15).
- An exception inside the advisory audit becomes one `info` row instead of aborting `run_doctor` (M19).
- `--local` cannot be removed from the upstream-config read without the suite going red (M3), via the command fragment in `test_an_unreadable_upstream_config_is_unknown_not_no_upstream`.

## Unexecuted

- `git config gc.auto 0` during the audit, and a real `git worktree prune`, as read-only mutants. Shell text containing those git writes was circuit-broken. The snapshot in `test_audit_never_changes_the_repository` does include local config, refs, HEAD reflog, `ls-files --stage`, stash list, worktree porcelain, HEAD, `.git` and `.git/worktrees` names, and the bare remote. It does not hash linked-worktree index bytes or untracked worktree files. Those oracle edges were not dynamically rechecked.
- Ignoring detached HEADs, dedup-by-path, `git_audit=False` on the default `scripts/grok_doctor.py` path, clearing `env_remove`, and disabling the budget refusal. Those edits were denied by the same breaker and were not retried. `run_doctor`'s default `git_audit=True` is what `DoctorWiringTests` calls; the script's default boolean is not what those tests invoke.
- `~/.gitconfig` without `GIT_CONFIG_GLOBAL`. M3 showed the hostile-global test stays green when `--local` is removed, because `GIT_*` scrubbing already drops `GIT_CONFIG_GLOBAL`. The suite still kills that product edit through the `--local` command fragment.
- Missing `git` binary (exit 127), a worktree registered inside a different repository, and a real command that runs longer than the 20s budget. The zero-budget tests are present; a hung `git` was not started.
- Two detached worktrees on one commit collapsing to one record. No shipped test plants that shape.

## Verdict

The suite locks the hazards it builds with an extra failing read or an obvious mis-upstream: protected base versus `main`, swallowed registry counts, nested untracked files, the protected-base screen line, a non-failing gate, and a contained doctor exception. It does not lock the rule it states first for a skipped tip check that is otherwise clean. The history-cap fixture already in `test_every_git_read_disables_optional_locks_and_history_is_command_bounded` leaves `no delivery hazard found`, an empty `human_commands`, and `git-audit: pass` unasserted, and the 48-test baseline is green.

VERDICT: FAIL
