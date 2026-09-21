# Requirements

- AC-001: gate-mode validation rejects unmapped AC, INV and FORBID; draft remains descriptive and AC-only v1 attestation semantics remain compatible.
- AC-002: route-declared local gates have explicit pending/approved/rejected/stale/invalid states, exact scope/action/resource bindings, and never replace an exact delegated grant or external Trust CI approval.
- AC-003: non-UTF-8 Git filenames preserve failing diff diagnostics and JSON serialization; strict subprocess decoding remains the default.
- AC-004: reviewers probe only private scratch, keep the reviewed candidate unchanged and report executed/unexecuted claims with identity and mutation outcomes.
- INV-001: current package checkpoints, nonmutating status, raw-path identity and ASCII-safe JSON remain intact.
- INV-002: no historical approvals or receipts are imported as authority.

Canonical governance JSON remains separately reviewed authority. This package is non-authoritative context until the verifier derives evidence. No canonical examples, debt entries or governance budgets change.

Important unresolved integration checks: pre-upgrade active packages without gate metadata; unsafe selected state/route inputs reaching the new gate status reader; actual later lifecycle integration. See test-plan.md.
