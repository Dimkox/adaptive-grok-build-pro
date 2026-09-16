PASS

Route `7c56479f61d3`, receipt kind `release_review`, head `8d45b31479529a680ddec10057d8fe64ca941c30`, base `c86b1a1989ace899a4450bde558fcd8adc00e4e2`. Reviewer: independent release reviewer, read-only (this file is the only write). No-go definition used is this package's own `release.md`: "any rewritten historical release, any activation claim, or a record that disagrees with the remote tag or the tracked bytes". None of those is present — see §A. The Important findings are documentation-currency and ledger defects of exactly the class this commit exists to close, so they must be fixed in a fast-follow doc commit before the next release chain, not waved off.

## Verdict

PASS — merge `SR` on its exact-head App check. The published-release record is complete, correct, re-derivable and does not over-claim; the doctrine `R → merge → A → merge → tag + Release → SR` is closed in the machine-readable record and the lockstep tests. Twelve residual defects remain (7 Important, 5 Minor); the worst are two sentences that still state `v2.0.16` is the latest published release, and an untouched `trust_ci.last_success` whose prose is internally false.

---

## A. Verified correct (observations, not reasoning)

**Publication identities re-derived from the remote, all matching the record:**

```
$ git ls-remote origin 'refs/tags/v2.0.17' 'refs/tags/v2.0.17^{}'
5c6687ed97e1c365597bf27047016eb07411f28b	refs/tags/v2.0.17
c86b1a1989ace899a4450bde558fcd8adc00e4e2	refs/tags/v2.0.17^{}
$ gh pr view 99 --json number,state,mergedAt,mergeCommit,headRefOid
{"headRefOid":"bbc5cdd9…","mergeCommit":{"oid":"c86b1a1…"},"mergedAt":"2026-09-16T01:14:19Z","number":99,"state":"MERGED"}
$ git cat-file -p c86b1a1… | head -1   → tree 5826924586f9d42b02bf9fd5d51985bd323da31e
$ gh release view v2.0.17 --json publishedAt,assets → publishedAt 2026-09-16T01:17:14Z, isDraft false,
  asset digests sha256:770f1db5… (size 10940676) and sha256:54db9f64…
$ sha256sum packages/adaptive-grok-build-pro-v2.0.17.zip packages/…zip.sha256
770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616  …zip
54db9f64bb7296ca657410131499ca06358f89b23171e221b04e300acf03f3c0  …zip.sha256
$ gh api repos/…/commits/bbc5cdd9…/check-runs
{"app":"adaptive-trust-ci","id":104621989321,"conclusion":"success","name":"adaptive-trust-ci/verified@06ecf1c875bc"}
{"app":"gitguardian","id":104621982710,"conclusion":"success"}
$ gh api repos/…/check-runs/104621989321 --jq .output.summary
… repository-verification: pass (exit 0)
attestation=b9510589-d40c-4976-aafd-cad6fc141972; signer=0519cf1d47436f2e
```
Every value in AC-001, including the attestation id and the GitGuardian `check_run_id`, is externally corroborated. `git ls-remote origin refs/heads/main` → `c86b1a1…`.

**Runtime dossier is true, and I re-read the live units myself on the same host:**

```
$ hostname                                   → claw
$ systemctl show -p MainPID -p ActiveState -p UnitFileState adaptive-l5.service adaptive-l5-grok.service
MainPID=698333 adaptive-l5.service active enabled
MainPID=3597736 adaptive-l5-grok.service active enabled
$ systemctl show -p ExecStart …  → /opt/adaptive-l5/releases/5f6f6ce1ecb0…/… and …/61a05da2bd0c…/…
```
That matches `evidence/runtime-observation-post-99.json` field for field (PIDs, enabled state, installed SHAs, `merged_source_not_installed: [98, 99]`, "nothing was installed, restarted or activated"). `runtime_observations.evidence` points at the new dossier and `test_runtime_observations_are_source_bound_without_promoting_qualification` binds `evidence["source_base"] == observed_main_sha == c86b1a1…`.

