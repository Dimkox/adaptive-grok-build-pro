# Analysis — task_analyst

Change: `20260816-ban-gha-rebuild-and-verify-2-0-6-publish-9fd274`  
Route: `9fd2741e5d1b` · intent=`feature` · risk=`low` · write=`general_implementer`  
Analysis wave: `repo_explorer` / `task_analyst` / `architect` / `docs_researcher`  
Reviews after implementation: `code_reviewer` + `test_reviewer`  
Evidence kinds: `verification`, `code_review`, `test_review`  
Human gates on this route: **none**  
Narrow question: **What is the outcome, what is out of scope, and what checkboxes close this change?**

Read-only. No application-code edits. No `.env`. No push / tag / merge / deploy from this agent.

---

## Ruling (one screen)

User: **never GitHub Actions**; **rebuild and verify on unpublished 2.0.6**; **then finish the GitHub Release**. Stay `VERSION` **2.0.6**. Do not add another CI vendor.

This **supersedes** `864726` (tag existing `549f29d`, no rebuild). That SHA still ships `.github/workflows/adaptive-grok.yml` and Dependabot `github-actions`. Tagging it would publish GHA. Forbidden.

This **does not implement** leftover draft `39b13f` (empty stub from the same outburst). Active package is **this** `9fd274`.

| Layer | Meaning |
| --- | --- |
| Product | This repo and the installer do not ship GitHub Actions. Local `grok_verify --mode pr` is the only gate. |
| Identity | Stay unpublished **2.0.6**. Do **not** bump to 2.0.7. Rewrite the unpublished 2.0.6 notes. Leave `## 2.0.5` historical text alone. |
| Package | Rebuild `packages/adaptive-grok-build-pro-v2.0.6.zip*` **after** the ban. Digest `b34af685…` is stale. |
| Last mile | Authorized by prior «делай всё полностью вместе с релизом», but the tag target is the **post-ban successor of `549f29d`**, not `549f29d`. Leave `v2.0.5` untouched. |

Adaptive-delivery §7 still says print-only last mile. User-approved scope is source of truth #1 and this package already names last mile as in-scope. Policy still requires a **fresh** `grok_approve.py production` token before `git push` / `gh release create` (the only rows in `approvals.json` are expired 2.0.5 tokens). Do not use MCP `create_release`.

---

## Current facts (do not treat as done)

| Item | Today |
| --- | --- |
| `VERSION` / README H1 | `2.0.6` / `Adaptive Grok Build Pro v2.0.6` |
| Local `HEAD` / `refs/heads/main` | `549f29da1c4ff44ba44d8388c294fd5dd29bfd81` — `Release v2.0.6: ruff, bandit, coverage, dependabot` |
| `origin/main` + GitHub `main` | `7c0ae7573535ddd0cfe3800f81278991ced81584` (v2.0.5) |
| Local tags | `v2.0.0`–`v2.0.5`. **No** `refs/tags/v2.0.6` |
| GitHub Latest | **v2.0.5** on `7c0ae75` (published 16 Aug 16:10). `/releases/tag/v2.0.6` absent |
| Tracked zip + digest | `packages/` and `dist/` both `b34af685c8d277aafcfbc4aa3f393286b12af2b092e5efa2b74ab6f5ba41b610` |
| `.github/workflows/adaptive-grok.yml` | Present. Verify + conditional package. Byte-identical to template |
| `.github/dependabot.yml` | Present. `package-ecosystem: github-actions` weekly |
| Template | `.grok-stack/templates/ci/github-actions.yml` (same 40 lines) + README that still offers optional GHA / self-host vendors |
| `install_into --with-ci` | Copies template → `.github/workflows/adaptive-grok.yml` |
| Tests that **require** GHA | `test_with_ci_preserves_unrelated_workflow` (asserts copy); `test_root_workflow_equals_template`; `test_template_package_job_is_conditional_and_has_no_publish`; `test_workflow_installs_quality_tools` |
| CHANGELOG / `dist/RELEASE-NOTES.md` §2.0.6 | Still advertise Dependabot-for-GHA and “CI fail-closed after `pip install`” |
| Prior ship `ec0388` | `ready` on `549f29d` (quality contour **with** GHA) |
| Sibling `864726` | Draft last-mile of `549f29d` as-is. **Stale.** |
| Sibling `39b13f` | Draft stub. Do not implement. |
| `approvals.json` | Two rows, expired `2026-08-16T16:24:55Z`, reason “publish v2.0.5…”. **Dead.** |
| `pyproject.toml` / `requirements.txt` / `setup.py` | Absent. Must stay absent. |
| This package | `draft`. Receipts dir `9fd2741e5d1b/` empty. |

