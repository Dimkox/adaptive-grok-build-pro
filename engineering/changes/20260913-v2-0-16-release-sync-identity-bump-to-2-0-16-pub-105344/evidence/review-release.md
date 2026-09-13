# Release review — v2.0.16 release-sync (R = 55364a4)

**Verdict: PASS** — R is mergeable as the 2.0.16 release-sync commit. Two minor doc findings, neither blocking.

## 1. Main self-consistency at 55364a4 — PASS
Worktree `/home/pall/grok-projects/adaptive-grok-build-pro-release-sync` HEAD = `55364a4`, clean.
```
$ python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package -q
----------------------------------------------------------------------
Ran 89 tests in 8.123s

OK
```
State reads `VERSION=2.0.16`, `product_version=2.0.16`, `published_release.tag=v2.0.15`,
`local_candidate.status=pending_release`, `artifact_status=pending_unpublished_artifact_child`,
`published=false`, `external_effect=false`. Consistent with "2.0.16 candidate / v2.0.15 published".

## 2. R→A ordering vs precedent — PASS (with a framing correction)
- v2.0.14 is the true R→A pair: `5b33a38` (docs, **no** zip) → `66a7fe5` (adds `v2.0.14.zip`, blob `9315208`)
  → squash `1751b58` → annotated tag `v2.0.14` → `1751b58`, same zip blob. Matches release.md exactly.
- v2.0.15 is **not** an R→A pair: `9fcc9d9` is PR #27 *checked head* and **already carried the zip**
  (blob `3f27187`); `fd51dcf` is its squash merge with the identical blob. So `9fcc9d9→fd51dcf` = head→merge,
  not R→A. It confirms the tag-target rule but is not evidence for a two-commit split.
- Tag targets: `v2.0.14 → 1751b58` contains the zip; `v2.0.15 → fd51dcf` contains the zip. Both annotated
  (`objecttype tag`), both GPG-signed, both squash merges (single parent). Planned rule
  "tag + Release bind to A's exact merged commit, zip built from merged R tree" **matches precedent**.
- Deviation, acceptable and forced: v2.0.14/15 put R and A in one PR; v2.0.16 makes A its own PR because the
  zip must be built from R's *merged* tree, which does not exist until R merges.

## 3. Rollback claim — TRUE
`git ls-tree -r 55364a4 | grep 2\.0\.16` → none; no `packages/*v2.0.16*`. Latest tag `v2.0.15`
(remote `refs/tags/v2.0.15 → fd51dcf`), latest Release `v2.0.15`. Base `1a8c891` = `origin/main`;
range `1a8c891..55364a4` = 1 commit. "Revert this single commit, nothing external created" holds.

## 4. Minimal edit set for A (checklist for next task)
- [ ] `packages/adaptive-grok-build-pro-v2.0.16.zip` — built in 0700 staging from R's merged tree, byte-reproduced twice
- [ ] `packages/adaptive-grok-build-pro-v2.0.16.zip.sha256`
- [ ] `PROJECT_STATE.json` → `local_candidate`: `status`, `artifact_status`, `published`, `notes`, and
      `artifact_child.{source_parent, source_parent_tree, commit, tree, zip_sha256, sidecar_sha256, status: not_built→…, requirement}`
- [ ] Test-literal flips (6 mandatory):
      - `tests/test_project_state.py:372` `status "pending_release"`
      - `tests/test_project_state.py:377` + `tests/test_manifest_package.py:1426` `artifact_status "pending_unpublished_artifact_child"` (2 sites)
      - `tests/test_project_state.py:378` `assertFalse(published)`
      - `tests/test_project_state.py:381,382` `assertIsNone(zip_sha256 / sidecar_sha256)`
      - conditional only, **no edit**: `tests/test_manifest_package.py:1434-1438` already branches on `published`
      - optional (4): `test_project_state.py:373-376` `route_id/branch/pull_request/change_package` assertIsNone, only if A fills them
      - unchanged by design: `test_manifest_package.py:1422,1439`, `test_project_state.py:371`, `test_structure.py:254-259`
- [ ] `packages/README.md` — add v2.0.16 table row; fix stale v2.0.15 wording (see F1)
- [ ] Keep `external_effect=false`, `operational_activation=false`; do **not** move v2.0.15 into `prior_published_releases`
- [ ] A cannot self-record its own `merge_commit`/`tree` → a doc-only post-A successor is expected (same as v2.0.15)

## 5. GitHub Release content (reuse v2.0.15 style)
Hand-written markdown, **not** `--generate-notes`. `name`: `Adaptive Grok Build Pro v2.0.16 — <subtitle>`;
`isDraft=false`, `isPrerelease=false`, marked Latest; 2 assets = zip + `.zip.sha256` (label empty).
Sections: `## Delivered` bullets → `## Exact delivery evidence` (PR URL, `Checked head`, `Protected squash merge`,
identical tree, App `4694114` + `adaptive-trust-ci/verified@<sha12>` run/attestation/signer, ZIP + sidecar SHA-256)
→ `## Explicit limits and next step` → rollback line. Length: v2.0.14 body = 533 chars, v2.0.15 = 3665.
Prefer v2.0.14 brevity + v2.0.15 evidence block. Tag message style: `Adaptive Grok Build Pro v2.0.16; protected PR#NN; <subtitle>`.
Must carry the v2.0.15 caveat verbatim in spirit: the zip/tag preserve the pre-publication snapshot, so README/
START_HERE/PROJECT_STATE candidate wording inside the artifact is historical.

## Findings
- **F1 (Suggestion, low)** — `packages/README.md` still calls `v2.0.15.zip` a "local unpublished candidate; artifact child A"
  and has no v2.0.16 row, while `PROJECT_STATE.json` records v2.0.15 as published and `gh release view v2.0.15` confirms
  publication. Not test-covered (no test references `packages/README`), which is why R passed green. Fix in R-amend or A.
- **F2 (Nice to have)** — `local_candidate.published` flips true in A, before tag/Release exist. Intended reading is
  "artifact bytes delivered into the tree", not "GitHub Release published"; make that explicit in the `notes` text so the
  field cannot be mistaken for merge/publication authority.
