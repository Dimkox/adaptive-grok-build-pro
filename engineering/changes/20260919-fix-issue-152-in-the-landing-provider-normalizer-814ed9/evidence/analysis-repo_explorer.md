# Repository exploration — issue #152

Route: `814ed9c452cd`; read-only source/test inspection; no tests or external calls performed.

## Minimal impact map
- `factory/src/adaptive_factory/landing_http.py:279–300`: execution/result validation precedes draft decoding; only the second catch has a validated completed result and therefore may retain its real response digest and a draft diagnostic.
- `landing_http.py:325–338`: `_terminal` receives that result and preserves reported observation usage, but always substitutes a state/reason digest. Preserve the fallback for paths without a validated result.
- `factory/src/adaptive_factory/landing_normalizer.py:465`: `decode_landing_draft` emits `LandingProviderError("draft_fields")` for `{}` and `LandingContractError("sections")` for the valid fixture with `sections=[]`.
- `factory/src/adaptive_factory/landing_contracts.py:50–176`: contract errors expose `.code`; their string includes potentially sensitive detail (unknown or duplicate JSON keys). Retain only closed allowlisted codes, never exception strings/details or raw response text.
- `factory/src/adaptive_factory/landing_provider.py:275`: `reason_code` is a bounded identifier with no enumeration, so it can carry the allowlisted draft code without changing the closed observation v1 shape or schema.
- `factory/src/adaptive_factory/landing_sqlite_store.py:625–666`: existing `reason_code` and canonical observation JSON already persist both facts; no SQL column, migration, historical backfill, or observation extension is needed.
- `factory/src/adaptive_factory/landing_failover_contracts.py:38–67`: attempt receipts already expose `reason_code` and nested evidence. Keep receipt keys/version, evidence versions, and closed legacy `/v1` response shapes.
- No product consumer compares `http_outcome_unusable`; `landing_failover.py:120` routes using observation category. Historical September 14 change requirements and dated review/runtime records retain their original generic reason as past evidence.

## Closest fixtures and existing tests
- `factory/tests/test_landing_failover_providers.py::ProviderObservationTests.normalize` uses fixed source, clock, usage and `httpx.MockTransport`; extend beside `test_valid_usage_survives_rejected_draft`.
- `factory/tests/test_landing_normalizer.py::draft` supplies valid canonical draft bytes; mutate only `sections` to isolate decoder failure. Its `source` helper supplies a stable input identity.
- Adapt `factory/tests/test_landing_live_executors.py::HttpLandingDraftNormalizationTests.test_http_malformed_sections_return_controlled_outcome_with_evidence` (~450) from the generic draft reason to the specific allowed code; retain `needs_human` and no artifact.
- Adapt `factory/tests/test_landing_live_executors.py::LandingLiveGrokQwenCompositionTests.test_malformed_sections_persist_controlled_reason_and_evidence` (~516); this is the second and final generic-reason assertion covering actual new draft failures.
- Retain `test_landing_live_executors.py::GrokReasoningUsageTests.test_aggregate_output_at_cap_passes_but_one_token_over_is_rejected` (~277) with generic reason: executor accounting fails before result validation, not during draft decoding.
- `factory/tests/test_landing_failover_backend.py::BackendObservationTests` contains authenticated `/v2/.../attempt`, SQLite restart, and legacy-store migration examples suitable for the durable/API regression.
- `factory/tests/test_landing_failover.py::CallerRoutingTests.test_policy_accounting_renderer_and_local_authorization_never_fall_back` guards the non-fallback semantics that draft rejection must retain.

## Required regression assertions
1. `{}` and valid-draft-with-empty-sections retain exact distinct allowlisted `reason_code` values, actual response SHA-256, and distinct evidence/observation digests with equal input/clock/usage.
2. Calculate expected response digests from the exact canonical HTTP envelopes supplied to the mock transport, independently of product helpers; hashing only decoded draft bytes would assert the wrong boundary.
3. Sensitive exception detail and unknown `LandingProviderError`, `ValueError`, or `OSError` content never appear in serialized jobs/receipts; unknown failures keep the generic reason, while allowlisted contract codes survive without their details.
4. Missing/invalid executor results and pre-dispatch failures cannot acquire a response digest or a draft diagnostic; normalized success and reported usage remain unchanged.
5. Persist the failing normalized job, reopen SQLite, retrieve its authenticated `/v2` receipt, and validate the receipt. Include historical generic-reason rows/observation JSON with original digests and unchanged closed `/v1` views.

## Focused command for the sole writer
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:delivery/src python3 -m unittest factory.tests.test_landing_failover_providers factory.tests.test_landing_failover_backend factory.tests.test_landing_live_executors factory.tests.test_landing_failover factory.tests.test_landing_api factory.tests.test_landing_sqlite_store`

Run schema/contract checks and route-required `python3 scripts/grok_verify.py --mode pr` after implementation; this analysis is not verification evidence.
