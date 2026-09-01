# M4 round-3 security review — FAIL

## Reviewed identity

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head: `8435e23458885a48e2d5784f8cd01e84d978c28c`
- Full reviewed diff: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c`
- Round-3 fix commit: `8435e23458885a48e2d5784f8cd01e84d978c28c` (parent `9bc51e81dddb8fc02f22171b586eb8c9caa7f304`)
- Reviewer: route-selected read-only `security_reviewer`
- Verdict: **FAIL**
- Critical findings: **0**
- Important findings: **1**
- Moderate findings: **0**

PASS requires zero Critical/Important findings. This local report is not merge authority and cannot replace the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact pull-request head.

## Prior-finding recheck

| Area | Round-3 result | Evidence |
| --- | --- | --- |
| M0 authority | **Closed** | Intake requires a matching non-revoked, independently provisioned observation/exception (`factory/src/adaptive_factory/service.py:43-49`, `factory/src/adaptive_factory/store.py:114-129`). Runtime has SELECT only on the trusted M0 tables; caller assertions alone still fail. |
| Worker actor/repository authorization | **Closed** | Claim derives owner from authenticated actor; worker kind, grant owner, scope and immutable task repository are checked before heartbeat/release/accounting (`factory/src/adaptive_factory/api.py:213-235`, `factory/src/adaptive_factory/service.py:61-132`). Store fencing locks task/run/allocation and checks owner/fence/packet/live lease/deadline. Cross-owner/repository regressions pass. |
| Completion accounting | **Closed** | Reservation/usage endpoints are authenticated; cost/token/wall/output bounds and settlement are durable; completion requires usage, no open reservation and no accounting block. Exact accounting replay succeeds before stale-fence checking and changed command content conflicts. |
| UDS-only bootstrap, mode and token permissions | **Closed** | The only server composition pre-binds `AF_UNIX`, validates an absolute owned safe parent/existing path, applies `0660`, and passes only that socket to Uvicorn (`factory/src/adaptive_factory/server.py:73-121`). Actor/token files are bounded, no-follow regular `0600` files. No TCP option/listener exists. |
| Streaming body cap | **Closed** | Middleware validates declared length and cumulatively caps all streamed chunks at 1 MiB before parsing (`factory/src/adaptive_factory/api.py:108-126`). Declared, chunked/no-length and malformed-length tests pass. |
| Claim-null replay | **Closed** | Every no-grant branch records `{"grant": null}` under the actor/action/request digest/correlation; exact replay remains null after work arrives and changed content conflicts (`factory/src/adaptive_factory/store.py:398-480`, `factory/tests/test_postgres_integration.py:275-298`). |
| Accounting idempotency/correlation | **Closed** | API/service now carry command key and correlation for reserve/observe (`factory/src/adaptive_factory/api.py:271-320`, `factory/src/adaptive_factory/service.py:97-132`). Store serializes keys with an advisory transaction lock, persists exact results/errors, replays before stale-fence validation and rejects changed content (`factory/src/adaptive_factory/store.py:89-103,728-927`). PostgreSQL regressions confirm both correlations. |
| Runtime UPDATE denial for capacity ceiling/intake identities | **Closed as written, but policy still bypassable through INSERT** | Migration 006 revokes table UPDATE and grants `active_count` only (`factory/src/adaptive_factory/resources/006_runtime_policy_privileges.sql:1-2`). Fresh effective-role probes denied both requested UPDATE statements. The remaining INSERT route is the Important finding below. |

## Important finding

### I-1 — Runtime can pre-seed an arbitrary repository capacity ceiling and bypass the hard limit

Migration 006 correctly removes UPDATE on `capacity_counters.ceiling` and `intake_identities`, but migration 003's table-level INSERT on `capacity_counters` remains (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:48-53`, `factory/src/adaptive_factory/resources/006_runtime_policy_privileges.sql:1-2`). Runtime legitimately needs to create dynamic repository counters, yet the schema only requires `ceiling > 0`; it does not constrain a `repository:*:reader` row to ceiling 10 (`factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql:38-43`). Claim inserts 10 only when the row is absent, then trusts the persisted ceiling (`factory/src/adaptive_factory/store.py:424-463`).

A fresh PostgreSQL 17 database migrated through version 006 produced:

```text
effective_privileges= ('factory_runtime', False, True, False, True)
denied= UPDATE factory.capacity_counters SET ceiling=999 WHERE scope_key='global:reader'
denied= UPDATE factory.intake_identities SET source_id='tampered'
inserted_repository_ceiling= 999
```

