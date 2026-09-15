# Direct Claude adapter preparation

User reports a Claude key in `.env`. No credential file was read, no model selected, and no authenticated request made.

The selected AI architect checked official Anthropic documentation:

- [API overview](https://platform.claude.com/docs/en/api/overview): Messages API is at `https://api.anthropic.com/v1/messages` and requires the Anthropic version header plus authentication and JSON content type.
- [Messages creation](https://platform.claude.com/docs/en/api/messages/create): top-level system instructions, `model`, `max_tokens`, message content blocks; response uses `content[]`, `stop_reason` and Anthropic usage rather than Chat Completions `choices[]`.
- [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs): schema output support depends on the selected model; refusal/truncation still need explicit handling and local draft validation.
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching): preserve cache-creation/cache-read input components when accounting, rather than considering only uncached input.
- [Thinking accounting](https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost): output thinking counts are a breakdown, not another quantity to add to total output tokens.
- [Errors](https://platform.claude.com/docs/en/api/errors): distinguish authentication, billing, permission, rate/spend limits, server failure and overload. Disable SDK automatic retries if an SDK is introduced; the existing bounded HTTP transport avoids adding one merely for this change.

Inference from these documented shapes and the inspected code: direct Claude needs a dedicated serializer/decoder implementing the shared attempt interface. Changing the URL/key in `OpenAICompatibleLandingExecutor` would be insufficient. New models, provider order and spending-related fallback policy remain explicit configuration/design choices, not assumptions from key presence.
