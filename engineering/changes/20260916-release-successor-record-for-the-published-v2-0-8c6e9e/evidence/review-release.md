FAIL

# Release review — v2.0.18 successor record (SR)

- Repository: `/home/pall/grok-projects/adaptive-grok-build-sr18`
- Branch: `feature/v2.0.18-successor-record`, HEAD `28de12c90e3b9914648aaefdc7ce422428261854` (worktree clean at review start)
- Diff under review: `git diff e7d0f72bf834b75eb543d9424ee47c7829cc65c0..HEAD` (21 files, +589/-161)
- Typed spec: `engineering/changes/20260916-release-successor-record-for-the-published-v2-0-8c6e9e/change-spec.yaml`
- Precedent compared field-for-field: `cfc4a5741210cc7b28431c56c92b9d549540c65d` (SR of v2.0.17, PR #100)
- Reviewer: `release_reviewer` (route `8c6e9e30b239`), read-only; only this file was written.

## Scope

Records-only successor: `PROJECT_STATE.json` publication records, current-state docs, coupled lockstep tests,
the SR change package and the `post-108` runtime dossier. No product code, packaging script, contract, rule,
migration or artifact byte is in scope (INV-002). `git diff --check e7d0f72..HEAD` is clean.

## Commands run

```bash
git status --short && git log --oneline -6 && git rev-parse HEAD
git diff --stat e7d0f72..HEAD            # and per-file diffs for PROJECT_STATE.json, docs, tests
git diff --check e7d0f72..HEAD           # clean
git ls-remote origin 'refs/tags/v2.0.1*' 'refs/heads/main' 'refs/tags/v2.0.18^{}'
gh pr view 108 --json number,mergedAt,mergeCommit,headRefOid,state,baseRefName
gh api repos/.../commits/07d1141e.../check-runs
gh api repos/.../check-runs/104809218211 --jq '.output.title,.output.summary'
gh api repos/.../releases/tags/v2.0.18   # and /releases, plus the v2.0.17 body
gh pr list --state open ; gh issue list --state open
sha256sum packages/adaptive-grok-build-pro-v2.0.18.zip{,.sha256} ; stat -c '%s' …zip
git rev-parse 'e7d0f72^{tree}' ; git cat-file -t 31d3171f651ea77e29de58d4affc58d008f1c7a5
python3 - <<'EOF'  # flat field-diff of HEAD prior_published_releases[0] vs e7d0f72 published_release,
                   # repeated for cfc4a57 vs cfc4a57^ (precedent parity)
python3 -m unittest tests.test_project_state tests.test_structure \
        tests.test_manifest_package tests.test_change_spec     # Ran 119 tests ... OK
systemctl show adaptive-l5.service adaptive-l5-grok.service -p MainPID -p ActiveState -p UnitFileState
```

## Verified against live reality (no defect)

| Claim | Live source | Result |
| --- | --- | --- |
| `published_release.tag` v2.0.18, `pull_request` 108, `checked_head` 07d1141e…, `merge_commit` e7d0f72…, `merged_at` 13:51:26Z, `published_at` 13:52:24Z | `gh pr view 108` (MERGED, base `main`), Releases API | match |
| `tag_object` 31d3171f… is an annotated tag whose peeled target is `e7d0f72…` | `git ls-remote … v2.0.18^{}`, `git cat-file -t` | match |
| `observed_main_sha` == `published_release.merge_commit` == `local_candidate.merge_commit` == `active_delivery.repository_delivery.merge_commit` == `dossier.source_base` == live `refs/heads/main` | ls-remote, PROJECT_STATE, dossier | all `e7d0f72…` |
| `tree` c78d200e… == `git rev-parse e7d0f72^{tree}`; also `local_candidate.tree` and `artifact_child.tree` | git | match |
| artifact `path`/`sha256` 0bc6adc9…, `sidecar_sha256` dd7e2ec5…, 11,160,330 B | local `sha256sum` of tracked blobs **and** GitHub Release asset `digest` fields + `size` | match, both sides |
| `trust_ci` check name/conclusion/`check_run_id` 104809218211, `attestation_id` 8172a5bc…, `signer` 0519cf1d…, `github_app_id` 4694114, all six commands | Checks API on `07d1141e` (app `adaptive-trust-ci`, conclusion success) + check-run `output.summary` | match |
| `gitguardian` SUCCESS / 104809206290 and the informational-only note | Checks API | match |
| `trust_ci.last_success` = PR 108 / head 07d1141e / run 104809218211 / attestation 8172a5bc…, `check_url` points at that run | Checks API, run id in URL | match, internally consistent |
| v2.0.17 archived with identity values unchanged | flat field diff `HEAD prior[0]` vs `e7d0f72 published_release`: the **only** differing field is `notes` | matches how `cfc4a57` moved v2.0.16 (same single `notes` rewrite, same prepend at index 0); 4 → 5 entries, order `v2.0.17, v2.0.16, v2.0.15, v2.0.14, v2.0.13` |
| `local_candidate` published form | successor-only `checked_head`/`merge_commit`/`tree`/`pull_request`/`published_at`/`external_effect_scope` filled; `reviewed_product_head`/`reviewed_product_tree` still `null`; `external_effect` true **only** under `github_repository_delivery_and_release_only`; `operational_activation` false | per AC-003 |
| `current_unreleased_change` | `status` published / `stage` released_and_published, `tag_and_release` and `artifact_child` text name the live tag object, merge and Release; `next_action` points at pilot acceptance → M8 cohort → M9 qualification with no remaining publication step | per spec; shape identical to `cfc4a57` |
| landing ledger | `post_v2_0_17_landing.status` = `landed_in_v2_0_18_release`, rows {101,102,105,106} only — the chain's own #107/#108/SR are excluded per the #102 convention | match |
| `runtime_observations.evidence` | `…8c6e9e/evidence/runtime-observation-post-108.json` exists, `source_base` = e7d0f72, `observed_at` 13:56:33Z == top-level `observed_at`; `previous_dossier` `post-107` exists; MainPIDs 698333 / 3597736 and both units active+enabled re-confirmed live; `merged_source_not_installed` [101,102,105,106,107,108] and "no install/restart" limits kept | honest, no over-claim |
| no operational claim | README / START_HERE / ROADMAP / CHANGELOG / HANDOFF / `published_release.notes` / `local_candidate.notes` / dossier: nothing says installed, activated, hosting, cohort or deployment for v2.0.18 | FORBID-001 held |
| coupled suite | `python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package tests.test_change_spec` | **Ran 119 tests … OK** |
| lockstep test inversions | published-form asserts move exactly where `cfc4a57` moved them (`pending_tag_and_release`→`published_tag_bound`, `assertFalse(published)`→`assertTrue`, `assertNotEqual(observed_main_sha, merge_commit)`→`assertEqual`, the `("checked_head","merge_commit","tree")`-must-be-null loop narrowed to the two `reviewed_product_*` keys, `artifact_child.status` and `source_base`/`source_parent` de-aliased off `OBSERVED_MAIN_SHA`), and the AC-001 assertions the precedent added (`tag_object`, `published_at`, `merged_at`, GitGuardian run, prior[0] reindexing) are all kept | no dropped or weakened assertion beyond findings 4 and 5 below |
| CHANGELOG heading form | `## 2.0.18 — 2026-09-16` asserted by `tests/test_structure.py` in that exact prefix form | match |

## Findings

1. **Important — AC-004 is not met: `packages/README.md` still certifies a superseded release and denies the v2.0.18 tag/Release.**
   The file is untouched by this wave, so at HEAD it says, at line 3,
   "The latest published release is [`v2.0.17`](…), published `2026-09-16T01:17:14Z`, targeting `c86b1a19…`",
   and at line 31, "| `adaptive-grok-build-pro-v2.0.18.zip` | 2.0.18 (artifact delivered, tag and GitHub Release pending) |".
   Both are now false against live reality (tag object `31d3171f…`, Release `v2.0.18` published 13:52:24Z) and against this
   commit's own README/START_HERE/ROADMAP/`PROJECT_STATE` text. The typed AC-004 lists "packages/README row" as one of the
   surfaces that must say v2.0.18 is the published release, so this is a named acceptance criterion left unmet, not an
   adjacent nit. INV-001 does not block the repair — it protects only *earlier* `packages/` rows.
   *Precedent:* `cfc4a57` updated exactly these two spots (head line to v2.0.17 + its digests; row to
   "2.0.17 (published 2026-09-16T01:17:14Z)"); the release reviewer of #100 had listed "packages/README.md still certified
   v2.0.16 as the latest published release" among the twelve defects repaired before merge.
   *Required transitions:* line 3 → latest published `v2.0.18`, published `2026-09-16T13:52:24Z`, targeting
   `e7d0f72bf834b75eb543d9424ee47c7829cc65c0`, ZIP `0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a`,
   sidecar `dd7e2ec5a979d70062f206f381efcb38b92da2f7bfc1129034b459e125a54216`, keeping v2.0.17 as history; line 31 row →
   "| `adaptive-grok-build-pro-v2.0.18.zip` | 2.0.18 (published 2026-09-16T13:52:24Z) |".
   *Why the suite did not catch it:* the only test that reads `packages/README.md`
   (`tests/test_project_state.py:534-543`) forbids specific stale-M4 phrases; nothing asserts the latest-release line or the
   per-version table row, so green tests are not evidence for this surface.

2. **Important — the R/A package lifecycle rows the SR wave promised to close were not closed.**
   `engineering/changes/20260916-release-sync-2-0-17-to-2-0-18-identity-bump-r-wi-968b3c/tasks.md:10` states "the remaining
   R lifecycle rows move to the SR paperwork wave like the v2.0.17 chain's", and this is that wave, but neither R nor A
   package was touched (they are absent from the diff). `.../20260916-build-and-deliver-the-deterministic-v2-0-18-zip-f03c54/tasks.md`
   still carries three unchecked rows that this HEAD proves complete, so the package now asserts pending work that is done:
   - line 10 "Independent `security_review` and `release_review` receipts on the final fingerprint, plus `grok_verify --mode pr`."
   - line 11 "Open the pull request, merge only on the exact-head App check; then tag and publish, each under its own delegated grant."
     — PR #108 was opened and merged on App check `104809218211` (SUCCESS on `07d1141e`), tag `v2.0.18` (`31d3171f…`) and the
     GitHub Release with both assets are live.
   - line 12 "`SR` records `merge_commit`, `tree`, `checked_head`, `pull_request`, `published=true` and `published_at`."
     — this commit records all six.
   *Precedent, checked as instructed:* `#100` did **not** advance the R/A `state.json` — at `cfc4a57`,
   `...f98796/state.json` and `...31155d/state.json` are still `status: approved` and `git log` shows each was last written
   by its own commit (`78082a2`, `c86b1a1`); `cfc4a57` also left the SR's own package at `approved`. So **no `state.json`
   transition is required for `968b3c`/`f03c54` by precedent** (their current `implementing` status is already ahead of it).
   What `#100` did instead was flip the R and A `tasks.md` rows to `[x]` with concrete outcomes in the same SR commit — that
   is the missing transition here.
   *Required:* mirror `cfc4a57`'s `31155d` edit — check lines 10-12 of `f03c54/tasks.md` with the observed outcome (receipts +
   `grok_verify` result, PR #108 / merge `e7d0f72…` / App check `104809218211`, tag object `31d3171f…`, and this SR's route
   `8c6e9e30b239` and package id); re-check the 968b3c promise once that is done so no row in the chain reads false.

