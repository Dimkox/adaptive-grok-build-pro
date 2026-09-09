# M4 Durable Factory Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a separate PostgreSQL-backed factory control plane that durably accepts immutable M1/M2/M3 handoffs, deduplicates and schedules work, enforces leases/fencing/capacity/budgets, and recovers without an interactive terminal.

**Architecture:** M4 is a standalone `factory/` Python package stacked on the reviewed M3 head. PostgreSQL schema `factory` is the sole operational truth for accepted intent, tasks, runs, monotonic lease fences, capacity allocations, budgets, kill switches, and append-only audit events; deterministic services and a local authenticated API/CLI are thin transaction boundaries around the store. M4 never executes a provider or repository command, installs/activates systemd, writes externally, or reads `trust_ci.*`; those execution and delivery capabilities remain absent until later milestones.

**Tech Stack:** Python 3.11+, FastAPI 0.128.2, Uvicorn 0.48.0, psycopg 3.3.4, PostgreSQL 15+, canonical JSON, `unittest`, real-PostgreSQL integration tests.

**Spec:** `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md`

## Global Constraints

- Stack M4 on the exact reviewed M3 head and require valid frozen M1 spec, M2 architecture, and M3 `GovernanceHandoffV1` digests before intake.
- Keep `factory.*` tables, migrations, role, package, credentials, and runtime entirely separate from `trust_ci.*`; never query or reuse Trust CI jobs, approvals, attestations, keys, policy, holdout, App credentials, or signing material.
- Do not add a root packaging marker, `.github/workflows/**`, provider adapters, workspace execution, note execution brokers, systemd units/activation, push/PR/merge/release/deploy/connector capabilities, or production writes.
- Global readers are at most `20`, readers for one repository are at most `10`, and live application writers are exactly at most `1`; PostgreSQL transaction/fence constraints are correctness authority.
- Infrastructure retries are initial attempt plus at most `2` retries; task wall time is at most `4h`; aggregate provider cost reservation is at most `USD 25`; semantic repair capacity is reserved at `1..3` but not executed by M4.
- Every mutable worker proposal checks task ID, run ID, immutable packet-input digest, lease owner, monotonic fence, current state, deadline, budget, and idempotency key in one transaction.
- Provider/model output cannot select state, retry class, budget, authority, or capability. M4 accepts only typed control-plane commands from authenticated local callers.
- Missing/invalid handoff, M0 availability observation, usage, pricing, lease, fence, or transition data fails closed; it is never interpreted as zero cost or implicit permission.
- Kill switches stop new claims while retaining evidence; reconciliation is idempotent, bounded, and restart-safe.
- All durable bodies and logs are bounded and allowlisted; no credentials, raw prompts, chain-of-thought, native provider streams, or unrestricted stdout/stderr are stored.
- Development runs only task-focused tests. Run PostgreSQL concurrency/drill tests once after store completion and the full repository verifier once on the final product fingerprint, followed by one review wave.

## File Map

- `factory/pyproject.toml`: isolated pinned package and CLI entrypoint.
- `factory/README.md`: control-plane-only operation, limits, API/CLI, recovery, and non-capabilities.
- `factory/compose.yaml`: local PostgreSQL/API development topology using environment substitution only.
- `factory/.env.example`: names and safe dummy defaults, never live credentials.
- `factory/src/adaptive_factory/models.py`: closed enums/dataclasses and validation.
- `factory/src/adaptive_factory/contracts.py`: canonical `TaskIntakeV1`, M1/M2/M3 handoffs, digests, and limits.
- `factory/src/adaptive_factory/state.py`: deterministic transition matrix and retry/error classification.
- `factory/src/adaptive_factory/migrations.py`: immutable packaged migration discovery/checksum/apply.
- `factory/src/adaptive_factory/resources/001_initial.sql`: schema, accepted intents, tasks, events, audit.
- `factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql`: runs, attempts, fences, heartbeats, allocations, counters.
- `factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql`: reservations, usage, kill switches, reconciliation/dead-letter projections.
- `factory/src/adaptive_factory/store.py`: typed store protocol and PostgreSQL transactions.
- `factory/src/adaptive_factory/service.py`: intake, scheduling, transition, retry, kill, and reconciliation use cases.
- `factory/src/adaptive_factory/api.py`: localhost authenticated HTTP boundary.
- `factory/contracts/openapi/factory-control.v1.json`: versioned submit/status/list/cancel/health contract used by later admin clients such as `baby-bot`.
- `factory/src/adaptive_factory/cli.py`: manual administration/intake boundary.
- `factory/src/adaptive_factory/settings.py`: explicit environment configuration with no secret logging.
- `factory/tests/test_contracts.py`: canonical input and fail-closed validation.
- `factory/tests/test_state.py`: transition/error classification.
- `factory/tests/test_migrations.py`: migration ordering/checksum/drift.
- `factory/tests/test_service.py`: deterministic service behavior through a strict fake store.
- `factory/tests/test_api.py`: authentication, request bounds, and response contract.
- `factory/tests/test_postgres_integration.py`: real concurrency, fencing, capacity, retries, kill, restart/reconciliation.
- `factory/tests/postgres_restart_probe.py`: bounded two-process restart/late-result drill.
- `architecture/system.yaml`, `architecture/rules.yaml`, generated diagrams: M2 model updated for the M4 source boundary.
- Root verifier/installer/docs/change package files: package discovery and exact evidence only.

