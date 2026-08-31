# Test plan — Fix Trust CI bounded workspace process cleanup in the immutable read-only runner: zombie-only descendants after SIGKILL must not mask the original stdout/stderr/timeout failure, while live or uncertain survivors remain fail-closed. Deliver as an isolated stacked Trust-CI-only bugfix on M2 with regression tests.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Zombie-only post-KILL group preserves stdout, stderr, and timeout errors | focused workspace regression |
| P0 | Live survivor remains `bounded process group survived SIGKILL` | focused workspace regression |
| P0 | Uncertain procfs observation fails closed | focused workspace regression |
| P0 | Direct bounded procfs classifier accepts all-Z target PGID records only | deterministic mocked `scandir`/`open`/`read` unit tests |
| P0 | Direct classifier rejects X/other live states, malformed/truncated/oversized records, open/read failures, caps, deadlines, and uncertain final probes | deterministic mocked procfs unit tests |
| P1 | Existing descendant cleanup, leader reap, own-group refusal, and ESRCH race behavior | `trust-ci/tests/test_workspace.py` |
| P1 | Frozen-adoption receipt binding remains deterministic for a later stacked hotfix | `tests/test_change_receipts.py` |

## Automated checks

- Unit: focused `PostKillProcessGroupClassifierTests` and `WorkspaceStreamingTests`, full `trust-ci/tests/test_workspace.py`, and the frozen-adoption receipt binding test.
- Integration: digest-pinned read-only runner execution where available.
- Contract: no public contract change; validate the v2 change spec.
- E2E: route verifier and final independent review receipts.
- Static analysis: Ruff with a writable temporary cache and `git diff --check`.

## Manual checks

- Capture RED before production implementation and final GREEN commands/results in `evidence/`.
