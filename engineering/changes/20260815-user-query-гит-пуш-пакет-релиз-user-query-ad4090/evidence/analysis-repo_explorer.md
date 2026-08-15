# Analysis — repo_explorer

Change: `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090`  
Route: `ad4090c51ca6` · write owner: none · intent: release

Read-only. No `git status`/`git show` shell. Facts from local refs, working tree, and public GitHub API.

## 1. HEAD vs origin/main, tag v2.0.4, VERSION 2.0.5

| Ref | Value |
| --- | --- |
| Branch | `main` (`.git/HEAD`) |
| Local `refs/heads/main` | `33a02f1128ab0a865bfb1c853248f997dcf9e39b` |
| `refs/remotes/origin/main` | same `33a02f1` |
| GitHub `commits/main` | same `33a02f1` — `Release v2.0.4: track zip and checksum` |
| Parent of HEAD | `097f5c9a112430f5250920bdbf96fb1b0fdc2f1c` — `v2.0.4: complete public product loop` |
| Local tag `v2.0.4` | annotated object `10c522f294bc5ffbdbef32d1487af59ff4e8453b` |
| Tag target | commit `33a02f1` (GitHub tag API; tagger 2026-08-15T01:27:21Z) |
| Working `VERSION` | `2.0.5` (`VERSION:1`) |
| Committed / origin `VERSION` | `2.0.4` (raw `main`) |
| Working README H1 | `v2.0.5` (`README.md:1`) |
| Origin README H1 | `v2.0.4` |
| Tag `v2.0.5` | absent locally (tags stop at `v2.0.4`) and on GitHub (release 404) |
| `packages/` / `dist/` 2.0.5 zip | absent |

HEAD is **not ahead** of origin. 2.0.5 exists only as uncommitted working-tree edits on top of tagged 2.0.4.

## 2. Uncommitted: ship vs keep out

No local 2.0.5 commit. Origin `engineering/changes` at `33a02f1` stops at `aea9d4` / `bb6ab3` / `99b743` / `14464b` / `19fc56`. Missing on origin (present locally):

**In the 2.0.5 product tree (commit these):**

- Version/docs: `VERSION`, `CHANGELOG.md` 2.0.5 (`CHANGELOG.md:3-12`), `README.md`, `QUICKSTART.md`
- Hook shims (absent on origin root 404): `session_start.py`, `user_prompt_submit.py`, `pre_tool_use.py`, `post_tool_use.py`, `pre_compact.py`, `subagent_start.py`, `subagent_stop.py`, `stop_gate.py`, `session_end.py` — same digest in working `MANIFEST.sha256` 415–451
- Installer list of those shims: `scripts/install_into.py:25-33`
- `.grok/hooks/adaptive.json` `||` fail-open (`adaptive.json:5-63`)
- `.grok-stack/config/toolchain.json` (not in origin `.grok-stack/config/`)
- Live `.grok-stack/config/routing.json` (origin file is docs-only, no floors/cap)
- Matching `router.py` / `policy.py` / `toolchain.py` / `doctor.py` / tests / skill copies
- Change packages: `8abd64`, `e1d4a6`, `3ac76c`, `661035`, `e584b3` (2.0.4 publish record), `ad4090`
- After human package step: `packages/adaptive-grok-build-pro-v2.0.5.zip*` + `packages/README.md` row (same as `33a02f1` did for 2.0.4)

**Must stay out of git and out of the zip:**

| Path | Why |
| --- | --- |
| `.env`, `.env.*` | `.gitignore:6-8`; packager `_is_secret_path` (`manifest.py:13-16,25-26`). Not in working `MANIFEST.sha256`. Do not read. |
| `.grok-stack/runtime/*` except `.gitkeep` | `.gitignore:2-3`; `manifest.py:27-28`. Runtime has `active-route.json`, receipts, approvals. |
| `err.log` | **Not gitignored.** **Not in `EXCLUDED_FILES`/`EXCLUDED_PARTS`.** Working `MANIFEST.sha256:399` already lists it. `package_stack.py` now would put it in the zip. Brief/requirements forbid it (`brief.md:5`, `requirements.md:5`). Move/delete or add an exclude **before** packaging. |
| `dist/` | `.gitignore:24`; scratch only |
| `__pycache__/`, `.pyc` | excluded (`manifest.py:7,29`) |
| private keys `*.pem` `*.key` `*.p12` `*.pfx` | gitignore + packager |

