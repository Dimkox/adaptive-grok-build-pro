# Independent code review — issue #152

Result: **PASS**. No actionable correctness, privacy, consumer-compatibility, or scope defect found in the reviewed diff.

Reviewer: route-selected `code_reviewer`, independent of implementation. Route `814ed9c452cd`; branch `fix/issue-152-draft-diagnostics`; workspace `/var/tmp/adaptive-issue152-20260919`; base and review-time HEAD `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`. Review covers the uncommitted product delta and new legacy fixture identified below, against the approved brief, specification and plan. This report is local review evidence, not merge or operational authority.

## Inspected behavior

- `factory/src/adaptive_factory/landing_http.py:78`: the 17-entry mapping has fixed string outputs; no exception message, unknown code, model-supplied key or response content becomes a reason. The helper accepts exact string contract codes, recognizes only the single exact provider argument `draft_fields`, and uses one fixed `draft_validation_failed` fallback. The known codes match the decoder and its called contract validators.
- `factory/src/adaptive_factory/landing_http.py:310`: executor execution and complete result validation still precede draft decoding. Invalid metadata retains `http_outcome_unusable`, synthetic response evidence, the original protocol/accounting category, and unavailable usage. The decoder catch has the same exception classes as the base; only its diagnostic selection changes.
- `factory/src/adaptive_factory/landing_http.py:355`: the only caller supplying `result` is the post-validation decoder-failure branch. Retaining its `response_digest` therefore preserves the validated upstream envelope hash rather than hashing extracted draft bytes or accepting unvalidated result metadata. Existing constructors reseal the evidence and observation. Terminal evidence counters remain zero and reported observation counters remain unchanged, as required by the scoped accounting boundary.
- `factory/src/adaptive_factory/landing_live_executors.py:533`, plus the decoder at `landing_normalizer.py:465` and contract validators in `landing_contracts.py`, confirm the digest and failure boundaries. Draft acceptance, prompts, profiles, adapter/decoder identities, transport behavior and exception policy are unchanged.
- `factory/src/adaptive_factory/landing_provider.py:262`, `landing_service.py:396`, `landing_sqlite_store.py:622`, `landing_observation.py`, `landing_failover_contracts.py:38`, and `landing_backend_api.py:42` preserve the bounded reason, evidence binding, authenticated retrieval and existing sealed record shapes. The attempt schema permits bounded string reasons without a value enum. The v1 projections remain closed.
- `factory/src/adaptive_factory/landing_failover.py:118` uses category/state/phase/artifact eligibility rather than reason text. The unchanged `draft` category is excluded from `FALLBACK_CATEGORIES`; rejection remains `needs_human` without a spec or artifact.

## Regression and evidence assessment

Inspected every changed test and the frozen historical receipt. The tests independently hash the exact mocked HTTP response envelope; distinguish `{}` from empty sections; reject sensitive or malformed exception diagnostics; guard the pre-validation result boundary; and exercise real normalization/service/SQLite storage with authenticated receipt retrieval after reopening and a forbidden replay executor. They retain exact historical receipt seals and stored observation bytes, reported usage, the v1 result shape and draft fallback refusal. Existing null-observation coverage remains in the affected suites. The two changed pre-existing expectations are limited to malformed-section diagnostics.

Read `implementation-red.txt`, `implementation-green.txt`, `implementation-focused.txt`, `verification.json`, and the ignored original/composed verifier reports. Recorded results are 13 tests with 24 expected pre-fix assertion failures, then 13 passing tests and 92 passing affected tests; the full verifier records 785 core tests plus 1098 subtests, 51 factory unit tests, and 774 factory tests with two skips and two disposable PostgreSQL restarts. These are inspected execution records, not tests rerun by this reviewer.

The original full invocation exited 1 solely for unresolved local `origin/HEAD`; its SHA-256 is `bf5e31b8ee6f5dc65c017c37d14903acf4e682da72f8b17f02bf835342b65f86`, matching the durable provenance. The composed report records the existing Git check passing after the local ref repair, on the same test-run fingerprint `2c3d1ec45d2ec2b56b5622a98ca524bb0040030231be2eb1e429702fb4633b96`. Current `origin/HEAD` resolves to `refs/remotes/origin/main`. Independently ran `git diff --check 26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960` successfully and recomputed every product-file hash below; all match `verification.json`. No unresolved concern justified repeating broad tests.

## Reviewed product SHA-256 values

| File | SHA-256 |
| --- | --- |
| `factory/src/adaptive_factory/landing_http.py` | `21c03d67fe6f2db1126238397d59e4fec5d38c17de6a82de2eb22d565ca01ddc` |
| `factory/tests/test_landing_failover_backend.py` | `77628b032986c6643aa27bb00392204f1de6244a16f0f972a1714fe8bc308ad7` |
| `factory/tests/test_landing_failover_providers.py` | `c5ced5327e4608c8656bbdb3f2e96faa4523820c2762589aa80bb7da015d3841` |
| `factory/tests/test_landing_live_executors.py` | `107a4da22510b43f658524d88484bf46d6f3626b232a383a0ff165bc700996f8` |
| `factory/tests/fixtures/landing-legacy-draft-attempt.json` | `55b684d1a6603b2a4da3e9ef7ecda75656e96d004e9e0f4e1d36837ef3a11d1c` |

## Limits and handoff

The unchanged decoder still has exception classes outside its existing catch scope; this review does not claim broader malformed-input hardening. Historical diagnostics are not reconstructed, and unchanged profile identities do not distinguish pre-fix retention from post-fix retention; exact source SHA remains the repair identity, consistent with the approved compatibility ruling. No live provider or production behavior was exercised.

Only this report was written by the reviewer. No product edits, test reruns, credentials, provider/runtime calls, commits, pushes or subagents were used. Review reports and other package updates change the whole-repository evidence fingerprint; the controller must bind final local receipts after those updates. The external exact-head Trust CI gate and any operational rollout remain separate.
