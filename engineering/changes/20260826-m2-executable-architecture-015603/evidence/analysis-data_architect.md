# M2 data architecture analysis — executable architecture contracts

Route: `0156034c05bd`  
Change: `20260826-m2-executable-architecture-015603`  
Role: route-selected `data_architect` (read-only analysis; this report is the only write)

## Ruling

M2 should introduce two strict, versioned data documents—`architecture/system.yaml` and `architecture/rules.yaml`—validated by one Draft 2020-12 contract with discriminated `$defs`. The files should contain canonical JSON despite the `.yaml` suffix, following the completed M1 convention. They model and validate the existing repository and Trust CI; they do not create a database, migration, service, queue, framework, provider adapter, factory table, or external write.

The stable M2 output for later M4 consumption is a composite `architecture_digest` plus its contract version and exact-state evidence. M4 must not ingest mutable model text as control-plane state, derive authority from K16, or invent a replacement architecture format.

## Source and baseline facts

- The M2 authority is `DARK_FACTORY_ROADMAP.md:356-443`. K16 remains decorative inventory, not an edge/data-flow source.
- The approved factory design requires M2/M3 to publish stable versioned intent-plane contracts before M4 and names `architecture_digest` as an immutable packet input. It explicitly defers `factory.*`, packets, leases, providers, adapters, and systemd topology.
- The active route's `base_commit=069fe822...` predates completed M1 and is not a valid M2-only comparison base.
- Completed M1 product source was independently reviewed at `98649e4e1e6a971fb802bc934eb5680de529e18a`; the current M2 branch parent is `25bfbe59ea188d9687b20a9caad19e7db3d031f8`, which also includes the M1 evidence/PostgreSQL closure commits. Use `25bfbe59...` as the M2 adoption/comparison base unless the owner records a different exact completed-M1 parent before implementation. Never silently reuse `069fe822...`.
- There is no exact M2 head yet: the M2 package is untracked at current `HEAD=25bfbe59...`. Exact-head architecture evidence cannot be emitted until the complete M2 tree is committed and clean.
- Existing migrations are checksum-locked, contiguous `001..003`, duplicated byte-for-byte under `trust-ci/sql/` and `trust-ci/src/adaptive_trust_ci/resources/`, and tested for drift. M1 later passed the isolated PostgreSQL integration `10/10` and the Trust CI suite `200/200` with no skips; that is local evidence, not deployment authority.
- Existing contract verification only checks JSON parseability and superficial OpenAPI/AsyncAPI markers. It is not compatibility analysis and must not be represented as such.

## Strict architecture document schema

Use one `schemas/architecture.schema.json` with `$id=urn:adaptive-grok:architecture:v1`, `additionalProperties: false` at every object, bounded arrays/strings/integers, and two discriminated roots selected by `document_kind`. Unknown versions, fields, enums, predicates, and formats fail closed.

### `system.yaml` exact root

```json
{
  "schema_version": 1,
  "document_kind": "system",
  "architecture_id": "ARCH-SYSTEM-001",
  "trust_domains": [],
  "data_types": [],
  "secret_types": [],
  "contracts": [],
  "nodes": [],
  "edges": []
}
```

All ID-keyed collections are sets with unique stable IDs and canonical sort order. Suggested patterns are `^ARCH-[A-Z0-9_-]{3,64}$`, `^TD-[A-Z0-9_-]{3,64}$`, `^DATA-[A-Z0-9_-]{3,64}$`, `^SECRET-[A-Z0-9_-]{3,64}$`, `^CONTRACT-[A-Z0-9_-]{3,96}$`, `^NODE-[A-Z0-9_-]{3,96}$`, and `^EDGE-[A-Z0-9_-]{3,96}$`.

Catalog entries should be exact objects:

- `trust_domain`: `{id, kind, owner}` where `kind` is a closed enum such as `repository_untrusted`, `local_preflight`, `trust_ci_control`, `trust_ci_execution`, `external_policy`, `external_platform`, or `production_trust`.
- `data_type`: `{id, classification, tenant_scoped, contains_secret}`. `classification` uses the fixed lattice below; booleans must be real booleans.
- `secret_type`: `{id, classification}`. It names a class only—never a value, locator, environment variable value, key body, or credential body. `classification` must be `trust_material`.
- `contract`: `{id, kind, path, version, role, compatibility}`. `kind` is one of `openapi`, `asyncapi`, `json_schema`, `signed_payload`, `cli`, or `sql_migration_set`; `role` is one of `producer`, `consumer`, or `bidirectional`; and `compatibility` is one of the bounded policies defined below. Paths are canonical repository-relative regular non-symlink files or declared migration directories; no URL is fetched.

