# Docs research — VERSION SoT, deploy `--title`, no GHA, last-mile argv; «делай новый релиз и ПУБЛИКУЙ» vs 2.0.7 + `gh release`

Route: `2929c09b96b5`. Change: `20260816-publish-v2-0-7-github-release-2929c0`.
Question: quote versioning (`VERSION` is source of truth), deploy `--title`, the GitHub Actions ban, and last-mile commands. Confirm whether user «делай новый релиз и ПУБЛИКУЙ» authorizes identity 2.0.7 plus `gh release create`.

Read-only. No application-code edits. No `.env`. No push / tag / merge / deploy. No APIs invented.

Adaptive-delivery loaded from `.grok/skills/adaptive-delivery/SKILL.md`. This agent is in `allowed_agents`. `write_agent` is `null`. Named gates: `scope_and_design_approval`, `production_action_approval`. Required evidence: `verification`, `security_review`, `release_review`. Workflow skills: `adaptive-delivery`, `release-readiness`.

## Sources

- This change package (`brief.md`, `architecture.md`, `requirements.md`, `release.md`, `rollback.md`, `tasks.md`, `test-plan.md`, `state.json`, `route.json`, `evidence/human-approval.md`)
- `.grok-stack/runtime/active-route.json` (`task`: `<user_query>делай новый релиз и ПУБЛИКУЙ НАХУЙ ЗАЕБАЛ</user_query>`)
- `.grok/skills/adaptive-delivery/SKILL.md` §7; `.grok/skills/release-readiness/SKILL.md`
- `AGENTS.md` source-of-truth order and prohibited routine actions
- `engineering/decisions.md` 2026-08-16 Never GitHub Actions; 2026-08-14 production-invocation prefixes; 2026-08-15 `делай` reuse
- `engineering/runbooks/publish-v2.0.{4,5,6}.md` (no `publish-v2.0.7.md` on disk)
- `CHANGELOG.md` §§2.0.6–2.0.1; `README.md`; `QUICKSTART.md`; `packages/README.md`; `VERSION`; `dist/RELEASE-NOTES.md`; `dist/HANDOFF.md`
- `.grok-stack/adaptive_grok/deploy.py` `_version` / `_human_commands`; `.grok-stack/adaptive_grok/__init__.py`; `scripts/package_stack.py` `_default_output`; `scripts/grok_deploy.py`; `scripts/grok_approve.py`; `scripts/install_into.py` `--with-ci`
- `.grok-stack/adaptive_grok/policy.py` `PRODUCTION_INVOCATIONS`; `tests/test_deploy.py`; `tests/test_structure.py`; `tests/test_manifest_package.py`
- `.grok-stack/templates/ci/README.md`; `Makefile`; `.grok-stack/runtime/approvals.json` (not `.env`)
- Prior packages: `58e51e` (VERSION SoT), `3c1039` (leftover `11da31a`, `--title`, stay 2.0.6), `5be23b` / `9fd274` (do not invent 2.0.7 while 2.0.6 unpublished), `864726` / `cd8a96` / `e584b3` / `b625b4` (last-mile print vs execute; title)
- `engineering/adr/` empty. `engineering/contracts/{openapi,asyncapi,schemas}/` have no product APIs.

This agent did not call `gh` or GitHub. Live Latest / tag-peel claims below are from this package and prior recorded evidence, not a fresh view.

---

## 0. Current identity (inspected)

| Surface | Value | Cite |
| --- | --- | --- |
| `VERSION` | `2.0.6` | root file, one line |
| `__version__` | `"2.0.6"` | `.grok-stack/adaptive_grok/__init__.py:3` |
| README H1 | `# Adaptive Grok Build Pro v2.0.6` | `README.md:1` |
| CHANGELOG top | `## 2.0.6 — 2026-08-16` | `CHANGELOG.md:3` |
| `dist/RELEASE-NOTES.md` | CHANGELOG §2.0.6 verbatim | on-disk scratch |
| `packages/README.md` last row | `v2.0.6` | line 13 |
| 2.0.7 zip | **absent** | `packages/` / `dist/` listings |
| `publish-v2.0.7.md` | **absent** | `engineering/runbooks/` has 2.0.4–2.0.6 only |
| Local `main` | `11da31a3f3e60a0463233cb96c576da8517ddabd` | `.git/refs/heads/main` |
| Tag object `v2.0.6` | `8e7c5b67a1f9e51cc2f15586b72e0dceff7f8ee1` | `.git/refs/tags/v2.0.6` |
| Prior recorded peel | `e75f3a1` (`Release v2.0.6: ban GitHub Actions, rebuild zip`) | `b625b4` / this `brief.md:3` |
| `3c1039` leftover | committed as `11da31a`, package `ready` | `3c1039/state.json:31-33` |

