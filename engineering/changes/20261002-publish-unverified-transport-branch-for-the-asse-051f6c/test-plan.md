# Test plan — Publish unverified transport branch for the assembled 2.1.0 release candidate; no merge tag or release

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Full repository PR verification on the exact candidate | `python3 scripts/grok_verify.py --mode pr` |
| P0 | Migration 024/025 identity and PostgreSQL restart/dispatch behavior | verifier factory/PostgreSQL checks |
| P1 | U5 prediction contracts and U6 deterministic FPF snapshot | focused factory tests plus full verifier |
| P1 | Release truth, package/state lockstep and U4 exclusion | structure/project-state/manifest/package tests and release review |

## Automated checks

- Unit: prediction contracts, FPF snapshot, result dispatch/client/server.
- Integration: disposable PostgreSQL/restart suite selected by the verifier.
- Contract: JSON schemas, semantic/landing inventories, architecture ownership.
- E2E: exact-head external Trust CI after PR creation.
- Static analysis: verifier-selected Ruff, architecture and diff checks.

## Manual checks

- Confirm remote PR head SHA, required check name, branch base and preservation count for dirty worktrees.
