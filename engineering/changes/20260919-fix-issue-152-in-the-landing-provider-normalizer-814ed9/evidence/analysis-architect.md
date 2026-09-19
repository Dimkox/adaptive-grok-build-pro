# Architecture analysis — issue #152

Route: `814ed9c452cd`; read-only source inspection; implementation owner: `data_implementer`.

## Recommendation

Use the existing outcome/job/attempt `reason_code` for a fixed diagnostic vocabulary, for example `draft_fields`, `draft_sections`, and `draft_validation_failed` for unknown failures.
Keep `state=needs_human`, `spec=None`, `category=draft`, and the existing evidence disposition. Failover decisions use category, so these diagnostic reasons must not enable fallback.
Change only the post-validated-result draft failure path in `landing_http.py`: preserve `result.response_digest` in evidence; retain the synthetic terminal digest when no fully validated result exists.
Keep reported observation usage and its exact validated counters unchanged; do not bundle transport/accounting or acceptance-policy changes.

## Why this placement is sufficient

`landing_provider.py:275` already bounds reason codes to an identifier of at most 128 characters.
`landing_service.py:421`, `landing_sqlite_store.py:251`, and `landing_failover_contracts.py:45` already carry the reason atomically into durable jobs and sealed attempt receipts.
The v2 attempt endpoint exposes that receipt; its reason field is not an enum. The closed v1 job/result projections need no additions.
`LandingProviderObservation.from_dict` accepts an exact v1 field set and verifies a canonical digest. Adding a diagnostic there would require versioned parsing, schema references, and mixed-version receipt support without improving this task's outcome.
The diagnostic is bound by the outer attempt receipt digest, not by `observation_digest` alone; consumers must retain the whole receipt when retaining the diagnostic.

## Security and compatibility

Map recognized `LandingContractError.code` values through an explicit finite allowlist; never persist `str(exc)`, exception details, unknown field names, output fragments, or arbitrary codes.
The decoder's `LandingProviderError("draft_fields")` has no structured code: recognize only that exact safe argument shape; all other caught errors receive the fixed generic reason.
Preserve `_validate_result` before trusting digest or usage; invalid result metadata remains the existing generic protocol/accounting failure.
Do not broaden decoder acceptance or exception handling merely to improve diagnostics.
No SQLite migration, backfill, observation schema, or API/receipt version is necessary. Existing rows, null observations, evidence digests, generic reasons, and synthetic historical response digests remain unchanged.
Offline validation should cover different known failures, unknown sensitive exceptions, invalid result metadata, restart plus authenticated attempt retrieval, legacy receipt validation, and unchanged closed v1 projections.

## Identity and rollout consequences

Recommend a patch adapter identity for every profile using the shared HTTP normalizer so newly emitted evidence identifies the changed retention semantics; a Grok-only bump would misdescribe the shared scope.
Keep draft schema, prompt, wire protocol, and decoder digest unchanged when the draft/transport decoding algorithm itself is unchanged; the adapter change already changes `profile_digest`.
Stored evidence parsers accept independent historic adapter/decoder identities, but caller configuration, capability checks, and active receipt binding require exact current profile identities (`landing_failover_config.py:88`, `landing_failover.py:149`).
Any adapter bump therefore requires coordinated caller/backend configuration refresh; preserve the old binary/configuration for unresolved historical caller attempts rather than rewriting their bindings or replaying provider work.
If this deployment cost is intentionally avoided, document retaining adapter identity as an observability-only compatibility ruling; do not claim that the unchanged profile hash distinguishes pre-fix and post-fix diagnostics.
Roll back code/configuration together while retaining the same compatible SQLite records; do not reconstruct historical diagnostics. This analysis authorizes no runtime operation.
