# Test review — #117 structured review evidence (re-review 2)

## Verdict

**BLOCKED — narrow regression coverage remains incomplete**

Reviewed the updated implementation and tests in `/tmp/adaptive-fix-evidence-claims`, route `a8759f7ed815`, against the revised change spec and prior review findings. The implementation now addresses both prior findings; the remaining issue is exact-case regression coverage below.

## Re-review of prior blockers

- **Claim statement changes:** `_validate_revision()` derives changes by comparing all claim fields per stable ID, then requires both declared ID arrays to equal the derived IDs. `test_revision_derives_statement_and_status_changes_and_rejects_removal` changes the source statement without listing `SRC-001`, while listing a different changed claim, and asserts rejection. This covers the unlisted statement case.
- **Claim membership:** linked revisions reject removals. The same test removes a predecessor claim and asserts rejection. Added claims are derived by the implementation, but the test only adds `EXEC-C` while declaring it changed; it does not prove that an omitted added ID is rejected.
- **Status:** implementation derives `changed_report_fields` exactly from predecessor/current status and requires changed claims on a status transition. Tests cover a status transition with the field listed but without changed claims (rejected), and a transition with both field and fresh claim (accepted). No test omits `changed_report_fields` while changing status, so the precise unlisted-status regression remains untested.
- **Probe shape/schema:** validation now accepts only the named `adaptive_grok.architecture.unsupported_schema` v1 probe with object input containing an object `schema`. Tests accept that object shape, reject a JSON string in `input.schema`, and reject an unknown schema ID. This covers the concrete string-vs-object and unknown-schema cases.

## Remaining regression gap

Add explicit negative cases for (1) a pass/fail status change with `changed_report_fields: []`, and (2) a predecessor-absent claim added in the new revision while omitted from `changed_claim_ids`/`fresh_evidence_claim_ids`. The implementation currently appears to reject both, but the requested fail-closed behavior should be locked by tests before this review passes.

## Commands run

- `python3 -m unittest tests.test_review_evidence` — PASS, 8 tests.
- `python3 -m unittest tests.test_change_receipts tests.test_hooks` — PASS, 58 tests.
- `git diff --check` — PASS.
