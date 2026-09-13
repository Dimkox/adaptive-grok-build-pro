# Test review — release-successor @ a1e977e

VERDICT: PASS

## 1. Baseline (worktree, HEAD a1e977e, clean)
`python3 -m unittest tests.test_project_state tests.test_manifest_package tests.test_structure tests.test_architecture_model -q`
Ran 156 tests in 10.099s — OK
Control: `git archive a1e977e` extracted to /tmp/mut/m0, same 4 modules: Ran 156 tests in 16.587s — OK (archive is byte-faithful, so mutation results below are attributable to the edits only).

## 2. Mutation bite-tests (all in /tmp copies, worktree untouched)
| # | Mutation | Result | Failing test |
|---|---|---|---|
| a | PROJECT_STATE published_release.tag v2.0.16 → v2.0.15 | BITE | test_project_state_has_independent_milestone_axes_and_truthful_facts `AssertionError: 'v2.0.15' != 'v2.0.16'`; plus test_manifest_package.test_published_zip_matches_immutable_release_record_and_embedded_manifest `'2.0.15' != '2.0.16'` (2 failures / Ran 70) |
| b | local_candidate.operational_activation → true | BITE | same project-state test, `True is not false` (1 failure / Ran 89) |
| c | drop prior_published_releases[2] (v2.0.13) | BITE | same project-state test, `2 != 3` (1 failure / Ran 14); prior[0]/[1] intact |
| d | README H1 → v2.0.15, VERSION left 2.0.16 | BITE | test_version_identity_matches_readme, `False is not true` (1 failure / Ran 19) |

Four expected-fails: the v2.0.16 record, the activation=false pin, prior length 3 and README/VERSION coupling are all locked.

## 3. Coverage sanity
`git show a1e977e --stat | grep '\.py'` → tests/test_manifest_package.py (±6), tests/test_project_state.py (110), tests/test_structure.py (±2).
Deviation from expectation: there is NO `__init__.py` in this commit — the `__version__` 2.0.16 bump landed earlier in 287b27a (parent chain a1e977e ← 969c4f6 ← … ← 287b27a). Outcome is stronger than expected: zero product .py changed; a1e977e is record/docs/tests only. VERSION=2.0.16 and .grok-stack/adaptive_grok/__init__.py=2.0.16 already agree.

## 4. Assertions that lost strength (all in the local_candidate block, none biting today)
- Deleted: `for key in ("reviewed_product_head","reviewed_product_tree","checked_head","merge_commit","tree"): assertIsNone(...)`. Three of those are re-pinned by equality, but `reviewed_product_head`/`reviewed_product_tree` are still present in PROJECT_STATE (both null) and now have NO assertion anywhere (`grep reviewed_product tests/*.py` = 0 hits). A future edit could stamp an unverified "reviewed" identity and nothing fails.
- Deleted: `for key in ("commit","tree"): assertIsNone(local["artifact_child"][key], "the artifact child cannot self-record its own identities")`. Correct for this successor record, but the anti-self-attestation invariant is now unenforced; no replacement guard exists (`grep 'self-record' tests/*.py` = 0).
- Semantics flips, not weakening: published/external_effect assertFalse→assertTrue; route_id/branch/pull_request/change_package null→concrete. The published claim stays bounded by the equality pin on `external_effect_scope == "github_repository_delivery_and_release_only"` and `assertFalse(operational_activation)`, which mutation (b) proves live.
- Pre-existing, not from this commit: `review_status`/`source_gate_status` unpinned before and after (0 refs in both revisions); the 4 assertions in (a)–(c) all sit inside one mega-test, so a failure reports a single name.

## Files
Read-only everywhere; writes only /tmp/mut/* copies and this file. Worktree /home/pall/grok-projects/adaptive-grok-build-pro-release-successor verified clean (git status --porcelain empty at start, no edits made).