**Truthful history (item 3 of the brief).**

```
archived v2.0.16 entry vs base published_release (notes key dropped): identity values identical = True, diffs = []
older prior entries byte-equal:            True      (v2.0.15 / v2.0.14 / v2.0.13 untouched)
prior tags now: ['v2.0.16','v2.0.15','v2.0.14','v2.0.13']  (base: three entries)
milestones / delivered_milestone / schedule / integrated_stack / trust_ci / work_inventory /
delivered_change_history / operational_qualification / fresh_clone: unchanged
changed top-level keys (exact set): active_delivery, current_unreleased_change, latest_published_release,
local_candidate, observed_at, observed_main_sha, prior_published_releases, published_release, runtime_observations
```
`active_delivery.integrated_stack` is still the historical v2.0.13 M-stack root (`m4_head 67dc4ddf…` → `release v2.0.13`, `migrations "001-018 byte-preserved"`). The v2.0.16 archive differs from `6d8f6ab`'s live `local_candidate` in exactly one key, `record_scope`, whose own text says "only this annotation key was added at archive time" — confirmed equal otherwise.

**No product byte moved (INV-002).** `git diff --name-only c86b1a1 8d45b31` outside `PROJECT_STATE.json`, the six top docs, `mistakes.md`, `tests/` and `engineering/changes/` → empty; no `.sql`, `scripts/`, `factory/`, `pilot/`, `governance/`, `architecture/` path and no `packages/*.zip` is in the diff.

**No activation over-claim (FORBID-001).** Every added line containing install/activat/deploy/host/provider was read: all of them *deny* an operational effect (e.g. `active_delivery.repository_delivery.record_scope`: "no installation, restart or activation happened for this release"; `release.md`: "Documentation only"). `operational_activation` is `false` in `local_candidate`, `current_unreleased_change` and `active_delivery.repository_delivery`. The `true`/`false` asymmetry is intended and precedent-identical: `6d8f6ab` set `published true`, `external_effect true`, `external_effect_scope "github_repository_delivery_and_release_only"`, `operational_activation false` with the same notes shape. `l5_production_preparation.operational_activation: true` is a *separate* pre-existing runtime record, not this release. `reviewed_product_head/tree` staying null also matches the precedent (both null at `6d8f6ab` with `checked_head` = the artifact-child head), and the new test comment states the reasoning.

**Prior-release index shift is a real shift, not a loosening (item 2).** `tests/test_project_state.py:330-360` now asserts `prior[0]`=v2.0.16 with `V2016_*`, `prior[1]`=v2.0.15 with `V2015_*`, `prior[2]`=v2.0.14 with `CURRENT_RELEASE_*`, `prior[3]`=v2.0.13 with `RELEASE_*` — every older release keeps its own constants, none dropped.

**Lockstep (item 2), exact tail:**

```
$ python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package tests.test_change_spec -q
Ran 119 tests in 8.971s

OK
/tmp/tmprtxixrib/publish/project.zip
56b4061f9397eda0a6efa8fcc18b81059b59823252c3efb6484506e533e8d156
```
The two trailing lines are unrelated scratch stdout emitted by a test in that module (the A review saw the same shape with `/tmp/tmpo3y150bx/…`); they are not failures. The `success_metric` count (119) and the A-package count (89 for its trio) are both reproducible.

---

## B. Findings

