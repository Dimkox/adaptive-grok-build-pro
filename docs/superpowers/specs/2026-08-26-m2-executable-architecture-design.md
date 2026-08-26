# M2 Executable Architecture — Frozen Design

## Status and approval

Approved for implementation by the user's earlier approval of the model-agnostic factory roadmap and the explicit 2026-08-26 instruction to continue. This document narrows that approved architecture into two delivery slices so the roadmap's own separation rule is not violated.

The completed-M1 adoption baseline is `25bfbe59ea188d9687b20a9caad19e7db3d031f8`. The active route's historical `base_commit=069fe8226addb8a1922dde3db4e753434baa3a3d` remains unchanged, but it is not the M2 architecture-diff baseline because it predates M1.

## Decision

M2 replaces the README K16 clique as architecture authority with two strict, canonical, repository-owned documents and deterministic evaluators. The K16 graph remains a decorative inventory regression only.

M2 is delivered as two dependent factory tasks:

1. **M2-A — executable source architecture:** schemas, target-owned model and rules, bounded loader, digests, semantic validation, contract baselines, deterministic text diagrams, exact-state diff, local fitness/risk evidence, verification/receipt integration, installer support, and documentation. M2-A does not mutate `trust-ci/**`.
2. **M2-B — independent enforcement:** an independently implemented external holdout floor and trusted attestation metadata consuming the frozen M2-A contract. M2-B changes no M2-A product implementation files and requires its own route, change package, branch, tests, and reviews.

Checked-in M2-B source will be only source-ready. M2 is externally complete only after a separately authorized operator rollout updates the external bundle/policy epoch and a fresh App-owned exact-SHA check proves it.

## Scope

M2-A includes:

- `architecture/system.yaml` and `architecture/rules.yaml` as canonical JSON text valid under YAML 1.2;
- strict Draft 2020-12 schemas for the system and rules roots;
- a dependency-free Python API for load, validate, normalize, digest, drift, diff, fitness, and diagram projections;
- current-source architecture for the local route/change/spec/evidence workflow and Trust CI boundaries without asserting live health or configuration;
- machine-readable baselines for existing Trust CI HTTP inputs/outputs and signed-envelope shapes;
- deterministic CLI and structured verification evidence;
- explicit applicability for every roadmap fitness category;
- a stable digest/evidence projection for future M4 consumption.

M2-A excludes:

- any `trust-ci/**` edit, deployed holdout/policy/image/key/trust-store/branch-protection change, or external write;
- any service, database, migration, queue, framework, provider adapter, Codex/Grok integration, systemd unit, factory runtime, scheduler, worker, broker, lease, retry loop, or production capability;
- automatic inference from README/K16, arbitrary rule code, shell, regex, network fetches, target application imports, or model output;
- a claim that local receipts or checked-in source are merge authority.

## Authority and compatibility

- M1 `change-spec.yaml` remains the typed authority for objective, criteria, risk, forbidden outcomes, rollback, and approvals.
- M2 system/rules are the architecture authority. Their digest is a separate exact-state binding; it never overrides M1.
- README diagrams and generated Mermaid views are projections, never authority.
- Existing M1 schema-v2 behavior, unchanged legacy v1 reading, criterion-bound receipts, and historical signed attestation verification remain compatible.
- Installer-delivered parser/CLI/schemas/templates must never create or overwrite a target repository's adopted model. Adoption is target-owned and explicit.

## Canonical documents

Two root schemas are used because the local zero-dependency schema engine supports a bounded subset and must not gain ambiguous conditional-schema behavior:

- `schemas/architecture-system.schema.json`
- `schemas/architecture-rules.schema.json`

Both documents require `schema_version=1` and the same stable `architecture_id`. Every authoritative object is closed with `additionalProperties: false`. Unknown versions, keys, duplicate JSON keys or stable IDs, BOM/trailing data, non-finite numbers, surrogates, excessive bytes/depth/nodes, symlinks, non-regular paths, and concurrent-read mutation fail closed.

The normalized composite digest is domain-separated:

```text
system_digest = sha256(canonical(normalized_system))
rules_digest  = sha256(canonical(normalized_rules))
schema_digest = sha256(canonical({system_schema_digest, rules_schema_digest}))
architecture_digest = sha256(canonical({
  contract: "adaptive-grok.architecture",
  contract_version: 1,
  schema_digest,
  system_digest,
  rules_digest
}))
```

Set-valued fields sort by stable ID or scalar value after duplicates are rejected. Ordered semantics are never silently reordered.

## System model

Every node has exactly the roadmap fields:

```text
id, type, owner, trust_domain, data_classification,
secrets, runtime, repository_paths, public_contracts
```

`secrets` contains stable secret-class metadata only, never values or paths to credential material. `runtime` distinguishes source-described from independently proven deployment facts. Repository paths and contract paths are canonical repository-relative, contained, no-follow references. Empty `.gitkeep` directories and examples do not fabricate public interfaces.

Every edge adds a stable `id` to the roadmap fields:

```text
id, from, to, type, protocol, direction, authentication,
network_policy, sync_or_async, allowed_data, failure_behavior
```

