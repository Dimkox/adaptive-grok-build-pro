# Requirements — M1 Typed Intent Evidence Rebuild

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

AC-001 through AC-006 are implemented and locally source-ready. Exact source HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a` passed the complete local verification set and all four route-selected wave-7 reviews; the later package closure changes evidence/docs/state only and does not change the reviewed product source.

- [x] AC-001: strict schema and semantic validation fail closed for malformed, ambiguous, duplicate, stale, or incomplete typed specs.
- [x] AC-002: new packages are generated deterministically from route facts and Markdown cannot override typed authority.
- [x] AC-003: CLI and local receipts expose deterministic digest, coverage, criterion IDs, and fingerprint staleness.
- [x] AC-004: the external holdout source independently enforces critical invariants without importing PR-controlled validator code.
- [x] AC-005: Trust CI source signs deterministic spec digest and coverage while retaining verification compatibility for existing schema-v1 attestations.
- [x] AC-006: exact source HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a` passed 223/223 root tests, compileall, exact-SHA holdout validation, PR verification, and code/test/security/release wave-7 reviews. A later authorized isolated run passed PostgreSQL integration 10/10 and the full Trust CI suite 200/200 with no skips; this remains local evidence, and no local receipt or external authority is inferred from it.

## Failure and edge cases

- Duplicate JSON keys, non-finite numbers, trailing data, excessive size/depth/count, traversal, symlinks, and non-regular files fail closed at the trust boundary.
- Unchanged legacy specs are not blocked or mass rewritten.
- A changed signed payload format must not invalidate verification of already stored signatures.
- Malformed spec bytes may be hashed for provenance but cannot be treated as mapped evidence.

## Non-functional requirements

- Security: no PR-controlled Python executes in trusted metadata extraction; no secrets or payload contents are logged.
- Reliability: deterministic canonicalization, stable sorting, and exact base/head binding.
- Performance: bounded reads and bounded recursion; no new runtime dependency.
- Observability: stable SIG identifiers and explicit unmapped criterion IDs.
