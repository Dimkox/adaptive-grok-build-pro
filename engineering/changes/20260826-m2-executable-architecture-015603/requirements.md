# Requirements — M2-A Executable Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001: strict schemas/loader/semantic validation and deterministic digests.
- [x] AC-002: truthful seed graph, real contract baselines, and repository/contract drift.
- [x] AC-003: deterministic CLI and five byte-reproducible Mermaid projections.
- [x] AC-004: every mandatory fitness category and monotonic post-diff risk.
- [x] AC-005: architecture-bound verification/receipts and staleness without M1 regression.
- [x] AC-006: safe installer delivery and K16 decorative-only documentation.
- [ ] AC-007: exact-fingerprint verification/reviews, no `trust-ci/**` diff, frozen M2-B contract.

AC-001 through AC-006 are source-backed by the tests mapped in `change-spec.yaml`. AC-007 remains open until the coordinator runs final verification and all five independent route reviews on one unchanged fingerprint and records fresh receipts.

## Frozen source contract

- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`.
- Architecture ID: `ARCH-ADAPTIVE-GROK-M2`.
- Composite architecture digest: `ca97384dd1ceb33547ef6de0b38fc04a3dcbdb8648ce0a278f764bec11c562bc`.
- System digest: `f8eeaf182b9f59fe33dd2c238e5147431569257f0a9ccdf7430bdee12b852847`.
- Rules digest: `b47a0ed9f4f82894ad7b0e713749a349c4b98703cbc6f93f64e8a156d671a4e4`.
- Composite schema digest: `c702531d97283ba01fdebe79081081b96095631a89cf91e4cf128cc2574456f0`.
- Contract inventory digest: `039feea9a076516e3dd414c8e59bc2a2eeb522e2ca19a9087438b7ec7314e017`.

Exact final head, architecture evidence digest, and repository fingerprint are intentionally not predeclared here: coordinator-owned final verification/reviews must bind them after the last repository write.

## Failure and edge cases

- Ambiguous, malformed, oversized, unsafe, unsupported, or partially missing adopted architecture fails closed.
- The single adoption base may have both model files absent; later absence is invalid.
- Unsupported applicable contract/language/SQL semantics fail and require architecture review.
- `not_applicable` is engine-derived with inventory evidence and is revoked by a newly matching artifact.
- A dirty tree is diagnostic only and cannot be labelled exact-SHA evidence.

## Non-functional requirements

- Security: no executable rule language, network fetch, target import, secret value, approval creation, or external capability.
- Reliability: canonical bytes, deterministic sorting, exact base/head and current-fingerprint binding.
- Performance: explicit byte/count/depth/finding/AST/output bounds.
- Observability: stable finding/reason/trigger IDs, per-category results, inventory/diff/evidence digests.
