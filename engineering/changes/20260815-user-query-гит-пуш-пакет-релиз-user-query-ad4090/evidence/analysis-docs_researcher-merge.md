# Docs research — merge / after push+tag+release

Route: `e2b4b7341a5c` (user «смерджи все»).  
Durable change: `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090` (`ad4090c51ca6`).  
Prior reports: `evidence/analysis-docs_researcher.md`, `evidence/analysis-docs_researcher-continue.md`.  
This report answers only: after a successful last-mile `git push origin main` + tag `v2.0.5` + `gh release create v2.0.5`, what a **fresh clone** and a **parallel Grok** will see.

No APIs invented. `engineering/adr/` is empty. `engineering/contracts/{openapi,asyncapi,schemas}/` have no product contracts. `.env` was not read. This agent did not push, merge, tag, or release.

## «смерджи все» is not a git-merge problem

There is nothing to merge.

| Check | Fact | Cite |
| --- | --- | --- |
| Local branches | only `main` | `.git/HEAD` → `refs/heads/main`; `.git/refs/heads/` lists `main` |
| GitHub branches | only `main` @ `33a02f1` | `GET /repos/Dimkox/adaptive-grok-build-pro/branches` |
| Pull requests | `[]` | `GET /repos/Dimkox/adaptive-grok-build-pro/pulls?state=all` |
| Local HEAD | `7c0ae7573535ddd0cfe3800f81278991ced81584` | `.git/refs/heads/main` |
| `origin/main` | still `33a02f1128ab0a865bfb1c853248f997dcf9e39b` | `.git/refs/remotes/origin/main`; GitHub `commits/main` |
| Local tags | stop at `v2.0.4` (`v2.0.5` absent) | `.git/refs/tags/` |
| GitHub latest release | **today** `v2.0.4` | `GET /repos/…/releases/latest` → `tag_name: v2.0.4` |
| GitHub `v2.0.5` | 404 | `GET /repos/…/releases/tags/v2.0.5` |

«смерджи все» in this change is the last mile already written in `release.md`, `requirements.md:6-8`, and `engineering/runbooks/publish-v2.0.5.md`: push the already-committed 2.0.5 tree, tag it, publish the GitHub Release. It is not a PR merge and not a multi-branch integration.

Agents still must not run those commands (`publish-v2.0.5.md:5`, adaptive-delivery §7, `scripts/grok_deploy.py` prepare-only).

## Identity that will be pushed

Publish commit (already local, not on origin):

- SHA: `7c0ae7573535ddd0cfe3800f81278991ced81584`
- Parent: `33a02f1` (tag `v2.0.4`)
- Message: `Release v2.0.5: hook shims, toolchain pins, track zip and checksum` (`.git/COMMIT_EDITMSG`, `.git/logs/HEAD:12`)
- Include list recorded in `evidence/implementation.md:42` and confirmed by `evidence/code-review.md:13-25`: `VERSION`, `CHANGELOG.md`, `README.md`, `packages/README.md`, `packages/adaptive-grok-build-pro-v2.0.5.zip*`, `engineering/runbooks/publish-v2.0.5.md`, plus the 2.0.5 product tree.

Working-tree identity files still match that commit (no later VERSION/README/CHANGELOG rewrite found):

| File | Working / `7c0ae75` | Cite |
| --- | --- | --- |
| `VERSION` | `2.0.5` | `VERSION:1` |
| `README.md` H1 | `# Adaptive Grok Build Pro v2.0.5` | `README.md:1` |
| `CHANGELOG.md` latest heading | `## 2.0.5 — 2026-08-15` | `CHANGELOG.md:3` |
| `packages/README.md` last row | `` `adaptive-grok-build-pro-v2.0.5.zip` `` / `2.0.5` | `packages/README.md:12` |

Documented version contract is the `VERSION` file (`CHANGELOG.md:51`). Runtime leftover `__version__ = "2.0.0"` (`.grok-stack/adaptive_grok/__init__.py:3`) is **not** that contract and will still be `"2.0.0"` after push. Out of scope; do not treat it as the product version.

## After a successful last mile — four surfaces

