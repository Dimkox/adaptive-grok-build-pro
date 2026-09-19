# Issue 152: preserve safe rejected-draft diagnostics

User requested continuation of the Claw upgrade after the Qwen draft failure. The accepted bounded source repair retains the safe validator cause and original validated response digest for future failures, with regression coverage and factory delivery. It does not reconstruct the discarded response or claim the primary profile is accepted.

Use existing reason_code in LandingNormalizationOutcome/SQLite/attempt receipts. Keep category=draft, state=needs_human and reported observation usage. Recognized contract codes map to fixed draft-prefixed strings; the exact LandingProviderError argument draft_fields maps to draft_fields; other caught failures map to draft_validation_failed. Preserve result.response_digest only after executor metadata validation has succeeded. No raw response/exception details are retained.

No database, API or observation schema, prompt, model, decoder algorithm, accepted inputs, transport behavior or accounting change is required. No profile identity bump: this corrects diagnostic retention using existing fields, while acceptance/wire/decoder policy remains the same; exact source SHA identifies the repair. Historic profile hashes cannot prove that diagnostics were retained. This bounded compatibility ruling resolves the architecture/integration reports' optional identity-bump alternative.

Historical rows remain immutable. Source verification is offline; a later operational route must bind installation and any new acceptance to its merged source. Current Grok and the separate Omni instance remain operating while source work proceeds.
