# OpenRouter integration constraints — design addendum

Route `24b49d0529c8`; official public documentation researched on 2026-09-15. No `.env`, credentials, authenticated API, live inference or runtime configuration was accessed. Key availability is user-reported, not verified activation. Existing implemented profiles remain Qwen/Grok; OpenRouter, direct OpenAI and direct Claude adapters are additional proposed scope. Provider order, exact models and OpenRouter upstream endpoint remain unselected pending the user and the design gate.

## Endpoint and authentication

- Chat Completions uses `POST https://openrouter.ai/api/v1/chat/completions`; the compatible client base is `https://openrouter.ai/api/v1`. Authenticate with the OpenRouter key in `Authorization: Bearer ...` and send JSON. It is a distinct credential from direct-provider keys. Sources: [Quickstart](https://openrouter.ai/docs/quickstart), [Chat API](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion).
- Suggested initial adapter shape is bounded non-streaming text Chat Completions, with the existing caller timeout/no-retry policy and no tools or optional plugins. This is a design recommendation, not a claim that compatibility alone implements the adapter.

## Disable nested routing

OpenRouter provider fallback defaults to enabled. `provider.allow_fallbacks=false` disables it; `provider.only` restricts eligible providers, while `provider.order` specifies preference. A base slug can match multiple regions/variants, so use an approved full endpoint slug when exact upstream identity is required. `provider.require_parameters=true` prevents routing to an endpoint that would ignore unsupported requested parameters. Account-level allowlists can further restrict the request; an empty intersection fails. Source: [Provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).

Recommended request constraint, with placeholders intentionally unselected:

```json
{
  "model": "<approved-concrete-model-id>",
  "provider": {
    "only": ["<approved-exact-endpoint-slug>"],
    "order": ["<approved-exact-endpoint-slug>"],
    "allow_fallbacks": false,
    "require_parameters": true
  }
}
```

Do not send a `models` fallback array: it explicitly enables model switching and can activate on moderation, context, rate-limit or availability errors. The application must retain its narrower approved failure policy. Source: [Model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks).

Avoid latest/automatic router aliases, presets and routing variants in the approved profile. Latest aliases intentionally change their resolved model without a client deployment; the response names the actual resolved model. Source: [Latest model resolution](https://openrouter.ai/docs/guides/routing/routers/latest-resolution). This prohibition is an application design recommendation to keep the explicit chain stable.

## Structured output and identity

Use `response_format.type=json_schema`, with `json_schema.name`, `json_schema.schema` and `json_schema.strict=true`, only for a model/endpoint that supports it. Retain local schema validation and treat unsupported schema parameters as a controlled configuration error rather than silently downgrading. Do not enable the optional Response Healing plugin implicitly. Source: [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs).

The model catalog exposes `id`, `canonical_slug`, supported parameters, modality and context limits; use these to validate the eventually selected configuration. Source: [Model catalog API](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties). Preserve the requested identity, validated returned `model`, OpenRouter response `id`, gateway identity and approved upstream endpoint separately. Do not relabel an OpenRouter Claude/Grok response as a direct Anthropic/xAI attempt. The Chat API documents optional `X-OpenRouter-Metadata: enabled`; consume only bounded allowlisted identity/accounting fields if enabled, never dump arbitrary routing metadata or request content. [Chat API](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion).

## Usage and uncertain outcomes

Usage is documented as automatically returned in complete non-streaming responses or the final SSE message: native-tokenizer prompt/completion/total tokens, optional reasoning/cache details, and account charge `usage.cost`. `usage: {include:true}` and `stream_options: {include_usage:true}` are deprecated. Upstream inference cost is distinct from the account charge; missing values must remain unknown. Generation-ID lookup can recover usage when a response ID is already known; it does not establish request-key idempotency or resolve a lost response with no ID. Source: [Usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting).

OpenRouter documents reasoning as included in completion tokens for billing; do not automatically apply the direct-Grok additive reasoning rule. Validate normalized usage with provider-specific fixtures before integration, and preserve known usage if downstream parsing fails. Source: [Activity export — reasoning tokens](https://openrouter.ai/docs/cookbook/administration/activity-export).

The explicit chain must still reconcile ambiguous POST outcomes before any further dispatch. Disabling OpenRouter routing fallbacks does not prove exactly-once execution or billing after network loss. This research selects no model, authorizes no provider call and establishes no installed fallback capability.
