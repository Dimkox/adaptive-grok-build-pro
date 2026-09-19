# Code review — #117 structured review evidence

**Result: FAIL — one requirement-level finding blocks approval.**

Reviewed the current working diff and surrounding receipt flow in `review_evidence.py`, `receipts.py`, and `grok_review.py`; focused tests covered `tests.test_review_evidence`, `tests.test_change_receipts`, and `tests.test_hooks` (65 tests, all pass). `python` was not installed under that command name; rerunning via `python3` succeeded. No files outside this review report were changed by the review.

## Finding F1 — revision validation does not derive the changed-claim set

**Severity: High / blocks AC-005.** In `.grok-stack/adaptive_grok/review_evidence.py:275-280`, the validator checks that declared `changed_claim_ids` are unique IDs in the new report, but never derives which claims actually changed. It then compares evidence payloads only for the IDs the author chose to list (`:300-311`). It does not compare all predecessor/current claims for statement, type, evidence, addition/removal, or status changes. As a result, a contradictory claim can be edited without being listed, while an unrelated claim is listed as changed to satisfy the non-empty requirement.

I reproduced this with a predecessor containing source claim `SRC-A` and execution claim `EXEC-B`: the next report changed `SRC-A.statement` to a contradictory conclusion while leaving its citation unchanged, changed `EXEC-B.argv`, and declared only `EXEC-B` changed with fresh evidence. `validate_review_report` accepted the report. This bypasses the stated requirement that contradictory revisions trigger re-derivation, and lets authors selectively omit a changed claim from the revision audit.

The validator should derive a canonical diff by stable claim ID and report-level status, require the declared changed set to equal (or conservatively contain) every material change, reject silent claim removal/addition unless explicitly modeled, and require fresh evidence for each changed material claim. Add regression cases for an unlisted changed statement, a removed claim, and a report status transition. The current positive and negative revision test only checks a listed claim with repeated/changed evidence, so it misses this path.

## Other reviewed boundaries

- Report, citation, and cwd reads use descriptor-relative `O_NOFOLLOW` traversal rooted at the canonical repository directory; absolute/traversal paths, symlinks, non-regular files, and oversized content are rejected. This closes the prior `root / absolute_path` escape.
- `write_receipt` validates the report before recording a passing review receipt, stores its digest and summary, and `validate_evidence` revalidates both and detects changed/deleted report bytes.
- Execution records are intentionally marked `self_reported_unverified`; the code and `docs/review-report-v1.md` do not claim local JSON proves execution, reviewer identity, clean-clone status, semantic truth, or Trust CI authority. This is an appropriate boundary for repository-local evidence.
- One migration consideration: existing prose/Markdown reports (including historical plan examples) no longer qualify for passing review receipts. The package explicitly says legacy prose is rejected, so this is consistent with the selected contract, though users will need structured v1 reports for future durable receipts.

## Verification performed

```text
python3 -m unittest tests.test_review_evidence tests.test_change_receipts tests.test_hooks
Ran 65 tests in 44.643s
OK
```

The review did not run the long full PR verification gate.
