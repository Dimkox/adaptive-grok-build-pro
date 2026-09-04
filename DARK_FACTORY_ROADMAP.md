# Adaptive Grok Build Pro — Dark Factory Roadmap

> **Execution handoff for Claw / Grok Build CLI.** This is the canonical consolidated roadmap derived from the current `main` tree, the Trust CI work, and the reviewed dark-factory videos. Implement it milestone by milestone. Do not treat a video claim, a prompt, a local receipt, or this document alone as merge authority.

## 1. Program goal

Build a controlled software factory that can turn a reviewed business intent into a pull request through durable task orchestration, isolated agent execution, independent validation, bounded repair, and measurable shadow-mode operation.

The target is not “maximum autonomy.” The target is **high-throughput delivery with bounded risk, reproducible evidence, and immediate human control**.

The program is complete only when the system can demonstrate this chain on an exact pull-request SHA:

```text
reviewed intent
→ typed specification
→ executable architecture constraints
→ durable factory task
→ isolated implementation workspace
→ one write owner
→ independent verification and semantic adjudication
→ bounded repair
→ pull request with signed evidence
→ App-owned Trust CI check
→ protected merge policy
→ measured shadow-mode quality
→ earned, revocable autonomy for low-risk classes only
```

## 2. Canonical baseline

Original planning baseline and current integration observation:

```text
repository: Dimkox/adaptive-grok-build-pro
branch: main
original baseline SHA: 73e4ae7c68a95d3a7440378964b8cc1879df9b89
publication snapshot main SHA: 1751b5855e46782b9a1bfceb6e1ab0102cba03b0 (2026-09-04T16:58:48Z; not a perpetual current-ref assertion)
product version: 2.0.14 (published release v2.0.14; v2.0.13 retained as immutable history)
Trust CI service version: 2.1.0
required check: adaptive-trust-ci/verified@06ecf1c875bc
```

Before implementing any milestone, compare the current `main` SHA with the recorded observation and update the milestone plan for intervening changes. Do not reset or discard newer work merely to match either historical identity.

## 3. What already exists

### 3.1 Local agent workflow

Implemented:

- deterministic task routing by intent, domain, complexity, and risk;
- domain-specific analysis, implementation, and review agents;
- one write owner per route;
- parallel read-only analysis and review waves;
- durable local change packages under `engineering/changes/`;
- fingerprint-bound local verification and review receipts;
- local quality profiles through `scripts/grok_verify.py`;
- explicit local delegated grants bound to repository, route, change, exact `HEAD`, tree fingerprint, named action/resource, source, and TTL;
- protected control-plane writer with optimistic SHA-256 locks and rollback;
- `low` reasoning by default, with `high` reserved for task framing, architecture, security, and release decisions;
- root `decisions.md` and `mistakes.md` as human-readable operational memory.

### 3.2 Trust CI source and harness

Implemented in-tree:

- no GitHub Actions;
- HMAC-verified pull-request webhook intake;
- PostgreSQL durable jobs, attempts, leases, approvals, events, and attestations;
- separate API, worker, migrator, and backup database roles;
- exact-SHA detached checkout;
- external holdout bundle outside the pull-request checkout;
- isolated no-network runner;
- tracked-source mutation detection;
- Ed25519 human approvals and CI attestations;
- GitHub App JWT and installation-token flow;
- GitHub Checks API publication;
- policy-epoch check naming;
- app-bound branch-protection configurator;
- bounded retry, lease reclaim, dead-letter behavior, backup, restore drill, and kill switch;
- immutable image policy, SBOM, vulnerability scanning, and signed supply-chain manifest;
- live PostgreSQL integration and restart drills recorded in repository evidence.

### 3.3 Current operational qualification

M0 Live Trust Authority is delivered. Protected `main` requires the App-owned policy-epoch check `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114`; repository source, prompts, local receipts and local grants cannot mint or replace it. The original roadmap observation predated that activation and is historical only.

M1-M9 are delivered to `main` as repository product source through PR #22. Checked head `b5eba759c309a92f92f4d4003d025795c7f8a1f9` passed App-owned `adaptive-trust-ci/verified@06ecf1c875bc` and merged as `8599d45f4f28285381b05a53feb3059de92eb2a8`, tree `03e122a30fb2dbb59907f4c4c28e17f93cbf0751`; release `v2.0.13` publishes ZIP SHA-256 `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`. Factual M8 cohort/activation, signed M9 input, operational environment/provider deployment, recovery proof, and human production authority remain separate operational gates.

Published `v2.0.14` adds the offline L5 multimodal landing dogfood vertical without changing M0-M9 milestone semantics. Its API/provider/render/evaluate/package path is bounded; provider and publisher defaults remain unavailable, `live_url` is unrepresentable except as null, the authoritative landing clone remains read-only, and repository publication supplied no operational provider, network, hosting, indexing, deployment, M8 activation, or production authority.

PRs #12 and #13 remain stale old-epoch `ACTION_REQUIRED` work whose unique lazy CLI imports/tests and repository-scoped Trust CI profiles are absent from `main`. PR #15's current-epoch `adaptive-trust-ci/verified@06ecf1c875bc` conclusion is `FAILURE` while GitGuardian is `SUCCESS`; its failure cause was not inspected or inferred. Wholesale merge of its obsolete M1-M3 aggregate is superseded, while investor-demo commit `9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b` and packaging hardening remain unique. All three need clean successor extraction; no successor PR is claimed.

## 4. Consolidated gap analysis

