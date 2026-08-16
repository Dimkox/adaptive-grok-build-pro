# Code review — finish unpublished v2.0.5 tag and GitHub Release

Change: `20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96`  
Route: `cd8a9662bc68` · reviewer: `code_reviewer` (read-only)  
Reviewed: 2026-08-16

**PASS.** I would not block. Public Latest is `v2.0.5` at `7c0ae75`. `v2.0.4` is intact. This wave did not rewrite `main` or edit product code.

I did not trust `evidence/implementation.md`. Local refs, working-tree product files, `grok_verify` dirty list, rollback text, and live GitHub HTML were checked independently. This reviewer session has no shell, so there is no live `git rev-parse` / `gh` / `sha256sum`. Equivalents are listed below.

---

## Verdict against the seven checks

| # | Check | Result |
| --- | --- | --- |
| 1 | HEAD / `origin/main` / peeled `v2.0.5` are `7c0ae7573535ddd0cfe3800f81278991ced81584` | **PASS** |
| 2 | GitHub Latest is `v2.0.5`; `v2.0.4` still exists | **PASS** |
| 3 | Assets are packages zip + sha256; zip digest `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` | **PASS** |
| 4 | Notes are CHANGELOG 2.0.5, not the 2.0.4 MIT wrapper | **PASS** |
| 5 | No force-push, no second ship commit, no product-code edits in this wave | **PASS** |
| 6 | Dirty tree is change-package evidence / gitignored scratch, not a publish defect | **PASS** |
| 7 | Rollback in the change package does not touch `v2.0.4` | **PASS** |

Would I block? **No.**

---

## Commands / reads performed

This agent cannot spawn a shell. Filesystem reads are the `git rev-parse` / reflog equivalents. Public GitHub was fetched as HTML / expanded-assets (unauthenticated REST returned 403 rate-limit).

```text
# local refs (git rev-parse / symbolic-ref equivalents)
read .git/HEAD                          → ref: refs/heads/main
read .git/refs/heads/main               → 7c0ae7573535ddd0cfe3800f81278991ced81584
read .git/refs/remotes/origin/main      → 7c0ae7573535ddd0cfe3800f81278991ced81584
read .git/ORIG_HEAD                     → 7c0ae7573535ddd0cfe3800f81278991ced81584
read .git/COMMIT_EDITMSG                → Release v2.0.5: hook shims, toolchain pins, track zip and checksum
read .git/refs/tags/v2.0.5              → 7f85f7be43fd8008f6af522a967ebc5268a481d1  (annotated tag object)
read .git/refs/tags/v2.0.4              → 10c522f294bc5ffbdbef32d1487af59ff4e8453b
read .git/FETCH_HEAD                    → main @ 7c0ae75; remote tags v2.0.0–v2.0.4 only (stale vs new v2.0.5)
read .git/logs/HEAD
read .git/logs/refs/heads/main          → last: 33a02f1 → 7c0ae75  commit: Release v2.0.5…
read .git/logs/refs/remotes/origin/main → last: 33a02f1 → 7c0ae75  update by push
read .git/config                        → origin = https://github.com/Dimkox/adaptive-grok-build-pro.git
read .git/packed-refs                   → absent
read .git/objects/7f/85f7be…            → zlib binary (cannot peel locally)

# product files vs ship commit
read VERSION                            → 2.0.5
read CHANGELOG.md (## 2.0.5 / ## 2.0.4)
read dist/RELEASE-NOTES.md
read packages/adaptive-grok-build-pro-v2.0.5.zip.sha256
read packages/adaptive-grok-build-pro-v2.0.4.zip.sha256
read packages/README.md
read README.md H1
read .gitignore                         → dist/, err.log, .grok-stack/runtime/* ignored

# change package
read brief.md, requirements.md, architecture.md, release.md, rollback.md, tasks.md, test-plan.md
read evidence/implementation.md (not used as authority)
read evidence/human-approval.md
read state.json, route.json
read .grok-stack/runtime/receipts/cd8a9662bc68/verification.json  (dirty file list)

# public GitHub (live, after the claimed last mile)
GET https://github.com/Dimkox/adaptive-grok-build-pro/releases/latest
    → 200, page title/body is Release v2.0.5 (redirect target)
GET https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.5
GET https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.4
GET https://github.com/Dimkox/adaptive-grok-build-pro/releases
GET https://github.com/Dimkox/adaptive-grok-build-pro/releases/expanded_assets/v2.0.5
GET https://github.com/Dimkox/adaptive-grok-build-pro/releases/expanded_assets/v2.0.4
GET https://github.com/Dimkox/adaptive-grok-build-pro/tags
GET https://github.com/Dimkox/adaptive-grok-build-pro/tree/v2.0.5
GET https://github.com/Dimkox/adaptive-grok-build-pro/commits/main
GET https://github.com/Dimkox/adaptive-grok-build-pro/commit/7c0ae7573535ddd0cfe3800f81278991ced81584
GET https://raw.githubusercontent.com/Dimkox/adaptive-grok-build-pro/7c0ae7573535ddd0cfe3800f81278991ced81584/VERSION
GET https://raw.githubusercontent.com/Dimkox/adaptive-grok-build-pro/7c0ae7573535ddd0cfe3800f81278991ced81584/packages/adaptive-grok-build-pro-v2.0.5.zip.sha256
GET https://api.github.com/repos/…/releases/latest  → 403 rate-limit (unused)
```

