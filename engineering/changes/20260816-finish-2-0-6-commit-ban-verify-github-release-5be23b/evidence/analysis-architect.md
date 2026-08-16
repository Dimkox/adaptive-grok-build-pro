# Analysis — architect

Change: `20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b`  
Route: `5be23b16d59f` · intent=`feature` · risk=`low` · write=`general_implementer` · reviews=`code_reviewer`+`test_reviewer` · gates=`[]` · evidence=`verification`,`code_review`,`test_review`  
User remaining sequence: (1) commit ban+rebuilt zip on 2.0.6, no `pyproject.toml`, no leftover ad4090 dirt (2) controller verify+reviews (3) last mile on the **new** SHA, not `549f29d`. `grok_approve` before push/release. No GHA. No edits.

Read-only design. No application-code edits from this agent. No `.env`. No push / tag / merge / `gh release`.

Narrow question: exact vertical so `general_implementer` commits the already-landed ban+zip and then stops, and the controller can verify, review, and publish Latest on that new SHA.

---

## Ruling (one screen)

**Do not edit product files. Do not rebuild the zip. Commit the on-disk GHA ban + existing `packages/` digest `55406ff2…` as unpublished 2.0.6. Then controller `grok_verify --mode pr` + independent reviews. Then last-mile tag the successor of `549f29d`, never `549f29d` itself.**

`9fd274` already implemented the ban, inverted the tests, and rebuilt the zip. This route owns the remaining three steps. `864726` (tag `549f29d`) and hollow `39b13f` are void. `ad4090` / `cd8a96` are the published 2.0.5 record — do not fold their leftover paperwork into this ship commit.

| In | Out |
| --- | --- |
| Explicit `git add` of the ban + rebuilt `v2.0.6` zip/sha256 | `git add -A`; `git add .`; adding leftover `ad4090` / `cd8a96` / `864726` / `39b13f` dirt |
| Stay `VERSION` 2.0.6 | `pyproject.toml` / `requirements.txt` / `setup.py`; bump to 2.0.7 |
| Existing zip `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d` | `python3 scripts/package_stack.py` (would fold post-rebuild change dirt and change the digest) |
| Tag **NEW** commit after verify+reviews | Tag `549f29d`; retag `v2.0.5`; force-push |
| `grok_approve.py production` then push main, push tag, `gh release create` with that zip + `dist/RELEASE-NOTES.md` | GitHub Actions; MCP `create_release`; new CI vendor |

`human_gates` is empty → implementer proceeds after this design. Last mile is still policy-gated: agent Bash `git push` / `gh release create` need a **live** production token. Expired 2.0.5 rows in `approvals.json` are dead.

---

## 1. Current facts (inspected this wave)

| Item | Value |
| --- | --- |
| Local `HEAD` / `refs/heads/main` | `549f29da1c4ff44ba44d8388c294fd5dd29bfd81` — `Release v2.0.6: ruff, bandit, coverage, dependabot` |
| `origin/main` | `7c0ae7573535ddd0cfe3800f81278991ced81584` (published v2.0.5) |
| Ancestry | linear: `7c0ae75` → `549f29d` (`.git/logs/HEAD`) |
| Local tags | `v2.0.0`–`v2.0.5`. **No** `refs/tags/v2.0.6` |
| Local `v2.0.5` | annotated object `7f85f7be43fd8008f6af522a967ebc5268a481d1` |
| GitHub Latest | **v2.0.5** @ `7c0ae75` (public `/releases/latest`, 16 Aug 16:10) |
| Remote | `origin` = `https://github.com/Dimkox/adaptive-grok-build-pro.git` |
| `VERSION` | `2.0.6` (unpublished) |
| On-disk zip digest | `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d` (`packages/` and `dist/` siblings match) |
| Stale unpublished digest on `549f29d` | `b34af685c8d277aafcfbc4aa3f393286b12af2b092e5efa2b74ab6f5ba41b610` — do not ship |
| v2.0.5 zip | `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` — **do not touch** |
| Live GHA on disk | **gone** — `.github/` does not exist |
| Template YAML | **gone** — `.grok-stack/templates/ci/` is README only |
| `--with-ci` | `SystemExit` / `forbidden` at start of `install()` |
| Packaging markers | **absent** — no `pyproject.toml`, `requirements.txt`, `setup.py`, root `MANIFEST.sha256` |
| `dist/RELEASE-NOTES.md` | CHANGELOG `## 2.0.6` verbatim (gitignored scratch; present) |
| This change | `draft`. Active change pointer is this `5be23b` package |
| Prior implement | `9fd274` status `implementing`; 177 tests + `grok_verify --mode pr` PASS recorded |
| Approvals | two rows, expired `16:24:55Z`, reason “publish v2.0.5”. **Dead.** |

