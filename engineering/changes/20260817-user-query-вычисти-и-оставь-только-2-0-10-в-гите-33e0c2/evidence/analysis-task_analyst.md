# Analysis — task_analyst

Change: `20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2`  
Route: `33e0c2404a15` · intent=`feature` · risk=`low` · complexity=`standard`  
Write owner: `general_implementer` (exactly one)  
Analysis wave: `repo_explorer`, `task_analyst`, `architect`, `docs_researcher`  
Reviews after implementation: `code_reviewer` + `test_reviewer`  
Evidence kinds: `verification`, `code_review`, `test_review`  
Human gates: none  
Quality profiles: `base`  
Workflow skills: `/adaptive-delivery`, `feature-workflow`  
Narrow question: **write Given/When/Then acceptance. Confirm that “only 2.0.10 in git” after a dirty-status report means `git status` clean at v2.0.10, NOT delete v2.0.8/v2.0.9 tags or historical `packages/*.zip`.**

Read-only. No application-code edits. No `.env`. This report does not restore, delete, commit, tag, push, merge, or deploy.

Loaded `/adaptive-delivery` from `.grok/skills/adaptive-delivery/SKILL.md` and `feature-workflow`. This agent is in `allowed_agents`. Package status when read: `approved`. Sibling: `evidence/analysis-docs_researcher.md` (docs touch list empty; product identity already 2.0.10).

---

## Phrase map (source of truth)

| User / status phrase | Means in this route |
| --- | --- |
| вычисти | Discard **uncommitted session dirt**. Restore dirty tracked files to `HEAD`. `rm` untracked leftover sibling change-package files. |
| оставь только 2.0.10 в гите | After a **dirty-status** report that already showed `v2.0.10` @ `975ccb2`, make `git status` clean **on that commit**. The visible git tree is published 2.0.10, not leftover paperwork. |
| only 2.0.10 in git | **Weak reading (this route):** porcelain has no sibling dirt; `HEAD` still peels as `v2.0.10`. |
| only 2.0.10 in git | **Strong reading (rejected):** delete older tags, GitHub Releases, or `packages/…v2.0.0`–`v2.0.9.zip*`. Not accepted. See §6. |

The dirty-status context is decisive. The user was not asking to rewrite published history. They were looking at a tree that was already 2.0.10 plus leftover session files.

---

## Ruling (one screen)

**Cleanup of uncommitted dirt on published `v2.0.10`. No new commit. No history delete.**

- **In:** path-limited `git restore` of the three named dirty `state.json` files; `rm` of untracked leftover files under sibling `engineering/changes/*`; leave this `33e0c2` package uncommitted.
- **Out:** new commit, `VERSION` bump, tag create/delete, zip delete, `git push --force`, `git tag -d`, `git push origin :refs/tags/…`, `gh release delete`, `git clean -fd` at repo root, product-doc edits, GHA, `pyproject.toml`.

`human_gates` is empty. Adaptive-delivery §3: proceed after this bounded ruling. Adaptive-delivery §7 still applies: this route does **not** push, publish, or deploy.

I do **not** argue the stronger reading. If a later human explicitly names tag/zip deletion, that is a new high-risk route with production gates — not this feature.

---

## Current facts (do not treat cleanup as done)

| Item | This tree |
| --- | --- |
| `VERSION` / README H1 | `2.0.10` / `# Adaptive Grok Build Pro v2.0.10` |
| `refs/heads/main` | `975ccb20dfc5fb9e925602d177069abe7e5ccfbc` |
| `refs/remotes/origin/main` | same SHA |
| Route `base_commit` | `975ccb2…` |
| Local tags present | `v2.0.0` … `v2.0.10` (annotated; tag objects, not peeled here) |
| Required peels (package + `decisions.md`) | `v2.0.8` → `0284241`; `v2.0.9` → `f72c0fc`; `v2.0.10` → `975ccb2` |
| Tracked zips | `packages/adaptive-grok-build-pro-v2.0.0.zip` … `v2.0.10.zip` + `.sha256` |
| `packages/README.md` | table rows 2.0.0–2.0.10 |
| CHANGELOG | `## 2.0.10` then historical `## 2.0.9` … `## 2.0.0` |
| Tests locking identity | `test_version_is_2_0_10_and_github_actions_are_absent`; README contains `2.0.10`; in-zip `VERSION` is `2.0.10` |
| Named dirty tracked files (package allow-list) | `…-70b284/state.json` (working copy `released`); `…-e61f9d/state.json` (`ready`); `…-8fe260/state.json` (`verifying`) |
| This package | `approved`; untracked by design |
| Sibling docs report | product docs **FROZEN** |
| Live `git status` | **not run by this agent** (no shell). Implementer must snapshot before first `restore`/`rm`. |
| `human_gates` | `[]` |
| GHA / `pyproject.toml` | absent; must stay absent |

