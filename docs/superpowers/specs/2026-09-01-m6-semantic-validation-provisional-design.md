# M6 M5-Aligned Semantic Validation Design

## Status and boundary

This is the approved source design for provisional route `82aac86a3bf9`. Phase A merged exact M5 candidate `141e51e75b2bb337fa3bb1544639c6c46c287309` by a normal two-parent merge at `c398ea06daa635ad679e22c8cd29dbf74d2ae12c`. M4 candidate `aee6558bb83418d7a1acb4582df6845bf7bdc3c6` and M5 are still unaccepted and unpublished, so M6 remains provisional and must later restack in order M4 -> M5 -> M6. No compatibility, completion, release, Trust CI, human approval, provider execution, push, PR, or merge authority is claimed.

Canonical package: [`engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/`](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/brief.md). Current topology: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ this design ↔ [plan](../plans/2026-09-01-m6-semantic-validation-provisional.md) ↔ [release](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/release.md) / [rollback](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/rollback.md) / [evidence](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/evidence/README.md) / [ledger](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/implementation-ledger.md).

## Outcome and contract graph

M6 places independent semantic backpressure after immutable M5 finalization while preserving M5's meaning: only a `WorkspaceResultV1` whose exact persisted `m4_status` is `ready_for_human` may become a semantic subject. Failed M5 results keep their exact `failure_class` and `failure_reason`; M6 never reinterprets them as a semantic repair request.

```text
M5 TaskPacketV1 + RunManifestV1 + WorkspaceSnapshotV1 + WorkspaceResultV1
  -> SemanticExecutionBindingV1 (all exact task/run/fence/result/evidence facts)
  + authenticated SemanticValidationInputsV1 (facts absent from M5)
  -> existing SemanticSubjectV1
  -> append-only findings + coverage
  -> deterministic verdict
  -> PASS evidence, NEEDS_HUMAN, or bounded repair child proposal cycles 1..3
  -> new exact M5 result and a newly generated subject/evidence set after source mutation
```

Any producer digest or exact SHA mutation invalidates every downstream consumer. Forward recovery appends a new object and retains superseded evidence; it never edits an accepted semantic object. M7 can later consume only an immutable PASS envelope on the same exact head, but M7 compatibility and activation are outside M6.

## Exact M5 bridge

`SemanticExecutionBindingV1` is a closed, versioned, canonical record produced only after the M5 store has reparsed and cross-checked the immutable packet, manifest, snapshot, terminal proposal, artifact attestations, and result. It carries, without inference:

- `task_id`, `run_id`, `fence`, `owner`, `role`, `repository_id`, and `legacy_intent_digest`;
- complete packet authority/provider/capability/plan/workspace/acceptance/limit bindings through `task_packet_digest` and the canonical packet body;
- complete native/provider/workspace/deadline/stage bindings through `run_manifest_digest` and the canonical manifest body;
- `workspace_result_digest`, `workspace_snapshot_digest`, terminal stage/proposal, artifact/note/usage/diagnostic manifest digests, exact base/input/result head, `m4_status`, `failure_class`, and `failure_reason`;
- the exact terminal proposal body and sorted artifact-attestation identities returned by the additive M6 read capability, so aggregate manifests are never treated as individual attestations.

The bridge rejects cross-task/run/fence/packet/manifest/workspace/head substitution, non-writer packets, non-`ready_for_human` results, malformed or unverified bundles, and same-result/different-body replay. It does not call Git, a provider, Trust CI, or an external system.

M5 does not durably contain holdout/review evidence, typed requirements beyond `acceptance_ids`, route risk, diff limit, or a complete original writer context digest. These values therefore come from a separate closed `SemanticValidationInputsV1`, authenticated by the semantic coordinator capability and bound to the exact workspace-result digest. Acceptance-criterion references must equal the packet's acceptance IDs exactly; extra typed invariant, forbidden-outcome, architecture-rule, and non-functional references are explicit inputs, never inferred. The bridge derives `SemanticSubjectV1` deterministically: base/spec/architecture and owner from the packet, result head/diff size from the verified snapshot/result, authority digest from the canonical authority object, and deterministic-evidence digest from the complete execution binding. Supplied holdout/review/context/risk/diff-limit fields remain visibly separate.

