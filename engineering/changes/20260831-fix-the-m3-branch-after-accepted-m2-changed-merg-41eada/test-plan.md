# Test plan — Fix the M3 branch after accepted M2 changed: merge exact M2 head 022411b05924618cfde0cb97b8c8aff4955e6013 into M3, resolve integration conflicts without changing M3 requirements, add or update regression tests if needed, run verification and reviews, and prepare PR #11 for fresh exact-SHA Trust CI; no external writes without exact delegated grants.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Exact M2 ancestry and two-parent merge provenance | `git show`, `git merge-base --is-ancestor` |
| P0 | M2 workspace cleanup accepts only proven all-zombie post-SIGKILL groups | `trust-ci.tests.test_workspace` |
| P0 | M2 packaging, source-invariance, safe-directory, exact-base receipt behavior survives | manifest/package, architecture-fitness, change-receipt tests |
| P0 | M3 governance schemas/lifecycle/handoff/fitness and receipt invalidation survive | governance, governance-fitness, architecture, receipt tests |
| P1 | Architecture model/rules and generated diagrams remain deterministic | architecture CLI validate/diagram checks |
| P1 | Full routed quality profiles and independent reviews bind one fingerprint | verifier and review receipts |

## Automated checks

- Unit: workspace, manifest/package, architecture model/fitness, governance, receipt suites.
- Integration: installer, structure, verification-doctor, exact-base handoff flows.
- Contract: architecture/governance schemas and unchanged OpenAPI inventory via full verifier.
- E2E: no browser/runtime E2E surface changes; repository CLI verification is the critical path.
- Static analysis: full `python3 scripts/grok_verify.py --mode pr`.

## Manual checks

- Inspect merge parents and ancestry against the exact accepted M2 SHA.
- Inspect diff/conflict resolutions for only intended semantic unions and stale README claims.
- Confirm no external write, deployed-policy change, secret access, or historical receipt rewrite occurred.
