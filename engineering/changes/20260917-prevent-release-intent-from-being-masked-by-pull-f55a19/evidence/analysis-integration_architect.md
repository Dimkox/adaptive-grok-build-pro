# Integration architecture analysis — #123

## Scope and evidence

Read the active route (`f55a194f40df`), the change package, `.grok-stack/adaptive_grok/router.py`, `workflow_artifacts.py`, `receipts.py`, `verification.py`, the route tests, and the current route JSON. This is a read-only compatibility assessment; no application code was changed.

## Findings

1. `build_route()` uses `intent` for several downstream decisions, not just labeling. It selects whether there is a write owner (`review`, `research`, and `release` are no-write intents); selects the default review floor; adds the release review floor and `release_review` evidence; and emits intent-specific workflow skills. Therefore, changing precedence between `review` and `release` can intentionally change the write owner, evidence obligations, skills, and allowed-agent set. The change must test this whole resulting route, not only `route.intent`.
2. `human_gates` are serialized route data (and included in workflow-artifact route identity), but I found no consumer that enforces a gate by itself. `production_action_approval` is advisory route metadata; actual writes are separately constrained by the production tool policy and exact delegated grants. This fix must preserve the gate in the route, and must not claim that classification itself authorizes production work.
3. `required_evidence` is consumed downstream: receipt validation restricts evidence to the closed set, and workflow-artifact validation binds reviewer agents and required evidence. If a release request is newly classified as `release`, the route needs the `release_reviewer` and matching `release_review` evidence together. Existing workflow artifacts may become incompatible if intent changes without regenerating their route-bound artifact/receipts; that is appropriate fail-closed behavior for a new route, not a reason to silently retain stale evidence.
4. The phrase `pull request` is a delivery reference and can occur in feature/bugfix/release tasks. Treating that phrase alone as review intent is semantically unsafe. Keep explicit review verbs/phrases (`review`, `code review`, `проведи ревью`, etc.) as review intent. Tests should show that removing or demoting delivery-only PR wording does not turn an explicit request to review a PR into a write task.
5. Preserve the independent delivery semantics: `delivery_expected` remains true for release and review routes; do not overload it as evidence that a PR review was requested. No-op/research behavior should remain unchanged.

## Recommended compatibility matrix

| Prompt shape | Expected intent/behavior | Controls that must survive |
| --- | --- | --- |
| `Prepare production release and open a pull request` | release; no write owner | `production_action_approval`, `release_reviewer`, `release_review`, release-readiness skill, verification |
| `Fix bug and open a pull request` | bugfix; write owner retained | delivery reviewers/evidence, risk-derived gates as applicable |
| `Implement feature and create a pull request` | feature; write owner retained | delivery reviewers/evidence; PR wording alone must not produce review intent |
| `Review this pull request` / `Проведи code review текущего PR` | review; no write owner | review-intent code/test review floors; do not add production approval absent production/deploy terms |
| `Prepare release for review in a pull request` | release | release reviewer/evidence and production gate, while delivery wording does not downgrade release intent |
| `Open a pull request` (without task semantics) | retain documented existing fallback or classify as review only if it explicitly requests review; do not infer production approval | no fabricated release gate |

For release prompts, assert the complete route contract: `intent`, `write_agent`, `review_agents`, `required_evidence`, `workflow_skills`, `human_gates`, and `delivery_expected`. For explicit PR review, assert the route remains non-writing and still has its review evidence. Add paired wording/order variants (PR before release and release before PR) so the result is not position-dependent.

## Boundary

The active route can state human gates and demand local evidence, but cannot grant an external production action, satisfy Trust CI, or replace branch protection. Tests and documentation should keep that authority boundary explicit.
