# Repository analysis — M2 Trust-CI workspace process cleanup

Route: `fa3ae6080deb`
Change: `20260831-fix-trust-ci-bounded-workspace-process-cleanup-i-fa3ae6`
Stacked base: `9493741dd34fdfa1e37efdc09b35e30d5535be7c`
Scope: read-only diagnosis; only this workflow-evidence report was added.

## Exact reproduction and root cause

The defect is in the trusted workspace command wrapper, not in the container
sandbox:

- Product: `trust-ci/src/adaptive_trust_ci/workspace.py`.
- Existing direct reproduction fixture:
  `trust-ci/tests/test_workspace.py::WorkspaceStreamingTests`
  `test_bounded_process_kills_sigterm_ignoring_descendants` (lines 355–381).

That test starts a leader which creates a descendant that ignores SIGTERM,
closes stdout/stderr, writes its PID, then sleeps. It drives three primary
failures: stdout overflow, stderr overflow, and timeout. The existing expected
primary exceptions are respectively `stdout byte limit`, `stderr byte limit`,
and `timeout`.

The first incorrect state is in the cleanup liveness predicate:

1. `_run_bounded_process` starts the Git subprocess as a new session/process
   group (`start_new_session=True`, lines 150–162).
2. On the original byte-limit/timeout exception it calls
   `_terminate_process` (lines 203–208).
3. `_terminate_process` correctly SIGTERMs and then SIGKILLs the *whole
   process group* (lines 119–132), rather than killing only the leader.
4. `_wait_for_process_group` decides that cleanup is complete only when
   `_process_group_exists` returns false (lines 102–117).
5. `_process_group_exists` uses `os.killpg(group_id, 0)` (lines 81–90). A
   group containing only a post-SIGKILL zombie may still satisfy that probe:
   it is not a live runnable survivor, but it has not yet been reaped by its
   parent/init. The function reports it as live.
6. After the one-second SIGKILL grace, `_terminate_process` raises
   `WorkspaceError('bounded process group survived SIGKILL')`. Because this is
   raised while handling the original exception, it masks the original bounded
   stdout/stderr/timeout error and its useful context.

This is an error-classification defect, not a missing group kill. The existing
group-kill sequence is required and must remain intact. Zombie-only remnants
must be accepted as post-kill cleanup success; any live process or inability to
classify the group must remain fail-closed.

## Minimal code and regression surface

| Path | Required role |
| --- | --- |
| `trust-ci/src/adaptive_trust_ci/workspace.py` | **Only product code target.** Refine `_process_group_exists` / `_wait_for_process_group` (or a small private status helper) so zombie-only post-SIGKILL group members do not count as live survivors. Preserve guards against worker's own process group, TERM then KILL ordering, bounded waits, leader reap, and fail-closed handling of permission/error/ambiguous status. |
| `trust-ci/tests/test_workspace.py` | **Regression-test target.** Extend `WorkspaceStreamingTests` with a deterministic zombie-only cleanup reproduction/assertion. Keep the current real descendant test as the behavior anchor and add explicit live/uncertain classification coverage if helper seams permit. |
| `trust-ci/src/adaptive_trust_ci/sandbox.py` | Not affected. It has a separate container-wrapper timeout path; this route explicitly says *workspace* cleanup and the existing reproduction is in `workspace.py`. |
| `trust-ci/tests/test_ops.py`, `trust-ci/tests/test_runner.py` | No direct bounded workspace-process coverage; do not broaden the repair here. |

The narrow regression should prove all of the following:

1. For each primary failure (stdout limit, stderr limit, timeout), a descendant
   that becomes zombie-only after SIGKILL leaves the original `WorkspaceError`
   intact rather than replacing it with `bounded process group survived SIGKILL`.
2. A runnable/non-zombie descendant after the same bounded TERM/KILL cycle still
   produces the existing fail-closed survivor error.
3. Missing permission, unreadable/malformed status data, or any other uncertain
   group-member observation remains fail-closed; it must never be silently
   classified as zombie-only.
4. The wrapper never signals/inspects the worker's own process group and does
   not introduce unbounded polling or host-wide cleanup.

Focused validation after the write owner adds the failing test and repair:

```bash
PYTHONPATH=trust-ci/src python3 -m unittest trust-ci.tests.test_workspace -v
python3 -m unittest tests.test_architecture_fitness -v
```

Then run the route-required `python3 scripts/grok_verify.py --mode pr` once on
the final product fingerprint, followed by the selected reviews.

## M2 stacked-base / isolation analysis

`HEAD` is exactly `9493741dd34fdfa1e37efdc09b35e30d5535be7c`, and the active
branch reports that commit as an ancestor. This is the M2 stacked baseline: it
contains `architecture/system.yaml`, `architecture/rules.yaml`, and the
architecture-fitness evaluator.

The source architecture maps `trust-ci/src/adaptive_trust_ci/workspace.py` to
`NODE-ISOLATED-RUNNER` in `TD-TRUST-CI-EXECUTION`. Its runner edges are
no-network filesystem paths with reject terminal actions. The repair preserves
those contracts: no HTTP/OpenAPI/event payload changes, no API consumer changes,
no database/schema changes, and no external write.

`architecture/rules.yaml` rule `FIT-TRUST-CI-SEPARATION` rejects a diff only
when it mixes one of the local implementation prefixes
(`.grok`, `.grok-stack`, `architecture`, `engineering/contracts`, `scripts`)
with `trust-ci/**`. The evaluator implements that exact two-sided condition in
`.grok-stack/adaptive_grok/architecture_fitness.py` lines 925–950. Limiting
product changes to:

```text
trust-ci/src/adaptive_trust_ci/workspace.py
trust-ci/tests/test_workspace.py
```

means the Trust-CI side is present and the local implementation side is absent,
so this isolated stacked hotfix passes the separation rule. The active change
package evidence is workflow evidence, not a product/architecture mutation.

## Risks and constraints

- Do not loosen the cleanup success condition to ignore every `killpg(..., 0)`
  success. Only an explicitly observed all-zombie group may be tolerated.
- Do not use an unbounded `ps` scrape, signal unrelated PIDs/groups, or inspect
  any credential/configuration file. Process inspection must be bounded,
  process-group-scoped, and fail closed on uncertainty.
- Preserve original exception causality/output semantics: cleanup is secondary
  when it can prove zombie-only remnants, but a live/unknown survivor is a
  containment failure and remains the reported error.
- No change is needed to public Trust-CI OpenAPI/schema contracts. The route's
  `api` domain derives from the repository contract inventory, not a requested
  API behavior change.
