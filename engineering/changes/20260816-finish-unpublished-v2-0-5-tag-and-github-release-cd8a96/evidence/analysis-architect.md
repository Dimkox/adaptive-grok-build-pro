# Analysis — architect (last mile for already-landed v2.0.5)

Change: `20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96`  
Active route: `cd8a9662bc68` · intent=`feature` · risk=`low` · write=`general_implementer` · reviews=`code_reviewer`+`test_reviewer` · gates=`[]`  
Prior durable package: `ad4090c51ca6` (status `ready`; ship already committed)  
User: «хули не запушено… там 2.0.4… делай»

Read-only design. No application-code edits. No `.env` read. No push / tag / merge / `gh release` from this agent.

Narrow question: safe last-mile sequence to publish the already-committed v2.0.5, given the local annotated tag already exists on `7c0ae75` and `origin/main` is already at that SHA.

## Ruling

**Do not retag. Do not commit. Do not push `main` again. Push the existing `v2.0.5` tag, then create GitHub Release `v2.0.5` from the tracked zip + this tree’s `dist/RELEASE-NOTES.md`. Write owner prints only.**

| # | Decision | Ruling |
| --- | --- | --- |
| 1 | Command sequence | Preconditions → `git push origin v2.0.5` → `gh release create v2.0.5 …`. Skip packager, `cp`, `git tag`, `git push origin main`. `grok_approve` is **not** in the human sequence. |
| 2 | Move/recreate local tag? | **No.** Leave `refs/tags/v2.0.5` = annotated object `7f85f7be…` pointing at `7c0ae75`. Do not `-d`, `-f`, or `tag -a` again. |
| 3 | Another `main` commit before tag push? | **No.** Dirty paths are leftover change-package evidence (ad4090 + this cd8a96 template). They are not the ship. |
| 4 | Rollback | Delete only release `v2.0.5` + remote/local tag `v2.0.5`. Do not touch `v2.0.4` / `33a02f1`. No force-push. |
| 5 | Write owner after «делай» | **Print commands only.** Do not execute last mile. |
| 6 | Reason not to create GitHub Release now? | **None.** Product is already on `origin/main`. Remaining gap is advertisement (tag + Release). Go. |

«там 2.0.4» is the **GitHub Releases latest** badge, not `main`. Public `main` already is 2.0.5. There is no PR to merge.

## Current facts (inspected this wave)

| Item | Value |
| --- | --- |
| Local `HEAD` / `main` | `7c0ae7573535ddd0cfe3800f81278991ced81584` — `Release v2.0.5: hook shims, toolchain pins, track zip and checksum` |
| `origin/main` (ref + reflog `update by push`) | same SHA |
| GitHub `GET /commits/main` | same SHA; `VERSION` raw on `main` = `2.0.5` |
| `FETCH_HEAD` | `7c0ae75` for `origin/main`; remote tags listed only through `v2.0.4` |
| Local tag `v2.0.5` | annotated object `7f85f7be43fd8008f6af522a967ebc5268a481d1` (ad4090 `code-review-merge.md`: peeled target is `7c0ae75`, not `33a02f1`) |
| Local tag `v2.0.4` | still `10c522f294bc5ffbdbef32d1487af59ff4e8453b` (untouched) |
| GitHub `refs/tags/v2.0.5` | **404** |
| GitHub `matching-refs/tags/v2.0` | `v2.0.0`–`v2.0.4` only; `v2.0.4` still `10c522f` |
| GitHub `releases/latest` | `v2.0.4` (id `370918434`) |
| GitHub `releases/tags/v2.0.5` | **404** |
| Zip digest | `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` (`packages/` + `dist/` siblings) |
| `dist/RELEASE-NOTES.md` | CHANGELOG `## 2.0.5` verbatim (gitignored scratch; present in this worktree) |
| `approvals.json` | two rows dated `2026-08-15T03:13:13Z`, expired `03:33:13Z`. **Dead.** |
| Active change status | `draft` (cd8a96 template) |
| cd8a96 receipts | empty |
| CI `.github/workflows/adaptive-grok.yml` | verify + upload `dist/*.zip*` artifact; **no** `gh release` / `git push` |

