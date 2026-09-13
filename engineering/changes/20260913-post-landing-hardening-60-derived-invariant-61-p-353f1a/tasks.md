# Tasks

- [x] AC-001 derived contract-inventory invariant
- [x] AC-002 production prohibited-member enforcement
- [x] AC-003 real PDF worker execution tests
- [x] PROJECT_STATE landed sync
- [ ] full verification receipt
- [ ] code/test/security/release review receipts
- [ ] PR + exact-head gate + merge

## Review follow-ups (recorded, not in this PR)
- code-review: `seal()` builds member tuples from raw `DEPLOY_MEMBERS` and never calls `deploy_members_for_source`; a poisoned constant would be packaged and only rejected downstream. Route `seal()` through the resolver in a security-sensitive PR.
- code-review §5: duplicate-id guard `len(records)==len(declared_ids)` added (fixed in-PR).
- test-review: `_pypdf_pinned()` now probes the isolated child, not the parent (fixed in-PR).
- issue #61 residual: `deploy_inventory_policies` fitness rule (design at /tmp/release-sync/fitness-rule-design.md) — a rules.yaml+architecture.py+architecture_fitness.py registration, own PR.
- issue #63 residual: `resources/landing_pdf_worker.py` still has no COVERAGE-counted execution (child is an uninstrumented subprocess); parser-present tests skip unless pypdf 6.18.1 is importable by the isolated child, which the current runner image is not.