`included_files()` does **not** exclude `.github/` or `.grok-stack/templates/ci/`. Today’s 2.0.6 zip therefore contains the workflow, Dependabot, and the GHA template. A rebuild on `549f29d` cannot satisfy “no GHA files”.

---

## Outcome

A consumer of this product, and this repository itself, never receives GitHub Actions from Adaptive Grok. Verification is local: `make verify` / `python3 scripts/grok_verify.py --mode pr`. Unpublished 2.0.6 is rebuilt under that rule and GitHub Latest becomes **v2.0.6** on the ban commit. Previous Latest **v2.0.5** remains a historical release.

---

## In scope

1. Delete shipped GHA: `.github/workflows/adaptive-grok.yml` and `.github/dependabot.yml`. No leftover workflow YAML under `.github/`.
2. Stop shipping a copyable workflow: delete (or neutralize so it is not a workflow file) `.grok-stack/templates/ci/github-actions.yml`. Packager will otherwise put it in the zip.
3. Rewrite `.grok-stack/templates/ci/README.md` to: never GHA; `make verify` / `grok_verify --mode pr` only. Do **not** add Woodpecker / Forgejo / GitLab / Drone / Jenkins templates.
4. `install_into --with-ci` → `SystemExit` (forbidden), **no** directory create, **no** copy, even with `--force` / `--dry-run`. Unrelated consumer workflows stay untouched.
5. Invert / replace the four tests that currently lock GHA in. Add tests that lock the ban (repo, installer, zip/manifest).
6. Rewrite unpublished `CHANGELOG` / `dist/RELEASE-NOTES.md` §2.0.6: drop Dependabot-for-GHA and hosted-CI fail-closed; state the ban. Do not invent `## 2.0.7`. Do not rewrite `## 2.0.5`.
7. Record the ban in `engineering/decisions.md` (one short entry).
8. Rebuild zip via `python3 scripts/package_stack.py` and copy to `packages/`. In-zip `VERSION` is `2.0.6`. No `.github/workflows`. No Dependabot. No GHA template YAML.
9. `python3 scripts/grok_verify.py --mode pr` PASS on the post-ban tree (ruff, bandit, unittest, coverage).
10. After reviews + receipts: annotated tag `v2.0.6` on the **post-ban** commit, `git push origin main`, `git push origin v2.0.6`, `gh release create` with the **new** zip + sha256 and updated notes.

## Out of scope

- Another CI vendor or hosted runner.
- `pyproject.toml` / `requirements.txt` / `setup.py`.
- Retag, rebuild, or delete `v2.0.5`.
- Force-push. `git push --force`. Rewriting `549f29d`.
- Bumping `VERSION` off `2.0.6`.
- New product features, Dobryakov dump, Bucket C scanners/SaaS.
- Removing GHA from **already-installed** consumer repos (installer does not delete unmanaged `.github/` files; `--with-ci` simply must not write one).
- Implementing sibling `39b13f` or tagging `549f29d` per `864726`.
- MCP `create_release` / `create_or_update_ref` as a second publisher.

---

## Acceptance checkboxes

Close the change only when all of these are true on the **same** tree.

### A. Ban (product)

- [ ] Repo has **no** `.github/workflows/*.yml` (directory absent or empty of workflow files).
- [ ] Repo has **no** `.github/dependabot.yml`.
- [ ] Zip / `included_files()` contain **no** `.github/workflows/…` and **no** Dependabot YAML.
- [ ] Zip does **not** contain a copyable GitHub Actions workflow (today that means delete `.grok-stack/templates/ci/github-actions.yml`, not leave it as a fossil).
- [ ] `python3 scripts/install_into.py <tmp> --with-ci` exits **nonzero**, message is forbidden/never-GHA, and `<tmp>/.github/workflows/adaptive-grok.yml` is **not** created.
- [ ] `--with-ci --force` and `--with-ci --dry-run` also write nothing.
- [ ] `--with-ci` against a target that already has an unrelated workflow leaves that file byte-identical and still writes no `adaptive-grok.yml`.
- [ ] Default install (no `--with-ci`) still does not create `.github/workflows`.
- [ ] Tests lock the above. The four current GHA-positive tests are gone or inverted. Existing non-CI installer tests still pass.
- [ ] Template README (if the `templates/ci/` dir remains) says never GHA; local `make verify` / `grok_verify --mode pr` only. No new vendor file.
- [ ] Unpublished §2.0.6 notes no longer claim Dependabot-for-GHA or hosted CI. `VERSION` file is still exactly `2.0.6`.
- [ ] No `pyproject.toml` / `requirements.txt` / `setup.py`. `detect_repo` on this tree stays `kind=generic`. `grok_verify` still emits `python-unittest`.

