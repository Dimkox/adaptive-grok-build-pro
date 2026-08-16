# Analysis — task_analyst

Change: `20260816-user-query-пиздец-ты-конченый-применяй-все-измен-ff295d`  
Route: `ff295dada3ef` · write=`general_implementer` · reviews=`code_reviewer` + `test_reviewer`  
Skills: `/adaptive-delivery`, `feature-workflow`. Allowed agents only. Read-only.

User: «применяй все изменения, старые и неактуальные удаляй, новые пуш в репо».

Parent mapping (this wave’s question, source of truth over the stub templates):

| Phrase | Means |
| --- | --- |
| применяй все изменения | Commit leftover **evidence of real work** already on disk |
| старые / неактуальные удаляй | Remove **superseded draft** change packages |
| новые пуш | `git push origin main` of that cleanup commit |

Product is already on `origin/main` at route `base_commit` `7152b75`. `VERSION` / `__version__` are `2.0.8`. This is not a release.

No `.env`. This agent does not commit, delete, push, tag, or mint approvals.

---

## Ruling

**Paperwork-only cleanup, then one fast-forward to `origin/main`.**

- **Apply** = path-limited `git add` + commit of leftover keeper evidence (shipped-work records that are still dirty/untracked).
- **Delete** = `rm` of superseded **untracked** draft packages (or untracked extras inside a tracked package). Never `git rm` a historical HEAD copy.
- **Push** = `git push origin main` after verify + independent reviews + a **fresh** `grok_approve.py production`. No force-push.

Not a 2.0.9 bump. Not a tag. Not a GitHub Release. Not GHA. Not `git add -A`. Not `grok_deploy.py` pack/tag/`gh release create`.

User-approved scope wins over adaptive-delivery §7 “humans own printed commands”: the user named push, and `human_gates` is empty. PreToolUse still requires a live production token. Tokens already on disk are the wrong action and must not be reused.

---

## Outcome

After close, a user listing `origin/main` sees the keeper change-package evidence that today exists only as dirt, and does **not** see the superseded draft directories. Working tree has no leftover `??` change packages. Product identity stays `2.0.8` at `7152b75` plus the cleanup commit(s).

---

## Scope

### In scope

- Classify each candidate with `git status --short` and `git ls-files` (this agent has no shell; implementer must snapshot).
- `rm -rf` fully untracked DELETE dirs.
- Delete untracked extras inside mixed packages; leave tracked HEAD files.
- Path-limited `git add` of KEEP leftovers + this package (`ff295d`).
- One or two path-limited commits on `main` (keepers+this package; optional second commit of this package’s review reports + `state=ready`).
- `python3 scripts/grok_verify.py --mode pr`.
- Independent `code_review` + `test_review` on the final fingerprint.
- Fresh `python3 scripts/grok_approve.py production --reason "push keeper change-package evidence; delete superseded drafts"`.
- `git push origin main` (controller, after the above).

### Out of scope

- Any product file that is already on `7152b75` (`VERSION`, `__init__.__version__`, `CHANGELOG.md`, `README.md`, `AGENTS.md`, root `decisions.md` / `mistakes.md`, tests, installer, packager, zips).
- `git add -A`, `git add .`, `git add -u` of the whole tree.
- VERSION bump, tag `v2.0.8` / `v2.0.9`, `gh release create` / `gh release edit`.
- `package_stack.py`, zip rebuild, `MANIFEST.sha256` at root.
- GitHub Actions, Dependabot, `pyproject.toml` / `requirements.txt` / `setup.py`.
- Staging gitignored runtime: `.grok-stack/runtime/**`, `dist/`, `err.log`, `__pycache__/`, `.env`.
- Force-push, other branches, merge, deploy, Bitrix, installer seed.
- Reusing production tokens `4dfff07da9e0` (expired; 2.0.8 identity push) or `7c5d3e65d4f1` (push of `7152b75`; wrong action).

---

## KEEP vs DELETE

Classification is **path + git index**, not `state.json` alone. A `ready` package can still have untracked extras (KEEP those). A `draft` package that is already tracked stays on HEAD (do not delete the tracked copy).

### KEEP — commit leftover evidence of real work

Shipped-work records. Add only dirty/untracked files under these dirs (plus this package):

| Short | Package | Why keep |
| --- | --- | --- |
| `5be23b` | finish 2.0.6 commit/ban/verify/release | Completed ship record; extras on HEAD |
| `2929c0` | publish v2.0.7 GitHub release | Completed last-mile record |
| `3c1039` | self-scan leftover 2.0.6 product bugs | Completed product-fix record |
| `ec0388` | ship working v2.0.6 quality contour | Completed contour record |
| `37141f` | 2.0.8 identity rebuild | Ready ship record; leftover analysis/review files |
| `a13da8` | README K10 + unfinished push | Product (K10) already on `7152b75`; commit leftover package extras only |
| `ad4090` | git/push/package/release | Released; commit **extra** evidence only |
| `d55ce4` | restore AGENTS.md self-learning | Ready; commit if still dirty |
| `ba1615` | root `decisions.md` / `mistakes.md` | Ready; product already on origin; commit if still dirty |
| `2f9f5d` | last-mile push of `7152b75` | Ready last-mile record of the product already on origin |
| `ff295d` | **this** cleanup | The vehicle; must land on origin |

