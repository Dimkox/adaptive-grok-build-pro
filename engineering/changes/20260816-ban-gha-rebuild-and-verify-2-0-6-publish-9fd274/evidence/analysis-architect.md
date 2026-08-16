# Analysis — architect

Change: `20260816-ban-gha-rebuild-and-verify-2-0-6-publish-9fd274`  
Route: `9fd2741e5d1b` · intent=`feature` · risk=`low` · write=`general_implementer` · reviews=`code_reviewer`+`test_reviewer` · gates=`[]` · evidence=`verification`,`code_review`,`test_review`  
User: never GitHub Actions; rebuild and verify on 2.0.6; finish unpublished Latest.

Read-only design. No application-code edits from this agent. No `.env`. No push / tag / merge / `gh release`.

Narrow question: exact vertical for `general_implementer` so this repo and the installer stop shipping GitHub Actions, stay on unpublished 2.0.6, pass local `grok_verify --mode pr`, rebuild the zip, then last-mile that new SHA.

---

## Ruling (one screen)

**Delete live GHA + Dependabot + the copyable workflow template. `--with-ci` is a hard `SystemExit` (word `forbidden`) before any write. Local `make verify` / `python3 scripts/grok_verify.py --mode pr` is the only gate. No replacement CI SaaS. Stay `VERSION` 2.0.6. Rebuild the zip. Tag the successor of `549f29d`, not `549f29d` itself.**

This user rule is source-of-truth #1. It supersedes:

| Prior | What it said | Now |
| --- | --- | --- |
| `ec0388` / CHANGELOG 2.0.6 | Dependabot `github-actions`; CI fail-closed after `pip install` | Those surfaces die. Ruff/Bandit/Coverage stay in `grok_verify` (local skip-if-missing). |
| `864726` last-mile design | Tag existing `549f29d`, no rebuild | **Do not execute.** That SHA still ships `.github/workflows/adaptive-grok.yml` and Dependabot. |
| Sibling `39b13f` | Same outburst, hollow package | **Do not implement there.** This change owns the work. |

| In | Out |
| --- | --- |
| Delete `.github/workflows/adaptive-grok.yml`, `.github/dependabot.yml`, `.grok-stack/templates/ci/github-actions.yml` | Any new workflow, Dependabot, CodeQL, or hosted runner file |
| Rewrite `.grok-stack/templates/ci/README.md` to never-GHA + local verify only | Woodpecker / Forgejo / GitLab / Drone / Jenkins / Circle as a recommended replacement |
| `--with-ci` → `SystemExit` containing `forbidden`; no workflow path created | Silent ignore of the flag; argparse-only reject (tests call `install(..., with_ci=True)`) |
| Tests lock absence + fail-closed flag | Keep `test_root_workflow_equals_template` / quality-tool / package-job locks |
| `engineering/decisions.md` 2026-08-16 entry | New ADR file; `pyproject.toml` |
| Rewrite **current** `## 2.0.6` CHANGELOG / `dist/RELEASE-NOTES.md` bullets | Bump to 2.0.7; rewrite historical 2.0.4 GHA sentence |
| Rebuild `packages/adaptive-grok-build-pro-v2.0.6.zip*` after the ban commit | Touch `packages/…-v2.0.5.*`; retag `v2.0.5` |
| Last mile **after** `ready` + live `grok_approve production` | Architect/analysis agents executing tag/push/`gh`; force-push; MCP `create_release` |

`human_gates` is empty → implementer proceeds after this design. Last mile is still policy-gated (`git push` / `gh release create` need a live production token for agent Bash). Human terminal may skip the token. Dead 2.0.5 rows in `approvals.json` are not reusable.

---

## 1. Current facts (inspected this wave)

