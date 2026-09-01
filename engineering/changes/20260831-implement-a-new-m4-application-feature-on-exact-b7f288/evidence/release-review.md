# Release review — M4 durable factory control plane

## Decision

**FAIL — NO-GO for local source release.**

Route: `b7f288f1e81e`
Reviewed base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
Reviewed head: `01643c6594947535e690c5722f710081c9b9db9f`
Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f`

The repository was at the reviewed head when inspected. The committed README/current-state/stack graph and installer inventory are coherent, and no provider, GitHub, deployment, production, or Trust CI write path was found in the factory product. The exact tree is nevertheless not locally release-ready: the runtime cannot be started through a supported Unix-socket composition path, terminal/supersession paths can leak capacity and defeat reconciliation, least-privilege roles are not operationally wired, required observability is absent, the P0 database/API evidence is outside the fingerprint-bound verifier, and the rollback version is stale.

Per the review contract, every Important finding below is release-blocking. Do not record a passing `release_review` receipt for this head.

## Findings

### Important — I-1: the shipped package has no runnable Unix-socket API composition root

`factory/pyproject.toml:11-12` installs only the client CLI. `factory/src/adaptive_factory/api.py:81-82` exposes a transport-agnostic `create_app(service, authenticator)` factory, while `factory/src/adaptive_factory/settings.py:41-47` only parses three settings; no product code constructs the migrator/store/service/authenticator, starts Uvicorn with a Unix socket, validates the socket parent, handles a stale socket, or enforces the documented `0660` mode. The checked-in `.env.example:2-6` does not even define the required `FACTORY_DATABASE_URL`, and it contains no token-to-actor/scope/repository mapping from which `Authenticator` can be built.

This contradicts the runnable authenticated Unix-socket API boundary required by `change-spec.yaml:5`, `architecture.md:23-25`, and the rollout step in `release.md:5`. It also means the “never a TCP listener” promise in `factory/README.md:22` is not enforced by the server product; it is true only of the CLI client transport. Add a supported, tested composition/start command that binds only an operator-owned UDS with fail-closed permissions and explicit actor/scope configuration.

### Important — I-2: supersession and cancellation can leak live capacity and make reconciliation fail

When changed intake supersedes an active leased task, `factory/src/adaptive_factory/store.py:157-179` clears `current_run_id` and `current_fence` but does not close the run/allocation or decrement global/repository capacity. Cancellation similarly changes only the task projection at `factory/src/adaptive_factory/store.py:689-700`. The reconciler later selects the still-open expired run at `factory/src/adaptive_factory/store.py:658-677`, but `_release_locked` delegates to the current-grant guard, which requires the task still to be leased and still reference that run (`factory/src/adaptive_factory/store.py:424-439`). It therefore raises instead of repairing the leak.

This breaks the 20/10/1 capacity invariant and the release/rollback claims that kill/reconciliation can restore zero leaked allocations. Close active runs and allocations atomically on supersede/cancel, or make reconciliation explicitly and idempotently repair terminal-projection orphan runs; cover both reader and writer cases and repeated repair.

### Important — I-3: declared PostgreSQL role separation is metadata, not the executable runtime boundary

Migration `001` creates three `NOLOGIN` roles (`factory/src/adaptive_factory/resources/001_initial.sql:1-5`) and migration `003` grants them privileges (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:48-58`). However, the migrator and every store operation accept the same arbitrary database URL (`factory/src/adaptive_factory/migrations.py:67-72`, `factory/src/adaptive_factory/store.py:44-53`), and no product bootstrap assumes `factory_migrator`, `factory_runtime`, or `factory_audit_reader`. The PostgreSQL test likewise migrates and exercises the store with the database-owner URL, then only queries privilege metadata (`factory/tests/test_postgres_integration.py:27-42,266-287`).

`release.md:7` names role separation as a go gate, and `requirements.md:26` requires separate least-privilege roles. The current artifact provides no reproducible way to meet that gate and does not prove representative runtime/audit operations under those roles. Define the operator provisioning/`SET ROLE` or credential model, use separate migrator/runtime connections, and test allowed and denied operations under the effective roles.

### Important — I-4: required release observability and readiness are not implemented

The typed change spec requires three metric families (`change-spec.yaml:23-26`), and `release.md:7` requires bounded visibility for intake, queue, transitions, leases, capacity, budgets, retry/dead, kills, reconciliation, and authentication failures. There is no metrics/telemetry/logging implementation in `factory/src`; `/health/ready` returns a constant ready response without checking database connectivity, migration status, or operational state (`factory/src/adaptive_factory/api.py:111-117`). No dashboard, alert, support owner, or concrete observation command is supplied.

Consequently an operator cannot execute the stated go/no-go observation gate or distinguish a live but unusable API from a ready control plane. Implement the specified low-cardinality/redacted signals, dependency-aware readiness, and an owned observation/runbook path before rollout.

### Important — I-5: the exact-head verification receipt omits the high-risk API/PostgreSQL/restart exit suite

