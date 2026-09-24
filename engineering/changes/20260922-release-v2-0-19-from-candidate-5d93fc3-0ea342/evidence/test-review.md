# Test review — v2.0.19 release sync

## Verdict

**PASS — the targeted PR-head provenance regression is repaired.** The candidate now binds every post-v2.0.18 landing PR number to its reviewed exact head SHA. Corrupting PR #111's recorded head to another valid-looking 40-hex value is rejected by the focused test.

This PASS covers the release-sync test change at committed HEAD `e95ada33501461cf848966f0bb4b68148ab065fd` plus the uncommitted `tests/test_project_state.py` patch. The pre-report candidate fingerprint was `928ecc05ac63a60bf679653c0580998c83e35b8bbc5b8a15995050684b01f195`; `tests/test_project_state.py` SHA-256 was `1dd4bf853a7c3039c533f320ba935edf7bb23a4c40a52ab49a5b2131b7514072`. Persisting this report changes the fingerprint, so final verification and receipt recording must use the resulting frozen tree.

## Concrete findings

- `POST_V2018_PR_HEADS` contains exact heads for all 15 expected PRs, and `test_post_publication_landing_and_archived_candidate_are_recorded` asserts each row's head against that map before its format checks.
- The previously surviving mutant is now killed. In scratch `/tmp/agbp-test-review.lHnKoW/repo`, PR #111's delivered-history head was changed from `176c3c6331241929c5e9091c93833c04d0d010d2` to forty zeroes. The focused test exited 1 at line 469 with the expected exact-value mismatch.
- GitHub's read-only PR metadata confirms PR #111 head `176c3c6331241929c5e9091c93833c04d0d010d2`, squash merge `d8b396cafc0c5953f2b419a29ce7eac292138d27`, and merge time `2026-09-16T15:58:23Z`.
- GitHub check run `104861527743` is completed/success for that exact head, named `adaptive-trust-ci/verified@06ecf1c875bc`, owned by App ID `4694114`.
- The two in-tree representations of the 15 predecessor rows currently agree for PR number, head, merge commit, merge time, and check-run ID. The observed-main/source boundary also agrees with PR #185's merge SHA `130ce4a42d9f9bbd1b56772d40b19ae530283205`.
- Exact-SHA boundaries remain fail-closed: v2.0.19 artifact and publication identities remain pending/null, and this local review does not replace the future App-owned check on the exact release-sync PR head or the later artifact-child head.

## Commands and results

```text
python3 -m unittest tests.test_project_state.ProjectStateTests.test_post_publication_landing_and_archived_candidate_are_recorded
Ran 1 test in 0.002s — OK

python3 -m unittest tests.test_project_state
Ran 15 tests in 0.194s — OK

git diff --check
exit 0, no output

gh pr view 111 --repo Dimkox/adaptive-grok-build-pro --json number,headRefOid,mergeCommit,mergedAt,state
MERGED; head/merge/time exactly match PROJECT_STATE.json

gh api repos/Dimkox/adaptive-grok-build-pro/check-runs/104861527743 --jq '{id,name,head_sha,status,conclusion,app_id:.app.id,completed_at}'
completed/success; exact PR #111 head; expected policy check name; App ID 4694114
```

Mutation probe setup reproduced the reviewed candidate in a mode-0700 private scratch directory with the same HEAD and pre-mutation fingerprint. Exact mutation command:

```text
sed -i '971s/176c3c6331241929c5e9091c93833c04d0d010d2/0000000000000000000000000000000000000000/' /tmp/agbp-test-review.lHnKoW/repo/PROJECT_STATE.json
python3 -m unittest tests.test_project_state.ProjectStateTests.test_post_publication_landing_and_archived_candidate_are_recorded
```

Result: `FAILED (failures=1)`, exit 1; mutant **killed**. The reviewed source remained unchanged: HEAD and fingerprint after the probe were still `e95ada33501461cf848966f0bb4b68148ab065fd` and `928ecc05ac63a60bf679653c0580998c83e35b8bbc5b8a15995050684b01f195` (`reviewed-tree-modified: no`).

## Limitations and required next gate

The new regression assertion binds exact head SHAs, which is the defect under review. It does not independently hard-code merge SHAs, merge times, check-run IDs, or enforce equality between the duplicated predecessor collections; those values were inspected and currently agree. The existing full verification receipt predates this test patch and is stale. Commit/freeze the patch and reports, rerun `python3 scripts/grok_verify.py --mode pr`, and record fresh fingerprint-bound reviews before any PR delivery action.

## Current protected-main rebind review

The preceding report is historical and is not a receipt for the current candidate. The current release-sync rebind was inspected read-only at:

- Base: `7650a5e12aad55bdcf730cd37e2faf162bec0486`
- HEAD: `1498273fb9866e7b388f885518555a795e8bdd2f`
- Tree fingerprint before this report section: `90704a206960486eb4b34feffcb9828dbc4993c67d8a57102daebb5bf103aa14`
- `reviewed-tree-modified: no`

`python3 -m unittest tests.test_project_state tests.test_structure` passed (36 tests), and the broader focused release set passed (92 tests). A parity probe found exactly 20 landing rows in both state representations, unique exact head SHAs, present merge objects, and #193's merge equal to observed `main=7650a5e…`; an in-memory head mutation was rejected without changing the worktree. Final verification and receipt binding remain pending until this section is committed.
