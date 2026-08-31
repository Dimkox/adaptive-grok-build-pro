# M2 integration architecture analysis

## Status and ruling

**READY FOR DESIGN SYNTHESIS, WITH TWO BLOCKING INTERFACE DECISIONS.** M2 should publish a strict versioned architecture declaration, deterministic architecture-diff/evidence contract, and independently reimplemented critical fitness checks for the existing local workflow and Trust CI. It must not represent the README K16 clique as dependency truth, invent M4+ runtime components, or claim that checked-in holdout source is already deployed enforcement.

Baseline facts:

- Worktree HEAD is `25bfbe5`; route `0156034c05bd` names base `069fe8226addb8a1922dde3db4e753434baa3a3d`, which predates the completed M1 source. Exact M2 diff evidence needs a separately recorded completed-M1 adoption base; otherwise M1 changes are falsely reported as M2 architecture drift.
- M1 supplies strict canonical spec v2, spec digest/fingerprint, criterion-bound receipts, independent changed-spec holdout validation, and backward-compatible signed attestation metadata. M2 should parallel these interfaces rather than put mutable architecture state into the intent spec.
- The approved overall factory design requires M2 to expose a stable `architecture_digest` later consumed by immutable M4/M5 packets, while leaving `factory.*`, adapters, provider protocol, execution isolation, and external-write capability deferred.
- Current Trust CI policy pins an immutable no-network runner and external holdout bundle, derives signed approval scopes from changed-path globs before running holdout, and signs exact base/head/policy evidence. Repository code, example holdout, local receipts, and route state are not merge authority.

## Architecture graph: required edge semantics

The graph must model capabilities and flows, not visual adjacency. Every edge should have a stable `id` in addition to the roadmap fields. An edge ID remains stable across descriptive edits; changing either endpoint or the capability creates a semantic edge change.

### Canonical orientation

- `from` is always the actor that initiates or exercises the capability: caller, reader, writer, producer, deployer, or credential user.
- `to` is always the component or resource that receives the call/data/effect or provides the capability.
- Schema v1 should admit only `direction: from_to`. Reverse and bidirectional capabilities are separate edges with separate IDs. This avoids hiding reverse data/secret flow inside a single `bidirectional` label.
- `sync_or_async` is closed to `sync`, `async`, or `static`. `static` is for build/deployment/mount/dependency relations that are not runtime messages.
- One edge represents one capability. A worker that reads PostgreSQL, invokes Docker Engine, publishes a GitHub check, and mounts a checkout needs four edges, not one broad dependency.
- `type` is a closed enum with defined endpoint semantics, for example `invokes`, `receives`, `reads`, `writes`, `publishes`, `consumes`, `mounts`, `loads`, `verifies`, and `deploys`. Unknown relationship types fail closed instead of degrading to a decorative edge.

### Structured edge fields

The roadmap field names should be objects or bounded arrays, not free-form prose:

- `protocol`: `{family, version, transport}`; examples are HTTPS/JSON, PostgreSQL wire protocol, Docker API over TCP, process/JSONL, filesystem read-only mount, or in-process Python call. `unknown` is invalid for gate validation.
- `authentication`: `{mode, credential_ref, presented_by, verified_by, termination}`. `credential_ref` names metadata only and never contains a value or secret path. `none` is explicit and triggers a crossing rule; it must never be inferred as trusted merely because two containers share a bridge.
- `network_policy`: `{default, source_zone, destination, ports, enforcement}` with a closed `default` of `deny` or `allow_declared`. `enforcement` records the real control (container `--network none`, loopback bind, Compose network, firewall/allowlist, or `none`), not an intended future control.
- `allowed_data`: bounded records such as `{classification, purpose, flow}` where `flow` is `request`, `response`, or `from_to`. Sync request/response data therefore remains independently visible even though initiation is `from_to`.
- `failure_behavior`: `{timeout, retries, idempotency, terminal, observable_signal}`. Values are bounded structured facts; absent retry/dead-letter guarantees cannot be described as “handled”.

All endpoint references, credential references, data classes, public-contract references, network zones, and signals must resolve. Duplicate IDs, duplicate capability tuples, conflicting parallel edges, implicit reverse flow, unresolved references, or an edge whose protocol/authentication fields contradict its type fail validation.

### Node and trust-domain semantics

- `trust_domain` is an enforcement boundary, not an organizational label. Components sharing a repository or Docker Compose project do not automatically share a trust domain.
- `runtime` must distinguish `local_process`, `trusted_service`, `untrusted_sandbox`, `database`, `external_service`, and `static_artifact`, and distinguish source-described topology from independently proven deployment facts.
- `data_classification` should use a closed ordered set such as `public < internal < confidential < restricted < trust_material`. A receiver must be allowed for every data class on an incoming edge.
- `secrets` contains typed references and residence/use permissions, never values. Distinguish a resident private key from a derived short-lived token and from corresponding public verification material.
- `repository_paths` and `public_contracts` are canonical repository-relative, containment-checked, no-follow, existing regular-file references. Directory globs may be used only as bounded ownership coverage, not as proof that a contract exists.

