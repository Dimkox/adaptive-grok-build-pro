# Test plan — Repair L5 current landing source binding

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Current source pin, protected stylesheet, exact two-path candidate | `test_landing_renderer.py`, `test_landing_api.py` |
| P0 | Complete deterministic 20-member artifact and source provenance | `test_landing_artifact.py` |
| P1 | OpenAPI patch identity and unchanged v1 operation/schema surface | `test_landing_contracts.py` |
| P1 | Existing intake/provider identities remain deterministic | `test_landing_intake.py`, `test_landing_provider.py` |

## Automated checks

- Unit: targeted renderer source-surface reject/accept matrix.
- Integration: hermetic exact-Git workspace and artifact sealing twice.
- Contract: OpenAPI `1.0.1`, new SHA/tree, unchanged v1 operations/responses.
- E2E: local TestClient stale/current pin behavior; no live system.
- Static analysis: targeted Ruff/Bandit for modified Python, then exactly one
  `python3 scripts/grok_verify.py --mode pr` on the frozen committed tree.

## Manual checks

- Confirm landing worktree HEAD/tree/status are unchanged and published
  `v2.0.14` ZIP/sidecar checksums remain frozen.
- Run no provider, publisher, deployment, hosting, DNS, or live-site action.