---

### Task 1: Create isolated package and exact frozen-input contracts

**Files:**
- Create: `factory/pyproject.toml`
- Create: `factory/src/adaptive_factory/__init__.py`
- Create: `factory/src/adaptive_factory/models.py`
- Create: `factory/src/adaptive_factory/contracts.py`
- Create: `factory/tests/__init__.py`
- Create: `factory/tests/test_contracts.py`

**Interfaces:**
- Consumes: canonical M1 spec digest, M2 five-field handoff, M3 six-field `GovernanceHandoffV1`, M0 authority availability observation, exact repository/base SHA.
- Produces: `TaskIntakeV1`, `ArchitectureHandoffV1`, `GovernanceHandoffV1`, `TaskLimitsV1`, `AcceptedIntentV1`, `canonical_digest(value) -> str`, and `ContractError(code: str)`.

- [ ] **Step 1: Write failing closed-contract tests**

```python
class ContractTests(unittest.TestCase):
    def test_valid_intake_binds_all_frozen_authorities(self):
        intake = TaskIntakeV1.from_dict(valid_intake())
        self.assertEqual(intake.spec_digest, "a" * 64)
        self.assertEqual(intake.architecture.architecture_contract_version, 1)
        self.assertEqual(intake.governance.governance_contract_version, 1)

    def test_unknown_fields_versions_dirty_sha_and_excessive_limits_fail(self):
        for mutation, code in INVALID_INTAKE_CASES:
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                TaskIntakeV1.from_dict(mutation(valid_intake()))
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest discover -s factory/tests -p 'test_contracts.py' -v`

Expected: FAIL because the package and contracts are absent.

- [ ] **Step 3: Define exact contract shapes and enums**

```python
@dataclass(frozen=True)
class ArchitectureHandoffV1:
    architecture_contract_version: int
    architecture_digest: str
    architecture_evidence_digest: str
    exact_base_sha: str
    exact_head_sha: str

@dataclass(frozen=True)
class GovernanceHandoffV1:
    governance_contract_version: int
    governance_digest: str
    governance_evidence_digest: str
    architecture_digest: str
    exact_base_sha: str
    exact_head_sha: str

@dataclass(frozen=True)
class TaskLimitsV1:
    wall_seconds: int = 14_400
    max_cost_usd_micros: int = 25_000_000
    max_token_units: int = 2_000_000
    max_output_bytes: int = 10_000_000
    max_events: int = 100_000
    infrastructure_retries: int = 2
    semantic_repairs: int = 3

@dataclass(frozen=True)
class TaskIntakeV1:
    contract_version: int
    request_id: str
    repository_id: str
    source_type: Literal["manual", "api", "github_issue_projection"]
    source_id: str
    source_digest: str
    route_id: str
    change_id: str
    exact_base_sha: str
    spec_digest: str
    architecture: ArchitectureHandoffV1
    governance: GovernanceHandoffV1
    policy_digest: str
    m0_authority_observed_at: datetime
    acceptance_ids: tuple[str, ...]
    limits: TaskLimitsV1
```

All input objects are closed. Require lowercase SHA-256 hex, 40-hex Git SHA, bounded NFC strings, sorted unique acceptance IDs, matching architecture digests/SHAs across M2/M3, current M0 observation no older than 300 seconds, and ceilings no greater than the defaults above. `github_issue_projection` is caller-supplied immutable data; M4 does not contact GitHub.

- [ ] **Step 4: Implement canonical accepted-intent and idempotency digest**

Compute:

```python
intent_digest = sha256(canonical_json(intake.to_dict()))
idempotency_key = sha256(canonical_json({
    "contract": "adaptive-factory.intake/v1",
    "repository_id": intake.repository_id,
    "source_type": intake.source_type,
    "source_id": intake.source_id,
    "source_digest": intake.source_digest,
    "exact_base_sha": intake.exact_base_sha,
    "spec_digest": intake.spec_digest,
    "architecture_digest": intake.architecture.architecture_digest,
    "governance_digest": intake.governance.governance_digest,
    "policy_digest": intake.policy_digest,
}))
```

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest discover -s factory/tests -p 'test_contracts.py' -v`

Expected: PASS.

```bash
git add factory/pyproject.toml factory/src/adaptive_factory factory/tests
git commit -m "feat(factory): freeze control-plane contracts"
```

### Task 2: Define the state machine and typed failure policy

**Files:**
- Create: `factory/src/adaptive_factory/state.py`
- Create: `factory/tests/test_state.py`

**Interfaces:**
- Consumes: `TaskStatus`, `RunRole`, `FailureClass`, actor kind, and current transition context.
- Produces: `authorize_transition(current, target, command) -> TransitionDecision` and `classify_retry(failure) -> RetryDecision`.

- [ ] **Step 1: Write failing exhaustive transition tests**

```python
def test_every_state_pair_has_an_explicit_decision(self):
    for current in TaskStatus:
        for target in TaskStatus:
            decision = authorize_transition(current, target, command_for(current, target))
            self.assertIn(decision.code, {"allowed", "forbidden", "needs_human"})