`549f29d` still ships `.github/workflows/adaptive-grok.yml` and Dependabot. That is why it must not be tagged.

---

## 2. Why this is a commit, not another product edit

The ban is already on disk and characterized:

- Deleted: workflow, Dependabot, `templates/ci/github-actions.yml`
- `install(..., with_ci=True)` raises before any copy
- Tests lock absence + refuse (`test_deploy`, `test_installer`, `test_structure`, `test_manifest_package`)
- `decisions.md` 2026-08-16 never-GHA entry exists
- CHANGELOG / `dist/RELEASE-NOTES.md` §2.0.6 already say no GHA / `--with-ci` forbidden
- Zip rebuilt; in-zip `VERSION` is 2.0.6; namelist has no workflow / Dependabot / `github-actions.yml`

A second `package_stack.py` now would walk `engineering/changes/**` (not excluded by `included_files`) and fold this `5be23b` package plus leftover sibling dirt into a **new** digest. User pinned `55406ff2…`. **Do not rebuild.**

---

## 3. Write owner — commit only

Exactly one write owner: `general_implementer`. No second implementer. No product file edits. No Bitrix core. No `.env`.

### 3.1 Preconditions before `git add`

Stop if any fail:

1. `VERSION` is `2.0.6`.
2. No `pyproject.toml` / `requirements.txt` / `setup.py` at repo root.
3. No `.github/workflows/*.yml`, no `.github/dependabot.yml`, no `templates/ci/github-actions.yml`.
4. `packages/adaptive-grok-build-pro-v2.0.6.zip.sha256` body starts with `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d`.
5. `packages/adaptive-grok-build-pro-v2.0.5.zip.sha256` still starts with `b80e6310…`.
6. No local/remote `refs/tags/v2.0.6` (re-check immediately before commit is enough for the writer; controller re-checks before tag).

### 3.2 Explicit include list (required)

```bash
git add -u -- \
  .github/workflows/adaptive-grok.yml \
  .github/dependabot.yml \
  .grok-stack/templates/ci/github-actions.yml
git add -- \
  .grok-stack/templates/ci/README.md \
  scripts/install_into.py \
  tests/test_installer.py \
  tests/test_deploy.py \
  tests/test_structure.py \
  tests/test_manifest_package.py \
  engineering/decisions.md \
  CHANGELOG.md \
  engineering/runbooks/publish-v2.0.6.md \
  packages/adaptive-grok-build-pro-v2.0.6.zip \
  packages/adaptive-grok-build-pro-v2.0.6.zip.sha256
```

`-u` on the three deletes is the deletion staging. If a path is already gone from the index, that is success. Do not recreate them.

`packages/README.md` already has the 2.0.6 row on `549f29d`. Add it only if it is actually dirty.

### 3.3 Allowed same-commit owning records

These may ride **in the same commit** if the writer wants the engineering record on the ship SHA:

- `engineering/changes/20260816-ban-gha-rebuild-and-verify-2-0-6-publish-9fd274/`
- `engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b/`

If they ride, add the folders as they exist at commit time. Still **do not rebuild** the zip. Post-commit review reports and `state.json` transitions stay uncommitted.

### 3.4 Forbidden from the index (leftover dirt)

Never stage:

| Path | Why |
| --- | --- |
| `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/` | leftover ad4090 dirt |
| `engineering/changes/20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96/` | leftover 2.0.5 last-mile paperwork |
| `engineering/changes/20260816-publish-v2-0-6-github-release-864726/` | void — would tag `549f29d` |
| `engineering/changes/20260816-ban-github-actions-publish-2-0-6-without-them-39b13f/` | hollow sibling |
| `pyproject.toml` / `requirements.txt` / `setup.py` | flips `detect_repo`; can skip unittest |
| root `MANIFEST.sha256` | packager scratch; `9fd274` already deleted it |
| `dist/**` | gitignored scratch (notes stay on disk for `--notes-file`) |
| `.grok-stack/runtime/**` | gitignored; includes dead approvals |
| `err.log`, `.env`, `.env.*`, keys | secrets / dumps |
| `packages/adaptive-grok-build-pro-v2.0.5.*` | published 2.0.5 |
| `VERSION` | already `2.0.6`; do not touch |