This package `brief.md:3`:

> `11da31a` leftover fixes sit on main but Latest is still v2.0.6 (`e75f3a1`). User: new release and publish now.

`3c1039/evidence/implementation.md:68`:

> Printer still emits `gh release create v2.0.6` because `VERSION` is 2.0.6. Humans must not re-create that tag.

So a **new** identity is required. Recreating `v2.0.6` is retag, which this package forbids (`brief.md:15`; `human-approval.md:7`).

---

## 1. Versioning — `VERSION` is the source of truth

No OpenAPI/ADR version contract. Standing product contract is the `VERSION` file.

### 1.1 Quoted SoT

`CHANGELOG.md` §2.0.1 (`CHANGELOG.md:61`):

> Version source of truth is `VERSION`; packager default output follows it

`scripts/package_stack.py` `_default_output` (`package_stack.py:37-39`):

```python
version = (root / 'VERSION').read_text(encoding='utf-8').strip() or '0.0.0'
return f'dist/adaptive-grok-build-pro-v{version}.zip'
```

`deploy.py` `_version` (`deploy.py:13-17`) reads the same file for tag / zip / `--title`. `packages/README.md:19` copies with `$(tr -d '[:space:]' < VERSION)`. `README.md:139`: default output is `dist/adaptive-grok-build-pro-v<VERSION>.zip`.

`58e51e/brief.md:13-14` (first VERSION/packager change):

> Bump `VERSION` and user-facing version strings
> Default packager output follows `VERSION`

`58e51e/requirements.md:5-6`: `VERSION` is `2.0.1`; packager default is `dist/adaptive-grok-build-pro-v2.0.1.zip`.

`ec0388/evidence/analysis-docs_researcher.md:46-64` already locked: bump `VERSION` **before** packaging; do not hard-code a zip name.

Do **not** add `pyproject.toml` / `requirements.txt` / `setup.py` as a second version source (`decisions.md` 2026-08-16 Ruff lives in `ruff.toml`; this `brief.md:15` out of scope).

### 1.2 Surfaces that must move with `VERSION` for 2.0.7

Same table `ec0388/evidence/analysis-docs_researcher.md:68-77` used for 2.0.5 → 2.0.6. This package restates it (`requirements.md:3-8`; `release.md:3-6`):

| Surface | On disk now | 2.0.7 must become |
| --- | --- | --- |
| `VERSION` | `2.0.6` | `2.0.7` |
| `__version__` | `"2.0.6"` hardcoded | `"2.0.7"` (test locks equality with `VERSION`) |
| README H1 | `Adaptive Grok Build Pro v2.0.6` | same form with `v2.0.7` |
| `CHANGELOG.md` | top `## 2.0.6 — 2026-08-16` | **new** top `## 2.0.7 — …`; keep 2.0.6–2.0.0 history |
| `dist/RELEASE-NOTES.md` | §2.0.6 | §2.0.7 verbatim for `--notes-file` |
| `packages/README.md` | last row 2.0.6 | **add** 2.0.7 row; do not drop 2.0.0–2.0.6 |
| Zip | `packages/adaptive-grok-build-pro-v2.0.6.zip` | new `…-v2.0.7.zip` + sibling `.sha256` |
| Tag | annotated `v2.0.6` → `e75f3a1` | new annotated `v2.0.7` on the 2.0.7 commit |
| Title | live card `Adaptive Grok Build Pro v2.0.6` (after `b625b4` edit) | `--title "Adaptive Grok Build Pro v2.0.7"` at **create** |

