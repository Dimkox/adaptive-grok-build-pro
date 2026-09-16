# Review response — SR (v2.0.17 published-release successor)

Reviewed object: `8d45b31479529a680ddec10057d8fe64ca941c30`. The dispositions below were applied in
the follow-up commit on this branch, so the pull request opens on the corrected tree and the receipts
bind to that final head.

Before acting on any finding I re-derived it in this worktree. Every row marked **confirmed** was
reproduced by command; nothing was accepted on description alone.

## `review-release.md` — PASS, no Critical, 7 Important, 5 Minor

| # | Finding | My check | Disposition |
| --- | --- | --- | --- |
| 1 | `packages/README.md:3` still certified v2.0.16 as the latest published release — and SR is the commit that made that sentence false | `sed -n '3p'` printed the v2.0.16 sentence | **Fixed.** Now names v2.0.17, `2026-09-16T01:17:14Z`, target `c86b1a1…` |
| 2 | ROADMAP identity block contradicted itself: line 37 still said `latest published release: v2.0.16, tag target 969c4f65…` while line 42 said v2.0.17 | `awk 'NR==36||NR==37'` showed the contradiction | **Fixed.** Line 37 names v2.0.17/`c86b1a1…` and keeps the superseded v2.0.16 target as history; line 36 observed SHA advanced to `c86b1a1…` |
| 3 | Four "observed main" pointers still named `78082a2…` after SR moved `observed_main_sha` | `grep -n 78082a2… README.md START_HERE.md GROK_BUILD_HANDOFF.md` → three live doc hits | **Fixed** in all three (README table row, START_HERE snapshot, HANDOFF item 2). The two remaining `78082a2…` mentions in tests are the intentional `V2017_SOURCE_BASE`/`source_parent` pins |
| 4 | `trust_ci.last_success` was not advanced, its prose was internally false (claimed PR #98 sits in the landing rows — it does not), and its `check_url` pointed at PR #94's run `104591923631` | dumped the object: `pull_request: 98` with `check_url …/runs/104591923631`, and the landing rows list is `81,82,83,85,88,89,90,91,93,13,64,94` | **Fixed.** Now PR #99, head `bbc5cdd9…`, merge `c86b1a1…`, run `104621989321`, attestation `b9510589-…`, correct `check_url`, and a `record_scope` that says what is and is not in the ledger |
| 5 | The "release-chain commits are not landing rows" convention lived only in one prose field, and row #81 contradicts it as a universal rule | #81 is indeed a successor of the *previous* chain | **Reworded, not deleted.** The scope now states the rule for this chain (#98 R, #99 A, SR) and explains why #81 legitimately stays in the list, instead of asserting a universality the ledger breaks |
| 6 | Deferred ROADMAP PR inventory still listed #13/#64 open and #15 open; no v2.0.17 delivery row | the inventory line named `9bdffde9…` "remains open" and `33c5f2af…` "is open" | **Fixed.** Rewritten from re-derived facts: #13 → `4383115…`, #15 closed-unmerged and in `retained_unresolved`, #33 the only open PR, #64 → `01d64e5…`, plus #94/#98/#99 rows with their merges |
| 7 | The `feature/workflow-artifact-adapters` retention gate was worded as pending although SR satisfies it | SR's record names the #93 lineage (`280cbff…` in predecessors and in the entry itself) | **Fixed** — and deliberately *not* deleted. Removal of the branch and its worktree is an irreversible cleanup that needs its own explicit approval, so the entry now says the condition is met and removal stays a separate approved step |
| 8 | `PROJECT_STATE.json` canonical-dump regression introduced by this commit (29 drift lines vs 2 at base) | measured: `raw == json.dumps(..., indent=2)` → base 2 drifting lines, SR 29 | **Fixed** by writing the file from the parsed structure with `indent=2, ensure_ascii=False`; 29 lines re-indented, content verified identical by re-parse, then re-validated by the test modules |
| 9 | Dead candidate-phase branch left in `tests/test_project_state.py` | read the `if/else` at 404-409 | **Fixed.** `source_parent`/`source_parent_tree` are now asserted unconditionally, which is stronger than the branch that could never run |
| 10 | Release-sync ledger left two boxes unticked that PR #98 had satisfied | `grep '^- \[ \]'` on that `tasks.md` | **Fixed** with the actual verification outcome and receipt fingerprints |
| 11 | Candidate-worded labels survived inside the published record | `post_v2_0_16_landing.status == "landed_in_2_0_17_candidate"` | **Fixed** to `landed_in_v2_0_17_release`, test pin moved with it. `current_unreleased_change.scope` keeps its R-era wording because it describes what R authored — the reviewer agreed those lines "are true of it" |
| 12 | AC-001 credited tests with assertions they did not contain (`tag_object`, `published_at`, GitGuardian) | `grep -n "tag_object" tests/*.py` → no hits before this change | **Fixed by making the claim true rather than downgrading it:** the test now asserts `tag_object`, `published_at`, `merged_at` and the GitGuardian conclusion and run id, and AC-001 says which layer proves which field |

## After the follow-up

`python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package
tests.test_change_spec` → **Ran 119 tests, OK**.

## Not taken from the review

The reviewer's §A positive observations were re-checked rather than copied: tag peel, release asset
digests, the App check summary line carrying the attestation, the sidecar byte layout, and the
historical immutability of `milestones`, `integrated_stack`, frozen migrations and the older prior
releases. Raw command output is kept in `command-evidence.txt` in this directory so a later reader
can see what the claims rest on.

## `review-security.md` — PASS, 0 Critical, 0 Important, 4 Minor

Same caveat as above: this reviewer examined `8d45b31`, before the follow-up commit.

| # | Finding | My check | Disposition |
| --- | --- | --- | --- |
| 1 | Minor — `START_HERE.md:7` and `GROK_BUILD_HANDOFF.md:304` still named `78082a2…` while the commit advanced `observed_main_sha` | reproduced with `grep -n 78082a2…` before the follow-up | **Already fixed** in the follow-up commit (same defect as release-review #3), together with `README.md:11` and `DARK_FACTORY_ROADMAP.md:36` |
| 2 | Minor — the archived v2.0.16 block was spliced in with 2-space indentation, breaking the file's canonical dump | measured: 29 drifting lines at `8d45b31` versus 2 at base | **Already fixed** by re-serialising `PROJECT_STATE.json` with `indent=2, ensure_ascii=False` and proving the parsed content identical (release-review #8 is the same defect) |
| 3 | Minor — the supplied `command-evidence.txt` contained two `cut: invalid decreasing range` errors, so the capture pipeline was partly broken | reproduced: my `cut -c1-0` was nonsense; the surviving digests were well formed and the reviewer recomputed both independently | **Fixed.** The evidence file is regenerated with a working pipeline (`git cat-file blob HEAD:… \| sha256sum`) and contains no error text; the digests are unchanged |
| 4 | Minor — `SIG-001`'s exact-head check cannot exist at evidence time (only PR #33 was open) | confirmed: this successor has no pull request yet | **Accepted as a status fact.** The pull request for this branch is opened next, and merge authority is its exact-head App check; no local receipt substitutes for it, and nothing in the package claims otherwise |

The reviewer's positive observations were re-checked rather than adopted: `operational_activation`
false in both the release record and `local_candidate`, the peeled tag resolving to the recorded merge,
GitHub's own asset digests equalling the tracked-blob digests, the sidecar's exact byte layout, and the
field-by-field equality of the archived v2.0.16 record against the base `published_release`.

## After both follow-up commits

`python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package
tests.test_change_spec` → **Ran 119 tests, OK**. `PROJECT_STATE.json` now satisfies the canonical dump
check. The remaining unfixed items are none; both reviews are PASS and this file records every
disposition.