### B. Rebuild + verify (2.0.6 identity)

- [ ] `python3 scripts/grok_verify.py --mode pr` **PASS** (ruff, bandit, unittest, coverage fail-under).
- [ ] `python3 scripts/package_stack.py` writes `dist/adaptive-grok-build-pro-v2.0.6.zip` + sibling `.sha256`.
- [ ] Tracked copy updated: `packages/adaptive-grok-build-pro-v2.0.6.zip*`.
- [ ] In-zip `adaptive-grok-build-pro/VERSION` is `2.0.6`.
- [ ] New sha256 **≠** `b34af685c8d277aafcfbc4aa3f393286b12af2b092e5efa2b74ab6f5ba41b610`.
- [ ] `v2.0.5` zip digest and GitHub Release `v2.0.5` are unchanged.

### C. Last mile (after A+B, reviews, and a live production token)

- [ ] Annotated tag `v2.0.6` peels to the **post-ban** commit (successor of `549f29d`), **not** `549f29d`.
- [ ] `origin/main` is that same SHA (fast-forward from `7c0ae75`).
- [ ] Remote tag `v2.0.6` exists.
- [ ] GitHub Latest is `v2.0.6` with the **rebuilt** zip + matching sha256.
- [ ] Release `v2.0.5` still exists.

Order is load-bearing: **ban + tests → rebuild zip → `grok_verify --mode pr` → independent reviews / receipts → fresh `grok_approve.py production` → tag successor → push `main` → push tag → `gh release create`.** Do not tag before the ban commit exists. Do not push `main` while it still contains GHA if a later ban commit is the ship.

---

## Flows

### Primary

1. Write failing tests for “no workflows / `--with-ci` refuses / zip has no GHA”.
2. Delete workflow + Dependabot + template YAML; refuse `--with-ci`; rewrite unpublished 2.0.6 notes + CI README; add the decisions entry.
3. Confirm the four old GHA-positive tests no longer assert the old contract.
4. `package_stack` + copy to `packages/`.
5. `grok_verify --mode pr`.
6. `code_reviewer` + `test_reviewer` on the actual diff. Record `verification` / `code_review` / `test_review`.
7. Transition this package to `ready` **before** binding receipts (`decisions.md` 2026-08-14).
8. Last mile on the successor SHA only.

### Alternate / error

| Case | Expected |
| --- | --- |
| Someone passes `--with-ci` | Nonzero exit, no file, no `.github/` created if it did not exist |
| Target already has `existing.yml` | File unchanged; no `adaptive-grok.yml` |
| Target already has our old `adaptive-grok.yml` | `--with-ci` still refuses; we do not overwrite or delete unmanaged consumer files in this slice |
| `grok_verify` red after deletions | Return to the same write owner. Do not record reviews on a failing tree |
| Last mile before ban commit | Stop. Publishing `549f29d` is a failed acceptance |
| Tag `v2.0.6` already minted on `549f29d` (race) | Do **not** `git tag -f`. Stop for a named decision. Today the tag is absent, so this is only a residual |
| Push / `gh` without live production token | PreToolUse denies. Mint a new 15-minute token; do not reuse expired 2.0.5 rows |

Empty/loading: N/A (no UI). Permissions: production invocations stay gated. No API/event/schema migration. No backfill.

---

## Constraints

| Kind | Rule |
| --- | --- |
| Compatibility | `--with-ci` becomes a hard refuse. That is the feature. Default install path is unchanged. |
| Version | `VERSION` stays `2.0.6`. This is a replacement of an **unpublished** identity, not a new patch. |
| Packaging marker | Do not add `pyproject.toml` (flips `detect_repo`, can skip unittest). |
| CI vendors | Delete GHA. Do not substitute another vendor. |
| v2.0.5 | Immutable. |
| Git | Fast-forward only. No force-push. |
| Secrets | Do not read `.env` / keys. Do not print tokens. |
| Last mile | User-authorized, policy-gated. Fresh `grok_approve.py production`. No MCP publish. |
| Receipts | Bind after the last change-package write. Any later edit invalidates them. |
| Write owner | Only `general_implementer`. This agent does not implement. |

---

## Conflicts and bounded rulings