Each node contains exactly the roadmap-required fields:

```text
id, type, owner, trust_domain, data_classification,
secrets, runtime, repository_paths, public_contracts
```

- `type` is a closed enum: `actor`, `local_component`, `service`, `worker`, `runner`, `datastore`, `repository`, `policy_bundle`, or `external_system`. Adding a new type is a schema change, not a free-form escape.
- `data_classification` is the maximum class the node may handle.
- `secrets` is a sorted unique list of `secret_type` IDs, never secret content.
- `runtime` is an exact object `{kind, lifecycle, network}` with closed enums. `kind`: `none`, `python_process`, `container`, `postgresql`, or `external_managed`; `lifecycle`: `none`, `on_demand`, `long_running`, or `job`; `network`: `none`, `local_only`, `declared_egress`, or `external_managed`.
- `repository_paths` is a sorted unique set of contained paths. Paths must reject absolute paths, `..`, backslashes, control/format/surrogate characters, symlinks, non-regular file targets where a file is required, and concurrent replacement.
- `public_contracts` is a sorted unique set of contract IDs. Empty means no public interface; `.gitkeep` never creates one.

Each edge adds a mandatory stable `id` to the roadmap fields and otherwise contains exactly:

```text
id, from, to, type, protocol, direction, authentication,
network_policy, sync_or_async, allowed_data, failure_behavior
```

- `from`/`to`, `allowed_data`, and any secret reference must resolve inside the document.
- `type` is a closed enum such as `dependency`, `control`, `data_flow`, `secret_flow`, `deployment`, or `publication`.
- `protocol` is a closed, reviewed enum for current reality: `none`, `filesystem`, `process_stdio`, `cli`, `git`, `http`, `https`, `postgresql`, `docker_api`, `github_webhook`, or `github_checks_api`. An unknown protocol is an architecture approval trigger, not an arbitrary string.
- `direction` is `from_to` or `bidirectional`; `sync_or_async` is `synchronous`, `asynchronous`, or `batch`.
- `authentication` is a closed enum (`none`, `local_os`, `database_role`, `github_app`, `signature`, `human_signature`, `mutual_tls`, `external_managed`). A `secret_flow` or `trust_material` edge cannot use `none`.
- `network_policy` is `no_network`, `local_only`, `allowlisted_egress`, `isolated_executor`, or `external_managed`. There is no `unrestricted` value.
- `allowed_data` is a sorted unique list of data-type IDs, not prose. Secret-bearing data requires `type=secret_flow` and an independently allowed domain pair.
- `failure_behavior` is an exact object `{mode, timeout_seconds, maximum_retries, observable_failure, dead_letter}`. Enums and bounds are fixed; background-job fitness applies stricter semantics. `dead_letter` describes behavior (`none`, `durable_record`, `manual_reconciliation`) and must not imply a queue that does not exist.

### Classification lattice and flow semantics

Use one code-owned total order, never a document-provided ordering:

```text
public < internal < confidential < restricted < trust_material
```

Recommended current data categories include repository source, typed change intent, architecture/rules, public API/event/schema contracts, migration DDL, job identity, policy/holdout digests, approval envelopes, signed attestations, and audit metadata. Treat approval envelopes and credential-bearing connection material as at least `restricted`; private approval, CI signing, GitHub App, database, provider, or production credentials are `trust_material`.

Flow validation must enforce:

1. A node's maximum classification is at least every declared data type it handles.
2. An edge carries only explicitly listed data types and cannot silently downgrade classification.
3. Any declassification requires a separately modeled, approved transformation; M2 should not seed one.
4. `tenant_scoped=true` revokes tenant-rule non-applicability and requires server-side tenant filter plus authorization evidence.
5. Secret values never appear in model, rules, findings, diagrams, evidence, logs, or digests. Only stable secret-type IDs appear.
6. Human approval private keys, CI signing private keys, GitHub App private keys, deployed holdout/policy material, and production credentials are never accessible from repository-controlled, runner, or future factory domains. The independent holdout must hard-code this minimum invariant so a PR cannot loosen it in `rules.yaml`.

