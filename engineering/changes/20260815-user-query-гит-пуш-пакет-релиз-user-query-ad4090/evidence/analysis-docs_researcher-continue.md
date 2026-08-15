# Docs research continue — 2.0.5 publish state

Route: `e85418e33648` (continue). Change: `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090` (package `route.json` still `ad4090c51ca6`).
Prior report: `evidence/analysis-docs_researcher.md`.
Compared now: `VERSION`, `CHANGELOG.md` §2.0.5, `README.md` H1 + hooks/install, `QUICKSTART.md`, `packages/README.md`, `dist/RELEASE-NOTES.md`, `engineering/runbooks/publish-v2.0.5.md`, `.grok-stack/adaptive_grok/__init__.py`.
Also checked: this change `brief.md` / `release.md` / `requirements.md`, `deploy.py`, `tests/test_deploy.py`, `CHANGELOG.md` §2.0.1, `engineering/changes/20260814-prepare-v2-0-1-package-for-manual-release-58e51e`, `engineering/adr/` (empty), `engineering/contracts/` (empty of APIs), `engineering/decisions.md`, `.grok/hooks/README.md`.

No APIs invented. No `.env` read.

## Delta vs previous report

| Item | Prior (`analysis-docs_researcher.md`) | Now |
| --- | --- | --- |
| `VERSION` | `2.0.5` | same (`VERSION:1`) |
| `CHANGELOG.md` §2.0.5 | heading + 6 bullets | same (`CHANGELOG.md:3-12`) |
| `README.md` H1 | `v2.0.5` | same (`README.md:1`) |
| `QUICKSTART.md` | no version; `--no-deps` only | same (`QUICKSTART.md:1-18`) |
| `packages/README.md` | last row `2.0.4` | **updated** — last row `2.0.5` (`packages/README.md:5-12`) |
| `publish-v2.0.5.md` | **did not exist** | **exists** (`engineering/runbooks/publish-v2.0.5.md`) |
| `dist/RELEASE-NOTES.md` | still 2.0.4 | **still 2.0.4** (`dist/RELEASE-NOTES.md:1-18`) |
| 2.0.5 zip in `packages/` / `dist/` | absent | **still absent** |
| `__version__` | `"2.0.0"` | same (`__init__.py:3`) |

## Current identity table

| Source | States | Matches `VERSION` `2.0.5` |
| --- | --- | --- |
| `VERSION:1` | `2.0.5` | source of truth (`CHANGELOG.md:51`) |
| `CHANGELOG.md:3` | `## 2.0.5 — 2026-08-15` | yes |
| `README.md:1` | `# Adaptive Grok Build Pro v2.0.5` | yes |
| `QUICKSTART.md:1` | `# Quickstart — Adaptive Grok Build Pro` (no version) | n/a (version-silent; same as prior releases) |
| `packages/README.md:12` | `` `adaptive-grok-build-pro-v2.0.5.zip` `` / `2.0.5` | table yes; **file not on disk** |
| `engineering/runbooks/publish-v2.0.5.md:1,10-13` | tag / zip / `gh release create v2.0.5` | yes |
| `dist/RELEASE-NOTES.md:1,17-18` | `# Adaptive Grok Build Pro v2.0.4` + 2.0.4 assets | **no** |
| `.grok-stack/adaptive_grok/__init__.py:3` | `__version__ = "2.0.0"` | no (see leftover section) |

This change still names 2.0.5 (`brief.md:1-3`, `release.md:3-6`, `requirements.md:4-8`). `requirements.md` boxes remain unchecked (zip, tag, push, GitHub Release).

## `publish-v2.0.5.md` now exists

Confirmed on disk: `engineering/runbooks/publish-v2.0.5.md` (prior report: only `publish-v2.0.4.md`). User note that git status lists it untracked is consistent with a new working-tree file; this agent did not run `git status`.

Contents (`publish-v2.0.5.md:1-22`):