If a KEEP path is already identical to HEAD, do not touch it.

### DELETE — superseded drafts (untracked dir or untracked extras only)

| Short | Status | Why delete |
| --- | --- | --- |
| `39b13f` | draft | Abandoned 2.0.6 “ban GHA / publish” wave |
| `864726` | draft | Abandoned 2.0.6 GitHub-release wave (superseded by later 2.0.6/2.0.7/2.0.8) |
| `0f3d94` | draft | Interrupt draft; superseded by `2f9f5d` |
| `2a31f5` | approved, never implemented | Interrupt draft; superseded by `2f9f5d` |
| `04ae05` | approved, never implemented | Push-only draft for ba1615; superseded by `2f9f5d` (`7152b75` already on origin) |

### Brief correction — do **not** whole-dir delete

| Short | Brief said | Ruling |
| --- | --- | --- |
| `b625b4` | DELETE | **Ready** last-mile for `gh release edit` of v2.0.6. Not a draft. Leave tracked HEAD. Drop untracked extras only. |

### Brief omissions — implementer classifies

| Short | Status | Ruling |
| --- | --- | --- |
| `9fd274` | implementing (abandoned 2.0.6 rebuild) | Superseded by `5be23b` + later 2.0.7/2.0.8. **DELETE if fully untracked.** Leave tracked HEAD. |
| `6d15cb` | draft (v2.0.3 publish) | Same rule. Historical; likely tracked — then leave HEAD. |
| `aea9d4` | reviewing | Historical contour work. Leave unless fully untracked and unused. |
| Older `approved` never-`ready` (`e86e93`, `b082cf`, `58e51e`, `b8b188`) | historical | Leave tracked copies. Not “new drafts”. |

### Hard rule for every DELETE path

1. `git ls-files -- <dir>` empty **and** `git status` shows `??` → `rm -rf <dir>`.
2. Some files tracked → delete only untracked extras; **do not** `git rm` the package.
3. Fully tracked, no extras → leave it. Status `draft` is not a license to erase history.

---

## Acceptance

### Authorized (pass only if all true)

- [ ] **Given** leftover keeper evidence on disk, **when** the write owner commits, **then** every dirty/untracked file under the KEEP dirs and `…-ff295d/` is in the commit, and no DELETE untracked draft dir remains in `git status --short`.
- [ ] **Given** that commit, **when** `git show --stat --name-only` is read, **then** every path is under `engineering/changes/` (keepers + this package). No `VERSION`, no `CHANGELOG.md`, no `packages/`, no `.github/`, no `pyproject.toml`, no `.grok-stack/runtime/`.
- [ ] **Given** the same commit, **when** the index is built, **then** the write owner used explicit paths only. No `git add -A` / `git add .` / repo-wide `git add -u`.
- [ ] **Given** a DELETE candidate that has tracked files, **when** cleanup runs, **then** the HEAD copy is still in the tree; only untracked extras (or a fully untracked dir) were removed.
- [ ] **Given** verify + passing `code_review` + `test_review` receipts on the final fingerprint, **when** last mile runs, **then** `origin/main` fast-forwards to that commit. No force-push. No other branch.
- [ ] **Given** PreToolUse, **when** `git push origin main` is invoked, **then** a **fresh** `has_valid_approval(..., 'production')` minted for **this** cleanup push is unexpired. Tokens `4dfff07da9e0` and `7c5d3e65d4f1` are not used.

### Forbidden (fail this change)

- [ ] **Given** «применяй все», **when** the write owner acts, **then** `VERSION` and `__version__` stay `2.0.8`. No `2.0.9`.
- [ ] **Given** the same go, **when** the session ends, **then** there is no new tag, no `gh release create` / `gh release edit`, no `package_stack.py`, no zip rewrite.
- [ ] **Given** «старые удаляй», **when** cleanup runs, **then** no tracked historical package is `git rm`’d (including `b625b4` and older approved/ready packages).
- [ ] **Given** `grok_deploy.py` printed commands, **when** last mile runs, **then** only `git push origin main` may run. Pack / tag / push-tag / GitHub Release stay unrun.
- [ ] **Given** the dirty tree, **when** staging happens, **then** runtime, secrets, `dist/`, `err.log`, and `__pycache__` are not added.

### Preconditions (not yet done)

