# Code re-review — M1 remediation 1

Verdict: **BLOCKED**

Reviewed exact remediation head `5b571b5452f9ffe1a9ee4f55374b49a9de541db8`, including `62b9c601de980b1e06cf78bd69e02c4847c7e2de..5b571b5452f9ffe1a9ee4f55374b49a9de541db8`, against base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`, the approved M1 plan/design, active package requirements, previous code-review findings, and surrounding tests.

## Remaining blocking findings

### P1 — Malformed spec provenance is discarded instead of signed

- The approved plan explicitly requires malformed JSON to retain a byte digest (`docs/superpowers/plans/2026-08-26-m1-typed-intent-evidence.md:206-208`), and the active package repeats that malformed bytes may be hashed for provenance but cannot count as mapped evidence (`engineering/changes/20260826-m1-typed-intent-evidence-rebuild-a4f882/requirements.md:16-21`).
- `extract_spec_metadata()` computes `raw_digest` at `trust-ci/src/adaptive_trust_ci/runner.py:219-221`, but `_metadata_document()` now raises for malformed JSON before the entry is appended. `JobRunner.process()` then replaces the entire binding with `spec_digest=None` and zero-spec coverage at `trust-ci/src/adaptive_trust_ci/runner.py:410-415`.
- The remediation test now asserts that loss (`trust-ci/tests/test_runner.py:300-305`), contradicting the plan instead of covering it. Direct reproduction on this head: malformed `{bad json` raises `SpecMetadataError` and yields no digest from `extract_spec_metadata()`.
- Preserve the deterministic composite digest containing `{path, raw_digest, semantic_digest: null}` while marking metadata/coverage invalid and producing a signed failed attestation. The malformed bytes must never be mapped, but their provenance must remain bound to the attestation.

### P1 — The multi-spec crash was replaced with an unapproved cross-spec ID prohibition

- The approved failure contract says duplicate IDs fail and, separately, that multiple changed specs are allowed and sorted deterministically (`docs/superpowers/specs/2026-08-26-m1-typed-intent-evidence-design.md:112-119`). The schema and local semantic validator scope `AC-*` uniqueness to each individual change spec; every spec also has its own `change_id` namespace.
- `trust-ci/src/adaptive_trust_ci/runner.py:218-230` introduces a new global `AC-*` namespace and rejects two otherwise valid changed specs that both use the conventional local ID `AC-001`, even when both criteria are fully mapped. This changes the previous exception into a deterministic failure but does not preserve the required multi-spec behavior.
- The remediation's own independent holdout test demonstrates the mismatch: `trust-ci/tests/test_change_spec_holdout.py:173-181` passes two full specs produced by `_valid()`, each containing `AC-001`, while runner tests deliberately reject the same ID shape at `trust-ci/tests/test_runner.py:207-216` and `308-322`.
- Reproduced on this head: two mapped changed specs with distinct change paths/change IDs and local `AC-001` values cause `SpecMetadataError: duplicate criterion ID across changed specs`. Keep within-spec duplicate rejection, but aggregate cross-spec coverage with an unambiguous/bounded representation (or unique-ID summary semantics) instead of inventing a global criterion namespace.

## Prior findings verified closed

- Malformed evidence values such as `{"test": []}` are now rejected by both the external holdout (`trust-ci/holdout.example/change_spec_validate.py:187-207`) and trusted metadata extraction (`trust-ci/src/adaptive_trust_ci/runner.py:117-136`); the runner produces a signed deterministic failure rather than counting them as mapped.
- Empty or dangling `observability.proves` is rejected by the schema, local semantic validation, holdout, and trusted extractor (`schemas/change-spec.schema.json:36`, `.grok-stack/adaptive_grok/spec.py:676-683`, `trust-ci/holdout.example/change_spec_validate.py:245-260`, `trust-ci/src/adaptive_trust_ci/runner.py:155-180`).
- The prior `AttestationPayload` constructor exception is no longer uncaught; metadata errors produce a signed failed result. The remaining multi-spec finding above concerns the new functional restriction, not the old crash.

## Verification observed

- Root focused suites (`test_change_spec`, `test_change_receipts`, `test_verification_doctor`) — PASS, 72 tests.
- Trust CI focused suites (`test_change_spec_holdout`, `test_runner`, `test_signing`) — PASS after invoking them with the repository's required `trust-ci/tests` import context; 44 tests total. An initial module-qualified invocation from repository root failed only because those tests import their local `_support` module by bare name.
- `python3 scripts/grok_verify.py --mode pr --no-record --json` — PASS, including gate-valid active spec, Ruff, Bandit, unit tests, and coverage.
- `git diff --check 0a4dd0a867c876f99a8fe3580c9f0d47c90e3105..HEAD` — PASS; the prior blank-EOF finding is fixed.

The security-sensitive evidence-value and signal-link repairs are materially improved, but the signed provenance and multi-spec contracts still do not match the approved M1 behavior.
