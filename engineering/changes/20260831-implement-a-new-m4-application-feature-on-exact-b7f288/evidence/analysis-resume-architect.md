# M4 resumed architecture analysis

- Route: `b7f288f1e81e`
- Required base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Inspected committed head: `9727bc30c82bb44a86db0ef5b62e507b5527207a`
- Head tree: `5feb9a74eda6c54cd37539a2c5dda378a5e27853`
- Scope: read-only factory boundary/contract and architecture/governance binding review; no application, external, or secret operation.

## Verdict

**BLOCKED for an M4 interface-complete/architecture-complete claim.** The trust-domain separation is coherent and the two latest commits do not change the adopted architecture or canonical governance bytes, but three existing contract/interface gaps should be resolved before the final verifier/review wave. Independently, every receipt at the prior `571cad7` tree is stale at `9727bc3` and cannot authorize this head.

## What remains architecturally sound

The adopted model declares three factory-owned nodes (`NODE-FACTORY-LOCAL-API`, `NODE-FACTORY-CONTROL`, `NODE-FACTORY-POSTGRES`) in the single `TD-FACTORY-CONTROL` local-preflight domain. It declares only UDS API-to-control and local PostgreSQL control-to-store edges. There is no modeled edge from that domain to Trust CI, GitHub, an external platform, or production. `FIT-FACTORY-NO-TRUST-OR-EXTERNAL-EDGE`, `FIT-FACTORY-CANNOT-DEFINE-TRUST-CI`, `FIT-FACTORY-MATERIAL-BOUNDARY`, and `FIT-FACTORY-SQL-HISTORY` reinforce that separation.

Fresh read-only checks at `9727bc3` returned:

- `grok_architecture.py validate`: PASS, no findings.
- `grok_architecture.py diagram --check`: PASS, no mismatches.
- exact-base/exact-head architecture fitness: PASS; risk remains red; required scopes are architecture, contract, data, and security.
- `grok_governance.py validate`: PASS, governance digest `dfb2631cf1d47deaea71dec2d576adb72182f55401f12517333d2fff13355463`.

The canonical governance registries contain zero rules, zero debt entries, and zero examples, exactly as they did at accepted base `67714a1`. That is not new drift, but it is important not to overstate the binding: the M3 digest authenticates an empty target-owned governance set. M4-specific constraints are currently carried by the typed change spec, adopted architecture/rules, repository contract, and code/tests—not by an active canonical governance rule.

## Blocking findings

### A-01 — The declared bidirectional OpenAPI contract is not a closed client contract

`architecture/system.yaml` declares `factory/contracts/openapi/factory-control.v1.json` as the factory API's bidirectional public contract, but that document contains 14 operation stubs, zero component schemas, and no typed request or success/error response bodies. All nine POST operations omit `requestBody`; both templated task paths omit a declared `task_id` path parameter; and all eleven secured operations omit at least one of the actual 401/403 outcomes. Required headers, query bounds/cursors, correlation response headers, and most 400/404/409/413/422 response shapes are likewise absent.

There are also two divergent API descriptions. FastAPI still exposes an auto-generated `/openapi.json`. Its path set matches the checked-in file, but its document does not: request bodies are generic open dictionaries, it contains only validation schemas, it lacks the manually declared bearer scheme, and its response inventory reflects decorator inference rather than the checked-in status contract. Existing tests compare selected paths/descriptions only and do not enforce document parity or a complete schema.

This blocks a stable M4 consumer boundary, including the later local admin adapter. Close it by defining closed request, response, header, parameter, cursor, error, task, run, attempt, and grant schemas; using typed adapter models; and making the runtime serve the exact reviewed contract (or disabling runtime OpenAPI). Add exact semantic parity and compatibility tests rather than path-set tests.

### A-02 — Typed task/run/attempt records and the state-control interface are incomplete

The routed task and task analysis require typed immutable task, run, and attempt records. The current Python boundary defines `TaskIntakeV1`, `TaskProjection`, and `LeaseGrant`, but no versioned `FactoryTaskV1`, `FactoryRunV1`, `FactoryAttemptV1`, or `FactoryEventV1` snapshot contracts. `attempt_no` exists only in PostgreSQL; it is absent from `LeaseGrant` and from every API response. Show/list return only the mutable task projection, with no bounded run/attempt/event inspection operation.

