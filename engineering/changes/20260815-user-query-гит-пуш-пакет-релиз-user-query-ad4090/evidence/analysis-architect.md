# Analysis — architect

Change: `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090`  
Active route (this continue): `e85418e33648` · intent=`feature` · write=`general_implementer` · reviews=`code_reviewer`+`test_reviewer`  
Durable change route: `ad4090c51ca6` · intent=`release` · write=`null` · reviews=`security_reviewer`+`release_reviewer` · status=`verifying`  
HEAD / origin/main: `33a02f1` (tag `v2.0.4`). Working `VERSION` is `2.0.5`. Tag `v2.0.5` absent.

Read-only design. No implementation. No `.env` read. No push / tag / `gh release`.

Synthesized from `architecture.md`, `rollback.md`, `brief.md`, `requirements.md`, `release.md`, `tasks.md`, `test-plan.md`, `evidence/human-approval.md`, `evidence/analysis-repo_explorer.md` + `-continue.md`, `evidence/analysis-docs_researcher.md` + `-continue.md`, `evidence/analysis-task_analyst.md`, `scripts/grok_deploy.py`, `.grok-stack/adaptive_grok/deploy.py`, `manifest.py`, `scripts/package_stack.py`, both publish runbooks, `policy.py`, `receipts.py`, `util.py` `tree_fingerprint`, and `engineering/decisions.md`.

## Ruling

**One write owner. One review set. Humans own tag / push / GitHub Release.**

1. Stay on active route `e85418e33648`. Do not rematch. Do not spawn `security_reviewer` or `release_reviewer`.
2. Write owner is `general_implementer` for leftover publish-prep only. No second writer. No new services.
3. Agent gate set is **verification + code_review + test_review** (current route `required_evidence`). That is also what `grok_deploy.py` will check, because it validates the **active** route, not `ad4090/route.json`.
4. Release substance that the old high-risk route wanted is not dropped: it is folded into this design, the code/test review checklists, and the human last mile. It is not a second receipt set.
5. Agents do not run `git tag`, `git push`, or `gh release create`. Last mile is `python3 scripts/grok_deploy.py` (print / optional `--record`). Humans execute the printed commands.
6. Do not create a second change package for «продолжай».

This collapses the two *evidence* lists. It does not rewrite history: leave `ad4090/route.json` as the original high-risk classification. Record this ruling here. When the implementer syncs `tasks.md`, replace “Verify + security/release review” with the e85418 set.

### Why not keep both review lists

Task-analyst’s split is factually correct (two routes exist because «продолжай» rematched across sessions and defaulted to `feature`). Keeping both is a deadlock:

- This session cannot spawn the old reviewers (`policy.py` spawn allow-list).
- `prepare_deploy` only looks at the active route’s receipts.
- Completing e85418 while still demanding ad4090 security+release means `grok_deploy.py` can succeed and the change package can never say “release evidence done,” or the reverse.

User asked for one coherent set. Active route is the dispatch and Stop authority (`AGENTS.md`, adaptive-delivery). Remaining writes are packaging hygiene on an already-implemented 2.0.5 tree (prior product changes `8abd64` / `e1d4a6` / `3ac76c` / `661035` already had code+test). Production side effects stay gated by invocation policy + a fresh `grok_approve.py production` + a human shell.

Do not rematch to resurrect security+release: rematch drops `general_implementer` and reopens a write-owner=none release route before the notes/zip exist.

## Current tree vs original pre-package list

| Item | Needed? | Now |
| --- | --- | --- |
| `err.log` out of git and zip | Yes before `package_stack.py` | **Already in the working tree.** `.gitignore:15`, `manifest.py:9` `EXCLUDED_FILES`, `test_archive_excludes_err_log`, not in `MANIFEST.sha256`. Origin `main` has none of that. Commit these files. Do not delete on-disk `err.log`. |
| `packages/README.md` 2.0.5 row | With the zip, not before | **Row exists.** Zip still missing. Commit row + zip + sha256 together. |
| `dist/RELEASE-NOTES.md` | Yes before `gh release create` | **Still v2.0.4.** Scratch file; `dist/` is gitignored. Rewrite from CHANGELOG 2.0.5. |
| `publish-v2.0.5.md` | Docs, not a zip blocker | **Exists** (untracked). Keep. Add the 2.0.4 “agents must not run tag/push/gh” sentence. |
| `__version__ = "2.0.0"` | No | Leftover. `VERSION` is the contract. Out of scope. |
| README/QUICKSTART feature gaps | No | Out of scope (`brief.md`: no new product features). |

