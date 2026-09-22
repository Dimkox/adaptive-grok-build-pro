# Requirements — Release v2.0.19 from candidate 5d93fc3

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given the exact candidate tree, when release-sync metadata is updated, then all product identity surfaces and coupled tests name `2.0.19`, while `v2.0.18` publication facts and bytes remain unchanged.
- [ ] Given the post-`v2.0.18` source history, when the release record is updated, then each included merge/head/check identity is explicit and the pending artifact slot claims no `v2.0.19` bytes.
- [ ] Given a merged release-sync tree, when `package_stack.py` runs twice against the sealed source, then the ZIP and sidecar bytes and digests match exactly.
- [ ] Given the artifact-child exact merge, when publication is authorized, then tag `v2.0.19` targets that commit and the GitHub Release carries both assets.
- [ ] Given any missing or stale check/grant, when the controller reaches the publication boundary, then it stops without tag, release or deployment.

## Failure and edge cases

- A new commit, changed base, changed deployed policy or changed holdout invalidates the external check and requires a fresh gate.
- A package digest mismatch blocks publication and leaves `v2.0.18` as the rollback release.
- Local receipts and grants are workflow evidence only and cannot substitute for Trust CI authority.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: PR-only delivery, exact-SHA Trust CI, immutable release artifacts.
- Canonical-example deviations and evidence: none; the v2.0.18 R/A chain is the precedent.
- Intentional debt created, repaid, or accepted: none; external pilot/M8/M9 qualification remains explicitly outside this release.

## Non-functional requirements

- Security: no secrets or production host data in source or package; security review is independent of implementation.
- Reliability: retain prior release and fail closed on stale identity or digest mismatch.
- Performance: one final verifier and bounded packaging; no repeated empty polling.
- Observability: record exact SHA, tree fingerprint, package digests, check name/run and publication target.
