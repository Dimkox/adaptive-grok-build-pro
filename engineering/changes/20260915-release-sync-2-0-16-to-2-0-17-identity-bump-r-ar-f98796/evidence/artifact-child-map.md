# Artifact-child (A) map for v2.0.17 — derived from the v2.0.16 precedent diff

Source of truth for this map: `git diff 287b27ac507a1089726c7cb8ce461f1c550f0b07 2b1517986b9b5b83a95b1286baac161074c58175`
(the v2.0.16 R merge → its artifact-child head), re-read on 2026-09-15. Values below are the
*v2.0.16 literals*; substitute the `v2.0.17` identities when executing. Placeholders are `<...>`.

## Build (before any commit)

```bash
bash /tmp/build_release_artifact.sh <repo> <R-MERGE-SHA> 2.0.17
# two independent exact-SHA clones, umask 077, 0700 staging; prints ZIP_SHA256 / ZIP_BYTES
```

Sidecar content is exactly `"<zip-sha>  adaptive-grok-build-pro-v2.0.17.zip\n"` (two spaces), as
asserted by `tests/test_manifest_package.py`.

## Files A touches (11 in the precedent)

1. `packages/adaptive-grok-build-pro-v2.0.17.zip` (new bytes)
2. `packages/adaptive-grok-build-pro-v2.0.17.zip.sha256` (new)
3. `packages/README.md` — one table row `| adaptive-grok-build-pro-v2.0.17.zip | 2.0.17 (artifact delivered, tag pending) |`
4. `PROJECT_STATE.json` — see below
5. `tests/test_project_state.py` — see below
6. `tests/test_manifest_package.py` — `artifact_status` expectation
7–11. this change package: `state.json`, `tasks.md`, and the docs whose wording changes with delivered bytes

## PROJECT_STATE.json deltas

| Key | R (now) | A |
| --- | --- | --- |
| `observed_at` | `2026-09-15T22:59:00Z` | fresh UTC timestamp |
| `observed_main_sha` | `7bbf4252…` | **R merge commit** |
| `local_candidate.status` | `pending_release` | `artifact_bytes_delivered` |
| `local_candidate.source_base` | `7bbf4252…` | **R merge commit** |
| `local_candidate.artifact_status` | `pending_unpublished_artifact_child` | `pending_tag_and_release` |
| `local_candidate.artifact_child.source_parent` | `null` | **R merge commit** |
| `local_candidate.artifact_child.source_parent_tree` | `null` | **R merge tree** |
| `local_candidate.artifact_child.zip_sha256` | `null` | built zip digest |
| `local_candidate.artifact_child.sidecar_sha256` | `null` | sidecar file digest |
| `local_candidate.artifact_child.status` | `not_built` | `built_byte_reproducible_twice` |
| `local_candidate.artifact_child.requirement` | pending wording | `Tag v2.0.17 and the GitHub Release bind to the exact merged commit of this artifact-child pull request; published stays false and merge_commit/tree stay null until the post-merge documentation successor records the tag binding.` |
| `local_candidate.artifact_child.zip_source_note` | absent | archive built from R merge `<R-MERGE-SHA>`; A's record/doc/test bytes are deliberately outside the archive (v2.0.15 pre-publication snapshot caveat) |
| `local_candidate.notes` | candidate-not-built wording | bytes-in-tree only; no tag, no Release, no external effect, no activation |
| `current_unreleased_change.artifact_child` | `Not built…` | delivered, tag pending |
| `current_unreleased_change.stage` | `identity_bump_in_pull_request` | `artifact_child_delivered_pending_tag` |

**Must stay** `false`: `published`, `external_effect`, `operational_activation`.
**Must stay `null`** (A cannot self-record): `local_candidate.checked_head`, `merge_commit`, `tree`,
`pull_request`, `artifact_child.commit`, `artifact_child.tree`, `reviewed_product_head`,
`reviewed_product_tree`. SR fills them.

## Test literal deltas (exactly these)

- `tests/test_project_state.py`: `OBSERVED_MAIN_SHA = "<R merge sha>"  # current main tip (PR #<R> release-sync merge)`
- `local["status"]` → `artifact_bytes_delivered`; `local["artifact_status"]` → `pending_tag_and_release`
- `assertIsNone(zip_sha256/sidecar_sha256)` → `assertEqual(..., "<digest>")`
- the null-pin loop splits: `commit`/`tree` stay pinned null unconditionally, while
  `source_parent`/`source_parent_tree` are only required null while
  `artifact_status == "pending_unpublished_artifact_child"` (guard with `if`/`else`)
- `tests/test_manifest_package.py`: `'pending_unpublished_artifact_child'` → `'pending_tag_and_release'`
  in the `artifact_status` assertion; the existence branch already switches on `artifact_status`, so
  the delivered-bytes path (both files exist, sidecar matches zip digest) activates without an edit.

## After A merges (tag + Release + SR)

1. `git tag -a v2.0.17 <A-merge-sha>` with message `Adaptive Grok Build Pro v2.0.17; protected PR #<A>; <subtitle>`
2. GitHub Release: hand-written body (`--notes-file`, never `--generate-notes`), `isDraft=false`,
   `isPrerelease=false`, latest, two assets = zip + sidecar
3. SR commit: `published=true`, `published_at`, `merge_commit`/`tree`/`checked_head`/`pull_request`
   for A, `artifact_child.commit`/`tree`, `tag_object`, `external_effect=true` scoped to
   `github_repository_delivery_and_release_only`, `operational_activation` **still false**,
   `current_unreleased_change` closed, `local_candidate` record archived verbatim into
   `delivered_change_history` as the precedent does.

## Gate caveat for A

`architecture diff analysis rejects >10 MB tracked binaries it never reads` (issue #80) is a known
local-only false red on artifact-child PRs: the **external** App check is authoritative.