## 1. Pre-package — smallest coherent write

Owner: `general_implementer` only.

Transition first: `verifying` → `implementing` (allowed). Then do the writes. Do not stay in `verifying` while editing.

### Do

1. Keep the already-landed `err.log` exclude (gitignore + `EXCLUDED_FILES` + existing test). Do not invent a second exclude mechanism. Do not add `err.log` to `EXCLUDED_PARTS`.
2. Rewrite **only** `dist/RELEASE-NOTES.md` to CHANGELOG 2.0.5. Docs-researcher continue already pinned the body: copy `CHANGELOG.md:3-12` verbatim. Do **not** keep the 2.0.4 wrapper (MIT one-liner, `## Changes` / `## Assets` / `## Install`). Do **not** add the consumer-upgrade sentence that is not in CHANGELOG 2.0.5. Do not change `deploy.py` notes path (`tests/test_deploy.py:108` pins `--notes-file dist/RELEASE-NOTES.md`).
3. Optionally add one sentence to `engineering/runbooks/publish-v2.0.5.md`: agents must not run `git push`, `git tag`, or `gh release`; humans own those commands. Do not rewrite the command list (it must stay the `deploy.py` printout).
4. Sync this change package (`tasks.md` review line, `architecture.md` write-owner/gate set, checkboxes after work lands). That is package hygiene, not product.

### Do not

- Bump `__version__`, expand README/QUICKSTART, retitle `.grok/hooks/README.md`, add tar.gz, add services, edit Bitrix core, read `.env`.
- Run `package_stack.py` until the exclude + notes rewrite are on disk (notes are not inside the zip; exclude is).
- `git add -A`.
- Tag, push, or `gh release create`.

## 2. Verification + reviews (one gate set)

**Recorded set (this session and `grok_deploy.py`): `verification`, `code_review`, `test_review`.**

| Check | Who | Pass means |
| --- | --- | --- |
| `python3 scripts/grok_verify.py --mode pr` | controller after last intended file write | unittest + repo checks green on the tree that will be tagged (includes zip in `packages/` and the err.log exclude) |
| `code_reviewer` | after that tree exists | Diff vs `33a02f1` matches this design; no `.env` / `err.log` / runtime in the commit set or zip; `deploy.py` still prepare-only; no new production executor |
| `test_reviewer` | same tree | `test_archive_excludes_err_log` present; verify actually ran; zip sha256 sibling matches; in-zip `MANIFEST.sha256` lists neither `.env` nor `err.log` |

Folded release/security checklist (reviewers assert; no extra agents):

- Notes file on disk is CHANGELOG 2.0.5, not 2.0.4.
- Artifacts are zip + sha256 only.
- Tag will land on the publish commit, not on `33a02f1`.
- Rollback commands in `rollback.md` still delete only `v2.0.5`.
- No secret values in added files or command logs.

Fingerprint rule (`util.py` `tree_fingerprint` = `HEAD` + non-runtime dirty/untracked files; `engineering/decisions.md` / `mistakes.md`):

- Any later working-tree edit or another commit invalidates receipts.
- Official verify + `grok_review.py` happen **after** package/copy and **after** review reports are written, and **before** any further file edit.
- If the publish commit happens *after* receipts, `HEAD` changes and receipts go stale. Then `grok_deploy.py` fails. Therefore: **commit the include list first, then write review reports if they were not already on disk, then re-verify, then record receipts, then `grok_deploy.py`, then human tag/push/gh.** Tag does not change `HEAD`.

Practical order that keeps one receipt wave:

1. Implementer finishes prep + package + copy + change-package doc sync.
2. `git add` include list + **one** commit (user authorized the commit; policy does not treat `git commit` as production).
3. Reviewers inspect that commit (or the identical working tree) and write `evidence/code-review.md` + `evidence/test-review.md`.
4. Transition `implementing` → `verifying` → `reviewing` → `ready` (last state.json write).
5. `python3 scripts/grok_verify.py --mode pr`
6. `python3 scripts/grok_review.py code_review --status pass --report …/evidence/code-review.md` and the same for `test_review`.
7. `python3 scripts/grok_status.py` — `evidence_gaps` empty. `prepare_deploy` can run.

If step 3/4 happens after step 5, drop the old receipts and repeat 5–6. Do not record reviews against a failing verify.

`grok_deploy.py` will not print until status is `ready`/`released` **and** the active-route gaps are empty. Today both receipt dirs are empty and status is `verifying`.

## 3. Package → copy → commit

