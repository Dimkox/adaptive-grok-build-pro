# Repo explorer — feeb4f381209

Read-only offline reproduction confirms executor_usage on captured Grok usage. Affected decoder: landing_live_executors.py _decode_response; identity sites: landing_http.py profile to_facts and normalizer _evidence. Qwen Omni has independent unchanged SSE accounting. No schema/database/dependency/model changes required.

Tests: captured sample yields1336/1262; derived output cap1262 passes/1261 fails; invalid types/bool/negative/excessive/missing reasoning and inconsistent totals rejected; legacy Grok and Qwen nonstream semantics retained; exact-model check retained; normalized evidence carries selected identity. Run existing SSE tests unchanged.

Preserve enabled Qwen profile digests:
- qwen: 63bee9e18255cbbbe940f94e96e130f6fffb103147d8cf1baf9cfa09595091be
- qwen-intl: 2616a276a5a6257515dc30e40d27fe32a667aa7d75f8205990c567166116de08
- qwen-omni: d8738006a475fbbdb5700876cec4669256933ae8c928a250853bd1775225212b

All bind adapter1.1.0 and decoder9513c336dc2e6cfecae92ebb743e10ea1bb37755e6a5a1da34393b6cd8512d43. Grok-only identity selection must be shared by profile facts and emitted evidence. Update runbook adapter wording.
