# Verification deferred by user

2026-09-12 instruction: «прверки пока не проводим», reinforced by «нашел - сохрани» and «и иди дальше».

No tests, lint, builds, compilation checks, local verifier, reviews or live probes are run. New test authoring is also postponed to keep this phase focused on source implementation. No passing receipts may be created.

Saved regression scenarios for a later phase: cross-provider/profile mismatch; unavailable mode reads no credential and performs no call; unsupported media is rejected before blob transfer; response overflow/duplicate keys/tool calls/nonterminal completion/missing usage; factual elapsed time and token counts; total deadline; owned-resource cleanup on partial startup; second-process writer exclusion; interrupted state recovery without replay; native Codex and fixture compatibility; existing v1 OpenAPI unchanged.

Later execution order, only when checks resume: focused cases, full PR verifier, independent route-selected reviews, exact-head external Trust CI via PR.
