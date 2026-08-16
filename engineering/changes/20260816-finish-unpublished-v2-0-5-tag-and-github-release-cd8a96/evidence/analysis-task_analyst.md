# Analysis — task_analyst

Change: `20260816-finish-unpublished-v2-0-5-tag-and-github-release-cd8a96`  
Active route: `cd8a9662bc68` · intent=`feature` · write=`general_implementer` · gates=`[]` · evidence=`verification` + `code_review` + `test_review`  
Durable prior package: `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090` · status=`ready` · never `released`  
User (angry): GitHub still shows 2.0.4; they think nothing was pushed/merged; they said «делай».

Read-only. No `.env` read. No push / tag / `gh release` / merge from this agent.

## Fact correction first

The user is half right. GitHub **Latest** is still 2.0.4. They are **wrong** that nothing was pushed or that a PR is missing.

| Item | Now | Source |
| --- | --- | --- |
| Local `main` / HEAD | `7c0ae7573535ddd0cfe3800f81278991ced81584` — `Release v2.0.5: hook shims, toolchain pins, track zip and checksum` | `.git/refs/heads/main`, `.git/logs/HEAD` |
| `origin/main` | **same SHA** | `.git/refs/remotes/origin/main` |
| GitHub `GET /commits/main` | **same SHA** (parent `33a02f1` = tag `v2.0.4`) | public API 2026-08-16 |
| PR | **None.** Nothing to merge. `main` already has the ship commit. | prior merge analysis + GitHub `main` |
| Local tag `v2.0.5` | **Exists.** Annotated object `7f85f7be43fd8008f6af522a967ebc5268a481d1`. Prior land review: not on `33a02f1`; intended target `7c0ae75`. | `.git/refs/tags/v2.0.5`, `ad4090/evidence/code-review-merge.md` |
| GitHub tag `v2.0.5` | **404** | `GET /git/refs/tags/v2.0.5` |
| GitHub Release `v2.0.5` | **404** | `GET /releases/tags/v2.0.5` |
| GitHub Latest | **`v2.0.4`** release id `370918434` on tag `v2.0.4` | `GET /releases/latest` |
| `VERSION` / notes / zip | Tree and `7c0ae75` are `2.0.5`. `dist/RELEASE-NOTES.md` = CHANGELOG §2.0.5. Digest `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd`. | `VERSION`, `CHANGELOG.md:3-12`, `packages/…v2.0.5.zip.sha256` |
| Machine production approval | **Dead.** Rows in `approvals.json` created `2026-08-15T03:13:13Z`, expired `2026-08-15T03:33:13Z`. Today is 2026-08-16. | `approvals.json`, `state.py:167-187` |

Why the Releases page still says Latest 2.0.4: GitHub Latest is the newest **Release object**, not `VERSION` on `main`. `main` already advertises 2.0.5. The unpublished last mile is only: push the existing local tag, then create Release `v2.0.5`.

Origin reflog last event is `update by push` of `33a02f1` → `7c0ae75`. An earlier land wave (`code-review-merge.md`) recorded a failed `git push` / `gh` auth attempt while origin was still `33a02f1`. A later push of `main` succeeded. Tag push and `gh release create` did not.

---

## 1. Remaining acceptance criteria (unpublished last mile only)

Already done on `7c0ae75` / working tree — **do not redo**:

- Zip `packages/adaptive-grok-build-pro-v2.0.5.zip` + sibling sha256
- `.env`, `err.log`, runtime (except `.gitkeep`) out of git and the zip
- Commit `7c0ae75` on `main`
- `git push origin main` (GitHub `main` == `7c0ae75`)
- Local annotated tag `v2.0.5` (do not create a second tag)
- `dist/RELEASE-NOTES.md` rewritten to CHANGELOG 2.0.5
- ad4090 change status `ready`

Remaining boxes (this is the entire publish gap):

- [ ] Confirm `git rev-parse 'v2.0.5^{}'` is still `7c0ae7573535ddd0cfe3800f81278991ced81584`. If it is not, **stop**. Do not retag. Reassess.
- [ ] `git push origin v2.0.5` — GitHub `GET /git/refs/tags/v2.0.5` returns the annotated tag, not 404
- [ ] `gh release create v2.0.5 packages/adaptive-grok-build-pro-v2.0.5.zip packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 --notes-file dist/RELEASE-NOTES.md`
- [ ] GitHub `GET /releases/latest` is `tag_name: v2.0.5` (no longer `v2.0.4` / id `370918434`)
- [ ] Release assets are the existing zip + sibling sha256; body is current `dist/RELEASE-NOTES.md` (CHANGELOG 2.0.5, not the 2.0.4 MIT wrapper)
- [ ] Tag `v2.0.4` and Release `v2.0.4` are untouched

