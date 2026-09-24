# Documentation and provenance audit — `docs_researcher`

Scope: read-only comparison of the current `/tmp/agbp-release-2019` release-sync worktree at Git `HEAD` `5d93fc3d68869ab26799935adab5fa62be5e2a80` against the published `v2.0.18` precedent, covering `README.md`, `START_HERE.md`, `DARK_FACTORY_ROADMAP.md`, `GROK_BUILD_HANDOFF.md`, `PROJECT_STATE.json`, `packages/README.md`, and coupled test literals. No long tests were run.

## Findings

1. **Package documentation points at the wrong state record (must fix).** `packages/README.md:43` says published `2.0.16` is verified against `PROJECT_STATE.json.published_release`. In the current state, `published_release.tag` is `v2.0.18`; `v2.0.16` is `prior_published_releases[1]`. Replace `2.0.16` with `2.0.18`, or describe lookup generically as newest release in `published_release` and older releases in `prior_published_releases`.

2. **The input candidate commit is presented as the current release-sync tree (must clarify).** `README.md:11` says the `v2.0.19` candidate “continues on exact tree `5d93fc3...`”, and `START_HERE.md:9` calls that SHA the “candidate tree”. That SHA is the current Git commit/input candidate, while the release-sync changes are uncommitted and `PROJECT_STATE.json.local_candidate.reviewed_product_head` / `reviewed_product_tree` are correctly `null` pending a frozen checkpoint. Call `5d93fc3...` the **input/source candidate commit** and explicitly leave the release-sync head/tree pending; otherwise readers can incorrectly treat a pre-sync commit as the reviewed 2.0.19 release tree.

3. **`current_unreleased_change.change_id` is a path, unlike the v2.0.18 precedent and the active route (should fix).** `PROJECT_STATE.json:207` stores `engineering/changes/20260922-release-v2-0-19-from-candidate-5d93fc3-0ea342`, while `change_package` stores the same path and the route/state use bare change ID `20260922-release-v2-0-19-from-candidate-5d93fc3-0ea342`. Restore the bare ID in `change_id`; keep the repository path only in `change_package`. Add a coupled assertion because current tests verify `change_package` but not `current_unreleased_change.change_id`.

4. **The package test describes a two-state contract but hard-codes only the first state (should fix before artifact child).** `tests/test_manifest_package.py:1424-1438` first requires `artifact_status == 'pending_unpublished_artifact_child'`, then contains an `else` intended to validate delivered candidate bytes. The `else` is unreachable under that literal and will fail before validating an artifact-child state. Assert an allowed state set and validate each state, or split release-sync and artifact-child tests. Also add a package-doc assertion for finding 1; current lockstep tests do not inspect `packages/README.md`.

5. **The bootstrap calls dated backlog data current (should qualify).** `START_HERE.md:19` says “current counts and scope live in PROJECT_STATE.json”, but `PROJECT_STATE.json.parallel_issue_work.observed_at` remains `2026-09-21T12:05:39Z` while the top-level observation is `2026-09-22T23:35:00Z`; it still reports 52 open issues and several deliveries as pending. Either refresh that nested inventory or call it a dated snapshot rather than current.

## Consistent surfaces

`VERSION`, runtime `__version__`, README identity, changelog heading, roadmap identity, `PROJECT_STATE.json.product_version`, and the principal structure/project-state literals consistently name unpublished `2.0.19`. The immutable `v2.0.18` tag target, artifact hashes, publication timestamp, and “no 2.0.19 package yet” boundary remain consistent. The fifteen post-`v2.0.18` landing rows match the first-parent history through PR #185, and no tracked `v2.0.19` ZIP or sidecar is present.
