# Release review — `9d97f8dcae59` (v2.0.12 bootstrap, zip re-review)

Reviewer: `release_reviewer` (read-only except this report). Write owner: **none** (parent).
Change: `engineering/changes/20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8`
Route: `9d97f8dcae59` · intent=`release` · risk=`high` · profiles=`base`
Skills: `/adaptive-delivery`, `release-readiness`.

Assigned: re-review after FAIL on zip contents. Working tree **2.0.12**; zip rebuilt without `pin.env` / leftover; `grok_verify` **PASS**. Remaining process: commit, rebase onto `origin/main` `8a2f95c`, push feat, `gh pr ready 2`, `gh pr merge --rebase`, tag/release merged SHA. Do **not** require App-owned check (named bootstrap). `dist/RELEASE-NOTES.md` will be written from CHANGELOG **2.0.12** at release time.

Fetched: 2026-08-23 (local tree + GitHub PR/release APIs). Did not read `.env`, PEMs, pin hex, or credential stores. Did not push, merge, tag, deploy, or mint a grant.

**PASS.** **GO** to proceed with commit → rebase onto `origin/main` `8a2f95c` → push **only** `feat/trust-ci-control-plane` → `gh pr ready 2` → `gh pr merge 2 --rebase` → tag/release the **merged** SHA.

Prior FAIL (zip member `build/adaptive-trust-ci-pin.env` + leftover `20260817-вычисти*` in archive digest `c3416b99…`) is **cleared**. Rebuilt zip digest `28c40c32751b3b30be05c1191e18dace4ced26f01b951c84e99370608609cc4a` has 0 `pin.env`, 0 leftover, 0 `build/`, 0 PEM, 0 `.github/workflows`. Inner identity is product **2.0.12** / Trust CI **2.1.0**.

This is **not** GO to merge current HEAD `bb143d3` (committed identity still **2.0.11**). Ship commit first.

| Check (assigned) | Result |
| --- | --- |
| VERSION / README H1 / CHANGELOG / packages zip / `test_manifest_package` = 2.0.12 | **PASS** (working tree + zip inner `VERSION`) |
| Trust CI identity stays 2.1.0; examples stay `REPLACE_WITH_*` | **PASS** |
| Rollback via `publish-v2.0.12.md` (v2.0.12-only withdraw) | **PASS** |
| `grok_verify --mode pr` | **PASS** (180 tests OK; coverage 74% at ratchet) |
| No GitHub Actions | **PASS** (`.github/` absent locally and 404 on GitHub; zip has none) |
| Do not retag `v2.0.11` | **PASS** (frozen; no local/GitHub `v2.0.12` tag) |
| Artifact hygiene (no leftover dir / pin env in zip) | **PASS** — rebuilt zip is clean |
| Do not require App-owned check | **PASS** — named bootstrap exception; check absent, not forged |
| Proceed to commit+push+rebase-merge | **GO** (after explicit ship commit; not current `bb143d3`) |

Do not push, merge, tag, deploy, or run `gh` from this review.

## Verdict

| Gate | Result |
| --- | --- |
| Identity surfaces (working tree) | **PASS.** `VERSION` = `2.0.12`; README H1 = `# Adaptive Grok Build Pro v2.0.12`; CHANGELOG top = `## 2.0.12 — 2026-08-23`; `packages/README.md` has the v2.0.12 zip row; `tests/test_manifest_package.py` pins `'2.0.12'` and the on-disk zip inner `VERSION` is `2.0.12`. |
| Trust CI identity | **PASS.** `trust-ci/pyproject.toml` `version = "2.1.0"`; `__init__.py` `__version__ = "2.1.0"`; API/User-Agent strings stay `2.1.0`. Example image pins remain `REPLACE_WITH_*` in `trust-ci/.env.example` and `trust-ci/config/policy.example.json` sandbox image. Product 2.0.12 is not Trust CI 2.1.0. |
| Artifact / provenance | **PASS.** Zip + sidecar digest `28c40c32751b3b30be05c1191e18dace4ced26f01b951c84e99370608609cc4a` (packages/ and dist/ match). 936 members, all under `adaptive-grok-build-pro/`. Inner CHANGELOG starts `## 2.0.12 — 2026-08-23`. Packer now excludes `build/` in `EXCLUDED_PARTS`, skips `*-pin.env` and paths containing `20260817-`. Prior dirty digest `c3416b99…` is superseded; do not ship the old bytes. |
| Frozen prior release | **PASS.** Annotated `v2.0.11` peels `c54fd01588eb343eeecde7302fee514bf3e6090d`. GitHub Latest is **Adaptive Grok Build Pro v2.0.11** (published 2026-08-17T00:13:29Z). Local 2.0.11 zip sidecar `37957cb220f97cb89046b5191074f49f6530658176a9cde66a20e4c9c519ec79` matches the GitHub asset digest. No `v2.0.12` tag or GitHub Release. |
| Quality gate | **PASS** on fingerprint `5df57dac05cbd62d5d16e510c9b777d60241ad6952363468874f1124c30165e8` at 2026-08-23T21:54:22Z. ruff pass, bandit pass, secret-scan 0, python-unittest **180 OK**, coverage **74%** (ratchet 74). Writing this report stale-dates that fingerprint. |
| Rollback | **PASS** for a published `v2.0.12` only, via the runbook. Change-package `rollback.md` is still the empty template. |
| Observability | **PASS** for this product shape (GitHub Release card), with the notes file rewritten at release time. Trust CI Prometheus metrics exist in-tree and are **not live** this slice. |
| Bootstrap merge of **current** PR head `bb143d3` | **no-go** — committed identity is still 2.0.11. |
| Bootstrap merge **after** ship commit + rebase onto `8a2f95c` + feat push + `gh pr ready 2` | **GO.** Named exception; do not wait for `adaptive-trust-ci/verified@*`. |
| Product mutation by this agent | **PASS / empty.** Overwrote only this report. No product edits. No `.env`. No publish. |