`__version__` is **not** SoT. `3c1039/evidence/code-review.md:217`:

> `__version__` is hardcoded. A later `VERSION` bump will fail `test_package_version_matches_version_file` until someone edits `__init__.py`. Intended lock, not a live bug.

Two tests also hardcode the **string** `2.0.6` (not only “equals `VERSION`”):

- `tests/test_structure.py:116` `test_version_is_2_0_6_and_github_actions_are_absent` → `assertEqual(..., '2.0.6')`
- `tests/test_manifest_package.py:113,124` `test_included_files_and_shipped_zip_have_no_github_actions` → live `VERSION` and in-zip `VERSION` both `'2.0.6'`

An identity bump that leaves those literals at `2.0.6` fails `grok_verify --mode pr`. Rename/update those assertions with the bump. Do not invent a `pyproject` version field to satisfy them.

### 1.3 Prior “do not invent 2.0.7” is scoped to unpublished 2.0.6

`9fd274/evidence/analysis-docs_researcher.md:184` and `5be23b/evidence/analysis-architect.md:22`:

> Stay `VERSION` 2.0.6 … bump to 2.0.7 [is out]
> stay on unpublished 2.0.6; do not open 2.0.7

That ruling applied while Latest was still `v2.0.5` and 2.0.6 itself was unpublished. 2.0.6 is now the published Latest (`brief.md:3`; `b625b4`). `3c1039` then landed leftover product fixes **on** identity 2.0.6 and said do not publish unless already-shipped identity (`3c1039/brief.md:14`). Those leftovers sit at `11da31a`, after tag peel `e75f3a1`. Shipping them as `v2.0.6` would be a retag. The only in-contract next identity is **2.0.7**.

---

## 2. Deploy `--title`

The GitHub Release **name** is not an OpenAPI field. In-repo flag is `gh release create … --title`.

### 2.1 Printer now (post-`11da31a`)

`deploy.py:24-34` `_human_commands` (version from `VERSION`):

```text
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v{version}.zip* packages/
git tag -a v{version} -m "v{version}"
git push origin {branch}
git push origin v{version}
gh release create v{version} packages/{zip} packages/{zip}.sha256 --title "Adaptive Grok Build Pro v{version}" --notes-file dist/RELEASE-NOTES.md
```

Locked by `tests/test_deploy.py:108`:

> `self.assertIn(f'--title "Adaptive Grok Build Pro v{version}"', joined)`

`3c1039/requirements.md:5` and `3c1039/evidence/implementation.md:28` added that flag because 2.0.5 and the first 2.0.6 create omitted it and shipped **empty** names (`b625b4/evidence/analysis-docs_researcher.md:51-54,71-78`). `publish-v2.0.6.md:27` was updated to match. Older `publish-v2.0.4.md:23` and `publish-v2.0.5.md:15` still have `--notes-file` only.

`dist/HANDOFF.md:25-30` (v2.0.1) already used `--title "Adaptive Grok Build Pro v2.0.1"`. Desired 2.0.7 name is the same form (`this release.md:5`; `test-plan.md:3`).

`scripts/grok_deploy.py:15`:

> Prepare human-owned publish commands. Never executes tag, push, or release.

Do not invent REST `name` / `--target` / asset-replace flags. Create-time title is `--title`.

### 2.2 Notes stay CHANGELOG verbatim

`this release.md:6`: `Notes: dist/RELEASE-NOTES.md from CHANGELOG 2.0.7`.

Standing contract from 2.0.5 onward (`cd8a96/evidence/analysis-docs_researcher.md:179-207`; `864726/evidence/analysis-docs_researcher.md:34-35`): working-tree `dist/RELEASE-NOTES.md` = new CHANGELOG section, no MIT one-liner, no `## Assets` / `## Install`, no leftover prior heading. `dist/` is gitignored; `gh` reads the working tree.

---

## 3. No GitHub Actions

Independent sources. No document equates GitHub CLI `gh release *` with GitHub Actions.

