# M2 architecture ruling — executable architecture and fitness

Route: `0156034c05bd`  
Reviewed baseline: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`  
Decision: **proceed only as two bounded delivery slices with one frozen contract**

## Executive ruling

The smallest coherent M2 is a dependency-free, canonical architecture snapshot made from two strict JSON-compatible YAML documents, a deterministic evaluator/diff/diagram library, and a separately deployed independent enforcement floor. It models the current local workflow and Trust CI as directed components and trust/data flows; it does not model the README K16 clique, future factory services, or unverified deployment facts.

This cannot honestly be closed as one ordinary factory task. The roadmap's mandatory rule forbids combining implementation changes with `trust-ci/` or holdout mutation in one factory task, while the routed wording asks for both. The binding resolution is:

1. **M2-A, executable source architecture:** schemas, target-owned system/rules documents, local parser/CLI, deterministic diagrams/diff, local fitness integration, installer delivery, and evidence bindings. No `trust-ci/**` mutation.
2. **M2-B, independent enforcement:** independent holdout validator, trusted runner metadata extraction, attestation-v2 dual reader/emitter, server policy/approval-source changes, and operator rollout evidence. No product implementation change. It consumes the frozen M2-A schema and digest contract.

M2 is not externally complete until M2-B is deployed outside the pull-request trust domain and a fresh policy-epoch exact-SHA check proves it. A source-tree `trust-ci/holdout.example` file or local green receipt is not that proof.

The active route's `base_commit=069fe822...` predates the completed M1 work. It must not be used as the M2 architecture-diff baseline because that would attribute all M1 changes to M2. Freeze `25bfbe59ea188d9687b20a9caad19e7db3d031f8` and its tree fingerprint as the M2 bootstrap parent in the durable package. Keep the historical route value intact; record the bounded baseline override as evidence rather than rewriting route history.

## Binding representation

Use two schemas, not a conditional umbrella schema:

- `schemas/architecture-system.schema.json`
- `schemas/architecture-rules.schema.json`

The roadmap's singular `schemas/architecture.schema.json` is recommended structure, not a requirement. Two root documents need two independently usable root schemas, and the current standard-library validator deliberately does not implement `oneOf`/`if`/`then`. An umbrella schema would either be ambiguous or force unrelated schema-language expansion. Both schemas use Draft 2020-12 vocabulary limited to the locally implemented, preflighted subset, `additionalProperties: false` at every authoritative object, bounded collections/strings, and local `$defs` only.

Both `architecture/system.yaml` and `architecture/rules.yaml` are UTF-8 canonical JSON text, as M1 v2 established for JSON-compatible YAML. New M2 documents do not accept the historical YAML-subset decoder. Reject duplicate keys, BOM, non-finite numbers, trailing bytes, unsupported/unknown schema versions, unknown properties, surrogates, oversize/deep documents, symlinks, non-regular files, and concurrent-read changes. Canonical bytes are sorted-key, two-space JSON plus one newline. The semantic composite digest is:

```text
sha256(canonical-json({"rules": normalized_rules, "system": normalized_system}))
```

Normalization sorts nodes, edges, and rules by stable ID and sorts fields declared as sets. It must not erase ordered semantics. `architecture_id` and `schema_version=1` occur in both documents and must agree. Unknown future versions fail closed.

### System document

Each node has the roadmap fields plus the minimum discriminators required to evaluate them:

```text
id, type, owner, trust_domain, data_classification,
secrets, runtime, repository_paths, public_contracts
```

- `secrets` contains stable secret-class identifiers and metadata only, never values, credentials, key bytes, or permission to read them.
- `runtime` is a closed object describing kind and source/deployment status. An externally operated component is labelled as such; repository source must not assert live configuration or health.
- `repository_paths` are normalized repository-relative path prefixes with an explicit role. Absolute paths, `..`, backslashes/control characters, ancestor symlinks, and ambiguous ownership fail.
- `public_contracts` are typed records with stable ID, kind (`openapi`, `asyncapi`, `json_schema`, `event`, or `migration`), repository-relative path, and compatibility mode. Empty `.gitkeep` directories and example contracts do not fabricate a public interface.

Each edge must additionally have a stable `id`. Although the roadmap field list omits it, an ID is required to distinguish parallel edges and make a changed edge deterministic rather than an ambiguous remove/add pair:

```text
id, from, to, type, protocol, direction, authentication,
network_policy, sync_or_async, allowed_data, failure_behavior
```

`from`/`to` define the initiator and target. `direction` is limited to `one_way`, `request_response`, or `bidirectional`; it does not restate the endpoint names. All endpoints resolve, IDs are unique, and duplicate semantic edges are rejected.

### Duplicate `failure_behavior` resolution

`failure_behavior` exists **once, on the edge**, as the authoritative operational failure contract. Remove any duplicate edge property or nested `reliability.failure_behavior`. Background-job rules inspect this edge object; they do not redefine it.

It is a strict object with all fields required:

```text
mode: fail_closed | fail_open | degrade | retry_bounded
max_retries: integer 0..20
terminal_action: reject | degrade | dead_letter | manual_recovery
observable_signal: stable non-secret identifier
```

Synchronous/non-retrying edges use `max_retries=0`. An async background-job edge must have bounded retries, an observable signal, and a terminal `dead_letter` or explicitly reviewed `manual_recovery`. This removes the duplicate while retaining enough structure for deterministic fitness evaluation.

### Rules document

Do not accept executable expressions, shell, Python, arbitrary regular expressions, URLs, command names, or a free-form `parameters` object. Use fixed, schema-typed top-level collections whose entries have stable IDs:

- `forbidden_edges`
- `path_boundaries`
- `contract_policies`
- `migration_policies`
- `change_separation_policies`
- `code_budgets`
- `background_job_policies`
- `tenant_authorization_policies`
- `network_policies`
- `secret_flow_policies`
- `workspace_trust_policies`
- `risk_escalations`

Each collection has its own closed record shape. This is smaller and safer than a polymorphic `rule.kind + parameters` mini-language and remains implementable by the present hand-written schema subset. Rule severities in repository data may make local checks stricter but cannot weaken the external critical floor.

## Initial graph ruling

Model real runtime/source boundaries, not documentation inventory labels. The minimum current graph should contain logical components equivalent to:

- local route/hook control and local policy;
- durable change/spec/evidence packages and local verifier;
- Trust CI webhook/read API;
- Trust CI PostgreSQL durable state;
- Trust CI worker/App publisher;
- exact-SHA workspace and isolated runner;
- external holdout bundle;
- GitHub/GitHub App checks;
- external human approval actor/trust store boundary.

The directed edges include webhook intake, approval submission, API/worker PostgreSQL access, worker GitHub App publication, worker workspace allocation, isolated runner execution, and runner-to-mounted-holdout validation. The repository/factory side has no edge to CI signing keys, GitHub App private key, human private keys, production credentials, deployed policy, deployed holdout, or PostgreSQL administration. Those absences are enforced invariants, not undocumented assumptions.

The K16 README graph and `tests/test_structure.py` may remain unchanged as the repository contract currently requires. M2 diagrams never parse it and no fitness result cites it. Planned M4-M6 factory/provider/systemd components are not inserted as current nodes; the later factory consumes the stable `architecture_digest` and adds nodes only in its own reviewed architecture change.

## Deterministic library, CLI, diagrams, and diff

The library boundary should expose data-only functions equivalent to:

```text
load_snapshot(root, system_path, rules_path) -> ArchitectureSnapshot
validate_snapshot(snapshot, root) -> tuple[Finding, ...]
architecture_digest(snapshot) -> sha256
diff_snapshots(base, head) -> ArchitectureDiff
evaluate_fitness(snapshot, diff, changed_paths, risk_pre) -> FitnessReport
render_views(snapshot) -> mapping[view_name, bytes]
```

No function reads mutable `.grok-stack/runtime` state, fetches a URL, imports target application modules, chooses a command, or writes outside an explicit output directory. M4 consumes the snapshot version and digest API, not CLI stdout or Python object internals.

The CLI supplies `validate`, `summary`, `diagram`, `diff`, and `fitness`, with explicit `--root`, `--base`, `--head`, and deterministic `--json`. `diagram --check` compares generated bytes without rendering images. Generate five sorted Mermaid text projections—context, container, deployment, data-flow, and trust-boundary—from the same snapshot. Diagrams are projections, never authority. Escape Mermaid labels from a strict safe alphabet or deterministic encoder; node/edge ordering and line endings are fixed.

The diff is a versioned JSON record binding exact base/head SHA and base/head architecture digests. It reports nodes, edges, rules, contracts, trust domains, data classifications, secrets, and runtime changes as sorted added/removed/changed records with before/after values. It reads base documents with bounded `git show <exact-sha>:<path>` and head documents from the exact state under evaluation. It must not use the route's stale base, merge-base inference, README, or an arbitrary worktree.

Because M2 introduces the first model, missing architecture files at the frozen M1 base are a typed `bootstrap=true` diff, not an error and not an empty diff. Every head node/edge/rule is reported added; bootstrap requires architecture approval. After adoption, a missing/deleted system or rules file fails closed.

## Fitness and risk monotonicity

Every mandatory roadmap category has a named evaluator returning `pass`, `fail`, `not_applicable`, or `unsupported`, plus rule ID, stable finding code, subjects, and bounded evidence paths. `unsupported` is gate-failing. `not_applicable` is allowed only when the typed model and exact changed paths prove there is no subject; missing declarations or unavailable analyzers are not `not_applicable`.

For this Python repository, import/package checks use the standard-library AST. Contract compatibility is conservative and data-only for supported JSON/JSON-compatible OpenAPI/AsyncAPI/JSON-Schema forms: removed public operations/events/properties, newly required fields, narrowed enums/types, or changed event meaning fail. A declared applicable format that cannot be parsed safely is `unsupported`/fail, not pass. Migration checks layer typed expand/contract phase rules over the existing destructive/unbounded SQL check. Code budgets inspect changed regular files only with explicit byte/line/AST-complexity limits. Network, job, tenant/auth, secret, and workspace checks require both a model declaration and bounded source evidence; a newly detected undeclared subject fails and escalates.

Normalize pre-risk as the maximum of the routed risk mapped through M1 (`low/medium/high -> green/yellow/red`) and the active M1 v2 spec risk. Then:

```text
risk_post = max(risk_pre, highest_architecture_trigger)
```

Repository rules can never lower it. New internal dependency edges, public contracts, network clients, or background jobs are at least yellow. New service, datastore, queue, framework, external integration, secret, breaking contract/destructive migration, or trust-domain crossing involving Trust CI/human/production is red. Product-plus-Trust-CI/holdout mutation is red and fail. All trigger codes remain visible even when `risk_pre` is already red, as it is for this M2 route. Any architecture-significant diff cancels a documentation-only exemption. Risk escalation requests approval; it never grants authority or capability.

## Evidence interfaces and compatibility

- M1 `change-spec.yaml` stays intent authority. Do not add a mutable architecture digest to it. Architecture digest, exact baseline/head, diff digest, risk pre/post, and fitness summary belong in verification/receipt/attestation evidence envelopes.
- Adopt verification-report schema v2 when the architecture object becomes required. Adopt receipt schema v2 with `architecture_digest` and `architecture_fingerprint`. Old receipt v1 remains readable only for pre-adoption routes; it cannot satisfy an adopted M2 gate.
- The architecture fingerprint binds composite digest, exact base/head SHA, normalized contract digests, rules digest, and relevant changed paths. Any architecture/rule/declared contract/SHA change stales verification and every required review receipt.
- New Trust CI attestations should use payload schema v2 with required `architecture_digest`; do not silently reinterpret signed schema v1. The verifier must accept historical v1 and new v2, verify the exact original serialized payload retained in the envelope, and reject partial v2 metadata. The trusted runner derives the digest independently from exact-checkout bytes and does not import pull-request architecture code.
- M4's immutable packet interface consumes `{architecture_schema_version, architecture_digest}` only. Fitness reports and diagrams are evidence artifacts, not mutable packet authority.

## Independent holdout boundary

The deployed holdout is an independent minimum policy, not an executor for `architecture/rules.yaml`. It uses standard-library bounded parsing over exact base/head checkout bytes and duplicates only critical invariants: canonical schema/document presence after adoption, unique/resolved graph identity, safe repository/contract paths, forbidden implementation/control-plane mixing, trust/secret/workspace denial, monotonic risk triggers, and the no-access edges from repository/runner/factory to production trust material. It must not import `.grok-stack/adaptive_grok.architecture`, execute repository commands, load rule-supplied regex/code, or read CI/human secrets.

Repository rules may be more restrictive. Removal, downgrade, or omission of an externally mandatory rule fails the external floor rather than weakening it. The holdout bundle remains server-mounted and digest-pinned outside the checkout. The checked-in `trust-ci/holdout.example/architecture_validate.py` is rollout source only.

Before external activation, deployed policy must separately require a signed `architecture` approval scope for at least `architecture/**`, `schemas/architecture-*.schema.json`, the local validator/CLI/verification integration, and relevant Trust CI validator/metadata source. The current example policy does not cover all of these paths. A local route gate or protected-path grant is not that signed approval.

## Installer, adoption, rollout, and rollback

The installer manages the parser module, CLI, schemas, and a non-authoritative template under `.grok-stack/templates/architecture/`. It must **not** add `architecture/system.yaml` or `architecture/rules.yaml` to `MANAGED_FILES`, and `--force` must never overwrite a target repository's architecture authority. Target models are operator-owned and repository-specific.

Use an explicit target-owned adoption marker/config. Legacy installations without it remain compatible and report `not_configured`; once `grok_architecture init` creates a reviewed model/rules and enables adoption, missing or invalid documents fail closed. Deleting the model cannot disable the gate. This is the bounded compatibility boundary; there is no legacy M2 document decoder and no silent auto-inference from repository contents.

Rollout order is:

1. approve/freeze design, M1-complete baseline, schemas, digest, and report contracts;
2. merge M2-A through the then-current App-owned policy-epoch exact-SHA check, describing it only as local/source-ready;
3. implement M2-B against the frozen contract and prove historical attestation-v1 verification plus new v2 fixtures;
4. operator deploys the independently built runner/worker and holdout bundle, updates server policy/approval scope and branch protection to the new policy-epoch check, then runs fresh exact-SHA adversarial/normal validation;
5. only then record M2 external exit evidence and allow M4 to consume the digest.

Source rollback is a normal revert of the M2-A contract before adoption, or a forward fix/new schema version after consumers exist. Never rewrite an existing schema version. Deployed rollback is an operator-controlled reactivation of the previous immutable image, holdout digest, policy epoch, and matching protected check configuration; it requires fresh checks and approvals. Do not accept old local receipts or a check from another policy/head SHA. Architecture files are source data only, so no database recovery, backfill, external write, or migration is authorized by this design.

## Critical concerns before implementation

1. The active M2 package is still a placeholder v2 spec with `UNKNOWN` metric/target and no acceptance criteria, invariants, forbidden outcomes, signals, or approval scopes. It cannot pass a red-risk M1 gate or authorize implementation until completed and approved.
2. A one-PR/product-plus-holdout plan violates the mandatory separation fitness rule. Split it; do not create a bootstrap exemption in repository-controlled rules.
3. The stale route base would contaminate changed-path, diff, risk, and receipt evidence. Freeze the completed-M1 baseline explicitly.
4. PR-controlled rules cannot be the critical security authority. Independent deployed policy/holdout floors and signed architecture approval are required.
5. Do not claim M2 complete when only example holdout source exists. Source and deployed Trust CI are separate rollouts.
6. Do not auto-install or overwrite a consumer's model, and do not allow model deletion to opt out after adoption.
7. A generic mandatory evaluator that silently passes unsupported languages/contracts is worse than no evaluator. Unsupported applicable analysis must fail closed with a typed finding.
