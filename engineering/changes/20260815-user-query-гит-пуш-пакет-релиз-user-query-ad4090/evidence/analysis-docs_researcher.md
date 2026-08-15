# Docs research — 2.0.5 consistency

Route: `ad4090c51ca6`. Change: `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090`.
Compared: `VERSION`, `CHANGELOG.md` §2.0.5, `README.md`, `QUICKSTART.md`, `packages/README.md`, `engineering/runbooks/publish-v2.0.4.md`.
Also checked (same question): `dist/RELEASE-NOTES.md`, `dist/` and `packages/` artifact lists, this change package, `.grok/hooks/README.md`, `scripts/grok_deploy.py` / `.grok-stack/adaptive_grok/deploy.py`, `engineering/adr/` (empty), `engineering/contracts/` (empty of APIs).

No APIs invented. No `.env` read.

## Is 2.0.5 documented consistently?

**No. Version identity is aligned in three places; publish/package docs are still 2.0.4.**

| Source | States current version | Matches `VERSION` |
| --- | --- | --- |
| `VERSION` | `2.0.5` | source of truth |
| `CHANGELOG.md` | latest heading `## 2.0.5 — 2026-08-15` | yes |
| `README.md` H1 | `Adaptive Grok Build Pro v2.0.5` | yes |
| `QUICKSTART.md` | no version string | n/a (version-silent) |
| `packages/README.md` table | last row `2.0.4` | no |
| `engineering/runbooks/publish-v2.0.4.md` | entire runbook is `v2.0.4` | no |
| `dist/RELEASE-NOTES.md` | `# Adaptive Grok Build Pro v2.0.4` | no |
| `packages/` files | zip+sha256 through `v2.0.4` only | no 2.0.5 artifact |
| `dist/` files | zip through `v2.0.4` only; no `v2.0.5` zip | no 2.0.5 artifact |
| `engineering/runbooks/` | only `publish-v2.0.4.md` | no `publish-v2.0.5.md` |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.0"` | no |

README does **not** still say 2.0.4. The leftover 2.0.4 identity is in `packages/README.md`, the only runbook, and `dist/RELEASE-NOTES.md`.

This change package already names 2.0.5 (`brief.md`, `release.md`, `requirements.md`, `rollback.md`). `release.md` says GitHub notes come from CHANGELOG 2.0.5. `requirements.md` still unchecked for zip, tag, push, and GitHub Release.

`grok_deploy.py` reads `VERSION` and would print `v2.0.5` tag/push/`gh release create` commands, but the notes file it names is still `dist/RELEASE-NOTES.md` (currently 2.0.4 text). Using those printed commands as-is would attach 2.0.4 notes to a 2.0.5 release.

### Feature coverage (CHANGELOG 2.0.5 vs README / QUICKSTART)

CHANGELOG 2.0.5 bullets (verbatim topics):

1. After `git pull`, missing or cwd-relative hook scripts no longer lock Grok.
2. Root hook files are thin dispatchers into `.grok/hooks/` (no root `_lib.py`).
3. `adaptive.json` commands try `.grok/hooks/…` then the cwd shim, then print `{}` / allow.
4. Installer copies those shims so older `python3 pre_tool_use.py` configs keep working.
5. Toolchain pins (built / minimum / fallback) in `.grok-stack/config/toolchain.json`; doctor offers install.
6. `install_into.py` pulls missing required toolchain tools by default (`--no-deps` / `--all-deps`).
7. `routing.json` is live: analysis floor `repo_explorer` / `task_analyst` / `architect` / `docs_researcher` on non-micro work; `max_parallel_analysis` (default 10) is a ceiling; still exactly one write owner.

README v2.0.5 documents (5) and (6): toolchain table, `toolchain.json`, `grok_doctor.py --offer-install`, `install_into.py` with `--no-deps` / `--all-deps`.

README does **not** document (1)–(4) or (7). Hooks section says adapters live in `.grok/hooks/` and are registered in `.grok/hooks.json` + `.grok/hooks/adaptive.json`. It does not say root shims exist, that `_lib.py` must not be at repo root, or that `routing.json` is loaded.

QUICKSTART documents doctor `--offer-install` and `install_into.py` with `--no-deps` only. It does not mention `--all-deps`, root shims, or `routing.json`.

`.grok/hooks/README.md` describes the 2.0.5 shim/`git pull` behavior but still titles the mode “Soft mode (default since v2.0.4)”.

