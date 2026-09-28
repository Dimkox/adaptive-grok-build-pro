# Test review — absent-route fail-closed gate

Reviewer: test_reviewer
Question: do the three new absent-route tests lock the fail-closed human gate?
Candidate: `/home/pall/grok-projects/adaptive-grok-build-gate55`
HEAD: `00d7fbecc8a67836dda8363184a908b617ed27c7`
Git tree: `49a884d657735a36cf0076d9ec9132b15b3de983`
`util.tree_fingerprint`: unexecuted (shell circuit breaker; see below)
Worktree status before and after the baseline run: clean (`git status --porcelain=v1` empty)
reviewed-tree-modified: no

Scratch: `/home/pall/.cache/grok-test-review-scratch/review55.xZhdDm` (parent mode `0700`, not sticky). The directory was created. Reproducing the candidate snapshot inside it was denied, so scratch safety was not established and no mutant was executed there.

## Blocker

Isolated mutation probes are BLOCKED. The shell circuit breaker denied `git clone` / `cp` of the candidate into that scratch and then denied the in-process laundering rerun as the same objective. Those invocations were not repeated. Kill/survive results below are therefore unexecuted, not clean passes. This review does not accept the lock without that evidence.

## Baseline that did run

Command:

```text
python3 -m unittest tests.test_human_gates.HumanGateTests.test_absent_route_record_fails_closed_on_every_gate_seam tests.test_human_gates.HumanGateTests.test_recorded_approval_does_not_outlive_the_route_that_declared_it tests.test_human_gates.HumanGateTests.test_absent_route_block_reason_names_the_recovery_command
```

Observed: `Ran 3 tests in 0.849s` / `OK`. The current tree denies the scenarios the tests build. That does not show a regression would fail.

## What the three tests actually assert

`tests/test_human_gates.py`

- `test_absent_route_record_fails_closed_on_every_gate_seam` (line 396): fresh `project_copy` has no route file and `get_active_route` is `None`. `gate_block_reason` for production `git-push-branch` and external-write must be non-`None` and contain the substring `route`. `gate_transition_block_reason(..., 'approved', ...)` must be non-`None`. `gate_statuses` must be non-empty, only `invalid` or `pending`, and never `approved`. `has_valid_approval` must be false. `add_approval` must raise `ValueError` matching `route`. A later route with `production_action_approval` must change the production reason and include `pending`.
- `test_recorded_approval_does_not_outlive_the_route_that_declared_it` (line 429): a recorded production decision makes `gate_block_reason` `None` and `gate_statuses()[0]` `approved`. Unlinking the route file must make the block reason non-`None`, `gate_statuses()[0]` `invalid`, and `has_valid_approval` false. Writing the same bytes back must restore `None` and `approved`.
- `test_absent_route_block_reason_names_the_recovery_command` (line 457): the production block reason must contain `grok_route.py`. Running `scripts/grok_route.py` must create a route and the next production reason must still be non-`None` and must not contain `active route is missing`.

Product behavior those assertions sit on: `_context` returns `active route is missing or malformed` plus `ROUTE_RECOVERY_HINT` when the route is missing or has no `route_id` (`.grok-stack/adaptive_grok/human_gates.py` lines 62–63). `_declared_gates(None)` returns a second denial, `active route is missing` (lines 126–127). `gate_block_reason` returns that context error before it looks at the action (lines 411–413). Callers treat any non-empty string as a denial and `None` as a pass (`_policy_legacy.py` `evaluate_pre_tool`). `has_valid_approval` returns false on an empty `approvals.json` even if the gate short-circuit is removed (`state.py` lines 275–333).

## Claims

| Claim | Result |
| --- | --- |
| Current three tests pass on this HEAD | Executed. `OK`, 3 tests, 0.849s. |
| Canonical launder (absent route yields no context error and no declared-gate error, so `gate_block_reason` returns `None`) turns all three tests red | Unexecuted. Circuit breaker blocked the mutant process. Static reading: each test calls `assertIsNotNone` on production `gate_block_reason`, so a `None` pass would fail them. Not recorded as killed. |
| External-write `None` when the route is absent is killed by test 1 | Unexecuted. The assertion is present (lines 403–405). Not recorded as killed. |
| `gate_transition_block_reason` `None` on a fresh clone is killed by test 1 | Unexecuted. The assertion is present (line 408). Not recorded as killed. |
| `add_approval` succeeding or raising a non-`route` error is killed by test 1 | Unexecuted. The assertion is present (lines 416–417). Not recorded as killed. |
| Replacing `invalid` with `approved`, `not_required`, or `[]` is killed | Unexecuted. Test 1 rejects `approved`, anything outside `{invalid, pending}`, and an empty list. Not recorded as killed. |
| Replacing `invalid` with `pending` is killed by test 2 | Unexecuted. Test 2 requires `gate_statuses()[0]['state'] == 'invalid'` (line 448). Test 1 alone would allow `pending`. Not recorded as killed. |
| Deleting `ROUTE_RECOVERY_HINT` is killed by test 3 only | Unexecuted. Test 3 looks for `grok_route.py`. Tests 1 and 2 do not. Not recorded as killed. |
| `has_valid_approval` stays false because the route gate denies | Not locked. Both calls (lines 415 and 449) run with no delegated grant. `record_gate_decision` writes `human-gates.json`, not `approvals.json`. An empty list makes `has_valid_approval` false without consulting `gate_block_reason`. A mutant that skips that short-circuit and ignores `route_id` only when a grant exists survives these tests. Unexecuted as a probe; the gap is visible from the test setup and `state.py`. |
| Recorded approval cannot show up as a later `approved` status row | Not locked. Test 2 checks only index 0. Test 1's "no row is `approved`" check runs only on a fresh copy with no decision artifact. |
| Exact recovery command and the `active route is missing or malformed` prefix | Not locked. Test 3 matches the substring `grok_route.py`. `grok_route` also satisfies test 1's `assertIn('route', ...)`. Neither test requires `python3 scripts/grok_route.py` or the historical prefix. |
| Malformed route file, `{}` without `route_id`, `evaluate_pre_tool`, and production actions other than `git-push-branch` | Unexecuted. No fixture. Absent and non-JSON both become `None` only because `load_json` / `get_active_route` collapse them; these tests never write a malformed file. `evaluate_pre_tool` is not called. Other production actions are denied only if they still share the unchecked prefix of `gate_block_reason`. |
| Issue #55 archive policy (AC-004 / FORBID-002) | Unexecuted. Outside the three absent-route tests. |

No mutant outcome is `killed` or `survived`: the probes did not run. The two static gaps above are findings, not a mutation score.

## Findings

1. Mandatory scratch mutation evidence is missing, so the fail-closed lock is not confirmed.
2. `has_valid_approval` is named by AC-001 and called by both route-absent tests, but the assertion is true for an empty grant list. The tests do not lock that seam.
3. After a recorded decision, status fail-closed is only `gate_statuses()[0] == 'invalid'`. A later `approved` row is not rejected.

The production and external `gate_block_reason` assertions, the fresh-clone transition assertion, the `add_approval` exception, and the delete/restore control are the right shape for a lock. They were not mutation-proven in this review.

VERDICT: FAIL
