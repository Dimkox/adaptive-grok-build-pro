# Test review — M0.3 characterization (`test_m0_invariants`)

Reviewer: `test_reviewer` (read-only). Route `54313e326a39`. Change `20260824-user-query-давай-далее-user-query-54313e`.

## Scope

Inspected `trust-ci/tests/test_m0_invariants.py` against pinned docs:

- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`
- `engineering/runbooks/trust-ci-activation-report.md`
- `README.md` current-state
- `decisions.md` 2026-08-24 M0.3 entry
- package `test-plan.md`

No product code edits. No merge, push, or GitHub API from this review.

## What the tests actually do

Both `test_m0_2_webhook_stage_closed_on_github_delivery` and `test_m0_3_main_is_app_bound` only `Path.read_text` on tracked markdown (and sibling tests read compose/API/worker/holdout). Imports are `unittest` and `pathlib`. No `requests`/`httpx`/`urllib`/`subprocess`, no env or PEM loads. Forbidden-key assertions look for PEM *markers in docs*, not files under `.env` or key stores.

## Pin vs live docs

| Claim | Plan / report / README / decisions | Test |
| --- | --- | --- |
| M0.3 boxes protect / other-actor / disable 340420982 / supersede / fill-report | `[x]` lines 47–51 | `assertIn` those exact `- [x]` strings |
| Mark PR ready | `- [ ] Mark PR ready; merge only through the live App-owned check` | `[ ]` required; `[x] Mark PR ready; merge` forbidden |
| M0.2 still “Do not protect `main`” + bind follows | line 41 `[x] **Do not protect \`main\`** in M0.2 (M0.3 bind follows)` | `test_m0_2` requires `**Do not protect \`main\`` and `M0.3 bind follows` — history, not “currently unprotected” |
| Activation report | `\| main protected \| true \|`, `\| Protection app_id \| 4694114 \|`, `340420982` + `disabled_manually` | exact cells |
| README | L11 live check + App 4694114 + protected main; PR #2 exception revoked; no “App-owned check is not live… PR #2 bootstrap” | `assertNotIn` that bootstrap sentence; current-state slice `assertNotIn` “main is unprotected” |
| decisions M0.3 | heading `2026-08-24 — M0.3 bind main; revoke bootstrap exceptions`; `4694114`; `adaptive-trust-ci/verified@6737355947c2`; “Revoke” | substring after `M0.3 bind main` (800 chars) |

Reverting current-state to unprotected `main` (`false` in the report, or “main is unprotected” in README current-state) or restoring the PR #2 bootstrap sentence fails `test_m0_3`. Dropping the historical M0.2 “Do not protect” line fails `test_m0_2` only — that is intended characterization of the closed M0.2 stage, not a standing unprotected-main order.

## Non-claims (required)

Tests do **not** assert PR #5 merged, `mergeable_state`, or Check Run `success`/`completed`. `decisions.md` still says PR #5 unmerged / `action_required`; the test only requires that entry exist with app_id, epoch check name, and “revoke”. Mark-ready staying unchecked is the merge-gate pin.

Package test-plan P0 “PR #5 not merged” is **not** a dedicated unittest assertion (report still says `5 (draft)`). Residual gap: docs could drop “draft” without failing `test_m0_3`. Does not over-claim merge.

## Verification evidence (assigned)

Operator already reported:

- `python3 -m unittest trust-ci.tests.test_m0_invariants` → 14 tests OK
- `python3 scripts/grok_verify.py --mode pr` → PASS

This review did not re-run those commands. Count in the file is 14 `test_*` methods, matching 14 OK.

## Adequacy

Characterization is tight for M0.3 bind language, App ID, disabled workflow wording, README current-state, and M0.2 historical protect constraint. Tests stay offline and key-safe. They would fail a bootstrap/unprotected revert. They do not treat Check Run green or PR #5 merge as done.

PASS