`70b284` implementation already recorded that 2.0.10 froze `v2.0.9` / `f72c0fc` and `packages/…v2.0.9.zip*`, and left other `engineering/changes/*` uncommitted. That leftover paperwork is the dirt this route removes. It is not a license to delete the frozen history.

---

## 1. Outcome

After this change, a human who inspects the clone sees:

1. `HEAD` is still `975ccb20dfc5fb9e925602d177069abe7e5ccfbc`.
2. `git describe --tags --exact-match` (or equivalent peel) still reports `v2.0.10`.
3. `VERSION` is still `2.0.10`. README H1 / Current state / CHANGELOG `## 2.0.10` are untouched.
4. `git status --porcelain` has **no** modified tracked files and **no** untracked sibling change-package leftovers. This `33e0c2` directory may remain as the only untracked path (gitignored runtime/`dist/`/`err.log` do not count).
5. Tags `v2.0.8`, `v2.0.9`, `v2.0.10` still exist and still peel to `0284241` / `f72c0fc` / `975ccb2`.
6. `packages/adaptive-grok-build-pro-v2.0.0.zip` through `v2.0.10.zip` (and `.sha256`) still exist and stay tracked.
7. No new commit, no force-push, no GitHub Release mutation.

That **is** “only 2.0.10 in git” after a dirty-status report.

---

## 2. Acceptance criteria (Given / When / Then)

Use these as the package `requirements.md`. All are in scope for `general_implementer` unless marked out.

### 2.1 Identity stays published 2.0.10

- [ ] **Given** `refs/heads/main` is `975ccb2…` and `VERSION` is `2.0.10`, **when** cleanup finishes, **then** `git rev-parse HEAD` is still `975ccb20dfc5fb9e925602d177069abe7e5ccfbc` and `VERSION` is still `2.0.10`.
- [ ] **Given** `origin/main` already equals that SHA, **when** cleanup finishes, **then** local `main` has not moved and no new commit exists (`git log -1 --oneline` still starts with `975ccb2`).
- [ ] **Given** annotated tag `v2.0.10`, **when** cleanup finishes, **then** `git rev-parse v2.0.10^{}` is still `975ccb2…`.

### 2.2 Working tree is clean of sibling dirt

- [ ] **Given** the pre-cleanup dirty-status (v2.0.10 plus session paperwork), **when** the write owner finishes, **then** `git status --porcelain` shows no ` M` / `M ` / `??` paths under sibling `engineering/changes/*` (any change-id other than `20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2`).
- [ ] **Given** the three named dirty tracked files, **when** cleanup runs, **then** each is restored with path-limited `git restore --` (not `git checkout .`, not `git restore .`):
  - `engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/state.json`
  - `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/state.json`
  - `engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/state.json`
- [ ] **Given** untracked leftover files under sibling `engineering/changes/*`, **when** cleanup runs, **then** only those untracked paths are `rm`’d. Tracked historical files in those packages stay at `HEAD`.
- [ ] **Given** this `33e0c2` package, **when** cleanup finishes, **then** it is **not** `git add`ed and **not** committed. It may remain untracked so analysis/review evidence can exist. Deleting it is not required and would drop evidence.

### 2.3 “Only 2.0.10” does **not** mean delete history

- [ ] **Given** local tags `v2.0.8` / `v2.0.9` / `v2.0.10`, **when** cleanup finishes, **then** all three still exist and still peel to `0284241` / `f72c0fc` / `975ccb2`.
- [ ] **Given** older tags `v2.0.0`–`v2.0.7`, **when** cleanup finishes, **then** they are still present. This route does not inventory-delete any `v2.0.*` tag.
- [ ] **Given** tracked `packages/adaptive-grok-build-pro-v2.0.{0..9}.zip` and `.sha256`, **when** cleanup finishes, **then** every pair still exists on disk and is still tracked (`git ls-files` still lists them).
- [ ] **Given** `packages/README.md` rows 2.0.0–2.0.10 and CHANGELOG sections `## 2.0.0`–`## 2.0.10`, **when** cleanup finishes, **then** those files are byte-identical to `HEAD` (docs_researcher: FROZEN).
- [ ] **Given** tracked historical change packages under `engineering/changes/`, **when** cleanup finishes, **then** no `git rm` of a path that exists in `975ccb2` has occurred.