| Capability | State | Required action |
| --- | --- | --- |
| Task/domain routing | Implemented | Preserve and integrate with durable factory tasks |
| One write owner | Implemented locally | Enforce across distributed factory workers |
| Low-by-default reasoning | Implemented | Record effective effort in every run manifest |
| Local verification | Implemented | Keep as preflight, never merge authority |
| Exact-SHA external Trust CI | M0 delivered and live | Preserve exact-head/App ownership; every new M4+ SHA must earn a fresh check |
| GitHub App registration | Delivered external authority | Keep credentials and deployed policy outside the PR trust domain |
| Durable CI jobs | Implemented | Keep separate from implementation task state |
| Typed business specification | M1 delivered to main in v2.0.13 | Retain typed intent and evidence as change authority |
| Executable architecture model | M2 delivered to main in v2.0.13 | Retain independent fitness enforcement |
| Agent-loop backpressure | M6 repository source delivered in `v2.0.13` | Preserve finite repair ceilings and independent semantic authority |
| Semantic validator/adjudicator | M6 verdict and artifact-validation boundary delivered | Retain independent verdict authority during operational qualification |
| Controlled learning | M3 delivered to main in v2.0.13; registries intentionally empty | Activation still requires independent evidence and human governance |
| Debt/slop ledger | M3 delivered to main in v2.0.13 | Keep empty/unapproved records non-authoritative and preserve owner/trigger/evidence requirements |
| Durable factory task queue | M4 repository source delivered in `v2.0.13` | Require separate rollout authority before persistent operation |
| Background implementation environment | M5 repository source delivered; live adapters disabled | Require separate rootless live-host evidence before operational acceptance |
| Immutable implementation run manifest | M5 repository source delivered | Accept operational use only after isolation/capability/orphan and live-host evidence |
| WIP, cost, and PR flood controls | M4 enforces durable WIP/cost; PR flood remains M7 work | Preserve M4 ceilings and add PR lifecycle bounds only at M7 |
| Automated PR lifecycle | M7 shadow source delivered; no external PR capability | Add runtime and real outcomes before activation; human merge remains mandatory |
| Shadow-mode metrics | Synthetic algorithm evidence only | Measure real quality and human disagreement before autonomy |
| Earned auto-merge | Corrected M8 evaluation delivered; deliberately inactive and capped at L2 | Require an exact-profile 30-real-task cohort plus explicit activation |
| Preview/staging/canary delivery | M9 sealed source delivered; no operational adapter | Require real signed input, environment/provider deployment and recovery evidence; production remains human-owned |
| L5 multimodal landing dogfood | Local `2.0.14` source candidate; bounded offline fixture path only | Complete exact-source gates and deterministic package binding; operational provider, data transfer, target write, signing, hosting and production require separate authority |

## 5. Non-negotiable constraints

Every milestone inherits these constraints.

1. **No GitHub Actions.** Do not add `.github/workflows/**`, Dependabot workflows, or another CI SaaS as a substitute.
2. **PR-only product delivery.** Direct push to `main` or another protected/shared branch is prohibited.
3. **Trust domains remain separate.** Factory execution cannot publish the authoritative Trust CI verdict.
4. **Exact-SHA evidence.** Approvals, verification, attestations, architecture checks, and semantic verdicts bind to exact base/head SHAs and policy digests.
5. **One write owner.** Multiple agents may read and review; only one implementer owns a task workspace at a time.
6. **Fresh bounded contexts.** Each task and repair cycle starts from durable state and an immutable task packet, not an endlessly accumulated chat.
7. **Low reasoning by default.** Use `high` for task analysis, architecture, security, release, and semantic adjudication; record the effective value.
8. **No secret inheritance.** Agent workspaces receive only short-lived, task-scoped credentials through an explicit broker.
9. **No network by default.** Any implementation-workspace egress requires an allowlist and is recorded in the run manifest.
10. **No self-approval.** Implementers cannot create semantic verdicts, Trust CI checks, human approval signatures, or active governance rules.
11. **No unbounded loops.** Every retry, repair cycle, runtime, token budget, cost, queue, and PR count has a hard ceiling.
12. **No Markdown-only authority.** Markdown remains useful explanation; machine-readable specifications and policies drive gates.
13. **No auto-merge before evidence.** Shadow mode and human merge are mandatory before earned autonomy.
14. **No production auto-deploy in the initial factory.** Human production promotion remains mandatory until a later delivery milestone.
15. **No root packaging marker.** Do not add root `pyproject.toml`, `requirements.txt`, or `setup.py`; new services use scoped subdirectories.

## 6. Target architecture

The target has four separate planes.

```text
Intent plane
  typed change specification
  business objectives and invariants
  architecture model and policy

Factory control plane
  durable tasks and leases
  scheduler, WIP, budgets, reconciliation
  PR lifecycle and run manifests

Factory execution plane
  isolated ephemeral workspaces
  one write owner and read-only specialists
  task-scoped secrets and network policy

Trust and delivery plane
  external holdout and deterministic checks
  semantic validation and adjudication
  App-owned Trust CI check
  protected merge and later preview/canary delivery
```

### 6.1 Trust boundary rule

The `factory/` service may create code, branches, commits, and pull requests. It must not hold the CI attestation key or the GitHub App credentials used to publish the authoritative Trust CI check.

The `trust-ci/` service may verify an exact SHA and publish the authoritative check. It must not implement the requested product change.

### 6.2 State ownership

Use separate PostgreSQL schemas or databases:

```text
trust_ci.*     exact-SHA verification, approvals, attestations
factory.*      intent, tasks, runs, workspaces, findings, costs, PRs
```

Do not turn `trust_ci_jobs` into a general factory queue.

## 7. Milestone dependency graph

```text
M0 Live Trust Authority
 ├──→ M1 Typed Intent and Evidence
 ├──→ M2 Executable Architecture
 └──→ M3 Controlled Knowledge and Debt

M1 + M2 + M3
 └──→ M4 Durable Factory Control Plane
       └──→ M5 Isolated Execution Plane
             └──→ M6 Semantic Validation and Repair
                   └──→ M7 Automated PR Lifecycle and Shadow Mode
                         └──→ M8 Earned Low-Risk Autonomy
                               └──→ M9 Preview, Canary, and Recovery Delivery
```

Milestones M1, M2, and M3 may be developed in parallel only after M0 has a live proof or an explicitly documented bootstrap exception approved by the user. M4 must consume their stable interfaces rather than inventing replacements.

The dependency-ordered M4 `67dc4ddf` → M5 `85cd4343` → M6 `c6d48ffd` → M7 `00e0e4f9` → corrected M8 `a937ac8d` → M9 `64b10689` source is delivered to `main` by PR #22 and published as `v2.0.13`. M8 remains inactive pending a factual exact-profile cohort of at least 30 human-accepted tasks. M9 remains non-operational pending signed input, an operational environment/provider deployment, exercised recovery, and human production authority.

## 7.1 Exact milestone handoff contracts