### Package (implementer; not production)

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.5.zip dist/adaptive-grok-build-pro-v2.0.5.zip.sha256 packages/
```

`package_stack.py` writes root `MANIFEST.sha256`, then `dist/adaptive-grok-build-pro-v2.0.5.zip` + sibling sha256. It does **not** write notes. Copy is manual (`deploy.py:29`). Zip prefix `adaptive-grok-build-pro/`; timestamps frozen `(2026, 8, 14, 0, 0, 0)`.

Post-copy checks (test-plan):

- `sha256sum -c packages/adaptive-grok-build-pro-v2.0.5.zip.sha256` from `packages/`
- In-zip `adaptive-grok-build-pro/MANIFEST.sha256` has no `.env` and no `err.log`
- Zip names include the nine root shims and `VERSION` `2.0.5`

### Commit include list

One publish commit on `main` (do not split product vs zip unless the implementer wants a 2.0.4-style second commit; the tag must be on the commit that contains the zip). Use pathspecs, not `-A`.

**Must add (product + publish record; all currently uncommitted vs `33a02f1`):**

- Identity: `VERSION`, `CHANGELOG.md`, `README.md`, dirty `QUICKSTART.md` if any
- Hygiene: `.gitignore` (`err.log` block), `.grok-stack/adaptive_grok/manifest.py`
- Nine root shims + `.grok-stack/templates/hook_root_shim.py`
- `scripts/install_into.py` (shim list)
- `.grok/hooks/adaptive.json`
- `.grok-stack/config/toolchain.json` (absent on origin)
- `.grok-stack/config/routing.json` (origin docs-only)
- Matching stack already edited for 2.0.5: `router.py`, `policy.py`, `toolchain.py`, `doctor.py`, installer, skill mirrors if dirty
- Tests: at least `test_hooks.py`, `test_structure.py`, `test_manifest_package.py`, `test_installer.py`, `tests/test_toolchain.py`
- `packages/README.md` + `packages/adaptive-grok-build-pro-v2.0.5.zip` + `.sha256`
- `engineering/runbooks/publish-v2.0.5.md`
- Change packages missing on origin: `8abd64`, `e1d4a6`, `3ac76c`, `661035`, `e584b3`, `ad4090`

Implementer confirms the exact dirty set with `git status` / `git diff --name-only` (read-only) and maps it onto this list. If a 2.0.5 product file is dirty and not listed, add it; do not add anything from the exclude list.

**Must not add:**

| Path | Why |
| --- | --- |
| `.env`, `.env.*` | gitignore + packager secret path. Do not read. |
| `err.log` | gitignore + `EXCLUDED_FILES` |
| `.grok-stack/runtime/**` except `.gitkeep` | gitignore + packager |
| `dist/**` including `RELEASE-NOTES.md` and the scratch 2.0.5 zip | gitignore; scratch |
| `MANIFEST.sha256` | generated; not on origin; zip already embeds a copy. Leave untracked. |
| `__pycache__/`, `*.pyc`, keys | excluded |

Suggested commit message: `Release v2.0.5: hook shims, toolchain pins, track zip and checksum`.

`git commit` may set identity from already-configured `user.name` / `user.email`. Do not `cat .env`. Do not put `GIT_FINE_GRAIN_TOKEN` on a command line.

## 4. Tag / push / gh — who executes

| Action | Who | Why |
| --- | --- | --- |
| Remaining file writes, `package_stack.py`, `cp` into `packages/` | `general_implementer` | Not a production invocation |
| `git add` include list + `git commit` | `general_implementer` (authorized) or human | Not in `PRODUCTION_INVOCATIONS` |
| `python3 scripts/grok_deploy.py` | controller / implementer | Prepare-only; prints; no subprocess |
| `python3 scripts/grok_deploy.py --record` | optional, after `ready` + current evidence | Writes receipt `deploy`/`prepared`. Requires **live** `has_valid_approval(..., 'production')`. Does **not** publish. |
| `git tag -a v2.0.5` | **human** | 2.0.4 runbook + adaptive-delivery last mile. Policy does not block `git tag`; we still do not run it. |
| `git push origin main` | **human** | `policy.py` production invocation |
| `git push origin v2.0.5` | **human** | same |
| `gh release create v2.0.5 … --notes-file dist/RELEASE-NOTES.md` | **human** | same (`gh release create`) |

`scripts/grok_deploy.py` never executes those four publish commands (`tests/test_deploy.py:184-191`). `--record` is not a substitute for running them.

Printed command set (`deploy.py:24-34`, `publish-v2.0.5.md`):

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.5.zip* packages/
git tag -a v2.0.5 -m "v2.0.5"
git push origin main
git push origin v2.0.5
gh release create v2.0.5 packages/adaptive-grok-build-pro-v2.0.5.zip packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 --notes-file dist/RELEASE-NOTES.md
```

After this session has already packaged and copied, the human may skip the first two lines or re-run them (zip is deterministic). They must **not** skip the notes rewrite. Tag must point at the new publish commit, not `33a02f1`.

### Credentials

- Names only: `GIT_FINE_GRAIN_TOKEN`, `GIT_LOGIN`, `GIT_EMAIL` (from `architecture.md`). Values live in `.env`.
- Do not read, echo, or interpolate those values into chat, receipts, or process logs.
- Agent file-read of `.env` is blocked (`policy.json` `secret_read_paths`).
- Human sources `.env` in **their** shell if git/gh are not already authenticated. Prefer an already-logged-in `gh` / credential helper over pasting a token into argv.
- Markdown `evidence/human-approval.md` is not a live approval. Machine approval `3fba57f3d0cb` expires `2026-08-15T02:53:45+00:00` and is **stale for `--record` and for any agent-side push**. Human running git/gh **outside** the hook does not need `grok_approve`. If an agent needs `--record` later: `python3 scripts/grok_approve.py production --reason "publish v2.0.5"` immediately before it. Default TTL is 15 minutes.

## 5. Residual risk and rollback

Rollback stays as already sketched (`rollback.md`, `publish-v2.0.5.md`). Do not touch `v2.0.4`. No force-push.

```bash
gh release delete v2.0.5 --yes
git push origin :refs/tags/v2.0.5
git tag -d v2.0.5
```

If `main` must come back: revert the 2.0.5 commit(s) and push (fresh production approval if an agent pushes). Remove unpublished `packages/adaptive-grok-build-pro-v2.0.5.zip*`. Restore `packages/README.md` last row to 2.0.4 if that commit is reverted.

| Risk | Mitigation |
| --- | --- |
| `gh` attaches 2.0.4 notes | Rewrite `dist/RELEASE-NOTES.md` before `gh`. If it still happens: `gh release edit v2.0.5 --notes-file dist/RELEASE-NOTES.md` — do not retag. |
| `err.log` in zip | Exclude already in tree; test locks it; inspect in-zip manifest before commit. |
| `git add -A` stages secrets | Pathspec include list. `.env` is gitignored; still never add it. |
| Tag on `33a02f1` | Commit 2.0.5 first; `git rev-parse` the tag target must not be `33a02f1`. |
| Receipts stale after commit or after package | Package + commit before official verify; no file writes after receipts; then tag (tag does not move `HEAD`). |
| Dual-route confusion | This ruling: e85418 evidence only. Do not wait for ad4090 security/release receipts. |
| Expired production TTL | Human executes last mile; refresh `grok_approve` only for `--record` or an agent-side gated command. |
| Push succeeds, `gh` fails | Retry `gh release create` only. Tag/commit already on origin. |
| `gh` succeeds, zip wrong | Delete release + tag (`rollback.md`), fix tree, new commit, new tag. Do not overwrite `v2.0.5` with `git tag -f` + force-push. |
| Credential leak | Never read `.env`; never print token; do not put token in `git remote` URL in chat. |
| `__version__` / README gaps | Accepted residual. Not a 2.0.5 identity contract. |
| Re-running `package_stack.py` after commit | Rewrites untracked `MANIFEST.sha256` (in fingerprint). Only re-run if contents are identical or you will re-verify. |

## Implementer task list (vertical, in order)

1. Transition ad4090 `verifying` → `implementing`.
2. Confirm err.log exclude + test; rewrite `dist/RELEASE-NOTES.md`; optional runbook sentence; sync `tasks.md` / `architecture.md` to this gate set.
3. `python3 scripts/package_stack.py` and copy zip+sha256 into `packages/`. Confirm sha256 + in-zip manifest.
4. `git add` include list; one commit; no tag/push.
5. Reviewers write reports; transition → `ready`; `grok_verify.py --mode pr`; record `code_review` + `test_review`.
6. `python3 scripts/grok_deploy.py` (and `--record` only with a live production approval). Stop.
7. Human: tag `v2.0.5`, `git push origin main`, `git push origin v2.0.5`, `gh release create` with the rewritten notes file.

**Go / no-go:** no-go on publish until steps 2–6 are done. This report is step 0 of the continue analysis wave, not authorization to execute the last mile.
