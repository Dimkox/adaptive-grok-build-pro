# Rejected-draft diagnostic repair implementation plan

Goal: retain a safe reason and the actual validated response digest without changing the closed receipt/observation shapes or historical rows.
Architecture: reuse reason_code and the current evidence/observation sealing path; no migration, API-field addition or profile epoch change. Spec: change-spec.yaml and brief.md. Sole application writer: route-selected data_implementer; root owns this package and delivery only.

## Task 1: failing regression and minimal normalizer repair

Files: factory/src/adaptive_factory/landing_http.py; factory/tests/test_landing_failover_providers.py; factory/tests/test_landing_live_executors.py.

- [x] Add failing tests for {} versus a valid draft with sections=[], asserting distinct safe reasons and original validated response digests, needs_human/draft, and unchanged reported usage.
- [x] Cover secret-bearing unknown/duplicate keys, unknown ValueError/OSError/provider error text, and malformed/non-string contract codes. Only explicit allowlisted codes or the fixed fallback may escape.
- [x] Run those tests before implementation and retain the expected assertion failures.
- [x] Implement the finite mapping at the existing decode catch and preserve validated result.response_digest in _terminal. Invalid executor metadata must still use current generic handling and synthetic evidence.
- [x] Adapt the two existing malformed-section reason assertions; retain the pre-validation reasoning-usage failure assertion unchanged. Do not expand decoding or exception catch behavior.

## Task 2: persistence and compatibility

Files: factory/tests/test_landing_failover_backend.py and existing fixtures as needed.

- [x] Through the real normalizer/service/SQLite path, submit a mocked failed response, close and reopen the store, retrieve the authenticated v2 attempt, and validate its seal, reason, response digest and usage. The resumed executor must be forbidden from running.
- [x] Retain exact legacy generic-reason/observation payloads and digests, including old null observations; do not invent missing data. Assert the v1 result field set stays unchanged and draft remains ineligible for failover.
- [x] Run only affected focused tests and report command/result counts. Root runs the mandatory factory verifier once on frozen product files, followed by the selected independent reviews and exact-head external Trust CI.

Rollback: deploy the previous compatible code against unchanged record formats; retain new diagnostic rows instead of rewriting them. This plan performs no provider call or operational rollout.

Implementation and focused checks are complete. The controller verifier ran once: all tests and product checks passed; its sole stale local origin/HEAD failure was repaired and only the existing Git checker repeated on the identical tree. Independent reviews and external delivery remain separate pending tasks.
