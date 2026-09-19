# Documentation and contract research — issue #126

## Finding

Issue #126 is supported by the checked-in contract and source. `AGENTS.md` says the active route governs local human gates; `.agents/skills/adaptive-delivery/SKILL.md` explicitly says to present the decision and stop before implementation when `scope_and_design_approval` is declared. The active route for this change declares that gate. However, the repository contract separately and correctly says local grants, receipts, change packages, prompts, hooks, tests, and reviews are workflow evidence only; merge authority remains the deployed App-owned exact-head Trust CI check, with separately required signed human approvals.

The product-code search in the issue body is consistent with this checkout: `router.py` produces the gate names; `state.py` validates local delegated grants without consuming those names; `deploy.py` requires the grant; the stop hook checks required evidence, not route gates. `README.md` describes `grok_approve.py` as an exact local action/resource grant and says the hook is a usability guardrail, while its workflow section distinguishes local `ready` from external Trust CI and human promotion.

## Relevant existing language

- `AGENTS.md`, “Independent merge trust”: local artifacts are workflow evidence, never merge authority; the App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run on the exact PR head is authoritative; Trust CI checks signed scopes against its server-mounted public keys.
- `AGENTS.md`, “Mandatory entrypoint” and “Local verification and completion”: route is authority for local skills/agents/profiles/human gates/evidence; local verification and receipts are preflight only; external check is still required.
- `.agents/skills/adaptive-delivery/SKILL.md`, “Scope and design gate”: `scope_and_design_approval` means present the decision and stop before implementation. This is a workflow requirement, not cryptographic Trust CI approval.
- `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md` §7 already distinguishes route scope/design approval, Trust CI Ed25519 human security approval, and delegated local operational grants.
- `README.md` lines 55, 98, 284, 308: local workflow/approval descriptions preserve the external-authority boundary, but do not state whether declared route gates are mechanically consumed or expose per-gate status.

## Recommendation for #126 documentation and status

Bind the field as a **local workflow/action-authorization invariant**, and describe it plainly as such. Keep these concepts distinct in names and output:

1. **Route gate**: a required local human decision for this workflow/action class. It has a known gate ID, applicable action scopes, and a status such as `required`, `satisfied` (with a referenced durable decision record), `blocked` (explicit rejection), or `unknown` (unrecognized gate ID; fail closed for the gated action).
2. **Delegated local grant**: exact user-delegated action/resource permission bound to repository, route, change, HEAD and tree. It authorizes only the listed local operation; it does not itself satisfy a route human gate unless the product explicitly records a separate decision and validates that record.
3. **Trust CI approval / merge authority**: signed human approval verified by deployed Trust CI and its App-owned exact-SHA Check Run. Neither a route decision record nor a local status may be presented as satisfying this external boundary.

For `grok_status`, report each declared gate by ID and its current status, decision-record reference/digest when present, and action scope. Missing, malformed, stale, or unknown gate evidence should be visibly unsatisfied and prevent only the relevant gated local action/transition. Do not infer satisfaction from route presence, an approval grant, a green local receipt, a review report, or a human-gate string in package metadata. Preserve fail-closed behavior for protected operations and do not weaken existing `required_evidence` checks.

Suggested concise README/CLI wording:

> “Route human gates are enforced local workflow gates. A declared gate remains unsatisfied until its separately recorded decision is validated for the current change and scope. `grok_status` reports each gate and evidence reference. This local decision is not a Trust CI signed security approval, an App-owned exact-SHA check, merge authority, or authorization for an external operation beyond an exact delegated grant.”

Suggested status labels: `required`, `satisfied`, `blocked`, `unknown`; include `evidence: <path-or-none>` and `scope: <action scopes>`. Avoid a generic `approved=true`, because it would collapse unlike authorities and could be mistaken for Trust CI approval.

## Gate and implementation sequencing

This route declares `scope_and_design_approval`, and the adaptive-delivery skill says to present the decision and stop before implementation. Before code changes, the owning agent should present the bounded design, accepted behavior, and exact local-vs-external authority boundary, then wait for that gate to be satisfied under the workflow. The user’s broad “исправляй всё” does not turn a local route-gate status into an external signed Trust CI approval, and this report itself is analysis rather than approval evidence.

## Scope cautions

- Do not change deployed Trust CI policy, holdout, trust stores, protected-branch settings, signing keys, or App configuration.
- Do not mint, read, request, submit, or simulate private-key approvals.
- Do not claim the repository can enforce human review of its own PR as an independent trust boundary: repository-local records are mutable with the PR. Treat them as workflow control, while deployed Trust CI remains independent authority.
- A route that omits a gate cannot be treated as authorization. Gate production should remain conservative and must not trade away `required_evidence` categories.

## Sources inspected

`AGENTS.md`; `.agents/skills/adaptive-delivery/SKILL.md`; `START_HERE.md`; `PROJECT_STATE.json`; `README.md`; `architecture/rules.yaml`; `.grok-stack/config/policy.json`; `.grok-stack/adaptive_grok/router.py`; `.grok-stack/adaptive_grok/state.py`; `.grok-stack/adaptive_grok/deploy.py`; `.grok/hooks/stop_gate.py`; `scripts/grok_approve.py`; existing Superpowers trust-authority and autonomous-factory specs; issue #126 body.