### 1. Important — `packages/README.md` still certifies v2.0.16 as the current published release, and this commit is what made it false
`packages/README.md:3`: "The latest published release is [`v2.0.16`](…), published `2026-09-13T22:04:08Z`, targeting `969c4f65f54…`. Its ZIP SHA-256 is `71f63a10…` … These immutable bytes are recorded in [`PROJECT_STATE.json`](../PROJECT_STATE.json) under `published_release`; earlier releases remain in `prior_published_releases`."
`packages/README.md:42`: "Published `2.0.16` is verified against the immutable tag-bound `published_release` record in PROJECT_STATE.json; earlier releases … use their entries in `prior_published_releases`."
After this commit `published_release` is v2.0.17 and v2.0.16 lives in `prior_published_releases`, so both sentences invert the store they describe. The same file's table row (line 32) *was* updated to "2.0.17 (published 2026-09-16T01:17:14Z)", and `tests/test_manifest_package.py:1448` now pins `published_version == '2.0.17'` — the prose is the only side left on the old value. AC-004 names "`packages/README.md` row" only, so the typed criterion is narrowly met while the file now contradicts the record.

### 2. Important — the ROADMAP identity block contradicts itself; AC-004's "ROADMAP … observed SHA" half is unmet
`DARK_FACTORY_ROADMAP.md:42` (moved here): `product version: 2.0.17 (latest published release: v2.0.17; published 2026-09-16T01:17:14Z)`.
`DARK_FACTORY_ROADMAP.md:37`, same fenced block, untouched: `latest published release: v2.0.16, tag target 969c4f65f54ef9230f3f94587e228098d1c2ecb9 (2026-09-13T22:04:08Z)`.
`DARK_FACTORY_ROADMAP.md:36`, untouched: `observed source SHA: 78082a290f8b90cade88685351fbb2ba263689b9 (2026-09-16; PR #98)` — while `PROJECT_STATE.observed_main_sha` is now `c86b1a1…` and `git ls-remote origin refs/heads/main` returns `c86b1a1…`. `test_version_identity_matches_readme` pins only the exact line-42 string, so the self-contradiction is invisible to the suite.

### 3. Important — four "observed main" pointers and one record field are now stale by exactly the release commit; the deferral said "align in SR"
`README.md:11` "| Repository source | `main` observed at `78082a290f8b…` (PR #98). … are part of this candidate's source." (v2.0.17 is published, so "this candidate" no longer denotes anything); `START_HERE.md:7` "Snapshot: **2026-09-16**. Repository `main` was observed at `78082a2…` (PR #98)" — three lines above the Released bullet that names `c86b1a1…`; `GROK_BUILD_HANDOFF.md:304` "Source `main` was observed at `78082a2…` (the PR #98 release-sync merge); the artifact child rides its own branch on that base" — PR #99 is `MERGED` and main is its merge commit, so the clause is false now, not just dated; `PROJECT_STATE.l5_production_preparation.actual_main_observation` `78082a2…`. These are the residuals of the previous cycle's **F1** (`A` release review) and item **3** (`A` security review, "align in `SR`"): the SR moved the heading to "(observed 2026-09-16)" and the SHA from `7bbf425` to `78082a2` but not to `c86b1a1`. Test blind spot confirmed: `test_current_epoch_and_app_are_consistent_in_handoff_documents` (`tests/test_project_state.py:674-689`) asserts `observed_main_sha` only *section-wide* for README "Current state" and START_HERE "Current project state", and never reads `GROK_BUILD_HANDOFF.md` — README passes solely because line 7 names `c86b1a1…`.

### 4. Important — `trust_ci.last_success` was not advanced, its prose is internally false, and the SR ledger claims it was
`git diff c86b1a1 8d45b31 -- PROJECT_STATE.json` touches no top-level `trust_ci` key. `PROJECT_STATE.json:1365-1373` still records PR #98 / head `83738723…` / merge `78082a2…` / `check_run_id 104605819798` with `"check_url": "https://github.com/Dimkox/adaptive-grok-build-pro/runs/104591923631"` — that run id is PR #94's (`delivered_change_history.post_v2_0_16_landing` row `pull_request 94 → check_run_id 104591923631`), so the deep link does not match the field beside it. Same field's `record_scope` asserts "PR #13, #64, #94 **and PR #98** are the post-publication merges recorded in `delivered_change_history.post_v2_0_16_landing`"; the ledger holds 12 rows `[81, 82, 83, 85, 88, 89, 90, 91, 93, 13, 64, 94]` and **no #98 row**. Meanwhile this package's `tasks.md:7` is ticked `[x] Advance current_unreleased_change, active_delivery and trust_ci.last_success`. Only `published_release.trust_ci` moved; the key literally named did not. The A release review's **F3** asked SR to advance it. (Disclosed counter-reading: `brief.md` Scope does not list `trust_ci`, so this may be scope drift in the checkbox text rather than an omitted edit — either way the sentence in the file is false and the ticked box overstates.)