Condition: human runs the runbook against **this** tree, tags `7c0ae75` (not `33a02f1`), and `gh` uses the current notes file. Then:

| Surface | Fresh clone of `origin/main` | Parallel Grok | GitHub |
| --- | --- | --- | --- |
| `VERSION` | `2.0.5` | same, if it `git pull`s / clones after the push | n/a |
| README H1 | `# Adaptive Grok Build Pro v2.0.5` | same | README on `main` / tag `v2.0.5` |
| CHANGELOG latest heading | `## 2.0.5 — 2026-08-15` | same | same file on `main` / tag |
| Latest GitHub Release | not a git file | `gh release view --latest` / API `releases/latest` → **`v2.0.5`** | `tag_name: v2.0.5`, notes = current `dist/RELEASE-NOTES.md` body |

### Fresh clone (post-push)

A new `git clone https://github.com/Dimkox/adaptive-grok-build-pro.git` of `main` (or `git checkout v2.0.5`) will read:

```text
VERSION:1          → 2.0.5
README.md:1        → # Adaptive Grok Build Pro v2.0.5
CHANGELOG.md:3     → ## 2.0.5 — 2026-08-15
```

They will also see `packages/adaptive-grok-build-pro-v2.0.5.zip` + sibling `.sha256` and `engineering/runbooks/publish-v2.0.5.md` (those are in `7c0ae75`).

They will **not** see `dist/RELEASE-NOTES.md`. `dist/` is gitignored (`/.gitignore:17-18,27`). Nothing generates that file on clone (`package_stack.py` writes zip+sha256 only; `deploy.py:33` only prints `--notes-file`).

They will **not** see post-commit workspace-only files unless those are committed later: `evidence/implementation.md`, `evidence/code-review.md`, `evidence/test-review.md`, this merge report, and the `ready` `state.json` write after `7c0ae75` (`state.json` `updated_at` `2026-08-15T02:51:12` is after the commit recorded in `.git/logs/HEAD`). That does not change VERSION / README H1 / CHANGELOG heading.

### Parallel Grok

| Where the other Grok sits | What it sees **today** (push not done) | What it sees **after** successful last mile |
| --- | --- | --- |
| This workspace | Working tree already 2.0.5 (`VERSION:1`, `README.md:1`, `CHANGELOG.md:3`); notes file 2.0.5; GitHub still 2.0.4 | Same tree; after `git fetch` tags, `v2.0.5` exists; GitHub latest becomes 2.0.5 |
| Fresh clone of origin **now** | **2.0.4** everywhere (see contrast below) | After re-clone / `git pull`: **2.0.5** identity as above |
| `gh release view --latest` / API | `v2.0.4` | `v2.0.5` |

A parallel Grok that does not pull still reports 2.0.4 from origin. Pull / re-clone is required.

### GitHub latest release (post-`gh release create`)

Runbook / `deploy.py` create a normal (non-draft, non-prerelease) release named `v2.0.5`. GitHub `releases/latest` will then return `tag_name: v2.0.5`.

Release **body** = contents of `dist/RELEASE-NOTES.md` at the moment of `gh release create` (`publish-v2.0.5.md:15`, `deploy.py:33`, asserted `tests/test_deploy.py:108`). That file is currently CHANGELOG 2.0.5 (next section). Assets are zip + sha256 only (`release.md:5`, `requirements.md:4,8`, runbook line 15). No tar.gz in the 2.0.5 contract.

If `gh` is skipped, latest stays `v2.0.4` even after `git push origin main`. If notes are rewritten back to 2.0.4 before `gh`, the tag can still be 2.0.5 with the wrong body.

## Confirm: `dist/RELEASE-NOTES.md` is still 2.0.5 text

**Yes.** Prior reports (`analysis-docs_researcher.md`, `-continue.md`) said this file was still `# Adaptive Grok Build Pro v2.0.4`. That is stale. Implementer rewrote it (`evidence/implementation.md:16`); `code-review.md:65-66` and `test-review.md:71` already passed that rewrite.

Re-read now (`dist/RELEASE-NOTES.md:1-10`) is `CHANGELOG.md:3-12` verbatim:

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

