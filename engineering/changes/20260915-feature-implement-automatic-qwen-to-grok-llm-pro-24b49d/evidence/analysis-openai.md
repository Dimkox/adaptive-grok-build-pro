# OpenAI adapter preparation

User reports adding an OpenAI API key to `.env`; no secret values or credential files were read, no authenticated request was made, and no model was selected.

Local source inspection found no direct OpenAI, Anthropic or OpenRouter landing profile. The existing `OpenAICompatibleLandingExecutor` is composed only for Qwen/Grok and is constrained by their closed profiles. A new key alone does not register another executable provider.

Official documentation fetched on 2026-09-15:

- [Chat completion creation](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) documents `/chat/completions`, model-dependent parameters and `max_completion_tokens`, which includes visible and reasoning tokens. Legacy `max_tokens` is deprecated and incompatible with o-series models. The current executor always sends `max_tokens`, so model-specific request shaping needs review.
- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) documents schema-constrained JSON. The adapter must still handle refusals and validate returned data before it becomes a landing spec.

Compatibility decision remains pending exact model selection. Preserve model identity, use an intentional response/token decoder and pin parameter support. Do not copy Grok reasoning-accounting assumptions into another provider without verifying its usage shape. Persist known failed-attempt usage and explicit unknown measurements through the common attempt contract.

This is protocol/design research, not evidence that the user's key is valid, funded or permitted to call a particular model.