## Strict rules document schema

`rules.yaml` has this exact root:

```json
{
  "schema_version": 1,
  "document_kind": "rules",
  "ruleset_id": "ARCH-RULESET-001",
  "supported_languages": ["python", "sql", "json", "canonical_json", "openapi", "asyncapi"],
  "rules": []
}
```

Every rule is an exact discriminated object:

```text
id, category, severity, critical, required_enforcement,
applicability, config
```

- `id` is stable (`FIT-*`) and unique.
- `category` is one of the mandatory M2 categories: `forbidden_edge`, `module_boundary`, `public_api_compatibility`, `event_schema_compatibility`, `migration_expand_contract`, `tenant_authorization`, `network_client`, `production_import`, `implementation_trust_mutation_mix`, `code_budget`, `background_job`, `secret_flow`, or `trust_material_isolation`.
- `severity` is `error` or `warning`; mandatory security/trust/data/API categories are `error`.
- `critical` is boolean. Critical system/schema, secret/trust isolation, and implementation-plus-Trust-CI/holdout-mutation rules require independent enforcement.
- `required_enforcement` is `local`, `external_holdout`, or `both`. This is a requirement, not a claim that a deployed holdout already enforces it; observed enforcement belongs only in evidence.
- `applicability` is exact `{scope, path_globs, node_types, edge_types, contract_kinds}`. `scope` is `changed`, `whole_tree`, or `both`. Globs use one documented bounded path-glob subset; forbid absolute paths, backslashes, `..`, character classes, braces, negation, shell expansion, and user-supplied regex execution.
- `config` is a schema-discriminated exact `$def` selected by `category`. Never accept generic expression text, Python, shell, arbitrary regex, command names, import strings that become commands, network locations, or model-generated code.

Category-specific configs should expose only finite deterministic inputs: allowed/forbidden node or edge ID pairs; source path prefixes and forbidden import prefixes; contract IDs and compatibility mode; migration path sets and phase policy; recognized network-client AST calls; changed-code byte/line/complexity thresholds; and background-job requirements. Unsupported language syntax or contract keywords produce `fail`/`needs_architecture_approval`, never pass or not-applicable.

The rules document is repository-controlled data. It may define stricter local policy but cannot weaken the independently implemented minimum rule set. The holdout must verify the presence and exact semantics/digest of critical rules without importing or executing `.grok-stack/adaptive_grok.architecture`.

## Canonicalization and digest contract

Reuse M1's defensive read posture, not merely `json.loads`:

1. Read each fixed path through descriptor-relative containment with `O_NOFOLLOW`; require a regular file, a fixed byte limit, stable inode/size/timestamps during read, strict UTF-8, no BOM, NUL, surrogate, control/format path characters, or trailing data.
2. Parse with duplicate-key rejection and non-finite-number rejection; cap depth, total nodes, arrays, strings, files, findings, and output bytes.
3. Validate schema and semantic cross-references before canonicalization. Invalid input has no semantic architecture digest.
4. Normalize set-valued arrays by their declared stable key (`id` or scalar value), normalize paths to canonical `/`-separated repository-relative text, and preserve order only where the schema explicitly declares semantic order. Reject duplicates before sorting.
5. Serialize with UTF-8, sorted object keys, compact separators, `ensure_ascii=false`, `allow_nan=false`, and no timestamp/random/host-path fields.

Publish component and composite digests:

```text
system_digest = sha256(canonical(normalized_system))
rules_digest  = sha256(canonical(normalized_rules))
schema_digest = sha256(exact committed schema bytes)

architecture_digest = sha256(canonical({
  "contract": "adaptive-grok.architecture",
  "contract_version": 1,
  "schema_digest": schema_digest,
  "system_digest": system_digest,
  "rules_digest": rules_digest
}))
```

For parse/validation failure evidence, retain bounded `system_raw_sha256` and `rules_raw_sha256` where readable, set semantic/component/composite digests to null, and fail. This preserves provenance without blessing malformed bytes, matching the lesson from M1's malformed-spec handling.

Canonical diagrams and summaries derive from the normalized semantic documents but are not included in `architecture_digest`; they are reproducible projections checked byte-for-byte. Their own artifact digests belong in evidence. Manual diagram edits fail regeneration and never change architecture authority.