Session-close evidence for route `cd8a9662bc68` (`verification` + `code_review` + `test_review`) is **not** a last-mile acceptance criterion. Completing those receipts does not flip GitHub Latest.

Human-owned commands (do **not** re-run `package_stack.py`; do **not** re-tag):

```bash
git rev-parse 'v2.0.5^{}'   # must be 7c0ae7573535ddd0cfe3800f81278991ced81584
git push origin v2.0.5
gh release create v2.0.5 \
  packages/adaptive-grok-build-pro-v2.0.5.zip \
  packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 \
  --notes-file dist/RELEASE-NOTES.md
```

`git push origin main` is a no-op if remotes still match. Include it only as a safety check, not as remaining work.

Rollback stays delete-only-`v2.0.5` (`ad4090/rollback.md`, `publish-v2.0.5.md`). Do not touch `v2.0.4`.

---

## 2. Non-goals

- **Do not retag, move, delete, or rewrite `v2.0.4`.** Do not edit Release `v2.0.4`. Do not rewrite commit `33a02f1`.
- **No force-push.** No `git push --force` / `-f`, no `git reset --hard`, no rebase onto origin. Origin is already the ship commit.
- **No new product features.** No VERSION bump past 2.0.5. No `__version__` tidy. No README/QUICKSTART/routing expansion. No zip rebuild. No tar.gz asset. No Bitrix/core work.
- **No PR** and no `gh pr merge`. `main` already has `7c0ae75`. «не смерджено» is a Releases-page illusion, not a missing pull request.
- **No second ship commit** of leftover ad4090 evidence, this analysis file, or cd8a96 paperwork before the tag is on GitHub. Tag target stays `7c0ae75`.
- **Do not re-run `package_stack.py`.** Tracked digest is `b80e6310…`.
- **Do not `git tag -a v2.0.5` again.** The local tag exists. Recreating it fails or (with `-f`) moves the tag — both out of scope.
- Do not treat this rematched `intent=feature` route as permission to implement anything beyond last-mile publish-prep docs/evidence. Write owner must not `git add -A`.
- Do not read `.env`. Do not print credentials.
- Do not rematch just to resurrect `security_reviewer` / `release_reviewer`. They are not in `allowed_agents`.

---

## 3. Is user «делай» sufficient short-lived production approval?

**Split ruling. Three different objects named “approval.”**

### A. User-approved scope to finish last mile — **yes**

User-approved scope is source of truth #1 (`AGENTS.md`). Already granted:

- 2026-08-15 ad4090 `evidence/human-approval.md`: «гит пуш пакет релиз» then «да». Authorized: commit 2.0.5 (done), `git push origin main` (done), tag `v2.0.5` (local only), package (done), GitHub Release (not done).
- 2026-08-15 «смерджи все» — land the prepared 2.0.5 publish. No PR.
- This prompt: they see Latest 2.0.4 and said «делай». Same outcome. No new product.

«делай» here is **not** a bare follow-up. `FOLLOW_UP_RE` (`router.py:51-54`) matches only a prompt that is *exactly* `делай`. This is a full rematch (`intent=feature`, new change cd8a96). Classification artifact. It does not change the authorized outcome.

### B. Live machine `has_valid_approval(..., 'production')` — **no**

Short-lived production approval in this repo is a TTL row in `.grok-stack/runtime/approvals.json` written by `python3 scripts/grok_approve.py production --reason "…"` (default 15 minutes, `grok_approve.py:18`). `has_valid_approval` (`state.py:167-187`) ignores markdown `human-approval.md`.

Current file: two rows from `2026-08-15T03:13:13Z` (`production` + `external-write`, reason «смерджи все»), expired `2026-08-15T03:33:13Z`. **Dead for more than a day.**

Chat «делай» does **not** write that row. PreToolUse (`policy.py:170-172`) will deny `git push` and `gh release create` (`PRODUCTION_INVOCATIONS`) until a human (or an explicitly approved `grok_approve` invocation) refreshes the token.

`git tag` is not a production invocation. It already happened locally. Do not tag again.

### C. License for an agent to execute last mile — **no**

Even after a fresh `grok_approve.py production --reason "publish v2.0.5"`:

