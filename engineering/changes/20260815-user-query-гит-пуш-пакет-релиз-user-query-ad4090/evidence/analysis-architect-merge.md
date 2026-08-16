# Analysis — architect (merge / land 2.0.5)

Change: `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090`  
Active route: `e2b4b7341a5c` · intent=`feature` · write=`general_implementer` · reviews=`code_reviewer`+`test_reviewer` · gates=`[]`  
Prior continue: `e85418e33648` (receipts exist; wrong `route_id` for this Stop)  
Durable package: `ad4090c51ca6` · status=`ready` · original intent=`release`  
User: «смерджи все»

Read-only design. No implementation. No `.env` read. No push / tag / merge / `gh release`.

Synthesized from local refs, `state.json`, `approvals.json`, `deploy.py`, `policy.py`, `grok_approve.py`, `publish-v2.0.5.md`, `rollback.md`, prior `evidence/analysis-architect.md`, `implementation.md`, `code-review.md`, `test-review.md`, and this wave’s `analysis-repo_explorer-merge.md` / `analysis-task_analyst-merge.md` / `analysis-docs_researcher-merge.md`. Public GitHub still advertises `v2.0.4` on `33a02f1`.

## Ruling

**Push `7c0ae75` as-is. Tag that SHA. Humans run last mile. Do not make a second commit. Do not re-run `package_stack.py`.**

| Question | Decision |
| --- | --- |
| Second commit of leftover ad4090 evidence/state, or push `7c0ae75` as-is? | **Push `7c0ae75` as-is.** Leave leftover evidence uncommitted. |
| Tag target | **`7c0ae7573535ddd0cfe3800f81278991ced81584`**, annotated `v2.0.5`. Not `33a02f1`. Not a later paperwork commit. |
| Who runs `git push` / `gh release` | **Human shell.** Not `general_implementer`. Not the controller. |
| Production approval | **False.** `approvals.json` is `[]`. «смерджи все» is a verbal go, not a live `grok_approve` token. |
| `package_stack.py` | **Do not re-run.** Would rewrite the zip to include post-commit evidence and break digest `b80e6310…`. |
| Rollback | **Unchanged.** Delete only `v2.0.5` (release + remote tag + local tag). Do not touch `v2.0.4`. |

«смерджи все» is colloquial “land it.” There is no PR, no second branch, no `MERGE_HEAD`. Local `main` is a direct child of `origin/main`. The land is a **fast-forward**, not `git merge` and not `gh pr merge`.

Empty `human_gates` on `e2b4b7341a5c` is a rematch artifact (`смердж` is not an intent keyword; `_best_intent` defaulted to `feature`). It is not permission for an agent to publish.

## Current facts

| Item | Value |
| --- | --- |
| Local `main` | `7c0ae7573535ddd0cfe3800f81278991ced81584` — `Release v2.0.5: hook shims, toolchain pins, track zip and checksum` |
| Parent / `origin/main` / GitHub `main` | `33a02f1128ab0a865bfb1c853248f997dcf9e39b` (tag `v2.0.4`) |
| Ahead | **1 commit**, fast-forward possible |
| Tag `v2.0.5` | Absent locally and on GitHub |
| GitHub latest | `v2.0.4` |
| Open PRs / other branches | None |
| `VERSION` / zip | `2.0.5` already in `7c0ae75`. Sibling digest `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` |
| `dist/RELEASE-NOTES.md` | CHANGELOG 2.0.5 verbatim. Gitignored scratch. Required by `deploy.py:33` |
| Change status | `ready` (working-tree `state.json`; committed copy is older) |
| Machine production approval | **Dead.** `approvals.json` = `[]`. Default TTL 15 minutes |
| e2b4b receipts | Empty |
| Root `MANIFEST.sha256` | Deleted after `7c0ae75` (doctor leftover). Do not regenerate |

### Leftover after `7c0ae75` (do not add before push)