| Thing | What the tree calls it | This change |
| --- | --- | --- |
| **GitHub Actions** | `.github/workflows/*.yml`; Dependabot; `--with-ci` | **Banned** |
| **GitHub CLI (`gh`)** | toolchain profile `release`; `README.md:60` | last mile |
| **`gh release create`** | human/controller last mile | **in scope** after identity 2.0.7 |
| **`gh release edit`** | in-place card fix (`b625b4`) | **not** this change |
| **`gh release delete`** | rollback only | `rollback.md:4` |

`engineering/decisions.md` 2026-08-16 Never GitHub Actions:

> Local `make verify` / `python3 scripts/grok_verify.py --mode pr` is the only quality gate. Do not add `.github/workflows/`, Dependabot, `--with-ci` copies, or another CI SaaS. `install_into --with-ci` is `SystemExit` / forbidden.

`CHANGELOG.md:5,10` (current §2.0.6 lead):

> Quality contour: Ruff, Bandit, coverage ratchet, no GitHub Actions.
> No GitHub Actions / Dependabot; local `python3 scripts/grok_verify.py --mode pr` is the only gate. `--with-ci` is forbidden.

`.grok-stack/templates/ci/README.md:3-15` (current file, post-ban):

> This product never uses GitHub Actions.
> Do not add `.github/workflows/` or Dependabot.
> Local `python3 scripts/grok_verify.py --mode pr` is the only gate.

`install_into.py:99-103`:

> GitHub Actions is forbidden. Use local `make verify` / `python3 scripts/grok_verify.py --mode pr`.

`publish-v2.0.6.md:5`:

> Last mile is the GitHub CLI (`gh release create`), not GitHub Actions. Do not add `.github/workflows/`.

`policy.py:48-54` `PRODUCTION_INVOCATIONS` is only `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`. There is no `github-actions` / `workflow` prefix. `git tag` is **not** in that tuple (`decisions.md:37-39`).

Zip must contain no GHA (`this requirements.md:5`; `test_manifest_package.py:111-127`; `test_structure.py:117-120`). `Makefile` `verify` / `package` / `deploy` are local only.

---

## 4. Last-mile commands

There is no `publish-v2.0.7.md`. After `VERSION` is `2.0.7`, `deploy.py` prints the six-line sequence with that version. Same shape as `publish-v2.0.6.md:21-27`.

### 4.1 After identity + zip exist