| Edge | Producer → consumer binding | Gate and invalidation | Rollback / forbidden authority |
| --- | --- | --- | --- |
| M4 → M5 | M4 emits an immutable task packet bound to `task_id`, accepted base/head SHA, complete frozen-intent/spec/architecture/governance/policy digests, route and budget; M5 accepts only the exact packet digest and M4 product SHA. | Accepted M4 exact-SHA verification/reviews/Trust CI plus a suitable rootless-isolation host; any predecessor SHA, packet field, policy or authority change invalidates dispatch and requires restack/reissue. | Cancel/expire the M4 lease, preserve packet/audit and destroy only the isolated workspace; M5 receives no intake-policy, Trust CI, merge, production or cross-task authority. |
| M5 → M6 | M5 emits an immutable execution-result/run-manifest digest bound to task packet digest, exact base/head SHA, workspace/image/tool/network/secret-scope evidence and artifacts; M6 verifies all bindings before judging. | Accepted M5 isolation/capability/orphan evidence and predecessor exact SHA; changed code, manifest, artifact, image or policy invalidates the verdict and starts a fresh bounded validation cycle. | Quarantine result/artifacts and return a structured finding to bounded repair; M6 cannot write implementation, mint Trust CI/human approval or mutate execution evidence. |
| M6 → M7 | M6 emits a signed/immutable semantic-verdict digest bound to execution result, requirement/criterion IDs, exact head SHA, findings, repair count and residual risk; M7 consumes only a PASS verdict with matching local/external checks. | Independent adjudication, repair ceiling and exact-SHA verifier/Trust CI; any source, criterion, policy, holdout or verdict change invalidates the ready-for-PR state. | Revert to needs-human/repair or supersede the bundle while preserving evidence; M7 cannot push/open/update a PR without exact delegated authority and cannot merge or publish Trust CI. |
| M7 → M8 | M7 emits an immutable shadow ready-for-PR bundle digest binding task/run/verdict/check/PR-head/human-decision and outcome metrics; M8 cohorts only exact trust-profile tuples. | At least 30 human-accepted tasks for the exact class/profile tuple, complete disagreement/rollback/security metrics and human merge for every PR; any tuple component or evidence mutation starts a new cohort. | Demote/discard the affected cohort and keep human merge; under current authority M8 is capped at L2, cannot auto-merge, rewrite historical decisions or activate governance. |
| M8 → M9 | M8 emits a durable trust-profile digest and L2-or-lower decision bound to repository/class/models/prompts/policy/runner/holdout digests; M9 binds preview/staging/canary inputs to the exact merged SHA and signed artifact digest. | Accepted predecessor profiles, exact signed supply-chain artifact, reproducible preview/staging, explicit canary thresholds and exercised recovery; incident, rollback, policy/artifact/SHA change invalidates promotion and triggers demotion. | Halt/rollback the canary, preserve deployment evidence and demote the profile; production promotion remains human-owned and no agent gains production, signing-key, branch-protection or Trust CI authority. |

M7-M9 repository source is delivered on exact predecessor bindings. That delivery does not establish a factual M8 cohort or activation, real M9 preview/canary evidence, operational deployment, or production authority.

---

# M0 — Activate and prove the external Trust Authority

## Objective

Turn the existing Trust CI source into the actual merge authority for `main`.

## Primary surfaces

```text
trust-ci/
engineering/runbooks/trust-ci-rollout.md
repository GitHub App installation
repository webhook configuration
main branch protection
CI host runtime configuration
```

## Work items