## Existing integration graph that the initial model must tell truthfully

At minimum, the initial model should represent these actual separations and directed capabilities:

1. Local route/change/spec/verification/receipt components operate in the local advisory domain. Their output can feed a PR but cannot publish Trust CI status or human approval.
2. GitHub calls Trust CI API `/webhooks/github` over HTTPS; the API authenticates the raw body with the API-only HMAC webhook secret and accepts only the bounded pull-request action projection.
3. A human-controlled client submits an Ed25519-signed approval envelope to `/approvals`; the API verifies it against the public-only trust store and exact repository/PR/base/head/policy/nonce/expiry. The private approval key never crosses into this system.
4. Read clients call `/jobs/{job_id}`, `/attestations/{job_id}`, and `/metrics` with the API-only bearer token. Health endpoints are separately unauthenticated and bounded.
5. Trust CI API reads/writes PostgreSQL with the API database role. Trust CI worker claims and updates jobs/attestations with the worker role. Migration and backup identities remain distinct.
6. Trust CI worker calls GitHub over HTTPS using a worker-only GitHub App private key to mint a JWT and obtain a short-lived installation token, then creates/completes the exact-SHA Check Run. The App private key does not flow to GitHub or the runner.
7. Trust CI worker calls the privileged rootless Docker Engine over unauthenticated TCP on the isolated `executor` bridge. This is an existing high-value edge and must be recorded as `authentication.mode=none`, constrained to its exact endpoints/zone, and denied any expansion; it must not be made cosmetically “trusted”.
8. Docker Engine starts the runner with `--network none`, a read-only exact-SHA checkout, dropped capabilities, immutable image, numeric user, resource bounds, and temporary filesystems. Repository commands receive no holdout mount.
9. The external holdout command receives both the checkout and the immutable external holdout as read-only mounts. Holdout visibility is not secrecy; its security property is independent deployment, digest pinning, no checkout import/execution, and fail-closed evaluation.
10. The worker alone holds the CI attestation key and GitHub App key. The API alone holds the webhook secret, read token, and approval public trust store. Runner/future factory workspaces must have no edge to any of those materials.

The model should not assert that an example policy, example holdout, source Compose topology, or source test proves the currently deployed digest/topology. Deployed identities belong in external attestation/operations evidence, not editable architecture declarations.

## API and event compatibility fitness

### Current contract gap

Trust CI exposes a real HTTP API and consumes GitHub webhook events, but `engineering/contracts/**` contains only `.gitkeep` files and `examples/contracts/**` is demonstrative. FastAPI explicitly disables its generated OpenAPI endpoint. Therefore M2 cannot honestly mark public API/event compatibility `not_applicable` or treat source route decorators as a versioned contract.

The bounded solution is to freeze machine-readable contracts for the existing interfaces without changing their runtime behavior:

- an OpenAPI contract for health, GitHub webhook intake, signed approval submission, job read, attestation read, and metrics authentication/response classes;
- JSON Schemas for approval envelope, attestation envelope (including historical compatibility), and the accepted GitHub pull-request event projection, or equivalent schema references from OpenAPI;
- an explicit owner, version, compatibility mode, consumers/producers, and lifecycle for every entry in node `public_contracts`.

The full GitHub webhook payload is GitHub-owned. This repository should contract the verified input headers and the minimal projection it consumes, backed by replay fixtures; it should not pretend to own GitHub's entire schema. No internal asynchronous business event or queue exists today, so event compatibility may be `not_applicable` only with evidence showing no declared AsyncAPI/event artifacts and no changed producer/consumer paths.

### Compatibility inputs and decisions

Compatibility is an exact base/head contract comparison, never a grep-only claim:

- Input includes contract kind, stable contract ID, version, compatibility mode, exact base bytes/digest, exact head bytes/digest, and producer/consumer node IDs.
- Removed paths/methods/events, removed response/status alternatives, newly required request/event fields, renamed identifiers, narrowed types/enums/ranges, changed authentication semantics, and changed existing event meaning fail backward compatibility.
- Additive optional fields or new versioned operations may pass only when the declared compatibility mode permits them.
- Existing event versions are immutable in meaning. Breaking event changes require a new version and an explicit producer/consumer migration; a filename bump without semantic ownership does not suffice.
- Unsupported OpenAPI/JSON-Schema constructs must return `unsupported` and require architecture review. A small zero-dependency checker must not claim complete standards-level compatibility.
- A source-code API/event change without a declared contract change is drift and fails. A contract change without a mapped implementation/owner path is also drift.

