# Release review — v2.0.17 release sync `R` (route `f98796afe7de`)

**Verdict: PASS — `R` is merge-ready.** No Critical finding. Identity is coherent, the twelve
post-publication landing rows re-derive exactly from GitHub, the candidate slot is honestly pending,
nothing is published or claimed published, and the published `v2.0.16` record is byte-unchanged.
Three **Important** findings are documentation-currency defects (none touches release or merge
authority); because **no pull request exists yet for `R`**, all three are cheapest to fold into one
final amend before opening the PR.

- Reviewed head: `dc11669c45eec289a9e22b0e94b12897b9904b4b` (branch `feature/v2.0.17-release-sync`),
  base `7bbf42526f207db0007daafa4cc946cc2d81f465` = current `origin/main`. The commit was amended
  twice while this review ran (`b2932dc` → `8c872b0` → `dc11669`); `dc11669` additionally repins
  `DARK_FACTORY_ROADMAP.md:36` to the post-#94 tip (a drift I had flagged) and adds
  `evidence/artifact-child-map.md`. All findings and verifications below are against `dc11669`;
  **any further amend invalidates this report and every fingerprint-bound receipt.**
- At review end the worktree was dirty with an in-flight follow-up (`PROJECT_STATE.json`,
  `README.md`, this package's `architecture.md` and `tasks.md`, uncommitted) that partially addresses
  F1(4) and F4. Re-issue this report against the amended head; the findings those edits do not cover
  (F1(1) `GROK_BUILD_HANDOFF.md:306`, F1(2)-(3) `START_HERE.md:10,14`, F1(5) PR #15, F2, F3) stay open
  either way.
- Method: `git show`/`git diff` on the two heads, full key-path data diff of
  `PROJECT_STATE.json` (base vs head), independent re-derivation of all twelve landing rows from
  `gh pr view` + the GitHub Checks API + `git log`, and the three coupled unittest modules run on
  the frozen tree. No full suite, no `grok_verify`, no writes except this file.

## 1. Verification that passed

| Check | Result | Evidence |
| --- | --- | --- |
| AC-001 six identity surfaces | PASS | `VERSION`=`2.0.17`; `README.md:1` `# Adaptive Grok Build Pro v2.0.17`; `README.md:7` `Identity: **2.0.17** (candidate, unpublished)`; `CHANGELOG.md:3` `## 2.0.17 — 2026-09-15 (candidate, unpublished)`; `DARK_FACTORY_ROADMAP.md:42` `product version: 2.0.17 candidate (latest published release: v2.0.16; …)`; `.grok-stack/adaptive_grok/__init__.py:3` `__version__ = "2.0.17"`; `PROJECT_STATE.json:7` `product_version: 2.0.17` |
| AC-001 published surfaces still name v2.0.16 | PASS | `latest_published_release=v2.0.16`, `published_release.tag=v2.0.16`; a recursive key-path diff of `PROJECT_STATE.json` shows **zero** changes under `published_release` and `prior_published_releases` |
| AC-002 all twelve landing rows vs ground truth | PASS, 12/12 | Each of #81 #82 #83 #85 #88 #89 #90 #91 #93 #13 #64 #94 re-derived: `gh pr view <n> --json mergedAt,mergeCommit,headRefOid` + `gh api repos/Dimkox/adaptive-grok-build-pro/commits/<head>/check-runs` filtered to `adaptive-trust-ci/verified@06ecf1c875bc` → `.id`. Every `head`, `merge_commit`, `merged_at` and `check_run_id` in `delivered_change_history.post_v2_0_16_landing.pull_requests` matched; no mismatch. The set is also complete and exclusive: `git log --first-parent 969c4f6..7bbf425` returns exactly those twelve merge commits |
| "twelve" count claim | PASS for the archive, FAIL for the CHANGELOG enumeration | 12 rows in `post_v2_0_16_landing` (pinned by `tests/test_project_state.py:390-404` as the set `{13,64,81,82,83,85,88,89,90,91,93,94}`) vs `CHANGELOG.md:5` — see F2 |
| AC-003 pending slot | PASS | `PROJECT_STATE.json:546-582`: `status=pending_release`, `artifact_status=pending_unpublished_artifact_child`, `artifact_child.status=not_built`, `published=false`, `published_at/checked_head/merge_commit/tree/reviewed_product_head/reviewed_product_tree/pull_request/external_effect_scope` all `null`, `artifact_child.{commit,tree,source_parent,source_parent_tree,zip_sha256,sidecar_sha256}` all `null`, `external_effect=false`, `operational_activation=false` |
| AC-003 absence assertion really guards | PASS | `packages/` contains no `v2.0.17` file (`git ls-files packages/ | grep -c 2.0.17` → `0`; working tree clean, no `dist/`). `tests/test_manifest_package.py:1425-1428` asserts `artifact_status == 'pending_unpublished_artifact_child'` *before* the branch, and `:1435-1436` then asserts `tuple(p for p in candidate_pair if p.exists()) == ()` — so bytes shipped under a pending claim fail this test; the digest-checking `else` arm (`:1437-1444`) is unreachable in this tree by design and activates only when A moves the expectation at `:1426` |
| ZIP path vs packaging naming | PASS | `scripts/package_stack.py:1091` → `dist/adaptive-grok-build-pro-v{version}.zip`; tracked copies live under `packages/` with the same `v<VERSION>` stem, matching `delta_paths` verbatim, so A's files are pinned by a test |
| Item 4 data-level compare | PASS | Recursive diff: the archived `delivered_change_history.v2_0_16_release_preparation.published_local_candidate` equals base `7bbf425:local_candidate` **except** one added key, `record_scope`. `published_release` equals base exactly. No pre-publication assertion was repointed (`INV-001` holds; milestone records, schedule dates, frozen migration range, released digests untouched) |
| AC-004 / `FORBID-001` | PASS | `README.md:7`, `START_HERE.md:9,16`, `GROK_BUILD_HANDOFF.md:303`, `CHANGELOG.md:18`, `current_unreleased_change.{artifact_child,tag_and_release}` all state that no `v2.0.17` ZIP, sidecar, tag or GitHub Release exists; `git tag --list 'v2.0.1*'` ends at `v2.0.16` locally and in `refs/tags` on origin. No tree text says "ten pull requests" or "no release preparation remains" (the only hit is `PROJECT_STATE.json:189`, quoting the removed claim as the reason for this change) |
| `INV-002` nothing published | PASS | Diff touches no `packages/` asset, no workflow, no runtime/host mutation; `active_delivery`/`current_unreleased_change` carry `external_effect=false`, `operational_activation=false` |
| Lockstep trio on the frozen head | PASS | `python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package -q` → `Ran 89 tests … OK`; `tests.test_change_spec` → `Ran 30 tests … OK`. Full suite and `grok_verify` deliberately not run (reviewer scope) |
| Evidence dossier | PASS with a note | `runtime_observations.evidence` now points at `evidence/runtime-observation-post-94.json`, which re-pins both units `active/enabled` with unchanged MainPIDs and states #93/#13/#94 are merged source only. MainPID/socket/`/opt/adaptive-l5/...` paths follow the already-tracked `post-91` dossier (same keys, same fields), so no new host-identity class enters the tree (`FORBID-002`); no secret or key material is present |

## 2. Findings

**F1 — Important (non-blocking): PR-status drift in current-state prose, one of it introduced by this commit.**
Reconciling bootstrap prose is exactly the recorded repo mistake (`mistakes.md` → "2026-09-15 Public
current-state drift after live activation") and AC-004's intent. Contradictions still standing at `dc11669`:

1. `GROK_BUILD_HANDOFF.md:306` — "Refresh the open-work inventory (**#15, #33, #94**)". `#94` **merged**
   (`gh pr view 94 --json state` → `MERGED 2026-09-15T22:58:12Z`) and *is* this commit's base; the same
   sentence correctly calls #13 and #64 merged. The base text listed `(#13, #15, #33, #64)`, so this
   is a new false claim authored here, not inherited.
2. `START_HERE.md:14` — "PRs **#13, #15, #33 and #64 were open at this observation**". The observation
   is now `7bbf425` (`START_HERE.md:7`), at which #13 and #64 are merged and archived in this very
   commit's `post_v2_0_16_landing`. Untouched by the commit, and now self-contradictory.
3. `START_HERE.md:10` — "the durable … failover (PR #91) and runtime connection work **reach the
   observed PR #91 source**" while line 7 says main was observed at `7bbf425` (PR #94); also
   "adapters … land with the delivered pull request of change
   `20260915-update-third-party-workflow-components-superpowe-1b0c02`" (#93 landed as `280cbff`).
4. `README.md:11` — "the workflow artifact adapters … **are delivered by this pull request**" inside
   a row that now reads `main` observed at `7bbf425` (PR #94). In the merged tree this resolves to the
   release-sync PR, which delivers no adapters at all. This line was edited in this commit (only its
   SHA was updated) and the stale clause was carried over.
5. `PROJECT_STATE.json` `work_inventory.open_pull_requests` still lists **PR #15 with
   `"status": "open"`** although GitHub reports `state=CLOSED closedAt=2026-09-15T20:02:30Z` — before
   this commit's own `observed_at` (`2026-09-15T22:59:00Z`). `gh pr list --state open` returns only #33.
   The commit curated this exact array (dropping #13/#64) and pins it at
   `tests/test_project_state.py:753` (`{15, 33}`), so the falsehood is test-enforced.
*Fix:* amend #1–#4 (one-line rewordings, no test impact) and either fix #5 in the same amend
(`open_pull_requests` → `[{33}]`, `#15` moved to `retained_unresolved` as closed-unmerged, and move
`tests/test_project_state.py:753`), or carry all five forward to `A` as checklist item A-9.

**F2 — Important (non-blocking): the CHANGELOG count claim is not backed by its own enumeration.**
`CHANGELOG.md:5` asserts "Twelve pull requests merged after `v2.0.16` was published" and the section
then lists **eleven** PR-attributed bullets (`#82 #83 #85 #88 #89 #90 #91 #93 #13 #64 #94`,
`CHANGELOG.md:7-17`); **#81 has no bullet** (`grep -n '#81' CHANGELOG.md` → no hit) even though the
commit message, `local_candidate.notes` and `post_v2_0_16_landing` all count it. Ground truth supports
"twelve" (F1 table), so the defect is the missing row, not the number. No test pins CHANGELOG rows to
archive rows, which is why the trio stayed green — the same blind spot as the v2.0.16 review's F1.
*Fix:* add a `#81` bullet ("records the published v2.0.16 release identity; documentation-only
successor, merged `2026-09-14T00:11:30Z` as `6d8f6ab`, App check `103814853460`") or reword to
"Twelve pull requests merged after `v2.0.16`; eleven changed product/docs source and #81 is the
v2.0.16 release-record successor".

**F3 — Important (non-blocking): the `requirement` string instructs `A` to flip `published`, contradicting the pinned sequence.**
`PROJECT_STATE.json:575` (`local_candidate.artifact_child.requirement`, copied verbatim from the
v2.0.16 `R`) says the artifact child "adds both delta_paths files … and **flips published**,
artifact_status and the artifact identities". `release.md` step 3 assigns `published=true` and
`published_at` to **SR**, `INV-002`/`FORBID-001` forbid presenting 2.0.17 as published while no tag
exists, and the precedent's `A` commit kept `"published": false` (verified:
`git diff 287b27ac 969c4f6 -- PROJECT_STATE.json` leaves `published`/`published_at`/`external_effect`
untouched and rewrites this string to "published stays false and merge_commit/tree stay null until the
post-merge documentation successor"). Low practical risk because A must rewrite the string anyway and
`tests/test_project_state.py:366` pins `assertFalse(published)`, but it is a trust-adjacent
misinstruction in the record the next agent will read first. `evidence/artifact-child-map.md` already
carries the correct replacement text — apply it (checklist A-4).

**F4 — Minor: typed spec and plan prose under-enumerate the landing set.** `change-spec.yaml` AC-002
names ten PRs (`#82 … #64`, omitting #81 and #94), `test-plan.md` P0 row says "the **ten**
post-publication merges are recorded", and `tasks.md` "Freeze the content" lists the same ten with
`Re-derive observed_main_sha after **#64** merges` while the delivered base is post-#94
(`7bbf425`). The implementation is a superset, so no acceptance criterion fails; the typed authority
is simply stale relative to the delivered content. Since the spec is source-of-truth rank 3, tighten
these three lines at A (or in the recommended amend).

**F5 — Minor: `requirements.md` AC-001 quotes a ROADMAP literal the tree does not contain.** The
criterion expects `product version: 2.0.17 (latest published release: v2.0.16; …)`; the tree and
`tests/test_structure.py:287` pin `product version: 2.0.17 **candidate** (latest published release:
v2.0.16; …)`. Intent (ROADMAP names 2.0.17 as candidate) is met; fix the quote.

**F6 — Minor: one file outside the declared scope.** The commit rewrites a 1-character typo
(`ebd904a` → `ebd9a0a`) in
`engineering/changes/20260915-fix-verify-reject-same-inode-cas-tampering-by-co-665347/evidence/review-code.md`,
another package's frozen review evidence. Harmless and correct, but `test-plan.md` "Manual checks"
asserts `git show --stat HEAD` touches "only the identity surface, `PROJECT_STATE.json`, the coupled
tests and this package". Either state the exception in `brief.md` Scope or drop the hunk.

**F7 — Minor: `A`'s new helper depends on untracked scratch.** `evidence/artifact-child-map.md`
instructs `bash /tmp/build_release_artifact.sh …`. The file exists now (`/tmp`, 1975 bytes, mtime
2026-09-15T22:47) but `/tmp` is not Git content and is not reviewable at A time; `AGENTS.md` treats
host-local deployment scratch as non-repository state. Inline the exact two-clone `0700` staging
commands (or the `scripts/package_stack.py --output` invocation plus the byte-compare loop) into the
map. Related: `route.json:base_commit` is `280cbff` (the routing-time tip) while the delivered
`source_base` is `7bbf425` — a frozen snapshot, not a defect, but worth one clarifying line so an
auditor does not read it as a base mismatch.

**F8 — Minor (A/SR planning): "twelve" is a snapshot that expires when `R` merges.** The count appears
in `CHANGELOG.md:5`, `PROJECT_STATE.json:582` (`local_candidate.notes`) and `:189`
(`current_unreleased_change.explanation`), and the archive is named `post_v2_0_16_landing`. After R
merges (and again after A merges), literally thirteen/fourteen pull requests have landed since the
publication. Name the convention in one sentence at A — "release-chain commits (`R`, `A`, `SR`) are
recorded in `local_candidate`/`current_unreleased_change`, not as `post_v2_0_16_landing` rows" — so
the archive stays honest without restating the count everywhere.

**F9 — Note, no action:** `tests/test_manifest_package.py:1435` branches on
`artifact_status == 'pending_unpublished_artifact_child'`, whose negation arm is currently unreachable
because `:1426` pins the same literal. That is intentional (the discriminator must move in exactly one
place, at A), but it means *this* test cannot by itself catch a future record that claims delivered
bytes while the branch key is renamed to a third value. `tests/test_project_state.py` pins the
allow-listed status values, which is the effective guard. Leave as is.

## 3. Concrete `A` checklist (verified against `dc11669`; supersedes nothing in `evidence/artifact-child-map.md` — it completes it)

Preconditions: `R` merged; no other PR landed in between (if one did, see §4).

1. **Build, then commit exactly two files** (nothing else may carry artifact bytes):
   `packages/adaptive-grok-build-pro-v2.0.17.zip` and
   `packages/adaptive-grok-build-pro-v2.0.17.zip.sha256`, built **from `R`'s merged tree** in a `0700`
   private staging dir from two independent exact-SHA clones; require byte-identical ZIP digests before
   writing anything. Sidecar content is exactly `<zip-sha256>  adaptive-grok-build-pro-v2.0.17.zip\n`
   (two spaces, LF) — asserted at `tests/test_manifest_package.py:1441-1444`. Paths must equal
   `local_candidate.artifact_child.delta_paths` (`PROJECT_STATE.json:569-570`).
2. `packages/README.md` — add one table row after `:29`
   (`| adaptive-grok-build-pro-v2.0.17.zip | 2.0.17 (artifact delivered, tag pending) |`); do not touch
   the immutable v2.0.13-v2.0.16 rows.
3. `PROJECT_STATE.json` flips: `observed_at` (fresh UTC) and `observed_main_sha` → **`R`'s merge
   commit**; `local_candidate.source_base` → same; `local_candidate.status`
   `pending_release` → `artifact_bytes_delivered`; `local_candidate.artifact_status`
   `pending_unpublished_artifact_child` → `pending_tag_and_release`;
   `artifact_child.source_parent`/`source_parent_tree` → `R`'s merge commit and its tree;
   `artifact_child.zip_sha256`/`sidecar_sha256` → the reproduced digests;
   `artifact_child.status` `not_built` → `built_byte_reproducible_twice`; add
   `artifact_child.zip_source_note` (pre-publication snapshot caveat); rewrite `local_candidate.notes`.
4. Rewrite `local_candidate.artifact_child.requirement` to the precedent text so it no longer says the
   child "flips published" (F3), and update `current_unreleased_change.artifact_child`
   (`:178` "Not built…") + `current_unreleased_change.stage`
   (`identity_bump_in_pull_request` → e.g. `artifact_child_delivered_pending_tag`; `stage` is **not**
   test-pinned) + `current_unreleased_change.next_action` (`:187`) / `active_delivery.next_action`
   (`:615`, same string, asserted equal to it by `tests/test_project_state.py:419-421`).
5. **Leave unchanged by design:** `product_version`, `latest_published_release`, `published_release`,
   `prior_published_releases`, `VERSION`, `.grok-stack/adaptive_grok/__init__.py`, README H1/Identity,
   the CHANGELOG `## 2.0.17 …` heading, the ROADMAP `product version:` line — i.e. every literal pinned
   by `tests/test_structure.py:280-289` and `tests/test_manifest_package.py:1422`. A does not bump identity.
6. **Must stay `false`:** `local_candidate.published`, `external_effect`, `operational_activation`;
   also `current_unreleased_change.external_effect`/`operational_activation` and
   `operational_qualification.*`. **Must stay `null` (A cannot self-record its own merge identity):**
   `local_candidate.checked_head`, `merge_commit`, `tree`, `pull_request`, `published_at`,
   `external_effect_scope`, `reviewed_product_head`, `reviewed_product_tree`, and
   `artifact_child.commit` + `artifact_child.tree` — all pinned by
   `tests/test_project_state.py:360,366-378`. SR fills them (precedent `6d8f6ab` set
   `published/published_at/external_effect=true`, `external_effect_scope=github_repository_delivery_and_release_only`,
   `pull_request=79`, `checked_head/merge_commit/tree`, `artifact_child.commit/tree`, and rewrote
   `published_release`/`latest_published_release` — none of that belongs to A).
7. **Keep `local_candidate.route_id`/`branch`/`change_package` naming the `R` lineage**
   (`f98796afe7de` / `feature/v2.0.17-release-sync` / this package) even though A rides its own branch
   (`feature/v2.0.17-artifact-child`, as in the precedent). Pinned at
   `tests/test_project_state.py:358-364`; the precedent's final published record names exactly the
   release-sync route/branch/package together with **A's** PR number, which SR supplies. `A` deviating
   here would erase the release-sync lineage.
8. Test literals that must move with the bytes:
   - `tests/test_project_state.py:16` `OBSERVED_MAIN_SHA = "<R merge sha>"  # … (release-sync merge)`
     (drives `:77` and the `source_base` pin at `:379`)
   - `tests/test_project_state.py:357` `status` → `artifact_bytes_delivered`
   - `tests/test_project_state.py:365` `artifact_status` → `pending_tag_and_release`
   - `tests/test_project_state.py:371-372` `assertIsNone(zip_sha256/sidecar_sha256)` →
     `assertEqual(..., "<digest>")`
   - `tests/test_project_state.py:376-378` split the null loop: keep
     `("commit","tree")` pinned `null` unconditionally; require
     `source_parent`/`source_parent_tree` `null` only while
     `artifact_status == "pending_unpublished_artifact_child"`
   - `tests/test_project_state.py:380` `artifact_child["status"]` `not_built` →
     `built_byte_reproducible_twice`
   - `tests/test_manifest_package.py:1426` expected `artifact_status` → `pending_tag_and_release`;
     the `if/else` at `:1435` needs **no** edit — flipping `:1426` is what makes the
     exists-both-files + digest/sidecar arm execute
   - `tests/test_project_state.py:423` stays `release_sync_authored` unless A changes
     `current_unreleased_change.status` (then move it in lockstep); `:426/:429`
     (`identity`, `target_version`) unchanged
9. Doc wording that flips when bytes exist: `CHANGELOG.md:18` ("No `v2.0.17` ZIP, sidecar, tag or
   GitHub Release exists yet" → ZIP+sidecar delivered, tag and Release pending), `README.md:7`,
   `START_HERE.md:9` and `:16`, `GROK_BUILD_HANDOFF.md:303`. If F1/F2/F4/F5 were not folded into the R
   amend, fix them here (including `work_inventory.open_pull_requests` → `[{33}]` plus
   `tests/test_project_state.py:753`).
10. Gate expectation: `grok_verify --mode pr` will flag the >10 MB tracked binary it never reads
    (issue #80, local-only red, already recorded in
    `engineering/changes/20260914-test-l5-execute-offline-backup-restore-boundarie-962a9c/evidence/analysis-docs_researcher.md:56`).
    The external App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on A's exact head is the merge
    gate; disclose the local red rather than suppressing it.
11. Verification before declaring A locally complete: `python3 -m unittest tests.test_structure
    tests.test_project_state tests.test_manifest_package` on the frozen tree, then
    `python3 scripts/grok_verify.py --mode pr`, then route-selected review receipts.

## 4. Go/no-go and what must be re-derived at `A`

**Go for `R`:** merge it. Preferably as one final amend (or a second commit on the same branch) that
clears F1-F3 — the PR is not open yet, so an amend costs no re-approval, whereas every amend demands a
fresh exact-head App check and re-bound local receipts. Required before merge per `release.md`:
`grok_verify --mode pr` PASS on the frozen tree plus `security_review` and `release_review` receipts on
the final fingerprint (this report is the `release_review` evidence; `route.json:required_evidence` =
verification + security_review + release_review). **No-go triggers, none present:** any claim that a
v2.0.17 tag/Release/bytes exist, any `packages/v2.0.17*` file in `R`, any rewritten published record.

**No-go for tag + GitHub Release** until: `R` merged; `A` built from `R`'s merged tree with two
byte-identical builds; `A` merged on its own exact-head App check; and a separate explicit delegated
grant for *each* of tag push and Release publication bound to that exact commit (a grant does not
survive a tree or commit change, and never substitutes for the external check or a human security
approval). `operational_activation` stays `false` through the whole chain.

Re-derive at A time if anything landed between `R` and `A` — these surfaces go stale immediately:
`observed_main_sha`/`observed_at` (+ `tests/test_project_state.py:16`), `local_candidate.source_base`,
`current_unreleased_change.source_base`/`predecessors`, `l5_production_preparation.actual_main_observation`,
`trust_ci.last_success` (today bound to PR #94 head `9437efed`, run `104591923631`), the
`post_v2_0_16_landing` row set and the "twelve" count in `CHANGELOG.md:5` /
`PROJECT_STATE.json:189,582` / `brief.md`, the PR-number references in `README.md:11`,
`START_HERE.md:7,14`, `GROK_BUILD_HANDOFF.md:304,306`, and `DARK_FACTORY_ROADMAP.md:36`. A new landing
row must be re-derived the same way (Checks API on the exact head, not from prose). Also re-check:
whether any new merge changed `VERSION`-coupled surfaces (it must not), whether the installed L5 SHAs
still match `runtime_observations` (they were `active/enabled` on pre-#93 SHAs at
`2026-09-15T23:02:27Z`; a restart or reinstall would stale the dossier and the README table), and
re-pin `artifact_child.source_parent`/`source_parent_tree` to the exact commit whose tree was packed —
never to a later tip — because the ZIP is built from a specific SHA and the tag binds A's merged commit.