## Contract compatibility semantics

Every declared contract binds exact base/head file digests, parser/version, role, and compatibility mode. Compatibility must compare the contract at exact commits, not only inspect changed working-tree text.

Use directional language-set semantics:

- `consumer_accepts_old`: all payloads accepted under the base contract remain accepted by the head consumer (`L(base) subset L(head)`). This prevents narrowing inputs.
- `producer_accepted_by_old`: all payloads emitted under the head contract remain acceptable to the base consumer (`L(head) subset L(base)`). This prevents widening outputs beyond old consumers.
- `bidirectional`: both checks.
- `exact`: canonical contract meaning must not change under the same version.
- `versioned_break`: permitted only with a new major/versioned ID, explicit old+new coexistence/deprecation evidence, architecture approval, and no silent meaning change to the prior ID.

For OpenAPI, fail on removed operations/responses, newly required inputs, narrowed input schemas, incompatible response widening, authentication weakening, or unchanged-version meaning changes. For AsyncAPI/event schemas, fail on removed channels/messages, changed business meaning, incompatible producer output, required consumer behavior changes, or reuse of a versioned event ID with new semantics. For JSON Schema, implement only a documented finite keyword subset; full JSON Schema inclusion is not generally decidable by superficial diff. Unknown combinators/formats/unevaluated semantics fail closed and require architecture approval.

The existing examples under `examples/contracts/` are fixtures unless explicitly referenced by `public_contracts`; empty `engineering/contracts/**` directories are not contracts. Existing `_contracts()` marker checks may remain a syntax precheck but cannot satisfy any M2 compatibility rule.

M1 compatibility is mandatory: schema-v2 typed specs and criterion/fingerprint bindings remain current, historical v1 specs remain read-only compatibility, and pre-M1 signed schema-v1 attestations verify against their original serialized payload. If M2 adds optional architecture metadata to the existing attestation JSONB payload, the metadata is all-or-none, strictly normalized, absent for old signed payloads, and verified from the original signed mapping. No SQL column or migration is needed.

## Migration expand/contract fitness semantics

M2 adds no migration. It models the existing Trust CI PostgreSQL datastore and both checksum-mirrored migration locations, then evaluates migration fitness only when the exact base/head diff touches a declared migration set or introduces a datastore/migration path.

The state machine is:

```text
expand -> migrate/backfill -> contract
```

- **Expand:** additive and old-code compatible. New tables/columns/indexes or parallel versioned structures are allowed only with lock/query-plan reasoning. New required columns need a safe default or staged nullable population. No drop, rename, type narrowing, immediate `NOT NULL`, destructive rewrite, history edit, or old-reader break.
- **Migrate/backfill:** bounded, resumable, idempotent, observable, reconciled, tenant-safe, and stoppable. Evidence declares cursor/checkpoint, batch limit, timeout, retry bound, progress/failure metrics, validation query, stop condition, and forward recovery. It does not remove the old representation.
- **Contract:** removes or tightens only after exact evidence identifies a previously delivered expand step, all readers/writers are migrated, the compatibility window is complete, reconciliation passes, rollback/forward recovery is documented, and the required human-signed destructive/migration approval is present. Expand and contract for the same compatibility boundary cannot be collapsed into one unproven release.

Additional immutable-history rules:

1. Existing numbered migration bytes, version, and name never change or disappear; checksum drift fails.
2. Versions are unique and contiguous according to the declared migration-set convention.
3. `trust-ci/sql/` and packaged resource copies remain byte-identical.
4. Generic token scanning (`DROP`, `TRUNCATE`, unbounded `DELETE`/`UPDATE`) remains a coarse safety check, not proof of expand/contract correctness.
5. Unsupported SQL dialect or ambiguous DDL fails closed and requests architecture/migration review.

For the M2 change, the correct result is `not_applicable` only if the recorded exact M2 base/head changed-path set contains no SQL/migration path and introduces no datastore. The result must still enumerate the scanned declared migration paths and their unchanged inventory digest. It is not valid to say “no database exists”: the repository already contains the Trust CI PostgreSQL system.

## Applicability and `not_applicable` evidence

Every mandatory category emits exactly one typed result. Silence is failure. Use a discriminated result union:

