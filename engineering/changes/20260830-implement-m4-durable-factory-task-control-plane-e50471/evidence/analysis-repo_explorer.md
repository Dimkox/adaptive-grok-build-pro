# Repository analysis — M4 Durable Factory Task Control Plane

Route: `e50471553166`  
Active change: `20260830-implement-m4-durable-factory-task-control-plane-e50471`  
Scope: read-only repository/history analysis; no product changes made.

## Finding: approved M4 design and plan

The approved implementation plan is present only on the milestone history, not in
the active checkout:

- `docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md` at
  `c1e4203` (`docs: plan stacked M3 and M4 delivery`), 745 lines.
- The corresponding design is
  `docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md`
  at the same revision.
- `DARK_FACTORY_ROADMAP.md` §M4 gives the shorter product objective, state
  machine, durable-field list, work items, and exit criteria.

The plan is specific: create a separate nested `factory/` Python package with a
PostgreSQL `factory` schema as its sole operational truth. It explicitly excludes
provider/repository execution, external writes, systemd activation, GitHub
operations, deployment, and *all* reads/writes of `trust_ci.*`.

## Material base mismatch — blocker before implementation

The active route declares base commit
`1c06299894279a88b881defa3f19b004fa742223` (`docs: refresh fresh-agent
bootstrap on current main (#9)`). The M4 plan requires its work to be stacked on
the reviewed M3 head `42bd75d180beb18fae712c907c9c12d410f5c7de`
(`milestone/m3-controlled-knowledge-debt`). These histories diverge:

```text
merge-base(route base, M3 head) = 069fe8226addb8a1922dde3db4e753434baa3a3d
M3 head is not an ancestor of route base
route base is not an ancestor of M3 head
```

Consequently, the route checkout lacks M2/M3 implementation artifacts that M4
must consume: `architecture/`, `governance/`,
`.grok-stack/adaptive_grok/{architecture,architecture_fitness,governance}.py`,
`schemas/governance-handoff-v1.schema.json`, `scripts/grok_architecture.py`,
and their tests. Do **not** recreate substitute M2/M3 handoff contracts in M4.
Resolve the stacking/base decision at the named scope-and-design gate, then work
on the reviewed M3 tree (or explicitly rebase/cherry-pick the already-reviewed
M2/M3 changes with fresh validation).

## Existing milestone implementation and reusable patterns

### M0 / Trust CI (current checkout)

`trust-ci/` is a separate FastAPI/PostgreSQL trust-control service. It is a
useful *implementation-pattern* reference only, never a dependency or state
source for M4:

| Existing pattern | Reference | M4 adaptation |
| --- | --- | --- |
| Frozen dataclasses and canonical JSON validation | `trust-ci/src/adaptive_trust_ci/models.py` | Define independent immutable `TaskIntakeV1`, architecture/governance handoffs, limits, task/run/attempt/lease projections. |
| Checksum-locked packaged migrations + advisory lock | `trust-ci/src/adaptive_trust_ci/migrations.py`, `resources/001_schema.sql` | Copy the design pattern into `factory/src/adaptive_factory/migrations.py`, but use `factory.schema_migrations` and a factory-specific lock only. |
| `FOR UPDATE SKIP LOCKED` leasing and restart recovery | `trust-ci/src/adaptive_trust_ci/store.py`; `trust-ci/tests/test_postgres_integration.py` | Implement independent factory claims, monotonic fences, allocations, capacity counters, and late-result rejection. Trust CI's owner-only lease is insufficient by itself because M4 requires fences and 20/10/1 capacity. |
| FastAPI bearer comparison and bounded public projections | `trust-ci/src/adaptive_trust_ci/api.py` | Implement a distinct Unix-socket, scope-mapped local API; no endpoint may execute providers/repository commands. |
| argparse administration | `trust-ci/src/adaptive_trust_ci/cli.py` | Independent `adaptive-factory` CLI: migrate/intake/show/list/cancel/kill/unkill/reconcile. |
| real PostgreSQL test gating | `trust-ci/tests/test_postgres_integration.py`, `trust-ci/compose.test.yaml` | Use only `FACTORY_TEST_DATABASE_URL`, a disposable factory database/schema, concurrency tests, and a restart/late-fence probe. |

Current Trust CI tables are unqualified names such as `trust_ci_jobs` and
`trust_ci_schema_migrations`; they are not the M4 schema and must not be queried,
extended, or reused. The existing service also has signing/GitHub/worker
capabilities that are prohibited in M4.

### M1

Current checkout includes the M1 typed change-spec implementation:
`schemas/change-spec.schema.json`, `scripts/grok_spec.py`, and
`tests/test_change_spec.py`. M4 must consume a valid frozen M1 spec digest as
input; it should neither weaken the schema nor turn the current active change's
template `change-spec.yaml` into a fabricated authority.

### M2 and M3 (reviewed branch, absent from active checkout)

The reviewed M3 branch adds the required architecture and governance machinery.
Its stable M3 handoff schema is
`schemas/governance-handoff-v1.schema.json`, with exactly six fields:
`governance_contract_version`, `governance_digest`,
`governance_evidence_digest`, `architecture_digest`, `exact_base_sha`, and
`exact_head_sha`. Its model is `GovernanceHandoffV1` in
`.grok-stack/adaptive_grok/governance.py`.

