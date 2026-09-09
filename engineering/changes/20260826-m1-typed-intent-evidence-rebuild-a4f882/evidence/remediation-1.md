# Remediation 1 — blocked M1 reviews

The four `review-*.md` reports in this directory are preserved as historical evidence for reviewed HEAD `62b9c601de980b1e06cf78bd69e02c4847c7e2de`; their `BLOCKED` verdicts have not been rewritten or converted into receipts.

## Source repairs

- The independent stdlib holdout now validates the nested v2 contract, exact evidence scalar types, approvals, contracts, rollback bounds, signal-to-objective references, exact SHA/diff/deletion/multi-spec/downgrade behavior, resource limits, and no-follow ancestor traversal.
- Trusted metadata extraction now rejects malformed JSON/evidence and cross-spec duplicate criterion IDs before commands run. Those cases produce a deterministic signed failed attestation with empty coverage instead of false mapped coverage or an `AttestationPayload` exception.
- Contract fingerprints hash a bounded regular file through no-follow descriptor-relative traversal, closing ancestor-symlink and path/open TOCTOU gaps.
- Receipt and verification regressions cover all receipt kinds, explicit-binding mismatch, legacy insufficiency, contract/base/HEAD staleness, active-plus-changed selection, v1 downgrade rejection, draft/gate separation, and the exact docs-micro exemption.
- Signed metadata is covered through runner success/failure/replay, field tampering, and a committed public-only pre-M1 golden envelope. PostgreSQL integration remains skipped when `TRUST_CI_TEST_DATABASE_URL` is unavailable; no database evidence is simulated.

## Local verification before fresh review

- Root unit suite: 221 passed.
- Trust CI suite: 169 passed, 8 skipped because PostgreSQL was not configured.
- Compileall: passed.
- PR verification with `--no-record`: passed, active red-risk spec gate-valid with 6/6 mapped criteria.

No passing verification or review receipt was created. Fresh independent review must inspect the final committed tree before Task 6, AC-006, or source-ready status can complete; deployed holdout/worker/policy activation remains explicitly incomplete.