### 2.4 Forbidden actions stay unused

- [ ] **Given** this feature route, **when** the write owner works, **then** none of these run: `git commit`, `git tag`, `git tag -d`, `git push`, `git push --force`, `git push origin :refs/tags/*`, `gh release delete`, `gh release create`, `python3 scripts/grok_deploy.py`, `python3 scripts/package_stack.py` as a ship step, `VERSION` edit.
- [ ] **Given** a dirty tree, **when** deleting leftovers, **then** the owner does **not** run `git clean -fd` at repo root (would sweep this package, unexpected `??`, and anything not in the allow-list).
- [ ] **Given** unexpected porcelain (a dirty path **not** in §2.2 / not this change-id), **when** the owner sees it, **then** they stop and record it. They do not guess.

### 2.5 Product behavior unchanged

- [ ] **Given** no product-file edit, **when** `python3 scripts/grok_verify.py --mode pr` runs on the cleaned tree, **then** it PASSes with identity still 2.0.10 and no GHA / no `pyproject.toml`.
- [ ] **Given** `tests/test_structure.py` / `tests/test_manifest_package.py`, **when** verification runs, **then** they still assert `VERSION == 2.0.10` and the 2.0.10 zip still contains `2.0.10`.
- [ ] **Given** adaptive-delivery §4 “failing test first”, **when** this is paperwork-only restore/`rm`, **then** no new characterization test is added (a new test would be a product-tree edit and would require a commit or leave new dirt). Existing suite is the characterization.

---

## 3. In scope

- Print `git status --porcelain` and `git ls-files` for each candidate **before** the first `git restore` or `rm`.
- Path-limited `git restore --` of the three `state.json` files in §2.2 if they differ from `HEAD`.
- `rm` of **untracked** leftover files (and fully untracked leftover sibling dirs) under `engineering/changes/*` except this `33e0c2` package.
- Leave this change package uncommitted (analysis + later review reports).
- Re-check porcelain: only this change-id (plus gitignored runtime/`dist/`) may remain.
- Confirm peels and zip inventory after the restore/`rm`.
- Run `python3 scripts/grok_verify.py --mode pr` on the resulting tree.
- Independent `code_reviewer` + `test_reviewer` after verification.

## 4. Out of scope

- Any new commit (including a “cleanup commit”).
- `VERSION` bump / retag / rebuild zip / `packages/` copy.
- Deleting or rewriting tags `v2.0.8`, `v2.0.9`, or any other `v2.0.*`.
- `git push --force` or any history rewrite (`reset --hard` of published commits, rebase of `main`, filter-repo).
- `gh release delete` / editing the published GitHub Release `v2.0.10` or older Releases.
- Deleting `packages/…v2.0.0`–`v2.0.9.zip*`.
- Deleting CHANGELOG sections or `packages/README.md` rows.
- `git rm` of tracked historical change packages that already live on `975ccb2`.
- Editing `README.md`, `CHANGELOG.md`, `AGENTS.md`, `VERSION`, `QUICKSTART.md`, runbooks (docs_researcher: empty touch list).
- Adding `.github/workflows/`, Dependabot, `pyproject.toml`, `requirements.txt`, `setup.py`.
- `git clean -fd` at repo root.
- `git add -A`.
- Push, merge, deploy, production mutation.
- Reading `.env` or credentials.

---

## 5. Why the weak reading is the acceptance

1. The user asked after a status that already showed **`v2.0.10` @ `975ccb2` plus dirty session paperwork**. “Вычисти” targets that dirt.
2. `975ccb2` **already contains** historical `packages/v2.0.0`–`v2.0.9` zips, CHANGELOG history, and older tags as published objects. Removing them cannot leave “only 2.0.10” — it creates a **new tree that is not `975ccb2`**.
3. Controller + package brief already froze: no new commit, no tag delete, no zip delete, no VERSION bump, no force-push.
4. `AGENTS.md` prohibits force-push and unapproved production mutation. Deleting remote tags is a production mutation.
5. docs_researcher: product docs already describe published 2.0.10; historical zip rows and CHANGELOG sections must stay if zips stay; zips must stay.