M4 must also consume the M2 five-field architecture handoff specified in the
approved plan, and validate all cross-handoff digest/SHA equality. The M3 source
tree contains `architecture/system.yaml`, `architecture/rules.yaml`, five
generated diagrams, `tests/test_architecture_model.py`,
`tests/test_architecture_fitness.py`, `tests/test_governance.py`, and
`tests/test_governance_fitness.py`; Task 9 of the approved plan modifies those
exact M2/M3 files to model the M4 boundary.

## Exact planned product files

All currently absent, to be added under the isolated package:

```text
factory/
  pyproject.toml                 README.md          compose.yaml       .env.example
  contracts/openapi/factory-control.v1.json
  src/adaptive_factory/
    __init__.py  models.py  contracts.py  state.py  migrations.py
    store.py     service.py api.py        cli.py    settings.py
    resources/{__init__.py,001_initial.sql,002_runs_leases_capacity.sql,
               003_budgets_kills_reconciliation.sql}
  tests/{__init__.py,test_contracts.py,test_state.py,test_migrations.py,
         test_service.py,test_api.py,test_postgres_integration.py,
         postgres_restart_probe.py}
```

The plan also modifies, *after the M2/M3 baseline is available*:

```text
architecture/system.yaml                 architecture/rules.yaml
architecture/generated/{context,container,data-flow,deployment,trust-boundary}.mmd
.grok-stack/adaptive_grok/verification.py
.grok-stack/config/managed.json          scripts/install_into.py
tests/test_architecture_model.py         tests/test_architecture_fitness.py
tests/test_installer.py                  tests/test_structure.py
README.md                                DARK_FACTORY_ROADMAP.md
```

The active change package needs completed scope/design/test/release/rollback
records and M4 PostgreSQL exit evidence under its own `evidence/` directory;
the historical plan's old `20260826-model-agnostic-autonomous-factory-355689`
package is reference material, not the active evidence destination.

## Required behavioral boundary and test anchors

1. Closed, versioned intake binds M1 spec, M2 architecture, M3 governance,
   route/change identifiers, exact base SHA, policy digest, M0 availability
   observation, source digest, and strict ceilings. Canonical intent and
   idempotency digests are SHA-256 of canonical JSON.
2. Three immutable migrations define separate `factory.*` accepted-intent,
   task/event/audit, run/attempt/fence/capacity, and budget/usage/kill/
   reconciliation tables. Migration checksums must be contiguous and immutable.
3. Intake locks source identity, returns the active task for exact duplicate
   idempotency, and supersedes nonterminal predecessor tasks on a changed source
   or frozen authority. Each mutation appends event plus audit in the same
   transaction.
4. Claim uses `FOR UPDATE SKIP LOCKED`, a monotonic fence, live allocation, and
   stable-order capacity locks. PostgreSQL is authority for reader ceilings
   20 global / 10 per repository and one global writer. Every late/replayed
   mutation must bind run, owner, fence, live expiry, packet digest, and proposal
   idempotency key.
5. Only typed infrastructure failures retry, for initial attempt plus two
   retries. Third infrastructure failure is `dead`; untrusted/provider text may
   not pick task state/retry/budget authority. Missing trustworthy price/usage
   blocks later reservations.
6. Global/repository kill switches block new claims but retain evidence. Audit
   is append-only hash chained; reconciliation is ordered, max 100 candidates,
   idempotent, statement-timeout bounded, and proves expired-lease reclaim plus
   late-fence rejection after a process restart.
7. API defaults to a Unix socket and scoped bearer credentials read from a
   secure no-follow token file. The public/admin surface is only health,
   submit/show/list/cancel; worker/operator endpoints remain separately scoped.
   No network bind by default and no provider, Git, GitHub, PR, deployment,
   systemd, or repository-execution endpoint.

The plan's test sequence is the most concrete implementation ordering:
`test_contracts` → `test_state` → `test_migrations` → service/intake + real
PostgreSQL intake → lease/capacity/fence → retry/budgets → kill/reconciliation
+ restart probe → API/CLI → M2/M3 architecture integration → one final root
`python3 scripts/grok_verify.py --mode pr` and the route-selected review wave.

## Repository hygiene observations

- Worktree contains unrelated user changes, including `trust-ci/compose.yaml`
  and several untracked historical change directories. Preserve them; do not
  fold them into M4.
- The current active M4 change-package documents are generated stubs and its
  `change-spec.yaml` still contains `{{OBJECTIVE_STATEMENT}}`; they cannot be
  used as frozen M1 authority until completed and validated.
- The root has no `pyproject.toml`, which matches the plan's isolation rule.
  `trust-ci/pyproject.toml` supplies the appropriate nested-package convention
  (pinned FastAPI/Uvicorn/psycopg and packaged SQL resources).

## Implementation recommendation

First obtain the scope-and-design decision for the M3 stacking mismatch. Once
the implementation tree contains the reviewed M2/M3 baseline, use exactly one
write owner to add `factory/` in the plan's task order. Borrow mechanical
migration/API/PostgreSQL-test patterns from `trust-ci/`, but enforce a hard
module/schema/credential boundary: no `adaptive_trust_ci` import and no
`trust_ci.*` query, role, credential, or configuration reuse.
