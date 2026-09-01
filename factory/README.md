# Adaptive Factory M4 local control plane

This nested Python package is a source-only, local control plane. It validates immutable M1/M2/M3/M0-bound intake, stores operational truth in an isolated PostgreSQL `factory` schema, schedules work with database leases and monotonic fences, enforces 20 global readers / 10 readers per repository / one writer, bounds retries and budgets, retains hash-chained audit, and performs restart-safe reconciliation.

It does not execute providers, shell or repository commands; access Git/GitHub, Trust CI state or credentials; install systemd; deploy; publish; or perform any external/production write. `ready_for_human` is its positive terminal state. M5+ capabilities remain absent.

## Local disposable verification

Use a freshly created disposable PostgreSQL 15+ database only. Never reuse a Trust CI/shared/production URL or inspect an existing `.env`.

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
FACTORY_TEST_DATABASE_URL='postgresql://factory_test:replace@127.0.0.1:5432/factory_test' \
  .venv/bin/python -m unittest tests.test_postgres_integration -v
```

The migration runner uses a factory-only advisory lock and immutable packaged checksums. Migration `005` adds trusted M0, command replay and accounting controls; migration `006` removes runtime policy/identity updates; migration `007` makes 20/10/1 capacity canonical and exposes only capability-shaped allocation/release functions; migration `008` removes runtime authority to hide or restore allocations; migration `009` binds M0 subjects and audit-v2 evidence and adds task-history indexes; migration `010` serializes authority revocation, quarantines legacy unresolved accounting and separates mandatory cleanup facts from the ordinary event budget. After durable intake, rollback is global kill + preserved audit + backup restore into a separate comparison database or forward migration `011+`; never down-migrate or delete evidence.

## Local API and CLI

The supported composition command is `adaptive-factory-server`. It builds the store, service, authenticator and ASGI application, then pre-binds only an operator-owned Unix socket (default `/run/adaptive-factory/control.sock`) at mode `0660`; there is no TCP option. The socket parent must be owned by the process user and not group/world writable. Actor configuration and every referenced token file require an absolute, owner-pinned, no-follow descriptor walk and a mode-`0600` leaf; see `actors.example.json`. The service login must be a `NOINHERIT` member of `factory_runtime`: every store connection executes `SET ROLE factory_runtime`, while migrations use a separate owner connection.

Before intake, an independently verified M0 observation (or separately approved bootstrap exception) must be provisioned into the matching immutable `factory.m0_*` table by the operator boundary. Caller JSON is only a lookup key and cannot originate authority. Budget reservation and usage observation are authenticated worker endpoints; completion is rejected until accounting is present, settled and unblocked.

All mutations require `Idempotency-Key` and `X-Correlation-ID`. Bodies are at most 1 MiB; list/reconcile pages are at most 100. Credentials, raw bodies/prompts, reasoning, native streams, unrestricted output and task IDs as metric labels are prohibited.

Configuration names are documented in `.env.example`; it contains placeholders only. For a newly created, explicitly disposable local database, load those names into the shell, start `docker compose up -d postgres`, and run `adaptive-factory-admin bootstrap-local`. That command applies checksum migrations with `FACTORY_MIGRATOR_DATABASE_URL`, creates or validates the bounded `FACTORY_RUNTIME_LOGIN`, grants only `factory_runtime`, and proves `FACTORY_DATABASE_URL` reaches readiness under the effective role; `adaptive-factory-admin migrate` is the migration-only interface. Do not point either command at a shared, external, Trust CI or production database. Source delivery does not run either command or activate a service.

## Readiness, observation and recovery

`/health/ready` checks the effective `factory_runtime` role and exact schema version. Authenticated `/metrics` returns only the three declared low-cardinality JSON families; it never labels task IDs or emits bodies, tokens or reasoning. `python3 scripts/grok_verify.py --mode pr` creates a disposable PostgreSQL 17 container, executes API/database/effective-role tests, performs an actual database restart, reconciles twice, and removes that exact container.

For a separately approved local rollout: preserve the distinct owner and runtime DSNs, start killed, verify a logical backup by restoring it into a distinct comparison database, run the admin bootstrap/migration interface through exact schema `010`, then start `adaptive-factory-server` only with the runtime DSN. Check readiness/metrics including capacity/allocation and claimable-accounting agreement; run synthetic submit/claim/reserve/observe/release/restart/reconcile twice; then clear kill. On any invariant failure, enable global kill, stop the socket process, preserve state/audit/logs, and forward-fix with migration `011+`.