- `evidence/implementation.md`
- `evidence/code-review.md`
- `evidence/test-review.md`
- working `state.json` (`ready` at `2026-08-15T02:51:12Z`; commit was `~02:42:20Z`)
- this wave’s `evidence/analysis-*-merge.md` files
- deleted untracked root `MANIFEST.sha256` (already gone)

Stay out of any add: `.env`, `err.log`, `.grok-stack/runtime/**`, `dist/**`, `__pycache__`.

## 1. No second commit

`7c0ae75` already contains the 2.0.5 product, the tracked zip + sha256, and the publish runbook. Parallel Grok processes see 2.0.4 because **origin** is still `33a02f1`, not because evidence reports are missing.

A pre-push evidence commit would:

1. Move `HEAD` off the reviewed ship SHA.
2. Create tag-target ambiguity (tag the paperwork commit, or tag `7c0ae75` and leave `main` ahead of the tag).
3. Invalidate fingerprint `6697b7cc…` (e85418 receipts; this route’s `base_fingerprint`).
4. Tempt a `package_stack.py` rebuild whose include set now contains those reports.

That is the opposite of smallest. Optional hygiene *after* `v2.0.5` points at `7c0ae75` is out of this land sequence. Do not retag. Do not force-push.

Write owner `general_implementer` remains the route’s single writer and is **idle** for landing. No product file writes remain. Do not amend `7c0ae75`. Do not `git add -A`.

## 2. Tag target

Pin the SHA. Do not rely on whatever `HEAD` is after this analysis wave.

```bash
git tag -a v2.0.5 -m "v2.0.5" 7c0ae7573535ddd0cfe3800f81278991ced81584
git rev-parse v2.0.5^{}
# must print 7c0ae7573535ddd0cfe3800f81278991ced81584
```

`git tag` is not in `PRODUCTION_INVOCATIONS`, so the hook would not block an agent tag. The runbook and adaptive-delivery still forbid it. Humans tag.

## 3. Who executes last mile

| Action | Who | Why |
| --- | --- | --- |
| Remaining product / zip / notes writes | **Nobody** | Already on disk / in `7c0ae75` |
| Second evidence commit | **Nobody** (this land) | See §1 |
| `python3 scripts/package_stack.py` | **Nobody** | Would rewrite zip to include post-commit evidence |
| `python3 scripts/grok_deploy.py` | Optional controller | Prints only. Will **fail** today: e2b4b evidence gaps. Not a publish blocker — commands are already known |
| `python3 scripts/grok_deploy.py --record` | Nobody unless a live production token exists | Still does not publish |
| `python3 scripts/grok_approve.py production` | Human, only if they later want `--record` or to unblock an agent hook | 15-minute TTL. Does **not** authorize the agent to execute |
| `git tag -a v2.0.5 … 7c0ae75` | **Human** | Runbook + last-mile contract |
| `git push origin 7c0ae75:main` | **Human** | `policy.py` `('git', 'push')`; `approvals.json` empty |
| `git push origin v2.0.5` | **Human** | same |
| `gh release create v2.0.5 …` | **Human** | `policy.py` `('gh', 'release', 'create')` |

`scripts/grok_deploy.py` never executes those commands (`tests/test_deploy.py:184-191`).

«смерджи все» + earlier «гит пуш пакет релиз» + «да» authorizes the **human** to run the printed commands. Markdown `human-approval.md` is not `has_valid_approval`. A fresh `grok_approve` would let the hook *pass* `git push` / `gh release create`; adaptive-delivery, `AGENTS.md` last mile, and `publish-v2.0.5.md:5` still say the human shell runs them. 2.0.4 chat precedent where agents pushed anyway does not repeal the 2.0.5 runbook.

Do not read `.env`. Human uses already-configured `git` / `gh`.

## 4. Human sequence (smallest)

Fetch first. If `origin/main` is no longer `33a02f1`, **stop**. Do not force-push. Do not rebase.

