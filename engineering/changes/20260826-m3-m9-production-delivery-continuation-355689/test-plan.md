# Test plan — M3-M9 production delivery continuation

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | | |
| P0 | Agent attempts to activate/self-review governance | Lifecycle and fitness tests fail closed |
| P0 | Unsafe, duplicate, mutated, stale, or unknown input | Schema/loader/handoff tests reject it |
| P0 | M3 change weakens Trust CI or adds runtime/external capability | Architecture/security review rejects diff |
| P1 | Governance digest or architecture/SHA changes | Receipts become stale |
| P1 | Installer targets an existing project | Engine/schemas install; target registries are preserved |

## Automated checks

- Unit: task-focused M3 unittest classes after each task.
- Integration: governance/architecture/receipt/installer focused suite.
- Contract: strict registry and exact handoff schema tests.
- E2E: one final `python3 scripts/grok_verify.py --mode pr` on the final fingerprint.
- Static analysis: `git diff --check`, secret/path/network boundary inspection.

## Manual checks

- Route-selected code, test, security, and release reviewers inspect the identical final SHA/fingerprint.
