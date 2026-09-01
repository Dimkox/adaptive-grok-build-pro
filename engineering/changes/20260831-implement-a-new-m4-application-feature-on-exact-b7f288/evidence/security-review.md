# M4 round-4 security review — PASS

## Reviewed identity

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Full reviewed diff: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Round-4 fix commit: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c` (parent `8435e23458885a48e2d5784f8cd01e84d978c28c`)
- Reviewer: route-selected read-only `security_reviewer`
- Verdict: **PASS**
- Critical findings: **0**
- Important findings: **0**
- Moderate findings: **1**

No Critical or Important security finding remains. The Moderate least-privilege cleanup below is bounded, fail-closed, observable through readiness and does not invalidate this security PASS. This report is local evidence only; it is not merge authority and cannot replace the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact pull-request head.

## Round-3 blocker closure: canonical database-owned capacity

Migration 007 closes the arbitrary-ceiling INSERT bypass with three mutually reinforcing controls:

1. `capacity_counters_canonical_policy` constrains the only legal rows to `global:reader=20`, `global:writer=1`, and `repository:*:reader=10` (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-9`). Even the table owner cannot insert a ceiling of 999.
2. Runtime loses direct INSERT/UPDATE on counters and direct INSERT on allocations (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:160-169`). Fresh effective-role probes returned no INSERT/UPDATE privilege and denied forged statements with SQLSTATE `42501`.
3. Counter creation/allocation/release is performed by four `SECURITY DEFINER` functions with `SET search_path=pg_catalog,factory`, schema-qualified relations, closed role/repository/live-run checks, stable ordered locks and canonical ceilings (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:11-158`). PUBLIC execute is revoked and only `factory_runtime` receives execute.

The store now calls only those functions for capacity eligibility, allocation, lock and release (`factory/src/adaptive_factory/store.py:440-494,524-575,625-655`). Readiness additionally compares counters with live allocations and fails closed on drift (`factory/src/adaptive_factory/store.py:61-85`). The supported PostgreSQL suite proves 20 global readers, 10 per repository, one writer, reader 21 rejected, and lifecycle release returning readiness to consistent.

Fresh round-4 evidence:

```text
effective_dml= ('factory_runtime', False, False, False, True, False)
```

Tuple: effective role; counter INSERT denied; counter UPDATE denied; allocation INSERT denied; allocation `released_at` UPDATE still allowed (Moderate M-1); PUBLIC counter INSERT denied.

```text
function_security= ('capacity_allocate', True, ['search_path=pg_catalog, factory'], True, False)
function_security= ('capacity_eligible_repositories', True, ['search_path=pg_catalog, factory'], True, False)
function_security= ('capacity_lock_run', True, ['search_path=pg_catalog, factory'], True, False)
function_security= ('capacity_release', True, ['search_path=pg_catalog, factory'], True, False)
```

For each function: `SECURITY DEFINER=true`; fixed search path; runtime execute=true; PUBLIC execute=false.

```text
forged_dml_denied= 42501 INSERT capacity_counters(... ceiling=999)
forged_dml_denied= 42501 UPDATE capacity_counters SET active_count=0
forged_dml_denied= 42501 INSERT capacity_allocations(...)
canonical_constraint_denied_owner= 23514
```

The prior reader-11 attack no longer has a runtime DML path, and the canonical constraint independently rejects the forged row under owner authority.

## All prior security findings rechecked

