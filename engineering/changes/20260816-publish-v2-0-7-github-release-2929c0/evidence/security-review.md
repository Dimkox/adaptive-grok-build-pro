# Security review — `2929c09b96b5`

**PASS**

Route: `2929c09b96b5` (intent=`release`, risk=`high`, `write_agent: null`)  
Change: `20260816-publish-v2-0-7-github-release-2929c0`  
Object reviewed: ship commit `02376cc097d7640d56dd308b98efe4e026f4c253` — *Release v2.0.7: leftover 2.0.6 fixes as a published identity*  
Reviewer: `security_reviewer` (read-only; in `allowed_agents`)  
Inspected: change package + analysis + `human-approval.md`, local refs, identity files, packager/manifest/policy/tests, zip sidecars, public GitHub HTML for `.github`, `pyproject.toml`, `/actions`, `/releases`. Unauthenticated GitHub HTML for `/releases` is incomplete (“Sorry, something went wrong”); local refs are the authority for this ship.

No application-code edits. `.env` was not read. No push, merge, tag, retag, zip rebuild, or `gh release` from this agent.

---

## Verdict in one screen

`02376cc` is a local identity+zip commit. It advertises **2.0.7**, adds a new 2.0.7 zip, and does not restore GitHub Actions, packaging markers, or secrets. The leftover 2.0.6 artifact is untouched. Last mile (tag / push / GitHub Release) has **not** run and is **not** authorized by this report.

| Required confirmation | Result |
| --- | --- |
| VERSION 2.0.7 | **PASS.** `VERSION` and `__version__` are `2.0.7`. README H1, CHANGELOG `## 2.0.7`, packages/README row, and test pins match. |
| No GitHub Actions | **PASS.** No local `.github/`. No `dependabot.yml`. No `github-actions.yml`. No `runs-on:` workflow YAML. GitHub `main/.github` is 404. `/actions` has only historical v2.0.4 / v2.0.5 failures. |
| No `pyproject.toml` | **PASS.** Absent locally and 404 on GitHub `main`. `requirements.txt` / `setup.py` also absent. |
| No secrets in zip | **PASS.** Packager still drops `.env` / keys / runtime; tests lock that; tree secret-scan patterns are clean; shipped-zip test requires in-zip `VERSION=2.0.7` and no GHA members. |
| Leftover 2.0.6 zip untouched | **PASS.** Sidecar still `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d`. `v2.0.6` tag object still `8e7c5b67…`. `v2.0.5` still `7f85f7be…` / digest `b80e6310…`. |

**Authz** is the named gates from «делай новый релиз и ПУБЛИКУЙ НАХУЙ ЗАЕБАЛ», scoped to identity 2.0.7 + later last mile. This review covers the ship commit only. **Secrets / PII / tenant isolation** are not in play. **Irreversible** actions (tag, push, `gh release create`, retag, force-push, GHA restore) did not happen.

---

## 1. What `02376cc` is

| Probe | Value |
| --- | --- |
| Local `refs/heads/main` / `HEAD` | `02376cc097d7640d56dd308b98efe4e026f4c253` |
| Parent (from `.git/logs/HEAD`) | `11da31a3f3e60a0463233cb96c576da8517ddabd` |
| `refs/remotes/origin/main` | still `11da31a` — **not pushed** |
| Local tag `v2.0.7` | **absent** (tags stop at `v2.0.6`) |
| Subject | `Release v2.0.7: leftover 2.0.6 fixes as a published identity` |

This is the architect’s required **new** commit after `11da31a`. It is not a retag of `v2.0.6` (`e75f3a1`) and not a 2.0.7 tag on the still-2.0.6 leftover SHA.

Identity surfaces on the tree:

| Surface | Value |
| --- | --- |
| `VERSION` | `2.0.7` |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.7"` |
| `README.md` H1 | `# Adaptive Grok Build Pro v2.0.7` |
| `CHANGELOG.md` top | `## 2.0.7 — 2026-08-16` (still “Still no GitHub Actions”) |
| `packages/README.md` | 2.0.7 row added; 2.0.6–2.0.0 rows kept |
| Tests | `test_version_is_2_0_7_and_github_actions_are_absent`; zip pin `2.0.7` |
| Runbook | `engineering/runbooks/publish-v2.0.7.md` (CLI last mile, not Actions) |
| Zip | `packages/adaptive-grok-build-pro-v2.0.7.zip` + sidecar `ec48d3174248e15e241519546b1414a7698857509cf97ac61e078dbd204de01c` (matches `dist/`) |
| Scratch notes | `dist/RELEASE-NOTES.md` = CHANGELOG §2.0.7 only |

