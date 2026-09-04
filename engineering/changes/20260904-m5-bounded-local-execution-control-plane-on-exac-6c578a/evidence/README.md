# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

## Scope/design inputs

- `analysis-repo_explorer.md` — exact lineage and semantic-port inventory.
- `analysis-task_analyst.md` — finite acceptance and approval boundary.
- `analysis-architect.md` — architecture, conflicts and recovery model.
- `analysis-docs_researcher.md` — factual documentation/state closure.
- `analysis-data_architect.md` — migrations, roles, persistence and PostgreSQL evidence.
- `analysis-ai_architect.md` — offline provider and untrusted-output boundary.
- `analysis-integration_architect.md` — additive M4/M5 API, service, store and server integration.

All reports are design inputs for route `6c578a9933b3`; they are not verification or review receipts. Canonical M5 reference `3940267` supplies source semantics only. Current evidence must be generated from the final descendant of exact predecessor `67dc4dd` and may use disposable local PostgreSQL 17 only.

## Gate evidence

The scoped/approved state transitions record the user's explicit authorization for repository-local source, authoring unpublished additive migrations `014`-`017`, and disposable local PostgreSQL. They do not authorize shared/persistent database mutation or any network, provider, service, delivery, external, or production action.

## Provisional source checkpoint

The repository-local implementation is carried by source commits `edc01c5`, `3c9b36f`, `e5a20a7`, and `c5fdbe8`, all descending from exact M4 predecessor `67dc4dd`. It preserves `factory-control.v1.json` and migrations `001`-`013`, adds the closed execution v1/v2 contract family and migrations `014`-`017`, keeps execution disabled in shipped settings, and contains no live provider, credential, network, systemd activation, delivery, or production path.

Focused evidence executed during implementation:

- 42 contract/protocol/adapter/broker tests, 23 execution-service tests, 11 workspace tests, and 14 recovery tests passed.
- 43 API/server checks passed, including disabled startup and the twelve execution route-method pairs; the one M4-compatible route-inspection adjustment was rerun alone.
- Five focused migration checks, 12 migration/harness preflight checks, 36 retained M4 model/contract/state/service checks, architecture validation, and generated-diagram parity passed.
- The first disposable PostgreSQL integration run exposed 21 failure/error instances in 16 methods: canonical M5 fixtures reused an M4 transport request identifier, test-only fault injectors used the owner DSN after least-privilege enforcement, and failure release did not quarantine residual task accounting. Those three roots were repaired without weakening runtime capability checks.
- Only those 16 methods were rerun; all 16 passed. A subsequent actual two-restart PostgreSQL 17 probe passed exact runtime/attestor role isolation, cancelled and orphaned recovery, ambiguous-cleanup fence-2 replay, absence of fabricated proposal/result/attestation evidence, and a higher replacement M4 fence.

These are implementation-phase facts, not final receipts. Exact-head PR verification and the route-selected independent review wave remain required after tracked finalization.
