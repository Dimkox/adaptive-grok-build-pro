# Official xAI usage analysis

Completed read-only by docs_researcher, route feeb4f381209.

The official Chat Completions example reports prompt32 + visible completion9 + reasoning94 = total135, matching the live structure; generic total_tokens prose inconsistently says prompt+completion. max_completion_tokens covers visible output, excludes reasoning/function calls, and max_tokens is deprecated. Reasoning is billed at completion-token rates; exact cost_in_usd_ticks is separate and is outside this repair.

Grok additive total P+C+R maps to generated output C+R. Preserve inclusive P+C=T as legacy compatibility only with R<=C (positive-reasoning inclusive form was not independently demonstrated by an xAI example). Require explicit valid reasoning metadata to explain discrepancies; reject bool/negative/excessive fields. Qwen remains unchanged. Existing local output cap can remain an acceptance bound on normalized output, stricter than the wire visible cap, but cannot prevent charges already incurred.

Sources:
- https://docs.x.ai/developers/rest-api-reference/inference/chat-completions.md
- https://docs.x.ai/developers/advanced-api-usage/prompt-caching/usage-and-pricing
- https://docs.x.ai/developers/model-capabilities/text/reasoning
- https://docs.x.ai/developers/cost-tracking
