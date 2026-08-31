# Requirements reconciliation — M1 and model-agnostic local factory roadmap

## Scope ruling

M1 is the model-neutral **intent-and-evidence contract** required by the future autonomous local service.  It must not contain a Codex-specific field, provider SDK dependency, agent scheduler, `systemd` unit, workspace launcher, durable task queue, or automatic external-write capability.  Those are later, separate vertical slices: M4 owns durable orchestration and limits, M5 owns local/background execution and backend adapters, M6 owns independent semantic validation/repair, and M7 owns external PR operations.  This preserves a stable contract for Codex first and future backends without prematurely creating the factory service.

The approved user constraint is therefore a forward-compatibility constraint on M1, not authorization to implement M4–M9 in this route.  Ignore issue/PR/task `#10`; it contributes no scope or acceptance criterion.

## M1 acceptance criteria (observable)

1. **Typed, backend-neutral authority.** New or modified `change-spec.yaml` is bounded UTF-8 canonical JSON (valid YAML 1.2), schema-version 1, and is the only authority for objective, risk, AC/INV/FORBID/SIG IDs, evidence mappings, contracts, observability, rollback, and approvals.  No field names a model, provider, Codex, agent prompt, systemd service, lease, or worker implementation.
2. **Fail-closed validation.** Local draft/gate validation rejects malformed/unbounded input, unknown properties, duplicate logical IDs/JSON keys, invalid identifiers, invalid risk or rollback values, unresolved production signals, and incomplete standard/high-risk criteria.  Only draft generation may use `UNKNOWN` in the two explicitly allowed objective fields.
3. **Deterministic route-to-spec generation.** A new package copies known route task/domains and maps low/medium/high to green/yellow/red; it neither fabricates success targets nor silently inherits model/provider state.  Markdown templates link to, but cannot override, the typed values.
4. **Criterion-bound local evidence.** CLI JSON results, coverage, canonical digest, and fingerprint are deterministic.  Receipts persist canonical criterion IDs plus spec digest/fingerprint; a changed spec, declared contract, applicable base/head, or tree makes evidence stale.  PR/release validation gates changed/new non-exempt specs; fast mode is draft-only.
5. **Independent trusted enforcement.** The external holdout independently validates changed/new specs using only bounded byte/data reads and stdlib parsing; it does not import or execute local/PR validator code.  Trust CI independently creates deterministic composite digest/coverage metadata from sorted changed paths and signs it with the existing exact-SHA attestation.
6. **Final M1 evidence.** This active package’s fully completed yellow-risk spec maps every AC to focused test/receipt/attestation evidence, all required local checks and the code/test/security/release reviews bind to the final fingerprint, and merge remains contingent on the App-owned exact-head check and any externally required approval scope.

## Invariants that enable the later model-agnostic service

| Invariant | M1 enforcement now | Later owner |
| --- | --- | --- |
| Intent/evidence is portable across Codex and future backends | Typed schema and receipt/attestation contracts contain business/evidence identifiers, never provider implementation details. | M5 records selected backend/model in its immutable run manifest. |
| A backend cannot self-certify business correctness | Local receipts are preflight only; holdout and Trust CI evidence are independent. | M6 adds independent semantic validator/adjudicator; M8 never promotes a backend based on self-reported evidence. |
| Exactly one application-code writer | M1 does not claim to technically enforce it; its evidence IDs can describe a writer-control criterion. | M4 durable lease plus M5 isolated workspace enforce it. |
| At most 20 concurrent read/note agents | No M1 scheduler or concurrency counter.  The typed spec remains able to state this as a future operational constraint without assigning it false evidence. | M4 enforces configured read/note WIP ceiling and audit records. |
| Restart-safe, bounded local autonomy | No background daemon, retry worker, or persistent task state in M1. | M4 owns task/attempt/lease/dead-letter state; M5 owns systemd deployment, process restart, orphan reconciliation, and run manifest. |
| No automatic external writes | M1 does not introduce GitHub, deployment, approval, comment, or production mutation code; no typed evidence or receipt becomes such authority. | M7 only after separate approval may perform branch/PR actions; production remains M9 and human-controlled. |
| Trust boundary survives backend change | Signed attestation derives data only from exact changed specs, not from a Codex or future-provider implementation. | M0/Trust CI remains independently deployed and policy-owned. |

## Backward-compatibility rulings

