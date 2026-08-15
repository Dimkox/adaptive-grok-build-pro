# Analysis — repo_explorer (continue)

Change: `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090` (status `verifying`, `state.json:37-38`).
Active route now: `e85418e33648` (`продолжай`). Original publish route: `ad4090c51ca6`.
HEAD / `origin/main` still `33a02f1128ab0a865bfb1c853248f997dcf9e39b`. Tag `v2.0.5` absent locally (tags stop at `v2.0.4`) and on GitHub (release 404). Origin `VERSION` is `2.0.4`; working `VERSION` is `2.0.5`.

Read-only. No `git status` / `git show`. Compared working tree to previous `evidence/analysis-repo_explorer.md` and public GitHub `main`.

## Deltas vs previous analysis

| Prior fact | Now |
| --- | --- |
| `err.log` not gitignored, not in `EXCLUDED_*`, listed in `MANIFEST.sha256:399` | **Updated.** Ignored + excluded + not in manifest. |
| `packages/README.md` last row 2.0.4 | **Updated.** Last row is 2.0.5; zip still missing. |
| No `publish-v2.0.5.md` (docs_researcher) | **Updated.** Runbook exists. |
| Change `draft` | **Updated.** `verifying`. |
| No 2.0.5 zip; `package_stack` does not write notes; deploy prints only; shims are dispatchers; `MANIFEST.sha256` not gitignored | **Confirmed.** |

---

## 1. `err.log`

- **Exists** at repo root (`err.log`; listed by workspace root).
- **Not** listed in working `MANIFEST.sha256` (repo-wide grep of that file: no `err.log`).
- **Excluded from the zip:** `EXCLUDED_FILES = {'MANIFEST.sha256', '.coverage', '.env', 'err.log'}` (`.grok-stack/adaptive_grok/manifest.py:9`). `included_files` skips any `path.name in EXCLUDED_FILES` (`manifest.py:22`).
- **Not** in `EXCLUDED_PARTS` (`manifest.py:6-8`) — not needed; filename exclude is enough.
- **Gitignored locally:** `.gitignore:14-15` (`# Local crash / hook dumps` / `err.log`).
- Origin `.gitignore` (raw `main`) has **no** `err.log` lines. Origin `manifest.py` `EXCLUDED_FILES` is only `{'MANIFEST.sha256', '.coverage', '.env'}`. Origin root listing has no `err.log`.

Test already locks the packager: `tests/test_manifest_package.py:98-109` (`test_archive_excludes_err_log`).

**Smallest change to keep it out of git and out of the zip — already in the working tree:**

1. Keep `.gitignore:15` (`err.log`) — stops `git add`.
2. Keep `manifest.py:9` (`'err.log'` in `EXCLUDED_FILES`) — stops zip + future `generate_manifest`.

Do **not** delete the on-disk file. Do **not** `git add err.log`. No `git rm --cached` — origin never tracked it. Regenerating `MANIFEST.sha256` is optional now (stale listing already gone).

---

## 2. `packages/README.md` and 2.0.5 zip

Working last rows (`packages/README.md:6-12`):

| File | Version |
| --- | --- |
| `…-v2.0.3.zip` | 2.0.3 |
| `…-v2.0.4.zip` | 2.0.4 |
| `…-v2.0.5.zip` | 2.0.5 |

Origin `packages/README.md` still ends at 2.0.4.

**No v2.0.5 zip under `packages/` or `dist/`.** Present artifacts stop at `adaptive-grok-build-pro-v2.0.4.zip` (+ `.sha256`; `dist/` also has 2.0.2/2.0.3 tarballs). Table row is ahead of the files.

---

## 3. `scripts/package_stack.py` writes

`write_archive` (`package_stack.py:19-33`):

1. `generate_manifest(root)` → root `MANIFEST.sha256` (`manifest.py:43-47`).
2. Zip `included_files` + that `MANIFEST.sha256`.
3. Prefix `adaptive-grok-build-pro/`; timestamps frozen `(2026, 8, 14, 0, 0, 0)` (`package_stack.py:16,26`).
4. Sibling `{zip}.sha256` next to the zip (`package_stack.py:31-32`).

Default path: `dist/adaptive-grok-build-pro-v$(VERSION).zip` → now `dist/adaptive-grok-build-pro-v2.0.5.zip` (`package_stack.py:36-38`, `Makefile:8-9`).

**Does not write `dist/RELEASE-NOTES.md`.** Nothing in `package_stack.py` / `manifest.py` touches it. `prepare_deploy` only **prints** `--notes-file dist/RELEASE-NOTES.md` (`deploy.py:33`). Working `dist/RELEASE-NOTES.md:1` is still `# Adaptive Grok Build Pro v2.0.4`. Rewrite that scratch file from `CHANGELOG.md:3-12` before `gh release create` (`release.md:6`, `requirements.md:8`).

Copy into git is **manual**: `cp dist/…-v$(VERSION).zip* packages/` (`deploy.py:29`, `publish-v2.0.5.md:8-9`).

---

## 4. `grok_deploy.py` / `deploy.py`

CLI (`scripts/grok_deploy.py:15-19`): “Never executes tag, push, or release.” `--record` only writes a receipt. `--json` dumps the report.

`prepare_deploy` (`deploy.py:51-88`) requires, in order:

1. Active route (`deploy.py:52-54`).
2. `validate_evidence` empty (`deploy.py:55-57`) — every `route['required_evidence']` receipt must exist, `status=pass`, fingerprint current (`receipts.py:40-52`).
3. Active change (`deploy.py:58-60`).
4. Change `status` in `{'ready', 'released'}` (`deploy.py:10,61-63`).

