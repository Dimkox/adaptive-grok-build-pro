# Security review — `70b284082a16`

**GO** for last mile, path-limited commit only.

Route: `70b284082a16` (intent=`release`, risk=`high`, `write_agent: null`)  
Change: `20260816-system-reminder-background-subagent-01a00cea-6b8-70b284`  
Object reviewed: **live working tree** after the controller 2.0.10 identity bump (uncommitted on top of published `v2.0.9` / `f72c0fc`). Not a stale 2.0.8 / 2.0.9 analysis.  
Reviewer: `security_reviewer` (read-only; in `allowed_agents`)  
Inspected: `/adaptive-delivery` + `/release-readiness`, this change package + analysis + `human-approval.md` + `rollback.md` + `publish-v2.0.10.md`, local refs, identity files, packager / `manifest.py` / `policy.py` / `.gitignore` / tests, zip sidecars, leftover dirty `engineering/changes/*`, `approvals.json` metadata only, public GitHub HTML for `.github`, `pyproject.toml`, `/releases/latest`, `/releases/tag/v2.0.9`, `/releases/tag/v2.0.10`.

No application-code edits. `.env` was not read. No push, merge, tag, retag, zip rebuild, or `gh release` from this agent.

---

## Verdict in one screen

The live tree is an **unpublished 2.0.10 identity+zip** sitting on dirty `main`. `HEAD` / `origin/main` are still published `f72c0fc` (`v2.0.9`). Last mile is a **new** commit + annotated `v2.0.10` + push + `gh release create`. Do **not** retag `v2.0.9`. Do **not** `git add -A`.

| Required confirmation | Result |
| --- | --- |
| VERSION 2.0.10 | **PASS.** `VERSION` and `__version__` are `2.0.10`. README H1, Current-state identity, CHANGELOG `## 2.0.10`, packages/README 2.0.10 row, and test pins match. |
| In-zip VERSION 2.0.10 | **PASS.** `packages/…v2.0.10.zip` exists. Sidecar `607827bd9899141d2a6a8d7fe03c55be82fdc47cd60631d253de7d96d5a7794f` matches `dist/`. `grok_verify --mode pr` PASSed 192 tests including `test_included_files_and_shipped_zip_have_no_github_actions` (opens that zip, asserts in-zip `VERSION == 2.0.10`). |
| No GitHub Actions | **PASS.** No local `.github/`. No `dependabot.yml`. No `github-actions.yml`. No `runs-on:` YAML. GitHub `main/.github` is 404. |
| No `pyproject.toml` | **PASS.** Absent locally and 404 on GitHub `main`. `requirements.txt` / `setup.py` also absent. |
| No secrets in the new zip | **PASS.** Packager still drops `.env` / keys / runtime / `err.log`; tests lock that; tree secret-scan is clean; verify `secret-scan` = `0 potential secrets`. |
| Do not retag `v2.0.9` | **PASS so far.** Local annotated tag object still `020921e7ac069bbbabe3686c3af74678fabd9cce`. GitHub Latest / `/releases/tag/v2.0.9` still peels to `f72c0fc`. `/releases/tag/v2.0.10` is 404. Local tags stop at `v2.0.9`. |
| Frozen leftover zips | **PASS.** 2.0.9 sidecar still `b9d2398ac6c4863c72476bf069d405eb2938ccefa16c39cdf9c0b9f43dfa2f4b`. 2.0.8 sidecar still `42a08851…`. Tag object `v2.0.8` still `695ee791…`. |
| Leftover uncommitted `engineering/changes/*` | **Constraint, not a leak.** Verification dirty list includes sibling packages `06a59f`, `8fe260`, `e4afbb`, `e61f9d`, `f1bdb9`. Those must **not** enter the 2.0.10 commit. Path-limited add only. |

**Authz** is «релиз сделай» plus standing Release when green plus `evidence/human-approval.md`, scoped to identity 2.0.10 + last mile. **Secrets / PII / tenant isolation** are not in play. **Irreversible** last-mile actions have **not** run.

