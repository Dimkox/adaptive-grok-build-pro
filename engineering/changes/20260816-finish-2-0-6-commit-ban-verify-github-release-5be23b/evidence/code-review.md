# Code review — finish 2.0.6 commit ban

Change: `20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b`  
Route: `5be23b16d59f` · reviewer: `code_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-16  
Subject: `e75f3a1b92e247279fbb6210d46715a90cf7895c`

**PASS.** I would not block.

I did not trust `evidence/implementation.md`. Inspected git refs, the index, the live tree at `e75f3a1`, surrounding installer/tests/docs, the change-package contracts, and the shipped zip sidecar / namelist strings. This reviewer session has no shell, so there is no live `git show` / `sha256sum` / unzip. Equivalents are listed below. No `.env`. No push / tag / merge / `gh release`.

---

## Verdict against the requested checks

| # | Check | Result |
| --- | --- | --- |
| 1 | No GHA workflow / Dependabot / template yml | **PASS** |
| 2 | `--with-ci` forbidden | **PASS** |
| 3 | `VERSION` 2.0.6 | **PASS** |
| 4 | Zip digest `55406ff2…` | **PASS** |
| 5 | No `pyproject.toml` | **PASS** |
| 6 | Residual risk / would you block? | Residuals only. **No block.** |

Would I block? **No.**

---

## What was actually inspected

```text
# refs
read .git/HEAD                     → ref: refs/heads/main
read .git/refs/heads/main          → e75f3a1b92e247279fbb6210d46715a90cf7895c
read .git/refs/remotes/origin/main → 7c0ae7573535ddd0cfe3800f81278991ced81584
read .git/COMMIT_EDITMSG           → Release v2.0.6: ban GitHub Actions, rebuild zip
read .git/logs/HEAD                → 549f29d → e75f3a1  commit: Release v2.0.6: ban GitHub Actions, rebuild zip
read .git/refs/tags/               → v2.0.0 … v2.0.5 only; no v2.0.6
read .git/refs/tags/v2.0.5         → 7f85f7be43fd8008f6af522a967ebc5268a481d1  (unchanged)

# contracts
engineering/changes/…-5be23b/{brief,architecture,requirements,tasks,test-plan,release,rollback}.md
engineering/changes/…-5be23b/evidence/{analysis-*,human-approval,implementation}.md
engineering/changes/…-9fd274/evidence/implementation.md  (prior on-disk ban, not this commit)

# product
VERSION  CHANGELOG.md  README.md  packages/README.md  dist/RELEASE-NOTES.md
.grok-stack/templates/ci/README.md
scripts/install_into.py
.grok-stack/adaptive_grok/{deploy,repo}.py
engineering/decisions.md
engineering/runbooks/publish-v2.0.6.md
.gitignore

# tests
tests/test_installer.py
tests/test_deploy.py
tests/test_structure.py
tests/test_manifest_package.py

# artifacts
packages/adaptive-grok-build-pro-v2.0.6.zip.sha256
packages/adaptive-grok-build-pro-v2.0.5.zip.sha256
dist/adaptive-grok-build-pro-v2.0.6.zip.sha256

# index / zip string probes (no shell git ls-files / unzip)
.git/index  — no `.github/workflows`, `dependabot.yml`, `github-actions.yml`,
              `pyproject.toml`, `requirements.txt`, `setup.py`
            — no `864726`, no `39b13f`
            — contains `v2.0.6.zip`, `v2.0.5.zip`, `9fd274`, `5be23b`
              (and inherited `ad4090` / `cd8a96` path fragments)
packages/…-v2.0.6.zip — no `.github/workflows`, `dependabot.yml`, `github-actions.yml`

