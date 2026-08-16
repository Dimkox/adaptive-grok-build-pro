# Analysis — task_analyst (checklist only)

Change: `20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b`  
Route: `5be23b16d59f` · write=`general_implementer` · evidence=`verification` + `code_review` + `test_review` · gates=`[]`

User «go ahead» = finish unpublished **2.0.6**: **commit** the on-disk GHA ban, **`grok_verify --mode pr`**, then **tag / push / `gh release`**. Stay **2.0.6**. **Do not restore GHA.**

This agent is read-only. No application edits. No `.env`. No tag / push / merge / deploy from here.

---

## Ruling

Ban work is **already on disk** (`9fd274`). It is **not** in git. `HEAD` is still `549f29d` (GHA ship). Do **not** re-implement. Do **not** tag `549f29d`. Commit the successor, verify that tree, publish **that** SHA.

GitHub **Release** ≠ GitHub **Actions**. Prior «делай всё полностью вместе с релизом» still authorizes `gh release create`.

---

## Facts (do not treat remaining boxes as done)

| Item | Now |
| --- | --- |
| `VERSION` / README H1 | `2.0.6` |
| Local `main` / `HEAD` | `549f29d` — still ships GHA |
| `origin/main` + GitHub `main` | `7c0ae75` (v2.0.5) |
| Local / remote tag `v2.0.6` | **Absent** |
| GitHub Latest | **v2.0.5** @ `7c0ae75` (16 Aug 16:10). `/releases/tag/v2.0.6` 404 |
| On-disk `.github/` | **Gone** |
| Template YAML | **Gone**. `templates/ci/README.md` = never GHA |
| `--with-ci` | `SystemExit` / `forbidden` |
| Tracked zip | `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d` |
| Stale pre-ban zip | `b34af685…` |
| v2.0.5 zip | `b80e6310…` unchanged |
| `approvals.json` | Expired 2.0.5 tokens only |
| This package | `draft`. Receipts dir empty |
| Siblings | `9fd274` implementing (ban landed, not published). `864726` / `39b13f` leftover drafts |

---

## Already on disk — do not redo, do not revert

- [x] No `.github/workflows/*.yml`
- [x] No `.github/dependabot.yml`
- [x] No `.grok-stack/templates/ci/github-actions.yml`
- [x] `--with-ci` / `--with-ci --force` / `--with-ci --dry-run` write nothing
- [x] Tests lock the ban (`test_deploy`, `test_installer`, `test_structure`, `test_manifest_package`)
- [x] Unpublished §2.0.6 notes state the ban
- [x] `decisions.md` 2026-08-16 never GHA
- [x] Zip rebuilt; in-zip `VERSION` `2.0.6`; no workflow / Dependabot / `github-actions.yml` in namelist
- [x] `9fd274` recorded `grok_verify --mode pr` PASS (177 tests) — **stale after this commit**

---

## Remaining acceptance (close only when all true on the **same** SHA)

### A. Commit (stay 2.0.6, no GHA)

- [ ] One new commit on `main`, **successor of `549f29d`**, containing the ban + rebuilt zip
- [ ] `git show HEAD:.github/workflows/adaptive-grok.yml` fails (file not in commit)
- [ ] Commit does **not** restore Dependabot or `templates/ci/github-actions.yml`
- [ ] `VERSION` in that commit is exactly `2.0.6`
- [ ] No `pyproject.toml` / `requirements.txt` / `setup.py`
- [ ] `packages/…v2.0.5.zip*` byte-identical (`b80e6310…`)
- [ ] No force-push. No `git commit --amend` of `549f29d`. No `git checkout` of deleted GHA
- [ ] If `engineering/changes/**` rides in the commit, **rebuild zip after the last product file** and commit the matching `packages/…v2.0.6.zip*`. Ship digest may differ from `55406ff2…`; it must **≠** `b34af685…`
- [ ] Do not commit `.env`, `err.log`, root `MANIFEST.sha256`, or `.grok-stack/runtime/**` (except `.gitkeep`)

### B. Verify (after A, on the committed tree)

- [ ] `python3 scripts/grok_verify.py --mode pr` **PASS** (ruff, bandit, unittest, coverage)
- [ ] `python3 scripts/install_into.py <tmp> --with-ci` exits nonzero; no `adaptive-grok.yml`
- [ ] Independent `code_reviewer` + `test_reviewer` on the **actual commit diff**
- [ ] Package → `ready`, **then** bind `verification` / `code_review` / `test_review` to that fingerprint

### C. Last mile (after A+B + live production token)

- [ ] `python3 scripts/grok_approve.py production --reason "publish v2.0.6"` (do not reuse expired 2.0.5 rows)
- [ ] `git tag -a v2.0.6 -m "v2.0.6"` peels to the **post-ban** commit, **not** `549f29d`
- [ ] `git push origin main` (fast-forward `7c0ae75` → `549f29d` → ban commit)
- [ ] `git push origin v2.0.6`
- [ ] `gh release create v2.0.6 packages/adaptive-grok-build-pro-v2.0.6.zip packages/adaptive-grok-build-pro-v2.0.6.zip.sha256 --notes-file dist/RELEASE-NOTES.md`
- [ ] GitHub Latest = `v2.0.6` with the **committed** zip digest
- [ ] Release `v2.0.5` still exists

Order is load-bearing: **commit ban → rebuild zip if needed → `grok_verify` → reviews / `ready` / receipts → fresh approve → tag successor → push `main` → push tag → `gh release create`.**

---

## Out of scope

- [ ] Restore GHA / Dependabot / `--with-ci` copy / template YAML
- [ ] New CI vendor (GitLab, Woodpecker, Forgejo, Drone, Jenkins)
- [ ] Touch, retag, or rebuild **v2.0.5**
- [ ] Bump to 2.0.7 or rewrite `## 2.0.5`
- [ ] Tag `549f29d` / ship digest `b34af685…` (`864726` is void)
- [ ] Implement leftover `39b13f` / `864726` as a second write
- [ ] MCP `create_release` / `create_or_update_ref`
- [ ] `git push --force` / `git tag -f`

---

## Failures

| If | Then |
| --- | --- |
| Commit re-adds `.github/workflows` | Stop. Reset that path. Do not tag |
| `grok_verify` red | Return to `general_implementer`. No receipts, no tag |
| Tag already on `549f29d` (race) | Do **not** `git tag -f`. Stop |
| Push / `gh` without live token | PreToolUse denies. Mint new 15-minute token |
| `--with-ci` after commit writes a file | Ban is broken. Do not publish |

Rollback of a published `v2.0.6` only: `gh release delete v2.0.6 --yes`; `git push origin :refs/tags/v2.0.6`; `git tag -d v2.0.6`. Leave `v2.0.5`. Restore GHA only by revert, not force-push.

---

## Write owner

`general_implementer` only. Commit the existing ban tree. Re-run verify. Stop for reviews. Last mile after `ready` + live production token. Do not fold `864726` / `39b13f` into a second product change.
