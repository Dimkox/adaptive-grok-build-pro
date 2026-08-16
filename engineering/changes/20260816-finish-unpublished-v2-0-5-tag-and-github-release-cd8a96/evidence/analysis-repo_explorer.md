# Analysis — repo_explorer

Change: `20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96`  
Route: `cd8a9662bc68` · write owner: `general_implementer` · intent: finish unpublished v2.0.5 tag + GitHub Release

Read-only. This agent has no shell, so there is no live `git status` / `git show` / `gh` CLI. Checks are the filesystem equivalents of `git rev-parse` / `git log --walk-reflogs` plus public GitHub REST (same data `gh` would return). No push, tag, merge, or release from this agent.

Repo: `https://github.com/Dimkox/adaptive-grok-build-pro.git`  
Only local branch: `main`. No `packed-refs`. No `MERGE_HEAD`. Only remote branch: `origin/main`.

---

## Commands / reads performed

```text
# local refs (git rev-parse equivalents)
read .git/HEAD                          → ref: refs/heads/main
read .git/refs/heads/main               → 7c0ae7573535ddd0cfe3800f81278991ced81584
read .git/refs/remotes/origin/main      → 7c0ae7573535ddd0cfe3800f81278991ced81584
read .git/ORIG_HEAD                     → 7c0ae7573535ddd0cfe3800f81278991ced81584
read .git/COMMIT_EDITMSG                → Release v2.0.5: hook shims, toolchain pins, track zip and checksum
read .git/refs/tags/v2.0.0 … v2.0.5
read .git/FETCH_HEAD                    → main @ 7c0ae75; remote tags v2.0.0–v2.0.4 only
read .git/logs/refs/heads/main
read .git/logs/refs/remotes/origin/main → last event: 33a02f1 → 7c0ae75  update by push
read .git/config                        → origin = https://github.com/Dimkox/adaptive-grok-build-pro.git
read .git/MERGE_HEAD                    → absent
read .git/packed-refs                   → absent
read VERSION, CHANGELOG.md, packages/README.md, packages/…v2.0.5.zip.sha256
list .git/refs/tags, .git/refs/heads, packages/, dist/,
     engineering/changes/…ad4090/evidence/

# GitHub REST (gh release / gh api / gh pr equivalents)
GET /repos/Dimkox/adaptive-grok-build-pro/commits/main
GET /repos/Dimkox/adaptive-grok-build-pro/commits/7c0ae7573535ddd0cfe3800f81278991ced81584
GET /repos/Dimkox/adaptive-grok-build-pro/branches
GET /repos/Dimkox/adaptive-grok-build-pro/tags?per_page=20
GET /repos/Dimkox/adaptive-grok-build-pro/git/matching-refs/tags
GET /repos/Dimkox/adaptive-grok-build-pro/git/ref/tags/v2.0.5          → 404
GET /repos/Dimkox/adaptive-grok-build-pro/git/tags/7f85f7be43fd8008…   → 404
GET /repos/Dimkox/adaptive-grok-build-pro/releases?per_page=10
GET /repos/Dimkox/adaptive-grok-build-pro/releases/latest
GET /repos/Dimkox/adaptive-grok-build-pro/releases/tags/v2.0.5         → 404
GET /repos/Dimkox/adaptive-grok-build-pro/pulls?state=all&per_page=20  → []
GET /repos/…/contents/packages?ref=7c0ae7573535ddd0cfe3800f81278991ced81584
GET /repos/…/contents/…ad4090/evidence?ref=7c0ae75
GET /repos/…/contents/…cd8a96?ref=main                                 → 404
GET raw main VERSION / CHANGELOG.md / README.md / packages/…v2.0.5.zip.sha256
```

Limitation: `.git/objects/7f/85f7be…` is zlib-compressed; this agent cannot peel `v2.0.5^{}` with `git rev-parse`. Peel is inferred below from ref shape + land-wave record. Do not treat that peel as a fresh `git cat-file -p` dump.

---

## 1. origin/main SHA and 2.0.5 product files on origin

