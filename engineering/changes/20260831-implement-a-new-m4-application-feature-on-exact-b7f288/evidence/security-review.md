# M4 round-2 security review — FAIL

## Reviewed identity

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head: `9bc51e81dddb8fc02f22171b586eb8c9caa7f304`
- Full reviewed diff: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9bc51e81dddb8fc02f22171b586eb8c9caa7f304`
- Fix commit: `9bc51e81dddb8fc02f22171b586eb8c9caa7f304` (`01643c6594947535e690c5722f710081c9b9db9f` parent)
- Reviewer: route-selected read-only `security_reviewer`
- Verdict: **FAIL**
- Critical findings: **0**
- Important findings: **1**
- Moderate findings: **1**

The task supplied abbreviation `9bc51e8c`, which does not resolve in this repository. The clean checked-out fix commit is `9bc51e81dddb8fc02f22171b586eb8c9caa7f304`; this report and all executable evidence are bound to that exact SHA.

PASS requires zero Critical/Important findings. This is local review evidence only and cannot substitute for the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact pull-request head.

## Prior-finding closure matrix

| Prior finding | Round-2 result | Evidence |
| --- | --- | --- |
| I-1 caller-forgeable M0 authority | **Closed** | Intake now requires a matching, non-revoked row in a separately provisioned M0 observation/exception table (`factory/src/adaptive_factory/service.py:43-49`, `factory/src/adaptive_factory/store.py:113-128`). Observation names are constrained to `adaptive-trust-ci/verified@<12 hex>` and runtime receives SELECT only (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:1-19,68`). Focused service tests reject unpersisted caller assertions and fabricated bootstrap exceptions. |
| I-2 worker actor/repository boundary | **Closed** | Claim owner is derived from `actor.actor_id`; worker kind, grant owner, and immutable task repository are checked before mutation (`factory/src/adaptive_factory/api.py:213-235`, `factory/src/adaptive_factory/service.py:61-95,97-127`). Store fencing still checks task/run/owner/fence/packet/live state in one locked transaction (`factory/src/adaptive_factory/store.py:601-617`). Cross-owner/cross-repository service regressions pass. |
| I-3 completion accounting | **Closed** | Authenticated reservation and usage endpoints now exist (`factory/src/adaptive_factory/api.py:271-317`). Cost/token/wall reservations are bounded and settled (`factory/src/adaptive_factory/store.py:718-872`); completed release rejects blocked, absent, or unsettled accounting (`factory/src/adaptive_factory/store.py:637-666`). PostgreSQL regressions prove missing/unsettled accounting fails and settled accounting completes. |
| I-4 UDS-only bootstrap/mode | **Closed** | `adaptive-factory-server` is a dedicated composition root (`factory/pyproject.toml:11-13`, `factory/src/adaptive_factory/server.py:102-121`). It pre-binds only `AF_UNIX`, rejects relative paths and unsafe/non-owned parents/existing paths, applies `0660`, passes only the pre-bound socket to Uvicorn, and exposes no host/port/TCP option (`factory/src/adaptive_factory/server.py:73-99,107-121`). Actor/token files are no-follow, regular, private and bounded (`factory/src/adaptive_factory/server.py:22-70`, `factory/src/adaptive_factory/settings.py:13-31`). Focused socket/config tests pass. |
| I-5 effective least-privilege DB roles | **Still Important — open** | Connections do execute `SET ROLE factory_runtime` and immutable audit/intent/event updates are narrowed, but inherited table-level privileges remain exploitable; see I-1 below. |
| M-1 streaming body cap | **Closed** | Middleware validates malformed/negative/declared lengths and cumulatively caps every streamed chunk before parsing (`factory/src/adaptive_factory/api.py:108-126`). Oversized declared and chunked/no-length plus malformed-length tests pass. |
| M-2 correlation/idempotency | **Still Moderate — open** | Kill, release, heartbeat, cancel, reconcile and successful claim now record exact command results/correlation and reject changed replay, but reservation/usage and no-result claims remain incomplete; see M-1 below. |

