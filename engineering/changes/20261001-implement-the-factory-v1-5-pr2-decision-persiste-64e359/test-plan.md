# Test plan — Implement the Factory v1.5 PR2 decision persistence contour on current main: transplant the five existing decision persistence commits from the isolated branch, resolve bounded API and data persistence conflicts, preserve behavior and tests, and deliver the isolated candidate

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | JSON Schema closedness/parity and semantic admission split | dependency-free schema test |
| P0 | Atomic commit, replay/conflict, fencing and runtime privileges | PostgreSQL integration tests |
| P0 | Decision survives two PostgreSQL restarts unchanged | restart probe |
| P1 | 022→023/fresh migration and legacy caller compatibility | migration/service/API tests |

## Automated checks

- Unit: decision digest, timing and cost completeness.
- Integration: PostgreSQL atomicity, concurrency, identity binding, replay and restarts.
- Contract: JSON Schema structural validation plus native semantic admission.
- E2E: full `grok_verify.py --mode pr` on the final tree.
- Static analysis: route-selected ruff, bandit, architecture and governance checks.
- Architecture regression: Factory test files and the exact root decision shim are
  summed into one budget, and a synthetic 800001-byte union fails closed.

## Manual checks

- Confirm exact base, preserved five-commit behavior, bounded product diff and untouched unrelated worktrees.
