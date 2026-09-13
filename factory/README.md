# Adaptive Factory M4-M8 control/evaluation and default-off L5 landing runtime

L5 delivery slice D adds bounded HTTP/media normalization and durable runtime composition. HTTP evidence emits v2; native and fixture evidence retains v1, and retained readers accept both. The sealed source is `fde60e040167c10975b00d11f578c4da6763069a` / `21817e70e079b772e1f3114a80dfc0320d1ada91` with 22 publishable files. Rollback after v2 records exist requires a compatible reader or a consistent pre-v2 snapshot.


This nested Python package is a source-only, local control plane. It validates immutable M1/M2/M3/M0-bound intake, stores operational truth in an isolated PostgreSQL `factory` schema, schedules work with database leases and monotonic fences, enforces 20 global readers / 10 readers per repository / one writer, bounds retries and budgets, retains hash-chained audit, and performs restart-safe reconciliation.

It does not make a live provider call, execute repository commands, access Git/GitHub or Trust CI credentials, activate systemd, deploy, publish, or perform an external/production write. `ready_for_human` remains M4's positive terminal state. M5 adds immutable execution packets/manifests, closed provider-neutral protocols and APIs, offline ineligible adapters, trusted proposal/workspace boundaries, atomic terminal finalization, and bounded factual recovery. Shipped execution remains disabled by default.

Current status is bounded by the [root current-state summary](../README.md), [program roadmap](../DARK_FACTORY_ROADMAP.md), and milestone change packages. This M4-M8 source was delivered to `main` by PR #22 and published in `v2.0.13`; the checked head was `b5eba759c309a92f92f4d4003d025795c7f8a1f9` and the merge was `8599d45f4f28285381b05a53feb3059de92eb2a8`. Repository delivery does not authorize deployment, live-provider action, persistent database mutation, M8 activation, or production acceptance.

Published `v2.0.14` introduced the separate L5 store and four authenticated local operations. This branch advances the exact source and current deploy inventory to 22 files while retaining historical 19/20-member layouts. Default-off composition can persist unavailable operation in SQLite; explicitly enabled HTTP composition normalizes, renders, evaluates and seals candidates. The publication port remains unavailable here and every result has `live_url` null. Dedicated host, filesystem publication and backup are subsequent delivery slices.

## Local disposable verification

Use a freshly created disposable PostgreSQL 17 database only. The reconciler uses PostgreSQL 17 `transaction_timeout` together with decreasing statement timeouts to bound one complete page. Never reuse a Trust CI/shared/production URL or inspect an existing `.env`.

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
FACTORY_TEST_DATABASE_URL='postgresql://factory_test:replace@127.0.0.1:5432/factory_test' \
  .venv/bin/python -m unittest tests.test_postgres_integration -v