| Conflict | Ruling |
| --- | --- |
| `864726` “tag `549f29d`, no rebuild” vs this prompt | **This prompt wins.** `549f29d` ships GHA. Last mile moves to the successor. Digest `b34af685…` is not the ship asset. |
| `ec0388` acceptance required Dependabot `github-actions` | Superceded for unpublished 2.0.6. Ruff / Bandit / Coverage **stay**. Dependabot / hosted workflow **go**. |
| Adaptive-delivery §7 print-only vs «делай всё полностью вместе с релизом» | Last mile is in scope **after** A+B+reviews. Execute only with a live production token. Print-only already left Latest on 2.0.5. |
| `864726` human-approval named SHA `549f29d` | Authorization to **publish 2.0.6** stands; the SHA does not. Publishing GHA would violate the newer user rule. |
| Template README currently lists Woodpecker / GitLab / … | Docs may say “wire the same local commands if you already have CI”. **Do not** add vendor files. |
| Keep template YAML but refuse `--with-ci`? | **No.** “No GHA files” + zip rebuild would still ship `github-actions.yml`. Delete the YAML. |
| Parallel draft `39b13f` | Ignore. One write owner on `9fd274`. |
| Runbook `publish-v2.0.6.md` still says agents must not tag/push/`gh` | Standing printer. This route’s user scope is the exception, same pattern as cd8a96. Do not expand the runbook into a new CI vendor. |
| CHANGELOG 2.0.4/2.0.5 mention this-repo GHA | Historical. Do not rewrite. Only unpublished §2.0.6 changes. |

No named human gate on this route. No stop for design approval. Architect records the file list; implementer owns the vertical.

---

## Tests the write owner must land

P0 (ban):

1. Repo has no `.github/workflows/*.yml` and no `.github/dependabot.yml`.
2. `--with-ci` raises `SystemExit`, writes no workflow, preserves an unrelated `existing.yml`.
3. `included_files()` / rebuilt zip: no `.github/workflows`, no Dependabot, no `templates/ci/github-actions.yml`.
4. Existing installer tests that do not use `with_ci` still pass.

P0 (quality, already required by `pr`):

5. `python3 scripts/grok_verify.py --mode pr` PASS.

P1 (identity):

6. Zip member `adaptive-grok-build-pro/VERSION` == `2.0.6`.
7. Characterization: default install still does not create `.github/`.

P0 last mile (manual / `gh`, after publish):

8. Latest is `v2.0.6` on the successor SHA; `v2.0.5` remains; zip digest matches the rebuilt sibling.

Remove or invert:

- `tests/test_installer.py::test_with_ci_preserves_unrelated_workflow` (today asserts the copy).
- `tests/test_deploy.py::test_root_workflow_equals_template`
- `tests/test_deploy.py::test_template_package_job_is_conditional_and_has_no_publish`
- `tests/test_deploy.py::test_workflow_installs_quality_tools`

Do not add a second unittest discover in CI — there will be no CI.

---

## Rollout / rollback / observability

Rollout: one commit on `main` (ban + notes + rebuilt zip), then tag/push/release. No feature flag. No migration.

Success signals: `grok_verify --mode pr` pass; `--with-ci` nonzero; GitHub Latest `tag_name=v2.0.6`; asset digest equals `packages/…v2.0.6.zip.sha256`.

Rollback of a published `v2.0.6` only:

```bash
gh release delete v2.0.6 --yes
git push origin :refs/tags/v2.0.6
git tag -d v2.0.6
```

Restore GHA only by reverting the ban commit. No force-push. Leave `v2.0.5`.

---

## Suggested vertical for `general_implementer`

1. Failing tests first (`feature-workflow` / adaptive-delivery §4).
2. Delete GHA files + refuse `--with-ci` + invert old tests.
3. Docs: unpublished §2.0.6, template README, `decisions.md`.
4. `package_stack` + copy to `packages/`.
5. `grok_verify --mode pr`.
6. Stop. Reviews next. Last mile only after `ready` + live production token.

Do not fold leftover `864726` / `39b13f` / `ad4090` paperwork into the ship commit beyond what this package needs.

---

## Residual risks (not blockers)

- A consumer who already copied `adaptive-grok.yml` keeps running GHA until they delete it. Out of scope.
- If someone tags `549f29d` as `v2.0.6` before this lands, last mile cannot `-f`. Unlikely: tag is absent now.
- Expired production tokens will surprise a controller that assumes `864726` approval is still live. Mint new.
- Coverage fail-under 74 and ruff/bandit stay; deleting CI must not regress those local checks.

No open product question that requires asking the user. Facts above are recovered from the tree, the active package, siblings `ec0388` / `864726` / `39b13f`, and public Latest still being v2.0.5.
