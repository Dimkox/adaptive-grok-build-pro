# Analysis — repo_explorer (merge)

Change: `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090`  
Route: `e2b4b7341a5c` · task: «смерджи все» · write owner: `general_implementer`

Read-only. No `git status` / `git log` / `git push` / `git merge`. Facts from local refs, working tree, and public GitHub API `https://api.github.com/repos/Dimkox/adaptive-grok-build-pro`.

---

## 1. Local HEAD vs origin/main

| Ref | SHA / value | Source |
| --- | --- | --- |
| Branch | `main` | `.git/HEAD` → `ref: refs/heads/main` |
| Local `refs/heads/main` | `7c0ae7573535ddd0cfe3800f81278991ced81584` | `.git/refs/heads/main` |
| Message | `Release v2.0.5: hook shims, toolchain pins, track zip and checksum` | `.git/COMMIT_EDITMSG:1` |
| Parent of HEAD | `33a02f1128ab0a865bfb1c853248f997dcf9e39b` | `.git/logs/HEAD` last line: `33a02f1… 7c0ae75… commit` |
| Local `refs/remotes/origin/main` | `33a02f1128ab0a865bfb1c853248f997dcf9e39b` | `.git/refs/remotes/origin/main` |
| `FETCH_HEAD` | same `33a02f1` (`branch 'main' of https://github.com/Dimkox/adaptive-grok-build-pro`) | `.git/FETCH_HEAD:1` |
| GitHub `GET /commits/main` | same `33a02f1` — `Release v2.0.4: track zip and checksum` | public API |
| GitHub `GET /commits/7c0ae75…` | **422** `No commit found for SHA` | public API |
| GitHub compare `33a02f1...7c0ae75` | **404** (right side not on GitHub) | public API |
| `origin` URL | `https://github.com/Dimkox/adaptive-grok-build-pro.git` | `.git/config:9-10` |
| `branch.main.merge` | `refs/heads/main` | `.git/config:12-14` |

HEAD is **1 commit ahead** of `origin/main`. That commit is **not** on GitHub.

### Other local branches

None. `.git/refs/heads/` contains only `main`. No `.git/packed-refs`. No `.git/refs/stash`. No `MERGE_HEAD`, `CHERRY_PICK_HEAD`, or `.git/rebase-merge/`.

### Other remote branches

GitHub `GET /branches` returns only `{name: main, commit: 33a02f1…, protected: false}`. Local remotes: only `refs/remotes/origin/main`.

### Open GitHub PRs

- `GET /repos/Dimkox/adaptive-grok-build-pro/pulls?state=open` → `[]`
- `GET /repos/Dimkox/adaptive-grok-build-pro/pulls?state=all&per_page=10` → `[]`

No open PRs. No PRs in the first page of all-state PRs.

---

## 2. Unpushed commits. Uncommitted paths. Tag v2.0.5

### Unpushed

Exactly one commit, on `main`, parent = current `origin/main`:

```
33a02f1128ab0a865bfb1c853248f997dcf9e39b  (origin/main, tag v2.0.4)
        └── 7c0ae7573535ddd0cfe3800f81278991ced81584  (local main; not on origin)
```

Reflog line: `.git/logs/refs/heads/main` last entry `33a02f1… 7c0ae75… commit: Release v2.0.5: hook shims, toolchain pins, track zip and checksum`.  
`origin` reflog last event is the push of `33a02f1` (`.git/logs/refs/remotes/origin/main` last line). No later `update by push`.

Recorded in `evidence/implementation.md:35-40`: 121 files, +4301 / −67. Tag `v2.0.5` still absent at that write.

### Uncommitted / dirty (no `git status`; listed from tree + post-commit reports)

**Written after `7c0ae75` and not in that commit** (`implementation.md:46`; reviews name HEAD `7c0ae75`):

- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/implementation.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/code-review.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/test-review.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/state.json` — `updated_at` `2026-08-15T02:51:12+00:00` (`state.json:64`); commit unix `1786761740` ≈ 02:42:20Z (`33a02f1` at 01:27:19Z + 4501s). Status now `ready` (`state.json:62`).
- this file (`evidence/analysis-repo_explorer-merge.md`)

**Deleted after commit, now absent:** root `MANIFEST.sha256` (`implementation.md:122-124`; read of that path: does not exist).

**Gitignored, present, must stay out of any add** (`.gitignore:1-27`):

- `.grok-stack/runtime/*` except `.gitkeep` — live `active-route.json`, `receipts/e2b4b7341a5c/`, `receipts/ad4090c51ca6/`, `receipts/e85418e33648/`, etc.
- `err.log` (root listing; `.gitignore:14-15`)
- `dist/` including `dist/adaptive-grok-build-pro-v2.0.5.zip*`, `dist/RELEASE-NOTES.md`, `dist/HANDOFF.md`
- `tests/__pycache__/`, `scripts/__pycache__/`
- `.env` / `.env.*` — ignored (`.gitignore:6-8`). Not read.

**Not git status-verified:** any silent edit to files already inside `7c0ae75`. `VERSION` working tree is `2.0.5` (`VERSION:1`); `CHANGELOG.md:3` is `## 2.0.5`; `packages/README.md:12` has the 2.0.5 zip row; sibling digest `packages/adaptive-grok-build-pro-v2.0.5.zip.sha256:1` is `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd`. Those match the committed 2.0.5 product described in `implementation.md:31-42`.

### Tag v2.0.5

| Place | v2.0.5 |
| --- | --- |
| Local `.git/refs/tags/` | **absent**. Present: `v2.0.0` … `v2.0.4` only |
| Local `.git/refs/tags/v2.0.4` | annotated object `10c522f294bc5ffbdbef32d1487af59ff4e8453b` |
| GitHub `GET /git/refs/tags/v2.0.5` | **404** |
| GitHub `GET /releases/tags/v2.0.5` | **404** |
| GitHub `GET /tags` | `v2.0.4` (commit `33a02f1`), `v2.0.3`, `v2.0.2`, `v2.0.1`, `v2.0.0` — no `v2.0.5` |

---

## 3. GitHub latest release tag

`GET /repos/Dimkox/adaptive-grok-build-pro/releases/latest`:

| Field | Value |
| --- | --- |
| `tag_name` | **`v2.0.4`** |
| `id` | `370918434` |
| `name` | `Adaptive Grok Build Pro v2.0.4` |
| `html_url` | https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.4 |
| `target_commitish` | `main` |
| `published_at` | `2026-08-15T01:27:26Z` |
| assets | `adaptive-grok-build-pro-v2.0.4.zip` (`sha256:e76cd399…`), `adaptive-grok-build-pro-v2.0.4.zip.sha256` |

`GET /releases?per_page=5` first item is the same `v2.0.4`. Older tags on that list: `v2.0.3`, `v2.0.2`, `v2.0.1`, `v2.0.0`. No `v2.0.5` release.

---

## 4. Merge vs fast-forward push

**There is nothing to `git merge`.**

- One local branch (`main`) and one remote branch (`origin/main`).
- No second branch, no PR, no `MERGE_HEAD`.
- Local `main` is a **direct child** of `origin/main`: `33a02f1` → `7c0ae75`.
- A `git push origin main` from this HEAD would be a **fast-forward** of `main` by that one commit.
- `git merge` of any other ref is a no-op: there is no other ref to merge.

Not done (and not a merge): tag `v2.0.5`, `git push origin v2.0.5`, `gh release create v2.0.5`. Those are still absent locally and on GitHub (`implementation.md:65`, `tasks.md:7`).

This agent did not push, merge, tag, or deploy.
