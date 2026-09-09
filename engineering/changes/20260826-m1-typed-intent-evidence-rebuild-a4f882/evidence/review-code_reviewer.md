# Code review — M1 typed intent and evidence

Verdict: **BLOCKED**

Reviewed exact head `62b9c601de980b1e06cf78bd69e02c4847c7e2de` against base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`, the approved M1 design/plan, the active typed spec, and the surrounding local/Trust CI implementations.

## Blocking findings

### P0 — Independent holdout accepts malformed evidence references and the trusted runner counts them as mapped

- `schemas/change-spec.schema.json:13-20` defines every evidence value as a bounded string (and constrains receipt values to an enum), but `trust-ci/holdout.example/change_spec_validate.py:173-179` checks only that an evidence item is a one-key object with a supported key. It never validates the value type, value bounds, receipt enum, test/reference pattern, or empty string.
- `trust-ci/src/adaptive_trust_ci/runner.py:118-123` repeats the same shallow condition and therefore records malformed references as mapped criterion coverage.
- Reproduction on the reviewed head: calling `_validate_document()` with `{"test": []}` and `rollback.maximum_steps = 0` prints `holdout accepted malformed evidence and rollback`; the trusted holdout does not reject either schema violation.
- This defeats the independent trust boundary: pull-request-controlled local validation/tests can be changed by the PR, while the external holdout and signed metadata would still accept/count a non-reference such as `{"test": []}` as evidence. Duplicate the critical bounded value validation in the holdout and require the runner coverage extractor to count only references that satisfy the trusted contract. Add an exact-SHA holdout regression test for malformed values, not only malformed JSON.

### P1 — Multiple changed specs can make attestation construction raise instead of producing a signed failed result

- `trust-ci/src/adaptive_trust_ci/runner.py:129-154` aggregates bare `AC-*` IDs across specs and preserves duplicate unmapped IDs. Two changed specs may each legitimately use local ID `AC-001`; when both are unmapped, extraction returns `criterion_total=2`, `criterion_mapped=0`, and `unmapped_ids=["AC-001", "AC-001"]`.
- `trust-ci/src/adaptive_trust_ci/models.py:38-40` deduplicates the IDs and then requires the deduplicated length to equal `total - mapped`, so `AttestationPayload(...)` raises `ValueError`. `JobRunner.process()` constructs that payload at `trust-ci/src/adaptive_trust_ci/runner.py:376-394` without converting this into a deterministic failed attestation.
- Reproduced on the reviewed head: `extract_spec_metadata()` returned the duplicate list above, and `AttestationPayload(...)` failed with `ValueError: criterion_coverage unmapped IDs do not match counts`.
- The design explicitly allows multiple changed specs. Make unmapped identities unambiguous (for example, path-qualified records under a versioned metadata contract) or define a bounded representation whose cardinality remains valid across specs, then cover the two-spec failure path through `JobRunner.process()`.

### P1 — Gate validation accepts a production signal that proves no current objective

- `schemas/change-spec.schema.json:36` permits an empty `observability[].proves` array and accepts any syntactically valid `OBJ-*` value.
- `.grok-stack/adaptive_grok/spec.py:593-650` validates that a criterion's `production_signal` resolves to a signal ID, but never checks that each signal's `proves` entries resolve to the spec's sole objective or that a referenced signal proves at least one objective. The independent holdout has the same gap at `trust-ci/holdout.example/change_spec_validate.py:156-179`.
- Reproduced on the reviewed head by changing `SIG-001.proves` to `["OBJ-999"]`: gate `validate_spec()` returned `ok=True` while `AC-006`-style signal evidence could no longer prove the declared objective.
- Require non-empty `proves`, resolve every entry to `objective.id`, and independently enforce the same critical relationship in the holdout. Add regressions for empty and dangling `proves` arrays.

## Verification observed

- `python3 -m unittest tests.test_change_spec tests.test_change_receipts -v` — PASS, 30 tests.
- `python3 scripts/grok_verify.py --mode pr --no-record --json` — PASS; one gate-valid active spec, Ruff/Bandit/unit/coverage checks passed.
- `git diff --check 0a4dd0a..HEAD` reports one pre-existing-in-this-diff whitespace issue in `evidence/analysis-docs_researcher.md` (`new blank line at EOF`); the repository verifier only runs `git diff --check` for working-tree changes and therefore did not catch committed-range whitespace.

The overall structure is maintainable and the legacy signed-payload preservation is directionally correct, but the independent evidence boundary is not yet strict enough for a passing M1 review.