1. **Specs:** unchanged historical YAML packages are not mass-migrated and are ignored by changed-spec gate discovery.  New/generated and modified specs use strict canonical JSON.  Legacy parsing is compatibility-only and must never allow a modified spec to evade the canonical/strict path.
2. **Package IDs:** preserve the route-generated change ID (`20260826-m1-typed-intent-evidence-rebuild-a4f882`) as the package locator.  Do not require a new `CHG-*` locator in a way that makes the active route invalid; if `CHG-*` is required, it needs a distinct, explicitly versioned field rather than replacing route identity.
3. **Receipts:** prior receipts lacking `criterion_ids`, `spec_digest`, or `spec_fingerprint` remain readable as historical records.  They are insufficient as current gate evidence when the active spec declares criterion binding; never synthesize missing bindings.
4. **Attestations:** `AttestationPayload` remains schema version 1.  `from_dict()` supplies `spec_digest=None` and empty normalized coverage for pre-M1 signed payloads, preserving signature verification of their original serialized bytes.  New fields are optional, deterministic, and emitted by new writers only.
5. **Public interfaces:** `grok_spec validate|summary|coverage [path] [--json]` and explicit-path operation are the supported M1 interface.  Any prototype-only command/parameter compatibility is optional, but a compatibility alias must not weaken gate mode or produce ambiguous output.
6. **No repository-owned Trust CI rollout:** changing the source/example holdout is source compatibility work only.  Deployed policy, holdout bundle, image, trust stores, keys, and branch protection are outside this PR and require their own exact delegated rollout plus external evidence.

## Phase-boundary rulings

| Work | Include in M1 | Explicitly defer |
| --- | --- | --- |
| Typed business outcomes, criteria, evidence, risk, rollback, approvals | Yes | Model/provider selection, agent prompts, task packets, architecture model (M2) |
| Local validator, CLI, receipts, verification staleness | Yes | Durable task rows, `SKIP LOCKED` leases, retry/dead-letter, WIP/budget counters, global kill switch (M4) |
| Trust CI spec digest/coverage and independent holdout | Yes | Factory worker deployment and operational Trust CI policy/holdout rollout |
| Systemd persistence | No | M5 service unit, process lifecycle/restart drill, isolated workers and artifacts |
| Codex-first/future backend adapter | No implementation; preserve vendor-neutral M1 contract | M5 backend adapter, capability policy, model/run-manifest provenance |
| Twenty read/note agents and one code writer | No scheduler implementation; do not represent a prompt instruction as enforcement | M4 concurrency/lease enforcement and M5 workspace capability isolation |
| Retry and recovery | M1’s own validation must be bounded (size/depth/count/read limits) | Autonomous task retry/reclaim/attempt exhaustion (M4), bounded repairs (M6) |
| External writes | No new external mutation and no receipt/attestation authority escalation | M7 delegated branch/push/PR lifecycle; M8 narrowly-earned auto-merge; M9 human-gated delivery |

## Non-goals for this route

- `factory/`, root packaging changes, PostgreSQL factory schema, API/UI, webhooks, dashboard, systemd units, Codex SDK/backend adapter, task persistence, or a worker daemon.
- Multiple application-code writers, a 20-agent scheduler, unbounded repair/retry loops, model-specific policy, automatic push/PR/comment/merge/deploy/production writes, or creation of human approvals.
- M2 executable architecture, M3 learning/debt policy, M4/M5/M6/M7/M8/M9 implementation, GitHub Actions, mass legacy conversion, or reading secrets/approval keys.

## Required verification implications

- Add focused negative tests for malformed/unbounded/untrusted spec input, canonicalization, IDs/evidence/signals/red controls, draft-versus-gate profiles, explicit docs-only exemption, and unchanged-legacy exclusion.
- Add generation and CLI tests demonstrating no provider/model data leaks into the spec and deterministic explicit-path JSON output.
- Add receipt tests for sorted IDs and stale fingerprint after spec/contract/base-head changes, plus old receipt readability without treating it as current criterion evidence.
- Add holdout source/behavior tests proving no local-validator import and fail-closed changed-spec handling; add signed-payload tests for old schema-v1 inputs and deterministic new coverage.
- Before completion run root and Trust-CI discovery suites, compileall, PR verification, and all route-selected independent reviews on the final tree.  The external App-owned exact-SHA check remains the final merge gate; no local result authorizes an external write.
