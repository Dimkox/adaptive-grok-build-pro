# Approved architecture

## Composition

`adaptive-landing-submit` coordinates up to five independent Unix hosts in the order Qwen, Grok, OpenAI, Anthropic Claude, OpenRouter. It runs independently of Qwen and therefore covers primary-process absence before submission. Each host keeps its provider key and artifact builder; the CLI receives scoped service credentials. Direct socket calls remain supported.

A private SQLite caller journal and bounded private input spool provide crash/replay recovery across hosts. Reuse standard-library SQLite and the existing host entrypoint. A wrapper inside Qwen cannot cover primary-process absence; a permanent router would add unnecessary lifecycle scope.

Preserve `qwen-intl/qwen-plus` and `grok-vision/grok-4.6`. New defaults: `gpt-4.1-mini-2025-04-14`, `claude-haiku-4-5-20251001`, OpenRouter `google/gemini-3.1-flash-lite` pinned to `google-vertex/global`; official sources are in `evidence/model-selection.md`. Anthropic needs a Messages serializer/decoder. OpenRouter disables nested provider/model fallback and requires supported parameters. Local fixtures do not prove account access.

## Request lifecycle

1. Validate private configuration, scoped caller, immutable repository/base and text/safe-DOCX input. Authenticate expected backend capability/profile before POST.
2. Persist logical key, original content digest, actor mapping, configuration digest and bounded input spool. Reject key reuse with changed bindings.
3. Derive stable distinct child IDs. Persist intent before POST under process-safe exclusive ownership. At most one dispatch per backend, five total.
4. Select the first verified artifact. Otherwise persist a terminal receipt before advancing under the closed policy.
5. After reply loss/restart, observe the exact child. Recover its artifact if complete; unknown/in-flight/historical-untracked outcomes cannot authorize another dispatch.
6. Persist selection and attempt summaries before return. Terminal replay uses this saved result. The CLI neither rebuilds nor publishes artifacts.

## Fallback policy

| Observation | Action |
| --- | --- |
| Verified artifact ready | Select and stop |
| Connect failure proven before transmission; no older unresolved intent | Advance once |
| Durable terminal provider auth/rate/unavailability/5xx or terminated provider deadline/transport failure; artifact absent | Advance once, preserve unknown spend |
| Lost reply, caller crash after intent, interrupted backend | Read-only reconciliation; unresolved stays explicit |
| Caller/API authorization, source/profile/tenant mismatch, unsafe input, cancellation/expiry | Stop |
| Refusal/moderation, unclassified output, wrong model, invalid accounting | Stop |
| Renderer/evaluator/artifact-retention failure after normalization | Stop/recover without another model |
| Every provider fails | Finite result; no return to Qwen |

Provider-side 401 differs from local API 401/403. A terminated timeout can still cost tokens; five attempts is a request bound, not a monetary guarantee.

## Durable facts and compatibility

Add versioned authenticated capability/attempt-status contracts. Preserve closed v1 job/result shapes and retained provider evidence v1/v2. Store an atomic snapshot of state, provider phase/finality, safe category and artifact absence/presence. Bind actual provider/profile/model/adapter, tenant/repository/child, content/base and actor identities.

Persist independently validated usage even if later draft validation fails. Missing measurements use null and explicit status. Keep provider-specific accounting and actual winner evidence. Child input digests may differ due to child IDs/timestamps; bind each to the same original bytes/target.

Use additive schema migration, strict validation and backup/restore compatibility. Historical jobs lacking facts stay untracked; never synthesize authoritative receipts. Private storage rejects symlinks/unsafe ownership/overlap, bounds size/retention and excludes raw input, bodies, credentials or reasoning from results/logs.

## Adoption

Install exact reviewed merged source and compatible state readers, then common CLI/scoped config. Route new submissions through it and qualify controlled safe failures. Source support alone does not prove activation. Rollback stops new routed submissions, preserves/reconciles journals and uses compatible readers; do not downgrade migrated stores to incompatible binaries.