## 1. Identity (working tree vs committed vs published)

| Surface | Value |
| --- | --- |
| Working `VERSION` | `2.0.12` |
| `HEAD` | `bb143d3b64644f905c8f5a21868fd3be7139e17e` `feat/trust-ci-control-plane` — **committed `VERSION` is still `2.0.11`** |
| `origin/main` | `8a2f95c4893e89297fbce39a9b0c0c78610f14ed` «Update mistakes.md» — **not an ancestor of HEAD** (`1` behind / `200` ahead) |
| Merge-base with `v2.0.11` | `c54fd01` |
| PR #2 | open **draft**, head `bb143d3`, GitHub `base.sha` still `c54fd01`, `mergeable_state=unstable` |
| GitHub Latest | `v2.0.11` on `main` / peel `c54fd01` |
| README current-state | claims published GitHub Release is already `v2.0.12` — true only after last mile |
| K16 graph | 16 nodes, 120 `---` edges, **complete** |

`CHANGELOG` 2.0.12 correctly records PR-only / bootstrap exception / Trust CI **2.1.0** / no GitHub Actions. It does not revive `git push origin main` as current procedure. `AGENTS.md` and `QUICKSTART.md` forbid `git push origin main`. Historical `CHANGELOG` 2.0.11 and `decisions.md` 2026-08-17 still document the old push-main contract; that is history, not this ship.

## 2. Verification

`.grok-stack/runtime/receipts/9d97f8dcae59/verification.json` (tree fingerprint `5df57dac…`, 2026-08-23T21:54:22Z):

| Check | Status |
| --- | --- |
| git-diff-check | pass |
| secret-scan | pass (0 potential secrets) |
| contract-structure | pass |
| sql-safety | pass |
| ruff | pass |
| bandit | pass |
| python-unittest | **pass** — Ran 180 tests in 46.939s — OK |
| coverage | pass (74%) |
| overall | **pass** |

`last-fingerprint.json` matched that receipt before this report. Local receipts are preflight, not merge authority. Receipt `changed_files` still *lists* the untracked leftover `20260817-вычисти*` directory because it is on disk; that is not a zip member and must not enter the index.

## 3. Rollback — adequate for v2.0.12 withdraw

Authority is [`engineering/runbooks/publish-v2.0.12.md`](../../../../engineering/runbooks/publish-v2.0.12.md), not the empty change-package `rollback.md`.

```bash
gh release delete v2.0.12 --yes
git push origin :refs/tags/v2.0.12
git tag -d v2.0.12
```

- Deletes **only** `v2.0.12`. Leaves `v2.0.11` on `c54fd01` / zip `37957cb2…`.
- No force-push. No `git tag -f`. No `git push origin main`.
- Does **not** roll back a rebase-merge of ~200 Trust CI commits off `main`. That recovery is a later named revert/forward-fix, not this runbook. Acceptable while `main` is unprotected and this is the first publication of that history — residual, not a no-go.
- Trust CI host deploy / branch-protect are out of this slice; `engineering/runbooks/trust-ci-rollout.md` stays unused.