| Ref | SHA / value | Source |
| --- | --- | --- |
| Local `HEAD` / `refs/heads/main` | `7c0ae7573535ddd0cfe3800f81278991ced81584` | `.git/refs/heads/main` |
| `refs/remotes/origin/main` | **same** `7c0ae75` | `.git/refs/remotes/origin/main` |
| `FETCH_HEAD` branch `main` | **same** `7c0ae75` | `.git/FETCH_HEAD:1` |
| GitHub `GET /commits/main` | **same** `7c0ae75` | public API |
| GitHub `GET /branches` | only `{name: main, commit: 7c0ae75, protected: false}` | public API |
| Commit message | `Release v2.0.5: hook shims, toolchain pins, track zip and checksum` | `COMMIT_EDITMSG` + GitHub commit |
| Author date | `2026-08-15T02:42:20Z` | GitHub commit |
| Parent | `33a02f1128ab0a865bfb1c853248f997dcf9e39b` (`Release v2.0.4: track zip and checksum`, tag `v2.0.4`) | reflog + GitHub parents |
| Origin reflog last event | `33a02f1` → `7c0ae75` **`update by push`** | `.git/logs/refs/remotes/origin/main` last line |

Local `main` is **not** ahead of origin. The 2.0.5 ship commit is already on `origin/main` and on GitHub `main`.

Stale warning: `ad4090/evidence/analysis-repo_explorer-merge.md` and `code-review-merge.md` still say origin is `33a02f1` and GitHub 422s `7c0ae75`. That was true during the failed-auth land wave. It is **false now**. Do not re-push `main`.

### Product files at `7c0ae75` on GitHub (also working tree)

| Path | On origin / GitHub `7c0ae75` | Local working tree |
| --- | --- | --- |
| `VERSION` | `2.0.5` | `2.0.5` |
| `README.md` H1 | `# Adaptive Grok Build Pro v2.0.5` | same |
| `CHANGELOG.md` | `## 2.0.5 — 2026-08-15` (lines 3–12) | same |
| `packages/README.md` last row | `adaptive-grok-build-pro-v2.0.5.zip` / `2.0.5` | same |
| `packages/adaptive-grok-build-pro-v2.0.5.zip` | present, size `436159` | present |
| `packages/adaptive-grok-build-pro-v2.0.5.zip.sha256` | `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd  adaptive-grok-build-pro-v2.0.5.zip` | same bytes |

---

## 2. Local tag target vs HEAD

| Place | Value |
| --- | --- |
| `.git/refs/tags/v2.0.5` | annotated tag object **`7f85f7be43fd8008f6af522a967ebc5268a481d1`** |
| `HEAD` / `ORIG_HEAD` | commit **`7c0ae7573535ddd0cfe3800f81278991ced81584`** |
| Tag object == commit SHA? | **No** (annotated, not lightweight) |
| Tag object == `33a02f1`? | **No** (not the v2.0.4 ship) |
| GitHub `GET /git/tags/7f85f7be…` | **404** — tag object never pushed |

Peel inference (not a live `git rev-parse 'v2.0.5^{}'`):

- Tag ref appeared after `HEAD` was already `7c0ae75` (`ad4090/evidence/code-review-merge.md:56-57`).
- Default `git tag -a v2.0.5` and the architect pin both target `7c0ae7573535ddd0cfe3800f81278991ced81584`.
- `v2.0.4` is untouched (`10c522f294bc5ffbdbef32d1487af59ff4e8453b`).

Treat local `v2.0.5` as already created on the publish commit. Last mile is **push the existing tag**, not retag.

---

## 3. Remote tags

`GET /git/matching-refs/tags` and `GET /tags` and `FETCH_HEAD` agree. Origin has **only**:

| Tag | Annotated object (local = remote) | Peeled commit (GitHub `/tags`) |
| --- | --- | --- |
| `v2.0.0` | `3cfb2b41c85f5f4f1afb0ed70a237df7572d3e6a` | `786e41a1…` |
| `v2.0.1` | `4aac2b3b58719afaefa204e351f63e3902700f54` | `79d1f104…` |
| `v2.0.2` | `5d732ed3c8a2193c564fe685193f7a7dcd52eda6` | `6be318f0…` |
| `v2.0.3` | `794718e1d784e0806392207c27ff18ef28a88b92` | `263b6eb0…` |
| `v2.0.4` | `10c522f294bc5ffbdbef32d1487af59ff4e8453b` | `33a02f11…` |
| **`v2.0.5`** | **local only** `7f85f7be…` | **absent** (`GET /git/ref/tags/v2.0.5` = 404) |

There is no `refs/remotes/origin/tags/` directory. `FETCH_HEAD` lists remote tags through `v2.0.4` only.

---

## 4. GitHub releases — `v2.0.5` does not exist

`GET /releases/latest` and first row of `GET /releases?per_page=10`:

| Field | Value |
| --- | --- |
| `tag_name` | **`v2.0.4`** |
| `name` | **`Adaptive Grok Build Pro v2.0.4`** |
| `id` | `370918434` |
| `html_url` | https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.4 |
| `target_commitish` | `main` |
| `published_at` | `2026-08-15T01:27:26Z` |
| assets | `adaptive-grok-build-pro-v2.0.4.zip` (`sha256:e76cd399…`), sibling `.sha256` |

Older releases on that list: `v2.0.3`, `v2.0.2`, `v2.0.1`, `v2.0.0`.  
`GET /releases/tags/v2.0.5` → **404**. Equivalent of `gh release list` / `gh release view v2.0.5`: Latest is 2.0.4; 2.0.5 was never created.

Scratch notes for the missing release already exist locally and must stay untracked: `dist/RELEASE-NOTES.md` is `CHANGELOG.md` §2.0.5 verbatim (lines 3–12). `dist/` is gitignored (`.gitignore:27`).

---

## 5. PRs — nothing to merge

`GET /pulls?state=all&per_page=20` → **`[]`**.

- No open PRs.
- No closed PRs.
- One branch (`main`) on both sides; local `main` **is** `origin/main` at `7c0ae75`.
- No `MERGE_HEAD`.

The user complaint «не смерджено» is a misread of the GitHub UI: Latest **Release** is still `v2.0.4`. The 2.0.5 **commit is already on `main`**. There is no PR to merge. Do not open one for last mile.

---

## 6. Zip + sha256 are tracked at HEAD

Confirmed three ways:

1. GitHub `GET /contents/packages?ref=7c0ae75` lists both `adaptive-grok-build-pro-v2.0.5.zip` (blob `4a475f84…`, size 436159) and `…v2.0.5.zip.sha256` (blob `161a7ed4…`, size 101).
2. GitHub commit `7c0ae75` message is the track-zip release; parent is the 2.0.4 track-zip commit.
3. Working sibling digest matches origin raw file: `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd`.

Do **not** rebuild with `package_stack.py`. A rebuild would change timestamps/manifest and break the already-tracked digest. Attach the **existing** `packages/` pair to `gh release create`.

---

## 7. Dirty files that must NOT be included in last-mile publish

Last mile is tag-push + `gh release create` only. **Do not make a second ship commit.** Do not `git add -A`.

### A. Leftover ad4090 evidence (on disk, **not** in `7c0ae75`)

Origin `GET /contents/…ad4090/evidence?ref=7c0ae75` has only 8 files:

`README.md`, `analysis-architect.md`, `analysis-docs_researcher.md`, `analysis-docs_researcher-continue.md`, `analysis-repo_explorer.md`, `analysis-repo_explorer-continue.md`, `analysis-task_analyst.md`, `human-approval.md`.

Local extras (9) — stay uncommitted:

| Path under `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/` |
| --- |
| `evidence/implementation.md` |
| `evidence/code-review.md` |
| `evidence/test-review.md` |
| `evidence/code-review-merge.md` |
| `evidence/test-review-merge.md` |
| `evidence/analysis-architect-merge.md` |
| `evidence/analysis-docs_researcher-merge.md` |
| `evidence/analysis-repo_explorer-merge.md` |
| `evidence/analysis-task_analyst-merge.md` |