---

## 6. Strong reading — rejected (irreversible risks)

I do **not** accept “leave only 2.0.10” as delete older tags or historical packages.

If someone later forces that reading, these are the irreversible / high-cost risks — **not authorized here**:

| Action | Risk |
| --- | --- |
| `git tag -d v2.0.8` / `v2.0.9` (and older) | Local consumers and scripts that pin those tags lose the peel. Recoverable locally only if the tag object is still in reflog/remote. |
| `git push origin :refs/tags/v2.0.8` (etc.) | **Irreversible for anyone who already fetched.** Re-pushing a tag with the same name later is a retag; clients that already have the old tag keep the old object until a force fetch. |
| `gh release delete v2.0.8` / `v2.0.9` | Drops GitHub Release notes and attached assets. Recreate is a new release object, not the original. |
| Delete `packages/…v2.0.0`–`v2.0.9.zip*` | Requires a **new commit**. That commit is not `v2.0.10` / `975ccb2`. Breaks `packages/README.md` 1:1 table, install/repro of older zips, and the 2.0.10 “history of this product” contract. |
| `git push --force` of a rewritten `main` | Rewrites public `origin/main` (currently `975ccb2`). Breaks anyone who cloned/tagged that SHA. Violates `AGENTS.md` prohibited actions. |
| `git clean -fd` at root | Deletes this package and any unclassified untracked work with no undo. |

Those actions need an explicit human production gate and a different route (`intent=release` / high-risk). This route’s `human_gates` is empty **because** it is restore/`rm` only.

---

## 7. Implementer procedure (smallest vertical)

1. Snapshot: `git status --porcelain`, `git rev-parse HEAD`, `git rev-parse v2.0.8^{} v2.0.9^{} v2.0.10^{}`.
2. Classify every porcelain path:
   - dirty tracked + in §2.2 allow-list → `git restore -- <path>`
   - untracked under sibling `engineering/changes/*` → `rm` that path/dir
   - untracked under this `33e0c2` → keep
   - anything else → **stop**
3. Do not touch `packages/`, tags, `VERSION`, README, CHANGELOG, AGENTS.md.
4. Re-snapshot porcelain and peels.
5. `python3 scripts/grok_verify.py --mode pr`.
6. Hand to `code_reviewer` + `test_reviewer`. Do not record receipts until the last intended leftover file (this package’s review reports) is on disk.

Rollback: uncommitted restore/`rm` only. `git restore` already put tracked files back. Untracked deletes are gone unless the implementer still has a copy; do not compensate by committing or force-pushing.

---

## 8. Acceptance checklist (copy to `requirements.md`)

- [ ] HEAD is `975ccb20dfc5fb9e925602d177069abe7e5ccfbc` / `v2.0.10`.
- [ ] `VERSION` is `2.0.10`. No bump.
- [ ] No new commit. `origin/main` still that SHA (no push required).
- [ ] Sibling change-package dirt gone (`git status --porcelain` excluding this change-id).
- [ ] This package remains untracked (or, if removed, say so; reviews then have no on-disk home).
- [ ] Tags `v2.0.8` / `v2.0.9` / `v2.0.10` still peel to `0284241` / `f72c0fc` / `975ccb2`.
- [ ] `packages/…v2.0.0`–`v2.0.10.zip*` still tracked.
- [ ] README / CHANGELOG / AGENTS.md / `packages/README.md` untouched.
- [ ] No force-push, no tag delete, no zip delete, no `gh release delete`.
- [ ] `grok_verify --mode pr` PASS on the cleaned tree.

---

## 9. Open / unverified

- Live `git status --porcelain` was not executed by this agent. The three `state.json` paths and “untracked sibling evidence” come from the change-package allow-list (`brief.md`, `architecture.md`) plus working copies observed as `released` / `ready` / `verifying`. Implementer must confirm they actually differ from `HEAD` before restore, and must list every `??` sibling path before `rm`.
- Annotated tag objects were not peeled here (zlib git objects). Required peels are those already recorded in this package and `decisions.md`; implementer confirms with `git rev-parse 'v2.0.8^{}'` etc.
- Whether entire untracked sibling **directories** exist (vs only extra evidence files inside tracked packages) is unknown without porcelain. Rule: fully untracked sibling dirs may be `rm -rf`; mixed packages lose only untracked extras.

This report is analysis only. It does not authorize a commit, tag mutation, or remote write.