The tuple is: effective role `factory_runtime`; capacity-ceiling UPDATE denied; active-count UPDATE allowed; intake-identity UPDATE denied; capacity-counter INSERT allowed. The same effective role successfully inserted `repository:probe/repo:reader` with ceiling `999`.

This is not merely theoretical privilege metadata. A second clean migrated database pre-seeded that row, submitted 11 ordinary tasks through `FactoryService`, then claimed them through the supported scheduler:

```text
reader_grants_for_one_repository= 11
```

The documented/database-authoritative maximum is 10 readers per repository. A compromised runtime credential, future SQL injection, or unintended runtime statement can therefore modify security policy without UPDATE/migrator authority and make the supported claim path violate AC-005. The new privilege regression checks UPDATE denial and a positive `active_count` update, but does not attempt an arbitrary INSERT (`factory/tests/test_postgres_integration.py:608-654`).

Required remediation: make ceilings schema-authoritative, not caller-supplied runtime data. For example, add a constraint/trigger that permits exactly `global:reader=20`, `global:writer=1`, and `repository:*:reader=10`, or move repository-counter creation behind a narrowly defined security-definer function while revoking direct INSERT. Add an effective-role regression that arbitrary repository ceiling INSERT fails and an end-to-end test proving a preexisting/malformed counter cannot yield reader 11. Audit all other policy-bearing columns for the same insert-vs-update privilege gap.

## Positive security evidence

- Bearer hashes use constant-time comparison. Actor configuration and token files are closed, bounded and no-follow/private; credentials are not logged.
- All application SQL values are parameterized. Migrations are contiguous, packaged and checksum-bound. No SQL-injection path was found in the current API/store.
- Monotonic task fences, live owner/run/packet/state/deadline checks, stable capacity lock order, `FOR UPDATE SKIP LOCKED`, bounded retries, kill-before-claim and bounded reconciliation remain intact.
- Audit log remains insert/select-only for runtime and hash-chain verification passes. Command results are insert/select-only and serialize duplicate command keys.
- No provider execution, subprocess/shell, repository/Git/GitHub, systemd, deploy, TCP/network-client, external-write or production-mutation path was found under `factory/src/adaptive_factory`.
- Readiness checks effective `factory_runtime` and exact schema version 6. Deployment must additionally ensure the login role is not owner/superuser; disposable tests intentionally use an owner login that can `SET ROLE`.

## Commands and evidence

```text
git rev-parse HEAD
8435e23458885a48e2d5784f8cd01e84d978c28c

git show -s --format='%H %P %s' HEAD
8435e23458885a48e2d5784f8cd01e84d978c28c 9bc51e81dddb8fc02f22171b586eb8c9caa7f304 fix(factory): complete durable command and role invariants

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..HEAD
PASS (no output)

uv run --project factory python -m unittest -v \
  factory.tests.test_contracts factory.tests.test_service factory.tests.test_api \
  factory.tests.test_server factory.tests.test_migrations factory.tests.test_state
Ran 30 tests — OK

uv run --project factory python factory/tests/run_disposable_exit.py
Ran 42 tests — OK
PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected
PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation

fresh PostgreSQL 17 effective-role privilege probe
effective_privileges= ('factory_runtime', False, True, False, True)
requested UPDATE denials passed; arbitrary repository ceiling INSERT returned 999

fresh PostgreSQL 17 end-to-end supported scheduler probe
reader_grants_for_one_repository= 11
```

The parent reports a fresh root `python3 scripts/grok_verify.py --mode pr` PASS for this exact head. That broad verifier result does not exercise the arbitrary counter INSERT/reader-11 abuse case and therefore does not negate I-1.

Both exact reviewer-created containers, `adaptive-factory-security-r3` and `adaptive-factory-security-r3-claims`, were removed by EXIT cleanup; the checked-in exit runner also removed its unique container. No `.env`, token content, private key, credential store, production dump, Trust CI secret/state, or human approval material was read. No shared/production database, external system, push, merge, release or deployment was mutated. The only repository write by this reviewer is this requested report.

## Required disposition

**FAIL.** Return I-1 to the single route write owner, add the schema/effective-role/end-to-end regressions, rerun exact-tree verification, and repeat affected independent reviews. Do not record a passing `security_review` receipt for `8435e23458885a48e2d5784f8cd01e84d978c28c`.