The existing exact-head receipt records a passing tree fingerprint `6831959f1205504b2c10f019a03a95d6143c01c3dc41a0de4cf90df81b7887f5`, but its factory check ran only 19 dependency-free contract/state/migration/service tests. The verifier explicitly selects only those four modules (`.grok-stack/adaptive_grok/verification.py:574-587`); it excludes `test_api.py`, `test_postgres_integration.py`, and `postgres_restart_probe.py`. The implementation report records a prior disposable PostgreSQL run, but that prose is not a fingerprint-bound mandatory check.

This does not satisfy `requirements.md:18`, `test-plan.md:5-13`, or `release.md:3,7`, all of which require the real PostgreSQL/API/restart evidence and reviews on the final fingerprint. Make a disposable PostgreSQL/API/restart profile mandatory for this high-risk route, fail rather than skip when it is unavailable, and bind its result to the same final tree before reviews are recorded. The currently present independent test and security reports also return FAIL, so the five-review gate is independently unmet.

### Important — I-6: rollback documentation names the already-applied migration as a future recovery

The packaged schema is already at migration `004` (`factory/src/adaptive_factory/resources/004_event_and_repair_budgets.sql:1-3`), yet `rollback.md:5`, `factory/README.md:18`, and `architecture.md:31` instruct the operator to forward-fix with `004+`. The implementation report correctly says `005+` at `evidence/implementation-report.md:44`, leaving the authoritative operational documents inconsistent. The release/rollback plans also provide no concrete backup verification, restore validation, ownership, or smoke command sequence.

Using the current migration number as a supposed forward repair is ambiguous and cannot recover an already-migrated database. Update all recovery docs to the next migration (`005+` for this head), and add a bounded, testable backup/restore/smoke procedure with named go/no-go ownership.

## Positive release evidence

- README identity is `2.0.12` and its current-state section accurately calls M4 a pending local source candidate (`README.md:1,5-16`).
- The K17 inventory graph declares 136 pairwise edges including Factory, and `tests.test_structure.StructureTests.test_readme_stack_graph_is_complete` passed (`README.md:91-263`).
- Installer inventory includes the full factory source/contracts/config and migration `004`, while excluding factory tests, credentials, sockets, and database/runtime state (`scripts/install_into.py:17-30`; focused inventory check passed). Installer and structure focused tests passed.
- Migration discovery is contiguous and checksum-locked under a factory advisory transaction (`factory/src/adaptive_factory/migrations.py:33-64,84-108`); destructive down-migrations are absent.
- Static search of the exact head found no subprocess/shell/provider/GitHub/deployment/production/Trust CI write path in `factory/src` or its API contract. The only HTTP client is the CLI's explicit UDS transport (`factory/src/adaptive_factory/cli.py:65-66`). The sample PostgreSQL port is loopback-only (`factory/compose.yaml:8-9`) and source delivery does not start it.
- The architecture model/rules contain the Factory boundary and prohibit Factory-to-Trust-CI/external/production edges (`architecture/rules.yaml:113-134,190-219`).

These positives support the no-external-write claim for source delivery, but they do not cure the release-blocking runtime, recovery, observability, and evidence gaps.

## Commands and evidence

```text
git rev-parse HEAD
  01643c6594947535e690c5722f710081c9b9db9f

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f
  PASS (no output)

python3 -m unittest factory.tests.test_contracts factory.tests.test_state \
  factory.tests.test_migrations factory.tests.test_service \
  factory.tests.test_api tests.test_installer tests.test_structure -v
  51 tests passed; API module import ERROR because FastAPI is not installed in the reviewer base environment.
  This is not represented as passing API evidence.

python3 scripts/grok_status.py
  Route b7f288f1e81e at status verifying; verification reported stale after repository evidence changes;
  code/test/security/data/release review receipts were not complete.

git grep -n -E 'uvicorn|create_app\(|FactorySettings|PostgresMigrator|factory_(intake|lease|capacity).*_total|prometheus|metrics' 01643c6 -- factory ':!factory/tests'
  Only the Uvicorn dependency declaration, uncomposed create_app, settings class, and migrator class matched;
  no server composition or required metric implementation matched.

git grep -n -E 'subprocess|Popen|os\.system|requests|urllib|aiohttp|https://|github\.com|api\.github' 01643c6 -- factory/src factory/contracts
  No product external-execution/write match.

installer build_payload exact inventory check
  factory/src/adaptive_factory/resources/004_event_and_repair_budgets.sql: included
  factory/tests/test_postgres_integration.py: excluded
  factory/tests/test_api.py: excluded
```

## Required release-gate reset

Return I-1 through I-6 to the single route write owner. After product/document changes, rerun the mandatory real PostgreSQL + API + restart cohort and `python3 scripts/grok_verify.py --mode pr` on the new final fingerprint, then rerun all five independent reviews. PR delivery, the App-owned exact-SHA Trust CI check, signed approval scopes, merge, tagging, publication, and activation remain separately controlled and were not performed by this review.