Attestation evolution is especially sensitive. Existing signed schema-v1 payload mappings must continue to verify from their original bytes. If M2 adds signed `architecture_digest` or fitness summary fields, add them as one validated optional metadata group for new emissions, preserve the original stored payload map during replay, and test old public-key fixtures unchanged.

## Data and background integration fitness

- Migration fitness operates on versioned migration files at exact base/head, requires append-only ordering and explicit expand/contract phases, and rejects destructive/locking operations unless an independently enforced approval and recovery plan exist. M2 itself adds no migration or backfill.
- The transactional PostgreSQL state remains `trust_ci.*`; no architecture declaration may make it `factory.*` or a general task queue. Search/analytics stores do not exist and must not be invented.
- Background-job fitness is applicable to the existing Trust CI worker. Its model/rule evidence should cover idempotent enqueue identity, bounded attempts, lease/heartbeat/reclaim, correlation by job/repository/base/head, observable terminal failure, and dead state. “DLQ” may be represented by the existing durable `dead` terminal state only if the model points to the actual store/query/operator recovery behavior; do not invent a queue.
- Future job-like changed paths without a model declaration must fail/escalate, not become `not_applicable`.

## Architecture diff: frozen interface

### Inputs

A deterministic committed-tree diff accepts:

```text
schema_version
repository_id
exact_base_sha
exact_head_sha
base system/rules bytes (or explicit absent-at-adoption)
head system/rules bytes
base/head referenced-contract bytes and digests
exact changed-path list
declared pre-risk and exemption state
independent enforcement-policy digest when run by Trust CI
```

The trusted path requires both 40-hex commits to exist, workspace HEAD to equal `exact_head_sha`, bounded NUL-safe path discovery, no symlink following, and reads from Git objects or descriptor-safe checkout paths without executing repository code. A local dirty-tree mode may use `head_kind=worktree` plus tree fingerprint, but it must never label that result exact-SHA or Trust CI evidence.

For first adoption, an absent base model is explicit `baseline_introduced=true`; every head node/edge/contract/rule is reported as added and risk is escalated. K16 is never used to synthesize a fake base. Missing only one of system/rules, unsupported versions, or an unreadable base is `invalid`/`unsupported`, not an empty diff.

### Canonical outputs

The CLI/verification output should be bounded canonical JSON with stable sorting:

```json
{
  "schema_version": 1,
  "repository": "owner/name",
  "base_sha": "...",
  "head_sha": "...",
  "base": {"system_digest": "...", "rules_digest": "...", "architecture_digest": "..."},
  "head": {"system_digest": "...", "rules_digest": "...", "architecture_digest": "..."},
  "diff": {
    "nodes": [], "edges": [], "contracts": [], "rules": [],
    "digest": "...", "baseline_introduced": false
  },
  "drift": [],
  "fitness": [],
  "risk": {"pre": "red", "floor": "red", "post": "red", "triggers": [], "exemption_revoked": true},
  "required_approval_scopes": [],
  "enforcement_policy_digest": "..."
}
```

Each changed record contains stable ID, `added|removed|changed`, before/after canonical object digests, and sorted changed field names. Each fitness record contains stable rule ID, `pass|fail|not_applicable|unsupported`, severity, exact subject IDs/paths, bounded reason code, and evidence digest. Critical rules may not return `skip`.

Use three separately exposed digests: `system_digest`, `rules_digest`, and a domain-separated combined `architecture_digest`. The diff has its own digest over base/head identities and normalized change records. Trust CI additionally binds its independently deployed policy/holdout digest; repository `rules.yaml` never replaces that digest.

Post-risk is monotonic: `post = max(declared_pre, independent_risk_floor)`. New service, database, queue, framework, external integration, public contract, background job, network client, secret, trust-domain crossing, or capability edge raises the floor and cancels a docs exemption. The engine records required approval but never edits route/spec risk, issues approval, changes capabilities, or publishes a PR comment.

## Keeping critical enforcement independently measurable

Critical rule IDs should be stable and evaluated twice:

1. local M2 parser/fitness code produces advisory preflight evidence;
2. the external holdout independently parses bounded architecture/contract bytes and exact Git diff without importing `.grok-stack/adaptive_grok/architecture.py` or executing checkout modules.

The independently enforced minimum is strict architecture schema/version, no unresolved/undeclared security-sensitive edges, secret-flow denial, runner/factory denial of production trust material, new network/trust crossing escalation, implementation-plus-Trust-CI/holdout mixing, and inability to lower risk/exemption state. Results need per-rule status/count/digest rather than only a single `PASS` line. A trusted data-only runner extractor should bind the independently derived head architecture digest and bounded fitness summary into new signed attestations while retaining raw-payload replay compatibility.