Current blockers: change is `verifying` (`state.json:37-38`); active route is `e85418e33648` (required: `verification`, `code_review`, `test_review`) not `ad4090c51ca6`.

`--record` extra: `has_valid_approval(root, 'production')` (`deploy.py:74-75`, `state.py:167-187`) then `write_receipt(..., 'deploy', 'prepared')` (`deploy.py:76-81`). Dry-run (`record=False`) does **not** need production approval (`deploy.py:66-73`).

**Prints only.** Command list (`deploy.py:24-34`): `package_stack.py`, `cp` to `packages/`, `git tag -a`, `git push origin <branch>`, `git push origin v<ver>`, `gh release create … --notes-file dist/RELEASE-NOTES.md`. No `subprocess` / `os.system` (`tests/test_deploy.py:184-191`). Humans own execution (`adaptive-delivery` close + `publish-v2.0.5.md`).

---

## 5. Nine root hook shims

All nine (`session_start.py`, `user_prompt_submit.py`, `pre_tool_use.py`, `post_tool_use.py`, `pre_compact.py`, `subagent_start.py`, `subagent_stop.py`, `stop_gate.py`, `session_end.py`) are **thin dispatchers**, not copies of `.grok/hooks/*`.

Each is byte-identical to `.grok-stack/templates/hook_root_shim.py` (same digest `0e7e9fc65eac55…` in `MANIFEST.sha256:61,427-429,444-448,463`). They `runpy` `.grok/hooks/<this-file-name>` (`hook_root_shim.py:16,20-26`); missing canonical → `{"decision":"allow"}` for `pre_tool_use.py` else `{}` (`hook_root_shim.py:27-30`). No root `_lib.py`.

Canonical hooks are real implementations (e.g. `.grok/hooks/pre_tool_use.py:1-19` imports `_lib` and runs policy).

Installer ships the shims: `scripts/install_into.py:25-33`. `adaptive.json` tries `.grok/hooks/…` then cwd shim then `{}` / allow (`adaptive.json:5-63`). Tests: `tests/test_structure.py:62-74`, `tests/test_hooks.py:20-51`. Origin root listing has **none** of the nine files.

---

## 6. `.gitignore`

| Path | Ignored? |
| --- | --- |
| `err.log` | **Yes**, local `.gitignore:15`. Origin raw `main` does **not** ignore it. |
| `MANIFEST.sha256` | **No.** Not in `.gitignore`. In `EXCLUDED_FILES` so it is not re-zipped as a member of `included_files`; `package_stack.py:21` adds it explicitly. Origin root has no `MANIFEST.sha256`. |

Also ignored: `.grok-stack/runtime/*` (keep `.gitkeep`) (`.gitignore:2-3`); `.env` / `.env.*` except `.env.example` (`:6-8`); `dist/` (`:27`); `__pycache__/` (`:23`); keys (`:9-12`).

---

## 7. Commit vs stay untracked (2.0.5)

HEAD is **not** ahead of origin. 2.0.5 is uncommitted working-tree work on tagged 2.0.4.

**Must commit (product + this publish record):**

- Version/docs: `VERSION`, `CHANGELOG.md` §2.0.5, `README.md`, `QUICKSTART.md` if dirty
- `.gitignore` (`err.log` block)
- Nine root shims + `.grok-stack/templates/hook_root_shim.py`
- `scripts/install_into.py` shim list
- `.grok/hooks/adaptive.json` `||` fail-open
- `.grok-stack/config/toolchain.json` (absent on origin)
- `.grok-stack/config/routing.json` (origin is docs-only; working has `max_parallel_analysis` + `analysis_floors`)
- Matching stack: `manifest.py` (`err.log` exclude), `router.py` / `policy.py` / `toolchain.py` / `doctor.py` / installer as already edited
- Tests: at least `test_hooks.py`, `test_structure.py`, `test_manifest_package.py`, `test_installer.py`, **new** `tests/test_toolchain.py` (not on origin)
- `packages/README.md` 2.0.5 row
- After human package step: `packages/adaptive-grok-build-pro-v2.0.5.zip` + `.sha256`
- `engineering/runbooks/publish-v2.0.5.md`
- Change packages missing on origin: `8abd64`, `e1d4a6`, `3ac76c`, `661035`, `e584b3`, `ad4090`

**Must stay untracked:**

| Path | Why |
| --- | --- |
| `err.log` | `.gitignore:15`; brief/requirements forbid (`brief.md:5`, `requirements.md:5`) |
| `.env`, `.env.*` | `.gitignore:6-8`; packager `_is_secret_path` (`manifest.py:13-16`). Do not read. |
| `.grok-stack/runtime/*` except `.gitkeep` | `.gitignore:2-3`; `manifest.py:27-28` |
| `dist/**` including leftover `dist/RELEASE-NOTES.md` and future `dist/…-v2.0.5.zip*` | `.gitignore:27`; scratch. Rewrite notes locally before `gh`. |
| `MANIFEST.sha256` | Generated at package time; not on origin; do not `git add`. Zip will contain a fresh copy. |
| `__pycache__/`, `*.pyc` | excluded |
| `*.pem` `*.key` `*.p12` `*.pfx` | gitignore + packager |

Do not treat `__init__.py` `__version__ = "2.0.0"` (`.grok-stack/adaptive_grok/__init__.py:3`) as a 2.0.5 identity file.

**Publish sequence still human-owned** (`publish-v2.0.5.md:6-14`): package → `cp` to `packages/` → commit (no `err.log` / `.env`) → tag `v2.0.5` → push `main` + tag → `gh release create` with rewritten notes.
