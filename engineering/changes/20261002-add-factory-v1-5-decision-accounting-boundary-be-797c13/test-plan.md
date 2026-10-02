# Test plan — Add Factory v1.5 decision accounting boundary behavior from source commit 531089f to the PR2 persistence foundation: enforce bounded cost and duration values and exact persisted accounting invariants as a new feature slice, with regression tests and isolated PR delivery

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Cumulative cost at max and max+1 | Focused shared contract suite |
| P0 | Complete and estimated/incomplete overflow rejection | Focused shared contract suite |
| P1 | Cost completeness/scalar/currency/duplicate matrix | Factory + root discovery |
| P1 | Timing/parser characterization remains green | Factory + root discovery |
| P1 | Persistence/replay/fence regression | Full PR verifier and PostgreSQL exit gate |

## Automated checks

- Unit: both decision contract discovery modules.
- Integration: existing decision PostgreSQL persistence and restart coverage via full verifier.
- Contract: schema parity and semantic admission remain dependency-free.
- E2E: full `grok_verify.py --mode pr` on the final tree.
- Static analysis: ruff, bandit, architecture and governance through verifier.

## Manual checks

- Inspect final diff against source commit `531089f` and confirm unrelated hunks were not copied.