Not run (no shell): `git rev-parse`, `git ls-remote`, `git status`, `git push`, `git tag`, `gh release *`, `sha256sum` of zip bytes. No push, tag, or release from this agent.

---

## 1. HEAD / origin/main / peeled v2.0.5

| Ref | Value | Source |
| --- | --- | --- |
| Local `HEAD` / `refs/heads/main` | `7c0ae7573535ddd0cfe3800f81278991ced81584` | `.git/refs/heads/main` |
| `refs/remotes/origin/main` | same | `.git/refs/remotes/origin/main` |
| `ORIG_HEAD` / `FETCH_HEAD` main | same | `.git/ORIG_HEAD`, `.git/FETCH_HEAD` |
| GitHub `commits/main` tip | `7c0ae75` — *Release v2.0.5: hook shims, toolchain pins, track zip and checksum* | public commits page |
| GitHub commit page | full SHA `7c0ae7573535ddd0cfe3800f81278991ced81584` | `/commit/7c0ae75…` |
| Local tag `v2.0.5` | annotated object `7f85f7be43fd8008f6af522a967ebc5268a481d1` (not a lightweight tag at HEAD) | `.git/refs/tags/v2.0.5` |
| Public peel of `v2.0.5` | `7c0ae7573535ddd0cfe3800f81278991ced81584` | `/releases/tag/v2.0.5`, `/tree/v2.0.5`, `/tags` |

Limitation: `.git/objects/7f/85f7be…` is zlib; this session cannot dump `v2.0.5^{}`. Public GitHub resolves the tag to the same ship commit as local `HEAD` / `origin/main`. Tag date on `/tags` is **15 Aug 2026** (annotated-tag timestamp from the prior prepare wave). Release timestamp is **16 Aug 16:10**. That is the existing annotated tag, not a GitHub-minted lightweight tag from today's HEAD.

`FETCH_HEAD` still lists remote tags only through `v2.0.4`. That is a stale local fetch record, not a missing remote tag. `/tags` now lists `v2.0.5`.

---

## 2. Latest is v2.0.5; v2.0.4 still exists

`/releases/latest` serves the `v2.0.5` page and the page carries the **Latest** badge.

`/releases` order:

- `v2.0.5` — Latest — released 16 Aug 16:10 — commit `7c0ae75`
- `Adaptive Grok Build Pro v2.0.4` — 15 Aug 01:27 — commit `33a02f1`
- v2.0.3 … v2.0.0 still listed

`/releases/tag/v2.0.4` is live. `/tags` still lists `v2.0.4` → `33a02f1`.

---

## 3. Assets and zip digest

`/releases/expanded_assets/v2.0.5` (independent of implementation.md):

| Asset | GitHub digest | Size / time |
| --- | --- | --- |
| `adaptive-grok-build-pro-v2.0.5.zip` | `sha256:b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` | 426 KB, 2026-08-16T16:10:09Z |
| `adaptive-grok-build-pro-v2.0.5.zip.sha256` | sidecar of the zip (101 Bytes) | 2026-08-16T16:10:09Z |
| Source zip / tar.gz | GitHub auto-archive of the tag | 2026-08-15T03:13:17Z (tag object date) |

Same digest in three independent text sources:

- local `packages/adaptive-grok-build-pro-v2.0.5.zip.sha256`
- raw file at commit `7c0ae75`
- GitHub expanded-assets `sha256:` on the zip

This session did not re-hash zip bytes. The three text sources agree, and the asset set is the tracked packages pair plus GitHub's automatic source archives (not a second packager run).

---

## 4. Notes are CHANGELOG 2.0.5

Public body of `v2.0.5` starts with:

```text
## 2.0.5 — 2026-08-15

After `git pull` on a consumer project, missing or cwd-relative hook scripts no longer lock Grok.
```

That matches `CHANGELOG.md` lines 3–12 and `dist/RELEASE-NOTES.md` verbatim (hook shims, toolchain pins, `install_into.py` deps, live `routing.json`).

It is **not** the v2.0.4 MIT wrapper. Live `v2.0.4` notes still begin:

```text
# Adaptive Grok Build Pro v2.0.4
Commercial-grade public product, free of charge, MIT-licensed.
```

---

## 5. No force-push, no second ship, no product-code edits

- Local `main` reflog last event is `33a02f1 → 7c0ae75` **`commit`**. No later commit. No `reset` / `rebase` / `forced-update` in this wave. The only `reset` in `HEAD` is the older 2.0.3-era move to `origin/main`.
- `origin/main` reflog last event is `33a02f1 → 7c0ae75` **`update by push`** (forward). Not a force.
- GitHub `/commits/main` tip is still `7c0ae75` (15 Aug). History under it is the same linear chain (`33a02f1`, `097f5c9`, …). No extra ship commit after the last-mile tag/release.
- `VERSION` local and at `7c0ae75` on origin are `2.0.5`. README H1 is `# Adaptive Grok Build Pro v2.0.5`.
- `grok_verify.py --mode pr` dirty list (`verification.json` `changed_files`) contains **only** leftover `ad4090` paperwork and this `cd8a96` change package. No `scripts/`, hooks, tests, `VERSION`, `CHANGELOG.md`, or `packages/` entries.

This wave matches the change package: push existing tag + `gh release create`. No `package_stack.py`, no retag, no `git push origin main`, no second product commit.

---

## 6. Dirty working tree is not a publish defect

`verification.json` dirty paths (quoted UTF-8 leftovers + this package):

- `engineering/changes/20260815-user-query-…-ad4090/evidence/*` merge/review leftovers, `implementation.md`, `requirements.md`, `state.json`
- `engineering/changes/20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96/**` (this package; not in `7c0ae75`)

`.gitignore` covers `dist/`, `err.log`, `.grok-stack/runtime/*`, `__pycache__/`. Those are scratch / receipts, not published artifacts.

Do not `git add -A` and commit this dirt onto `main`. That would move HEAD off the tagged ship SHA. Residual only; not a reason to retag or fail this review.

---

## 7. Rollback does not touch v2.0.4

`rollback.md` is delete-only-`v2.0.5`:

```bash
gh release delete v2.0.5 --yes
git push origin :refs/tags/v2.0.5
git tag -d v2.0.5
```

It states it does not touch `v2.0.4` or rewrite `main`. Independent check of live `v2.0.4`:

- Release still present; commit still `33a02f1`
- Assets still `adaptive-grok-build-pro-v2.0.4.zip` + `.sha256`
- Zip digest still `e76cd399c81c2f56aa7f12d70789658159d55a88079b7644f84807f3aab3304a` (matches local sidecar)
- Asset timestamps still `2026-08-15T01:27:25Z` (not rewritten on 16 Aug)

---

## Contract / change-package fit

In scope (tag push + GitHub Release + confirm Latest) landed. Out of scope (rebuild, retag, PR, `git push origin main`, second ship commit, force-push, touching `v2.0.4`) did not happen.

Acceptance criteria in `requirements.md` are met on the public repo.

`python3 scripts/grok_verify.py --mode pr` already recorded `status=pass` (156 tests, secret-scan/sql/diff-check clean). That receipt is fingerprint-stale after later evidence writes; expected for a last-mile-only change. No product test gap for this wave.

---

## Residual (non-blocking)

- Release **name** is empty (UI shows the tag `v2.0.5`). Prior releases used `Adaptive Grok Build Pro v2.0.x`. Cosmetic. Fix with `gh release edit`, not a retag.
- Local `FETCH_HEAD` does not yet list remote `v2.0.5`. Harmless; `/tags` has it.
- Machine approvals cited in implementation.md expire ~16:24Z the same day. Irrelevant after the two commands already ran.
- `engineering/runbooks/publish-v2.0.5.md` still says humans own `git push` / `gh release`. This change recorded an authorized exception. Do not treat the runbook as a reason to republish.

---

## Block?

**No.** Last mile did what the change package authorized and nothing else. Latest is `v2.0.5` at `7c0ae75` with the expected zip digest and CHANGELOG 2.0.5 notes. `v2.0.4` remains a previous release.
