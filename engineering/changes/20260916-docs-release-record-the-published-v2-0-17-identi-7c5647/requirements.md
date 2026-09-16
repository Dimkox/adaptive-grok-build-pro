# Requirements — v2.0.17 published-release successor

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC-001: `published_release` names v2.0.17 with PR #99, checked head, merge commit, tree, tag object, artifact and sidecar digests, App check run and attestation id, all re-derived from the remote.
- [x] AC-002: `prior_published_releases` grows by exactly one unchanged v2.0.16 record (four entries: v2.0.16, v2.0.15, v2.0.14, v2.0.13).
- [x] AC-003: `local_candidate` is the published record; `reviewed_product_head/tree` stay null and `operational_activation` stays false.
- [x] AC-004: every current-state surface reads as published and none claims installation, activation or deployment.

## Failure and edge cases

- A test literal left on the candidate wording while the record says published (or the reverse) breaks lockstep: the four modules must pass on the frozen tree.
- Re-stamping an older release's identity or dropping it from history is a forbidden outcome, not a tidying preference.
- The local verifier still refuses to analyse the tracked >10 MB ZIP (issue #80); disclosed, and the App-owned exact-head check remains authority.

## Governance context

Canonical governance JSON under `governance/` stays separately reviewed authority; this commit restates no governance digest as current.

- Applicable rule IDs: release-governance (immutable published releases), documentation currency.
- Intentional debt created, repaid, or accepted: repaid — the pending-candidate wording is removed instead of left stale.

## Non-functional requirements

- Security: no credential, key, host mutation or machine-local secret in the diff; the dossier carries only values already published on `main`.
- Reliability: no runtime is touched; `operational_activation` false.
- Observability: recomputable digests plus the exact-head App check.