Leftover after `7c0ae75` (do not add before tag push): ad4090 evidence written after the ship (`implementation.md`, reviews, `*-merge.md`), working `ad4090/state.json`, this whole `cd8a96` package, runtime, `err.log`, `dist/**`. Stay out of any add: `.env`, `.env.*`, keys.

## 1. Exact command sequence

`scripts/grok_deploy.py` / `deploy.py:_human_commands` still print the full six-line runbook (`package_stack` → `cp` → `git tag` → `git push origin <branch>` → `git push origin v2.0.5` → `gh release create`). That printer is **stale relative to this tree**: packager, `cp`, tag, and `main` push are already done. Running `grok_deploy.py` **now also fails**: change is `draft` and route `cd8a9662bc68` has no verification/review receipts (`deploy.py:55-63`). That failure is not a publish blocker. Use the reduced sequence below.

### Human shell (authorized last mile)

No `grok_approve`. PreToolUse does not apply to a human terminal.

```bash
# Preconditions — stop if any expect fails
git fetch origin
git rev-parse 'v2.0.5^{}'
# expect 7c0ae7573535ddd0cfe3800f81278991ced81584
git rev-parse origin/main
# expect 7c0ae7573535ddd0cfe3800f81278991ced81584
git ls-remote --tags origin 'refs/tags/v2.0.5'
# expect empty
# zip sibling must still be
# b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd  adaptive-grok-build-pro-v2.0.5.zip

# Last mile — existing annotated tag first, then Release attached to that ref
git push origin v2.0.5
gh release create v2.0.5 \
  packages/adaptive-grok-build-pro-v2.0.5.zip \
  packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 \
  --notes-file dist/RELEASE-NOTES.md

# Confirm
git ls-remote --tags origin 'refs/tags/v2.0.5'
gh release view v2.0.5
# latest must be v2.0.5; v2.0.4 must still exist as the previous release
```

Order is load-bearing: **push the local annotated tag, then create the release.** `gh release create v2.0.5` before the ref exists on origin can mint a *different* remote tag from `HEAD`. A later `git push origin v2.0.5` would then reject (or require `-f`, which is forbidden).

### Skip (already done / would make things worse)

| Command | Why skip |
| --- | --- |
| `python3 scripts/package_stack.py` | Rebuild would include post-`7c0ae75` evidence and break digest `b80e6310…` |
| `cp dist/…v2.0.5.zip* packages/` | Tracked zip already in `7c0ae75` |
| `git tag -a v2.0.5 …` | Tag exists. Re-run errors. `-f` would retarget — forbidden |
| `git push origin main` / `git push origin 7c0ae75:main` | Origin already at that SHA. A later evidence commit would ride along if `HEAD` moves |
| `python3 scripts/grok_deploy.py` | Optional print only; currently fails on `draft` + missing receipts |
| `python3 scripts/grok_deploy.py --record` | Needs live production approval; still does not publish |

### `grok_approve` — only a PreToolUse unblock, not this sequence

```bash
python3 scripts/grok_approve.py production --reason "publish v2.0.5 tag and GitHub Release"
```

- **Human shell:** not required. `evaluate_pre_tool` only sees agent `Bash`.
- **Agent `git push` / `gh release create`:** required. `policy.py` `PRODUCTION_INVOCATIONS` is `('git','push')` and `('gh','release','create')`. Live `approvals.json` rows expired 2026-08-15. `test_policy.py` locks deny-without / allow-with.
- **`grok_approve.py production` itself** is allowed without a prior token (`test_approve_script_is_not_blocked_by_scope_argument`).
- A fresh 15-minute token **does not** authorize the write owner to execute. Adaptive-delivery close, `release-readiness`, `grok_deploy.py:15`, `publish-v2.0.5.md:5`, and `.grok/agents/general_implementer.md:12` still say humans run the printed commands.