---

## 1. What the live tree is

| Probe | Value |
| --- | --- |
| Local `refs/heads/main` / `HEAD` | `f72c0fc2bb27de5dee67f799517f71cd678eb068` |
| Parent of that SHA | `02842413509dc98eaaf104e27f212888f9449826` (`v2.0.8`) |
| `refs/remotes/origin/main` | same `f72c0fc` — **2.0.10 not committed, not pushed** |
| Local tag `v2.0.9` | annotated object `020921e7…` → peels to `f72c0fc`. **Do not move.** |
| Local tag `v2.0.10` | **absent** |
| GitHub Latest | Adaptive Grok Build Pro **v2.0.9** on `f72c0fc` (16 Aug 23:40) |
| GitHub `/releases/tag/v2.0.10` | **404** |
| Route `base_commit` | `f72c0fc` |
| `write_agent` | **null** — controller owns identity + last mile |
| Verify receipt | `.grok-stack/runtime/receipts/70b284082a16/verification.json` **pass** at `2026-08-16T23:48:54+00:00`, fingerprint `f1299cbf…`, 192 tests OK |

This is the required **new** identity after published `v2.0.9`. Tagging `f72c0fc` as `v2.0.10` would dual-tag the 2.0.9 SHA. Last mile must **commit first**, then tag the **new** SHA.

Identity surfaces on the dirty tree:

| Surface | Live value |
| --- | --- |
| `VERSION` | `2.0.10` |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.10"` |
| `README.md` H1 | `# Adaptive Grok Build Pro v2.0.10` |
| `README.md` Current state | Identity **2.0.10**; Published GitHub Release is `v2.0.10` (becomes true after last mile) |
| `CHANGELOG.md` top | `## 2.0.10 — 2026-08-16` inserted above frozen `## 2.0.9` |
| `packages/README.md` | 2.0.10 row added; 2.0.9–2.0.0 kept |
| Tests | `test_version_is_2_0_10_and_github_actions_are_absent`; zip pin `2.0.10` |
| Runbook | `engineering/runbooks/publish-v2.0.10.md` (CLI last mile). `publish-v2.0.9.md` not rewritten. |
| Zip | `packages/adaptive-grok-build-pro-v2.0.10.zip` + sidecar `607827bd…` (matches `dist/`) |
| Scratch notes | `dist/RELEASE-NOTES.md` = CHANGELOG §2.0.10 only (gitignored) |

`deploy.py` still prints `--title "Adaptive Grok Build Pro v{version}"` from live `VERSION`. Not edited.

---

## 2. Leftover uncommitted `engineering/changes/*` (the last-mile trap)

`grok_verify --mode pr` `changed_files` on this tree is **not** “identity + this package + zip”. It also lists sibling session dirt:

| Package | Dirty paths (must stay uncommitted) |
| --- | --- |
| `20260816-user-query-…-06a59f` | 5 evidence files (analysis + `security-review.md` + `release-review.md`) written **after** `v2.0.9` already shipped |
| `20260816-user-query-…-8fe260` | analysis + reviews + `state.json` — leftover 2.0.8-era security review of `83673bb` |
| `…-e4afbb` | 3 analysis files |
| `…-e61f9d` | analysis + `implementation.md` + reviews + `state.json`. That `implementation.md` says it is **intentionally uncommitted** |
| `…-f1bdb9` | 3 analysis files |
| `decisions.md` | new top heading “next SKU is 2.0.10”. Not leftover-package dirt. Architect path-limited set **omits** it. Adding it is not a secret leak; using it as an excuse for `git add -A` **is** the leak class |

Also dirty and **in** scope: this `70b284` package, the eight identity/pin surfaces, `engineering/runbooks/publish-v2.0.10.md`, `packages/…v2.0.10.zip*`.

