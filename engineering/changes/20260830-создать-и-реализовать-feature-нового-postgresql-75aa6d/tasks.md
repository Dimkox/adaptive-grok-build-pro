# Tasks — production-only human approvals

- [x] Collect all six route-selected analyses.
- [x] Freeze the user-approved staged design and fill the durable package, including validated typed change spec.
- [x] Record the user's explicit written-spec approval and single final production ceremony refinement.
- [x] Write and self-review the implementation plan: `docs/superpowers/plans/2026-08-30-production-only-human-approvals.md`.
- [x] Preflight the producer-consumer chain and map M2–M9 files, interfaces, tests, rollout, recovery, and final ceremony in the plan.
- [x] Add failing contract, provenance, migration and replay tests.
- [x] Implement the single-owner vertical slices from plan.
- [ ] Run full route verification and real PostgreSQL evidence.
- [ ] Complete code, test, security, data and release reviews on one fingerprint.
- [ ] Prove shadow/deny-only behavior locally; keep external migration, service, policy and production mutations pending while automated PR delivery remains signature-free.
- [ ] At final production go/no-go only, hand off exactly one human-signed `promotion:production` envelope followed by consume-once deploy and reconciliation; merge and attestation are already automated.