`from` is the initiator/capability user and `to` is the receiver/resource. Schema v1 accepts only `direction=from_to`; reverse capability is a separate edge. One edge represents one capability. Endpoint, secret, data, contract, signal, and trust-domain references must resolve.

The roadmap's duplicated `failure_behavior` is resolved as one edge object with:

```text
mode, timeout_ms, max_retries, idempotency,
correlation_id, terminal_action, observable_signal
```

Async background work requires bounded retries, idempotency, correlation, observable terminal failure, and `dead_letter` or reviewed `manual_recovery` behavior.

The seed graph models current source boundaries: local route/policy, change/spec/evidence, local verifier, Trust CI API, PostgreSQL, worker/App publisher, exact-SHA workspace, Docker execution boundary, isolated runner, external holdout, GitHub, and human approval actor. It explicitly records privileged unauthenticated Docker Engine access as an existing constrained risk. It does not add future M4-M6 components.

## Rules and fitness

`architecture/rules.yaml` uses fixed, closed collections rather than executable expressions or a generic mini-language:

- forbidden edges and module/package boundaries;
- public API/event/schema compatibility policies;
- migration expand/migrate/contract policies;
- tenant/authorization policies;
- network-client controls;
- production-import boundaries;
- implementation/Trust-CI mutation separation;
- changed-code size and AST-complexity budgets;
- background-job requirements;
- secret-flow and workspace trust-material isolation;
- monotonic architecture risk escalations.

Every mandatory category returns exactly one deterministic result: `pass`, `fail`, `not_applicable`, or `unsupported`. `unsupported` fails the gate. `not_applicable` is computed by the engine from declared inventory plus exact changed paths and includes its predicate, scanned paths/subjects, reason code, and inventory digest. A newly matching or unsupported artifact revokes non-applicability.

Supported compatibility checking is intentionally conservative and directional. Removed operations/events/properties, newly required inputs, narrowed input types/enums, widened producer outputs, weakened authentication, reused event meaning, destructive migration changes, and unmodelled source/contract drift fail. Unsupported schema constructs produce `unsupported`, never an optimistic pass.

Risk ordering is `green < yellow < red` and is monotonic:

```text
risk_post = max(route/spec risk_pre, highest architecture trigger)
```

New edges, contracts, jobs, network clients, secrets, datastores, services, queues, frameworks, external integrations, or trust-domain crossings remain visible as triggers even when pre-risk is already red. Architecture-significant changes revoke documentation-only exemptions. The engine may require approval; it cannot grant it.

## Exact-state diff and evidence

The adoption base is the exact completed-M1 SHA. Absence of both architecture documents at that one base is `baseline_introduced=true`, not an empty diff. After adoption, missing either document fails closed.

Exact evidence requires clean exact base/head commits and NUL-delimited changed paths. Dirty worktrees may produce diagnostic evidence explicitly labelled `head_kind=worktree`, never exact-SHA evidence. Diff output binds base/head SHA and component digests and reports sorted added/removed/changed nodes, edges, rules, contracts, classifications, secrets, and runtimes.

The digest-bearing evidence core includes contract version, exact base/head, schema/system/rules/architecture digests, contract and repository inventory digests, diff digest, every fitness result, risk pre/escalation/post, exemption state, required scopes, and overall status. Timestamps, host paths, durations, logs, and source bodies stay outside the core.

Receipts adopt an architecture binding without weakening M1 spec binding. An architecture/schema/rules/declared-contract/base/head/fingerprint change stales all required M2 receipts.

Future M4 consumes only:

```json
{
  "architecture_contract_version": 1,
  "architecture_digest": "<sha256>",
  "architecture_evidence_digest": "<sha256>",
  "exact_base_sha": "<sha>",
  "exact_head_sha": "<sha>"
}
```

M4 does not parse K16, execute the local validator as trusted code, or persist mutable model contents as authority.

## CLI and diagrams

`scripts/grok_architecture.py` provides `validate`, `summary`, `diagram`, `diff`, `fitness`, and `drift`. Explicit paths remain repository-contained. Machine output is bounded, canonical, and stable; commands do not read mutable runtime state when exact inputs are supplied.

Five generated Mermaid text files live under `architecture/generated/`: context, container, deployment, data-flow, and trust-boundary. Ordering, escaping, labels, and LF line endings are deterministic; there are no timestamps or renderer dependencies. `diagram --check` regenerates in memory and fails on manual drift.

## Installer ruling

The installer manages architecture library modules, CLI, schemas, and a non-authoritative template. It does not copy `architecture/system.yaml` or `architecture/rules.yaml` into consumer repositories and never overwrites them with `--force`. A repository without explicit adoption reports `not_configured`; after adoption, deletion or corruption fails closed.

## Rollback and completion

M2-A has no migration or external state. Before adoption it can be reverted to the completed-M1 tree. After consumers bind contract v1, repairs use a forward fix or a new version; v1 meaning is never rewritten.

M2-A is locally complete only when focused/root verification, deterministic diagrams, gate-valid typed package, exact M2-A receipts, and all route-selected reviews pass. M2 as a whole remains incomplete until M2-B independent source is reviewed and its separately authorized deployed policy-epoch exact-SHA evidence exists.