3. **Minor — two current-state sentences still call v2.0.18 a candidate.** `README.md:11` "…PR #105 … are part of this
   candidate's source" and `GROK_BUILD_HANDOFF.md:306` "PRs #101, #102, #105 and #106 are merged as the source of the 2.0.18
   candidate". Both were true at A and are false at HEAD; neither is asserted by any test. `cfc4a57` left
   `GROK_BUILD_HANDOFF.md` with zero occurrences of "candidate". Fix the wording (ROADMAP:98 already reads "as the source of
   `2.0.18`").

4. **Minor — one assertion lost, one duplicated in `tests/test_project_state.py`.** A's form asserted
   `self.assertTrue(local["artifact_child"]["zip_source_note"])`; this wave deletes it (the `zip_source_note` field itself
   survives in the record, so nothing fails), leaving the pre-publication-snapshot caveat unasserted — the `cfc4a57` test
   file has no such assertion either, so this is parity with the precedent at the cost of coverage the v2.0.18 chain had.
   Lines 434-435 are byte-identical duplicates of
   `self.assertTrue(local["artifact_child"]["requirement"])`; drop one.

5. **Minor — the published GitHub Release body cites the wrong App run and the record does not disclose it.**
   `gh api …/releases/tags/v2.0.18` body: "…after the App-owned exact-head check `adaptive-trust-ci/verified@06ecf1c875bc`
   (run 104782126773 lineage, PR #108)". `104782126773` is PR #107's run (the value `trust_ci.last_success` held before this
   wave); PR #108's run is `104809218211`. Every in-tree value is correct, so this is not a record defect, but the successor
   whose whole purpose is "the record agrees with reality everywhere" leaves an externally visible mis-citation about merge
   authority unmentioned. The Release body cannot be corrected by a Git change (it needs its own delegated action) — record
   the discrepancy in the change package evidence, or amend the Release text under an exact grant.

6. **Nice to have — typed spec declares `risk.tier: red` where the followed precedent deliberately chose `yellow`.**
   `cfc4a57`'s spec is `yellow` with `pull-request-merge` only, with the stated reason "instead of over-stating risk" for a
   records-only successor. The red tier is still satisfiable here (both `forbidden_outcomes` and
   `approvals.required_scopes` are present, per `.grok-stack/adaptive_grok/spec.py:754-758`), and it over-states rather than
   under-states, so nothing is weakened — but it is a divergence from the declared field-for-field mirror.

7. **Nice to have — `mistakes.md` untouched.** The defect class the #100 reviewer named (a release-facing file certifying a
   superseded latest published release) recurs here, and `mistakes.md` has no entry for it (no `packages/README` or
   "latest published release" entry exists in `mistakes.md`/`decisions.md`). `AGENTS.md` asks for the root cause to be
   recorded when a mistake leads to a problem.