`git add -A` or `git add engineering/changes/` would commit the sibling dirt into the 2.0.10 ship. Those files contain **no secret values** (token *kinds* and historical review prose only), but they are **not** this product identity. Architect Phase F is the authority:

```text
VERSION
.grok-stack/adaptive_grok/__init__.py
README.md
CHANGELOG.md
packages/README.md
packages/adaptive-grok-build-pro-v2.0.10.zip
packages/adaptive-grok-build-pro-v2.0.10.zip.sha256
tests/test_structure.py
tests/test_manifest_package.py
engineering/runbooks/publish-v2.0.10.md
engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/
```

Do **not** add other `engineering/changes/*`. Do not add `dist/`. Do not add `.grok-stack/runtime/` (would pack approvals metadata into git; packager already drops runtime from the zip).

The short runbook `engineering/runbooks/publish-v2.0.10.md` prints pack / tag / push / `gh release create` and **omits** the commit. Following it against current `HEAD` would annotate `f72c0fc` as `v2.0.10` (dual-tag of the 2.0.9 SHA). Last mile is the user-specified sequence: **commit identity + this package + zip, then tag the new SHA**.

`included_files()` walks the working tree, so sibling change-package markdown **is already inside** `packages/…v2.0.10.zip` even if it stays uncommitted. Same accepted class as 2.0.7 / 2.0.8 / 2.0.9. No secret values. Do not expand excludes on this route. Do not `git add` those siblings to “match the zip”.

---

## 3. Secrets in the new zip

`.env` exists on the operator machine (parent listing / prior reviews). **Not opened.** `.gitignore` and `policy.py` `DEFAULT_SECRET_READ` still cover `.env`, `.env.*`, `*.pem` / `*.key` / `*.p12` / `*.pfx`, `id_rsa`, `id_ed25519`, `credentials*`, `secrets/**`.

Packager (`manifest.py`):

- `EXCLUDED_FILES` includes `.env`, `err.log`, `MANIFEST.sha256` (re-embedded then root unlinked)
- `_is_secret_path` drops `.env`, `.env.*` (except `.env.example`, which is absent), and key suffixes
- `.grok-stack/runtime/*` except `.gitkeep` is dropped (so `approvals.json` is not packed)
- `.zip` / `.sha256` members are dropped (the 2.0.10 archive does not nest prior zips)
- `dist/` is an excluded part

Locked by `test_archive_excludes_dotenv_and_keys`, `test_archive_excludes_err_log`, and the shipped-zip GHA / in-zip VERSION asserts. Verify `secret-scan` on this dirty tree: `0 potential secrets`.

Workspace text scan (not `.env`):

- No live `github_pat_` / `ghp_` / `gho_` / `BEGIN … PRIVATE KEY` / `AKIA…` values (hits are historical review prose saying those were absent)
- No `token|secret|password|api_key = "…"` matches except test fixtures (`tests/test_verification_doctor.py` fake `'abcde'*5`) and historical review prose
- Only fixture mention: `tests/test_manifest_package.py` `GIT_FINE_GRAIN_TOKEN=should-not-pack` (unquoted; not packed from a real `.env`)

Zip bytes were not unzipped here (binary; no shell on this release route). Evidence is packager + passing shipped-zip test + matching `packages/`/`dist/` sidecars + tree scan. Same bar as prior release reviews.

---

## 4. Production last-mile commands

Authorized sequence (commit **before** tag; path-limited add above):

```bash
git commit -m "Release v2.0.10: published identity after v2.0.9"
git tag -a v2.0.10 -m "v2.0.10"
git push origin main
git push origin v2.0.10
gh release create v2.0.10 \
  packages/adaptive-grok-build-pro-v2.0.10.zip \
  packages/adaptive-grok-build-pro-v2.0.10.zip.sha256 \
  --title "Adaptive Grok Build Pro v2.0.10" \
  --notes-file dist/RELEASE-NOTES.md
```