Do not use MCP `create_release` / `create_or_update_ref`. That is an `external-write` side effect and a second publisher next to the runbook.

## 2. Do not move or recreate the local tag

`.git/refs/tags/v2.0.5` is annotated object `7f85f7be43fd8008f6af522a967ebc5268a481d1`. ad4090 `code-review-merge.md` already peeled it to `7c0ae75` and confirmed it is not `33a02f1`. This prompt forbids retargeting.

- `git tag -a v2.0.5` → fatal: tag exists. Do not “fix” with `-f`.
- `git tag -d v2.0.5` then recreate → unnecessary risk of tagging a later paperwork `HEAD`.
- `git tag` is **not** a production invocation; the hook would not stop an agent retag. The runbook still forbids it.

`git tag` is done. Only `git push origin v2.0.5` remains for the ref.

## 3. No second commit on `main` before the tag push

`7c0ae75` already contains VERSION/CHANGELOG/README 2.0.5, the tracked zip + sha256, and `engineering/runbooks/publish-v2.0.5.md`. Parallel clones already see 2.0.5 **source** on `main`. They still see latest **Release** 2.0.4 because the tag and Release were never published.

Uncommitted paths are paperwork:

- ad4090 evidence written *after* the ship commit
- this `cd8a96` template (brief/requirements/architecture still empty)
- gitignored runtime / `dist/` / `err.log`

A pre-push evidence commit would move `HEAD` off the reviewed ship SHA, create tag-vs-`main` skew, and tempt a packager rebuild. Same ruling as ad4090 `analysis-architect-merge.md` §1, now stronger because `origin/main` is already `7c0ae75`.

Optional hygiene commit **after** `v2.0.5` exists on origin is out of this last mile. Do not retag after that commit.

## 4. Rollback that does not touch v2.0.4

Unchanged from `engineering/runbooks/publish-v2.0.5.md` and ad4090 `rollback.md`:

```bash
gh release delete v2.0.5 --yes
git push origin :refs/tags/v2.0.5
git tag -d v2.0.5
```

| Must not | Why |
| --- | --- |
| `gh release delete v2.0.4` / edit that release | Published 2.0.4 stays the previous artifact |
| `git push origin :refs/tags/v2.0.4` / retag `v2.0.4` | Remote tag still `10c522f` → `33a02f1` |
| `git push --force` / `git reset --hard` | `policy.py` `DESTRUCTIVE_COMMANDS`; would rewrite `main` |
| Revert `7c0ae75` as part of a *failed tag/Release* | `main` is already the intended 2.0.5 tree. Only withdraw the unpublished advertisement |
| Delete `packages/…v2.0.5.zip*` | Tracked on `7c0ae75`; belongs on `main` even if the Release is withdrawn |

If `main` itself must come back later: revert `7c0ae75` and push (fresh production approval if an *agent* pushes). That is a separate decision, not this last mile.

Note: `gh release delete` is **not** in `PRODUCTION_INVOCATIONS` (only `gh release create`). Rollback is still human-owned so v2.0.4 cannot be deleted by a sloppy agent command.

Partial-failure matrix:

| After | Next |
| --- | --- |
| Tag push fails | Stop. Do not `gh release create`. Fix auth. Retry tag push only |
| Tag push ok, `gh` fails | Retry `gh release create` only. Do not retag |
| Release created against the wrong tag object | Rollback **v2.0.5 only** (delete release + remote tag). Recreate from the local annotated tag after it again peels to `7c0ae75`. No `-f` on `v2.0.4` |
| Notes wrong | `gh release edit v2.0.5 --notes-file dist/RELEASE-NOTES.md`. Do not retag |
| Zip wrong after publish | Rollback v2.0.5 only; new commit + **new** tag name. No `git tag -f v2.0.5` |