## Important finding

### I-1 — Effective runtime role can still rewrite security policy and other supposedly narrow state

Migration `003` granted table-level `SELECT, INSERT, UPDATE` on all operational tables to `factory_runtime`, including `intake_identities` and `capacity_counters` (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:48-53`). Migration `005` revokes table-level UPDATE from several immutable tables, then adds column grants, but it never revokes the inherited table-level UPDATE on `capacity_counters` or `intake_identities` (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:58-71`). Therefore the later column-oriented narrowing does not protect the capacity `ceiling` column.

A fresh disposable PostgreSQL 17 database was migrated through version 005, and a connection created by the production `PostgresFactoryStore._connect()` confirmed the effective role and mutated the global reader ceiling:

```text
effective_privileges= ('factory_runtime', True, True, True, True)
runtime_ceiling_mutation= 999
```

The tuple means: current role `factory_runtime`; UPDATE allowed on `capacity_counters.ceiling`; table UPDATE allowed on `intake_identities`; INSERT allowed on `accepted_intents`; INSERT allowed on `kill_switches`. The direct `UPDATE factory.capacity_counters SET ceiling=999 WHERE scope_key='global:reader'` succeeded. Claim trusts the database ceiling (`factory/src/adaptive_factory/store.py:429-458`), so a compromised runtime credential or injection in any future runtime path can bypass the hard 20-reader policy without migrator/operator authority.

The new integration privilege test covers update denial only for `accepted_intents`, `task_events`, and `audit_log` (`factory/tests/test_postgres_integration.py:514-548`), so it misses this live privilege. The app legitimately needs to adjust `active_count`, but not `ceiling`; it also does not need UPDATE on intake identity columns.

Required remediation: revoke the inherited table-level privileges first, then grant only the exact operations/columns used by runtime. At minimum, revoke table UPDATE on `capacity_counters` and grant UPDATE on `active_count` only; revoke UPDATE on `intake_identities`; audit all privileges inherited from migration 003 rather than sampling three tables. Add effective-role negative tests that attempt to change every policy/identity/immutable column, including `capacity_counters.ceiling`, while retaining positive tests for legitimate runtime operations.

## Moderate finding

### M-1 — Correlation and command idempotency remain incomplete on accounting and no-result claims

The API computes and validates the command key and correlation header for budget reservation, but passes only the command key to the service; correlation is dropped (`factory/src/adaptive_factory/api.py:271-293`, `factory/src/adaptive_factory/service.py:97-111`). For usage observation it computes then discards the command key and also drops correlation (`factory/src/adaptive_factory/api.py:295-317`, `factory/src/adaptive_factory/service.py:113-127`). `observe_usage()` deduplicates only by `(run_id, provider_call_id)` (`factory/src/adaptive_factory/store.py:766-872`), so the same `Idempotency-Key` with a changed provider call is accepted as a second mutation rather than rejected as a conflicting replay.

A focused ASGI probe sent one reservation and two different usage bodies under the same idempotency/correlation headers:

```text
statuses= 200 200 200
service_kwargs= [
  ('reserve', {... 'idempotency_key': '<derived>', 'actor': ...}),
  ('usage', {'provider_call_id': 'provider-1', ... 'actor': ...}),
  ('usage', {'provider_call_id': 'provider-2', ... 'actor': ...})
]
```

Neither accounting call received `correlation_id`; usage received neither the command key nor correlation. This can double-observe and consume/block budget when a caller reuses one command identity with changed content, and it prevents correlation of accounting evidence to the authenticated API command.

Claim has a related gap: kill/capacity/no-task returns occur before `_record_command()` (`factory/src/adaptive_factory/store.py:397-458`), so the same idempotency key that first returned no grant can later acquire a lease after state changes. Exact replay is recorded only for a successful claim (`factory/src/adaptive_factory/store.py:500-524`).

