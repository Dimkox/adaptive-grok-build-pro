# Test plan — Fix issue #167: select focused static SEO landing verification for landing-only changes while retaining full PR verification for runtime, contract, Trust CI, package, architecture, or workflow changes, with regression tests.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | One landing directory plus one named focused test selects focused mode | `test_static_landing_scope_accepts_one_explicit_focused_contract`; focused execution test |
| P0 | Mixed/unknown/excluded paths, malformed raw values, missing or multiple tests, invalid inventory fail closed | selector regression matrix; exact reason-code assertions |
| P0 | Multiple landing directories fail closed | `test_static_landing_scope_rejects_multiple_landing_directories` |
| P0 | A focused test for another landing is rejected | `test_static_landing_scope_rejects_mismatched_focused_test` |
| P0 | Deleted, renamed, copied, or ambiguous Git status fails closed before contract execution | status-provenance regression matrix |
| P0 | Empty/non-unittest contract fails before subprocess discovery | `test_focused_landing_contract_rejects_empty_file_before_discovery` |
| P0 | Rejected focused scope does not execute a contract subprocess | `test_rejected_focused_scope_does_not_execute_contract_subprocess` |
| P1 | Exact focused workflow command is allowlisted; arbitrary flags are rejected | workflow artifact regression |
| P1 | `--mode pr` remains the full path for an eligible landing inventory | `test_pr_mode_keeps_eligible_landing_inventory_on_full_path` |

## Automated checks

- Unit: targeted verifier/workflow/status cases; 2026-09-23 result: 17 focused verifier tests, 2 Git-status tests, and 1 workflow allowlist test passed (`Ran 20 tests in 6.529s`, exit `0`).
- Integration: not run; no integration or external-system change.
- Contract: focused mode invokes exactly one named landing contract only when scope and status provenance are eligible; rejected scope invokes none.
- E2E: not run; landing content is unchanged.
- Static analysis: full `python3 scripts/grok_verify.py --mode pr` was attempted after this repair, reached factory/PostgreSQL and security checks, then was interrupted by the execution harness after approximately 15 minutes (exit `130`). It still requires a complete uninterrupted run; no PASS receipt is claimed.

## Manual checks

- Safe CLI smoke rerun 2026-09-23: `python3 scripts/grok_verify.py --mode focused-static-seo-landing --no-record --json` → exit `1`; `git-diff-check` PASS, `scope-selection` FAIL (`out-of-scope-or-invalid-paths`), `source-stability` PASS, landing contract NOT RUN, broad suite NOT RUN.
- Required independent reviews: active-route `code_reviewer` and `test_reviewer` reports both PASS; reports are stored under `evidence/`.
- Final verification must be rerun after review reports and any final package edits so the receipt binds to the final tree fingerprint.