def test_provider_proposal_cannot_choose_state_or_retry_class(self):
    command = transition_command(actor_kind="provider", target="ready_for_human")
    self.assertEqual(authorize_transition(TaskStatus.IMPLEMENTING, TaskStatus.READY_FOR_HUMAN, command).code, "forbidden")
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest discover -s factory/tests -p 'test_state.py' -v`

Expected: FAIL because the state policy is absent.

- [ ] **Step 3: Implement the exact M4 state graph**

Support normal states `inbox`, `triaged`, `waiting_design_approval`, `queued`, `leased`, `analyzing`, `implementing`, `verifying`, `reviewing`, `ready_for_human`; exceptional states `retry`, `needs_human`, `dead`, `cancelled`, `superseded`. Reserve `pr_open`, `merged`, and deployment names only as rejected future values; do not put them in `TaskStatus`.

Only the authenticated control plane may transition. Leased phase transitions require the same live run/fence. `cancelled`, `superseded`, `dead`, and `ready_for_human` are terminal in M4. `needs_human -> queued` requires a separately persisted operator decision ID.

- [ ] **Step 4: Implement retry classification**

Only `database_unavailable`, `worker_lost`, `provider_transport_unavailable`, and `temporary_resource_exhaustion` are retryable infrastructure classes. Validation, policy, authentication, unsupported version/capability, budget, security, stale digest/SHA, protocol, and provider-quality failures return `needs_human` or terminal failure; untrusted text cannot supply the enum.

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest discover -s factory/tests -p 'test_state.py' -v`

Expected: PASS.

```bash
git add factory/src/adaptive_factory/state.py factory/tests/test_state.py
git commit -m "feat(factory): define closed task state policy"
```

### Task 3: Add immutable PostgreSQL migrations

**Files:**
- Create: `factory/src/adaptive_factory/migrations.py`
- Create: `factory/src/adaptive_factory/resources/__init__.py`
- Create: `factory/src/adaptive_factory/resources/001_initial.sql`
- Create: `factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql`
- Create: `factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql`
- Create: `factory/tests/test_migrations.py`

**Interfaces:**
- Consumes: `FACTORY_DATABASE_URL` supplied by operator environment.
- Produces: `discover_migrations()`, `plan_migrations()`, `PostgresMigrator.status()`, `PostgresMigrator.apply()`, and checksum-bound `factory.schema_migrations`.

- [ ] **Step 1: Write failing migration discovery/drift tests**

```python
def test_packaged_migrations_are_contiguous_and_immutable(self):
    migrations = discover_migrations()
    self.assertEqual([item.version for item in migrations], [1, 2, 3])

def test_missing_renamed_or_checksum_changed_applied_migration_fails(self):
    with self.assertRaises(MigrationError):
        plan_migrations(available(), applied_with_checksum_drift())
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest discover -s factory/tests -p 'test_migrations.py' -v`

Expected: FAIL because packaged migrations are absent.

- [ ] **Step 3: Implement migration registry and migrator**

Use a factory-specific advisory lock and `factory.schema_migrations(version, name, sha256, applied_at)`. Require contiguous `001..N`, unique names/versions, UTF-8, immutable SHA-256, and one transaction. Never search or mutate `trust_ci_schema_migrations`.

- [ ] **Step 4: Define normalized durable tables and constraints**

Migration 001 creates `factory.accepted_intents`, `factory.tasks`, `factory.task_events`, and `factory.audit_log`; immutable intent bodies are `jsonb` with byte limits enforced before SQL. Migration 002 creates `factory.runs`, `factory.attempts`, `factory.lease_sequences`, `factory.capacity_counters`, and `factory.capacity_allocations`. Migration 003 creates `factory.budget_reservations`, `factory.usage_observations`, `factory.kill_switches`, and `factory.reconciliation_runs`.

Required database constraints include unique intake idempotency key, unique `(task_id, event_sequence)`, unique proposal idempotency key, non-negative attempts/cost/tokens, deadlines at most four hours after acceptance, partial unique live writer allocation, unique live allocation per run, and foreign keys that prevent cross-task run/allocation/events.

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest discover -s factory/tests -p 'test_migrations.py' -v`

Expected: PASS.

```bash
git add factory/src/adaptive_factory/migrations.py factory/src/adaptive_factory/resources factory/tests/test_migrations.py factory/pyproject.toml
git commit -m "feat(factory): add durable schema migrations"
```

### Task 4: Implement transactional intake, deduplication, and supersession

**Files:**
- Create: `factory/src/adaptive_factory/store.py`
- Create: `factory/src/adaptive_factory/service.py`
- Create: `factory/tests/test_service.py`
- Create: `factory/tests/test_postgres_integration.py`

**Interfaces:**
- Consumes: `AcceptedIntentV1`, authenticated `Actor`, injected UTC `now`.
- Produces: `FactoryStore.intake(intent, actor, now) -> IntakeResult(task, created)`, `get_task(task_id)`, `list_tasks(filter, limit, cursor)`, and append-only audit/event rows.

- [ ] **Step 1: Write failing service and real-PostgreSQL intake tests**

```python
def test_duplicate_intake_returns_one_active_task(self):
    first = service.intake(valid_intake(), actor=OPERATOR, now=NOW)
    second = service.intake(valid_intake(), actor=OPERATOR, now=NOW)
    self.assertTrue(first.created)
    self.assertFalse(second.created)
    self.assertEqual(first.task.task_id, second.task.task_id)

