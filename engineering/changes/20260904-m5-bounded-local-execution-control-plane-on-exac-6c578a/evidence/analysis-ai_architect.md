# AI architect analysis — M5 offline execution boundary

## Result

Port the final M5 contract/protocol boundary from
`3940267ac5754ad07a047894102015d33eb759b1` onto exact M4
`67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4` as an additive, disabled-by-default
repository-local control plane. The built-in Codex and Grok adapters remain
offline conformance translators only: neither is execution-eligible, neither has
an `invoke` method, and no product path may spawn a provider process, use a
provider SDK, read credentials, or access the network.

This conclusion is bounded to the core M5 flow. It does not add speculative
hardening or turn edge discoveries into additional acceptance rounds.

## Minimal additive port

Copy the final forms at `3940267` of these add-only surfaces, including all
hardening accumulated through `c70950d` and `0e5f0ef` rather than their initial
versions:

- `factory/src/adaptive_factory/execution_contracts.py`
- `factory/src/adaptive_factory/protocol.py`
- `factory/src/adaptive_factory/adapters/{__init__,base,codex,grok}.py`
- `factory/src/adaptive_factory/brokers.py`
- `factory/src/adaptive_factory/workspace.py`
- `factory/contracts/schemas/{task-packet,execution-invocation,execution-event,workspace-result}.v1.json`
- the two exact-version JSONL fixtures and focused tests
  `test_execution_contracts.py`, `test_protocol.py`, `test_adapters.py`,
  `test_brokers.py`, and `test_workspace.py`

Then graft only the M5 symbols and calls needed by those modules into the current
M4 application seams. In particular, add `ExecutionStage` and `ExecutionGrant`
to the current models without replacing M4's `RunStatus`, versioned history
models, or compatibility aliases. Resolve an `ExecutionSelectionV1` through the
trusted registry before acquiring an execution claim; construct the packet and
manifest from the locked M4 grant/material; and keep finalization, trusted
snapshot acquisition, artifact attestation, and recovery server-owned.

Do **not** merge or cherry-pick the canonical branch wholesale. Its merge base is
the obsolete M4 `9727bc3`, and its overlapping `contracts.py`, `models.py`,
`store.py`, `service.py`, API, architecture, tests, and state surfaces can undo
current M4 behavior. Exact M4 wins every overlap; adapt the M5 seam around it.

## Critical fail-closed boundaries

1. **Tenant and actor authority:** `repository_id` remains the tenancy boundary.
   It is derived from the locked task and checked against the authenticated
   worker's repositories and `task:execute` scope. Request/provider values never
   confer repository, task, run, owner, role, fence, or workspace authority.
2. **No caller-selected provider trust:** selection must exactly match one
   server-supplied `TrustedExecutionProfile`, including provider, adapter/native
   versions and digests, model, capabilities, policy, plan, workspace, and role.
   Missing registry, unknown provider/version, mismatch, ineligible conformance,
   or reader write capability is a closed denial; there is no fallback.
3. **Offline adapters only:** Codex `0.152.1` and Grok `1.0.17` translate bounded
   fixture bytes into canonical events. Both keep `execution_eligible=false` in
   the shipped registry material. Tests may inject a closed trusted profile to
   exercise orchestration, but production composition must not synthesize one.
4. **Immutable identities:** the task packet and run manifest use separate
   domain digests and bind the exact M4 task/run/owner/role/fence, repository,
   authority digests, provider/model/tool/prompt/output identities, ordered plan,
   limits, acceptance IDs, workspace handle, and deadline. The M5 packet digest
   never replaces M4's legacy intent/packet identity.
5. **Untrusted output is proposal-only:** accept strict UTF-8 JSONL with bounded
   bytes, lines, events, depth, nodes, strings, exact identity, increasing
   sequence, declared capabilities, and exactly one terminal event. Unknown
   fields/events, duplicate keys, non-finite values, partial/post-terminal data,
   raw provider streams, prompts, stdout/stderr, and private reasoning categories
   fail closed before persistence.
6. **Broker enforcement:** every proposal is rebound to current owner, live
   fence, durable role, declared capability, allowed relative path, artifact
   class, budget, and idempotency digest. Artifacts are writer-only and require a
   matching server-side trusted attestation. Provider output cannot supply an
   authoritative workspace snapshot or choose the terminal M4 disposition.
7. **Capability startup gate:** execution routes stay absent by default. Enabling
   them without the trusted registry, snapshot broker, artifact broker, separate
   attestor persistence capability, and required database readiness must fail
   before the Unix socket is exposed.
8. **Factual recovery:** restart recovery may fence and mark stale work, release
   allocation, and retry exact-handle cleanup. It must never fabricate provider
   proposals, attestations, snapshots, successful results, or external actions.

## Focused acceptance evidence

Use the canonical focused tests above plus the service/API/startup tests for:

- exact registry resolution and no fallback;
- cross-repository, cross-owner, cross-run/workspace, reader-write, and stale-fence denial;
- closed protocol projection and rejection of unknown/private/native material;
- packet/manifest digest stability and distinction from M4 identity;
- trusted snapshot/attestation requirements and atomic terminal result;
- execution-disabled startup and incomplete-composition failure.

These are the complete AI/provider P0 checks for this port. Do not add live
provider tests, fuzzing, additional native versions, style permutations, or
unobserved edge cases to the M5 blocking boundary.

## Deferred without weakening the source contract

Live provider invocation, credentials, egress, executable discovery, rootless
host qualification, real workspace/Git mutation, dynamic routing/fallback,
additional providers/models, pricing feeds, fleet behavior, and cross-department
approval automation remain outside M5. Product documentation should retain its
serious enterprise contract language and state these capabilities factually as
disabled or unavailable; the temporary MVP prioritization itself must not be
written into customer-facing documentation.
