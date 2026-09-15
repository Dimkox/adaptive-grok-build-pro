# Reserve model defaults — official documentation review

Date: 2026-09-15. Route: `24b49d0529c8`. Author: `docs_researcher`.
Scope: delegated default selection for bounded L5 JSON normalization, after the accepted five-provider continuation in `brief.md`. This supersedes the earlier reports' pending-model-selection wording. No credentials or inference endpoints were used.

## Recommended defaults

Preserve Qwen (`qwen-intl` / `qwen-plus`) then Grok (`grok-vision` / `grok-4.6`). Add these reserves in order:

| Position | Service | Request model ID | Standard USD / 1M text tokens, input / output |
| --- | --- | --- | --- |
| 3 | Direct OpenAI | `gpt-4.1-mini-2025-04-14` | $0.40 / $1.60 |
| 4 | Direct Anthropic | `claude-haiku-4-5-20251001` | $1.00 / $5.00 |
| 5 | OpenRouter, Google Vertex global endpoint | `google/gemini-3.1-flash-lite` | $0.25 / $1.50 |

- OpenAI documents the dated snapshot, Chat Completions and structured outputs support, and low latency without a reasoning step. Choosing this supported snapshot for a bounded normalization task is an engineering judgment; it is not a measured comparison with newer models. [Model, capabilities and prices](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
- Anthropic documents the dated Haiku API ID and these prices in its current model table. Haiku 4.5 supports structured JSON; leave extended thinking disabled. [Model table](https://platform.claude.com/docs/en/models/overview), [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
- OpenRouter's paid, non-preview model is documented for efficient, high-volume tasks. Its public catalog identifies canonical slug `google/gemini-3.1-flash-lite-20260507`; use the catalog's request `id` above, rather than assuming the canonical slug is an accepted request alias. The selected endpoint supports `response_format`, `structured_outputs` and `max_tokens`. [Model and pricing](https://openrouter.ai/google/gemini-3.1-flash-lite), [public model catalog](https://openrouter.ai/api/v1/models), [exact model endpoints](https://openrouter.ai/api/v1/models/google/gemini-3.1-flash-lite/endpoints).

These prices are a documentation snapshot for standard text traffic, excluding caching, batch/flex/priority discounts or premiums and other billable features. They establish neither account access nor measured latency/quality.

## Wire compatibility

- OpenAI: non-streaming Chat Completions; `response_format={"type":"json_schema","json_schema":{"name":"landing_draft","strict":true,"schema":...}}`. Keep the task's bounded output cap; do not send a reasoning-effort setting to this non-reasoning model. Detect refusal and truncation before validating success. [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
- Anthropic: POST `https://api.anthropic.com/v1/messages`; top-level `system`, `messages`, `model`, `max_tokens`, and `output_config.format={"type":"json_schema","schema":...}`. Send `anthropic-version: 2023-06-01`; current authentication supports Bearer or legacy `x-api-key`. Structured-output beta headers are no longer required. Do not copy Chat Completions `response_format` into Messages. [API overview](https://platform.claude.com/docs/en/api/overview), [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
- OpenRouter: POST `https://openrouter.ai/api/v1/chat/completions`, Bearer OpenRouter key, the Chat Completions JSON-schema shape, and bounded `max_tokens`. The chosen model supports reasoning effort `minimal`; use that explicitly if requesting reasoning control. [Chat API](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion), [selected model](https://openrouter.ai/google/gemini-3.1-flash-lite).

## Pin OpenRouter routing

```json
{"model":"google/gemini-3.1-flash-lite","provider":{"only":["google-vertex/global"],"order":["google-vertex/global"],"allow_fallbacks":false,"require_parameters":true}}
```

`google-vertex/global` is the full standard endpoint slug returned by the public endpoint catalog; avoid the broad `google-vertex` slug and the `/flex` or `/priority` variants. `allow_fallbacks` defaults to true, so it must be disabled explicitly. Required-parameter enforcement prevents silent loss of structured-output constraints. Account-level restrictions may still make this exact endpoint unavailable. [Provider routing](https://openrouter.ai/docs/guides/routing/provider-selection), [endpoint catalog](https://openrouter.ai/api/v1/models/google/gemini-3.1-flash-lite/endpoints).

Omit `models` fallback arrays, routers, `:latest` / `:free` aliases, response-healing plugins, tools and automatic service-tier selection. A model fallback array can retry other models on many errors, including moderation, which would add an uncontrolled inner chain. [Model fallback behavior](https://openrouter.ai/docs/guides/routing/model-fallbacks), [latest resolution](https://openrouter.ai/docs/guides/routing/routers/latest-resolution).

## Implementation and acceptance limits

- Bind each attempt to its configured model, API family, endpoint and accounting rules; permit explicit reviewed overrides without silently substituting an unconfigured model.
- Retain the accepted outer-chain eligibility rules and one dispatch per backend. Schema failure, refusal or a lost POST response is not evidence that an unbilled attempt never occurred.
- OpenRouter reasoning is included in completion usage for billing; do not apply xAI's separately reported reasoning addition to it. Retain usage/cost and generation identity when available. [Usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting), [activity export fields](https://openrouter.ai/docs/cookbook/administration/activity-export).
- Native structured output does not replace local schema validation, output caps or rejection of incomplete/refused results. Mock protocol tests establish adapter behavior; only a separately authorized runtime check can establish account/model access and real task quality.

Decision pattern for the implementation owner: use documented fixed model identities plus a full upstream endpoint to keep the outer failover chain observable and reproducible; newer or larger models are unnecessary to establish this integration contract. No product files were edited by this analysis.
