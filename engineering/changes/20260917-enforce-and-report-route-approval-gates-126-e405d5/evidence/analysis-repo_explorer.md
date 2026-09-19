# Repo explorer findings — issue #126

## Reproduction at the exact base

This worktree is at `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217`, the route's declared base. I reproduced the security-sensitive path using an isolated temporary git project, with an active route declaring `human_gates: ["production_action_approval"]`, then materialized an exact route/HEAD/tree-bound `production` grant for `git-push-tag`. Calling `evaluate_pre_tool(..., "git push origin v2.9.0")` returned `(True, None)`. The gate declaration did not participate in the authorization result.

Issue #126's source inventory is accurate:

- The only producers of `scope_and_design_approval`, `migration_or_external_write_approval`, and `production_action_approval` are in `.grok-stack/adaptive_grok/router.py:419-425`.
- `Route.human_gates` at `.grok-stack/adaptive_grok/router.py:171` serializes the names. Outside tests, the field is only listed as a workflow-artifact manifest key and demo field: `.grok-stack/adaptive_grok/workflow_artifacts.py:57`, `.grok-stack/adaptive_grok/demo.py:79`. Neither evaluates it.
- `.grok-stack/adaptive_grok/state.py:add_approval()` binds a delegated grant to repository, route ID, change ID, exact HEAD and tree fingerprint. `has_valid_approval()` validates those bindings plus scope/action/resource/expiry, but never reads `human_gates`.
- `.grok-stack/adaptive_grok/_policy_legacy.py:588-596` allows production and direct HTTP writes based on `has_valid_approval`; MCP side-effect tools use the same grant check at :642-643. `.grok-stack/adaptive_grok/deploy.py:85-86` similarly checks a `github-release` grant without checking a route gate. `scripts/grok_approve.py` delegates to `add_approval`, also without gate handling.
- Required evidence is a separate enforced mechanism: `receipts.validate_evidence()` consumes `required_evidence`, not gates. `.grok/hooks/stop_gate.py` explicitly says it is soft/non-blocking and only reports evidence gaps.
- `scripts/grok_status.py` prints raw route/change/agent state and evidence gaps; it has no per-gate enforcement/decision status.

## Boundary and severity

This is a local policy mismatch: a route field described as authority is presently descriptive metadata, and users/reviewers can mistake it for a control. It does not bypass the external Trust CI exact-SHA merge gate, signed human Trust CI approvals, or the existing requirement for an exact local delegated grant. Do not change those external trust boundaries or claim a local gate artifact creates external authority.

A durable gate decision and a local action grant are different facts. The grant authorizes an exact operation on an exact tree. A gate decision records that the human approved a workflow checkpoint. The implementation should not silently infer the second fact from a generic grant's free-form `reason`, and a local agent-written artifact alone is not proof of human identity. The product's existing authority model is explicit user consent materialized into a local grant; any new decision-record command/API must preserve that boundary and require a distinct explicit user decision rather than letting an agent manufacture “approved”.

## Minimal fail-closed recommendation

Keep the route field because both the engineering contract and adaptive-delivery workflow promise these checkpoints. Centralize a closed gate registry (gate ID → applicable action classes and expected decision artifact schema), then have the authorization boundary fail closed when a required gate has no valid, route/change-bound decision record. At minimum apply it inside `has_valid_approval()` (so hooks, deployment preparation and other callers cannot diverge) and reject gate-bearing grants in `add_approval()`/the CLI until the decision is present. Decision records should live under the active change package, have a closed schema, bind route ID/change ID and the approved scope/action/resource, and be shown as `pending/approved/stale/invalid` in `grok_status`. The user must explicitly authorize creation of the gate decision; the agent must never translate a candidate artifact, route label or generic grant reason into approval. Preserve exact local grant binding and external Trust CI rules.

For `scope_and_design_approval`, map the gate to implementation authorization (writer start / change transition) rather than production-action authorization; for `production_action_approval`, map it to production/external side effects. `migration_or_external_write_approval` should apply only to enumerated migration/external-write actions. If this mapping or a trustworthy human-decision path cannot be represented without changing the deployed trust model, the safer bounded resolution is to retire the misleading field and amend its contract/workflow docs, rather than leave a decorative “authority” field. Do not map every gate to every action.

## Concrete tests for the implementation owner

1. `tests/test_policy.py`: route with `production_action_approval` + valid exact production grant still blocks tag push, branch push, release, and external-write until a distinct valid gate decision exists; wrong gate/action/resource, missing, malformed, stale route/change/tree, and expired records fail closed. The exact matching gate decision + exact grant permits only the named action.
2. `tests/test_deploy.py`: release preparation observes the same central gate result (avoid a deploy-only duplicate rule).
3. `tests/test_state.py` or focused approval tests: gate decision validation is closed-shape and route/change bound; CLI/materialization cannot synthesize a decision from its `--reason`.
4. `tests/test_hooks.py`: Bash, HTTP, and MCP side effects are blocked consistently when declared gates are pending.
5. `tests/test_status.py` (or a focused status test): each declared gate is reported with deterministic enforcement and decision state; missing/invalid decision appears as a gap.
6. `tests/test_repo_router.py`: preserve current route classification assertions and ensure known gate IDs only are emitted.

Keep existing tests that prove exact local grants and external Trust CI are separate. Avoid changing deployed Trust CI source, policy, holdout bundle, or signed approval protocol as part of this issue.