`MANIFEST.sha256` is generated at package time (`package_stack.py:20`, `manifest.py:43-47`) and was **not** on origin `33a02f1` root. Do not treat the current dirty copy as a ship artifact until `err.log` is excluded and the file is regenerated.

## 3. `package_stack.py` / `packages/` / `dist/` / `MANIFEST.sha256`

```
python3 scripts/package_stack.py
  → generate_manifest(root) writes root MANIFEST.sha256 from included_files
  → zip included_files + MANIFEST.sha256
  → default output dist/adaptive-grok-build-pro-v$(VERSION).zip   # now v2.0.5
  → sibling .sha256
```

Citations: `package_stack.py:19-38`, `manifest.py:19-47`, `Makefile:8-9`.

- Zip prefix `adaptive-grok-build-pro/` (`package_stack.py:26`).
- Zip timestamps frozen `(2026, 8, 14, 0, 0, 0)` (`package_stack.py:16`).
- `dist/` is gitignored scratch (`packages/README.md:3`, `.gitignore:24`).
- Tracked published copies live in `packages/` with sibling `.sha256` (`packages/README.md:1-17`). Copy is **manual**: `cp dist/…-v$(VERSION).zip* packages/` (`deploy.py:29`, runbook `publish-v2.0.4.md:19`).
- Current tracked latest: `packages/adaptive-grok-build-pro-v2.0.4.zip` digest `e76cd399c81c2f56aa7f12d70789658159d55a88079b7644f84807f3aab3304a` (matches GitHub asset + `dist/` copy).
- `.zip` / `.sha256` members are not re-included in a later zip (`manifest.py:29`).

## 4. `RELEASE-NOTES.md` is not generated

Nothing writes `dist/RELEASE-NOTES.md`. `package_stack.py` only writes the zip + `.sha256`. `prepare_deploy` only **prints** `--notes-file dist/RELEASE-NOTES.md` (`deploy.py:24-34`, asserted `tests/test_deploy.py:108`).

Working `dist/RELEASE-NOTES.md:1-24` is still **v2.0.4** and matches the live GitHub release body. `dist/` is gitignored, so notes must be **rewritten in `dist/`** before `gh release create`. ad4090 says notes come from `CHANGELOG` 2.0.5 (`release.md:6`, `requirements.md:8`), not the leftover 2.0.4 file.

## 5. How v2.0.4 was published

Sequence (human-owned; agents must not run push/tag/`gh release` — `publish-v2.0.4.md:1-3,40-42`):

1. `097f5c9` — product (`git log` reflog line 9; GitHub commit message lists policy, rematch, deploy, CI, MIT docs).
2. `python3 scripts/package_stack.py` then `cp dist/…-v2.0.4.zip* packages/` (`publish-v2.0.4.md:18-19`).
3. `33a02f1` — add zip + sha256 + `packages/README.md` rows for 2.0.3/2.0.4 (GitHub commit files).
4. `git tag -a v2.0.4` on **`33a02f1`** (annotated object `10c522f`, message `Adaptive Grok Build Pro v2.0.4`).
5. `git push origin main` (`097f5c9` then `33a02f1`) and `git push origin v2.0.4` (`e584b3/evidence/human-approval.md:7-8`).
6. `gh release create v2.0.4 packages/…zip packages/…sha256 --notes-file dist/RELEASE-NOTES.md` (`publish-v2.0.4.md:23`, `deploy.py:33`).

Live release: https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.4  
id `370918434`, published 2026-08-15T01:27:26Z, assets zip + sha256 only (no source tar attached as extra assets; GitHub still offers tag tarball). e584b3 `state.json` is `released` (`state.json:52-57`).

Same printed command set will target **2.0.5** once `VERSION` is 2.0.5 (`deploy.py:13-17,26-33`). Change is still `draft` (`ad4090/state.json:14`); `prepare_deploy` requires status `ready`/`released` plus evidence (`deploy.py:10,55-63`). Route human gates: `scope_and_design_approval`, `production_action_approval`.

## 6. Remote

`.git/config:9-10`: `origin` = `https://github.com/Dimkox/adaptive-grok-build-pro.git`  
`branch.main.merge` = `refs/heads/main`. Public API confirms the same repo and `main` @ `33a02f1`.