# absences (read of each path → does not exist)
.github/
.github/workflows/adaptive-grok.yml
.github/dependabot.yml
.grok-stack/templates/ci/github-actions.yml
pyproject.toml  requirements.txt  setup.py
MANIFEST.sha256  (root)
```

`HEAD` is `e75f3a1`. Parent is `549f29d`. `549f29d` is an ancestor, not the ship SHA. No local `v2.0.6` tag. `origin/main` is still published `7c0ae75` / v2.0.5.

---

## 1. No GHA workflow / Dependabot / template yml — PASS

On-disk:

- `.github/` does not exist.
- `.grok-stack/templates/ci/` contains only `README.md` (never-GHA; local `make doctor` / `make verify` / `python3 scripts/grok_verify.py --mode pr`).
- Workspace glob of `*.{yml,yaml}` found no `adaptive-grok.yml`, `dependabot.yml`, or `github-actions.yml`.
- No replacement CI vendor file (`.gitlab-ci.yml`, Woodpecker, Jenkinsfile, Circle, Drone, Forgejo). Mentions of those names exist only as “do not add” analysis text.

In the commit index (string probe of `.git/index`): those three GHA paths are **absent**. Combined with `HEAD == e75f3a1` and a working tree that no longer has `.github/`, this is a staged delete, not an uncommitted working-tree-only wipe.

Locked by:

- `tests/test_structure.py::test_version_is_2_0_6_and_github_actions_are_absent`
- `tests/test_deploy.py::test_repo_has_no_github_actions_workflow_or_template`
- `tests/test_deploy.py::test_repo_has_no_workflow_yaml_or_dependabot`
- `tests/test_deploy.py::test_ci_readme_bans_github_actions_and_is_not_a_publisher`
- `tests/test_manifest_package.py::test_included_files_and_shipped_zip_have_no_github_actions`

`deploy.py` still prints `gh release create` (GitHub CLI). That is GitHub **Release**, not GitHub **Actions**. Policy still gates `('gh', 'release', 'create')`. The runbook says the same. Out of scope for this ban.

Historical `CHANGELOG.md` §2.0.4 still says “This-repo GitHub Actions: verify plus a conditional package job (no publish)”. That is prior-release history. Do not rewrite.

---

## 2. `--with-ci` forbidden — PASS

`install()` raises before any mkdir / copy / merge:

```96:100:scripts/install_into.py
    if with_ci:
        raise SystemExit(
            'GitHub Actions is forbidden. Use local `make verify` / '
            '`python3 scripts/grok_verify.py --mode pr`.'
        )
```

The old template → `.github/workflows/adaptive-grok.yml` copy block is gone. `--with-ci` remains as an argparse flag so callers get an explicit error instead of a silent no-op.

Tests:

- `test_with_ci_is_forbidden_and_preserves_unrelated_workflow` — `SystemExit` contains `forbidden`; `existing.yml` untouched; no `adaptive-grok.yml`
- `test_with_ci_dry_run_is_forbidden_and_writes_nothing` — `--force --dry-run --with-ci` still writes nothing (no workflow, no `scripts/grok_verify.py`)
- `test_default_install_does_not_copy_workflow_from_grok_stack` — default install copies the stack, not a workflow / `github-actions.yml`

`force` cannot bypass the raise. The flag help text is also “Forbidden.”

---

## 3. VERSION 2.0.6 — PASS

| Surface | Observed |
| --- | --- |
| `VERSION` | `2.0.6` |
| README H1 | `# Adaptive Grok Build Pro v2.0.6` |
| `CHANGELOG.md` | `## 2.0.6 — 2026-08-16`; `## 2.0.5` intact |
| `dist/RELEASE-NOTES.md` | 2.0.6 section only; same ban bullet |
| `packages/README.md` | 2.0.6 row present; 2.0.0–2.0.5 kept |
| Tests | `test_version_is_2_0_6_and_github_actions_are_absent`; zip member `VERSION` must be `2.0.6` |

No bump to 2.0.7. `VERSION` was not restaged as a product edit.

---

## 4. Zip digest `55406ff2…` — PASS

Sidecars (read, not rehashed):

```
55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d  adaptive-grok-build-pro-v2.0.6.zip
b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd  adaptive-grok-build-pro-v2.0.5.zip
```

`packages/` and `dist/` 2.0.6 siblings match. v2.0.5 digest is unchanged from the published wave. Index contains both `v2.0.6.zip` and `v2.0.5.zip`.

Zip namelist string probe: no `.github/workflows`, no `dependabot.yml`, no `github-actions.yml`. Stale pre-ban digest `b34af685…` is not the sidecar.