- Header: `# Publish v2.0.5`
- Package + copy: `python3 scripts/package_stack.py` then `cp dist/adaptive-grok-build-pro-v2.0.5.zip* packages/`
- Tag: `git tag -a v2.0.5 -m "v2.0.5"`
- Push: `git push origin main` and `git push origin v2.0.5`
- Release: `gh release create v2.0.5 packages/adaptive-grok-build-pro-v2.0.5.zip packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 --notes-file dist/RELEASE-NOTES.md`
- Rollback: `gh release delete v2.0.5 --yes` then delete remote/local tag

Same notes-file path as `deploy.py:33` and `tests/test_deploy.py:108`. The new runbook is version-correct for tag/zip, **but still points at the leftover 2.0.4 notes file**.

`publish-v2.0.4.md` remains on disk as historical record. It is not the 2.0.5 procedure.

## Exact GitHub notes for `dist/RELEASE-NOTES.md`

Contract: this change `release.md:6` (`Notes: CHANGELOG 2.0.5`) and `requirements.md:8` (`notes from CHANGELOG 2.0.5`). Nothing generates `dist/RELEASE-NOTES.md` (`package_stack.py` writes zip+sha256 only; `deploy.py:33` only prints `--notes-file`).

**Use CHANGELOG 2.0.5 only** (`CHANGELOG.md:3-12`). Do not reuse the current `dist/RELEASE-NOTES.md` body (it is the 2.0.4 condensed notes). Do not paste 2.0.4 bullets. Do not add the consumer-upgrade sentence from `engineering/changes/20260815-fail-open-hooks-after-git-pull-on-any-project-8abd64/release.md:3` — that line is **not** in CHANGELOG 2.0.5.

Write this text (verbatim from `CHANGELOG.md:3-12`):

```text
## 2.0.5 — 2026-08-15

After `git pull` on a consumer project, missing or cwd-relative hook scripts no longer lock Grok.

- Root hook files are thin dispatchers into `.grok/hooks/` (no root `_lib.py`)
- `adaptive.json` commands try `.grok/hooks/…` then the cwd shim, then print `{}` / allow
- Installer copies those shims so older `python3 pre_tool_use.py` configs keep working
- Toolchain pins (built / minimum / fallback) in `.grok-stack/config/toolchain.json`; doctor offers install of the fallback or a newer version
- `install_into.py` pulls missing required toolchain tools by default (`--no-deps` to skip, `--all-deps` for optional PHP/Node/gh)
- `routing.json` is live: analysis floor is `repo_explorer` / `task_analyst` / `architect` / `docs_researcher` on non-micro work; `max_parallel_analysis` (default 10) is a ceiling, not a quota; still exactly one write owner
```

The live 2.0.4 notes file (`dist/RELEASE-NOTES.md:1-24`) used a different wrapper (`# Adaptive Grok Build Pro v2.0.4`, MIT one-liner, `## Changes` / `## Assets` / `## Install`). That wrapper is **not** in CHANGELOG 2.0.5. This change’s written contract is CHANGELOG 2.0.5 only, so do not invent Assets/Install/upgrade sections.

Using `publish-v2.0.5.md:13` or `deploy.py:33` **without rewriting** `dist/RELEASE-NOTES.md` would attach 2.0.4 notes to tag `v2.0.5`. That is the remaining docs blocker for the GitHub Release step.

Assets remain zip + sha256 only (this change `release.md:5`, `requirements.md:4`, `publish-v2.0.5.md:13`, `deploy.py:26-33`). No tar.gz in the 2.0.5 contract.

## README / QUICKSTART gaps — do they block publish?

**No. They can ship as-is for this change.**

This change’s acceptance list (`requirements.md:3-8`) is: verify, zip+sha256, keep `.env` / `err.log` / runtime out, tag, push, GitHub Release with CHANGELOG 2.0.5 notes. It does **not** require README/QUICKSTART to cover every 2.0.5 bullet. `brief.md:5`: “No new product features.”