```json
{
  "rule_id": "FIT-MIGRATION-001",
  "status": "not_applicable",
  "applicability": {
    "scope": "both",
    "predicate_id": "changed_declared_migration_path",
    "scanned_paths": ["trust-ci/sql", "trust-ci/src/adaptive_trust_ci/resources"],
    "matched_paths": [],
    "matched_node_ids": ["NODE-TRUST-CI-POSTGRES"],
    "matched_edge_ids": [],
    "matched_contract_ids": ["CONTRACT-TRUST-CI-MIGRATIONS"],
    "inventory_digest": "<sha256>"
  },
  "reason_code": "no_changed_declared_migration",
  "findings": []
}
```

Pass has no `reason_code` and an empty findings list; fail has one or more bounded typed findings; not-applicable has a closed reason code and no findings. Conditional schema/semantic checks enforce the variant.

Not-applicable is engine-derived, not author-selected. It is allowed only when both the current architecture inventory and exact base/head changed paths fail to trigger the category. A newly matching path, contract, datastore, job, network client, secret, tenant-scoped data type, or trust-domain crossing revokes not-applicable. An unsupported new language/artifact is `fail` with `undeclared_or_unsupported_artifact`, not not-applicable. A rules edit cannot hide a previously applicable category.

Minimum closed reason codes should include `no_declared_contract_kind`, `no_changed_declared_migration`, `no_tenant_scoped_data`, `no_background_job`, and `no_supported_artifact_in_scope`. Evidence still records scopes, exact scanned paths/IDs, and inventory digest so reviewers can distinguish genuine absence from an empty scan.

## Exact base/head architecture evidence

PR/release evidence should be one bounded canonical object with no timestamp in its digest-bearing core:

```json
{
  "schema_version": 1,
  "evidence_kind": "architecture_verification",
  "architecture_contract_version": 1,
  "repository": "<trusted owner/name>",
  "base_sha": "<40 lowercase hex>",
  "head_sha": "<40 lowercase hex>",
  "bindings": {
    "schema_digest": "<sha256>",
    "base": {"status": "present|absent_at_adoption", "system_digest": null, "rules_digest": null, "architecture_digest": null},
    "head": {"system_digest": "<sha256>", "rules_digest": "<sha256>", "architecture_digest": "<sha256>"},
    "contract_inventory_digest": "<sha256>",
    "repository_inventory_digest": "<sha256>"
  },
  "diff": {
    "added_nodes": [], "removed_nodes": [], "changed_nodes": [],
    "added_edges": [], "removed_edges": [], "changed_edges": [],
    "changed_contracts": [], "changed_data_types": [], "changed_secrets": [],
    "changed_rules": []
  },
  "fitness": {"rules_digest": "<sha256>", "results": [], "status": "pass|fail"},
  "risk": {"pre": "red", "escalation": "red", "post": "red", "exemption": "none"},
  "status": "pass|fail"
}
```

`absent_at_adoption` is allowed only for the single recorded M2 adoption base and makes the initial full model addition visible. After adoption, an absent model/rules file fails. Null component fields are permitted only in that exact variant.

The evidence digest is SHA-256 over canonical normalized evidence. Human-readable timestamps, host paths, temporary roots, process IDs, durations, and logs remain outside the digest-bearing core. Findings use stable codes and bounded repository-relative locations; never embed source, contract bodies, SQL bodies, secrets, or arbitrary stdout/stderr.

Exact-state requirements:

1. Base/head must be existing exact commits; workspace `HEAD` must equal `head_sha`.
2. Use `git diff --name-only -z --no-renames base head --`, not the current local `changed_files()` union of route-base, staged, unstaged, and untracked paths.
3. Authoritative PR/release evidence requires a clean tracked/untracked product tree. A dirty local tree may produce draft diagnostics but not exact-head evidence.
4. Base/head, schema/model/rules/contract inventories, fitness results, risk, and generated artifact digests bind together. Any change makes receipts/reviews stale.
5. Local evidence remains preflight. Only the externally deployed App-owned policy-epoch check on the exact head SHA is merge authority.

## Safe future M4 consumption

M4 should persist or packet-bind only this stable projection from independently validated M2 evidence:

```json
{
  "architecture_contract_version": 1,
  "architecture_digest": "<sha256>",
  "architecture_evidence_digest": "<sha256>",
  "exact_base_sha": "<40 lowercase hex>",
  "exact_head_sha": "<40 lowercase hex>"
}
```

