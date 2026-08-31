# Integration analysis — bounded workspace cleanup hotfix

Route: `fa3ae6080deb`  
Change: `20260831-fix-trust-ci-bounded-workspace-process-cleanup-i-fa3ae6`  
Method: read-only product analysis; this report is the sole write.

## Boundary decision

This is an internal Linux process-lifecycle repair in `trust-ci/src/adaptive_trust_ci/workspace.py`, not an HTTP, webhook, database, approval-envelope, attestation-envelope, or OpenAPI contract change. Preserve the external contract: a bounded Git command that overflows stdout/stderr or times out must report that original bounded failure after cleanup succeeds; a live or unverifiable survivor must remain a fail-closed workspace failure.

`_run_bounded_process()` starts a new session, making `process.pid` the process group ID. On a bounded failure it calls `_terminate_process()`, which currently uses `killpg(..., 0)` through `_process_group_exists()` as its only proof that the group is gone. Linux reports a zombie as extant to signal 0, so a killed, zombie-only descendant can make the post-SIGKILL grace expire and replace the original `stdout byte limit`, `stderr byte limit`, or timeout error with `bounded process group survived SIGKILL`.

## Required compatibility / security gates

| Area | Required behavior | Gate |
| --- | --- | --- |
| Original failure semantics | Preserve the initial overflow/timeout `WorkspaceError` if all remaining group members are conclusively zombies or disappear. | Regression cases cover stdout, stderr, and timeout with SIGTERM-ignoring descendants. |
| Live descendant | Any non-zombie member after SIGKILL is an unsafe survivor. | Keep `bounded process group survived SIGKILL` / fail-closed behavior; never return the original error. |
| Uncertain process state | Missing, malformed, unreadable, permission-denied, racing, or namespace-incomplete procfs evidence is not proof of zombie-only membership. | Fail closed rather than treating uncertainty as successful cleanup. |
| Leader lifecycle | The direct `Popen` leader must still be reaped with `wait`; zombie tolerance applies only to remaining descendants. | Preserve the leader-reap check and bounds. |
| Scope of signals | Never inspect/signal the worker's own process group; retain `start_new_session=True`, positive PGID checks, and `ProcessLookupError` tolerance. | Existing own-group/ESRCH regression stays green. |
| Resource bounds | Procfs inspection/polling must be bounded by existing SIGTERM/SIGKILL grace windows and never become an unbounded `/proc` scan. | Enumerate only the target PGID with bounded parsing/count/time; errors fail closed. |
| Trust boundary | Helper runs in the Trust-CI worker workspace path, not in untrusted checked-out code or isolated runner image. | No new runner capability, network edge, Docker socket access, credential path, or repository-command execution. |

The safe interpretation is Linux-specific: read target-PGID members from the same PID namespace's `/proc`, parse only kernel task state, and accept only a complete affirmative result that every remaining member is `Z`. Do not infer zombie status from PID existence, process name, PPID, elapsed time, or a host `/proc` view. A restricted/masked procfs is an explicit fail-closed deployment incompatibility, not an excuse to relax cleanup.

## Runner and M2 architecture implications

- This helper bounds local Git commands used to construct/validate the exact-SHA workspace. It is on M2 edge `EDGE-WORKER-WORKSPACE`: local OS/filesystem, no network, required correlation/idempotency, bounded retries, observable `SIG-WORKSPACE-FAILURE`, manual recovery.
- The repair changes only post-failure classification. It must not alter checkout SHA validation, Git environment sanitization, byte limits, argv, session isolation, workspace reset/source-mutation detection, worker retry policy, or the immutable read-only runner image.
- There is no consumer migration/version bump. Keep `engineering/contracts/openapi/trust-ci.v1.json` and signed approval/attestation envelopes unchanged unless a separate contract change is scoped.
- Do not add systemd units, Compose activation, deployment changes, external writes, or GitHub calls. Tests must not inspect runtime secrets, `.env`, host keys, or deployed worker configuration.

## Stacked base and external Trust-CI gates

The worktree is currently exactly at selected stacked base `9493741dd34fdfa1e37efdc09b35e30d5535be7c` (`milestone/m2-executable-architecture`); it is `HEAD`. The hotfix must remain an isolated descendant of that M2 head and its PR must target the intended M2 stack, not silently retarget `main`. Retarget/rebase changes verification inputs and needs fresh evidence.

For any hotfix commit, a new PR head SHA requires a new deployed GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run on that exact head. Local tests, receipts, and this report are only preflight evidence. The worker must continue exact base/head validation and source-integrity verification before it signs/publishes a result; cleanup success cannot mask checkout, policy, holdout, approval, runner, or source-mutation failure. If deployed policy requires external approval for `trust-ci/**`, stop for that cryptographic approval; no local grant can substitute.

## Required regression evidence

1. Exercise stdout cap, stderr cap, and timeout with a SIGTERM-ignoring same-session descendant that becomes zombie-only after SIGKILL; each reports the original cause and leaves no live survivor.
2. Exercise a live post-SIGKILL descendant and procfs read/parse/permission/membership uncertainty; each reports a survivor cleanup failure, not the original bounded failure.
3. Retain leader reaping, own-group refusal, ESRCH tolerance, byte caps, and Git sanitization tests; run the focused workspace suite before route verification.

## Sources inspected

- Active route and change package.
- `trust-ci/src/adaptive_trust_ci/workspace.py` and `trust-ci/tests/test_workspace.py`.
- M2 architecture/rules, Trust-CI Compose topology/contracts, `AGENTS.md`, and Trust-CI runner design documents.