def test_changed_source_or_frozen_digest_supersedes_old_active_task(self):
    old = service.intake(valid_intake(), actor=OPERATOR, now=NOW).task
    new = service.intake(valid_intake(source_digest="f" * 64), actor=OPERATOR, now=LATER).task
    self.assertEqual(store.get_task(old.task_id).status, TaskStatus.SUPERSEDED)
    self.assertNotEqual(old.task_id, new.task_id)
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest factory.tests.test_service factory.tests.test_postgres_integration.PostgresIntakeTests -v`

Expected: FAIL because the store/service are absent.

- [ ] **Step 3: Implement the store protocol and intake transaction**

Lock the repository/source identity row, insert immutable accepted intent by digest, return the existing active task for the exact idempotency key, and supersede older non-terminal tasks when source digest, base SHA, spec, architecture, governance, or policy digest changes. Append both task event and audit records in the same transaction. Never overwrite accepted intent JSON.

- [ ] **Step 4: Bound query/read surfaces**

Use opaque `(created_at, task_id)` cursors, maximum page size `100`, statement timeout `5s`, deterministic ordering, and explicit selected columns. Return typed projections, never arbitrary SQL/JSON bodies or credentials.

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest factory.tests.test_service factory.tests.test_postgres_integration.PostgresIntakeTests -v`

Expected: PASS against the configured disposable PostgreSQL database.

```bash
git add factory/src/adaptive_factory/store.py factory/src/adaptive_factory/service.py factory/tests/test_service.py factory/tests/test_postgres_integration.py
git commit -m "feat(factory): persist idempotent task intake"
```

### Task 5: Implement leases, fencing, and 20/10/1 capacity

**Files:**
- Modify: `factory/src/adaptive_factory/store.py`
- Modify: `factory/src/adaptive_factory/service.py`
- Modify: `factory/tests/test_service.py`
- Modify: `factory/tests/test_postgres_integration.py`

**Interfaces:**
- Consumes: `ClaimRequest(worker_id, role, repository_allowlist, lease_seconds)`, live task, capacity rows, kill state.
- Produces: `LeaseGrant(task_id, run_id, role, owner, fence, expires_at, packet_input_digest)`, `heartbeat(grant, now)`, `commit_proposal(grant, proposal, now)`, and `release(grant, outcome, now)`.

- [ ] **Step 1: Write failing concurrency/fence tests**

```python
def test_two_workers_cannot_claim_same_task(self):
    grants = concurrently(2, lambda i: store.claim(reader_claim(f"reader-{i}"), now=NOW))
    self.assertEqual(sum(grant is not None for grant in grants), 1)

def test_capacity_is_twenty_global_ten_per_repo_and_one_writer(self):
    self.assertEqual(count_claims(role="reader", repositories=["a", "b"], attempts=30), 20)
    self.assertEqual(count_claims(role="reader", repositories=["a"], attempts=20), 10)
    self.assertEqual(count_claims(role="writer", repositories=["a", "b"], attempts=5), 1)

def test_late_fence_cannot_heartbeat_or_commit(self):
    old = claim_then_expire_and_reclaim()
    with self.assertRaisesRegex(FenceError, "stale fence"):
        store.commit_proposal(old, valid_terminal_proposal(), now=LATER)
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest factory.tests.test_postgres_integration.PostgresLeaseTests -v`

Expected: FAIL because claim/fence/capacity behavior is absent.

- [ ] **Step 3: Implement atomic claim**

In one transaction: lock global/repository capacity counters in stable order, reject active kill switches, select eligible work with `FOR UPDATE SKIP LOCKED`, increment the task's monotonic fence sequence, create run/attempt/allocation, transition to `leased`, and append audit/event. Lease duration must be `30..300` seconds and expiry cannot exceed task deadline.

- [ ] **Step 4: Enforce capacity in PostgreSQL**

Maintain locked counters with checks `global_reader <= 20`, `repository_reader <= 10`, `global_writer <= 1`; add a partial unique index for an unreleased writer allocation. Every release/reclaim decrements counters transactionally and cannot go below zero. Application prechecks improve errors but are not authority.

- [ ] **Step 5: Fence every proposal**

Heartbeat, phase transition, usage, note/finding/artifact metadata, retry, terminal, and release operations require current `run_id`, owner, fence, unexpired lease, packet-input digest, and idempotency key. Replays return the original result only when payload digest matches; conflicting reuse fails.

- [ ] **Step 6: Run focused tests and commit**

Run: `python3 -m unittest factory.tests.test_service factory.tests.test_postgres_integration.PostgresLeaseTests -v`

Expected: PASS.

```bash
git add factory/src/adaptive_factory/store.py factory/src/adaptive_factory/service.py factory/tests
git commit -m "feat(factory): enforce fenced 20-10-1 leases"
```

### Task 6: Add bounded retry, dead-letter, deadlines, and budget accounting

**Files:**
- Modify: `factory/src/adaptive_factory/store.py`
- Modify: `factory/src/adaptive_factory/service.py`
- Modify: `factory/tests/test_service.py`
- Modify: `factory/tests/test_postgres_integration.py`

**Interfaces:**
- Consumes: typed `FailureClass`, `BudgetReservation`, trustworthy `UsageObservation(price_table_digest, provenance)`.
- Produces: `retry_or_terminal(...)`, `reserve_budget(...)`, `reconcile_usage(...)`, `dead`/`needs_human` terminal projections.

- [ ] **Step 1: Write failing retry and budget tests**

