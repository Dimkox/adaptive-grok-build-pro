# Failover verification plan

Start with failing regression coverage before implementation. Use injected transports and private disposable SQLite/Unix fixtures; do not invoke live models during automated verification.

- Primary success: zero reserve calls, original Qwen artifact/profile.
- Primary socket absent/refused before submission: exactly one secondary invocation.
- Terminal provider 401, 429, 5xx and deadline: classified fallback; API 401/403: stop.
- Policy refusal, unsafe input, incompatible media, wrong source/profile and corrupt evidence: no secondary invocation.
- Lost response after the job was accepted or artifact generated: recover from the exact child observation, without duplicate effects.
- Caller crashes before intent, after durable intent, during dispatch and after response: at-most-once behavior and explicit ambiguity.
- Every edge of Qwen → Grok → OpenAI → Claude → OpenRouter: each backend once, first success stops, all five failures terminate without returning to Qwen.
- Provider-specific requests and accounting: OpenAI completion cap, Anthropic Messages/native schema/cache accounting, pinned OpenRouter upstream with nested fallback disabled.
- Same logical ID/content replay versus changed input under the same ID; concurrent caller lock contention.
- Complete and missing usage, failed-output usage already received, profile identity, historical v1/v2 compatibility.
- Private file ownership, symlink/overlap rejection, input size/deadline/retention bounds and absence of raw input or secrets in output.

After focused checks, run `python3 scripts/grok_verify.py --mode pr` and all four route-selected independent reviews. A controlled operational smoke is separate and must bind exact installed source and authorized resources. It should inject a known primary failure through a test boundary; do not stop the working primary service just to demonstrate fallback without exact operational scope.

Typed criteria name required future receipts; map the actual regression paths after implementation and execution. Planned coverage is not evidence of a pass.