Version identity is already aligned:

- `README.md:1` is `v2.0.5` (not leftover 2.0.4).
- `QUICKSTART.md` has never carried a version string (same as 2.0.1–2.0.4). That is not a 2.0.5 regression.

Feature-doc residuals (unchanged from the prior report; still not in this change’s checklist):

| 2.0.5 CHANGELOG topic (`CHANGELOG.md:5-12`) | README | QUICKSTART |
| --- | --- | --- |
| git-pull / missing cwd hook scripts | omitted (`README.md:124-131` describes `.grok/hooks/` adapters only) | omitted |
| root shims, no root `_lib.py` | omitted | omitted |
| `adaptive.json` `.grok/hooks` then cwd shim then `{}` / allow | omitted | omitted |
| installer copies shims | omitted | omitted |
| toolchain pins + doctor offer | documented (`README.md:51-70`) | documented (`QUICKSTART.md:3-5`) |
| `install_into.py` default deps / `--no-deps` / `--all-deps` | documented (`README.md:74-78`) | `--no-deps` only (`QUICKSTART.md:16-17`); no `--all-deps` |
| live `routing.json` floor/cap / one write owner | omitted | omitted |

`.grok/hooks/README.md:5-11` still titles the mode “Soft mode (default since v2.0.4)” while describing the 2.0.5 shim/`git pull` behavior. Not a publish-acceptance item.

Historical pattern: 2.0.4 CHANGELOG items remain in README (fail-open Stop, invocation policy, `grok_deploy.py`, MIT). That is leftover-from-previous-release documentation, not a 2.0.5 contradiction (`README.md:110-131,148`).

`packages/README.md:12` now claims `adaptive-grok-build-pro-v2.0.5.zip` before the zip exists. The rebuild snippet (`packages/README.md:16-18`) is `VERSION`-driven and is correct once `package_stack.py` + `cp` run. Table-ahead-of-artifact is a pre-package inconsistency, not a reason to hold the release after the zip is copied.

## `__version__` — leftover, not a documented contract

`.grok-stack/adaptive_grok/__init__.py:1-3`:

```python
"""Adaptive Grok Build Pro runtime."""

__version__ = "2.0.0"
```

Documented version contract is the `VERSION` file, not this attribute:

- `CHANGELOG.md:51` (2.0.1): “Version source of truth is `VERSION`; packager default output follows it”
- `58e51e/evidence/analysis-repo_explorer.md:3`: “Version strings live in `VERSION`, `README.md`, `CHANGELOG.md`, and `scripts/package_stack.py` default output”
- `58e51e/brief.md:13`: bump `VERSION` and **user-facing** version strings
- Runtime readers use the file: `deploy.py:13-17` (`_version` reads `VERSION`), `package_stack.py:37`, `tests/test_deploy.py:99`, `tests/test_manifest_package.py:55`

No other tree reference treats `adaptive_grok.__version__` as a contract. Grep of docs/ADRs/decisions/tests/scripts finds no import or assertion of that symbol. Tests never hardcode `2.0.0` as the product version. The attribute was not listed among version strings in the 2.0.1 bump and was never updated for 2.0.1–2.0.5.

**Ruling:** leftover from 2.0.0, not a publish contract. Bumping it is optional cleanup, not required by `requirements.md` or CHANGELOG 2.0.1. Leaving `"2.0.0"` does not block v2.0.5.

## Still blocking the GitHub Release step (docs)

1. Rewrite `dist/RELEASE-NOTES.md` to the CHANGELOG 2.0.5 text above **before** `gh release create` / before running the printed `deploy.py` command.
2. Create `packages/adaptive-grok-build-pro-v2.0.5.zip` + sibling `.sha256` (still missing under both `packages/` and `dist/`). The `packages/README.md:12` row already names that file.

README H1, QUICKSTART, `packages/README.md` 2.0.5 row, and `publish-v2.0.5.md` existence do **not** block. `__version__` does **not** block.