No deployed policy mutation is authorized by M2 source work. The checked-in example may add `architecture_validate.py`, wire it through the already configured `/holdout/validate.py` entrypoint, and update the **example** bundle digest required by its regression test; this does not activate the live bundle. Actual activation necessarily requires a separate operator-controlled deployment of the reviewed external bundle and matching server-mounted holdout digest, which changes the policy epoch. Until that exact rollout and App-owned exact-SHA proof occur, documentation must say “source-ready independent validator”, not “externally enforced”.

There is also a current enforcement gap for semantic approvals: `JobRunner` derives approval scopes only from `Policy.required_scopes(changed_paths)` before it runs holdout. The holdout cannot currently demand and verify a new architecture scope based on a semantic edge/service/datastore diff. M2 must choose one honest boundary:

- source-ready only: independently fail any undeclared/prohibited addition, report semantic `required_approval_scopes` locally, and defer trusted semantic approval consumption to a separately designed server-policy/runner interface; or
- add a reviewed trusted semantic classification phase before approval lookup and map its stable result codes through server-owned policy. This is a Trust CI policy/API change and cannot be smuggled into an architecture parser task.

Path-only coverage of `architecture/**` with `governance` is useful defense in depth but does not satisfy “explicit approval for a new service/database/queue/framework/external integration,” because such additions can occur outside architecture paths. Conversely, an architecture file changed without corresponding implementation is not proof the implementation exists.

## Explicit M4+ non-goals

M2 publishes versioned architecture declarations, rules, digests, diagrams, diff records, and fitness evidence only.

- **M4:** no `factory/` service, `factory.*` schema/migration, task intake API, scheduler, state machine, leases/fences, WIP/concurrency/budget accounting, kill switches, reconciliation, audit store, task-packet persistence, or architecture-digest database column.
- **M5:** no Codex/Grok/future-provider adapter, JSON/JSONL provider protocol, background/systemd worker, workspace manager, Git broker, note broker, secret broker, network controller, provider credential, short-lived task credential, egress enablement, artifact store, or run-manifest writer.
- **M6:** no semantic validator/adjudicator, findings database, provider selection, repair cycle, same-writer repair enforcement, or `pass/repair/needs_human` state transition.
- **M7:** no branch creation, commit, push, PR creation/update/comment, supersession automation, or shadow-mode orchestration.
- **M8:** no trust profile, earned auto-merge, policy promotion, or autonomous merge.
- **M9:** no preview/staging/canary environment, deployment credential, production write, rollback automation, or promotion.
- Across all later milestones: no new service, database, queue, framework, external integration, root packaging marker, systemd unit, GitHub Action, or reuse of `trust_ci.*` as the factory queue.

Future M4/M5 consumers receive immutable IDs and digests from M2. They must not reinterpret graph semantics, parse K16/Markdown, invent replacement edge types, or allow architecture data to select executables, credentials, unit names, network destinations, or state transitions.

## Critical concerns for synthesis

1. **Baseline contamination:** route base `069fe822` predates M1 completion. Freeze an exact completed-M1 M2 base before implementing diff/evidence.
2. **Missing real API/event contracts:** Trust CI has externally consumed HTTP/webhook/approval/attestation interfaces but only example contracts. Compatibility cannot honestly pass until current interfaces are frozen in machine-readable artifacts or explicitly blocked as uncontracted drift.
3. **Semantic approval gap:** current Trust CI approval scopes are path-derived before holdout. A local `required_approval_scopes` field is advisory and cannot enforce architecture approval for semantically new services/edges.
4. **Deployment truth:** adding an example holdout validator changes only source. Activating it requires a separately authorized external bundle/digest rollout and fresh policy-epoch exact-SHA check.
5. **Self-bootstrap mixing:** M2 necessarily changes local enforcement and holdout example source while introducing the rule that application implementation and Trust CI/holdout changes cannot share a factory task. Define an exact M2 governance-bootstrap exception or split implementation and trusted-enforcement delivery; never create a reusable wildcard exception.
6. **Existing unauthenticated Docker control edge:** worker-to-Docker Engine TCP/2375 is privileged and currently unauthenticated. Model and constrain it honestly; do not erase the risk by assigning both nodes one broad trust domain.
7. **Rules are not deployed policy:** PR-controlled `architecture/rules.yaml` may describe/evaluate local rules but cannot disable, downgrade, or substitute for fixed critical rules in the external holdout/server policy.
8. **Bounded compatibility claims:** a dependency-free subset checker must fail `unsupported` on constructs it cannot prove; it must not claim full OpenAPI/JSON-Schema/AsyncAPI compatibility.