### B. Dirty tracked file (content differs from origin)

| Path | Origin `7c0ae75` | Working tree |
| --- | --- | --- |
| `…ad4090/state.json` | `status: implementing`, `updated_at: 2026-08-15T02:40:00+00:00` | `status: ready`, `updated_at: 2026-08-15T02:51:12+00:00` |

`…ad4090/tasks.md` matches origin (last mile still unchecked). Leave `state.json` unstaged.

### C. This change package (created after HEAD; 404 on GitHub `main`)

Entire tree `engineering/changes/20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96/` including this report. Paperwork for *this* route. Not part of the 2.0.5 ship commit. Do not fold it into a retag or a new product commit.

### D. Gitignored (present; never add)

| Path | Why |
| --- | --- |
| `.grok-stack/runtime/*` except `.gitkeep` | `.gitignore:2-3` (active-route, receipts, approvals) |
| `.env` / `.env.*` | `.gitignore:6-8`. Do not read. |
| `err.log` | `.gitignore:14-15` |
| `dist/**` including `dist/adaptive-grok-build-pro-v2.0.5.zip*`, `dist/RELEASE-NOTES.md`, `dist/HANDOFF.md` | `.gitignore:27` |
| `tests/__pycache__/`, `scripts/__pycache__/` | `.gitignore:23` |
| `*.pem` `*.key` `*.p12` `*.pfx` | `.gitignore:9-12` |

Root `MANIFEST.sha256` is absent (deleted after the ship commit). Do not regenerate it.

---

## Gap matrix

| Artifact | Local | `origin/main` / GitHub `main` | GitHub tag | GitHub Release |
| --- | --- | --- | --- | --- |
| Commit `7c0ae75` | yes | **yes (already pushed)** | — | — |
| `VERSION` / CHANGELOG 2.0.5 / README v2.0.5 | yes | **yes** | — | — |
| `packages/…v2.0.5.zip` + `.sha256` | yes | **yes** | — | **no asset** |
| Annotated tag `v2.0.5` (`7f85f7be`) | **yes** | **no** | **404** | — |
| Release named Adaptive Grok Build Pro v2.0.5 | — | — | — | **missing; Latest = v2.0.4** |
| PR | none | none | — | — |

Remaining last mile (human-owned per `engineering/runbooks/publish-v2.0.5.md`; do not retag; do not rebuild; do not force-push; do not merge):

```bash
git rev-parse HEAD                 # expect 7c0ae7573535ddd0cfe3800f81278991ced81584
git rev-parse 'v2.0.5^{}'          # expect 7c0ae7573535ddd0cfe3800f81278991ced81584
git push origin v2.0.5
gh release create v2.0.5 \
  packages/adaptive-grok-build-pro-v2.0.5.zip \
  packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 \
  --notes-file dist/RELEASE-NOTES.md
```

`git push origin main` is a no-op if remotes are still at `7c0ae75`. Confirm with `git fetch` first; stop if `origin/main` moved.

---

## Conclusion

The 2.0.5 product is already published as git history: local `main`, `origin/main`, and GitHub `main` are the same commit `7c0ae7573535ddd0cfe3800f81278991ced81584` (`Release v2.0.5: hook shims, toolchain pins, track zip and checksum`), and that tree already carries `VERSION=2.0.5`, CHANGELOG §2.0.5, and the tracked zip + sha256 (`b80e6310…`). What GitHub still shows as “2.0.4 / not merged” is only the **Release** surface: remote tags stop at `v2.0.4`, Latest release is still **Adaptive Grok Build Pro v2.0.4** (id `370918434`), `v2.0.5` 404s as both a ref and a release, and there are no PRs to merge. The annotated tag `v2.0.5` (`7f85f7be`) exists locally on that commit and was never pushed. Last mile is push that existing tag and `gh release create` with the already-tracked `packages/` assets and gitignored `dist/RELEASE-NOTES.md`. Leave leftover ad4090 evidence, dirty `ad4090/state.json`, this `cd8a96` change package, runtime, `err.log`, and `dist/` out of git.
