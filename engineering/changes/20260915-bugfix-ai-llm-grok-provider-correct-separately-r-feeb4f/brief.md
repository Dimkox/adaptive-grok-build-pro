# Grok reasoning usage compatibility

Typed authority: [change-spec.yaml](change-spec.yaml).

User requested adding Grok alongside Qwen using the designated local key. The installed Grok adapter rejected a real authenticated grok-4.6 response with executor_usage: 1336 prompt + 93 completion + 1169 reasoning = 2598 total. The normalizer reduced this to needs_human/http_outcome_unusable, preventing artifact generation. Sanitized response metadata and the failed job are preserved in evidence.

Scope: fix only provider response usage normalization, its identity binding and regression tests/documentation. No dependency, API schema, database, routing algorithm, model change, automatic retry or fallback. One implementation owner: ai_implementer. Route feeb4f381209 has no named design approval gate. Five selected analyses run with three concurrent slots; the remaining selected agents start as slots free.

Current operations: Qwen remains active/enabled with original PID 698333 and installed release 5f6f6ce. The additional Grok instance is configured, but stopped/disabled after the failed probe. Runtime-only preparation is preserved outside Git in the original checkout .grok-stack/runtime/grok-connect-20260915. Its credentials never enter this change package.

Completion: verified source and independent code/test/security reviews first; branch push/PR, exact-SHA external Trust CI, required approvals and merged-code deployment precede a new Grok live task.
