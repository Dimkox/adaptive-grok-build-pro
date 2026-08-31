# Requirements — M2-A Executable Architecture

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001: strict schemas/loader/semantic validation and deterministic digests.
- [x] AC-002: truthful seed graph, real contract baselines, and repository/contract drift.
- [x] AC-003: deterministic CLI and five byte-reproducible Mermaid projections.
- [x] AC-004: every mandatory fitness category and monotonic post-diff risk.
- [x] AC-005: architecture-bound verification/receipts and staleness without M1 regression.
- [x] AC-006: read-only existing-target planning, atomic absent-target materialization, architecture-authority exclusion, and K16 decorative-only documentation.
- [ ] AC-007: exact-fingerprint verification/reviews, no `trust-ci/**` diff, frozen M2-B contract.

AC-001 through AC-006 are source-backed by the tests mapped in `change-spec.yaml`. AC-007 remains open until the coordinator runs final verification and all five independent route reviews on one unchanged fingerprint and records fresh receipts.

## Frozen source contract

- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`.
- Architecture ID: `ARCH-ADAPTIVE-GROK-M2`.
- Composite architecture digest: `d2f31484721c02d7ae0dcd2faa8519a6d20cb23da10de7378ed02fd1a293061b`.
- System digest: `da6453d9bbb291b297a393ff3d63fb68a0f3ec120107b6ed2cac4ee5a2d6e72b`.
- Rules digest: `2d42ca7373cebd4bf954bcfe1bdb784688df8665d08c4dce2b13de536abee69e`.
- Composite schema digest: `c702531d97283ba01fdebe79081081b96095631a89cf91e4cf128cc2574456f0`.
- Contract inventory digest: `039feea9a076516e3dd414c8e59bc2a2eeb522e2ca19a9087438b7ec7314e017`.

Exact final head, architecture evidence digest, and repository fingerprint are intentionally not predeclared here: coordinator-owned final verification/reviews must bind them after the last repository write.

## Failure and edge cases

- Ambiguous, malformed, oversized, unsafe, unsupported, or partially missing adopted architecture fails closed.
- The single adoption base may have both model files absent; later absence is invalid.
- Unsupported applicable contract/language/SQL semantics fail and require architecture review.
- `not_applicable` is engine-derived with inventory evidence and is revoked by a newly matching artifact.
- A dirty tree is diagnostic only and cannot be labelled exact-SHA evidence.
- Diagram render/check never mutates repository paths; render returns the bounded artifact payload and check compares no-follow.
- Package-relative queue adapters resolve according to Python module/package semantics; relevant ambiguity and analysis ceilings are `unsupported`, while unproven common method names remain non-queue.
- Queue control-flow and container values use a bounded abstract interpreter with commutative, associative, idempotent joins; fitness and `new_queue` risk share its exact result.
- Installer planning never mutates a target or executes dependency advice. Materialization requires an absent target and fail-closed no-replace publication; `--force` is rejected.
- If a constructor gap leaves original staging-entry ownership unprovable, preserve the unresolved name and emit `manual cleanup required: installer ownership is unresolved`; a later same-name lookup is never deletion authority.

## Non-functional requirements

- Security: no executable rule language, network fetch, target import, secret value, approval creation, or external capability.
- Reliability: canonical bytes, deterministic sorting, exact base/head and current-fingerprint binding, read-only existing-target planning, and verified atomic new-target publication.
- Performance: explicit byte/count/depth/finding/AST/output bounds.
- Observability: stable finding/reason/trigger IDs, per-category results, inventory/diff/evidence digests.