| Area | Round-4 result | Evidence |
| --- | --- | --- |
| M0 authority | **Closed** | Intake requires a matching non-revoked, independently provisioned M0 observation/exception; caller assertions alone fail (`factory/src/adaptive_factory/service.py:43-49`, `factory/src/adaptive_factory/store.py:134-149`). Runtime has SELECT only on those authority tables. |
| Worker actor/repository auth | **Closed** | Claim owner derives from authenticated actor. Worker kind, scope, grant owner and immutable task repository are checked before heartbeat/release/accounting, while the store rechecks owner/run/fence/packet/live state under locks. Cross-owner/repository regressions pass. |
| Completion accounting/budgets | **Closed** | Authenticated reservation/usage endpoints enforce cost/token/wall/output ceilings, missing pricing blocks, reservations settle, completion requires usage and no open reservation/block, and exact command replay precedes stale-fence checks. |
| Claim-null replay | **Closed** | Every no-grant result is durably recorded with actor/action/request digest/correlation. Exact replay remains null after work arrives and changed content conflicts. |
| Accounting idempotency/correlation | **Closed** | Reserve/observe carry command key and correlation through API/service/store, serialize the key with an advisory transaction lock, replay exact results/errors and reject changed content. Durable correlations are asserted in PostgreSQL tests. |
| UDS-only server and secrets | **Closed** | The composition root pre-binds only `AF_UNIX`, validates absolute owned safe paths, applies `0660`, and exposes no TCP setting. Actor/token files are bounded no-follow regular `0600`; bearer hashes compare constant-time; access logging is disabled. |
| Streaming body cap | **Closed** | Declared length is validated and streamed chunks are cumulatively capped at 1 MiB before parsing. Declared, chunked/no-length and malformed-length regressions pass. |
| SQL/injection/search path | **Closed** | Application values are parameterized. Definer functions use fixed `pg_catalog,factory`, schema-qualified relations and closed typed inputs; PUBLIC execute is revoked. No SQL injection or search-path substitution path was found. |
| Lease fencing/kill/audit | **Closed** | Database time, monotonic fences, owner/run/packet/current-state/deadline checks, kill-before-claim, ordered locks and bounded reconciliation remain. Audit log is insert/select-only for runtime, hash-chain verification passes, and command results are immutable replay evidence. |
| Unsafe/external operations | **Closed** | No provider execution, subprocess/shell, repository/Git/GitHub, systemd, deploy, TCP client/listener, connector, production mutation or Trust CI authority path exists under `factory/src/adaptive_factory`. |

## Moderate finding

### M-1 — Obsolete direct allocation-release UPDATE grant remains

Migration 005 granted runtime UPDATE on `capacity_allocations.released_at` (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:67`). Migration 007 revokes direct allocation INSERT but does not revoke that column UPDATE (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:164-169`). The fresh effective-role probe confirms `has_column_privilege(... released_at, UPDATE)=true`.

The store no longer uses that direct grant; all legitimate allocation release goes through `factory.capacity_release(uuid)`. A compromised runtime credential could mark an allocation released without decrementing counters. This does not permit over-capacity execution: counters remain conservatively high, readiness compares them to live allocations and becomes `not_ready`, and subsequent claims fail closed. Impact is bounded availability/evidence inconsistency, not authorization or cap bypass.

Recommended forward cleanup: revoke UPDATE on `factory.capacity_allocations` from `factory_runtime` in migration 008 and add an effective-role denial regression, while retaining positive release/reconciliation tests through `capacity_release`.

## Verification evidence

```text
git rev-parse HEAD
9fd2a56c57f834ad39c03a2f748bdbaefc79c91c

git show -s --format='%H %P %s' HEAD
9fd2a56c57f834ad39c03a2f748bdbaefc79c91c 8435e23458885a48e2d5784f8cd01e84d978c28c fix(factory): make capacity authority database-owned

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

fresh PostgreSQL 17 privilege/function/forged-DML probe
direct counter INSERT/UPDATE and allocation INSERT denied
owner-level noncanonical ceiling rejected by CHECK
all four functions SECURITY DEFINER, fixed search_path, runtime-only execute
```

The parent reports a fresh root `python3 scripts/grok_verify.py --mode pr` PASS on this exact head. The focused independent probes above cover the former security gap beyond the broad verifier.

The exact reviewer-created container `adaptive-factory-security-r4` and the checked-in exit runner's unique container were removed. No `.env`, token content, private key, credential store, production dump, Trust CI secret/state, or human approval material was read. No shared/production database, external system, push, merge, release or deployment was mutated. The only repository write by this reviewer is this requested report.

## Verdict

**PASS** for local `security_review` on exact head `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`. The Moderate M-1 cleanup is recommended but does not block this source-only local M4 change. Record the receipt only while the tree fingerprint remains current; any repository change invalidates this report and requires affected verification/review again.