`deploy.py` still prints `--title "Adaptive Grok Build Pro v{version}"`. Not edited on this ship.

---

## 2. Required confirmations

### 2.1 VERSION is 2.0.7

Working tree and ship identity agree. `test_package_version_matches_version_file` still locks `__version__ == VERSION`. In-zip `VERSION` is asserted as `2.0.7` by `tests/test_manifest_package.py::test_included_files_and_shipped_zip_have_no_github_actions` when `packages/adaptive-grok-build-pro-v2.0.7.zip` exists (it does).

Packager default output follows `VERSION` (`package_stack.py` `_default_output`). A pack after the bump cannot silently emit `v2.0.6.zip`.

### 2.2 No GitHub Actions

| Probe | Result |
| --- | --- |
| Local `.github/` | absent |
| `.github/dependabot.yml` | absent |
| `.grok-stack/templates/ci/github-actions.yml` | absent; CI README still bans Actions |
| Repo `*.yml` / `*.yaml` with `runs-on:` | none |
| `install_into(..., with_ci=True)` | still `SystemExit` (“GitHub Actions is forbidden”) |
| `https://github.com/Dimkox/adaptive-grok-build-pro/tree/main/.github` | **404** |
| `/actions` | **5 historical failures**, all `.github/workflows/adaptive-grok.yml` on **v2.0.4 / v2.0.5** (`097f5c9`, `33a02f1`, `7c0ae75`). **No v2.0.6 or v2.0.7 run.** |

`included_files()` would pack `.github/` if it existed. It does not. The shipped-zip test fails if any member path contains `.github/workflows/`, `dependabot.yml`, or `github-actions.yml`.

GitHub CLI last mile (`gh release create`) is not Actions. Policy `PRODUCTION_INVOCATIONS` lists that prefix; this review did not execute it.

### 2.3 No `pyproject.toml`

| Probe | Result |
| --- | --- |
| Root `pyproject.toml` | does not exist |
| `requirements.txt` / `setup.py` | do not exist |
| `test_product_tree_has_no_packaging_markers` | still locks all three absent |
| GitHub `main/pyproject.toml` | **404** (“does not contain the path pyproject.toml”) |

Adding a packaging marker would flip `detect_repo` and can skip `python-unittest`. This ship does not do that.

### 2.4 No secrets in the 2.0.7 zip

`.env` exists on the operator machine (parent listing only). **Not opened.** `.gitignore` and `policy.py` `DEFAULT_SECRET_READ` still cover `.env`, `.env.*`, `*.pem` / `*.key` / `*.p12` / `*.pfx`, `id_rsa`, `id_ed25519`, `credentials*`, `secrets/**`.

Packager (`manifest.py`):

- `EXCLUDED_FILES` includes `.env`, `err.log`, `MANIFEST.sha256` (re-embedded then root unlinked)
- `_is_secret_path` drops `.env`, `.env.*` (except `.env.example`, which is absent), and key suffixes
- `.grok-stack/runtime/*` except `.gitkeep` is dropped (so `approvals.json` is not packed)
- `.zip` / `.sha256` members are dropped (the 2.0.7 archive does not nest prior zips)
- `dist/` is an excluded part

Locked by `test_archive_excludes_dotenv_and_keys` and `test_archive_excludes_err_log`. Root `MANIFEST.sha256` is gone after pack (`test_write_archive_unlinks_root_manifest_but_embeds_it`).

Workspace text scan (not `.env`):

- No `github_pat_` / `ghp_` / `gho_` / `BEGIN … PRIVATE KEY` / `AKIA…` values
- No `token|secret|password|api_key = "…"` matches of the `secret-scan` generic regex
- Only fixture mention: `tests/test_manifest_package.py` `GIT_FINE_GRAIN_TOKEN=should-not-pack` (unquoted; not packed from a real `.env`)

Zip bytes were not unzipped here (binary; no shell on this release route). Evidence is packager + tests + tree. That is the same bar used on prior release reviews when shell is blocked.

Residual (accepted, named by architect): `included_files()` walks `engineering/changes/`, so this `2929c0` analysis and sibling change-package markdown that were on disk at pack time are inside the zip. Those files name token *kinds* (`GIT_FINE_GRAIN_TOKEN`) and approval *ids*, not secret values. Do not add an exclude list on this route.

### 2.5 Leftover 2.0.6 zip untouched

| Probe | Value |
| --- | --- |
| `packages/…v2.0.6.zip.sha256` | `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d` |
| `dist/…v2.0.6.zip.sha256` | same |
| Frozen digest (architect / prior reviews) | same `55406ff2…` |
| `packages/…v2.0.5.zip.sha256` | still `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` |
| Local annotated tag object `v2.0.6` | still `8e7c5b67a1f9e51cc2f15586b72e0dceff7f8ee1` (peel `e75f3a1`) |
| Local annotated tag object `v2.0.5` | still `7f85f7be43fd8008f6af522a967ebc5268a481d1` (peel `7c0ae75`) |
| New artifact | `…v2.0.7.zip` sidecar `ec48d317…` — different name, not an overwrite |