`git add -A` is a no-go. After staging, `git diff --cached --stat` must not mention `ad4090`, `pyproject`, `v2.0.5.zip`, or `.github/workflows` as an **add**.

### 3.5 Commit

Suggested message (writer may tighten wording, not the meaning):

```
Release v2.0.6: never GitHub Actions, local grok_verify

Ban workflows, Dependabot, and --with-ci copy. Keep VERSION 2.0.6.
Rebuilt zip digest 55406ff2. No pyproject.toml.
```

Then **stop**. Do not `git tag`. Do not `git push`. Do not `gh`. Do not run `package_stack.py`. Write `evidence/implementation.md` with the new SHA if useful; leave that file uncommitted if it appears after the commit.

`git commit` is not a production invocation. No `grok_approve` for this step.

---

## 4. Controller — verify + reviews (after the commit)

Do not make a second product commit. Transition this package `implementing` → `verifying` → `reviewing` → `ready` in `state.json` without folding that dirt into a new SHA.

1. Confirm `HEAD` ≠ `549f29d` and `git merge-base --is-ancestor 549f29d HEAD`.
2. Confirm staged/uncommitted leftover dirt is **not** required for the ship; do not `git add` it.
3. `python3 scripts/grok_verify.py --mode pr` — required evidence kind `verification`. Expect `profiles=base` plus the hardcoded Python contour (ruff / bandit / unittest / coverage if those CLIs are on PATH).
4. Dispatch **only** `code_reviewer` and `test_reviewer` on the actual diff vs `549f29d` (or vs the new commit’s parent). They must see: no GHA, no `pyproject.toml`, zip digest `55406ff2…`, 2.0.5 zip untouched, no leftover ad4090 in the commit.
5. Record receipts **after** the last intended `state.json` write:

```bash
python scripts/grok_review.py code_review --status pass --report engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b/evidence/code-review.md
python scripts/grok_review.py test_review --status pass --report engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b/evidence/test-review.md
```

6. `python3 scripts/grok_status.py` — zero evidence gaps.

A failing check returns to the same write owner. Do not record reviews against a failing tree. Do not spawn `security_reviewer` / `release_reviewer` (not on this route).

---

## 5. Last mile (after `ready` + live approve — not this report)

`864726` is void. Tag the **new** ban+zip commit.

Default runbook `engineering/runbooks/publish-v2.0.6.md` still prints `package_stack` + `cp`. Those are already done. **Do not run them.** `grok_deploy.py` may also fail while this change is not `ready` or receipts are missing — that failure is not a publish blocker once the sequence below is satisfied. Use the SHA-pinned commands.

Order is load-bearing:

1. `python3 scripts/grok_approve.py production --reason "publish v2.0.6 without GitHub Actions"` (agent Bash only; 15 min TTL). Finish tag + both pushes + `gh` inside that window.
2. Preconditions — stop if any fail:
   - `origin/main` is still `7c0ae75` or a fast-forward of it
   - local `v2.0.5^{}` still peels to `7c0ae75`
   - **no** local or remote `refs/tags/v2.0.6`
   - `HEAD` / `NEW_SHA` ≠ `549f29d`
   - `VERSION` is `2.0.6`
   - zip sibling still `55406ff2…`
   - working tree may be dirty with leftover change paperwork; that must **not** be added
3. `git tag -a v2.0.6 <NEW_SHA> -m "v2.0.6"`
4. `git push origin <NEW_SHA>:refs/heads/main`
5. `git push origin v2.0.6`
6. `gh release create v2.0.6 packages/adaptive-grok-build-pro-v2.0.6.zip packages/adaptive-grok-build-pro-v2.0.6.zip.sha256 --notes-file dist/RELEASE-NOTES.md`

Who executes: **controller** (or a human terminal) after the write owner returns the commit. Not architect. Not reviewers. Not `39b13f` / `864726` / `9fd274` as a second publisher.

