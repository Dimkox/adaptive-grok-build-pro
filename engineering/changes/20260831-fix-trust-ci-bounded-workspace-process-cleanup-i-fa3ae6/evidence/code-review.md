# Code review — bounded workspace zombie-only cleanup

Verdict: **PASS**

Route: `fa3ae6080deb`
Stacked base: `9493741dd34fdfa1e37efdc09b35e30d5535be7c`
Reviewed tree: dirty worktree at base HEAD, before this report was added
Pre-review verification tree fingerprint: `7b768fbef0db4c1cfe7a9603349a6e71cdc60907c96d2f0f7b2ba3f6584e93b6`

This is independent, read-only review evidence. It is not merge authority and does not replace the App-owned exact-SHA Trust CI check.

## Findings

No blocking, important, or minor correctness findings.

## Review evidence

- The product change is confined to `trust-ci/src/adaptive_trust_ci/workspace.py`; the paired behavior tests are in `trust-ci/tests/test_workspace.py`. No deployed policy, holdout, image, approval, trust-store, architecture-authority, public API, schema, migration, or GitHub Actions file changes are present.
- The containment sequence remains intact: a new session supplies the original PGID; cleanup sends `SIGTERM`, performs the existing bounded TERM wait, sends `SIGKILL`, performs a bounded post-KILL check, and polls/reaps the direct `Popen` leader. The new classifier does not signal individual or unrelated processes.
- Cleanup succeeds only for `absent` or positively observed `zombie_only`. A live member, invalid/own PGID, unavailable or unreadable procfs, malformed/truncated stat data, deadline exhaustion, entry-limit exhaustion, inability to prove absence, or inspection error returns/raises an uncertain outcome and therefore fails closed.
- Procfs work is bounded by the existing KILL deadline, a 100,000 numeric-entry ceiling, and a 4,096-byte stat ceiling. Parsing uses the last `) ` separator so spaces and parentheses in `comm` do not shift the state/PPID/PGID fields; `fields[2]` is the process-group field after state and PPID.
- Error causality is preserved correctly. `_run_bounded_process()` re-raises the already classified stdout, stderr, or timeout error only when `_terminate_process()` proves absence/zombie-only cleanup. Live or unknown state still replaces it with `bounded process group survived SIGKILL`, preserving containment priority.
- The one-line receipt-test adjustment removes a branch-global fitness assertion from a test whose contract is frozen-adoption comparison-base binding. The remaining assertions still bind architecture base, exact comparison base, architecture fingerprint, route base, base kind, and bootstrap state. Independent architecture fitness against this route's exact stacked base remains authoritative and passed.
- Rollback is narrow and recoverable: revert/forward-fix the classifier plus focused regressions. The documented rollback explicitly forbids replacing it with unconditional group-presence tolerance.

## Commands and observed results

```text
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest trust-ci.tests.test_workspace -v
Ran 19 tests in 3.024s — OK

python3 -m unittest tests.test_change_receipts -v
Ran 22 tests in 27.009s — OK

python3 scripts/grok_architecture.py fitness \
  --base 9493741dd34fdfa1e37efdc09b35e30d5535be7c \
  --worktree --pre-risk yellow --json
fitness_status=pass; risk_escalation=green; findings=[]

git diff --check
clean

python3 scripts/grok_spec.py validate \
  engineering/changes/20260831-fix-trust-ci-bounded-workspace-process-cleanup-i-fa3ae6/change-spec.yaml \
  --gate
ok=true; errors=[]
```

The existing route verification receipt for the reviewed pre-report tree records `status=pass`, exact route base `9493741dd34fdfa1e37efdc09b35e30d5535be7c`, architecture drift/fitness/diagrams pass, and 404 root tests passing. Writing this report changes the repository fingerprint, so the coordinator must bind final review/verification evidence to the resulting tree rather than reuse stale evidence.

## Residual risks

- The positive zombie-only classification is Linux/procfs-specific and is a bounded snapshot. PID churn, restricted procfs, slow enumeration, or disappearance during a read can conservatively produce `unknown` and mask the original command error; it cannot turn uncertainty into cleanup success.
- A host near the entry or time ceiling may fail closed more often. This is operational availability risk, not containment weakening; the configured limits and current one-second KILL grace should be monitored through the existing low-cardinality runner failure outcome without logging PIDs or process listings.
- Local review remains preflight evidence. A committed hotfix still needs a fresh App-owned policy-epoch check on the exact PR head SHA and any external approval required by deployed policy.