Default packager output is `dist/adaptive-grok-build-pro-v2.0.7.zip`. A 2.0.7 pack does not rewrite the 2.0.6 path. Dist 2.0.6 sidecar still matches the published digest, so 2.0.6 was not rebuilt after the identity bump.

This reviewer did not re-hash zip bytes (no shell). Sidecar + frozen digest + distinct 2.0.7 output path are the evidence.

---

## 3. Authz, secrets, PII, tenant isolation, irreversible actions

### Authz

Named gates `scope_and_design_approval` and `production_action_approval` are recorded in `evidence/human-approval.md` from «делай новый релиз и ПУБЛИКУЙ НАХУЙ ЗАЕБАЛ», scoped to: VERSION 2.0.7, package, tag, push `origin/main`, push tag, GitHub Release. Do not retag 2.0.6. No GitHub Actions. Do not print secrets.

`git commit` is not a `PRODUCTION_INVOCATIONS` prefix. The identity ship is in scope of the user ruling and the null `write_agent` (controller owns it).

`approvals.json` still holds **expired** leftover-push rows (`37754a2d61eb` production, `5babcf924709` external-write, reason “push 2.0.6 leftover bugfixes to origin/main”, window 19:26–19:41Z). Those must **not** be reused for tag/push/`gh release create`. Last mile still needs a **fresh** `grok_approve.py production --reason "publish v2.0.7 tag and GitHub Release"` if an agent terminal runs it.

This report does **not** authorize last mile.

### Secrets

No new credential path. No token in CHANGELOG / RELEASE-NOTES / runbook. Packager exclusions unchanged. Local `.env` unopened. Runtime approvals not packed.

### PII

No customer data, no email harvest, no coverage/SaaS upload. Public MIT product tree. Git author email lives in `.git` (excluded from the zip).

### Tenant isolation

CLI installed into consumer git trees. No multi-tenant data plane. A new versioned zip does not read or write another customer’s tree.

### Irreversible actions

None executed by this ship, and none by this reviewer.

| Forbidden | Observed |
| --- | --- |
| `git tag` / `git tag -f` / retag `v2.0.6` | no `v2.0.7` tag; `v2.0.6` object still `8e7c5b67…` |
| `git push` / force-push | `origin/main` still `11da31a` |
| `gh release create` / delete / edit | no local tag to attach; GitHub list has no `v2.0.7` |
| Rebuild / overwrite 2.0.6 zip | digest still `55406ff2…` |
| Touch `v2.0.5` | tag + digest unchanged |
| `.github/workflows` / Dependabot | still absent |
| `pyproject.toml` | still absent |
| Read `.env` | not read |

Rollback of a *failed later* last mile remains v2.0.7-only (`rollback.md`). Do not touch `v2.0.6` / `v2.0.5`. No force-push.

---

## Findings

No blocking findings.

| ID | Severity | Item | Disposition |
| --- | --- | --- | --- |
| S1 | Residual (accepted) | 2.0.7 zip embeds `engineering/changes/**` on disk at pack time, including this route’s analysis | Same class as `11da31a` shipping `3c1039`. No secret values. Do not expand excludes here. |
| S2 | Residual (accepted) | Zip namelist / 2.0.6 bytes not independently unzipped or re-hashed (no shell on this release route) | Packager + shipped-zip test + matching sidecars. Same bar as prior release reviews. |
| S3 | Residual (process) | Expired 19:26 leftover-push tokens still on disk | Wrong reason. Do not reuse. Mint a 2.0.7 production row only if last mile runs. |
| S4 | Historical, not this ship | Five failed Actions runs on v2.0.4 / v2.0.5 | Workflows banned since `e75f3a1`. This commit does not restore them. |
| S5 | Observational | Public `/releases` HTML errored and did not list v2.0.6; `/actions` and path 404s were usable | Last mile has not published 2.0.7. `release_reviewer` owns live Latest/title after publish. |

---

## Recommendation

**PASS.** Treat `02376cc` as an authorized 2.0.7 identity+zip ship: no GHA, no `pyproject.toml`, no packed secrets, leftover 2.0.6 zip digest frozen, VERSION 2.0.7.

Do not retag 2.0.6. Do not rebuild the 2.0.6 zip. Do not add GitHub Actions. Do not add `pyproject.toml`. Do not read `.env`. Do not publish from this review.
