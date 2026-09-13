# Release review — `eb9df64..4e71afa` (branch `feature/l5-post-landing-hardening`)

## Verdict: PASS (conditional — merge only after the exact-SHA App check exists; release-sync PR is mandatory follow-up)

## 1. Ship-before-bump self-consistency — HOLDS
`VERSION` = `2.0.15` (repo root `/VERSION`). This diff touches none of `VERSION`, `CHANGELOG.md`, `README.md`,
so after merge main still satisfies the version-coupled assertions (`tests/test_structure.py:254,256,257,259`,
`tests/test_project_state.py:89`, `tests/test_manifest_package.py:1421-1423`). Deferred sync is test-visible-safe.
Pre-existing defect this diff exposes but does not create: tag `v2.0.15` (`fd51dcfe…`, 2026-09-05) **is already
published** — GitHub Release `v2.0.15`, `isDraft=false`, `isPrerelease=false`, "Latest", assets
`adaptive-grok-build-pro-v2.0.15.zip` (digest `1f0f64557fd2…`, matches tracked `packages/` copy) + `.sha256`
(`8f3ed4b8…`) — while CHANGELOG head says `(unreleased)`, README says "remains unpublished" and
`PROJECT_STATE.json` `published_release.tag` is `v2.0.14`. A published tag cannot be reused (no tag rewrite).

### Release-sync PR must update (VERSION candidate = **2.0.16**; 2.1.0 collides with trust-ci service identity 2.1.0)
1. `VERSION` → `2.0.16`; `PROJECT_STATE.json` `product_version` → `2.0.16`, `published_release` block → v2.0.16 record.
2. `CHANGELOG.md`: restate the existing 2.0.15 section as published (tag `fd51dcfe…`, 2026-09-05T20:17:20Z, zip/sidecar SHAs) and add `## 2.0.16` covering the L5 A–G union landing (#65 + #75 → `eb9df64`) plus this hardening commit.
3. `README.md`: H1, the `Identity: **2.0.15**` bullet, and **Current state** — it still says "The assembled L5 source on `feat/l5-split-g-final-runtime`" while this commit's `l5_production_preparation.branch` is now `main`/`landed_main_commit eb9df64`. Stack graph (231 edges) and role table unchanged unless nodes are added.
4. Version-coupled test constants in lockstep: `tests/test_structure.py:254,256,257,259`; `tests/test_project_state.py:89`; `tests/test_manifest_package.py:1422-1423`.
5. `packages/adaptive-grok-build-pro-v2.0.16.zip` + `.sha256` as the artifact-only child commit `A` (R+A pattern); tag `v2.0.16` from the exact merged source commit; update `l5_production_preparation.next_action` (hardening no longer "in flight").

## 2. Rollback claim "forward_fix, revert one commit" — VERIFIED, no state-format change
Semantic `PROJECT_STATE.json` diff is 1 removed key (`l5_production_preparation.source_predecessor`), 3 added
(`landed_at`, `landed_main_commit`, `landing_method`), 3 changed values (`branch`, `next_action`, `status`); the
other ~330 diff lines are inline-object re-indenting. Top-level `schema_version` stays `2`, key count stays 24.
`grep -rn l5_production_preparation scripts/ tests/ .grok-stack/` → **zero matches**. Repo-wide only mentions are
docs (`START_HERE.md:36`, split-G evidence instruction). `git grep source_predecessor eb9df64` → only its own
definition (`PROJECT_STATE.json:762`), so removing it breaks no consumer; the changed status string has no consumer
either. Only `tests/test_project_state.py` and `tests/test_manifest_package.py` read PROJECT_STATE — both green.
No `.sql`/migration/schema path; `architecture/rules.yaml`, `architecture/`, `trust-ci/`, `delivery/`, `adaptive_grok/`
untouched. Sealed digests unaffected: `_approved_deploy_members` is a pure validator returning the same tuple for all
three epochs (member lists unchanged), so prior sealed artifacts stay reproducible; the new import-time call fails
closed. Caveat: any revert changes PROJECT_STATE.json, so fingerprint-bound local receipts sealed against a tree
containing it go stale — expected, not a blocker.

## 3. Observable success signal — matches release.md, but NOT YET OBSERVABLE
`release.md` declares exactly one merge requirement: App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on the
exact head. Branch is pushed at `4e71afa` but **no PR exists** (`gh pr list --head feature/l5-post-landing-hardening`
→ empty), so the signal is unsatisfiable at review time: do not merge before it appears on that SHA.
Local (non-authority) preflight, pristine clone of `4e71afa`: `tests.test_structure`+`test_project_state`+
`test_architecture_model` → 100 OK; `factory.tests.test_landing_artifact`+`test_landing_pdf_worker` → 16 OK / 4 skipped;
`tests.test_manifest_package` → 56 OK. Two weaknesses: (a) the four real-execution PDF cases (#63's headline) skip
unless `pypdf==6.18.1` is importable by the isolated child — absent in the default interpreter (no `.venv`; pinned only
in `factory/pyproject.toml`), so only `parser_unavailable` + input-guard paths run by default; record which env the
verifier uses. (b) The sibling review reports (`evidence/review-code.md`, `evidence/review-security.md`, this file) are
**untracked**, i.e. not in the tested tree; committing them creates a new head SHA requiring a fresh exact-SHA check.

## 4. Merge order vs in-flight #72 — NO COLLISION
#72 (`docs/l5-split-verification-evidence`, head `05e7ff6`, MERGEABLE) = 100 files via paginated API, all under
`engineering/changes/20260913-l5-split-*`; intersection with this diff's 16 files is **empty**. `eb9df64` is already an
ancestor of `05e7ff6`, and neither PR edits `PROJECT_STATE.json`/`README`/`CHANGELOG`/tests the other touches, so both
orders are conflict-free. Whichever lands second must re-merge main → new head SHA → new App check (both orders).
Also checked: PRs #64 (19 files) and #33 (32 files) → zero intersecting paths.