```python
def test_initial_plus_two_infrastructure_retries_then_dead(self):
    task = queued_task()
    for expected_attempt in (1, 2, 3):
        grant = claim(task)
        self.assertEqual(grant.attempt_number, expected_attempt)
        result = retry_infrastructure(grant)
    self.assertEqual(result.status, TaskStatus.DEAD)

def test_missing_usage_or_price_blocks_next_reservation(self):
    grant = claim_with_reservation()
    store.record_usage(grant, usage_without_trusted_price(), now=NOW)
    with self.assertRaisesRegex(BudgetError, "trustworthy usage"):
        store.reserve_budget(grant.task_id, next_call(), now=LATER)
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest factory.tests.test_service.FactoryBudgetTests factory.tests.test_postgres_integration.PostgresBudgetTests -v`

Expected: FAIL because retry/budget transactions are absent.

- [ ] **Step 3: Implement attempt exhaustion and dead-letter evidence**

Increment attempts only when a lease is granted. Retry only typed infrastructure failures, with maximum attempt number `3`. On third infrastructure failure, atomically transition to `dead`, release capacity, retain all attempts/events, and record a bounded failure code/message digest. Non-retryable failures transition directly to `needs_human`, `cancelled`, or `dead` according to `state.py`.

- [ ] **Step 4: Implement aggregate wall/token/cost reservations**

Reserve before dispatch under a task row lock. Reject reservation when aggregate reserved plus observed exceeds task ceilings or deadline. Store USD as integer micros and token units as integers. Reconcile once by unique `(run_id, provider_call_id)` with exact price-table digest and metering provenance. Missing/invalid usage marks accounting blocked and prevents another reservation.

- [ ] **Step 5: Run focused tests and commit**

Run: `python3 -m unittest factory.tests.test_service.FactoryBudgetTests factory.tests.test_postgres_integration.PostgresBudgetTests -v`

Expected: PASS.

```bash
git add factory/src/adaptive_factory/store.py factory/src/adaptive_factory/service.py factory/tests
git commit -m "feat(factory): bound retries deadlines and budgets"
```

### Task 7: Add kill switches, append-only audit, and restart reconciliation

**Files:**
- Modify: `factory/src/adaptive_factory/store.py`
- Modify: `factory/src/adaptive_factory/service.py`
- Modify: `factory/tests/test_service.py`
- Modify: `factory/tests/test_postgres_integration.py`
- Create: `factory/tests/postgres_restart_probe.py`

**Interfaces:**
- Consumes: authenticated operator command with exact scope `global|repository`, reason code, actor, and idempotency key.
- Produces: `set_kill_switch`, `clear_kill_switch`, `reconcile(limit, cursor, now) -> ReconcileResult`, and append-only audit chain.

- [ ] **Step 1: Write failing kill/reconciliation tests**

```python
def test_kill_switch_stops_new_claims_without_deleting_or_stealing_live_evidence(self):
    live = claim(reader_claim("reader-1"))
    service.set_kill_switch(scope="global", reason_code="operator-stop", actor=OPERATOR)
    self.assertIsNone(store.claim(reader_claim("reader-2"), now=NOW))
    self.assertEqual(store.get_run(live.run_id).fence, live.fence)
    self.assertGreater(store.audit_count(live.task_id), 0)

def test_reconciliation_reclaims_expired_lease_and_rejects_late_worker(self):
    old = claim_with_short_lease()
    result = service.reconcile(limit=100, cursor=None, now=AFTER_EXPIRY)
    self.assertEqual(result.reclaimed, 1)
    new = store.claim(reader_claim("reader-2"), now=AFTER_EXPIRY)
    self.assertGreater(new.fence, old.fence)
    self.assertRaises(FenceError, store.heartbeat, old, now=AFTER_EXPIRY)
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest factory.tests.test_postgres_integration.PostgresRecoveryTests -v`

Expected: FAIL because kill/reconciliation behavior is absent.

- [ ] **Step 3: Implement authenticated kill switches and hash-chained audit**

Require operator actor kind, bounded reason code, and idempotency key. Global or repository switch blocks claims but does not delete/alter existing result evidence. Audit rows are insert-only and contain previous event digest plus canonical current digest over actor, action, resource, reason code, receive time, and bounded metadata; add database permissions/tests that reject update/delete through the runtime role.

- [ ] **Step 4: Implement bounded reconciliation**

Each call handles at most `100` ordered candidates with a `5s` statement timeout: expired leases, orphan allocations, deadline-exhausted tasks, accounting-blocked runs, stale digest/base tasks, and incomplete terminal projections. Use idempotent event keys; re-running produces no duplicate state transition or counter decrement.

- [ ] **Step 5: Run restart/late-result drill and commit**

Run:

```bash
python3 -m unittest factory.tests.test_postgres_integration.PostgresRecoveryTests -v
python3 factory/tests/postgres_restart_probe.py --database-url-env FACTORY_TEST_DATABASE_URL
```

Expected: the probe kills the lease-holder subprocess, waits only until the configured expiry, reclaims with a higher fence, and proves the late result is rejected.

```bash
git add factory/src/adaptive_factory factory/tests
git commit -m "feat(factory): reconcile durable work safely"
```

### Task 8: Expose authenticated local API and CLI without execution capability

**Files:**
- Create: `factory/src/adaptive_factory/settings.py`
- Create: `factory/src/adaptive_factory/api.py`
- Create: `factory/src/adaptive_factory/cli.py`
- Create: `factory/tests/test_api.py`
- Create: `factory/contracts/openapi/factory-control.v1.json`
- Create: `factory/.env.example`
- Create: `factory/compose.yaml`
- Modify: `factory/pyproject.toml`

