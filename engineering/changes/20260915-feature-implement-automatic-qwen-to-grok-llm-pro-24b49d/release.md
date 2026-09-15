# Delivery and qualification

Source change through this isolated branch and a pull request, after the named scope/design gate. The selected `ai_implementer` owns implementation; local verification and independent reviews remain preflight. Merge authority is the exact-head App-owned Trust CI check and required external signed scopes.

Operational installation uses the exact merged source, explicit runtime paths and applicable exact grants. The existing provider key boundaries remain outside the checkout. A successful synthetic failover proves bounded L5 fallback only; v2.0.16, external-pilot status, M8 and general M9 qualification do not change automatically.

Authenticated metadata probes on 2026-09-15 returned HTTP403 for OpenAI, Anthropic and OpenRouter; OpenAI explicitly reported `unsupported_country_region_territory`. One synthetic generation POST each through the candidate `f079b925160a5d6c0ac66f9905f1cb83672f74d2` Anthropic and OpenRouter adapters also returned permission/403, without an artifact or service activation; their exact upstream, account or network cause remains unestablished. See `evidence/provider-readiness.json` and `evidence/provider-generation-probe.json`. All three added providers and the full chain remain unqualified for inference, and access restrictions must not be bypassed.
