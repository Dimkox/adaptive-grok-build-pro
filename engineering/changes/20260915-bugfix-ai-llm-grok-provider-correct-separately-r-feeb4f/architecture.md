# Bounded design

Change the existing Grok response decoder. Validate P,C,T and optional completion_tokens_details.reasoning_tokens as bounded non-boolean integers. For Grok, accept additive T=P+C+R with explicit valid R and report output C+R; preserve legacy inclusive T=P+C when R<=C, reporting C. Reject any other total relationship and malformed reasoning. Do not infer arbitrary reasoning from a residual.

Preserve the existing maximum-output check against normalized generated output as a local acceptance limit. xAI wire max_tokens limits visible output only; local validation detects an overrun after consumption and makes no spend-prevention claim. No cap increase, reasoning-effort override, wire-parameter migration, price calculation, fallback or retry belongs here.

Select a new Grok-only adapter version and decoder digest for current profile facts and emitted evidence. Preserve Qwen profile/evidence identity and behavior. Retained evidence v1/v2 already accepts independent versions and remains read-only compatible. No schema, migration, dependency, model or prompt change.

Route-selected analysis/review roles are mandatory; ai_implementer is the sole product-code owner. Product rollout must pass external Trust CI on the exact PR head and use the exact merged commit. The separate Grok instance can upgrade independently while Qwen remains on its working release.