Runbook last-mile still prints `python3 scripts/package_stack.py`. The ship zip is already rebuilt and clean (`28c40c32…`). Do not rerun the packager unless the tree changes after this review. After merge, tag the **merged** SHA; copy zip to `packages/` only if a post-merge pack is required.

## 4. Observability

No APM required for the product zip. After GO last mile, confirm:

| Signal | Expected |
| --- | --- |
| `/releases/latest` title | `Adaptive Grok Build Pro v2.0.12` |
| Notes first heading | `## 2.0.12 — 2026-08-23` (not current `dist/RELEASE-NOTES.md` 2.0.11) |
| Tag peel | exact **merged** SHA (not `bb143d3`, not `c54fd01`) |
| Zip asset | digest `28c40c32…` unless a post-merge repack produces a new matching sidecar |
| `v2.0.11` | still exists, peel `c54fd01`, zip `37957cb2…` |
| `.github/workflows/` | still absent |
| `adaptive-trust-ci/verified@*` | **absent** (bootstrap; do not invent) |

Today Latest is still `v2.0.11`. Current `dist/RELEASE-NOTES.md` still starts `## 2.0.11 — 2026-08-17` and names `git push origin main`. That file is gitignored scratch. **GO** for commit/merge without rewriting it now. **no-go** to pass the current file as `--notes-file`. Copy the CHANGELOG `## 2.0.12` section into `dist/RELEASE-NOTES.md` immediately before `gh release create`.

Trust CI `metrics.py` / Prometheus text exist in-tree. Host dashboards, alerts, and the App-owned check are **not** this release. Support visibility for 2.0.12 is the GitHub Release card plus README current-state.

## 5. Remaining risk (do not expand scope)

1. **Leftover `engineering/changes/20260817-вычисти*` is still untracked (14 files).** Packer now skips `20260817-` and the rebuilt zip has **none**. Fail-closed if those paths appear in `git diff --cached`. Never `git add -A`.
2. **`build/adaptive-trust-ci-pin.env` still exists on disk** (gitignored `build/`, mode 0600, 396 bytes). Not opened. Not in the zip. Do not force-add.
3. **Ship commit has not happened.** Merge of `bb143d3` would still publish committed identity **2.0.11**. Sequence requires the 2.0.12 commit first.
4. **Rebase onto `8a2f95c` is required.** `origin/main` is a GitHub-UI `mistakes.md` hook-dump. Keep the working 2026-08-23 grant-invalidation entry; drop the dump. Do not rebase `--onto` past `8a2f95c`.
5. **PR #2 is draft** (`mergeable_state=unstable`). `gh pr ready 2` before merge. GitGuardian Security Checks = **failure** is not Trust CI and is not a required check while `main` is unprotected. Do not wait for it. Do not forge `adaptive-trust-ci/verified@*`. Do not `--admin`. Combined status `pending`, 0 statuses; only GitGuardian exists.
6. **Bootstrap exception is recorded** in `decisions.md` and README current-state. User text «мое прямое указание» is the named `scope_and_design_approval` + `production_action_approval`. That exception authorizes rebase-merge **without** a live App check; it does not authorize `git push origin main`, squash, merge-commit, MCP `github__merge_pull_request`, host deploy, or `branch-protect`.
7. **Merge method is `--rebase` only.** `main` has zero merge commits. `--squash` / `--merge` are no-go. If GitHub rejects rebase, stop.
8. **Grants.** Protected-path batch before the ship commit; production `git-push-branch` / `pull-request-merge` / `git-push-tag` / `github-release` after, bound to feat ref, PR #2 URL, `v2.0.12`, exact HEAD/fingerprint. First mutation invalidates the grant (`mistakes.md` 2026-08-23). Wildcard `*` forbidden. `--profile release` is wrong (omits `pull-request-merge`).
9. **Coverage is exactly 74%.** Pass, no margin.
10. **Change-package `release.md` / `rollback.md` / `test-plan.md` are empty templates.** Operational last mile is the publish runbook + architect sequence, not those files.
11. **Include the packer fix in the ship commit.** `.grok-stack/adaptive_grok/manifest.py` (and the new `test_scratch_build_pin_env_and_leftover_change_are_not_packaged`) were not on the original architect include list; they are now required. `tests/test_protected_write.py` is still dirty — explicit `git add` only.
12. **On-disk `evidence/security-review.md` is still the previous FAIL** against zip `c3416b99…`. This release review does not substitute that receipt. Parent must have `security_reviewer` PASS on digest `28c40c32…` before treating route `required_evidence` complete. If that parallel review finds a new blocker, stop.
13. **No root `pyproject.toml` / `requirements.txt` / `setup.py`.** Keep absent. `trust-ci/pyproject.toml` is the service.
14. **`policy.example.json` `holdout.digest` is one committed 64-hex** for `trust-ci/holdout.example` (already on HEAD). Not a registry pin. Example sandbox image stays `REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`.

