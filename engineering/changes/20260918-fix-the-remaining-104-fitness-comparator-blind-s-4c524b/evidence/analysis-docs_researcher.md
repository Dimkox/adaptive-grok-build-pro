# Documentation investigation — remaining #104 OpenAPI comparator gap

## Finding

The residual is documented as known and intentionally deferred, but it does **not** have a standalone ADR/design decision covering support for the reachable OpenAPI `$ref` closure. The durable records that do name it are the public #104 issue corrections and PR #112's own change package. The earlier repository-wide note in `decisions.md` describes the original object-enum limitation and review boundary; it predates #112 and does not describe the current `anyOf`/reference-closure gap.

## Current contract and implementation semantics

- `architecture/rules.yaml` applies `FIT-OPENAPI-BIDIRECTIONAL` to OpenAPI contracts. JSON Schema contracts are checked under both `FIT-CONSUMER-CONTRACTS` (`consumer_accepts_old`) and `FIT-GOVERNANCE-HANDOFF-COMPATIBILITY` (`producer_accepted_by_old`).
- The architecture analyzer intentionally uses a closed supported subset and returns `unsupported` when an applicable construct cannot be analyzed; fitness treats `unsupported` as a gate failure. The merged #112 change extended that subset only for bounded opaque JSON values in `enum`; it did not change composition or reference resolution.
- The #112 change package's brief and AC-004 explicitly record that editing the capability schema still fails end-to-end because the dependent failover OpenAPI reaches `landing-attempt-status.v1`, whose `anyOf` constructs remain outside the subset. It also records the separate producer-compatibility verdict for adding a profile.
- The OpenAPI closure is not localized to one response/reference by the issue's latest measurement: removing the attempt operation's 200 response did not clear `unsupported`, and replacing `anyOf` with `oneOf` in the candidate schemas added further unsupported findings. The issue reports 17/27 JSON Schema contracts use top-level `$defs`; therefore adding only `anyOf` is not demonstrated sufficient. The actual trigger within the reachable closure remains unbisected in the cited measurement.

## Issue / PR evidence

- Issue #104's latest measurement (comment dated 2026-09-17) supersedes earlier, narrower explanations. It records the metadata-only capability edit, the persistent failover OpenAPI unsupported result, the failed localization probes, the `$defs` coverage count, and the still-separate producer-policy question.
- PR #112 is merged. Its description states that `$ref` handling and composition were untouched; the merged scope fixes only object-valued enum analysis. The change package `engineering/changes/20260916-add-support-for-bounded-opaque-enum-member-value-3d9627/brief.md` and `change-spec.yaml` correctly preserve that residual.
- `decisions.md`'s 2026-09-16 note about keeping the comparator closed records the pre-fix decision and the original options. It is historical context, not a current design for the remaining reference/composition support.

## Documentation gap / implementation implication

There is no ADR specifying the exact supported composition/reference semantics, cycle behavior, or bounded traversal rules for the OpenAPI-reachable schema graph. Existing issue/package prose is enough to prevent claiming #104 complete, but it is not a design contract for implementing resolver expansion. The active change should derive a bounded design from observed contracts and tests, then document its exact scope; do not assume that implementing `anyOf` alone closes the end-to-end finding. The profile-enumeration policy decision remains separate and is not resolved by analyzer support.

Sources inspected: `gh issue view 104`; `gh pr view 112`; `architecture/rules.yaml`; `.grok-stack/adaptive_grok/architecture.py`; `engineering/changes/20260916-add-support-for-bounded-opaque-enum-member-value-3d9627/{brief.md,change-spec.yaml,evidence/review-response.md}`; `decisions.md`.