2.0.4 CHANGELOG items (fail-open PreToolUse/Stop, invocation policy, rematch, `grok_deploy.py`, MIT line) remain in README. That is leftover-from-previous-release documentation, not a 2.0.5 contradiction.

No ADR files under `engineering/adr/`. No OpenAPI/AsyncAPI/JSON contracts for this product surface.

## What release notes should go on GitHub?

Source of truth in-repo: `CHANGELOG.md` §2.0.5 (this change `release.md` / `requirements.md` say so). Do **not** reuse `dist/RELEASE-NOTES.md` as it stands (it is the 2.0.4 notes).

Suggested GitHub body (facts already written in CHANGELOG + consumer upgrade from `engineering/changes/20260815-fail-open-hooks-after-git-pull-on-any-project-8abd64/release.md`):

```text
Adaptive Grok Build Pro v2.0.5 — 2026-08-15

After `git pull` on a consumer project, missing or cwd-relative hook scripts no longer lock Grok.

- Root hook files are thin dispatchers into `.grok/hooks/` (no root `_lib.py`)
- `adaptive.json` commands try `.grok/hooks/…` then the cwd shim, then print `{}` / allow
- Installer copies those shims so older `python3 pre_tool_use.py` configs keep working
- Toolchain pins (built / minimum / fallback) in `.grok-stack/config/toolchain.json`; doctor offers install of the fallback or a newer version
- `install_into.py` pulls missing required toolchain tools by default (`--no-deps` to skip, `--all-deps` for optional PHP/Node/gh)
- `routing.json` is live: analysis floor is `repo_explorer` / `task_analyst` / `architect` / `docs_researcher` on non-micro work; `max_parallel_analysis` (default 10) is a ceiling, not a quota; still exactly one write owner

Upgrade existing installs: `python3 scripts/install_into.py . --force` from this package, or copy the nine root shim files.

Assets (after package step):
- `adaptive-grok-build-pro-v2.0.5.zip`
- `adaptive-grok-build-pro-v2.0.5.zip.sha256`
```

`deploy.py` and the 2.0.4 runbook attach **zip + sha256 only**. CHANGELOG 2.0.2 mentioned a source tar.gz on that older GitHub Release; later 2.0.4 publish (`engineering/changes/20260815-publish-v2-0-4-github-release-e584b3/evidence/human-approval.md`) used the zip+sha256 pattern. This change package also specifies zip + sha256, not tar.gz.

Do not paste 2.0.4 bullets (fail-open Stop, `grok_deploy.py`, MIT positioning, `прод` word match) into the 2.0.5 GitHub notes. Those are already on `v2.0.4`.

## Gaps

- **README is not still saying 2.0.4.** H1 is `v2.0.5`.
- **`packages/README.md` table is missing 2.0.5.** Last listed file is `adaptive-grok-build-pro-v2.0.4.zip`. Rebuild snippet uses `VERSION`, so it would copy a 2.0.5 zip *if one existed*.
- **No 2.0.5 zip or checksum** under `packages/` or `dist/`.
- **No `engineering/runbooks/publish-v2.0.5.md`.** Only `publish-v2.0.4.md` exists. That file still says tag `v2.0.4`, copy `v2.0.4.zip*`, `gh release create v2.0.4`, and “Do not copy a 2.0.4 zip into `packages/` until this human publish step” (that zip is already in `packages/`).
- **`dist/RELEASE-NOTES.md` is still the 2.0.4 notes.** `grok_deploy.py` and the 2.0.4 runbook both pass `--notes-file dist/RELEASE-NOTES.md`. Publishing without rewriting that file would ship the wrong notes.
- **QUICKSTART has no version** and omits `--all-deps`, root shims, and `routing.json`.
- **README omits** the git-pull shim contract and the live `routing.json` floor/cap. Those are the other half of the 2.0.5 changelog.
- **`.grok/hooks/README.md`** documents the shim/`git pull` fix but still labels the mode as “since v2.0.4”.
- **Runtime `__version__`** in `.grok-stack/adaptive_grok/__init__.py` is still `"2.0.0"`.
- **This change package `requirements.md`** still has unchecked boxes for the 2.0.5 zip, tag, push, and GitHub Release.

Historical (not a 2.0.5 doc bug, but do not copy blindly): `dist/HANDOFF.md` is the 2.0.1 handoff.