| Item | Value |
| --- | --- |
| Local `HEAD` / `refs/heads/main` | `549f29da1c4ff44ba44d8388c294fd5dd29bfd81` — `Release v2.0.6: ruff, bandit, coverage, dependabot` |
| `origin/main` | `7c0ae7573535ddd0cfe3800f81278991ced81584` (published v2.0.5) |
| Local tags | `v2.0.0`–`v2.0.5`. **No** `refs/tags/v2.0.6` |
| `VERSION` | `2.0.6` (unpublished) |
| Current zip digest | `b34af685c8d277aafcfbc4aa3f393286b12af2b092e5efa2b74ab6f5ba41b610` — **will change** after this vertical |
| Live GHA | `.github/workflows/adaptive-grok.yml` (40 lines; byte-identical to template) |
| Dependabot | `.github/dependabot.yml` — `package-ecosystem: github-actions` weekly |
| Template | `.grok-stack/templates/ci/github-actions.yml` (same 40 lines) |
| Template README | still calls GHA “optional”; names Woodpecker/GitLab/Drone/Jenkins |
| Installer | `install()` lines 119–127 copy template → `.github/workflows/adaptive-grok.yml` when `with_ci` |
| `.grok-stack` copy | `MANAGED_DIRS` includes `.grok-stack`, so the template yml **ships to every consumer even without `--with-ci`** |
| Tests that will go red | `test_deploy.py` three CI tests; `test_installer.py::test_with_ci_preserves_unrelated_workflow` |
| `grok_verify` | no GHA branch. `_ruff` / `_bandit` skip-if-CLI-missing. Coverage fail-under 74 in `pr`/`release` |
| This change | `draft`. Sibling `39b13f` also `draft` (empty). `864726` still `draft` (do not run) |
| Approvals | two rows, expired `16:24:55Z`, reason “publish v2.0.5”. **Dead.** |

`.github/` currently holds only the workflow and Dependabot. After both deletes the directory is empty; git does not track empty dirs. That is the desired end state — no `.github/` in the tree.

---

## 2. Why the template yml must die

`--with-ci` is not the only ship path. `install_into.iter_source_files` walks all of `.grok-stack` except `runtime/`. Leaving `.grok-stack/templates/ci/github-actions.yml` means every `install_into` target receives a ready-to-enable Actions workflow. That violates “this repo **and the installer** do not ship GitHub Actions.”

Ruling: delete the yml. Keep the directory with a rewritten README only. Installer then copies a ban notice, not a workflow.

Do not add an installer exclude-list for that one file as a substitute. Delete the bytes.

---

## 3. `--with-ci` contract

Keep the flag. Old scripts and muscle memory must fail closed, not look like an unknown argument.

| Input | Behavior |
| --- | --- |
| `install(..., with_ci=True)` | `raise SystemExit(<msg>)` **before** any `mkdir` / `copy2` / `merge_agents` |
| `with_ci=True` + `dry_run=True` | same `SystemExit`; no “WOULD COPY” |
| `with_ci=True` + `force=True` | same `SystemExit` |
| `with_ci=False` (default) | unchanged stack install; never creates `.github/workflows/` |
| argparse `--with-ci` | still parsed; help says forbidden; `main()` passes through to `install()` |

Message **must** contain the substring `forbidden` (requirements + tests). Point at the real gate:

```
GitHub Actions is forbidden. Use local `make verify` / `python3 scripts/grok_verify.py --mode pr`.
```

Raise at the top of `install()`, not only inside the current `if with_ci:` block after the managed-file loop. A late raise would still write the stack and then die — acceptable for “no workflow”, but a start-of-function raise is the smaller, testable contract: `--with-ci` is a rejected invocation.

Update `parser.add_argument('--with-ci', …)` help from “Install a generic GitHub Actions verification workflow.” to the forbidden sentence.

Do not remove the flag. Do not make it a no-op that prints and continues (return code 0 would let wrapper scripts think CI was installed).

---

## 4. Docs (bounded)

### 4.1 `.grok-stack/templates/ci/README.md` (required)

Replace the current “optional GitHub Actions / self-host Woodpecker…” text. Whole file should say, in substance:

- This product never uses GitHub Actions.
- Do not add `.github/workflows/` or Dependabot.
- Source of truth:

```bash
make doctor
make verify
python3 scripts/grok_verify.py --mode pr
```

Do **not** list other CI vendors. “No new CI SaaS” includes not advertising a replacement. A consumer who already has their own automation can run the same commands; that is not a product surface and does not get a vendor name in this README.

### 4.2 `engineering/decisions.md` (required)

New entry, ≤3 sentences, dated 2026-08-16, after the Ruff/`pyproject.toml` entry:

> ## 2026-08-16 — Never GitHub Actions
>
> Local `make verify` / `python3 scripts/grok_verify.py --mode pr` is the only quality gate. Do not add `.github/workflows/`, Dependabot, `--with-ci` copies, or another CI SaaS. `install_into --with-ci` is `SystemExit` / forbidden.

### 4.3 `CHANGELOG.md` §2.0.6 and `dist/RELEASE-NOTES.md` (required, same identity)

Stay on `## 2.0.6 — 2026-08-16`. Rewrite the two stale bullets:

- Drop “CI fail-closed after `pip install`”.
- Replace “Dependabot for GitHub Actions only” with “No GitHub Actions / Dependabot; local `grok_verify --mode pr` is the gate. `--with-ci` is forbidden.”

