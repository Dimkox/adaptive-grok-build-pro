# Architecture analysis — bounded workspace zombie-only cleanup

**Route:** `fa3ae6080deb`
**Stacked base:** `9493741dd34fdfa1e37efdc09b35e30d5535be7c`
**Scope:** read-only product analysis; this report is workflow evidence, not merge authority.

## Architecture ruling

Approve a narrow internal repair in `trust-ci/src/adaptive_trust_ci/workspace.py` plus focused regression tests. It must preserve the trusted workspace wrapper's existing containment protocol—new process session, original-PGID ownership, `SIGTERM`, bounded grace, `SIGKILL`, bounded grace, and leader reap—and correct only the final liveness interpretation. There is no public API/event/schema/database/policy/holdout/image change and no need to alter `architecture/system.yaml` or `architecture/rules.yaml`.

The correct post-`SIGKILL` outcome is tri-state:

```text
group absent                         -> cleanup proven
group members positively all zombie  -> cleanup proven for this error path
any live member / uncertain evidence -> cleanup containment failure (fail closed)
```

A verified zombie-only group must allow `_run_bounded_process()` to re-raise the *already-classified* `WorkspaceError` (stdout byte limit, stderr byte limit, or timeout). A live or unclassifiable group must retain `WorkspaceError('bounded process group survived SIGKILL')` as the stronger containment failure. This fixes error masking without weakening cleanup safety.

## Current flow and root cause

`_run_bounded_process()` starts each trusted Git command with `start_new_session=True` and records the child PID as its isolated process-group ID (`workspace.py:150–162`). On an output-limit/timeout error, `_terminate_process()` signals the whole original group, waits 0.25 seconds, escalates to `SIGKILL`, waits one second, and reaps the leader (`:119–137`).

The bug is solely `_process_group_exists()` (`:81–90`): `killpg(pgid, 0)` reports existence while a killed descendant remains a zombie awaiting reaping. `_wait_for_process_group()` treats that as a survivor (`:102–117`); the post-KILL timeout therefore raises the cleanup error and masks the original bounded failure. Existing `WorkspaceStreamingTests.test_bounded_process_kills_sigterm_ignoring_descendants` supplies the direct resistant-descendant reproduction and establishes preservation requirements.

## Bounded implementation design

Keep `_process_group_exists()` as the initial, inexpensive group-presence probe and retain its rejection of the worker's own process group. Add a small private post-KILL classifier (or equivalent) used **only after** the existing post-KILL grace has not observed group absence:

1. Enumerate only numeric entries in `/proc` with a finite entry/read byte ceiling and deadline no later than the existing cleanup deadline. Do not use `ps`, shell commands, unbounded polling, or host-wide signalling.
2. Read each candidate's `/proc/<pid>/stat` defensively. Parse the final `)` delimiter before splitting the remainder, because `comm` can contain spaces/parentheses. Extract the process state and process-group field from the kernel stat format; malformed/truncated/non-numeric data is not evidence of a zombie.
3. Count only entries whose parsed process-group equals the original `pgid`. A vanished PID while opening/reading is an expected race and may be ignored because it is no longer a surviving member. Permission denied, an I/O error other than disappearance, malformed state, unsupported `/proc`, enumeration failure/limit/deadline, or inability to determine membership makes the result **unknown**, not zombie-only.
4. If an observed member is not `Z`, return live. Return zombie-only only if at least one matching member was observed and every matching member was positively parsed as `Z`; otherwise return unknown/absent as appropriate. A final group-presence probe can distinguish no members from a group that vanished between probes.
5. Never classify from `killpg(pgid, 0)` alone. It is an existence signal, not a liveness/state signal. Never ignore a failure to inspect `/proc` just because the original command was already failing.

This classifier must not expand privilege: `/proc` is evidence read from the worker host, contains no repository data, and must not be logged/persisted. It neither executes repository code nor changes the no-network, read-only, no-secret runner boundary.

## Safety invariants

