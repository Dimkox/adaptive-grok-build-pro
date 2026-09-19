# Integration architecture analysis — route approval gates (#126)

## Findings

`Route.human_gates` is populated by `router.py` for high-risk/architecture scope, high-risk integration/data work, and production/release intent. The field is serialized into the active route and change workflow manifest, but product enforcement paths do not read it. `evaluate_pre_tool()` instead checks only an exact delegated local grant for production actions, direct HTTP writes, MCP side effects, and protected paths; `prepare_deploy(record=True)` checks a `github-release` grant. Thus a route can declare `production_action_approval` while the local action path does not require or report any gate-specific human decision.

The repository has two separate authorization protocols which must remain distinct:

1. **Delegated local grants** (`scripts/grok_approve.py`, `state.add_approval()/has_valid_approval()`) are short-lived action/resource permissions, bound to repository, route ID, active change ID, Git HEAD and tree fingerprint. They are intentionally local and do not satisfy external Trust CI approvals.
2. **Trust CI human security approvals** use a signed envelope bound to repository, PR number, base SHA, head SHA, deployed policy digest, configured scope, issue/expiry time and nonce. The CLI signs on a human-controlled machine; the API validates against its server-owned trust store and bound server policy; the runner blocks the exact-SHA check run until all policy-required scopes are accepted. This protocol is external authority and is not connected to `human_gates`.

The envelope schema has no route ID, change ID, gate name, or local tree-fingerprint field. Trust CI scopes come from deployed `approval_rules`, not repository route classification. Mapping route gate names directly to Trust CI scopes or treating a local grant as a signed human approval would therefore break trust-boundary and binding semantics. Deployed Trust CI policy/API/store must not be changed in this repository to close #126.

## Safe minimal design

Consume the route gates locally as a separate, explicitly non-Trust-CI workflow. Add a durable, change-package gate-decision record for each declared gate with a closed status vocabulary (`pending`, `approved`, `rejected`), gate ID, route/change/repository identity, exact approved scope digest or equivalent bounded decision target, actor, timestamp, and rationale/evidence reference. The approval writer must require explicit human input and reject agent/local-grant metadata as proof of the decision; action authorization must fail closed when a matching gate record is absent, rejected, stale, or bound to another route/change/target. Do not infer gate approval from `approvals.json`, `--source`, `--reason`, a local receipt, or a Trust CI scope name. For production actions, both the gate decision and existing exact delegated grant remain necessary; the latter still only authorizes the named local operation.

Expose each declared route gate and its resolution in `grok_status.py` (and preferably the common status API): declared gate, enforcement kind, decision status, target binding, and a short missing/stale reason. A missing route gate should be visible as a missing control; it must not be synthesized from the task text at check time. If a compatible human-decision writer cannot be added without asserting identity/provenance the local system cannot verify, use the issue's explicitly permitted retirement option: describe the field as agent discipline only, remove claims that it is machine-enforced, and keep exact local grants plus external Trust CI checks as the actual controls.

The action-to-gate mapping should be centralized and narrow. At minimum, `production_action_approval` gates production-scope actions and release preparation; `migration_or_external_write_approval` gates only the relevant integration/data external-write or migration operation; `scope_and_design_approval` is a pre-implementation workflow gate and should not silently become a blanket authorization for unrelated writes. Existing action/resource checks must remain in force independently.

## Contract and compatibility impacts

- Route schema v1 already serializes `human_gates`; keeping its shape avoids breaking existing route consumers and recorded package manifests. Additive status/decision metadata should have a schema version/default for absent records.
- Existing active routes and old change packages have no decision artifact. Treat their declared gates as `pending` (fail closed for gated actions); do not auto-migrate them to `approved`.
- Approval artifacts need exact change/route/target bindings and invalidation rules. A route change, changed approved scope, changed relevant tree/HEAD, new active change, or expiry must stale the local decision. Avoid requiring equality to a changing whole-tree fingerprint for a long-lived pre-implementation design decision unless the approved-scope digest is stable and explicit.
- Keep local gate records distinct from Trust CI envelope v1 and local delegated-grant schema v2. Do not add fields to the signed envelope, broaden deployed scope rules, or claim that local `grok_status` can attest to external approval.
- Add route gate status to the workflow manifest/status output additively; tolerate old manifests with no status fields. `required_evidence` remains its own checked field and must never be dropped or treated as equivalent to a human gate.

## Tests needed

1. Classifier/route tests cover each producer condition and preservation through route serialization and workflow-manifest output.
2. Table-driven policy tests show each gated production/external-write/migration action denied for absent, pending, rejected, stale, wrong-route, wrong-change, and wrong-target decisions; the same operation succeeds only with a matching gate decision **and** its existing exact local delegated grant.
3. Negative tests prove a local grant, free-form `reason`, review receipt, user-supplied `source` string, or an unrelated Trust CI scope cannot satisfy a route gate.
4. Status tests show every declared gate with `pending`/`approved`/`rejected`/`stale` and actionable cause; no-gate routes remain backward compatible.
5. Trust CI contract regression tests confirm approval-envelope v1 schema, deployed-policy scope matching, exact repository/PR/base/head/policy binding, signature verification, and `needs_approval` behavior remain unchanged.
6. Migration/compat tests load legacy route/package data and verify absent decision data is pending, never implicitly approved; changing the approved target invalidates the decision.

## Boundaries and blocker

The repository can make the local route contract honest and fail closed around local actions. It cannot create a cryptographically verified human decision or satisfy a deployed Trust CI approval from route metadata. Any requirement that route gates become external merge authority needs an independently deployed Trust CI policy/protocol change and human-held signature workflow; that is outside this issue's repository change and must not be represented by local evidence.