- [ ] Implementer snapshot: `git status --short` and per-dir `git ls-files` for every KEEP/DELETE short id. This analysis does not invent that list.
- [ ] Path-limited commit exists on local `main` and is not yet on `origin/main`.
- [ ] Fresh `python3 scripts/grok_verify.py --mode pr` **pass** on route `ff295dada3ef` after the last file that will remain in that tree (`state.json` → `ready` first).
- [ ] Independent `code_review` + `test_review` **pass** receipts bound to that fingerprint.
- [ ] Fresh `python3 scripts/grok_approve.py production` unexpired at push time.

---

## Sequence (who does what)

`write_agent` = `general_implementer` owns deletes + path-limited add + commit. Do not spawn a second writer.

1. Snapshot status / `ls-files`.
2. Delete superseded untracked drafts (and extras).
3. Stage keepers + this package by explicit path.
4. Commit. Message: cleanup of keeper evidence + removal of superseded drafts. Not a release.
5. Controller: `grok_change.py transition … ready`, then `grok_verify.py --mode pr`.
6. Controller: dispatch `code_reviewer` + `test_reviewer`; `grok_review.py` both kinds.
7. If reviews write files after the first commit: second path-limited commit of `…-ff295d/` only, then re-verify. Do not amend a commit that already left this machine if origin might have it; origin does not have it yet, so amend of the **unpushed** local commit is allowed only if nothing else moved `HEAD`.
8. Controller: fresh production approval, then `git push origin main`.

Reviews must not be recorded against a tree that will still change. Last file write → verify → receipts.

---

## Failure and edge cases

- **Mixed package.** Tracked `architecture.md` + untracked `evidence/foo.md` on a DELETE id: delete `foo.md` only.
- **KEEP file already on HEAD.** Skip; do not empty-commit it.
- **`b625b4` whole-dir `rm -rf`.** Fail. Ready last-mile, not a draft.
- **`04ae05` kept and pushed as if it were the last mile.** Fail. Product push already happened via `2f9f5d` / `7152b75`.
- **Receipts before `state.json` → ready.** Fail. Fingerprint includes change-package writes (`mistakes.md` 2026-08-14; `decisions.md` bind-after-last-write).
- **Expired or wrong-reason production token.** PreToolUse denies or the push is the wrong action. Mint new.
- **`git add -A` stages `??` drafts just deleted from the mental list but still on disk, or runtime files.** Fail. Explicit paths only.
- **Push without verify/reviews.** Fail. Route `required_evidence` is `verification`, `code_review`, `test_review`.
- **Untracked DELETE dir still listed in `git status` after commit.** Fail.

---

## Non-functional

- **Security:** Do not read `.env` or credentials. Do not stage secrets. Push only `origin/main` over existing remotes; no new remotes.
- **Reliability:** Fast-forward only. Rollback = new revert commit for keepers; deleted untracked drafts exist only on this disk until wiped.
- **Performance:** Irrelevant. No pack, no test-suite expansion required.
- **Observability:** `grok_verify --mode pr` is the only gate. No GHA.

No new product tests. Characterization of this change is the post-commit `git status` (DELETE dirs gone; no stray `??` packages) plus verify.

---

## Conflicts recorded

| Source | Says | Ruling |
| --- | --- | --- |
| `release.md` “VERSION 2.0.8” | Could be read as a bump | **Stay** at current `2.0.8`. No bump. |
| `brief.md` DELETE includes `b625b4` | Whole-dir delete | **Override:** extras-only; package is ready last-mile. |
| `brief.md` omits `9fd274` | Unclassified | DELETE if fully untracked; else leave HEAD. |
| adaptive-delivery §7 | Humans own last-mile commands | User named push; empty `human_gates`. Controller may run `git push origin main` after evidence + fresh approval. Pack/tag/release still forbidden. |
| `04ae05` analysis | Push ba1615 tree; do not add leftover packages | That go is **spent**. `7152b75` is already the product-on-origin. This route commits the leftovers `04ae05` refused. |
| `handoff.json` | Still points at `3ac76c` | Stale. Ignore. Active change is `ff295d`. |

---

## Unverified (blocked without a shell)

- Exact dirty vs tracked split for each KEEP/DELETE path. Implementer must print `git status --short` before the first `rm` or `git add`.
- Whether `origin/main` is still exactly `7152b75` (route base). If origin moved, rebase/ff only; do not force.
- Whether token `7c5d3e65d4f1` is still unexpired. Even if live, **do not reuse** (wrong reason: push `7152b75`).

---

## Done when

`origin/main` has the cleanup commit. KEEP leftover evidence is in that commit. DELETE untracked drafts are gone from the working tree and were never `git add -A`’d. `VERSION` is `2.0.8`. No tag, no GHA, no zip. Verify + both reviews pass on the final fingerprint.
