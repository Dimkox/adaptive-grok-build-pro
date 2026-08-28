# Test plan — Model Agnostic Autonomous Factory

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Typed package is red-risk, complete, schema-valid, evidence-mapped, and placeholder-free | `grok_spec validate`, map output, placeholder scan |
| P0 | Design contains all approved hard limits and no silent fallback/external-write/CoT loophole | self-review report and source scans |
| P0 | Canonical design and package agree on milestone order and trust separation | contradiction review |
| P0 | Planning diff contains no application code, external action, systemd install, secret, or second package | diff/status/scope review |
| P1 | Markdown formatting, links, and repository structure remain valid | `git diff --check`, focused structure tests, PR-mode local verification |
| P0 | Agent-authored rule cannot become active; expired/revoked rules do not influence handoff | focused M3 lifecycle tests |
| P0 | M3 handoff binds governance/architecture/evidence/exact SHAs with its exact closed v1 shape | focused M3 contract tests |
| P0 | Concurrent PostgreSQL claims enforce one lease, fences, 20/10/1 capacity, reclaim, and dead-letter | one real PostgreSQL M4 exit run |
| P0 | Duplicate/stale intake, budgets, kill switches, audit, and reconciliation fail closed | M4 service/PostgreSQL tests |
| P0 | Unix-socket API requires scoped auth, idempotency/correlation, redacts secrets, and exposes no execution/external-write operation | M4 API contract/security tests |

## Automated checks

- Unit: run only focused M3/M4 modules during red-green iterations.
- Integration: run the complete real-PostgreSQL concurrency/restart group once after the M4 store is complete.
- Contract: validate `change-spec.yaml`; inspect protocol and exact-state design invariants against all analysis reports.
- E2E: M4 ends at authenticated intake/control/recovery; provider, workspace, systemd, bot deployment, isolation, and semantic-repair E2E remain later gates.
- Static analysis: placeholder/scope/security scans, `git diff --check`, and repository quality profile.

## Manual checks

- Verify branch and changed-file set before commit.
- Confirm five analysis reports and design self-review exist.
- Confirm no credential, secret, or raw reasoning entered the design.
- Confirm the existing `scoped -> approved` state transition remains byte-for-byte preserved while later user scope expansions are recorded in the Markdown package history.
- Confirm both plans contain no placeholders and use consistent M1/M2/M3 handoff types.
- Confirm no `.env`, credential, Telegram token, or token-bearing URL enters repository evidence.

## Reduced repetition policy

During implementation, run focused tests for the changed task only. Run one full repository verifier on the final M3 product fingerprint and one on the final M4 product fingerprint; report-only/evidence commits do not trigger redundant full suites. A product repair invalidates the prior verifier and gets one replacement final run after all repairs.
