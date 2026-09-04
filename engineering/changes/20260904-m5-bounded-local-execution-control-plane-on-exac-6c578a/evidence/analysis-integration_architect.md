# M4-to-M5 additive integration assessment

## Scope and evidence identity

This assessment compares exact M4 `67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4` (tree `399c65e7c65626f3d5236cae1bce009c5d3a9714`) with canonical M5 `3940267ac5754ad07a047894102015d33eb759b1` (tree `4646582a7c5ff6f08ee7e8462687da400459b08d`) at their local merge base `9727bc30c82bb44a86db0ef5b62e507b5527207a`. It is limited to `models.py`, `api.py`, `service.py`, `store.py`, `server.py`, and the factory control/execution OpenAPI contracts. No external state was consulted or changed.

The safe integration direction is **M4 as the authoritative base, followed by a selective M5 transplant**. A file-level checkout, merge preference for M5, or wholesale cherry-pick is not acceptable: canonical M5 retains the pre-repair control API and store implementations and would remove M4 history routes, the fenced phase transition, typed error envelopes, semantic-work identity replay, the current transition authority, and stronger accounting/reconciliation behavior.

## Contract inventory

| Surface | M4 authority to retain | M5 addition |
|---|---|---|
| Control OpenAPI | Preserve blob `78365e2367c31b22fbdcab16133ff0973f4460b5` for `factory-control.v1.json`; it defines 17 checked operations, including run history, event history, and fenced phase transition. | None; canonical M5 carries the obsolete control blob `33256c53f83e35491254be3842789355f71b61b9` and it must not replace M4. |
| Execution OpenAPI | No M4 execution surface. | Add `factory-execution.v1.json` blob `bedd10e267025f9e8faa2a126b0c3a73592190f8` and `factory-execution.v2.json` blob `e3fdd5018f42997dab31bd19e11aa3cc1a44a8f3`: six operations per version. V1 terminal returns the accepted proposal; V2 terminal additionally returns the finalized workspace result. |
| Runtime routes | Keep every M4 path, method, authorization scope, closed body, status, response shape, operation identity, and correlation behavior. | Add `/v1/execution/{claims,stages,notes,artifacts,usage,terminal}` and their `/v2` counterparts behind the execution capability gate. The resulting checked union is 29 operations; disabling execution removes only the 12 execution path/method pairs. |

Execution schemas remain independently versioned. They must not be copied into or used to rewrite the M4 control schema. Shared values (`LeaseGrant`, task/run IDs, fence, and legacy packet digest) have one runtime representation and must satisfy both documents without weakening either closed contract.

## Additive integration recipe

### 1. `models.py`

Start from the complete M4 file. Retain `TaskStatus`, `RunRole`, `RunStatus`, `FailureClass`, `Actor`, all `Factory*V1` immutable history projections, `_deep_freeze`, and the identity alias `TaskProjection = FactoryTaskV1`. Add only canonical M5 `ExecutionStage` and `ExecutionGrant`; `ExecutionGrant.lease` must use the existing M4 `LeaseGrant`. Do not reintroduce the old standalone `TaskProjection` class and do not remove or rename any M4 enum value. Execution stage is an orthogonal run-execution state, not a replacement for M4 task phase or run status.

### 2. `api.py`

Start from M4 and retain its field-wise dataclass serialization (required for immutable mapping-backed event metadata), canonical UUID rejection, checked `{error, code, detail}` envelopes, Starlette/FastAPI validation handlers, bounded body middleware, generated/validated correlation ID, response `X-Correlation-ID`, strict repository kill-scope validation, and all 17 control handlers.

Add the M5 execution imports, redacted execution/broker/integrity exception handlers, `_execution_request_id`, `_execution_command_key`, the optional `execution_enabled` argument, and the six dual-version execution handlers. Each handler must preserve closed bodies, `task:execute`, repository authorization, canonical grant parsing, bounded integers/digests, and idempotency/correlation binding. Preserve the V1/V2 terminal response distinction from the two execution contracts. Capability-off filtering must enumerate only execution routes and leave the M4 route set byte-for-byte behaviorally intact. Do not adopt canonical M5's older generic HTTP responses, permissive UUID normalization, unconditional request streaming, removed correlation header, weakened kill-scope check, or omission of `/runs`, `/events`, and `/v1/transitions`.

### 3. `service.py`

Extend the M4 constructor with keyword-only snapshot broker, artifact broker, artifact-attestation store, and execution registry dependencies. Add the two snapshot error types, `ExecutionTerminalCompletion`, authorized workspace-result lookup, and the canonical M5 claim/start, stage advancement, proposal, terminal-composite, snapshot, and finalization methods.

Keep all current M4 methods and signatures, notably intake correlation propagation, tenant-authorized run/event history, `transition_phase`, grant-owner/repository checks, and best-effort fence-rejection accounting. M5 authority must be additive: a caller needs `task:execute`, worker identity, repository membership, the exact M4 lease grant, and every execution identity. The immutable task packet is derived from the persisted accepted-intent body; the M4 complete-intent digest, semantic work idempotency key, request transport identity, task packet digest, and M0 proof retain their distinct meanings. The execution packet/manifest digests are subordinate identities and must never overwrite or recompute the M4 task/lease identity.

