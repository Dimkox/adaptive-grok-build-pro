# Final data and contract review — M2-A

## Reviewed identity

- Route: `0156034c05bd`
- Change: `20260826-m2-executable-architecture-015603`
- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Reviewed head: `99de2f9757400f7394b7a9e2c46b3ebce939e438`
- Reviewed head tree: `bae34faabdf968396e393d40f7219d3bbf5a60b5`
- Exact diff package: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-25bfbe5..99de2f9.diff`
- Diff package SHA-256: `385aef31d68d78ce9f68b824900bba01d9980e66bf5370897cda77b2dac49a01`

## Verdict

**FAIL — 0 Critical, 2 Important, 0 Minor.** PASS requires zero Critical or Important findings.

## Findings

### Important 1 — Added contracts bypass supported-semantics validation, so exact contract fitness reports an optimistic pass

The compatibility evaluator explicitly says it applies to added, removed, or changed contracts, but for every added contract it returns early without invoking the kind-specific comparator (`.grok-stack/adaptive_grok/architecture_fitness.py:408-458`, especially lines 431-434). The exact adoption-base-to-head result therefore reports `contract_compatibility=pass` with no finding for all four newly declared contracts.

That pass is false for the frozen OpenAPI baseline under the implementation's own supported subset. `_supported_content()` accepts exactly one `application/json` media type (`.grok-stack/adaptive_grok/architecture.py:1097-1107`), while the declared baseline contains `text/plain` and a two-media-type webhook body (`engineering/contracts/openapi/trust-ci.v1.json:364,422`). The committed test confirms that comparing the current OpenAPI record with itself is `unsupported` (`tests/test_architecture_model.py:991-997`). An exact-head probe reproduced the contradiction: `openapi_self=unsupported` while `exact_contract_fitness=pass` with empty findings.

This violates AC-004 and the frozen fail-closed rule that unsupported applicable contract constructs produce `unsupported`, never an optimistic pass (`change-spec.yaml:19-21`; design lines 121-123). It also means a newly added malformed or unsupported JSON Schema/OpenAPI baseline can be blessed as compatible merely because no prior record exists.

Required repair: validate every added contract against the comparator's supported baseline semantics before returning pass. For OpenAPI, either implement bounded comparison for the actually frozen media-type surface or split the explicitly comparable contract surface from non-comparable inventory; unsupported additions must emit `unsupported` and fail. Add a regression that introduces an unsupported contract at a bootstrap/adoption base and asserts overall failure.

### Important 2 — Repository path ownership is ambiguous and the seed model already contains a duplicate owner

System semantic validation checks path syntax but never checks duplicate or overlapping ownership across nodes (`.grok-stack/adaptive_grok/architecture.py:360-411`). The canonical seed assigns the exact same path, `trust-ci/compose.yaml`, to both `NODE-TRUST-CI-WORKER` and `NODE-DOCKER-ENGINE` (`architecture/system.yaml:496-515,548-565`). An exact-head inventory probe reproduced that duplicate.

Downstream ownership resolution does not fail closed: `_owner_for_path()` selects the longest match and silently returns one node; equal-length matches are resolved by list order (`.grok-stack/adaptive_grok/architecture_fitness.py:724-731`). Consequently a repository path can have two incompatible node types, trust/data classifications, runtime facts, secrets, or network policies while validation/drift remains green, and owner-sensitive fitness is bound to an arbitrary normalized node order. This contradicts AC-001/AC-002's resolved stable identities and truthful source-boundary drift contract (`change-spec.yaml:3-11`).

Required repair: define repository ownership semantics and reject ambiguous exact/overlapping ownership during system semantic validation, or model shared manifests through one explicit repository/config node with directed relationships to the described runtime nodes. `_owner_for_path()` must reject ties rather than choose by ordering. Add exact-duplicate and equal-specificity overlap regressions, including owner-sensitive network/source fitness.

## Evidence checked

- The repository was exactly at the reviewed head before this report was written; only other route reviewers' untracked reports were present.
- `git merge-base` equals the adoption base. The exact base/head changed-path set contains no `trust-ci/**` path and no SQL file.
- Canonical model validation and repository drift both returned success with no findings.
- Focused architecture suites passed: `84` tests in `76.306s`.
- The typed change-spec gate passed with all `7/7` criteria mapped.
- Exact digests match the frozen package: architecture `ca97384dd1ceb33547ef6de0b38fc04a3dcbdb8648ce0a278f764bec11c562bc`, system `f8eeaf182b9f59fe33dd2c238e5147431569257f0a9ccdf7430bdee12b852847`, rules `b47a0ed9f4f82894ad7b0e713749a349c4b98703cbc6f93f64e8a156d671a4e4`, schema `c702531d97283ba01fdebe79081081b96095631a89cf91e4cf128cc2574456f0`, contract inventory `039feea9a076516e3dd414c8e59bc2a2eeb522e2ca19a9087438b7ec7314e017`.
- Exact fitness records migration safety as `not_applicable`, with the declared `trust-ci/sql` inventory bound, while retaining `new_datastore` and the `data` approval scope. No migration/database/backfill/external-state mutation exists in this range, and rollback/no-migration claims are truthful.
- The checked-in Trust CI API/envelope/projection baselines were compared with the existing `trust-ci/src` implementations for route/status/authentication and payload-field truth. No `trust-ci/**` source mutation occurred.

## Residual risks and disclaimer

The current OpenAPI baseline truthfully inventories non-JSON endpoints, but those surfaces are deliberately outside the current compatibility subset; after the repair above they must remain fail-closed or be given bounded semantics. The directional compatibility values stored on individual signed-payload contract records differ from the kind-wide `exact` enforcement rule; this is stricter today, but the authoritative relationship between record-level and rule-level modes should be documented and semantically validated to prevent future divergence.

This is repository-local review evidence only. It is not merge authority, does not establish M2-B or deployed independent enforcement, and does not replace the App-owned policy-epoch exact-SHA Trust CI check or required human-signed approvals.