### 5. Important — the "release-chain commits are not landing rows" convention lives in one prose field and the ledger contradicts it
The convention text exists only inside `PROJECT_STATE.json:1373` (`trust_ci.last_success.record_scope`) plus the superseded review reports; `grep -rniE "not a (landing )?row|release-chain|recorded through local_candidate"` over `*.md|*.json|*.py|*.yaml` returns nothing in `AGENTS.md`, `START_HERE.md`, `README.md`, `CHANGELOG.md` or any `engineering/changes/*/requirements.md`. A zero-context agent routed through `START_HERE.md` → `PROJECT_STATE.json` will not find the rule where it reads it, and the sentence's own literal form is already violated: row `pull_request 81` has `"purpose": "release record successor"` — the v2.0.16 SR **is** a landing row. Either the convention needs its exception stated (rows recorded before the convention existed) or the ledger needs a #98 row; the record currently does neither.

### 6. Important — the deferred ROADMAP PR inventory and the missing v2.0.17 delivery-history row
`DARK_FACTORY_ROADMAP.md:98` (previous cycle's **F7**, "listed so `SR` closes it", untouched) still says "PR #13 (repository-scoped Trust CI profiles, head `9bdffde9…`) **remains open** … its profiles stay absent from `main` until it merges" and "PR #64 … **is open** with `SUCCESS`", and lists PR #15's head as carrying a failure. Observed now: `gh pr list --state open --json number,title` → `[{"number":33,"state":"OPEN","title":"perf: parallelize local Python verification"}]` only; #13 merged as `4383115…` and #64 as `01d64e5…` (both in `post_v2_0_16_landing` and in `CHANGELOG.md`), #15 `closed_unmerged` in `work_inventory`. Also `DARK_FACTORY_ROADMAP.md:100` "### 3.4 Dated delivery history — through 2026-09-15" has no `2026-09-16` row for the v2.0.17 publication even though §3.4 carries a dated row for v2.0.16 (`:110`) — precedent nuance: that v2.0.16 row was added later by `02ac8c3` (PR #89), not by SR `6d8f6ab`, so this is a convention lag rather than a regression.

### 7. Important — a now-opened retention gate was left worded as pending, and the gate is genuinely satisfied
`PROJECT_STATE.work_inventory.retained_unresolved` for branch `feature/workflow-artifact-adapters`: "…they are retained **until the v2.0.17 release record references the #93 lineage**; **only then** may branch and worktree be removed as one cleanup step." The condition is met by this commit: `current_unreleased_change.predecessors[0]` = `{"kind": "workflow_artifact_adapters", "pull_request": 93, "head": "9086f2bc…", "merge_commit": "280cbff1…", "merged_at": "2026-09-15T20:03:41Z", "check_run_id": 104536573008}`, plus landing row #93 and `README.md:11`. The A release review checklist step 8 pointed SR at exactly this. `work_inventory` is unchanged (`git diff` shows no hunk), and the retained objects still exist: `git ls-remote origin refs/heads/feature/workflow-artifact-adapters` → `dccaeec2a6b7…`, `git worktree list` → `/home/pall/grok-projects/adaptive-grok-build-pro-workflow-adapters dccaeec [feature/workflow-artifact-adapters]`. The ADR-0001 golden copy of the uncommitted epic is therefore still held by a gate that no longer applies, and no text records the disposition either way.

### 8. Minor — `PROJECT_STATE.json` formatting regression: only this commit breaks the canonical dump
The appended v2.0.16 archive block (`PROJECT_STATE.json:69-97`) is written at 2-space depth with `"tag": …`/`},` at column 2 while every sibling entry is at column 6:
```
$ python3 -c "raw=open('PROJECT_STATE.json').read(); import json; print(raw==json.dumps(json.loads(raw),indent=2,ensure_ascii=False)+'\n')"
8d45b31 canonical: False | delta lines: 29
c86b1a1 canonical: True | 6d8f6ab canonical: True | 969c4f65 canonical: True
```
Values are correct (verified in §A), so this is cosmetic, but `PROJECT_STATE.json` is the machine handoff that `mistakes.md`'s new rule (added by this very commit) tells future agents to edit by brace depth — a mixed-depth block is exactly the anchor hazard that rule exists to survive. No test pins JSON style.

### 9. Minor — leftover candidate-phase scaffolding in `tests/test_project_state.py`
`tests/test_project_state.py:404-409` keeps a dead branch with a tell-tale comment — `if local["artifact_status"] == "pending_unpublished_artifact_child":  # SR: published, so the else arm pins them` — whose `if` body can never run for a published record. Two lines above the new assertions that *require* the child's identities, the inherited comment still reads "The child can name the release-sync parent … but never its own identities: those belong to the post-merge successor.", which now describes the opposite of what the code checks (`tests/test_project_state.py:398-402`).

### 10. Minor — the release-sync ledger understates its own evidence while SR ticked later boxes in the same file
`engineering/changes/20260915-…-f98796/tasks.md` still carries `- [ ] Run python3 scripts/grok_verify.py --mode pr on the frozen tree and record the verification receipt.` and `- [ ] Independent security_review and release_review receipts for this route.`, for a route whose PR #98 is merged and whose release is published, while SR ticked the three later boxes (`A`, tag/Release, `SR`) in that same file. The review reports do exist on disk (`…/evidence/review-release.md`, `review-security.md`, `review-response.md`), and the claim SR newly wrote — `active_delivery.local_source_gate.record_scope` "the release-sync and artifact-child heads passed the repository verifier before the exact-head App gate" — is externally supported: both `104605819798` (head `83738723…`) and `104621989321` (head `bbc5cdd9…`) summaries print `repository-verification: pass (exit 0)`. The honest gap is only the *fingerprint-bound local* receipt, which cannot exist for a superseded tree; the fix is a dated note, not a tick.

### 11. Minor — candidate-worded labels retained inside the published record
`delivered_change_history.post_v2_0_16_landing.status = "landed_in_2_0_17_candidate"` and `current_unreleased_change.scope[0..1]` — "… move to the 2.0.17 candidate" / "opened `local_candidate` slot with the artifact pair asserted absent" — describe the R commit and are true of it, but they are the only remaining places where "candidate"/"absent" wording attaches to a now-published release. `engineering/runbooks/l5-runtime-observation-2026-09-15.md:7` ("The latest published release remains [`v2.0.16`]…") is explicitly dated `2026-09-15T09:54:21Z` and is therefore correct history, not staleness.

### 12. Minor — AC-001 credits tests with coverage they do not have
AC-001 lists `tests/test_project_state.py` and `tests/test_manifest_package.py` as the evidence for a statement that includes `tag_object`, `published_at` and the GitGuardian run. `grep -n "tag_object" tests/test_project_state.py` → no matches, and none exists at `969c4f65`, `6d8f6ab` or `c86b1a1` either, so the tag-object binding — the single most important value this commit adds — is pinned only by the constant in `tests/test_project_state.py:22` if a later commit forgets it. `published_release.published_at` and `published_release.gitguardian.check_run_id` are likewise unasserted (`test_project_state.py:348` checks only the conclusion). Pre-existing convention, disclosed rather than invented: I verified those three values directly against `git ls-remote`, `gh release view` and `gh api` (§A).

---

## C. Go / no-go

**GO** for merging `SR`, with findings 1–7 assigned to an immediately-following documentation commit on the same chain discipline (own route, own exact-head App check; no re-tagging, no byte change). Nothing in this commit is irreversible or authority-claiming: history is unmodified, the record matches the remote tag, the Release assets and the tracked bytes, both recomputable digests hold, `operational_activation` stays false, no product path moves, and the 119-test lockstep is green on the frozen tree.

Do **not** read this release as establishing, and do not let any follow-up imply: an installed or restarted L5 provider (the live units still run `5f6f6ce…`/`61a05da…`, which I confirmed myself), a fully evidenced external pilot with maintainer acceptance, an exact-profile M8 qualifying cohort or activation, general M9 operational qualification (production/signed input/recovery/human authority), any factory publication of a public site, or a deployed Trust CI policy/holdout/branch-protection change (the repository-profile capability is source-only). `operational_qualification`, `work_inventory.active` and the `M8`/`M9` milestone gates correctly remain untouched by this commit and remain the authoritative "not proven" surface.

## D. Backlog this review hands to the next session

1. Fix `packages/README.md:3` and `:42` (v2.0.17 is the latest published release; v2.0.16 now sits in `prior_published_releases`).
2. Fix `DARK_FACTORY_ROADMAP.md:37` and `:36`; the identity block must not contradict line 42.
3. Move the four observed-main pointers to `c86b1a1…` and drop the "rides its own branch" clause: `README.md:11` (also "this candidate's source"), `START_HERE.md:7`, `GROK_BUILD_HANDOFF.md:304`, `l5_production_preparation.actual_main_observation`; consider teaching `test_current_epoch_and_app_are_consistent_in_handoff_documents` to cover `GROK_BUILD_HANDOFF.md`.
4. Resolve `trust_ci.last_success`: either advance it to the A merge (`99`, `bbc5cdd9…`, `c86b1a1…`, run `104621989321`, attestation `b9510589-…`) or state why a release-chain head is out of scope — and in both cases repair the mismatched `check_url` (`…/104591923631` is PR #94) and the false "PR #98 … recorded in post_v2_0_16_landing" sentence. Then correct this package's `tasks.md:7`.
5. State the release-chain/landing-row convention in a place a routed agent reads (`AGENTS.md` or `START_HERE.md`), and reconcile it with row #81 or add the #98 row.
6. Rewrite `DARK_FACTORY_ROADMAP.md:98` against `gh pr list --state open` (only #33) and add the dated `2026-09-16` v2.0.17 publication row to §3.4, retitling "through 2026-09-15".
7. Decide the now-unlocked retention of branch `feature/workflow-artifact-adapters` (`dccaeec…`) and its worktree, and record the disposition in `work_inventory` — keeping the golden-copy caveat of the uncommitted epic until that decision is explicit.
8. Re-indent the v2.0.16 archive block in `PROJECT_STATE.json` (canonical `indent=2`), delete the dead `pending_unpublished_artifact_child` branch and the stale "never its own identities" comment in `tests/test_project_state.py`.
9. Close this package's `tasks.md:10-11` only after `grok_verify --mode pr` and the `security_review`/`release_review` receipts bind this fingerprint (both reports land in this package's `evidence/`), open the SR pull request, and merge solely on the exact-head `adaptive-trust-ci/verified@06ecf1c875bc`. I deliberately did not run the verifier: it writes into the tree it verifies, which would void the reviews.
10. Not fixed here and still open upstream: issue #80 (local architecture analysis refuses the >10 MB tracked ZIP) and PR #33 (only open pull request, historical `FAILURE` conclusion, cause not inspected).