## Precedent comparison summary

Against `cfc4a57` this wave is faithful on `published_release` completeness, the single-`notes` archive rewrite and prepend
position, the `local_candidate` published form (including the two nulls and the scope-gated `external_effect`), the
`current_unreleased_change` status/stage/`external_effect`/`record_scope` shape, the `active_delivery` + `trust_ci.last_success`
follow-through, the landing-status flip with release-chain rows excluded, the CHANGELOG heading form, and every lockstep test
inversion. It falls short in exactly two places the precedent covered: `packages/README.md` was one of the six surfaces
`#100` moved at SR and was not moved here (finding 1), and `#100` closed its own chain's R/A `tasks.md` rows at SR while this
wave's R row defers them to a wave that has now passed without doing them (finding 2). Neither gap is a trust-boundary or
record-accuracy defect in `PROJECT_STATE.json` itself; both are the change failing its own AC-004 and its own promised
lifecycle closure. Rollback is honest: `forward_fix` ≤1 restores the pre-publication candidate shape and the file correctly
says reverting does not un-publish the external tag and Release.

## Limits

- Verified live: `git ls-remote`, `gh pr view 108`, GitHub Checks API (run list + run output summary), Releases API
  (assets, digests, sizes, timestamps, bodies), tracked-blob `sha256sum`, `git rev-parse`/`cat-file`, read-only `systemctl show`.
  Both attestation UUIDs were taken from the App check-run output text, not from the Trust CI API or its signing keys, and
  nothing was read from any key, approval or credential store.
- The full local PR gate (`python3 scripts/grok_verify.py --mode pr`) was **not** run: `tasks.md:8` of this package still has
  it unchecked, it writes into the verified tree, and the route's `verification` receipt is the parent's to bind. The 119-test
  coupled suite is green independently and was re-run by this review; `test_change_spec` covers the spec module's own unit
  tests, not this package's gate, so no claim is made here that the spec passes the PR gate.
- This successor has no pull request yet at review time (`gh pr list --state open` → `[]`), so no exact-head App check exists
  for `28de12c`; the route's `security_review` and `release_review` receipts and the `verification` evidence remain outstanding.
- Not evaluated: `grok_verify` results for earlier chain heads, deployed Trust CI policy/holdout, branch protection, and any
  operational state beyond the two installed L5 units.
