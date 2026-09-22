# Repository exploration: v2.0.19 release-sync readiness

Observed 2026-09-22 after `git fetch --all --prune`. This was a read-only inspection except for this report; the full verifier was not run.

## Decision

**Not ready to checkpoint or submit the release-sync PR.** The intended source chain and product identity are coherent, and immutable `v2.0.18` is preserved, but the release-sync edits are still uncommitted, the active typed change specification is invalid, and required verification/review evidence is absent.

## Exact source identity

- Fetched `origin/main` and route source base: `130ce4a42d9f9bbd1b56772d40b19ae530283205` (tree `3b51c9d21550627bb35fdb06753d2bedd5cf97ff`).
- Worktree branch: `release/v2.0.19-candidate-20260922`.
- Current `HEAD`: `5d93fc3d68869ab26799935adab5fa62be5e2a80` (tree `794e7623b8c1551528147b949342ca477c2f1b46`), with merge-base equal to the fetched source base.
- `HEAD` is seven commits beyond the source base; those commits are the exact candidate named by the task. The uncommitted release-sync layer is therefore **not** represented by the current HEAD/tree.

## Changed product paths

The release-sync layer has 11 unstaged product changes and no staged changes:

`VERSION`, `.grok-stack/adaptive_grok/__init__.py`, `README.md`, `CHANGELOG.md`, `DARK_FACTORY_ROADMAP.md`, `START_HERE.md`, `GROK_BUILD_HANDOFF.md`, `PROJECT_STATE.json`, `tests/test_structure.py`, `tests/test_project_state.py`, and `tests/test_manifest_package.py`.

From source base through candidate HEAD, the candidate also changes `decisions.md`, `mistakes.md`, `engineering/runbooks/l5-runtime-observation-2026-09-15.md`, `trust-ci/README.md`, `trust-ci/config/policy.example.json`, `tests/test_structure.py`, and the committed `20260922-consolidate-...-b26dff` evidence package. Two additional change-package directories are currently untracked: the active release package and `20260922-prepare-v2-0-19-release-candidate-from-the-verif-219603`.

## Immutable v2.0.18 preservation

- Annotated tag object: `31d3171f651ea77e29de58d4affc58d008f1c7a5`.
- Tag target: `e7d0f72bf834b75eb543d9424ee47c7829cc65c0`; release tree: `c78d200ee6a6a7ab1e32f2194691a8e639b9dab3`.
- ZIP SHA-256: `0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a`.
- Sidecar SHA-256: `dd7e2ec5a979d70062f206f381efcb38b92da2f7bfc1129034b459e125a54216`; its recorded ZIP digest matches.
- `git diff v2.0.18 --` for the v2.0.18 ZIP and sidecar is empty, and neither path is dirty.

## Package and release identity

- `VERSION`, runtime `__version__`, README heading/identity, changelog, roadmap, and `PROJECT_STATE.product_version` agree on candidate `2.0.19`.
- `PROJECT_STATE` keeps `latest_published_release` at `v2.0.18`, binds the candidate source base to `130ce4a...`, marks the candidate unpublished, and records operational activation/external effect as false.
- `packages/adaptive-grok-build-pro-v2.0.19.zip` and its `.sha256` sidecar are absent, consistent with `artifact_status: pending_unpublished_artifact_child` and `artifact_child.status: not_built`.
- State inconsistency: `current_unreleased_change.change_id` contains the full `engineering/changes/...` path, while the route, state, spec, gates, and brief use the bare change ID. `change_package` already carries the path.

## Concrete blockers / next gates

1. Checkpoint the 11 release-sync product edits so the reviewed identity has an exact commit/tree; currently HEAD still names only candidate `5d93fc3`.
2. Repair `change-spec.yaml`: `python3 scripts/grok_spec.py validate --change-id 20260922-release-v2-0-19-from-candidate-5d93fc3-0ea342` fails because `$.observability[0].proves[1]` does not match the schema (the signal lists acceptance-criterion IDs where the schema permits only the objective ID).
3. Normalize `PROJECT_STATE.current_unreleased_change.change_id` to the bare change ID, and deliberately include or exclude the unrelated untracked predecessor package before checkpointing.
4. After the tree is frozen, run the route-required verification and independent code, test, security, and release reviews. `grok_status` currently reports all five receipts as `not_run` and package completeness as invalid.
5. The v2.0.19 ZIP/sidecar must remain absent from this release-sync change; build them only from the merged, exact release-sync parent in the separate artifact-child change. Protected delivery still requires the App-owned exact-head check and fresh action-bound grants.
