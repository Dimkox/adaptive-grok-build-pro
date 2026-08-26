# Requirements — M2-A Executable Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001: strict schemas/loader/semantic validation and deterministic digests.
- [ ] AC-002: truthful seed graph, real contract baselines, and repository/contract drift.
- [ ] AC-003: deterministic CLI and five byte-reproducible Mermaid projections.
- [ ] AC-004: every mandatory fitness category and monotonic post-diff risk.
- [ ] AC-005: architecture-bound verification/receipts and staleness without M1 regression.
- [ ] AC-006: safe installer delivery and K16 decorative-only documentation.
- [ ] AC-007: exact-fingerprint verification/reviews, no `trust-ci/**` diff, frozen M2-B contract.

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