Keep Ruff / Bandit / Coverage / skip-unless-signal Semgrep bullets. Do not invent `## 2.0.7`. Leave the historical 2.0.4 “This-repo GitHub Actions…” line alone.

`package_stack.py` does not generate `dist/RELEASE-NOTES.md`. Refresh that gitignored scratch from the updated 2.0.6 section before last mile (`gh release create --notes-file`).

### 4.4 Root `README.md`

No GHA mention today. Do not expand scope. Optional one clause under License is not required.

---

## 5. Tests — write these first (they must fail on `549f29d`)

One write owner. TDD. Do not keep tests that require the workflow to exist.

### 5.1 `tests/test_installer.py`

Replace `test_with_ci_preserves_unrelated_workflow` with something that:

1. Creates `target/.github/workflows/existing.yml`.
2. Calls `install(..., with_ci=True)` (and a second case with `dry_run=True`).
3. Asserts `SystemExit`.
4. Asserts `'forbidden'` in the exception message (or `str(ctx.exception)`).
5. Asserts `existing.yml` bytes unchanged.
6. Asserts `target/.github/workflows/adaptive-grok.yml` does **not** exist.

Default `install(..., with_ci=False)` must still install the stack and must **not** create `adaptive-grok.yml`. Existing tests already cover the no-flag path; add one explicit `assertFalse` if cheap.

### 5.2 `tests/test_deploy.py` — `DeploySourceAndCiTests`

Delete or invert all three:

| Remove | Replace with |
| --- | --- |
| `test_root_workflow_equals_template` | neither `.github/workflows/adaptive-grok.yml` nor `.grok-stack/templates/ci/github-actions.yml` exists |
| `test_template_package_job_is_conditional_and_has_no_publish` | no `.github/workflows/*.yml` under ROOT; no `.github/dependabot.yml` |
| `test_workflow_installs_quality_tools` | `templates/ci/README.md` exists and contains `never` / `GitHub Actions` ban plus `grok_verify.py --mode pr` (or `make verify`) |

Keep `test_prepare_sources_do_not_execute_publish_commands` (unrelated, still valid).

### 5.3 Zip / VERSION lock

`included_files()` already omits missing paths. After deletes, the packager will not put workflows in the zip. Still lock it:

- `test_structure.py` or `test_manifest_package.py`: ROOT `VERSION` is `2.0.6`; no path under ROOT matching `.github/workflows/*.yml`; no `.github/dependabot.yml`; no `templates/ci/github-actions.yml`.
- After rebuild, if `packages/adaptive-grok-build-pro-v2.0.6.zip` exists, its namelist contains `adaptive-grok-build-pro/VERSION` with body `2.0.6` and no member containing `.github/workflows/`. Run that assertion in the same module so `grok_verify` fails if someone copies an old zip.

Do not add a test that `github-actions.yml` **content** lacks `gh release` — the file must be gone.

---

## 6. Implementation order for `general_implementer`

Exactly one write owner. No second implementer. Do not edit Bitrix core, `.env`, or `packages/…-v2.0.5.*`.

