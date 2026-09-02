# Code rereview — TR-001 remediation

Verdict: **PASS**

Route: `fa3ae6080deb`
Stacked base: `9493741dd34fdfa1e37efdc09b35e30d5535be7c`
Reviewed verification fingerprint: `a9a4cc297ab7e84b301340aaf8bea48b1c6a92d8bb578e862d081370826a3da9`
Superseded code-review fingerprint: `7b768fbef0db4c1cfe7a9603349a6e71cdc60907c96d2f0f7b2ba3f6584e93b6`

This report is independent local review evidence only. It does not modify the prior reports, create a receipt, or replace the App-owned exact-SHA Trust CI merge gate.

## Findings

No blocking, important, or minor code findings.

TR-001 is closed for code-review purposes. The remediation adds direct deterministic execution of the security-relevant procfs classifier without changing production cleanup behavior.

## Rereview assessment

- `PostKillProcessGroupClassifierTests` now directly executes `_classify_post_kill_process_group()` rather than mocking its returned classification. It proves that all observed target-PGID members in `Z` state yield `zombie_only`, while `R`, `S`, and explicitly `X` yield `live` and therefore remain fail closed.
- Malformed, truncated, oversized, unavailable, open/read-error, numeric-entry-limit, enumeration-deadline, post-read-deadline, and final-probe-uncertain paths are directly asserted as `unknown`. A vanished `/proc/<pid>` entry is accepted only when the final group probe independently proves absence.
- Non-numeric procfs entries are ignored, non-target PGIDs are not treated as target members, and seeing no target member is not zombie proof. Final group presence produces `unknown`; only independently proven nonexistence produces `absent`.
- Test fixtures keep enumeration, file descriptors, stat records, monotonic time, and group-existence outcomes deterministic. The mocked stat records use the real Linux field ordering consumed by the implementation: state, PPID, then PGID after the final `) ` separator.
- The original runtime invariants remain unchanged: new session/original PGID, own-group guard, `SIGTERM`, bounded TERM wait, `SIGKILL`, bounded KILL wait/classification, and direct leader polling/reaping. The classifier performs bounded read-only observation and never signals an individual or unrelated PID.
- Original stdout/stderr/timeout failures are still preserved only after `absent` or `zombie_only`; live and uncertain classifications still produce `bounded process group survived SIGKILL`.
- The prior one-line frozen-adoption receipt-test stabilization remains scoped to binding evidence. The current route-base architecture fitness independently passes against exact base `9493741dd34fdfa1e37efdc09b35e30d5535be7c`; no architecture, public contract, policy, holdout, image, approval, trust-store, deployment, or GitHub Actions authority changed.
- The documented rollback remains a narrow revert/forward-fix of the classifier and tests and explicitly forbids unconditional process-group tolerance.

## Independent commands and results

```text
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest \
  trust-ci.tests.test_workspace.PostKillProcessGroupClassifierTests -v
Ran 9 tests in 0.027s — OK

PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest \
  trust-ci.tests.test_workspace -v
Ran 28 tests in 3.058s — OK

COVERAGE_FILE=/tmp/fa3ae6-code-rereview.coverage \
PYTHONPATH=trust-ci/src coverage run --branch \
  --source=adaptive_trust_ci.workspace \
  -m unittest trust-ci.tests.test_workspace -q
Ran 28 tests in 3.152s — OK
workspace.py: 81%; classifier body covered except the early own-worker-PGID return

python3 scripts/grok_architecture.py fitness \
  --base 9493741dd34fdfa1e37efdc09b35e30d5535be7c \
  --worktree --pre-risk yellow --json
fitness_status=pass; risk_escalation=green; findings=[]

git diff --check
clean
```

The full `grok_verify --mode pr` receipt created at `2026-08-31T15:04:00+00:00` is PASS for reviewed fingerprint `a9a4cc297ab7e84b301340aaf8bea48b1c6a92d8bb578e862d081370826a3da9`: diff, spec, architecture drift/fitness/diagrams, secret scan, contracts, SQL safety, Ruff, Bandit, 404 root unittests, and coverage all passed. Its exact architecture base is the selected stacked base `9493741dd34fdfa1e37efdc09b35e30d5535be7c`.

Writing this rereview report changes the tree fingerprint. The coordinator must bind final receipts to the resulting tree and must obtain a fresh independent test-review PASS; the retained `test-review.md` is intentionally the prior fingerprint's TR-001 failure record.

## Residual risks

- Zombie-only classification remains a bounded Linux/procfs snapshot. PID churn, restricted procfs, slow enumeration, or a read race can conservatively return `unknown`; this may mask the original command error but cannot weaken containment.
- A runner near the 100,000-entry or one-second KILL-grace bounds may fail closed more often. Existing low-cardinality runner failure signals should surface that availability condition without logging PIDs, process listings, commands, or environment data.
- Local verification and review remain preflight evidence. The final committed PR head still requires the deployed App-owned policy-epoch check and any external approval required by deployed policy.