Substitute `version=2.0.7` into the printer (branch today is `main`):

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.7.zip* packages/
git tag -a v2.0.7 -m "v2.0.7"
git push origin main
git push origin v2.0.7
gh release create v2.0.7 packages/adaptive-grok-build-pro-v2.0.7.zip packages/adaptive-grok-build-pro-v2.0.7.zip.sha256 --title "Adaptive Grok Build Pro v2.0.7" --notes-file dist/RELEASE-NOTES.md
```

Skip the first two lines only after the 2.0.7 zip + sha256 are already tracked (`864726/evidence/analysis-docs_researcher.md:23`; same reduction as cd8a96). They are **not** on disk yet, so the packager lines are in scope (`this tasks.md`: Identity + zip).

`this release.md`: assets = packages zip + sha256; title = `Adaptive Grok Build Pro v2.0.7`; notes = CHANGELOG 2.0.7 via `dist/RELEASE-NOTES.md`. No source tar.gz after 2.0.2 (`cd8a96/evidence/analysis-docs_researcher.md:216-217`).

### 4.2 Gates before those argv

`publish-v2.0.6.md:11-17` / `adaptive-delivery` §7 / `release-readiness`:

```bash
python3 scripts/grok_status.py
python3 scripts/grok_verify.py --mode pr
python3 scripts/grok_deploy.py
python3 scripts/grok_approve.py production --reason "publish v2.0.7"
```

`--record` needs a live production token (`deploy.py:74-75`). Dry-run print needs change status `ready`/`released` and empty evidence gaps (`deploy.py:55-63`). This change is still `draft` (`state.json:14`).

Agent-side `git push` / `gh release create` need a **live** 15-minute `grok_approve.py production` (`grok_approve.py:18`; `AGENTS.md:104`). A human terminal outside the hook does not. Markdown `human-approval.md` is not `has_valid_approval` (`864726/evidence/analysis-docs_researcher.md:80`).

Order is load-bearing (`cd8a96/evidence/analysis-architect.md:83`): push the annotated tag, then `gh release create`. Creating the Release before the remote tag exists can mint a different remote ref. No `-f`. No force-push.

### 4.3 Confirm after publish (`this test-plan.md`)

1. `VERSION` is `2.0.7`; no `.github/workflows` / Dependabot / `github-actions.yml`
2. `python3 scripts/grok_verify.py --mode pr` PASS
3. Latest `tag_name` `v2.0.7` and `name` `Adaptive Grok Build Pro v2.0.7`
4. `v2.0.6` (and `v2.0.5`) still exist

### 4.4 Rollback (`this rollback.md`; same shape as `publish-v2.0.6.md:30-35`)

```bash
gh release delete v2.0.7 --yes
git push origin :refs/tags/v2.0.7
git tag -d v2.0.7
```

Do not touch `v2.0.6` / `v2.0.5`. No force-push.

### 4.5 Print vs execute (already named)

Standing rule is print-only (`publish-v2.0.6.md:3-7`; adaptive-delivery `SKILL.md:103`; release-readiness `SKILL.md:18-20`; `README.md:110`; `QUICKSTART.md:33`). `AGENTS.md:104` bans publish **without** short-lived explicit approval; user-approved scope is SoT #1 (`AGENTS.md:19-21`).

Prior last miles after an explicit go:

| Change | User go | What executed |
| --- | --- | --- |
| `e584b3` | «я разрешаю» | recorded push + tag + `gh release create` v2.0.4 (`write_agent` null) |
| `cd8a96` | «делай» | `grok_approve` + push tag + `gh release create` v2.0.5 |
| `864726` / `5be23b` | «делай всё полностью вместе с релизом» / «go ahead» | tag/push/`gh release create` v2.0.6 |
| `b625b4` | «меняй в гите релиз» | `gh release edit` only, not a new create |

`ec0388` wrote print-only back and said a prior «делай» **does not transfer**. A later prompt that **names** release, plus recorded `production_action_approval`, is the on-ramp (`864726/evidence/analysis-docs_researcher.md:140-145`).

This route `write_agent` is **null** (`route.json:67`; `architecture.md:3`): controller owns identity bump + last mile after production approval. This agent (`docs_researcher`) does not run git/gh.

---

## 5. Does «делай новый релиз и ПУБЛИКУЙ» authorize 2.0.7 + `gh release`?

Route `task` and `evidence/human-approval.md` quote the same user text: «делай новый релиз и ПУБЛИКУЙ НАХУЙ ЗАЕБАЛ».

`human-approval.md:3-7`:

> **scope_and_design_approval** and **production_action_approval** granted 2026-08-16.
>
> User: «делай новый релиз и ПУБЛИКУЙ НАХУЙ ЗАЕБАЛ»
>
> Authorized: VERSION 2.0.7, package, tag, push origin main, push tag, GitHub Release. Do not retag 2.0.6. No GitHub Actions. Do not print secrets.

Split the two meanings of “approval,” same split as `864726/evidence/analysis-docs_researcher.md:128-168` and `cd8a96/evidence/analysis-docs_researcher.md:248-289`.

### 5.1 Verbal / markdown — **yes, for a new 2.0.7 create**

| Check | This prompt | Cite |
| --- | --- | --- |
| Names a **new** release | «**новый** релиз» | route `task`; `brief.md:3`; not «меняй» (edit) |
| Names publish | «**ПУБЛИКУЙ**» | same; stronger than bare «делай» |
| Latest is already v2.0.6 | leftover `11da31a` is unpublished | `brief.md:3`; `3c1039/state.json` |
| Next identity | 2.0.7, not retag 2.0.6 | `requirements.md`; `brief.md:15` |
| SoT #1 | user-approved scope outranks print-only default | `AGENTS.md:19-21` |
| Named gates | both present and recorded | `route.json:22-25`; `human-approval.md:3` |
| Prior 2.0.6 «делай» / «go ahead» | does **not** transfer | `ec0388`; `864726` |
| Prior “do not open 2.0.7” | applied to **unpublished** 2.0.6 | `9fd274`; `5be23b` |

Authorized outcome (already written in this package): identity 2.0.7, tracked zip + sha256, annotated tag `v2.0.7` on the 2.0.7 commit, `git push origin main`, `git push origin v2.0.7`, `gh release create … --title "Adaptive Grok Build Pro v2.0.7" --notes-file dist/RELEASE-NOTES.md`, GitHub Latest that name. Leave `v2.0.6` and `v2.0.5` up. No GHA. No `pyproject.toml`. No force-push.

That is the same shape as 2.0.5 leftover → 2.0.6: new `VERSION` / tag / zip / CHANGELOG section (`ec0388/evidence/analysis-docs_researcher.md:40`).

`делай` is a follow-up token for **route reuse**, not a veto of a new production go (`decisions.md:33-35`; `CHANGELOG.md:35`). It does not revive ready `3c1039` or ready `5be23b`. That is why this is new route `2929c09b96b5`.

### 5.2 Live machine token — **no, this prompt is not `has_valid_approval` for 2.0.7**

`.grok-stack/runtime/approvals.json` currently has two rows, both reason `"push 2.0.6 leftover bugfixes to origin/main"`, created `2026-08-16T19:26:43+00:00`, expire `19:41:43+00:00` (`production` `37754a2d61eb`, `external-write` `5babcf924709`). Those are leftover-push tokens from `3c1039` / `11da31a`, not a “publish v2.0.7” reason. Default TTL is 15 minutes.

Markdown approval is not a live token. Agent-side `git push` / `gh release create` still need a **fresh** `python3 scripts/grok_approve.py production --reason "publish v2.0.7"` in this session, the same gate `cd8a96` / `864726` used before they executed.

### 5.3 What this phrase does **not** authorize

- Retag / `git tag -f` / delete+recreate `v2.0.6`
- Any mutation of `v2.0.5`
- GitHub Actions / `.github/workflows/` / Dependabot / `--with-ci`
- `pyproject.toml` / `requirements.txt` / `setup.py`
- Force-push
- MCP `create_release` / `create_or_update_ref` (`864726/evidence/analysis-architect.md:165`)
- Reading `.env`
- This agent (`docs_researcher`) running git/gh

---

## 6. Bottom line

1. **`VERSION` is SoT.** Bump the file to `2.0.7` first. Packager, deploy printer, zip name, and tag follow it. Also move `__version__`, README H1, new CHANGELOG `## 2.0.7`, `packages/README.md` row, `dist/RELEASE-NOTES.md`, and the two tests that hardcode the string `2.0.6`. Do not add `pyproject.toml`. Do not retag `v2.0.6`.

2. **`--title` is required at create.** Current `deploy.py` prints `--title "Adaptive Grok Build Pro v{VERSION}"`. 2.0.7 must ship that flag so Latest `name` is `Adaptive Grok Build Pro v2.0.7`, not an empty card. Notes = CHANGELOG 2.0.7 via `dist/RELEASE-NOTES.md`.

3. **No GitHub Actions.** Last mile is GitHub CLI. Local `grok_verify --mode pr` is the only gate. `--with-ci` is `SystemExit`. Zip and tree must have no workflows / Dependabot.

4. **Last-mile argv** (after identity + zip): tag `v2.0.7`, `git push origin main`, `git push origin v2.0.7`, `gh release create v2.0.7` zip + sha256 + `--title` + `--notes-file`. Rollback deletes only `v2.0.7`. Leave 2.0.6 / 2.0.5.

5. **«делай новый релиз и ПУБЛИКУЙ» is verbal `production_action_approval` for 2.0.7 + `gh release create`.** Both named gates are already recorded. It is the “names a new release” prompt, not a card edit and not a 2.0.6 retag. It is **not** a live 15-minute token; leftover-push rows in `approvals.json` do not cover this publish. Controller owns the bump and last mile (`write_agent` null). This agent does not execute.