The roadmap's normal M4 graph includes `leased -> analyzing -> implementing -> verifying -> reviewing -> ready_for_human`, and `state.py` declares those transitions. However, `authorize_transition` is unused by the store/service/API, there is no fenced phase-transition operation, and a completed `/v1/proposals` call moves a task directly from `leased` to `ready_for_human`. Thus the declared intermediate states are unreachable through the supported control boundary, and the supposedly authoritative transition policy is not on the production path.

Resolve this as one explicit architecture decision. The scope-consistent repair is to add closed immutable snapshot types plus bounded inspection and a fenced/idempotent phase-proposal command that routes every state mutation through the transition policy. If the intended M4 contract is deliberately only `queued -> leased -> ready_for_human`, then narrow the roadmap/state schema and remove the unreachable state-policy surface rather than carrying two state machines.

### A-03 — Work identity is coupled to transport replay identity

`TaskIntakeV1` computes `intent_digest` over the entire normalized intake, including `request_id` and time-varying M0 evidence, then derives its database idempotency key only from that digest. The API additionally requires the transport `Idempotency-Key` header to equal `request_id`. Consequently an otherwise identical active source/frozen-authority submission with a fresh request ID—or refreshed observation evidence for the same authority—does not return the existing task; it presents as a changed generation and may supersede it.

That conflicts with the stated boundary that exact logical work deduplicates while changed source or frozen semantic authority supersedes. Separate command replay identity from canonical work identity. Freeze and document the exact semantic fields that create a new task generation, and add concurrent/replay tests that vary only request/correlation IDs and refreshed equivalent observation evidence.

## Non-blocking model precision issue

`EDGE-FACTORY-CONTROL-POSTGRES` declares `max_retries: 2` and terminal action `dead_letter`, while synchronous store availability failures are returned as bounded 503 responses and are not automatically retried by that edge. The two retries belong to a persisted task's typed infrastructure-failure policy. The architecture should distinguish request/transaction failure behavior from task-attempt recovery so operators and future M5 consumers do not infer transparent SQL retries.

## Effect of the last two commits

Commit `3b1f9a5` adds command-local `safe.directory=<canonical-root>` to sanitized read-only Git invocations in release packaging and parity tests; it also records non-authoritative decision/mistake notes. Commit `9727bc3` rebuilds only the tracked `2.0.13` ZIP and sidecar. Neither commit changes `factory/`, the M4 change spec/architecture, `architecture/{adoption,system,rules}`, or canonical `governance/**/index.json`. Relevant authority/contract blob IDs are identical between `571cad7` and `9727bc3`.

The rebuilt ZIP has SHA-256 `57e6e00a6c5281fda33e1317d955dd5ca0e1a6f9467e60daa256a8919b408bcc` according to the inspected artifact/sidecar, and direct archive-to-tree comparisons matched the architecture adoption/system/rules, all three governance registries, and the factory OpenAPI bytes. Therefore these commits do **not** introduce a new M4 trust edge, datastore, secret, contract version, or governance rule.

They do change exact-state evidence. The prior receipts bind head `571cad7`, tree `9d29f25d...`, and fingerprint `2f9b3ec2...`; the current committed tree is `5feb9a74...`. Although the architecture content digest remains `cd475bc397dcba41b4584912d4a30b88262f86e155e7afa1ec1dc03184ee4a69`, exact-head architecture evidence changes from `4038a97b...` to `fa9558528cfdff6d3ba737d9749a529a24728125c24e28ae2ce98aab1eebfed4` because its exact head/diff/repository inventory changed. Governance evidence must consequently be rederived for the new exact head as well. `grok_status.py` correctly reports verification plus all five review receipts stale across repository/spec/architecture/governance bindings.

## Exit recommendation

Return the three blocking contract/interface findings to the single route-selected write owner. After the last product repair, rebuild the tracked package once, run `python3 scripts/grok_verify.py --mode pr`, dispatch all five selected independent reviews on that same final tree, record fresh receipts, and only then prepare PR delivery. The App-owned exact-SHA Trust CI check remains separate merge authority.