```bash
git fetch origin
git rev-parse origin/main
# expect 33a02f1128ab0a865bfb1c853248f997dcf9e39b

git tag -a v2.0.5 -m "v2.0.5" 7c0ae7573535ddd0cfe3800f81278991ced81584
git rev-parse 'v2.0.5^{}'
# expect 7c0ae7573535ddd0cfe3800f81278991ced81584

git push origin 7c0ae7573535ddd0cfe3800f81278991ced81584:main
git push origin v2.0.5
gh release create v2.0.5 \
  packages/adaptive-grok-build-pro-v2.0.5.zip \
  packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 \
  --notes-file dist/RELEASE-NOTES.md
```

Skip the runbook’s first two lines (`package_stack.py` + `cp`). Zip is already tracked. Notes file is this working tree’s `dist/RELEASE-NOTES.md` (not in git; a clean clone will not have it).

Pinning `7c0ae75:main` still fast-forwards even if local `HEAD` later gains an evidence commit.

After this, a fresh clone / other Grok that pulls origin sees `VERSION=2.0.5`, README H1 v2.0.5, CHANGELOG `## 2.0.5`, tracked zip, and GitHub latest `v2.0.5`. They will not see leftover evidence unless a later hygiene commit lands.

## 5. Do not re-run `package_stack.py`

`write_archive` embeds current `included_files` + a regenerated root `MANIFEST.sha256`. Post-commit evidence and this merge wave are ordinary `engineering/changes/**` paths. A rebuild now would:

- produce a **different** zip than `packages/adaptive-grok-build-pro-v2.0.5.zip` (`b80e6310…`);
- recreate untracked `MANIFEST.sha256` (fingerprint noise; previously made doctor fail);
- pressure a second commit and a new tag target.

Packager timestamps are frozen, but the **file set** is not the `7c0ae75` set anymore. Deterministic ≠ same as the already-shipped artifact.

## 6. Rollback (unchanged — delete only v2.0.5)

```bash
gh release delete v2.0.5 --yes
git push origin :refs/tags/v2.0.5
git tag -d v2.0.5
```

Do not delete or move `v2.0.4`. No force-push. If `main` must come back: revert `7c0ae75` and push (fresh production approval if an *agent* pushes). Leave unpublished zip files in `packages/` only if that revert happens.

| Risk | Mitigation |
| --- | --- |
| Tag lands on `33a02f1` or a later evidence commit | Explicit SHA on `git tag` and `git push origin <sha>:main` |
| Origin moved; FF rejected | Stop. Reassess. No `-f` |
| Agent runs push because gates=`[]` | Policy still requires live production approval; runbook still forbids it |
| `gh` uses 2.0.4 notes | Use this tree’s `dist/RELEASE-NOTES.md`. Fix with `gh release edit`, do not retag |
| Re-run packager | Forbidden. Existing digest is the release asset |
| Push succeeds, `gh` fails | Retry `gh release create` only |
| `gh` succeeds, zip wrong | Rollback `v2.0.5` only; new commit + new tag. No `git tag -f` |
| Session vs publish confusion | e2b4b receipts close **this session**. They do not publish. |

## 7. This session vs the publish

Keep the split. Do not rematch. Do not spawn `security_reviewer` / `release_reviewer`. Do not open a second change package.

| | Land 2.0.5 on origin | Close route `e2b4b7341a5c` |
| --- | --- | --- |
| Need | Human last mile on `7c0ae75` | `verification` + `code_review` + `test_review` on the tree that includes these merge reports |
| Write owner | Idle | Idle (no product change) |
| `grok_deploy.py` | Optional print; currently blocked by e2b4b gaps | After those receipts, print only |

Writing this file dirties fingerprint `6697b7cc…`. Expected. e85418 receipts become stale. That does not block the human push.

**Go / no-go:** go on the prepared tree. No-go on a second commit. No-go on agent-executed tag / push / `gh release`. This report is design only, not authorization to execute the last mile.