1. **Failing tests first** (§5). Confirm they fail on the current tree.
2. **Delete** the three files in §Ruling. Leave `templates/ci/README.md`.
3. **`install_into.py`**: start-of-`install` `SystemExit`; help text; no copy block (delete lines 119–127, do not leave a dead `if with_ci` that copies).
4. **Docs**: template README, `decisions.md`, CHANGELOG §2.0.6.
5. Focused unittest on the two test modules.
6. `python3 scripts/grok_verify.py --mode pr` (alias `make verify`). This is the quality profile `base` plus the hardcoded Python contour. Expect `ruff` / `bandit` / `python-unittest` / `coverage` to run if those CLIs are on PATH (they are on this tree).
7. Refresh `dist/RELEASE-NOTES.md` from CHANGELOG §2.0.6.
8. Rebuild:

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.6.zip* packages/
```

9. Confirm in-zip `VERSION` is `2.0.6` and namelist has no `.github/workflows` and no `dependabot.yml` and no `github-actions.yml`.
10. Stop. Do **not** tag / push / `gh` in the implement step.
11. Transition package `implementing` → `verifying` → `reviewing` → **`ready` first**, then official verify + `grok_review` receipts (fingerprint includes `state.json`; ready-then-receipts is the 2026-08-14 decision).
12. Independent `code_reviewer` + `test_reviewer` on the actual diff.

`VERSION` file is not touched. Identity stays 2.0.6. Digest `b34af685…` is expected to change; that is the point of the rebuild.

---

## 7. Last mile (after `ready`, not this report)

`864726` is void. Tag the **new** ban+rebuild commit (the successor of `549f29d`).

Print-only runbook `engineering/runbooks/publish-v2.0.6.md` is still the command shape. `grok_deploy.py` will print `package_stack` + `cp` again; those are already done in step 8 — humans/controller may skip them if the tracked `packages/` siblings match `dist/`.

Order is load-bearing:

1. `python3 scripts/grok_approve.py production --reason "publish v2.0.6 without GitHub Actions"` (agent Bash only; 15 min TTL).
2. Preconditions: `origin/main` still `7c0ae75` or a fast-forward of it; local `v2.0.5^{}` still `7c0ae75`; **no** local/remote `refs/tags/v2.0.6`; `VERSION` is `2.0.6`; zip has no workflows.
3. `git tag -a v2.0.6 <NEW_SHA> -m "v2.0.6"`
4. `git push origin <NEW_SHA>:refs/heads/main`
5. `git push origin v2.0.6`
6. `gh release create v2.0.6 packages/adaptive-grok-build-pro-v2.0.6.zip packages/adaptive-grok-build-pro-v2.0.6.zip.sha256 --notes-file dist/RELEASE-NOTES.md`

Who executes: controller or a human terminal after the write owner returns `ready`. Not architect. Not reviewers. Not `39b13f` / `864726`.

No-go: remote already has `v2.0.6`; `v2.0.5` moved; non-ff `main`; zip still contains a workflow. Then stop. No `-f`.

Rollback (already in this package): delete only `v2.0.6` release+tag. Restore GHA only by reverting the ban commit. Leave `v2.0.5`.

---

## 8. File ledger

| Path | Action |
| --- | --- |
| `.github/workflows/adaptive-grok.yml` | **Delete** |
| `.github/dependabot.yml` | **Delete** |
| `.grok-stack/templates/ci/github-actions.yml` | **Delete** |
| `.grok-stack/templates/ci/README.md` | **Rewrite** (never GHA; local verify only) |
| `scripts/install_into.py` | **Edit** (`SystemExit` first; drop copy block; help text) |
| `tests/test_installer.py` | **Edit** (invert `--with-ci`) |
| `tests/test_deploy.py` | **Edit** (absence locks) |
| `tests/test_structure.py` and/or `tests/test_manifest_package.py` | **Edit** (no workflows; VERSION 2.0.6; zip namelist) |
| `engineering/decisions.md` | **Append** 2026-08-16 entry |
| `CHANGELOG.md` | **Edit** §2.0.6 bullets only |
| `dist/RELEASE-NOTES.md` | **Refresh** (gitignored; last mile) |
| `packages/adaptive-grok-build-pro-v2.0.6.zip*` | **Rebuild + overwrite** |
| `VERSION` | **Do not touch** |
| `packages/…-v2.0.5.*` | **Do not touch** |
| `.grok-stack/adaptive_grok/verification.py` | **Do not touch** (already the gate) |
| `ruff.toml` / `bandit.yaml` / `.coveragerc` | **Do not touch** |
| Sibling `…-39b13f/` / `…-864726/` | **Do not implement** |

---

## 9. Risks

| Risk | Mitigation |
| --- | --- |
| Tagging `549f29d` by habit (864726 muscle memory) | Last mile pins the **new** SHA after rebuild; preconditions refuse an existing `v2.0.6` |
| Consumer trees that already have `adaptive-grok.yml` from an older `--with-ci` | Out of scope. New installs do not write one. Do not remotely delete customer workflows |
| `install_into --with-ci` in published docs / old blog posts | Flag stays; fails with `forbidden` + the local command |
| Coverage / ruff fail after deleting files | Unlikely (those paths are not in `QUALITY_PY_PATHS`). If `grok_verify` fails, fix the test/doc edit — do not weaken fail-under 74 |
| Empty `.github/` leftover as an untracked dir | Harmless; do not add a `.gitkeep` there |
| Dual draft packages (`39b13f`, `864726`) | This route is the authority (`active-change.json` points here) |

Residual: GitHub will stop running Actions on this repo once `main` has no workflow file. That is the intended signal, not a regression.

---

## 10. What this agent did not do

No application edits. No package rebuild. No `git push` / `git tag` / `gh release`. No read of `.env`. Independent reviews wait for the implementer tree.

This report is design. It is not a verification or review receipt.