`dist/RELEASE-NOTES.md` is CHANGELOG §2.0.10 only. Title must be exactly `Adaptive Grok Build Pro v2.0.10`.

Forbidden in this last mile:

| Action | Why |
| --- | --- |
| `git tag -f v2.0.9` / any touch of `v2.0.9` | published Latest; peel must stay `f72c0fc` |
| `git tag -a v2.0.10` on `f72c0fc` (no new commit) | dual-tags the 2.0.9 SHA |
| `git push --force` / `git push -f` | policy `DESTRUCTIVE_COMMANDS`; rewrites shared history |
| `gh release create v2.0.9` / `gh release edit v2.0.9` | mutates the published card |
| GitHub Actions / `pyproject.toml` / `requirements.txt` / `setup.py` | banned; flips repo detect |
| `git add -A` / `git add engineering/changes/` | scoops leftover sibling packages |
| Rebuilding `packages/…v2.0.9.zip*` | frozen digest `b9d2398a…` |
| Reading `.env` | secret-read policy |

`git push` and `gh release create` are `PRODUCTION_INVOCATIONS`. `git tag` is not. If an agent terminal runs the push / `gh` lines, mint a **fresh** `python3 scripts/grok_approve.py production --reason "publish v2.0.10 tag and GitHub Release"`. Do **not** reuse:

| id | reason (wrong for this ship) | window |
| --- | --- | --- |
| `a6cc4f6d9775` | “last mile v2.0.8 from 0284241” | expired `23:48:56Z` |
| `ba29880c29cc` | “publish v2.0.9 from f72c0fc” | expires `23:54:55Z`; **wrong SKU** |

Named gates are recorded in `evidence/human-approval.md`. This report authorizes the path-limited last mile; it does not execute it.

Review reports dirty the tree. After this file (and `release-review.md`) land under `70b284/evidence/`, they are inside the allowed add directory. Architect: re-pack **once** if those reports stay, then re-run `python3 scripts/grok_verify.py --mode pr` before binding receipts. A re-pack still walks leftover sibling markdown into the zip; that remains accepted residual.

---

## 5. Rollback

`rollback.md` and the runbook are correct and sufficient:

```bash
gh release delete v2.0.10 --yes
git push origin :refs/tags/v2.0.10
git tag -d v2.0.10
```

- Delete **Release + `v2.0.10` tag only**.
- Do **not** force-push `main`.
- Do **not** delete `v2.0.9` (object `020921e7…` / peel `f72c0fc`).
- GitHub Latest then falls back to **v2.0.9**.
- If `main` already contains the 2.0.10 identity commit: leave it. Forward-fix is 2.0.11. Do not rewrite published history.

`git push origin :refs/tags/v2.0.10` is still a `git push` (production invocation). Needs a fresh production row if an agent runs rollback.

---

## 6. Authz, secrets, PII, tenant isolation, irreversible actions

### Authz

Named gates `scope_and_design_approval` and `production_action_approval` are recorded from «релиз сделай» plus standing «всегда если все тесты прошли и все ок делай новый релиз» and prior «полное согласие». Scope: VERSION 2.0.10, zip, commit, push `origin/main`, annotated tag `v2.0.10`, GitHub Release titled `Adaptive Grok Build Pro v2.0.10`. Do not retag 2.0.9. No GitHub Actions. Do not print secrets.

`git commit` is not a `PRODUCTION_INVOCATIONS` prefix. The identity ship is in scope of the user ruling and the null `write_agent` (controller owns it).

### Secrets

No new credential path. No token in CHANGELOG / RELEASE-NOTES / runbook / this package. Packager exclusions unchanged. Local `.env` unopened. Runtime approvals not packed and must not be committed.

### PII

No customer data, no email harvest, no coverage/SaaS upload. Public MIT product tree. Git author email (`bpall@mail.ru`) lives in `.git` (excluded from the zip). Change-package directory names carry user-prompt fragments; sibling leftovers stay uncommitted.