```

The migration runner uses a factory-only advisory lock and immutable packaged checksums. M4 migrations `001`-`013` remain unchanged. M5 migration `014` adds execution packets, manifests, stages and proposals; `015` adds canonical proposal, attestation and result persistence plus trusted finalization; `016` removes only superseded provisional constraints in the same migrator transaction; and `017` adds PostgreSQL-17 recovery jobs, claims, outcomes and fixed execution metrics. Recovery and migration paths do not fabricate proposals, results, snapshots or attestations. M6 begins at `018`.

The published M4 repair supports only a fresh PostgreSQL 17 database bootstrapped directly through schema `013` for the M4-only rollout boundary. Release publication did not authorize a persistent rollout, so there is no supported deployed schema-`013` upgrade population and this repair does not add a migration. A database created from an older candidate is unsupported as an operational target: preserve or restore it only into a separately named comparison database, keep it killed, and provision a fresh schema-`013` operational database. Readiness fails closed when legacy terminal accounting has unresolved evidence without an explicit quarantine marker. M5 migrations `014` through `017` and M6 migration `018` remain additive; any future persistent-data repair requires a separately reviewed, dependency-coordinated forward migration. Never down-migrate or delete evidence.

## Local API and CLI

The supported composition command is `adaptive-factory-server`. It builds the store, service, authenticator and ASGI application, then pre-binds only an operator-owned Unix socket (default `/run/adaptive-factory/control.sock`) at mode `0660`; there is no TCP option. The socket parent must be owned by the process user and not group/world writable. Actor configuration and every referenced token file require an absolute, owner-pinned, no-follow descriptor walk and a mode-`0600` leaf; see `actors.example.json`. The service login must be a `NOINHERIT` member of `factory_runtime`: every store connection executes `SET ROLE factory_runtime`, while migrations use a separate owner connection.

Before intake, an independently verified M0 observation (or separately approved bootstrap exception) must be provisioned into the matching immutable `factory.m0_*` table by the operator boundary. Caller JSON is only a lookup key and cannot originate authority. The stored `intent_digest` continues to bind the complete normalized request, including `request_id` and the full M0 proof, and remains the opaque task packet digest consumed by later milestones. Deduplication uses a separate `adaptive-factory.work-identity/v1` digest over semantic work fields only; transport `request_id` and the entire M0 proof are excluded so a new request with refreshed equivalent authority returns the existing task. A namespaced intake command key independently makes exact request replay stable and rejects reuse of one request ID with a different full body. Budget reservation and usage observation are authenticated worker endpoints; completion is rejected until accounting is present, settled and unblocked.

All mutations require `Idempotency-Key` and `X-Correlation-ID`; intake records that correlation independently in command/audit evidence without changing full-intent, semantic-work or replay identity. Bodies are at most 1 MiB; list/reconcile pages are at most 100 and execution recovery uses a bounded two-lane page of 2-100. Authenticated `runs` and `events` reads retain the immutable M4 history model. When fully injected into a local composition, `/v1/execution/*` and additive `/v2/execution/*` expose six logical operations each; both terminal routes use the same server-owned proposal, trusted snapshot, and finalization flow. Clients cannot supply trusted snapshots or select unregistered provider profiles.

Runtime-generated OpenAPI, Swagger and ReDoc routes are disabled. [`factory-control.v1.json`](contracts/openapi/factory-control.v1.json) remains the byte-identical 17-operation M4 control contract. M5 execution v1/v2 and the six-operation [`factory-semantic.v1.json`](contracts/openapi/factory-semantic.v1.json) are reviewed separately. Every response carries `X-Correlation-ID`; omitted read correlation is generated, normalized errors retain bounded `error`, `code` and `detail`, and 401 retains `WWW-Authenticate`. Credentials, raw bodies/prompts, reasoning, native streams, unrestricted output and task IDs as metric labels are prohibited.

Configuration names are documented in `.env.example`; it contains placeholders only. For a newly created, explicitly disposable local database, load those names into the shell, start `docker compose up -d postgres`, and run `adaptive-factory-admin bootstrap-local`. That command applies checksum migrations with `FACTORY_MIGRATOR_DATABASE_URL`, creates or validates the bounded `FACTORY_RUNTIME_LOGIN`, grants only `factory_runtime`, and proves `FACTORY_DATABASE_URL` reaches readiness under the effective role; `adaptive-factory-admin migrate` is the migration-only interface. Do not point either command at a shared, external, Trust CI or production database. Source delivery does not run either command or activate a service.

## Readiness, observation and recovery

`/health/ready` checks the isolated `factory_runtime` capability and exact schema version `17`; the artifact attestor uses a separate non-inheriting login and capability. Recovery has bounded connection, lock, statement and transaction timeouts, a 30-second monotonic coordinator budget, exact-handle idempotent cleanup, durable claim fences and work-conserving fresh/retry lanes. Cancel and supersede project cleanup transactionally; stale completion is rejected and replacement M4 work receives a higher fence. Authenticated metrics remain fixed and low-cardinality, with additive execution, terminal, recovery and cleanup families. A disposable PostgreSQL 17 probe has passed two actual restarts and confirmed zero fabricated proposal/result/attestation evidence.

For a separately approved local rollout, follow the [M4 / 2.0.13 local rollout and recovery runbook](../engineering/runbooks/m4-v2.0.13-local-control-plane.md). Provision PostgreSQL 17 and a fresh schema-`013` operational database, preserve the distinct owner and runtime DSNs, and start killed. Check readiness/metrics including capacity/allocation, retry-limit and claimable/positive-endpoint accounting agreement; run synthetic submit/claim/reserve/observe/release/restart/reconcile twice; then clear kill. On any invariant failure, enable global kill, stop the socket process, preserve state/audit/logs, and require a reviewed dependency-coordinated forward repair before reuse.

## Live Grok / Qwen landing executors (default off)

`landing_live_executors.py` owns provider transport; `landing_http.py` defines the closed profiles and bounded response decoder. Profiles are explicit: Beijing `qwen` / `qwen-plus`, Singapore `qwen-intl` / `qwen-plus`, `qwen-omni` / `qwen3.5-omni-plus-2026-03-15`, `grok` / `grok-4`, and `grok-vision` / `grok-4.6`. Region or model failures do not cause automatic fallback. Legacy profiles and qwen-intl accept text/safe DOCX; Omni adds textual PDF, PNG/JPEG and WAV/MP3, while grok-vision adds PDF/images. These are implemented profiles, not a claim that every modality has passed a live provider probe.

PDF text extraction uses packaged `pypdf==6.18.1` in a bounded child process. Scanned, encrypted or oversized inputs remain `needs_human`, without OCR. Requests have an absolute asynchronous timeout and bounded streaming. SSE requires terminal text, final factual usage and DONE; invalid identity/usage, refusal and uncertain outcomes remain explicit failures. Automated executor tests use `httpx.MockTransport`.

The existing `adaptive-factory-server` composes durable unavailable mode when `FACTORY_LANDING_STATE_PATH` and the private runtime paths are set. Explicit `FACTORY_LANDING_LIVE_ENABLED=true`, a named provider and complete state/quarantine/source/scratch/output paths select HTTP execution. The source is validated before credentials, and the SQLite lifetime writer lock precedes quarantine recovery and credential acquisition. Source delivery does not activate the server or call a provider.

`compose_server_landing` accepts an explicit `qwen_env_file` for Qwen profiles. It must remain outside the control repository and runtime/source roots and pass private-file validation. Only `DASHSCOPE_API_KEY` is selected; the file is not executed or imported into the process environment. Explicit file errors fail closed and disabled mode does not read it. Otherwise the selected provider uses its existing environment credential loader. Dedicated host CLI support arrives in E.

The explicit synthetic probe is available when separately invoked with factory dependencies installed:

```bash
PYTHONPATH=factory/src python -m adaptive_factory.landing_live_executors \
  --profile qwen-intl --qwen-env-file "$HOME/.qwen/.env"
```

It sends one fixed synthetic request and prints bounded status, profile/model, digests, usage and elapsed time. It does not start a service or publish a site. This command is documentation; the source extraction and automated tests do not execute it.
