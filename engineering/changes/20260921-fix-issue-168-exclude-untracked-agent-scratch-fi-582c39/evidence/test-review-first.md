# Independent test review — issue 168

**Recommendation: PASS for the bounded product change and its test adequacy. No blocking findings.** This is a local test review, not a fresh final verification receipt or merge authority.

Reviewer: route-selected `test_reviewer` (`fingerprint_test_reviewer`), independent of `fingerprint_integration_implementer`; 2026-09-21. Route `582c39d6afb6`. Reviewed HEAD `5adc4f853741ced0f1332fcdb2d5e5d95446bed4` against frozen PR170 base `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`, in `/home/pall/grok-projects/adaptive-grok-build-wave-fingerprint`.

Read the bootstrap/state, contract, active route, selected role, applicable skills, change specification, design, test plan, implementation report and analysis. Inspected the actual utility/test diff plus receipt validation, verification source stability and fixture support. Fetched remote refs. No product file was changed and no test, lint, compiler or Docker workload was started by this reviewer; coordinator-owned recorded executions were inspected directly under the serialized-test constraint.

## Acceptance coverage

| Requirement | Concrete evidence inspected | Assessment |
| --- | --- | --- |
| AC-001: scratch create/edit/remove is stable | `test_untracked_scratch_create_edit_remove_does_not_change_binding` uses a committed temporary Git repository, asserts the changed-path inventory and fingerprint, and includes a nested filename containing spaces and a newline. | Adequate positive control for exactly top-level `.qwen/tmp/`. |
| AC-002: tracked ownership overrides filtering | The matrix exercises nine scratch/legacy-noise paths across unstaged/staged edits and deletions. Separate cases cover immediate staging, force-added ignored scratch, both rename endpoints, base-relative deletion, and staged deletion recreated as untracked whose replacement bytes subsequently change. | Adequate protection against index-only or unconditional-prefix filtering. |
| AC-003: configuration/source/lookalikes remain bound | Configuration under `.qwen`, `.codex`, `.agents` and `.claude`, ordinary new source, `.qwen/tmpfile`, `.qwen/tmp-config.json`, a nested `.qwen/tmp/`, the exact `.qwen/tmp` filename, and `.qwen/tmp-link/` are checked first untracked and then as tracked edits. | Assertions cover both changed-path inclusion and fingerprint inequality. |
| AC-004: uncertain tracking includes candidates | Tests simulate failed, timed-out and malformed index inventories and failed tracked diffs. Real non-Git and unborn repositories retain scratch; a staged runtime file removed from the unborn worktree remains in the inventory and changes the fingerprint. | Error results cannot authorize the new exclusion; absence of HEAD is not treated as proof of untracked ownership. |
| AC-005: receipt/source-stability integration | The new receipt case proves create/edit/remove scratch freshness, then mixes scratch with a tracked VERSION edit and requires the exact stale-repository gap while preserving the original receipt bytes. Existing `test_verify_does_not_receipt_checks_from_an_older_fingerprint` mutates a real product file during verification and requires a failing source-stability result and absence of the verification receipt. | Both receipt validation and verifier refusal are exercised through their real shared fingerprint consumer. |

Existing untracked runtime/cache exclusions have an explicit stability control. Tests use real temporary Git repositories for ownership transitions; mocks are confined to deliberate Git failure results. The tracked-path matrix uses `finally` cleanup so expected RED assertions do not cascade into fixture commit errors. The implementation keeps HEAD binding in `tree_fingerprint`, retains tracked diff paths before applying noise exclusions, and uses NUL-separated results with rename detection disabled to retain both endpoints. No receipt format or external authority behavior changes are present in the reviewed product diff.

## Execution evidence inspected

Raw records are under `/home/pall/.cache/agbp-run/issues-wave-20260921/fingerprint/`:

- `red-clean.log`: 10 tests in 4.408 seconds, 40 assertion failures, zero error headings. Failures cover untracked scratch/receipt churn, tracked legacy-noise omissions, rename provenance, failed inventory and unborn missing staged content. The failure shapes agree with the inspected baseline; this reviewer did not rerun the baseline.
- `green.log`: 12 tests in 6.163 seconds, `OK`. The implementation record identifies the exact focused command and explains the two subsequently added characterization cases for recreated staged deletion and failed diff inspection.
- `integration.log`: 92 tests in 222.691 seconds, `OK`, for the receipt and verification/doctor modules.
- `verify-initial-meta.json` and `verify-initial.json`: `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, exit 0, 07:35:39–07:43:53 UTC on the reviewed HEAD. Report route is `582c39d6afb6`, profiles are base/contracts/integration, and fingerprint is `f4ebf05ae78b2b60901341ecd21b7ac9ccfdbb820a1ccff72560318cf895b4cd`. The report contains 15 passing checks and one workflow-artifacts skip because it is not configured. Root tests report 797 passed and 1149 passing subtests; source stability, factory unit and PostgreSQL checks report pass. The pilot suite records its explicit pinned-local-sandbox skip.

Evidence content hashes, for later archival without silently substituting records:

| Record | SHA-256 |
| --- | --- |
| `red-clean.log` | `ed89917d4f8fb66302b1ce260bd9a978ffa651c0f1f61dcc8771c8c823ac377b` |
| `green.log` | `91c237e574eca5386c9339675cb9b63ed3889489995334f4e1713a8f71d4f23e` |
| `integration.log` | `cf48315fa3bffc72e89b6a7c344c847ce953b251c264b925b7a800f5ff8d9911` |
| `verify-initial.json` | `4b9721cd25444ba908d53fd0b41b33db64db452397a9014aebb638038258ca08` |
| `verify-initial-meta.json` | `2a6802a2c3d7760dde3255b8ccb4ae13d86c65ee573c29effa3379fc3f9b646e` |

The three reviewed product files have no worktree diff against the reviewed HEAD. Their SHA-256 values are:

- `.grok-stack/adaptive_grok/util.py`: `37b1fd4754f091761d9d4e55f1948b9a927b3cc526cdf439f546ea8999460d7a`.
- `tests/test_util_fingerprint.py`: `ae27d2a91f532cd1b9c2460a4cf5222ee93abf3a2779a63ac0312b1ec7c82419`.
- `tests/test_change_receipts.py`: `a4b3d0bc98689e10bc17f60c417692d651fd0abcde1207cefa5a852afdf828d5`.

## Limits and delivery binding

Timeout coverage models the existing runner's nonzero/124 result; it does not wait for a real Git process timeout. There is no separate physical index-file-removal scenario; inventory failure and staged files absent from the worktree are covered, and the inspected diff provenance preserves tracked deletions absent from index membership. The scoped repair does not claim to recover paths from every pre-existing failed Git enumeration command.

At review start, only the change package state transition was dirty. `grok_status.py` correctly reported stale verification/governance binding after that transition and missing review receipts. This report adds further evidence content, so the initial full-gate fingerprint must not be presented as current final-tree evidence. The coordinator must bind final verification/review receipts after all repository changes; any subsequent product change requires renewed review. External exact-head Trust CI and applicable approval requirements remain separate.
