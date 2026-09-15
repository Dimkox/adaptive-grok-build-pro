# Implementation plan

Sole writer: `ai_implementer` owns product code/tests/contracts/config/operator docs. Parent owns this package and verification/delivery coordination. User approval is recorded in `brief.md`.

1. Add red regressions for absent primary, lost HTTP class/usage, new adapters and replay after lost submission. Use mocked provider transports and disposable private Unix/SQLite resources.
2. Implement all five explicit profiles/key loaders. Add Anthropic Messages, OpenAI token handling and pinned OpenRouter. Validate request/response fixtures and preserve historical profiles.
3. Add authenticated versioned capability/attempt facts with atomic storage, additive migration and backup compatibility. Verify phase, artifact absence, factual/unknown usage and old records.
4. Add common CLI/config/journal/spool, stable child IDs, one dispatch per backend, receipt validation and crash/replay reconciliation. Test all five failures and stopping conditions without nested retry.
5. Add entrypoint/examples/operator instructions, exact model defaults and rollback; README separates source support from installed qualification.
6. Run focused tests, map actual evidence, freeze source and run `python3 scripts/grok_verify.py --mode pr`. Run all four independent reviews. Deliver PR and await exact-head App-owned Trust CI/required external scopes. Install/qualify only exact approved operational resources.

Preserve architecture budgets without limit weakening/minification/route splitting. Automated checks use no live models. Any review fix returns to the same writer and invalidates stale evidence.