No MIT one-liner. No `## Changes` / `## Assets` / `## Install`. No `v2.0.4` heading. Matches this change’s notes contract (`release.md:6`, `requirements.md:8`: notes from CHANGELOG 2.0.5).

Scratch only: gitignored (`/.gitignore:27`). A fresh clone will not contain it. The GitHub Release body is the durable copy of this text after `gh`.

## Confirm: `publish-v2.0.5.md` command list

Confirmed on disk. Full command block (`engineering/runbooks/publish-v2.0.5.md:7-16`):

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.5.zip* packages/
git tag -a v2.0.5 -m "v2.0.5"
git push origin main
git push origin v2.0.5
gh release create v2.0.5 packages/adaptive-grok-build-pro-v2.0.5.zip packages/adaptive-grok-build-pro-v2.0.5.zip.sha256 --notes-file dist/RELEASE-NOTES.md
```

Surrounding runbook facts:

- Header: `# Publish v2.0.5` (`publish-v2.0.5.md:1`)
- Agent rule: “Agents must not run `git push`, `git tag`, or `gh release`; humans own those commands.” (`publish-v2.0.5.md:5`)
- Rollback (`publish-v2.0.5.md:18-24`, same as `rollback.md:3-7`):

```bash
gh release delete v2.0.5 --yes
git push origin :refs/tags/v2.0.5
git tag -d v2.0.5
```

Same six publish lines as `deploy.py:24-34` would print for `VERSION=2.0.5` on branch `main` (`tests/test_deploy.py:103-108`). Zip+copy already done (`implementation.md:50-55`); human may skip the first two lines or re-run them (packager is deterministic). Human must **not** skip the notes file: `gh` reads `dist/RELEASE-NOTES.md` from the working tree, not from git.

Tag target must be `7c0ae75`, not `33a02f1` (`implementation.md:108`, `architecture.md` / `evidence/analysis-architect.md:185`).

## Contrast: what origin / a clone sees **right now** (push not done)

These are live GitHub `main` / latest-release facts. They flip only after the last mile.

| Surface | Origin / GitHub **today** | Cite |
| --- | --- | --- |
| `VERSION` | `2.0.4` | raw `main` `VERSION` |
| README H1 | `# Adaptive Grok Build Pro v2.0.4` | raw `main` `README.md` line 1 |
| CHANGELOG latest heading | `## 2.0.4 — 2026-08-15` | raw `main` `CHANGELOG.md` |
| GitHub latest release | `v2.0.4` — “Adaptive Grok Build Pro v2.0.4”, 2.0.4 wrapper body, zip+sha256 assets | `releases/latest` `html_url` `…/releases/tag/v2.0.4` |

Until push+tag+release succeed, a fresh clone and a parallel Grok that only looks at GitHub will keep reporting **2.0.4**.

## Leftovers a clone will still see after 2.0.5 (not identity bugs)

Already ruled out of this change (`brief.md:5`, architect / prior docs reports):

- `.grok-stack/adaptive_grok/__init__.py:3` `__version__ = "2.0.0"`
- README / QUICKSTART still omit some CHANGELOG 2.0.5 hook/`routing.json` bullets
- `.grok/hooks/README.md` still titles soft mode “since v2.0.4”

Those ship as-is. They do not change VERSION, README H1, CHANGELOG latest heading, or the GitHub latest tag name.

## Bottom line

After a successful push of `7c0ae75`, tag `v2.0.5` on that commit, and `gh release create` with the current notes file:

1. Fresh clone `VERSION` = `2.0.5` (`VERSION:1`).
2. Fresh clone README H1 = `# Adaptive Grok Build Pro v2.0.5` (`README.md:1`).
3. Fresh clone CHANGELOG latest heading = `## 2.0.5 — 2026-08-15` (`CHANGELOG.md:3`).
4. GitHub latest release = `v2.0.5`, body = CHANGELOG 2.0.5 text from `dist/RELEASE-NOTES.md:1-10`.
5. `dist/RELEASE-NOTES.md` **is still 2.0.5** on disk; it will **not** appear in the clone (`/.gitignore:27`).
6. `publish-v2.0.5.md` command list is the six lines above; humans own them.

Today none of that is on origin. There are no PRs or extra branches to merge.