Define one lifecycle owner per run. A run with an execution packet is advanced and terminalized through the M5 execution service; ordinary M4 runs retain `/v1/transitions` and `/v1/proposals` unchanged. Legacy phase/release commands against an execution-owned run must fail closed or enter the explicitly tested recovery path; they must not create a second terminal decision. Heartbeat, bounded budget reservation, authoritative usage observation, cancellation, supersession, and operator reconciliation remain shared M4 controls. An execution usage proposal is evidence and does not itself settle M4 accounting.

### 4. `store.py`

Use M4 `store.py` as the merge skeleton. Preserve without semantic substitution:

- `_apply_task_transition`, `TransitionError`, `TerminalizationResult`, and the closed transition graph;
- intake command replay keyed by request transport while duplicate work resolves through the semantic-work identity;
- M4 audit digest v2 and correlation/run binding;
- immutable, bounded run/attempt/event history and its strict row validation;
- active-phase grant fencing, capacity-before-task lock order, retry classification, terminalization, deadline handling, and mandatory cleanup events;
- the full current `_accounting_consistent` predicate, bounded reconciliation clock/transaction handling, budget settlement, and accounting quarantine.

Transplant the M5 execution imports and errors, least-privilege session validation, dedicated `PostgresArtifactAttestationStore`, transaction-timeout support, session identity in readiness, recovery methods, combined metrics, execution material/start/stage/proposal/replay/finalize/workspace methods, and artifact/recovery persistence. Merge these into the M4 connection and transaction wrappers rather than replacing those wrappers. Combined metrics must preserve every M4 legacy counter and validation while appending the three M5 metric families; canonical M5's older accounting predicate must not be imported.

Every M5 mutation must bind `(task_id, run_id, owner, role, fence, M4 packet_digest, execution packet_digest)` as applicable, verify live lease/current pointers/deadline/capacity, use the existing command replay/audit primitives, and remain in one database transaction. Migrations `014`-`017` are appended after unchanged migrations `001`-`013`; no earlier migration is rewritten.

The canonical M5 finalizer directly updates M4 task/run/attempt/capacity state. During transplant it must be reconciled with the M4 invariant: only an execution-owned live run may finalize; its source task state is the accepted execution state; the resulting target must be authorized equivalently to M4 `RELEASE_COMPLETED` or `RELEASE_FAILURE`; accounting must be settled or quarantined; run, attempt, capacity, task pointer, execution result/stage, command result, mandatory task event, and audit fact commit atomically. The M4 task event must retain the existing closed metadata (`from_state`, `target`, `operation`, `run_id`, `fence`, and applicable quarantine/reason). Store the workspace-result digest in execution persistence and audit metadata rather than silently widening the checked M4 event contract. Cancellation, supersession, expired-lease reconciliation, and restart recovery must leave at most one fenced cleanup claim and no live allocation.

### 5. `server.py`

Retain M4 actor identifier validation, private-file checks, Unix-socket ownership/mode protections, and the existing default control application construction. Add M5 runtime readiness validation, execution dependency injection, separate runtime and artifact-attestor capability identities, and `execution_enabled` routing. Execution enabled must fail startup unless registry, snapshot broker, artifact broker, schema `001`-`017`, `factory_runtime`, and a distinct least-privilege `factory_artifact_attestor` are all ready. Execution disabled must start only the complete M4 control plane and must not require execution-only dependencies. Neither path performs a live provider call.

## Critical focused verification only

1. `factory/tests/test_models.py` and `factory/tests/test_openapi_contract.py`: retain the M4 model aliases/history immutability and exact 17-operation control contract; assert the runtime union adds exactly the six V1 and six V2 execution operations without a control deletion or identity change.
2. `factory/tests/test_api.py`: control error/correlation/body/UUID/kill-scope behavior remains unchanged; execution authorization and closed bodies are tenant-safe; V1 terminal omits `result`, V2 includes it; capability-off removes execution only.
3. `factory/tests/test_contracts.py` plus `factory/tests/test_execution_contracts.py`: request/M0 refresh changes complete intent but not semantic work identity; every semantic field changes it; execution packet/manifest/result canonical digests bind the persisted M4 authority and reject unknown or mismatched fields.
4. `factory/tests/test_service.py` plus `factory/tests/test_execution_service.py`: preserve tenant-filtered histories and fenced M4 phases; prove execution registry selection, exact grant ownership, failure cleanup, idempotent terminal composite, and rejection of split lifecycle ownership.
5. `factory/tests/test_execution_persistence_postgres.py`: migration `001`-`017` upgrade, start/stage/proposal/finalize replay, stale fence, cross-tenant/cross-run substitution, artifact-attestor separation, settled-accounting completion, failure quarantine, and atomic workspace-result/M4 terminal state.
6. `factory/tests/test_postgres_integration.py`: retain M4 semantic duplicate/supersession, immutable pagination, transition history, retry ceilings, bounded reconciliation, capacity release, and the complete accounting-consistency predicate after execution rows exist.
7. `factory/tests/test_recovery.py`, `factory/tests/test_runtime_capability_postgres.py`, and `factory/tests/test_server.py`: restart recovery is bounded and single-claim, cleanup is fenced/idempotent, login capabilities are disjoint, execution-enabled startup fails closed, and execution-disabled startup preserves the full M4 surface.

These focused gates are prerequisites to the repository's later exact-head verifier and independent review; they are not external acceptance or release authority.