## 6. GO / NO-GO

| Act | Decision |
| --- | --- |
| Merge PR #2 at current head `bb143d3` | **no-go** |
| `git push origin main` | **no-go** |
| `gh pr merge 2 --squash` / `--merge` / MCP merge | **no-go** |
| Retag / `-f` / delete / edit `v2.0.11` | **no-go** |
| Forge `adaptive-trust-ci/verified@*` / `compose up` / `branch-protect` / GitHub Actions | **no-go** |
| Wait for App-owned check before bootstrap merge | **no-go** (named exception; check cannot exist yet) |
| Use current `dist/RELEASE-NOTES.md` as GitHub notes | **no-go** until rewritten from CHANGELOG 2.0.12 |
| This reviewer executing last mile | **no-go** |
| Keep Trust CI service identity 2.1.0 | **GO** |
| Commit rebuilt zip `28c40c32…` (no pin.env / leftover members) plus 2.0.12 identity, explicit paths only | **GO** |
| Rebase onto `origin/main` `8a2f95c`, keep working `mistakes.md` | **GO** |
| Push **only** `feat/trust-ci-control-plane` | **GO** |
| `gh pr ready 2` then `gh pr merge 2 --rebase` | **GO** after the ship commit is on the PR head |
| Tag/release the **merged** SHA as `v2.0.12` | **GO** after merge; notes from CHANGELOG 2.0.12 |

Parent sequence (controller/human only; not this agent):

```bash
# explicit git add (never -A). Include packer fix + clean zip.
# fail-closed if cached names match 20260817|pin.env|.pem|trust-ci/runtime|trust-ci/env/[^. ]|.github/workflows
git add VERSION CHANGELOG.md README.md packages/README.md \
  packages/adaptive-grok-build-pro-v2.0.12.zip \
  packages/adaptive-grok-build-pro-v2.0.12.zip.sha256 \
  tests/test_manifest_package.py tests/test_structure.py tests/test_toolchain.py \
  tests/test_protected_write.py \
  engineering/runbooks/publish-v2.0.12.md engineering/runbooks/trust-ci-rollout.md \
  decisions.md mistakes.md QUICKSTART.md \
  .grok-stack/config/toolchain.json .grok-stack/adaptive_grok/manifest.py \
  trust-ci/README.md \
  engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec \
  engineering/changes/20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8
git commit -m "Release v2.0.12: Trust CI source, K16 docs, toolchain scanners"

git fetch origin
git rebase origin/main   # keep working mistakes.md
git push origin feat/trust-ci-control-plane
gh pr ready 2
gh pr merge 2 --rebase
git fetch origin
git checkout main
git merge --ff-only origin/main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
# write dist/RELEASE-NOTES.md from CHANGELOG ## 2.0.12, then:
git tag -a v2.0.12 "$(git rev-parse HEAD)" -m "v2.0.12"
git push origin v2.0.12
gh release create v2.0.12 \
  packages/adaptive-grok-build-pro-v2.0.12.zip \
  packages/adaptive-grok-build-pro-v2.0.12.zip.sha256 \
  --title "Adaptive Grok Build Pro v2.0.12" \
  --notes-file dist/RELEASE-NOTES.md
```

## What this review is not

- Not this agent publishing, merging, or tagging.
- Not a security review (parallel `security_reviewer`; on-disk report is still the prior FAIL).
- Not a second `package_stack` run.
- Not a retag of `v2.0.11`.
- Not a Trust CI host go-live.
- Did not read `.env` or pin hex. Did not push, merge, or deploy.

## Stop

**PASS.**

- Working-tree identity **2.0.12** and Trust CI **2.1.0** match. Rebuilt zip `28c40c32…` is clean. `grok_verify` **PASS** (180 / 74%). Rollback runbook is v2.0.12-only. Observability plan is the GitHub Release card; notes from CHANGELOG 2.0.12 at release time.
- **GO** for this bootstrap remaining process: explicit 2.0.12 ship commit, rebase onto `8a2f95c`, push feat only, `gh pr ready 2`, `gh pr merge --rebase`, tag/release the merged SHA. Do not require an App-owned check.
- **no-go:** merge current `bb143d3`, `git push origin main`, retag 2.0.11, GHA, forged App check, current `dist/RELEASE-NOTES.md`, this agent publishing.