The M4 packet builder must receive these fields from trusted validated durable records, verify supported contract version and exact SHA binding, and include them in the packet digest. It must not parse K16, execute the PR-controlled M2 validator, accept architecture paths/commands/capabilities from untrusted content, or copy whole model/rules/findings into `factory.*`. A changed architecture/rules/schema/evidence digest creates a new packet/run; nothing is edited in place.

M2 must not pre-create M4 tables, migrations, packet schemas, provider fields, leases, retries, schedulers, brokers, adapters, or systemd units. Existing Trust CI PostgreSQL remains independent and authoritative only for `trust_ci.*`; no M2 field belongs in a new database column merely to prepare for M4.

## Seed-model data guidance

Model current source/deployment boundaries only: local route/change/spec/verification components; Trust CI API, worker, PostgreSQL, isolated runner, external holdout/policy, and GitHub App integration. Do not add planned factory, provider, Codex/Grok, note-broker, or M4 PostgreSQL nodes.

At minimum, declare data types for source/contract bytes, M1 change spec, M2 architecture/rules, PR/job exact-SHA identity, policy/holdout digests, approval envelope, criterion coverage, and signed attestation. Declare secret classes for GitHub App, CI signing, database credentials, human approval private keys, and production credentials, while explicitly showing that runner/repository/future factory domains have no access to the last four trust classes. Public trust-store keys are not secrets but remain integrity-sensitive configuration.

## Required data-focused tests

- Schema: exact keys, enum/version rejection, duplicate IDs/keys, unresolved references, bounded structure, unsafe paths, symlink/non-regular/concurrent-read rejection.
- Digests: input key/order/path order invariance where declared set-valued; semantic edit changes the correct component and composite digest; malformed bytes retain only raw provenance.
- Classification: classification ceiling, secret-flow authentication/network, prohibited trust-domain pairs, tenant-scoped trigger, no implicit declassification.
- Contracts: positive additive and negative breaking OpenAPI/AsyncAPI/JSON-Schema fixtures in each direction; unsupported semantics fail closed; same-version meaning changes fail.
- Migrations: existing checksum drift/removal/version gaps/mirror mismatch; expand/migrate/contract fixtures; destructive or ambiguous DDL; bounded backfill evidence; exact no-change not-applicable proof.
- Applicability: every mandatory category returns pass/fail/not-applicable; new matching/unsupported artifacts revoke not-applicable.
- Evidence: exact base/head, adoption-only absence, dirty-head rejection, component/inventory/risk staleness, monotonic `post=max(pre, escalation)`.
- Compatibility: M1 v2 gate and receipts remain green; unchanged historical v1 spec reading and old signed attestation verification remain green; no SQL migration is added.
- Holdout: independent bounded implementation, no local architecture import, critical minimum rules cannot be weakened by edited `rules.yaml`, and source-local pass cannot assert deployed enforcement.

## Critical concerns

1. **Wrong baseline contaminates all evidence.** The route base predates M1. Record the exact M2 adoption base—currently `25bfbe59...`—before diffing, and do not claim an exact head while the M2 tree is untracked/dirty.
2. **A generic `config` or regex/expression field becomes an execution/bypass surface.** Use category-discriminated exact configs and a bounded supported path-glob/AST/contract subset; unsupported input fails closed.
3. **Not-applicable can become silent pass.** It must be engine-derived from both inventory and exact changed paths, with reason code, scanned scope, matches, and inventory digest. New or unsupported artifacts revoke it.
4. **Current contract checks are not compatibility proof.** Directional producer/consumer semantics and exact-base/head comparison are required; unsupported JSON Schema/OpenAPI/AsyncAPI semantics need approval, not optimistic acceptance.
5. **Migration fitness must not invent a migration.** Model the existing Trust CI PostgreSQL and immutable mirrored migrations, emit exact no-change evidence for M2, and add no DB/table/column merely for architecture metadata.
6. **Repository-controlled rules cannot protect their own trust boundary.** Critical schema, secret/trust isolation, mixed Trust-CI/implementation mutation, and monotonic-risk invariants need independently implemented holdout/server-policy checks; checked-in source proves only local readiness.
7. **M4 must consume a digest contract, not mutable architecture data.** Publish one versioned composite digest and exact evidence projection; keep factory schemas, packets, leases, providers, and persistence out of M2.