- `git tag` is not a production invocation. Still pin `<NEW_SHA>`.
- `git push` and `gh release create` are `PRODUCTION_INVOCATIONS`. Agent Bash needs the live token. Human terminal may skip the token; command bytes stay the same.
- `external-write` is not required. Do not call MCP `create_release` / `create_or_update_ref`.
- `git push origin main` is acceptable only if `HEAD` is `<NEW_SHA>` and the push is a fast-forward. Prefer the SHA-ref form.

No-go: remote already has `v2.0.6`; `v2.0.5` moved; non-ff `main`; zip digest changed; tag created on `549f29d`. Then stop. No `-f`.

Rollback (already in this package):

```bash
gh release delete v2.0.6 --yes
git push origin :refs/tags/v2.0.6
git tag -d v2.0.6
```

Do not touch `v2.0.5`. Restore GHA only by reverting the ban commit. No force-push.

---

## 6. File ledger

| Path | Action |
| --- | --- |
| `.github/workflows/adaptive-grok.yml` | **Stage delete** (already gone on disk) |
| `.github/dependabot.yml` | **Stage delete** |
| `.grok-stack/templates/ci/github-actions.yml` | **Stage delete** |
| `.grok-stack/templates/ci/README.md` | **Stage** (already rewritten) |
| `scripts/install_into.py` | **Stage** (already `SystemExit`) |
| `tests/test_installer.py` | **Stage** |
| `tests/test_deploy.py` | **Stage** |
| `tests/test_structure.py` | **Stage** |
| `tests/test_manifest_package.py` | **Stage** |
| `engineering/decisions.md` | **Stage** |
| `CHANGELOG.md` | **Stage** §2.0.6 already amended |
| `engineering/runbooks/publish-v2.0.6.md` | **Stage if dirty** |
| `packages/adaptive-grok-build-pro-v2.0.6.zip*` | **Stage existing rebuild** |
| `dist/RELEASE-NOTES.md` | **Do not add** (gitignored; last mile reads it) |
| `VERSION` | **Do not touch** |
| `packages/…-v2.0.5.*` | **Do not touch** |
| `pyproject.toml` | **Must not exist; do not create** |
| Sibling `…-ad4090/` `…-cd8a96/` `…-864726/` `…-39b13f/` | **Do not stage** |
| Product sources already matching `549f29d` | **Do not edit** |

---

## 7. Risks

| Risk | Mitigation |
| --- | --- |
| Tagging `549f29d` by habit (`864726` muscle memory) | Last mile pins `<NEW_SHA>`; preconditions refuse `HEAD == 549f29d` and refuse an existing `v2.0.6` |
| `git add -A` folds ad4090 / void siblings | Explicit include list; cached-diff check |
| Rebuild changes digest off `55406ff2…` | Ban `package_stack` / `cp` in both implement and last mile |
| Adding `pyproject.toml` to “replace” GHA pip-install | Tests + `decisions.md` already forbid it; writer must not create one |
| Dead 2.0.5 `approvals.json` rows reused | Mint a new production token in the 15-minute window |
| Second commit of review/`state.json` dirt before tag | Controller leaves that dirt uncommitted; tag the product SHA |
| Consumer trees that already have `adaptive-grok.yml` | Out of scope |

Residual: GitHub will stop running Actions on this repo once `main` has no workflow file. That is the intended signal.

---

## 8. Acceptance

- [ ] One new commit on `main` that is a successor of `549f29d` and is **not** `549f29d`
- [ ] That commit has no `.github/workflows/*.yml`, no Dependabot, no `pyproject.toml`, no leftover ad4090 paths
- [ ] Tracked zip digest is `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d`
- [ ] `python3 scripts/grok_verify.py --mode pr` PASS on that tree
- [ ] `code_review` + `test_review` receipts bound after the last intended package write
- [ ] Annotated `v2.0.6` peels to that new SHA
- [ ] `origin/main` is that SHA; GitHub Latest is `v2.0.6` with the rebuilt zip + `dist/RELEASE-NOTES.md`
- [ ] `v2.0.5` tag and release still peel to `7c0ae75`

---

## 9. What this agent did not do

No application edits. No commit. No package rebuild. No `git push` / `git tag` / `gh release`. No read of `.env`. Independent reviews wait for the committed tree.

This report is design. It is not a verification or review receipt.