**Interfaces:**
- Consumes: `FACTORY_DATABASE_URL`, `FACTORY_API_TOKEN_FILE`, fixed bind address, typed JSON bodies.
- Produces: Unix-domain-socket HTTP endpoints `/health/live`, `/health/ready`, `POST /v1/tasks`, `GET /v1/tasks/{task_id}`, `GET /v1/tasks`, `POST /v1/tasks/{task_id}/cancel`, plus worker/operator endpoints `/v1/claims`, `/v1/heartbeats`, `/v1/proposals`, `/v1/kill-switches`, `/v1/reconcile`; CLI `migrate`, `intake`, `show`, `list`, `cancel`, `kill`, `unkill`, `reconcile`.

- [ ] **Step 1: Write failing authentication/bounds tests**

```python
def test_mutating_endpoints_require_constant_time_bearer_auth(self):
    self.assertEqual(client.post("/v1/tasks", json=valid_intake()).status_code, 401)
    self.assertEqual(client.post("/v1/tasks", headers=AUTH, json=valid_intake()).status_code, 201)

def test_api_has_no_provider_external_write_or_systemd_endpoint(self):
    paths = set(client.get("/openapi.json").json()["paths"])
    self.assertFalse(paths & {"/v1/providers/run", "/v1/git/push", "/v1/pull-requests", "/v1/deploy", "/v1/systemd"})

def test_baby_bot_surface_is_versioned_idempotent_and_never_logs_auth(self):
    response = client.post("/v1/tasks", headers={**BOT_ADMIN_AUTH, "Idempotency-Key": REQUEST_ID, "X-Correlation-ID": CORRELATION_ID}, json=valid_intake())
    self.assertEqual(response.status_code, 201)
    self.assertEqual(response.headers["X-Correlation-ID"], CORRELATION_ID)
    self.assertNotIn(BOT_ADMIN_TOKEN, captured_logs())

```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest discover -s factory/tests -p 'test_api.py' -v`

Expected: FAIL because API/CLI/settings are absent.

- [ ] **Step 3: Implement explicit settings, Unix-socket transport, and scoped local authentication**

Listen by default on `FACTORY_SOCKET_PATH=/run/adaptive-factory/control.sock`, created by the operator with a dedicated group and mode `0660`; do not depend on the host network namespace. This is required because `/home/pall/baby-bot` runs as `baby-bot.service` inside `NetworkNamespacePath=/run/netns/vpn`. TCP listening is disabled by default and a non-loopback bind is never supported by this M4 slice.

Read bearer credentials from root/operator-provisioned regular no-follow files, never from task content or URL/query parameters; require token-file mode `0600`, compare with `hmac.compare_digest`, and map each token digest to a closed scope set. The future `baby-bot` client receives only `task:submit`, `task:read`, `task:list`, and `task:cancel`; it cannot claim, heartbeat, propose, kill, reconcile, or migrate. Redact `Authorization`, token values, query strings, settings, and request bodies by construction; cap requests at `1 MiB` and reject unknown JSON fields.

- [ ] **Step 4: Implement thin API/CLI boundaries**

Endpoints invoke only service methods and return typed bounded projections. `POST /v1/tasks` requires `Idempotency-Key` and `X-Correlation-ID`; status/list/cancel echo or generate a bounded correlation ID, and cancel is idempotent without deleting evidence. Health readiness checks migrations and database connectivity, not M0 health by proxy. CLI accepts intake JSON from an explicit regular file/stdin with a 1 MiB cap and prints canonical JSON. Neither surface shells out, fetches GitHub, invokes providers, touches repositories, installs units, or writes externally.

Create and validate `factory/contracts/openapi/factory-control.v1.json` with only the five `baby-bot` operations plus health in its public/admin tag; worker/operator operations use separate tags and scopes. The later bot adapter must verify the Telegram sender against an explicit admin allowlist before calling this API. M4 does not edit, restart, or deploy `/home/pall/baby-bot`.

- [ ] **Step 5: Add safe local compose example and commit**

`compose.yaml` uses `${FACTORY_POSTGRES_DB}`, `${FACTORY_POSTGRES_USER}`, `${FACTORY_POSTGRES_PASSWORD}`, and a named volume; `.env.example` contains non-secret local placeholders and warns not to commit real values. Do not read or copy any existing `.env`.

The integration security gate records that existing `python-telegram-bot`/`httpx` request logging has exposed a Telegram Bot API token in URL-shaped log data. Before any bot integration deployment, a human operator must rotate that token outside the agent environment and the bot slice must set `httpx`, `httpcore`, and `telegram` transport loggers to `WARNING` or stricter plus install URL redaction that replaces `/bot<token>/` with `/bot<redacted>/`. The agent must neither read nor rotate the Telegram secret, and no token or historical leaked value may enter this repository, tests, fixtures, reports, commands, URLs, or logs.

Run: `python3 -m unittest discover -s factory/tests -p 'test_api.py' -v`

Expected: PASS.

```bash
git add factory/src/adaptive_factory factory/tests/test_api.py factory/contracts/openapi/factory-control.v1.json factory/pyproject.toml factory/.env.example factory/compose.yaml
git commit -m "feat(factory): expose local control API"
```

### Task 9: Model the M4 source boundary in M2 and integrate repository tooling

**Files:**
- Modify: `architecture/system.yaml`
- Modify: `architecture/rules.yaml`
- Modify: `architecture/generated/context.mmd`
- Modify: `architecture/generated/container.mmd`
- Modify: `architecture/generated/data-flow.mmd`
- Modify: `architecture/generated/deployment.mmd`
- Modify: `architecture/generated/trust-boundary.mmd`
- Modify: `.grok-stack/adaptive_grok/verification.py`
- Modify: `.grok-stack/config/managed.json`
- Modify: `scripts/install_into.py`
- Modify: `tests/test_architecture_model.py`
- Modify: `tests/test_architecture_fitness.py`
- Modify: `tests/test_installer.py`
- Modify: `tests/test_structure.py`
- Modify: `README.md`
- Modify: `DARK_FACTORY_ROADMAP.md`
- Create: `factory/README.md`

**Interfaces:**
- Consumes: M1/M2/M3 handoffs and the new factory contracts/schema.
- Produces: executable architecture nodes/contracts/edges for the source-only M4 control plane and root verification of the isolated package.

- [ ] **Step 1: Write failing architecture/structure tests**

```python
def test_factory_is_separate_from_trust_ci_and_has_no_execution_edge(self):
    snapshot = load_architecture(ROOT)
    factory_nodes = nodes_in_domain(snapshot, "TRUST-FACTORY-CONTROL")
    self.assertTrue(factory_nodes)
    self.assertFalse(any(edge_between(factory_nodes, {"NODE-TRUST-CI-POSTGRES"}, edge) for edge in snapshot.system["edges"]))
    self.assertFalse(any(edge["type"] == "publication" for edge in edges_from(factory_nodes, snapshot)))

