# Architecture analysis — route approval gates (#126)

Route `e405d570fc4f`; base `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217`. This is a read-only analysis of the current implementation and issue semantics, not implementation or approval to perform any external action.

## Finding

The issue reproduces. `router.build_route()` emits `scope_and_design_approval`, `migration_or_external_write_approval`, and `production_action_approval` as labels, but runtime consumers do not read `human_gates`. The adaptive-delivery skill tells the controller to stop before implementation on the scope/design gate. Separately, `_policy_legacy.evaluate_pre_tool()` and `deploy.py` enforce exact delegated grants for production/external writes; those checks bind repository, active route/change, HEAD, tree, scope/action and (where applicable) resource, but do not inspect route gates. `grok_status.py` reports evidence gaps only. Thus a route can declare a gate while product behavior shows no gate lifecycle or status.

## Authority distinction

Keep three controls separate:

1. **Route gate** is a workflow requirement attached to a change (for example, human acceptance of a design or a human decision to proceed with a specified production operation). It is not a credential.
2. **Delegated local grant** is a short-lived, exact-scope execution authorization materialized from explicit/standing user consent. It is required by the existing last-mile hook for its named operation, but is bound to the current tree and can expire. It must not automatically mark a durable route gate complete: the gate may have different meaning/scope, and the grant is not durable approval evidence.
3. **External Trust CI authority** is the deployed App-owned exact-PR-SHA check plus any required human-signed scoped approval. No local gate record, receipt, grant, route field or test can satisfy or impersonate it.

A package `human-approval` document is durable workflow evidence, not cryptographic identity proof. A local implementation may report that evidence as *recorded* and use it to prevent accidental workflow bypass, but must not describe it as authenticated or as Trust CI approval. Likewise, a local grant is not a human-signed Trust CI envelope. Never read, generate or submit private keys.

## Recommended gate model

Use an explicit, fail-closed status per declared gate, with at least `pending`, `recorded`, `stale`, and `invalid`; undeclared gates are `not_required`. Include the gate ID, route ID, change ID, evidence path, relevant approval scope, and a concise reason in status output. Do not collapse status into one `approved` boolean. A missing route or malformed gate list must not yield a satisfied gate.

- `scope_and_design_approval`: pending until explicit human approval evidence for the current change's named scope/design is recorded. This permits the workflow transition to implementation only after that gate is recorded; it does not authorize production writes, branch push, merge, publish, or deployment.
- `production_action_approval`: pending until the human decision is recorded for the specific operation/resource. For an agent-side effect, require **both** this route-level gate and the existing exact, live delegated grant at the last-mile policy check. A gate record without a grant cannot execute; a grant without the required gate record must be denied. A separately executed human-controlled terminal remains governed by the repository's delegated-action rules and external approvals.
- `migration_or_external_write_approval`: if consumed by this issue's chosen scope, bind its evidence to the named migration or external target and preserve the existing exact resource grant/recovery constraints. Do not silently map it to a broad production grant.

For staleness, bind approval to the semantic artifact(s) that define its scope (e.g. typed change spec plus architecture/plan digest), not the whole repository tree: implementation itself necessarily changes the tree and should not invalidate design approval. A changed scope/design digest invalidates that record and returns the gate to pending. Production-action approval must identify the exact action/resource; changing either invalidates it. Do not reuse a past route's approval solely because the same gate label appears.

## Least-risk implementation boundary

Use one shared gate-status/evaluation function so status reporting and authorization do not diverge. Read only the active route and current change package; verify route/change identity and evidence binding before returning `recorded`. Call the evaluator at the true authorization boundary (`has_valid_approval`/`add_approval` or immediately around the production/external policy check), not only in a CLI or stop hook. Preserve existing exact grant checks as an independent conjunct. Apply gate enforcement only to applicable actions and gate IDs; avoid turning `scope_and_design_approval` into a blanket production lock or letting it authorize an action.

`grok_status.py` should expose each declared gate's status and reason. Its output is diagnostic; the status command itself is not the enforcement point. Tests should cover the cross-product: no declared gate, declared pending, valid bound evidence, stale/malformed evidence, route/change mismatch, correct gate plus exact grant, gate without grant, grant without gate, wrong action/resource, expiry/tree mismatch, and preservation of external Trust CI boundary. Router/route preservation also matters: any routing normalization must not drop human gates while retaining a high-risk route (related issue #123).

## Compatibility and migration

Existing change packages may have route snapshots with gates but no approval artifact. Treat them as `pending` (or explicitly `unrecorded`), never infer completion from age, status `approved`, free-form reason text, `human-approval.md` presence alone, or a matching local grant. Provide a clear status explanation and a documented recording path so operators can remediate intentionally. Existing production/external grant behavior should remain exact and continue to reject missing/expired/wrong-tree grants; the new gate check is additional. Keep machine-readable route schema compatible by treating absent `human_gates` as an empty list only for legacy routes, while malformed values fail closed. Do not edit deployed Trust CI policy, holdout, trust stores, or approval verification.

## Open design risk

This codebase's runtime route/package/grant inputs are local workflow state. A plain package artifact can be forged by a process that can edit the workspace, so local enforcement can prevent accidental skips but cannot establish cryptographic human identity against a malicious checkout/agent. If issue acceptance expects adversarially trustworthy human gate attestation, that must be performed by the external Trust CI service with its deployed verifier and human-signed scope; repository code cannot supply that authority. Keep these guarantees explicit in API/status wording.
