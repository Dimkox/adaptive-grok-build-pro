# Code review — absent-route human gate fails closed

Reviewer: code_reviewer
Scope: absent-route human-gate fail-closed behavior only. Untracking `packages/` was not a review requirement and is not a finding.
Candidate: `/home/pall/grok-projects/adaptive-grok-build-gate55`
Branch: `fix/issue-55-gate-without-route`
HEAD: `00d7fbecc8a67836dda8363184a908b617ed27c7`
Commit subject: `fix(gates): name the recovery path on an absent route and pin the fail-closed seam`

## Source identity

At review start, `git status --porcelain=v1` and `git diff --stat HEAD` were empty, so the candidate worktree matched HEAD. `tree_fingerprint` then hashes that HEAD and no changed paths. A later shell attempt to recompute the hex was circuit-broken and was not retried. The verification receipt for this same HEAD records `tree_fingerprint` `808ab5310e482c82dce9257f81cbdc997cdfd254aed7df18b93439a857b5d26d`, but that receipt is `stale` (`repository tree changed after tool use`). That hex is historical, not a fresh post-review digest.

Scratch: `/home/pall/review-scratch-gate55` (mode `0700`; parent `/home/pall` mode `750`, not sticky). Snapshot was the candidate `.grok-stack` package, config, templates, `tests/`, and `scripts/` copied before any mutation. Machine-local `.grok-stack/runtime/` was not copied. `human_gates.py.bak` matches the candidate file byte for byte (`cmp` after the probes). `tests/test_human_gates.py` matches the candidate. No product file in the candidate was edited. Mutations were applied only under the scratch and then reverted there.

reviewed-tree-modified: no

## Behavior reviewed

When `get_active_route` returns `None` (no `active-route.json`), `human_gates._context` returns `active route is missing or malformed` plus `ROUTE_RECOVERY_HINT`. `gate_block_reason` does not take the empty-gate early return unless the route value is a dict, so a missing route falls through to that context error. `gate_transition_block_reason` returns the same error for target `approved`. `gate_statuses` publishes one `__route_gates__` row with state `invalid` and that reason. `add_approval` raises that reason. `record_gate_decision` raises it. The hint keeps the old prefix and names `python3 scripts/grok_route.py "<task text>" --json`. `--session` defaults to `manual`, so the hint is a real router invocation.

## Claims probed

### C1 — Missing route is not approval on the seams the new tests call

Command:

```text
cd /home/pall/review-scratch-gate55 && python3 -m unittest \
  tests.test_human_gates.HumanGateTests.test_absent_route_record_fails_closed_on_every_gate_seam \
  tests.test_human_gates.HumanGateTests.test_recorded_approval_does_not_outlive_the_route_that_declared_it \
  tests.test_human_gates.HumanGateTests.test_absent_route_block_reason_names_the_recovery_command -q
```

Observed: `Ran 3 tests in 0.659s` / `OK`.

Result: killed for the laundering mutant below. The unmutated code denies.

### C2 — Laundering a missing route into `gate_block_reason is None` is detected

Scratch-only edit in `gate_block_reason`, after `route = get_active_route(root)`:

```text
if route is None:
    return None
```

Same three tests. Observed three failures:

- `test_absent_route_record_fails_closed_on_every_gate_seam`: `unexpectedly None : production gate laundered an absent route into a pass`
- `test_recorded_approval_does_not_outlive_the_route_that_declared_it`: `unexpectedly None`
- `test_absent_route_block_reason_names_the_recovery_command`: `unexpectedly None`

Mutant: killed. Scratch file restored from `human_gates.py.bak` before the next mutant.

### C3 — Denial text keeps the prefix and names the router command

Scratch-only edit: `ROUTE_RECOVERY_HINT = ""`. Same three tests. Observed one failure:

```text
AssertionError: 'grok_route.py' not found in 'active route is missing or malformed'
```

The other two tests stayed green. That split is intended: fail-closed does not depend on the suffix.

A second scratch-only edit changed only the context-error status from `invalid` to `approved` and left the reason alone. Observed:

```text
[{'gate': '__route_gates__', 'state': 'approved', 'reason': 'active route is missing or malformed; recreate it with: python3 scripts/grok_route.py "<task text>" --json', 'evidence_path': None}]
```

and `AssertionError: 'approved' != 'invalid'` in the recorded-approval test. The recovery-command test does not read `gate_statuses`, so it stayed green. The suite still killed the mutant.

Mutants: killed. Exact public reason on the missing-route status row is the string above.

### C4 — A recorded gate decision does not survive route deletion

Covered by the unmutated `test_recorded_approval_does_not_outlive_the_route_that_declared_it` (`OK` in C1) and by C2, where forcing `gate_block_reason` to `None` after unlink failed `assertIsNotNone`.

Mutant: killed.

## Surviving mutant (limitation, not a product pass)

Scratch-only edit in `has_valid_approval`: the production/external-write `gate_block_reason` short-circuit was forced off (`if False and scope in ...`). `human_gates.py` was the restored original. Same three tests: `Ran 3 tests in 0.668s` / `OK`.

Mutant: survived.

Why it is not a fail-open in this tree: those tests never write `approvals.json`. With no delegated grant, `has_valid_approval` is false even if it never calls the gate. The product function still calls `gate_block_reason` when `action` is set, and `evaluate_pre_tool` / `deploy.py` pass an action. A grant minted under a real `route_id` also stops matching once the route file is gone, because the binding `route_id` becomes null. The tests do not prove that second line. Restored the scratch `state.py` afterward.

## Unexecuted

- Separate process for non-object or unreadable route bodies. `get_active_route` already maps those to `None`, which is the branch C1–C3 executed. Not run as its own fixture.
- JSON object with no `route_id` and no declared gates, and no active change. Static reading only: `gate_block_reason` still has the pre-existing early `return None` for an empty gate list. That is not a missing route file. Requirements define the malformed case this change pins as non-JSON or non-object. Not executed, and not treated as an absent-route failure.
- `evaluate_pre_tool` and `scripts/grok_gate.py status` as separate processes. Both call `gate_block_reason` / `gate_statuses`, which were executed.
- Fresh hex of `tree_fingerprint` after the fingerprint command was circuit-broken.
- `packages/` tracking. Out of scope for this review.

## Conclusion

A checkout with no route record does not come back as an approval. Production and external-write `gate_block_reason`, the approved-transition block, `gate_statuses`, and `add_approval` stay on the missing-route denial, and deleting the route invalidates a previously approved gate decision. The denial still starts with `active route is missing or malformed` and appends the `grok_route.py` recovery command. The one surviving mutant shows a test gap around `has_valid_approval` when no grant file exists; it does not show the product treating a missing route as approval.

VERDICT: PASS