- Adaptive-delivery §7: do not deploy/publish/merge as closure. Last mile is `python3 scripts/grok_deploy.py`; **humans own the printed commands**.
- `scripts/grok_deploy.py:15`: “Never executes tag, push, or release.”
- `engineering/runbooks/publish-v2.0.5.md:5`: “Agents must not run `git push`, `git tag`, or `gh release`.”
- Active route `human_gates` is `[]`. No named gate on this rematch waives last-mile ownership.

2.0.4 mixed precedent (`e584b3` `human-approval.md` records agents did push `097f5c9`/`33a02f1` and create that Release) does **not** authorize a repeat. That runbook already forbade it. The 2.0.5 runbook is explicit. Chat history is source of truth #6; policy and the active runbook win.

**Bottom line:** «делай» is sufficient for the **human** to run the two remaining commands. It is **not** a live 15-minute production token and it does **not** authorize `general_implementer` or the controller to run `git push origin v2.0.5` / `gh release create`. Refresh `grok_approve.py production` only if someone needs `--record` or the hook to *pass*; that still does not move execution off the human shell.

---

## 4. Risks: print commands again vs execute last mile

### If we only print the commands again

| Risk | Why it matters now |
| --- | --- |
| GitHub Latest stays `v2.0.4` | Tag 404 + Release 404. Printing does not create either. |
| User repeats the same complaint | They already authorized this on 2026-08-15 (`да`) and again («смерджи все»). A third print loop is why they think “нихрена не смерджено.” |
| Parallel clone / other Grok still downloads the 2.0.4 zip from Latest | `main` is 2.0.5, but Releases/Latest and `gh release view --latest` still serve `v2.0.4`. |
| Local-only tag can drift | Tag exists only here. A later `git tag -f` or a new commit before push would publish the wrong object. |
| Auth lesson is hidden | Prior land wave’s `git push`/`gh` failure was credentials, not missing commands. Printing again does not test whether `gh` is authenticated now. `main` push later succeeded; `gh` is still unproven. |
| ad4090 never reaches `released` | Status stays `ready`. Durable package looks unfinished forever. |

Print-only is correct **for this agent** (task_analyst) and remains the standing last-mile contract. It will **not** satisfy the user’s observable criterion (Latest ≠ 2.0.4).

### If an agent actually executes last mile

| Risk | Mitigation / ruling |
| --- | --- |
| PreToolUse deny | No live production approval. Hook blocks `git push` / `gh release create`. |
| Violates adaptive-delivery, `grok_deploy.py`, and `publish-v2.0.5.md:5` | Standing rule: human shell. «делай» does not repeal it. |
| `gh` still unauthenticated | Earlier land attempt: invalid username/token / invalid `gh` auth. `main` push later worked; `gh release create` may still fail. Then Latest stays 2.0.4 even if the tag lands. Retry only `gh release create`. Do not retag. |
| Re-running the full six-line runbook | `package_stack.py` can emit a different zip; `git tag -a v2.0.5` fails or (with `-f`) moves the tag. **Out of scope.** Run only push-tag + `gh release create`. |
| Force-push / rewrite `v2.0.4` | Destructive and prohibited. Rollback deletes **only** `v2.0.5`. |
| Wrong notes | `gh` attaching 2.0.4 notes is mitigated on disk: `dist/RELEASE-NOTES.md` is CHANGELOG 2.0.5. Use that working-tree file. Fix with `gh release edit`, not a retag. |
| Reading `.env` for tokens | Forbidden. Git/`gh` may use already-exported env; do not open the file or print values. |
| Public publish of the zip | Repo is already public; zip is already on `main`. Incremental risk is the Release object + Latest flip. Rollback: `gh release delete v2.0.5 --yes` + delete remote/local tag `v2.0.5`. |

### Bounded ruling

- **Go** on the prepared tree. Ship commit, zip, notes, and local tag are ready. `main` is already on origin.
- **Go** for the **human** to run the two remaining commands. «делай» + prior «да» / «смерджи все» is enough user intent for that.
- **No-go** on agent-executed `git push` / `gh release create` from this route. Print those two commands. Do not invent a PR. Do not retag `v2.0.4`. Do not force-push. Do not add product code.
- **No-go** on treating this analysis, cd8a96 paperwork, or leftover ad4090 evidence as a second commit before the tag is on GitHub.

After a successful human last mile: GitHub Latest becomes `v2.0.5`, ad4090 can move `ready` → `released`, and a fresh clone of Latest matches `VERSION=2.0.5`.