- The worker's own process group remains uninspectable and unsignalable; keep both existing guards.
- `SIGTERM` then `SIGKILL` remains mandatory for a group that survives the TERM grace. Do not turn zombie recognition into a pre-KILL shortcut that could leave a live descendant.
- Cleanup has finite TERM grace, KILL grace, `/proc` scan size/time bounds, and leader-reap wait. Any exhausted bound is uncertain and fails closed.
- The original classified error is preserved only after post-KILL cleanup establishes *absence* or *all-zombie*. It is not preserved when cleanup detects a live or unknown survivor.
- The leader must still be reaped. A zombie-only descendant does not excuse an unreaped `Popen` leader or stream/selector cleanup regression.
- No PID/group external to the spawned original group is signalled. The fix adds observation only; it does not introduce a second kill strategy.

## Tests required before acceptance

The write owner should first add a deterministic failing regression, then make the narrow repair. Required focused checks:

1. A post-`SIGKILL` process group that is positively represented as zombie-only returns the original timeout error. The test fixture must clean up its helper on assertion failure.
2. Repeat or parameterize the same error-preservation assertion for stdout and stderr limits, so the repair cannot accidentally special-case timeout.
3. A matching non-`Z` member produces the existing fail-closed survivor error rather than the original command failure.
4. Permission denied, unreadable/malformed stat, unavailable `/proc`, or scan-limit/deadline paths produce the fail-closed survivor error. They must not be interpreted as an empty/zombie group.
5. Existing resistant-descendant cleanup, ESCRH race tolerance, own-group rejection, leader reap, successful command, and output-cap cases remain green.

The tests may mock the private `/proc` reader/classifier for deterministic status transitions and retain at least one real process-group regression. They must not depend on unbounded host-process enumeration or leave live/zombie probes behind. Focused commands are `PYTHONPATH=trust-ci/src python3 -m unittest trust-ci.tests.test_workspace -v` and `python3 -m unittest tests.test_architecture_fitness -v`; final route verification/reviews bind separately to the final tree fingerprint.

## Architecture fitness and trust-boundary separation

`architecture/system.yaml` assigns `trust-ci/src/adaptive_trust_ci/workspace.py` to `NODE-ISOLATED-RUNNER`, under `TD-TRUST-CI-EXECUTION`, with no secrets and no network. `EDGE-RUNNER-WORKSPACE` is already a no-network filesystem edge with `mode: fail_closed`, `max_retries: 0`, `terminal_action: reject`, and `SIG-RUNNER-FAILURE`. `FIT-UNTRUSTED-RUNNER-NO-SECRETS` remains unchanged. The repair refines local cleanup error classification only; it creates no node, edge, secret class, data flow, API contract, or policy change.

The change-separation evaluator only fails if a diff mixes `trust-ci/**` with the rule's local implementation prefixes (`.grok`, `.grok-stack`, `architecture`, `engineering/contracts`, `scripts`), as implemented in `.grok-stack/adaptive_grok/architecture_fitness.py:925–950`. Restrict product edits to `workspace.py` and `trust-ci/tests/test_workspace.py`; active change-package evidence does not change the declared architecture. Do not modify Trust CI policy/holdout/deployment material, architecture rules, or governance code in this stacked hotfix.

## Observability and rollback

Observable command behavior is sufficient for this slice: successful zombie-only classification retains the preexisting bounded timeout/stdout/stderr failure; live/unknown cleanup remains a redacted `bounded process group survived SIGKILL` workspace failure. Do not emit PID, process listing, raw command output, environment, repository SHA, or task identifiers as persistent telemetry. Existing `SIG-RUNNER-FAILURE` and `SIG-WORKSPACE-FAILURE` remain the architecture-level signals; no metric is required unless a new stable low-cardinality outcome counter is deliberately introduced and tested.

Deployment is not authorized or required. Rollback is one narrow, reviewed forward-fix/revert of the classifier and its regression test. It must never restore a variant that ignores group presence generally, treats `/proc` failure as safe, omits KILL/reap, weakens the immutable/read-only/no-network/no-secret runner, or changes Trust CI authority. No migration, data recovery, external write, push, or production action belongs to this task.

## Change-package gaps to close

The current typed spec is schema-v2 but incomplete: `UNKNOWN` objective metric/target and empty acceptance, invariant, forbidden-outcome, observability, and contract arrays cannot provide completion evidence. Before final verification, record stable criteria for original-error preservation and live/unknown fail-closed behavior, plus forbidden outcomes for weakening group containment or masking a cleanup failure without proof. Keep contract arrays empty only after explicitly documenting that no public contract changes. Complete the generated requirements, architecture, test, release, and rollback documents consistently with this bounded ruling.
