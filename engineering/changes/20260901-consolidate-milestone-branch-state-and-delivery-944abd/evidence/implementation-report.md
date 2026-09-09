# Implementation evidence — milestone state reconciliation

Route: `944abd96ddb3`
Original base: `1c06299894279a88b881defa3f19b004fa742223`
Current rebased main: `8ab4e57038dec2e07f01aaa0b207813a387358f4`
Scope: repository state/handoff only; no Trust CI implementation, roadmap checkbox, GitHub Actions, or external mutation.

## TDD evidence

RED command:

```text
python3 -m unittest tests.test_project_state -v
```

Result: four tests ran; schema version `1` versus required `2`, stale required check `6737355947c2`, and missing `work_inventory` produced two failures and one error. The pre-existing K16 graph was already green, proving the topology-preservation assertion was correctly characterized before documentation edits.

GREEN command:

```text
python3 -m unittest tests.test_project_state tests.test_structure -v
python3 scripts/grok_spec.py validate --change-id 20260901-consolidate-milestone-branch-state-and-delivery-944abd
python3 -m json.tool PROJECT_STATE.json
git diff --check
```

Result at the original implementation boundary: 15/15 tests passed; the change spec and JSON parsed. The bare working-tree `git diff --check` result was insufficient evidence for the committed PR range; the review repair below supersedes that hygiene claim.

## Delivered source behavior

- `PROJECT_STATE.json` schema version 2 separates implementation, review, stack integration, main delivery, and external gate for M0-M9 and binds the observation to current main.
- README and `START_HERE.md` agree on the current policy epoch/App and the M1-M4 delivery distinction; M5-M9 remain not started.
- Active/open/retained/superseded work is inventoried without branch cleanup or external writes.
- The README Mermaid topology remains exact K16 with 120 unique edges.

## Post-PR #19 integration refresh

- Fetched and rebased onto `origin/main` `8ab4e57038dec2e07f01aaa0b207813a387358f4`; the only conflict was `mistakes.md`, resolved by retaining both the delivered SEO branch's Chrome/optional-dependency lesson and this route's state-consolidation lesson.
- `PROJECT_STATE.json`, README, and `START_HERE.md` now record PR #19 as delivered non-milestone work at its exact merge commit, remove it from the open continuation set, and retain every other active/open/unresolved/superseded source.
- RED: two focused state/inventory tests failed because the snapshot still named main `1c06299894279a88b881defa3f19b004fa742223` and still listed PR #19 as open; the handoff consistency test then failed because current sections did not contain `8ab4e57038dec2e07f01aaa0b207813a387358f4`.
- GREEN at that boundary: the three focused regression tests passed, followed by `python3 -m unittest -v tests.test_project_state tests.test_seo_landing_side_project tests.test_structure` (26/26), change-spec validation, JSON parsing, and working-tree `git diff --check`. Exact candidate-range hygiene was added in the review repair.

## Blocking test-review repair

- RED: adversarial mutations of PR #17 base/head/status, M2/M3 commit evidence, and the Mermaid `GitHubApp` identity all passed the former assertions; the three new rejection tests therefore failed with “AssertionError not raised.”
- GREEN: literal milestone/inventory facts, local Git object/ancestry checks, and role-table-bound canonical graph identities reject those mutations. The focused state/structure/SEO suite passed 31/31; the full local suite passed 219/219; focused Ruff, change-spec validation, and JSON parsing passed.
- Exact-range defect: the former committed range exposed eight trailing-space lines across three historical analysis reports. Only those spaces were removed; the fourth report received only the separately reviewed absolute-path-to-repository-relative wording repair.
- Candidate hygiene: after staging the uncommitted repair, `git diff --check`, `git diff --cached --check origin/main`, and `git diff --check origin/main` pass. As required by the no-commit boundary, `origin/main...HEAD` still names the pre-repair commit and continues to reproduce the old failure until the staged candidate is committed; no exact-HEAD PASS is claimed.

## Trust CI exact-checkout repair

- External failure at exact head `718ec4d58ef37e2a77e8cc4423c37ae54a3737cf`: repository holdout and external holdout passed, while `root-unittest` failed because mandatory `git cat-file` could not resolve M2 commit `022411b05924618cfde0cb97b8c8aff4955e6013` in the isolated single-branch checkout. A local `--no-local --single-branch` clone reproduced the same failure with exit 1.
- RED: the new self-contained merge-parent test failed because `PROJECT_STATE.json` did not record the accepted parents for merges `c23fd49f80c7d1c74ca3393b6079a74f251a72d8` and `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`.
- Repair: durable state now records both exact ordered parent pairs and tests validate their literal and milestone relationships. Git-object corroboration remains an additional local path only when every named object exists; the durable proof always runs and its adversarial ancestry mutation remains mandatory.
- GREEN: the isolated single-branch clone still could not resolve `022411b…`, yet all 10 state tests and the full 220-test root suite passed without a fetch. The local full root suite also passed 220/220; focused lint/spec/JSON and exact diff checks follow the final evidence update.

## Remaining gates

Route-selected independent code, test, and security reviews plus fingerprint-bound verification/receipts remain pending outside this write-owner implementation handoff. The App-owned exact-head check and any signed approval are external merge authority and are not claimed here.
