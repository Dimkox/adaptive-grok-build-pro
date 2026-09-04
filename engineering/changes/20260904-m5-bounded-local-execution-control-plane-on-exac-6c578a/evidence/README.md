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