Limitation: no shell `sha256sum` of the zip bytes and no `unzip -l`. The sidecar, index presence, and `test_included_files_and_shipped_zip_have_no_github_actions` (177 tests OK in the already-recorded `grok_verify --mode pr`) are the independent stand-ins.

---

## 5. No `pyproject.toml` — PASS

Root reads of `pyproject.toml`, `requirements.txt`, and `setup.py` all miss. Index has none of those names. Locked by `test_product_tree_has_no_packaging_markers`.

`detect_repo` still only treats `pyproject.toml` / `requirements.txt` as `python:project`. Adding a marker would flip the route and, with pytest on PATH, skip `python-unittest`. The commit did not do that. `ruff.toml` / `bandit.yaml` / `.coveragerc` remain configs, not packaging markers.

Root `MANIFEST.sha256` (packager scratch) is absent.

---

## Commit vs package contracts

Matches `brief.md` / `architecture.md` / architect ledger:

- One new commit on `main`, successor of `549f29d`, **not** `549f29d`.
- Message is the ban + rebuilt zip. `COMMIT_EDITMSG` body: “Never ship GitHub Actions. Local grok_verify is the only gate.”
- Product deletes + installer + inverted tests + `decisions.md` + CHANGELOG §2.0.6 + rebuilt `packages/…v2.0.6.zip*` are the ship.
- Allowed owning records `9fd274` and `5be23b` are in the index.
- Void siblings `864726` and `39b13f` are **not** in the index.
- Inherited `ad4090` / `cd8a96` path fragments remain (published 2.0.5 record). Leftover uncommitted paperwork for those packages is still on disk and must stay unstaged.
- No `git add -A` smell of `pyproject`, `v2.0.5.zip` rewrite, or `.github/workflows` as an add.
- v2.0.5 tag object SHA is unchanged. No `v2.0.6` tag from this commit (correct — last mile is after reviews).

`grok_verify --mode pr` on this tree already recorded PASS (ruff, bandit, 177 unittests, coverage 76% / fail-under 74, `profiles=base`). That receipt is verification evidence, not this review.

---

## Findings

No functional, security, or scope-break findings that fail the ban contract.

### Nits (do not fail)

1. **No shell `git show HEAD:.github/workflows/adaptive-grok.yml`.** Absence is inferred from the missing directory, missing index paths, and inverted tests. Same class of gap as the previous 2.0.6 contour review.
2. **Could not rehash the zip.** Sidecar `55406ff2…` and namelist probe are consistent; I did not recompute SHA-256.
3. **Working tree still holds leftover sibling dirt** (`864726`, `39b13f`, leftover `ad4090` / `cd8a96` / `ec0388` paperwork, this package’s post-commit `implementation.md` / `state.json`). Not in the ship index for the void siblings. Controller must not `git add` it before tag.
4. **README / QUICKSTART do not mention `--with-ci` is forbidden.** Installer + tests own that contract. 9fd274 left those docs unchanged on purpose.
5. **§2.0.4 changelog still documents the old workflow.** History. Leave it.

---

## Residual risk

- Last mile is still outstanding: `origin/main` is `7c0ae75`, GitHub Latest is v2.0.5, no `v2.0.6` tag. Tag **`e75f3a1`**, never `549f29d`. Attach digest `55406ff2…`, not `b34af685…`.
- Fresh `grok_approve.py production` is required for agent-run `git push` / `gh release create`. Expired 2.0.5 approval rows are dead.
- Do not run `package_stack.py` again before publish — a rebuild would fold post-commit change dirt and move the digest off `55406ff2…`.
- Consumer trees that already have `adaptive-grok.yml` are out of scope. This product will not copy one.
- `secret-scan` remains changed-files regex; Bandit is complementary. Unrelated to the ban.

Rollback in the change package (`gh release delete v2.0.6` + delete that tag only; leave v2.0.5; restore GHA only by revert) is correct. No force-push.

---

## Recommendation

**PASS.** The six requested checks hold on `e75f3a1`. I would not block last mile on this SHA after `test_reviewer` and bound receipts.

Do not tag, push, or `gh release` from this review.