## Durable evidence and capabilities

Forward migration `014_semantic_validation_bridge.sql` adds immutable semantic subjects, assignments, findings, coverage, verdicts, directives, child proposals, and recovery records. It does not rewrite frozen migration 013. Every row stores a closed canonical body and digest plus redundant exact M5 keys needed for SQL cross-binding. Direct `UPDATE`/`DELETE` is unavailable; exact replay returns the prior object and the same idempotency key with a different request digest fails closed.

Capability roles are non-login, non-inheriting, and disjoint:

- semantic coordinator may publish an exact verified subject/assignment and request a repair proposal through narrow functions;
- semantic validator may append finding/coverage only for its immutable assignment;
- semantic adjudicator may read canonical evidence and append one deterministic verdict/directive through narrow functions;
- factory runtime, implementer, validator, and adjudicator receive no direct semantic-table mutation; validator/adjudicator receive no application-write, provider, Git, Trust CI, approval, credential, network, external-write, or execution-finalization capability.

Security-definer functions fix `search_path`, revoke `PUBLIC`, validate bounded JSON and exact cross-links, and never accept raw chain-of-thought, provider streams, source bodies, secrets, credentials, or PII. Human-readable narratives remain bounded untrusted data.

## Adjudication and repair lifecycle

Existing pure contracts remain backward compatible. Independent validators bind findings and exact coverage to one subject and distinct writer context. Adjudication revalidates all bindings, derives recurrence identities independently of prose, and reports duplicates, correlations, contradictions, unsupported passes, and missing/contradicted coverage. Precedence is `needs_human > repair > pass`; a provider or implementer proposal cannot select the verdict.

A repair verdict can create at most one durable child proposal for each cycle `1..3`. The proposal binds the original parent task/run/fence/packet/manifest/result, exact result head, original writer, a fresh unused context digest, unchanged base/architecture/authority, finding identities, positive remaining budget, and a future deadline. It is distinct from M4 infrastructure attempts and `repair_count`. Actual execution is handed to the existing M5 execution plane through a narrow coordinator broker; M6 itself never writes an application workspace or invokes a provider.

Cycle four, recurrent finding identity, wrong writer, reused context, increased risk, excessive diff, changed base/architecture/authority, exhausted budget/deadline, stale evidence, or unsupported result disposition produces an immutable `needs_human` escalation and no child. A repaired source head requires a new M5 packet/manifest/snapshot/result and fresh deterministic, holdout, semantic, and review evidence; prior evidence cannot be relabeled.

## API, restart, and observability

Any HTTP surface is additive and contract-first. Read endpoints expose bounded semantic envelopes only after repository authorization. Validator/adjudicator command endpoints use dedicated scopes and accept closed bodies with idempotency keys; `task:execute` is insufficient. Responses omit raw provider bodies, prompts, stdout/stderr, credentials, and implementation reasoning.

Restart recovery scans incomplete semantic subjects/proposals by bounded keyset, resumes exact idempotent work, and never duplicates a verdict or child proposal. A stale/deadline/budget/fence condition appends a typed escalation. Fixed low-cardinality metrics are limited to outcome, escalation-reason class, lifecycle state, and recovery outcome; IDs, digests, prompts, repository paths, findings, and error prose are not labels.

## Rollout and verification

Migration, installer, API, and runtime changes are source-only in this branch. PostgreSQL tests use a disposable local database/container when available and otherwise report the missing host honestly; no shared database is touched. Focused TDD covers bridge mutations, schema/OpenAPI closure, SQL roles/idempotency/cross-binding, adjudication, repair ceilings, restart, metrics, installer symmetry, and current architecture inventory. Full route verification, independent review, receipts, PR delivery, external Trust CI, and acceptance remain parent tasks after the source is complete and restacked.

Deadline `2026-09-08T00:00:00+03:00` is a hard planning target, not a gate waiver.
