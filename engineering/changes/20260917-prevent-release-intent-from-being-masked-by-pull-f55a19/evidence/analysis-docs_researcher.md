# Documentation research — release intent versus PR wording (#123)

## Finding

The documented delivery vocabulary is already clear and does not need a new intent label. `AGENTS.md` says product changes are delivered through an isolated branch and pull request, requires the App-owned exact-head Trust CI check for merge eligibility, and distinguishes exact delegated operational actions from signed security approvals and branch protection. `README.md` likewise calls delivery PR-only and says local receipts are preflight evidence while a human owns merge, tag, and production promotion. This means “open/prepare a PR” is the normal delivery mechanism and must not downgrade an independent release/deploy intent.

The router currently does have an ambiguity that docs cannot resolve: `INTENT_KEYWORDS.review` includes `pull request` and ` pr `, while `_best_intent()` checks `review` before `release`. Thus a prompt that mentions both release work and opening a pull request can classify as `review`, which does not add the release review floor or the `production_action_approval` route gate. The route context does expose `Human gates: ...`, so the status field is visible when correctly derived; the defect is upstream classification/gate derivation, not missing display text.

## Recommendation

Keep the existing vocabulary and PR-only contract. Repair classifier precedence or derive release intent independently so incidental PR-delivery wording cannot mask explicit release/deploy intent. Add regression cases for prompts combining release/deploy intent with “pull request” / “PR”, and assert both `release_reviewer` and `production_action_approval` are retained. Consider a separate negative case for a PR-only review request so it stays review-only. Preserve the distinction between route advisory gates and actual authority: a local `production_action_approval` label does not grant push/tag/release/deploy, cannot replace explicit resource-scoped delegation, and cannot replace required human-signed Trust CI approvals or exact-SHA App check.

## Sources inspected

- `AGENTS.md`, sections “Independent merge trust”, “PR-only delivery and delegated release actions”, “Mandatory entrypoint”, and “Local delegated grants”.
- `README.md`, current-state and delivery/Trust CI descriptions.
- `.grok-stack/adaptive_grok/router.py`: `INTENT_KEYWORDS`, `_best_intent()`, release review selection, human-gate derivation, and `route_context()` output.
- `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`: Trust CI pipeline is pull-request based and merge remains human-owned.

No product files were edited.