- [ ] Verify that `adaptive-trust-ci` is installed on `Dimkox/adaptive-grok-build-pro`.
- [ ] Record the App ID and installation ID in operator-only configuration; never commit them with private material.
- [ ] Generate or rotate the GitHub App RSA private key and mount it only into the worker.
- [ ] Provision an API-only webhook secret; the worker must not receive it.
- [ ] Build API, worker, runner, and holdout artifacts from reviewed sources.
- [ ] Pin every deployed image and holdout by immutable digest.
- [ ] Generate SBOMs, vulnerability reports, signatures, and the signed supply-chain manifest.
- [ ] Deploy PostgreSQL, migration job, API, worker, runner loader, holdout, metrics, backup timer, and HTTPS reverse proxy on an isolated CI host.
- [ ] Register pull-request webhook delivery to `/webhooks/github`.
- [ ] Open a disposable documentation PR and observe a Check Run named `adaptive-trust-ci/verified@<policy-sha12>` on its exact head SHA.
- [ ] Verify that the check is owned by `adaptive-trust-ci`, not another actor with the same text.
- [ ] Download and verify the signed attestation using the published CI public key.
- [ ] Exercise a protected-path diff that enters `needs_approval`, submit a valid human-signed approval, and confirm exact-SHA requeue.
- [ ] Verify rejection of an expired approval, wrong signer scope, changed SHA, changed policy digest, and replayed nonce.
- [ ] Activate the kill switch and prove that new jobs and approvals stop while guardrails remain active.
- [x] Apply branch protection only after the live check has succeeded.
- [x] Verify that branch protection binds the exact policy-epoch check and the GitHub App ID.
- [x] Verify that direct push, force push, branch deletion, and merge without the required check fail. (Documented 2026-08-24: `enforce_admins` true, `allow_force_pushes` false, `allow_deletions` false, PR #5 `mergeable_state=blocked`; no live push to `main` was issued.)
- [x] Remove or supersede the bootstrap-exception language once live authority is established.

## Exit criteria

```text
main protected = true
required check = current adaptive-trust-ci/verified@<policy-sha12>
required check app_id = adaptive-trust-ci App ID
exact-SHA disposable PR = success
signed attestation = independently verified
protected-path approval flow = proven
backup + restore + restart drill = pass
kill switch = pass
no GitHub Actions = true
```

## Evidence required in Git

- operator-safe activation report without secrets;
- App ID, installation confirmation, check run ID, policy digest, image digests, and holdout digest;
- attestation verification output;
- branch-protection response with secret fields removed;
- rollback instructions and key-rotation notes.

---

# M1 — Typed Intent, Acceptance Criteria, and Evidence Traceability

## Objective

Replace Markdown-only requirements as gate inputs with a typed change specification that maps business outcomes to requirements, invariants, tests, production signals, and approvals.

## Recommended file structure

```text
schemas/change-spec.schema.json
.grok-stack/templates/change/change-spec.yaml
.grok-stack/adaptive_grok/spec.py
scripts/grok_spec.py
tests/test_change_spec.py
trust-ci/holdout.example/change_spec_validate.py
```

## Minimum specification model

```yaml
schema_version: 1
change_id: CHG-...
objective:
  id: OBJ-...
  statement: measurable business outcome
  success_metric: metric_name
  target: explicit target
risk:
  tier: green | yellow | red
  domains: []
acceptance_criteria:
  - id: AC-001
    statement: observable required behavior
    evidence:
      - test: tests/path::test_name
invariants:
  - id: INV-001
    statement: property that must always hold
forbidden_outcomes:
  - id: FORBID-001
    statement: behavior that must never occur
contracts:
  openapi: []
  json_schema: []
  events: []
observability:
  - metric: metric_name
    proves: [OBJ-...]
rollback:
  strategy: feature_flag | forward_fix | restore | migration_reversal
  maximum_steps: explicit integer
approvals:
  required_scopes: []
```

## Work items

- [x] Define a strict JSON Schema with no ambiguous free-form alternatives for identifiers, risk tiers, evidence references, and approval scopes.
- [x] Add `change-spec.yaml` to every durable change package.
- [x] Generate an initial spec from the active route without inventing unavailable facts.
- [x] Add CLI commands to validate, summarize, and map evidence to criterion IDs.
- [x] Require stable IDs for objectives, acceptance criteria, invariants, forbidden outcomes, and production signals.
- [x] Link Markdown `brief.md`, `requirements.md`, and `architecture.md` to the typed spec instead of duplicating authority.
- [x] Extend local verification receipts with criterion IDs.
- [x] Extend Trust CI attestation source with the typed spec digest and criterion coverage summary; deployed emission remains a separate rollout.
- [x] Add independent external holdout source checks for missing or malformed specs; deployed bundle activation remains a separate rollout.
- [x] Define exemptions only for explicitly bounded documentation-only micro changes.
- [x] Fail standard/high-risk work when a required criterion has no evidence mapping.
- [x] Detect stale specs after a change to base/head SHA, contracts, or policy.

The checked work items mean their source and local regression coverage exist. At the M1 checkpoint, exact source HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a` passed full local verification and all four route-selected wave-7 reviews, followed only by evidence/docs/state closure. A later authorized isolated PostgreSQL run passed 10/10 database tests and the full Trust CI suite 200/200 with no skips, validating six Trust CI tables, migrations through version 3, and four bounded `NOLOGIN` roles; that remains historical local evidence, while the complete M1 source was subsequently delivered through PR #22. Deployed worker/reader/emitter/holdout/policy qualification remains separately governed.

## Exit criteria

- every standard/high-risk change has a schema-valid typed spec;
- every acceptance criterion maps to at least one independent evidence source;
- every red-risk change lists explicit forbidden outcomes and approval scopes;
- Trust CI attestation contains spec digest and criterion coverage;
- Markdown text cannot silently override typed fields;
- malformed, stale, or incomplete specs fail closed.

---

# M2 — Living Executable Architecture and Fitness Functions

## Objective

Replace the complete K16 graph as architectural authority with a machine-readable model of components, dependencies, data flows, trust domains, secrets, and deployment relationships.

The K16 graph may remain as a decorative inventory test. It must not be treated as evidence that the architecture is valid.

## Recommended file structure

```text
architecture/system.yaml
architecture/rules.yaml
architecture/adoption.json
architecture/generated/*.mmd
schemas/architecture-system.schema.json
schemas/architecture-rules.schema.json
.grok-stack/adaptive_grok/architecture.py
.grok-stack/adaptive_grok/architecture_diff.py
.grok-stack/adaptive_grok/architecture_fitness.py
.grok-stack/adaptive_grok/architecture_diagrams.py
scripts/grok_architecture.py
tests/test_architecture_model.py
tests/test_architecture_fitness.py
trust-ci/holdout.example/architecture_validate.py
```

## Architecture model requirements

Each node records:

```text
id
type
owner
trust_domain
data_classification
secrets
runtime
repository_paths
public_contracts
```

Each edge records:

```text
from
to
type
protocol
direction
authentication
network_policy
sync_or_async
allowed_data
failure_behavior
```

## Mandatory fitness functions

At the M2-A checkpoint, the checked items below meant bounded repository source and local regression coverage existed without claiming independent M2-B enforcement, deployment, merge eligibility, or a live external check. The source was subsequently delivered through PR #22; independent deployed enforcement remains a separate concern.

- [x] forbidden dependency edges;
- [x] module/package boundary enforcement;
- [x] public API compatibility;
- [x] event/schema backward compatibility;
- [x] migration expand/contract rules;
- [x] tenant-filter and authorization invariants;
- [x] no new uncontrolled network clients;
- [x] no production imports from test/governance packages;
- [x] no implementation change combined with Trust CI/holdout mutation in one factory task;
- [x] maximum file/module size and complexity budgets for changed code;
- [x] background jobs require idempotency, correlation IDs, observable failure, bounded retries, and dead-letter behavior;
- [x] secrets may flow only across declared trusted edges;
- [x] runner and factory workspaces may not access production trust material.

## Work items

- [x] Create the schemas and initial architecture model for the existing local stack and Trust CI source boundaries.
- [x] Generate C4 context, container, deployment, data-flow, and trust-boundary diagrams from the model.
- [x] Validate repository paths and declared contracts against the actual tree.
- [x] Add architecture-diff output to the deterministic CLI and local PR preflight evidence.
- [x] Add post-diff risk escalation when changed files introduce a new edge, secret, network client, datastore, or trust-domain crossing.
- [ ] Place critical fitness checks in external holdout or server policy, not only in pull-request-controlled tests.
- [x] Emit the explicit local `architecture` approval scope for new services, databases, queues, frameworks, or external integrations; independently trusted approval enforcement remains M2-B.

## Exit criteria

- architecture model validates against its schema;
- generated diagrams are reproducible from the model;
- prohibited dependency and trust-boundary changes fail independent validation;
- post-diff risk cannot be lower than pre-diff risk;
- architecture drift is visible in PR evidence;
- critical fitness rules are outside implementer control.

M2-A's delivered source proves schema validation, read-only reproducible text projections, a package-aware bounded abstract interpreter for queue provenance, monotonic risk, drift/diff evidence, read-only planning for existing installer targets, and atomic materialization of absent targets. The installer emits dependency advice but never executes it, rejects `--force`, and excludes target-owned architecture authority. PR #22 supplied the release-head gate for repository delivery; prohibited-edge independence and critical rules outside implementer control remain M2-B/deployed exit work.

---

# M3 — Controlled Learning, Canonical Patterns, and Debt Ledger

## Objective

Prevent agent mistakes or unreviewed observations from becoming permanent standing instructions while preserving useful organizational learning.

## Recommended file structure

```text
governance/rules/
governance/debt/
governance/canonical-examples/
schemas/governance-rule.schema.json
schemas/debt-entry.schema.json
.grok-stack/adaptive_grok/governance.py
scripts/grok_governance.py
tests/test_governance.py
```

## Rule lifecycle

```text
candidate
→ reviewed
→ approved
→ active
→ deprecated
→ revoked
```

Every rule records:

```text
rule_id
source_task
author
scope
evidence
confidence
created_at
expires_at
approved_by
policy_version
status
```

## Debt lifecycle

Every deliberate shortcut records:

```text
debt_id
introduced_by
reason
owner
interest
repayment_trigger
deadline
behavior-preserving tests
status
```

## Work items

- [ ] Convert agent-written lessons into `candidate` records rather than immediate standing policy.
- [x] Require independent review and explicit human approval before promotion to `active`.
- [x] Generate human-readable `decisions.md` and `mistakes.md` views from approved/candidate records, or clearly mark Markdown as a non-authoritative projection.
- [x] Add expiration and revalidation for context-sensitive rules.
- [x] Add revocation and provenance audit.
- [ ] Create canonical examples for HTTP adapters, repositories, background jobs, webhook handlers, migrations, authorization checks, and error handling.
- [ ] Require agents to prefer canonical examples or explicitly justify deviation.
- [x] Add duplicate-pattern and conflicting-pattern detection.
- [x] Introduce a debt ledger that distinguishes intentional debt from accidental slop.
- [x] Prevent a factory task from activating its own governance rule.

Checked M3 items denote behavior accepted at exact merge `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`; that source is an ancestor of the checked PR #22 head and is delivered in v2.0.13, but this does not denote deployment or active governance. The seven small example source files exist, while the canonical-example registry remains empty until an independent exact-record authority and real human governance approval are available; therefore the two canonical-example work items remain open. M4 consumed the exact aggregate; operational rollout remains separately gated.

## Exit criteria

- agent output cannot directly create active policy;
- every active rule has evidence and an approver;
- expired or revoked rules stop influencing routes;
- deliberate debt has owner, repayment trigger, and tests;
- canonical examples are versioned and independently reviewed;
- accidental pattern proliferation is detected.

---

# M4 — Durable Factory Task Control Plane

## Objective

Create a separate durable control plane that accepts work, classifies it, schedules it, limits it, and recovers it without relying on an interactive laptop session.

## Recommended service boundary

```text
factory/
  pyproject.toml
  src/adaptive_factory/
  sql/
  config/
  tests/
  compose.yaml
  README.md
```

Do not add a root packaging marker.

Current status: M4 is preserved at exact integrated ancestor `67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4` with migrations `001`-`013` and the complete durable control surface, delivered to `main` within PR #22. Persistent runtime rollout remains separately gated.

## Factory task state machine

```text
inbox
→ triaged
→ waiting_design_approval
→ queued
→ leased
→ analyzing
→ implementing
→ verifying
→ reviewing
→ ready_for_human
```

Exceptional states:

```text
retry
needs_human
dead
cancelled
superseded
```

`ready_for_human` is M4's positive terminal state. GitHub/PR states such as `pr_open` and `merged` are deliberately absent: they belong to later delivery milestones, and Trust CI remains a separate authority domain.

## Minimum durable fields

```text
intent_id
intent_digest
idempotency_key
task_id
repository_id
source_type
source_id
source_digest
route_id
change_id
spec_digest
architecture_digest
governance_digest
exact_base_sha
policy_digest
acceptance_ids
task_limits
state
generation
packet_digest
run_id
attempt_no
role
fence
lease_owner
lease_expires_at
deadline_at
budget_reservations
usage_observations
event_sequence
audit_digest
created_at
updated_at
```

The immutable accepted-intent body also freezes both producer handoffs, including their exact head SHA. M4 does not own or persist a Git branch, pull request, merge state, or Trust CI result.

## Work items

- [x] Implement authenticated manual API/CLI intake.
- [ ] Add a GitHub Issue connector in a later GitHub-capable milestone; M4 only accepts an already projected, authenticated source record.
- [x] Derive an idempotency key that prevents duplicate active tasks for the same source and frozen authority.
- [x] Use PostgreSQL `FOR UPDATE SKIP LOCKED` leases.
- [x] Add heartbeat, lease expiry, reclaim, bounded attempts, dead-letter, and reconciliation.
- [x] Cancel or supersede stale tasks when source content or frozen authority changes.
- [x] Add global and per-repository kill switches.
- [x] Add global/per-repository reader limits and a single-writer limit.
- [x] Add hard limits for runtime, tokens, cost, output, events, and repair cycles.
- [ ] Add open-factory-PR and PR-age limits only after a later milestone owns GitHub PR delivery.
- [x] Separate read-only analysis concurrency from single-writer concurrency.
- [x] Persist every state transition and actor in an append-only audit log.
- [x] Refuse dispatch when M0 Trust CI authority is unavailable unless the user records a named bootstrap exception.

Checked M4 items denote locally implemented behavior only. They do not claim final review, external Trust CI acceptance, PR delivery, merge, deployment, or production activation.

## Exit criteria

- duplicate intake creates one active task;
- two workers cannot own one live lease;
- a killed worker is recovered after lease expiry;
- attempts exhaust into `dead`;
- stale tasks become `superseded`;
- WIP and budget limits stop new dispatch;
- kill switch stops new work without deleting evidence;
- implementation task state is separate from Trust CI state.

---

# M5 — Isolated Background Execution Plane

Current status: M5 bounded-execution source is delivered in `v2.0.13` from checkpoint `85cd4343143915ce9342634e7fe81886b6394871` with additive migrations `014`-`017`; operational adapters remain ineligible and live-host proof is still required.

## Objective

Run implementation agents in ephemeral workspaces that survive laptop disconnection, cannot affect other tasks, and expose only task-scoped capabilities.

## Initial deployment recommendation

Use a dedicated factory worker host or VM with rootless Podman or an equivalent restricted runtime. Keep an interface that can later support Firecracker/Kata/gVisor without changing task semantics.

Do not colocate privileged execution workers with production workloads or the Trust CI signing authority.

## Required components

```text
workspace manager
immutable task packet builder
agent launcher
secret broker
network policy controller
artifact store
run-manifest writer
orphan reconciler
```

## Immutable task packet

Each agent receives:

```text
task_id
exact base SHA
typed change spec digest
architecture model digest
selected role
reasoning effort
allowed tools
allowed paths
allowed network destinations
short-lived secret scopes
acceptance criterion IDs
maximum runtime/tokens/cost
output contract
```

## Work items

- [ ] Create a dedicated branch and isolated workspace per task.
- [ ] Enforce one write owner using a durable lease, not only prompt instructions.
- [ ] Run analysis and review roles read-only.
- [ ] Start each task and repair cycle in a fresh context reconstructed from durable state.
- [ ] Prevent task A from reading or writing task B state, artifacts, or workspace.
- [ ] Prevent access to Trust CI keys, human approval keys, production credentials, and other control-plane secrets.
- [ ] Issue short-lived task credentials only when required.
- [ ] Apply no-network default and explicit egress allowlists.
- [ ] Record effective model, reasoning effort, prompt/agent definition digest, tools, image digest, network policy, secret scopes, tokens, cost, and timing.
- [ ] Destroy completed workspaces after artifact retention rules are satisfied.
- [ ] Reconcile orphaned runtimes and branches after worker failure.
- [ ] Store implementation artifacts and logs with bounded size and explicit retention.

## Exit criteria

- a task continues safely after the user disconnects;
- one task cannot access another task;
- only one writer holds the workspace write lease;
- secrets are scoped, short-lived, and absent from logs/manifests;
- network access matches the recorded allowlist;
- fresh-context reconstruction produces the same task packet;
- orphaned workspaces are reclaimed;
- every run has an immutable manifest.

---

# M6 — Independent Semantic Validation, Meta-Review, and Bounded Repair

Current status: M6 semantic-validation source is delivered in `v2.0.13` from checkpoint `c6d48ffd8594b3baab1a575021452ea5dfa2a98b` with additive migration `018`, independent verdict authority, artifact validation, and bounded repair.

## Objective

Add backpressure inside the agent loop so incorrect implementations stop early, produce structured findings, and undergo a finite repair process.

## Required roles

```text
implementer
code reviewer
test reviewer
security reviewer
architecture reviewer
semantic validator
meta-reviewer / adjudicator
```

The semantic validator and adjudicator are read-only. They do not receive implementer chain-of-thought or self-evaluation. They receive the typed spec, architecture constraints, final diff, deterministic evidence, and external holdout results.

Use a separate model/provider for semantic validation when available. At minimum, use separate definitions, contexts, prompts, and holdout evidence.

## Structured finding schema

```text
finding_id
requirement_id
severity
category
evidence
reproduction
repairable
source_validator
model_digest
created_at
```

## Decision model

```text
pass
repair
needs_human
```

## Work items

- [ ] Add a typed finding schema and durable finding store.
- [ ] Map every finding to an acceptance criterion, invariant, forbidden outcome, architecture rule, or explicit non-functional requirement.
- [ ] Run independent reviewers in parallel on the same immutable head SHA.
- [ ] Add a meta-reviewer that detects contradictions, duplicates, unsupported passes, and correlated findings.
- [ ] Add semantic coverage reporting: which criteria were proven, unproven, contradicted, or out of scope.
- [ ] Implement bounded repair with `maximum_repair_cycles = 3`.
- [ ] Send all repairs back to the same write owner.
- [ ] Escalate to `needs_human` when the same finding recurs, risk increases, diff size exceeds policy, architecture changes, or a fourth cycle would be required.
- [ ] Re-run affected deterministic checks, holdout, semantic validation, and reviews after every code change.
- [ ] Prevent the implementer from creating or editing validator evidence, holdout rules, or adjudication policy.
- [ ] Record costs and durations per cycle.

## Exit criteria

- validator assesses requirement satisfaction, not merely test success;
- contradictory reviewer outputs are surfaced;
- a repeated unresolved finding escalates;
- a fourth repair cycle is impossible;
- post-repair evidence binds to the new exact SHA;
- implementer cannot approve its own work;
- structured verdict and residual risk appear in PR evidence.

---

# M7 — Automated Pull-Request Lifecycle and Shadow Mode

Current status: M7 shadow-handoff source is delivered in `v2.0.13` from checkpoint `00e0e4f9a6f50844bf9e0ffc7139d3283dda889f`; evidence is synthetic, no external PR capability exists, and human merge remains mandatory.

## Objective

Turn successful factory tasks into controlled pull requests while limiting review load and collecting evidence about actual quality.

## Automated PR flow

```text
create branch
→ commit exact task result
→ push branch using delegated operational authority
→ open PR
→ link source issue and task
→ publish factory summary
→ wait for semantic verdict
→ wait for App-owned Trust CI
→ human decision during shadow mode
```

## Factory PR summary

Every PR records:

```text
task_id and run_id
source issue
base/head SHA
spec and architecture digests
pre/post risk
changed files and diff size
reasoning efforts and models
verification and holdout result
semantic verdict and findings
repair cycles
approved scopes
runtime, tokens, and cost
residual risk
recommended human action
```

## WIP and flood controls

- [ ] maximum active implementation tasks per repository;
- [ ] maximum open factory PRs per repository;
- [ ] maximum open PRs per risk tier;
- [ ] maximum task age and PR age;
- [ ] maximum daily cost and token consumption;
- [ ] duplicate and overlap detection;
- [ ] automatic supersession when a newer task replaces an older result;
- [ ] queue pause when human review capacity is exceeded;
- [ ] escalation for stale PRs rather than silent accumulation.

## Shadow-mode requirements

Run at least 30 accepted tasks for each candidate low-risk class before considering autonomy. Human merge remains mandatory.

Persist:

```text
first-pass acceptance rate
human review minutes
repair cycles
cost per accepted change
cycle time
rollback rate
escaped defects
validator false positives
validator false negatives
human/validator disagreements
duplicate dispatch rate
lease reclaim rate
security escalation rate
```

## Exit criteria

- successful tasks open reproducible PRs automatically;
- direct push to `main` remains impossible;
- WIP limits prevent uncontrolled PR growth;
- stale and superseded work is reconciled;
- human decisions are captured as training/evaluation evidence, not silently written into policy;
- at least one complete shadow-mode report exists per candidate task class;
- auto-merge remains disabled.

---

# M8 — Earned and Revocable Low-Risk Autonomy

Current status: M8 earned-autonomy evaluation is delivered in `v2.0.13` from corrected checkpoint `a937ac8d200a4e143c295fabd482b19bc8cc4286` over actual M7 records. Durable currentness, a factual 30-task cohort and activation remain absent; authority is capped at L2 and deterministic L0 demotion remains mandatory.

## Objective

Permit automated merge only for narrowly defined task classes that have demonstrated acceptable quality under shadow mode.

## Trust profile key

Trust is specific to this tuple:

```text
repository
change_class
agent_profile
validator_profile
model versions
prompt/definition digests
policy digest
runner image digest
holdout digest
```

Changing any material component starts a new evidence cohort.

## Suggested trust levels

```text
L0  agent may propose; all work manually reviewed
L1  agent implements; human reviews every PR
L2  automated reviewers recommend; human merges every PR
L3  approved green classes may auto-merge with sampled human audit
L4  approved green classes may auto-merge with post-merge monitoring and automatic revocation
```

## Minimum promotion conditions

- sample size meets the configured minimum for the exact trust-profile tuple;
- first-pass acceptance meets policy threshold;
- no critical security miss;
- no unauthorized protected-path or secret access;
- duplicate dispatch rate is zero;
- rollback and escaped-defect rates remain below policy thresholds;
- validator false-negative rate is below policy threshold;
- human review time is materially reduced;
- production observability exists for the affected behavior.

## Immediate demotion triggers

```text
production incident
security miss
incorrect auto-merge
rollback
policy bypass
unexplained metric regression
invalid attestation
```

Any trigger demotes the affected profile to `L0` or `L1` immediately. Promotion is gradual; demotion is immediate.

## Eligible initial classes

Potentially eligible after evidence:

- documentation-only;
- generated files with external validation;
- tests-only changes that do not weaken tests;
- formatting and lint corrections;
- bounded allowlisted refactors with unchanged contracts;
- patch dependency updates under strict policy and holdout coverage.

Never initially eligible:

- authentication or authorization;
- PII or tenant isolation;
- payments or financial calculations;
- database migrations and destructive data work;
- secrets;
- external integrations with side effects;
- production deployment;
- Trust CI, factory governance, holdout, or branch protection;
- destructive operations.

## Exit criteria

- trust profiles are durable and auditable;
- promotion uses empirical data rather than a manual toggle;
- policy changes invalidate old profiles;
- only approved green classes can auto-merge;
- demotion works immediately;
- sampled human audit continues.

---

# M9 — Preview, Staging, Canary, and Recovery-Aware Delivery

Current status: M9 repository source is delivered in `v2.0.13` from code checkpoint `64b10689ce78a0464a494440f3fa981e18789687` over exact M8, with immutable records, deterministic one-step preview/staging/bounded-canary decisions, a sealed in-memory environment and least-authority recovery. Real signed input, an operational environment/provider deployment, exercised recovery and production authority remain absent; production promotion remains human-owned.

## Objective

Extend proven low-risk automation into delivery environments without granting agents unrestricted production authority.

## Delivery flow

```text
protected merge
→ ephemeral preview
→ integration and smoke tests
→ staging
→ signed promotion request
→ canary
→ health and business metric evaluation
→ human production promotion
→ automated rollback or halt on policy breach
```

## Work items

- [ ] Create isolated preview environments per approved PR class.
- [ ] Bind preview artifacts to exact merged SHA and signed supply-chain manifest.
- [ ] Add deterministic smoke, contract, migration, and rollback checks.
- [ ] Define canary cohorts and measurable abort thresholds.
- [ ] Require observable business metrics linked to typed objectives.
- [ ] Add automatic halt and rollback when health, error, latency, security, or business thresholds breach.
- [ ] Preserve human production promotion for red/yellow classes.
- [ ] Record deployment, canary, rollback, and production outcomes in the trust profile.
- [ ] Feed incidents into immediate autonomy demotion and controlled-learning candidates.

## Exit criteria

- preview and staging are reproducible from exact SHA;
- production artifacts are signed and verified;
- canary has explicit success and abort criteria;
- rollback is exercised, not merely documented;
- no agent can bypass human promotion for non-approved classes;
- production outcomes update the empirical trust profile.

---

## 8. Cross-cutting engineering requirements

### 8.1 Testing

Every milestone uses test-driven development and includes:

- unit tests;
- real PostgreSQL concurrency/integration tests where state is durable;
- process-kill and restart drills;
- exact-SHA and stale-state tests;
- adversarial permission, secret, network, and replay tests;
- contract and schema compatibility tests;
- mutation tests for critical policy gates;
- end-to-end disposable-repository tests for GitHub interactions.

A mocked test does not replace a live integration test for leases, GitHub App ownership, branch protection, or container isolation.

### 8.2 Observability

Use structured logs and Prometheus-compatible metrics with `task_id`, `run_id`, `job_id`, repository, and exact SHA correlation.

Required families include:

```text
factory_queue_depth
factory_active_leases
factory_task_duration_seconds
factory_lease_reclaims_total
factory_repair_cycles_total
factory_dead_tasks_total
factory_needs_human_total
factory_cost_usd_total
factory_tokens_total
factory_open_prs
factory_first_pass_acceptance_ratio
factory_validator_disagreements_total
factory_rollbacks_total
factory_escaped_defects_total
trust_ci_jobs_total
trust_ci_publication_failures_total
trust_ci_invalid_approvals_total
```

Alert on stuck leases, dead tasks, cost spikes, PR WIP overflow, invalid signatures, failed check publication, backup failure, and active kill switch.

### 8.3 Security

- dedicated hosts or VMs for privileged workers;
- separate OS and database identities;
- no long-lived PATs in agent environments;
- no Docker socket inside untrusted workspaces;
- private keys in managed secrets or root-owned mounts;
- key rotation, revocation, overlap, and recovery drills;
- egress allowlists and DNS policy;
- artifact retention and deletion policy;
- audit log for every external write and approval decision.

### 8.4 Supply chain

- immutable base-image and dependency locks;
- SBOM for services and runner images;
- vulnerability policy with explicit severity threshold and exception expiry;
- signed image and artifact manifests;
- verification before service startup and deployment;
- reproducible build evidence where practical.

### 8.5 Human control surface

The operator view should show:

```text
task and current state
risk before and after diff
current agent and workspace
elapsed runtime and budget
next checkpoint
required approval
structured findings
repair-cycle count
PR and Trust CI status
cost and residual risk
one explicit next action
```

Do not force the human to monitor raw agent chat continuously. Prefer autonomous bounded intervals and batch checkpoints.

## 9. What not to copy from the videos

Do not implement these as goals:

- “Level 5” as a marketing label;
- number of agents, PRs, commits, or generated lines as success metrics;
- blanket removal of human review;
- auto-merge for every repository path;
- trust in multiple reviewers that share the same prompt, model, tests, and context;
- an IDE or dashboard before scheduler reliability, WIP limits, and evidence;
- a new programming language for agents;
- the assumption that a stronger future model fixes weak specifications or architecture;
- cargo-cult adoption of another company’s workflow without local shadow-mode data.

## 10. Program-level definition of done

The dark-factory program is considered operational only when all are true:

```text
GitHub App check is live and app-bound on protected main
standard/high-risk work uses typed specifications
critical architecture rules are executable and externally enforced
agent-generated rules require reviewed promotion
factory tasks are durable, leased, bounded, and recoverable
implementation workspaces are isolated and secret-scoped
one writer is technically enforced
semantic validation produces structured requirement-level verdicts
repair is bounded to three cycles
factory creates PRs without flooding human review
shadow-mode metrics exist for every autonomy candidate
low-risk autonomy is earned and immediately revocable
production delivery has observable canary and tested rollback
no GitHub Actions exist
```

## 11. Branch and PR strategy

Do not implement the whole roadmap in one branch or pull request.

Use this sequence:

```text
milestone/m0-live-trust-authority
milestone/m1-typed-intent
milestone/m2-executable-architecture
milestone/m3-controlled-learning
milestone/m4-factory-control-plane
milestone/m5-execution-plane
milestone/m6-semantic-validation
milestone/m7-shadow-mode
milestone/m8-earned-autonomy
milestone/m9-delivery-plane
```

For each milestone:

1. base from current protected `main`;
2. create or update a design spec under `docs/superpowers/specs/`;
3. create an implementation plan under `docs/superpowers/plans/`;
4. split implementation into independently reviewable tasks;
5. run targeted tests after each task;
6. commit frequently with one coherent purpose per commit;
7. open a draft PR early;
8. update PR evidence after every exact-SHA check;
9. do not mark ready until the milestone exit criteria are met;
10. merge only through the required App-owned Trust CI check and applicable human approval.

## 12. Claw / Grok Build CLI handoff

### 12.1 Pull the roadmap

```bash
cd ~/projects/adaptive-grok-build-pro
git fetch origin
git switch --track origin/docs/dark-factory-roadmap
# If the local branch already exists:
# git switch docs/dark-factory-roadmap && git pull --ff-only origin docs/dark-factory-roadmap
```

### 12.2 Start Grok Build

```bash
grok
```

Use this initial instruction:

```text
Read AGENTS.md, decisions.md, mistakes.md, README.md, trust-ci/README.md,
engineering/runbooks/trust-ci-rollout.md, and DARK_FACTORY_ROADMAP.md.

Treat main as the product source of truth and DARK_FACTORY_ROADMAP.md as the
program backlog. Do not add GitHub Actions. Do not implement multiple milestones
in one branch. Start with M0 only.

First inspect the current repository and live GitHub state. Verify what parts of
M0 are already operational, especially the adaptive-trust-ci App installation,
installation ID, live Check Runs, deployed worker, webhook deliveries, and main
branch protection. Never print or commit private keys or secrets.

Create milestone/m0-live-trust-authority from the current main. Write or update
the M0 design spec and implementation plan before changing runtime behavior.
Use TDD and real integration drills. Keep reasoning low for ordinary workers and
high only for task analysis, architecture, security, release, and adjudication.
Open a draft PR early and update it with exact-SHA evidence. Stop at M0 exit
criteria; do not begin M1 in the same branch.
```

### 12.3 Per-milestone continuation instruction

After a milestone is merged:

```text
Read DARK_FACTORY_ROADMAP.md again. Confirm the previous milestone exit criteria
against current main and live external evidence. Start only the next uncompleted
milestone on its named branch. Reuse published interfaces; do not silently
redesign earlier trust boundaries. Write the milestone spec and plan, implement
through small TDD tasks, commit all evidence, and open a draft PR. Do not proceed
to the following milestone until this one is merged and its external acceptance
criteria are proven.
```

## 13. Roadmap governance

Update this document only through a pull request. Any change that weakens a trust boundary, removes an acceptance gate, expands auto-merge eligibility, or changes a milestone dependency requires security and architecture review.

When actual implementation disproves an assumption, record:

```text
what was assumed
what evidence disproved it
which milestone or interface changes
what backward-compatibility or migration is required
```

Do not rewrite history to make the roadmap appear correct. Preserve the evidence and update the plan.

## 14. Source themes consolidated from the reviewed videos

The roadmap incorporates these recurring lessons:

- implementation speed moves the bottleneck to review and queue management;
- persistent background environments are required for real autonomy;
- deterministic orchestration should own state, leases, retries, and limits;
- agents need verification and backpressure inside the loop;
- Markdown is context, not a sufficient formal specification;
- architecture must be executable and continuously maintained;
- multiple reviewers need genuine independence and meta-adjudication;
- autonomy must be earned by risk class and revoked immediately after failure;
- uncontrolled PR generation is negative throughput;
- agent maintainability and canonical patterns are first-class quality attributes;
- technical debt must be deliberate, owned, and repayable; accidental slop is not debt;
- stronger models do not replace a strong harness, policy, tests, or operational controls;
- copying another company’s “dark factory” without local experiments is cargo cult engineering.
