# Delivery and qualification

Source change through this isolated branch and a pull request, after the named scope/design gate. The selected `ai_implementer` owns implementation; local verification and independent reviews remain preflight. Merge authority is the exact-head App-owned Trust CI check and required external signed scopes.

Operational installation uses the exact merged source, explicit runtime paths and applicable exact grants. The existing provider key boundaries remain outside the checkout. A successful synthetic failover proves bounded L5 fallback only; v2.0.16, external-pilot status, M8 and general M9 qualification do not change automatically.

Read-only authenticated metadata probes on 2026-09-15 returned HTTP403 for OpenAI, Anthropic and OpenRouter. OpenAI explicitly reports `unsupported_country_region_territory`; Anthropic reports `forbidden`; OpenRouter's precise cause is not established. No inference occurred. See `evidence/provider-readiness.json`. Source support for those APIs cannot be reported as successful live qualification, and access restrictions must not be bypassed.