### Tenant isolation

CLI installed into consumer git trees. No multi-tenant data plane. A new versioned zip does not read or write another customer’s tree.

### Irreversible actions

None executed by this identity bump, and none by this reviewer.

| Forbidden | Observed |
| --- | --- |
| `git tag` / `git tag -f` / retag `v2.0.9` | no `v2.0.10` tag; `v2.0.9` object still `020921e7…`; GitHub Latest still `f72c0fc` |
| `git push` / force-push | `origin/main` still `f72c0fc` |
| `gh release create` / delete / edit | `/releases/tag/v2.0.10` is 404 |
| Rebuild / overwrite 2.0.9 zip | digest still `b9d2398a…` |
| Touch `v2.0.8` | tag `695ee791…` + digest `42a08851…` unchanged |
| `.github/workflows` / Dependabot | still absent locally and 404 on GitHub |
| `pyproject.toml` | still absent locally and 404 on GitHub |
| Read `.env` | not read |

---

## Findings

No blocking findings **if** last mile uses the path-limited add.

| ID | Severity | Item | Disposition |
| --- | --- | --- | --- |
| S1 | **Required constraint** | Dirty sibling `engineering/changes/{06a59f,8fe260,e4afbb,e61f9d,f1bdb9}` would be scooped by `git add -A` / `git add engineering/changes/` | Path-limited add of identity + **this** `70b284` package + zip only. Session evidence is not product. |
| S2 | Residual (accepted) | 2.0.10 zip already embeds `engineering/changes/**` on disk at pack time, including sibling leftovers | Same class as 2.0.9. No secret values. Do not expand excludes. Do not commit siblings to “match the zip”. |
| S3 | Residual (accepted) | Zip namelist / 2.0.9 bytes not independently unzipped or re-hashed (no shell on this release route) | Packager + shipped-zip test (PASS, in-zip VERSION 2.0.10) + matching sidecars. |
| S4 | Residual (process) | Short runbook omits `git add` / `git commit`; tagging current `HEAD` would dual-tag `f72c0fc` | Last mile is commit-new-SHA then `git tag -a v2.0.10`. Architect Phase F. |
| S5 | Residual (process) | Disk production rows `a6cc4f6d9775` (2.0.8) and `ba29880c29cc` (2.0.9) are expired and/or wrong SKU | Do not reuse. Mint a 2.0.10 production row only if an agent runs `git push` / `gh release create`. |
| S6 | Residual (docs) | README Current state already claims “Published GitHub Release is `v2.0.10`” before the card exists | Becomes true after last mile. `release_reviewer` owns live Latest/title after publish. |
| S7 | Residual (scope) | `decisions.md` gained a 2.0.10 heading; architect path-limited set omits it | No secrets. Optional extra. Not leftover-package dirt. Never `git add -A` to include it. |
| S8 | Historical, not this ship | Failed Actions runs on v2.0.4 / v2.0.5 | Workflows banned since `e75f3a1`. This tree does not restore them. |

---

## Last-mile GO / NO-GO

**GO** for:

1. Path-limited commit of identity + this `70b284` package + `packages/…v2.0.10.zip*` (architect Phase F list).
2. Annotated tag `v2.0.10` on **that new commit**, not on `f72c0fc`.
3. `git push origin main` and `git push origin v2.0.10` (no `--force`).
4. `gh release create v2.0.10 … --title "Adaptive Grok Build Pro v2.0.10" --notes-file dist/RELEASE-NOTES.md`.

**NO-GO** if any of: `git add -A`; adding sibling `engineering/changes/*`; retag / edit `v2.0.9`; tag `f72c0fc` as `v2.0.10`; force-push; GitHub Actions; `pyproject.toml`; reading `.env`; reusing a 2.0.8 / 2.0.9 production token.

Rollback of a failed last mile remains v2.0.10-only. Latest falls back to `v2.0.9` on `f72c0fc`.

**GO**