Required remediation: route every mutation through the same durable command-result mechanism, including reserve, observe, and every claim result (`grant` or `null`); bind actor/action/request digest/correlation and return the exact recorded result; reject the same key with changed content. Keep `(run_id, provider_call_id)` as an additional provider-level uniqueness constraint, not a replacement for API command idempotency. Add changed-body/same-key, exact replay, correlation persistence, and no-grant-then-state-change regressions.

## Other security observations

- Bearer digests still use constant-time comparison, and raw tokens are loaded from bounded no-follow `0600` files without logging (`factory/src/adaptive_factory/api.py:35-53`, `factory/src/adaptive_factory/settings.py:13-31`).
- Application values are parameterized in SQL. Packaged migrations are contiguous and checksum-bound; no SQL-injection path was found.
- Lease fencing, capacity lock order, `FOR UPDATE SKIP LOCKED`, database deadlines, stale-fence rejection, kill-before-claim and bounded reconciliation remain present. The disposable restart probe demonstrated a higher fence and rejection of the late holder.
- Audit log UPDATE/DELETE remains denied to runtime and its hash chain verifies; command results are INSERT/SELECT only. Correlation is durable for the mutations that actually call `_record_command()`.
- No provider execution, shell/subprocess, repository/Git/GitHub, systemd, deploy, network client, external-write or production-mutation path was found in `factory/src/adaptive_factory`. The only socket family constructed by the server is `AF_UNIX`.
- Readiness proves effective `factory_runtime` and exact schema version 5 (`factory/src/adaptive_factory/store.py:50-65`). Operational deployment must still ensure the login role itself is not owner/superuser and can only `SET ROLE factory_runtime`; tests use a disposable owner login and therefore do not prove that host-level credential design.

## Commands and evidence

```text
git rev-parse HEAD
9bc51e81dddb8fc02f22171b586eb8c9caa7f304

git show -s --format='%H %P %s' HEAD
9bc51e81dddb8fc02f22171b586eb8c9caa7f304 01643c6594947535e690c5722f710081c9b9db9f fix(factory): close durable control-plane review blockers

uv run --project factory python -m unittest -v \
  factory.tests.test_contracts factory.tests.test_service factory.tests.test_api \
  factory.tests.test_server factory.tests.test_migrations factory.tests.test_state
Ran 30 tests — OK

uv run --project factory python factory/tests/run_disposable_exit.py
Ran 40 tests — OK
PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected
PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation

fresh disposable PostgreSQL 17 + PostgresMigrator + PostgresFactoryStore._connect privilege probe
effective_privileges= ('factory_runtime', True, True, True, True)
runtime_ceiling_mutation= 999
The exact probe container `adaptive-factory-security-r2` was removed by its EXIT cleanup.

focused ASGI accounting command probe
same Idempotency-Key with two different provider_call_id bodies: 200, 200
neither usage call received command key/correlation; reservation did not receive correlation

rg -n "subprocess|os.system|shell=True|git |github|provider|systemd|deploy|requests.|httpx.(get|post)|socket.AF_INET" factory/src/adaptive_factory -S
No execution/network/TCP operation matched; only provider-call identifiers and failure enums matched.
```

The full base-to-head `git diff --check` currently reports trailing Markdown hard-break spaces in committed first-round `release-review.md` and `test-review.md`; this is not a security finding, but the final evidence refresh should remove stale first-round review identities.

No `.env`, token contents, database credential store, private key, production dump, Trust CI secret/state, or human approval material was read. This review created and removed only exact disposable local PostgreSQL containers through the checked-in test runner and the focused privilege probe. It performed no shared/production database mutation, external write, push, merge, release or deployment. The only repository write by this reviewer is this requested report; concurrent changes to other evidence reports belong to other review agents and were not altered.

## Required disposition

**FAIL.** Return I-1 to the single route write owner and fix M-1 in the same bounded remediation because it is an explicit incomplete prior finding. Add the effective-role and command-replay regressions described above, rerun disposable verification, then repeat affected independent reviews on the new exact SHA. Do not record a passing `security_review` receipt for `9bc51e81dddb8fc02f22171b586eb8c9caa7f304`.
