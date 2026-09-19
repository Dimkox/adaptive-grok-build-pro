# Proposed architecture: route gate enforcement

## Decision for human approval

Bind the existing route gates to explicit, durable local decisions rather than retiring the field. This preserves the repository's declared human checkpoints while making their local limits visible. It is a workflow fail-safe, not a security attestation: an unsigned local artifact cannot establish the identity of its author and cannot replace an exact delegated grant or Trust CI's signed approval.

At change creation, persist the route's `human_gates` list and a digest over that list plus `route_id` in `state.json`. Enforcement requires the active route, the saved `route.json`, and this state-bound declaration to agree. Missing or modified copies fail closed before both transitions and protected actions; rewriting the active route while retaining its ID cannot remove a gate.

## State and binding

Add a change-package gate-decision artifact with one decision per declared gate. A decision records the route ID, change ID, gate name, approve/decline value, decision time and a stable digest over the approved scope files (brief, typed change spec, architecture, requirements and test plan). The digest excludes the decision artifact and volatile evidence so a reviewer report does not invalidate the approved scope. Missing, declined, malformed, mismatched, or stale records remain unsatisfied. Routes with a declared gate and no artifact remain pending; no migration or bootstrap auto-approves legacy routes.

Provide a narrow CLI to inspect and record a human-supplied decision. It must require an explicit decision and reason, reject unknown gates and route/change mismatch, and never infer approval from a local grant, review receipt, Git author, or user prompt classifier. Its report states that the record is local workflow evidence only.

## Enforcement boundaries

- `scope_and_design_approval`: require a current approved decision before the change can transition to `approved` or proceed to implementation.
- `production_action_approval`: require a current approved decision before a production-scoped local grant can be materialized and whenever that grant is consumed for a production action.
- `migration_or_external_write_approval`: require a current approved decision before a matching external-write grant is materialized or consumed.
- The exact delegated grant remains independently required and retains its existing repository/route/change/HEAD/tree/action/resource/TTL binding.
- `grok_status.py` reports every declared gate as pending, approved/current, declined, stale, or invalid, with the binding digest and evidence path.
- No code path may convert this local record into Trust CI approval. Trust CI policy and deployed state stay external and unchanged.

## Rollout and recovery

This changes only local source behavior. Existing declared gates without explicit decisions fail closed, which is the intended correction; the operator records decisions for the exact package scope before continuing. Rollback reverts the source change. No external state is mutated, and existing grants are not broadened.
