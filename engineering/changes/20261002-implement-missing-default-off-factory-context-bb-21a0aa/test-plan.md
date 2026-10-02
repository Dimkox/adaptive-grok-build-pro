# Test plan — Implement missing default-off factory context BB contracts rotator registry hardened VibeVM store and Linux setup manager source contours with tests while preserving migrations 023 through 025

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Feature contract/store/installer suites | focused unittest modules |
| P0 | Migration 023-025 preservation | migration/PostgreSQL/restart checks |
| P1 | Installer materialization and architecture truth | installer/structure/architecture tests |
| P1 | Aggregate compatibility | full PR verifier |

## Automated checks

- Unit: focused BB, FPF, rotator, prediction, VibeVM, installer, Linux adapter, and offline-builder tests.
- Integration: installer materialization, state/manifest lockstep, and disposable PostgreSQL verifier lane.
- Contract: schemas, default-off/no-authority behavior, exact pins, and migration identity.
- E2E: full exact-head PR verifier and external Trust CI remain delivery gates.
- Static analysis: architecture validation, generated-view check, secret scan, and diff check.

## Manual checks

- Independent reviewers ran bounded mutation probes in private scratch trees; reports are under `evidence/`.