## 5. Write owner does not execute last mile after «делай»

`general_implementer` is idle for product writes. Last mile is not application code.

| Action | Who |
| --- | --- |
| Fill cd8a96 brief/requirements/rollback text (paperwork only) | Write owner, **after** tag+Release or as non-committed notes. Do not commit before tag push |
| `package_stack` / retag / `git add` leftover evidence | Nobody |
| `git push origin v2.0.5` / `gh release create` | **Human shell** |
| Print the two remaining commands + preconditions | Write owner / controller |

Why «делай» does not flip ownership:

1. Source of truth #1 authorizes the **publish outcome** (tag on origin + GitHub Release v2.0.5). It does not repeal the last-mile contract.
2. Adaptive-delivery close (`SKILL.md:103`): do not deploy/publish/merge as closure; humans own `grok_deploy.py` printed commands.
3. `release-readiness` SKILL.md:20, `grok_deploy.py:15`, `deploy.py` (no subprocess), `tests/test_deploy.py:184-191`.
4. `publish-v2.0.5.md:5` and `publish-v2.0.4.md:3,40-42`.
5. `.grok/agents/general_implementer.md:12`: do not push, merge, or deploy.
6. Empty `human_gates` is a rematch artifact (`делай` / cursing is not an intent keyword; `_best_intent` defaulted to `feature`). Not permission to publish.
7. 2.0.4 chat precedent where agents pushed anyway is source of truth #6. The 2.0.5 runbook wins.
8. Expired `approvals.json` rows. Even a fresh `grok_approve` only lifts PreToolUse.

This report is design. It is not authorization for the architect or write owner to run the last mile.

## 6. No architectural reason to delay GitHub Release v2.0.5

Go, because:

- Ship commit is already the public `main` tip.
- Artifact + digest + 2.0.5 notes are already reviewed (ad4090 code/test review).
- Local annotated tag already pins `7c0ae75`.
- CI on tag push only verifies and uploads a *workflow* zip artifact; it does not create a Release (`test_template_package_job_is_conditional_and_has_no_publish`). No race with `gh release create` except “don’t let CI’s rebuilt zip replace the tracked asset” — `gh` must use `packages/…v2.0.5.zip`, not `dist/` from Actions.
- Rollback isolates v2.0.5 from v2.0.4.
- User-visible bug is exactly “Releases latest = 2.0.4”.

Not blockers:

| Observation | Why it does not delay the Release |
| --- | --- |
| cd8a96 is `draft` / templates empty | Session paperwork. Not the ship |
| This route has no receipts yet | Receipts close `cd8a9662bc68`. They do not publish |
| Dirty evidence files | Not in the tag, not in the tracked zip, not in notes |
| `grok_deploy.py` fails | Printer gated on `ready` + evidence; commands are known |
| Dead production approvals | Human shell does not need them |
| No PR | Land is already a fast-forward that happened |

No-go only if a precondition fails at execution time: `origin/main` moved off `7c0ae75`, local `v2.0.5` no longer peels to `7c0ae75`, origin already has a *different* `v2.0.5` object, or the zip digest changed. Then stop. Reassess. No `-f`.

## Write-owner residual (non-publish)

None for the product. After the human last mile:

1. Mark ad4090 tag/push/Release boxes and transition ad4090 `ready` → `released` if desired.
2. Optionally write cd8a96 brief/requirements from this report; do not fold that paperwork into a new tag.
3. Controller: `grok_verify.py --mode pr` + listed reviews bind to whatever tree then exists (will include this analysis file). Those receipts close the session. They are not a second ship.

**Go / no-go:** go on the existing tag + existing `main`. No-go on retag, second commit, packager rebuild, force-push, touching v2.0.4, or agent-executed `git push` / `gh release`.
