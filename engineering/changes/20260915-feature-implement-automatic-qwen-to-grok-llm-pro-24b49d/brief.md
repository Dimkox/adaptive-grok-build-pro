# Automatic five-provider failover

## Accepted outcome

Qwen remains primary. A common operator submission command advances through **Qwen → Grok → OpenAI → Anthropic Claude → OpenRouter** after a confirmed eligible failure. Success stops the chain. Each backend receives at most one dispatch per logical request; ambiguous submissions are reconciled without blind retry.

The user approved the presented common-CLI design with “Исправляй”, then explicitly required the other APIs and rereading `.env`. On 2026-09-15 a bounded parser confirmed nonempty `FACTORY_LANDING_QWEN_API_KEY`, `FACTORY_LANDING_GROK_API_KEY`, `FACTORY_LANDING_OPENAI_API_KEY`, `FACTORY_LANDING_ANTHROPIC_API_KEY`, and `FACTORY_LANDING_OPENROUTER_API_KEY`. Only names/presence were emitted. No model or endpoint settings were present. That presence inspection made no network request; later authenticated metadata-only probes are recorded in `evidence/provider-readiness.json`, with inference still unverified. This resolves the named scope/design gate; routine model and implementation choices are delegated.

## Verified baseline

- Source base `7b147366a1f9b7e4b59f17e10283cc8ad67ba0c8`; release v2.0.16.
- Qwen `adaptive-l5.service` at `5f6f6ce` and Grok `adaptive-l5-grok.service` at `61a05da` are active/enabled. Separate successful Unix-socket smokes have `live_url=null` and prove no automatic connection between them.
- Each host binds one profile to provider/artifact evidence. Current status omits failure/accounting facts needed for safe routing. Model execution precedes HTTP 202; a lost response is ambiguous.
- Provider errors currently collapse to an unusable-outcome reason (#87).

## Scope

Implement all five adapters, private per-profile host configuration, versioned durable attempt observations, common CLI/private SQLite recovery journal, regression tests and operator guide. Support text/safe DOCX. Reuse existing Unix hosts and standard-library SQLite; no extra daemon, database service, queue or SDK.

General repository coding, external accepted pilot, international Omni (#86), M8, general M9 and public publication remain separate. Direct backend calls retain single-provider behavior. Source support and installed/live qualification must be reported separately.

Route `24b49d0529c8` retains sole writer `ai_implementer`, five analysis and four review roles. Its generated task title predates the added APIs; this accepted package is the complete scope. The existing high-risk AI/API/security route covers this extension without router-policy changes.