def test_root_has_no_packaging_marker_and_factory_has_own_package(self):
    self.assertFalse((ROOT / "pyproject.toml").exists())
    self.assertTrue((ROOT / "factory/pyproject.toml").exists())
```

- [ ] **Step 2: Confirm RED**

Run: `python3 -m unittest tests.test_architecture_model tests.test_architecture_fitness tests.test_installer tests.test_structure -v`

Expected: FAIL because M2/root tooling does not know M4.

- [ ] **Step 3: Extend architecture and diagrams**

Add nodes for local factory API, supervisor/scheduler logic, and separate PostgreSQL `factory.*`; contracts for the versioned admin submit/status/list/cancel/health API plus intake/claim/proposal schemas; data classes for immutable task authority, operational task state, and bounded audit. Model the admin client edge as authenticated HTTP over an operator-owned Unix socket, not TCP/network-namespace reachability. Edges are local-only/database-role, bounded, idempotent, and fail closed. Do not add the `baby-bot` adapter implementation, provider, workspace, systemd activation, GitHub write, Trust CI DB, or production edges.

Run `python3 scripts/grok_architecture.py diagram --json`, patch the five exact returned artifacts, then require `diagram --check` PASS.

- [ ] **Step 4: Integrate isolated package verification/installation**

Root verifier runs factory unit tests and, only when `FACTORY_TEST_DATABASE_URL` is explicitly present, real PostgreSQL integration tests. Installer copies factory source/config/examples as a nested package but never copies `.env`, operator token files, live database URLs, volumes, or migrations into an already adopted database. Update README current state and full stack graph; mark M4 source complete only after its evidence gate and M5 absent.

- [ ] **Step 5: Run focused integration and commit**

```bash
python3 scripts/grok_architecture.py validate --json
python3 scripts/grok_architecture.py diagram --check --json
python3 -m unittest tests.test_architecture_model tests.test_architecture_fitness tests.test_installer tests.test_structure -v
python3 -m unittest discover -s factory/tests -p 'test_*.py' -v
git diff --check
git add architecture .grok-stack scripts tests factory README.md DARK_FACTORY_ROADMAP.md
git commit -m "feat(factory): integrate M4 control plane"
```

Expected: all focused checks PASS.

### Task 10: Run the one real PostgreSQL M4 exit gate

**Files:**
- Modify as failures require: `factory/tests/test_postgres_integration.py`
- Create: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-postgres-exit.md`

**Interfaces:**
- Consumes: disposable PostgreSQL 15+ database with no Trust CI schema/role reuse.
- Produces: exact command/result evidence for concurrency, fencing, idempotency, retry/dead, budget, kill, restart, and reconciliation.

- [ ] **Step 1: Provision only a disposable test database**

Use operator-provided `FACTORY_TEST_DATABASE_URL` or `docker compose -f factory/compose.yaml up -d postgres`. Do not inspect existing `.env` files or production credentials. Apply migrations with `adaptive-factory migrate`.

- [ ] **Step 2: Run the complete PostgreSQL integration group once**

Run:

```bash
FACTORY_TEST_DATABASE_URL="$FACTORY_TEST_DATABASE_URL" python3 -m unittest factory.tests.test_postgres_integration -v
FACTORY_TEST_DATABASE_URL="$FACTORY_TEST_DATABASE_URL" python3 factory/tests/postgres_restart_probe.py --database-url-env FACTORY_TEST_DATABASE_URL
```

Expected: duplicate intake yields one task; competing claims yield one lease; reader ceilings are exactly 20/10; writer ceiling is one; late fences fail; third retry dead-letters; stale tasks supersede; budget/WIP stops dispatch; kill prevents claims without evidence loss; restart reconciliation reclaims once.

