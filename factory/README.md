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

The migration runner uses a factory-only advisory lock and immutable packaged checksums. After any durable intake, rollback is global kill + preserved audit + backup restore into a separate database or forward migration `004+`; never down-migrate or delete evidence.

## Local API and CLI

The API is HTTP over an operator-owned Unix socket (default `/run/adaptive-factory/control.sock`, mode `0660`), never a TCP listener. Root/operator-provisioned bearer token files must be regular, no-follow, mode `0600`. The CLI uses only that socket/API and prints bounded canonical JSON.

All mutations require `Idempotency-Key` and `X-Correlation-ID`. Bodies are at most 1 MiB; list/reconcile pages are at most 100. Credentials, raw bodies/prompts, reasoning, native streams, unrestricted output and task IDs as metric labels are prohibited.

Configuration names are documented in `.env.example`; it contains placeholders only. `compose.yaml` creates only an isolated local PostgreSQL example. Source delivery does not activate a service or authorize a migration outside a disposable database.