- [ ] **Step 3: Record bounded evidence and remove disposable runtime**

Record PostgreSQL version, migration digests, test names/counts, elapsed time, and PASS/FAIL without connection strings or credentials. Stop the disposable compose project if this task started it; retain the named volume only until rollback/restart verification is complete, then remove it through the approved disposable-test cleanup path.

- [ ] **Step 4: Commit the exit evidence**

```bash
git add engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-postgres-exit.md
git commit -m "test(factory): prove durable control-plane invariants"
```

### Task 11: Final exact-fingerprint verification, review, release, and rollback record

**Files:**
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/brief.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/requirements.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/test-plan.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/architecture.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/release.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/rollback.md`
- Modify: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/tasks.md`
- Create after review: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-code-review.md`
- Create after review: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-test-review.md`
- Create after review: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-security-review.md`
- Create after review: `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-release-review.md`

**Interfaces:**
- Consumes: final M4 product fingerprint and M3 stacked-base identity.
- Produces: one full verifier, one independent review wave, exact local receipts, stacked PR readiness; no provider/systemd/external-write activation.

- [ ] **Step 1: Finish durable M4 documentation before final verification**

Record exact M4 state/schema/contracts, migration recovery, runtime-role permissions, limits, metrics, alert conditions, staged local rollout, and forward recovery. Release order is M2 exact base -> M3 PR -> M4 PR -> separately reviewed `baby-bot` admin adapter/integration slice. Go is source-level local control plane only; bot edits/deployment, M5 execution/systemd activation, and M7 external actions remain separate gates. Bot-integration no-go conditions include an unrotated exposed Telegram token, INFO request logging that can render Bot API URLs, absent URL redaction, non-admin Telegram access, token-in-URL authentication, or unavailable Unix-socket permissions.

- [ ] **Step 2: Define staged rollout and rollback commands**

Rollout: backup the disposable/staging `factory` schema, run migration status, apply migrations under advisory lock, start API manually on loopback, verify readiness, intake a synthetic task, claim/heartbeat/release it, enable kill switch, restart API, reconcile, then clear switch. Rollback before first intake may drop only the explicitly named disposable `factory` schema; after durable intake, never down-migrate—enable kill, stop claims, preserve audit/evidence, restore from the verified schema backup into a separate database, or forward-fix with migration `004+`.

- [ ] **Step 3: Run exactly one full repository verifier on final product fingerprint**

Run: `python3 scripts/grok_verify.py --mode pr`

Expected: root base/AI profiles, nested factory tests, governance/architecture checks, and exact receipt binding PASS. Do not repeat the full suite for report-only paperwork.

- [ ] **Step 4: Dispatch one parallel route-selected review wave**

Dispatch `code_reviewer`, `test_reviewer`, `security_reviewer`, and `release_reviewer` against the same SHA/fingerprint. Security must inspect SQL role isolation, query parameterization, token handling, no Trust CI access, late-fence rejection, audit immutability, and absence of provider/systemd/external-write capabilities. Test review must bind real PostgreSQL concurrency/restart evidence.

- [ ] **Step 5: Repair findings with focused tests only**

For each concrete finding, first add a failing regression test, then the minimal fix, then run only affected factory/root tests and affected re-review. If product code changes, run one replacement final verifier after the last repair; never claim the stale verifier.

- [ ] **Step 6: Record review receipts and commit exact evidence**

```bash
python3 scripts/grok_review.py code_review --status pass --report engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-code-review.md
python3 scripts/grok_review.py test_review --status pass --report engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-test-review.md
python3 scripts/grok_review.py security_review --status pass --report engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-security-review.md
python3 scripts/grok_review.py release_review --status pass --report engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/m4-release-review.md
python3 scripts/grok_status.py
git add engineering/changes/20260826-model-agnostic-autonomous-factory-355689
git commit -m "docs: record exact M4 evidence"
```

Expected: zero local evidence gaps and a clean tree. Push/open only the M4 stacked PR through exact delegated PR-only operations. Do not merge, install/activate systemd, invoke a provider, deploy, or perform any autonomous external write.

## Self-Review Record

- Spec coverage: tasks cover immutable M1/M2/M3 intake, idempotency/correlation, supersession, PostgreSQL migrations/source-of-truth, SKIP LOCKED leases, monotonic fencing, reclaim, initial-plus-two retries, dead-letter, 20/10/1 capacity, wall/token/cost budgets, kill switches, append-only audit, restart reconciliation, Unix-socket authenticated submit/status/list/cancel/health API for a later admin-only `baby-bot` client, local CLI, metrics-ready records, release, and forward recovery.
- Placeholder scan: every task names exact files, interfaces, red/green commands, implementation content, and commit boundary; no placeholder marker remains.
- Type consistency: M4 consumes the exact M2 five-field architecture handoff and exact M3 six-field `GovernanceHandoffV1`; `TaskIntakeV1`, `TaskLimitsV1`, `LeaseGrant`, state names, limit units, and digest field names remain identical throughout.
- Scope boundary: the `/home/pall/baby-bot` adapter/edit/deployment and Telegram token rotation are a separate post-M4 integration slice; provider execution, note execution, workspace isolation, systemd activation, push/PR/merge/release/deploy/connectors, production mutation, and all Trust CI state/keys/authority are explicitly absent; those belong to M5+ or operator-owned delivery.
