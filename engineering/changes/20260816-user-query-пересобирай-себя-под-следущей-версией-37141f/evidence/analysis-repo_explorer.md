# Analysis — repo_explorer

Change: `20260816-user-query-пересобирай-себя-под-следущей-версией-37141f`  
Route: `37141fbe6302` · write owner: `general_implementer` · analysis-only

Read-only. Local refs + public GitHub HTML. No product edits, tag, push, or `gh release`.

Confirmed: `HEAD` = `origin/main` = `02376cc` *Release v2.0.7*. GitHub Latest is **Adaptive Grok Build Pro v2.0.7** on that SHA. Next identity is **2.0.8**. Working tree already has the unpublished AGENTS.md self-learning restore. User asked rebuild + self-check + **git push if green**, not a GitHub Release.

| Check | Fact |
| --- | --- |
| `HEAD` / `refs/heads/main` / `origin/main` | `02376cc097d7640d56dd308b98efe4e026f4c253` |
| GitHub Latest | [Adaptive Grok Build Pro v2.0.7](https://github.com/Dimkox/adaptive-grok-build-pro/releases/latest) on `02376cc` |
| Local tag `v2.0.7` | annotated object `2407833d…` peels to `02376cc` |
| `VERSION` / `__version__` / README H1 | still **2.0.7** |
| Unpublished product | AGENTS.md first section + `test_agents_md_starts_with_self_learning` + mistakes.md 2026-08-16 entry |
| Next identity | **2.0.8**. No `## 2.0.8`, no 2.0.8 zip, no packages/README row |
| GHA | **none**. No `.github/workflows`, no Dependabot, no `templates/ci/github-actions.yml` |
| Approvals | expired 20:12:24Z, reason *publish v2.0.7 tag and GitHub Release*. Unusable. |

Do not retag 2.0.7. Do not add GHA. Do not add `pyproject.toml`. Pack **after** `VERSION=2.0.8`.

---

## 1. Files that pin 2.0.7 and must move to 2.0.8

`VERSION` is source of truth. Packager default output, deploy printer, zip name, and runbook tag follow it. `__version__` is a hardcoded lock; `test_package_version_matches_version_file` fails if they diverge.

### Must edit (committed identity)

| Path | Current | 2.0.8 action |
| --- | --- | --- |
| `VERSION` | `2.0.7` | replace with `2.0.8` (single line, no extra newline drama) |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.7"` | `"2.0.8"` |
| `README.md` L1 | `# Adaptive Grok Build Pro v2.0.7` | `v2.0.8`. Leave the rest. |
| `CHANGELOG.md` | top is `## 2.0.7 — 2026-08-16` | **insert** `## 2.0.8 — 2026-08-16` above it. Do **not** rewrite §2.0.7 or older. |
| `packages/README.md` | last row is 2.0.7 | **add** `adaptive-grok-build-pro-v2.0.8.zip` / `2.0.8`. Keep 2.0.0–2.0.7. |
| `tests/test_structure.py` | `test_version_is_2_0_7_and_github_actions_are_absent` asserts `'2.0.7'` | rename → `test_version_is_2_0_8_and_github_actions_are_absent`; assert `'2.0.8'`. Keep GHA-absent asserts. Keep `test_agents_md_starts_with_self_learning` (already dirty). Keep `test_changelog_2_0_6_does_not_claim_stale_latest` (historical 2.0.6 lock). |
| `tests/test_manifest_package.py` `test_included_files_and_shipped_zip_have_no_github_actions` | `version == '2.0.7'` and in-zip `VERSION == '2.0.7'` | both `'2.0.8'`. Leave the rest of the file. |

### Must create (committed)

| Path | Action |
| --- | --- |
| `engineering/runbooks/publish-v2.0.8.md` | **new**. Copy 2.0.7 shape with every `2.0.7` → `2.0.8`. Do **not** rewrite `publish-v2.0.7.md`. |
| `packages/adaptive-grok-build-pro-v2.0.8.zip` | create via packager + `cp` **after** the bump |
| `packages/adaptive-grok-build-pro-v2.0.8.zip.sha256` | sibling from packager |

### Scratch (gitignored — write, do not commit)

| Path | Action |
| --- | --- |
| `dist/RELEASE-NOTES.md` | overwrite with CHANGELOG **§2.0.8 only**. `--notes-file` if a later human runs `gh`. |
| `dist/adaptive-grok-build-pro-v2.0.8.zip*` | packager default output |

### Already-dirty product that is the 2.0.8 payload (commit; do not revert)

These are **not** on `02376cc`. They are the unpublished work this version advertises.

| Path | vs `02376cc` |
| --- | --- |
| `AGENTS.md` | HEAD starts with intro + `## Mandatory entrypoint`. Working tree inserts `## Agent self-learning` first, naming `engineering/decisions.md` / `engineering/mistakes.md`. |
| `tests/test_structure.py` | HEAD has no `test_agents_md_starts_with_self_learning`. Working tree L22–36 lock first heading + wording. |
| `engineering/mistakes.md` | HEAD has no 2026-08-16 authorship-omission entry. Working tree added it at the top. |

### Suggested CHANGELOG §2.0.8

```markdown
## 2.0.8 — 2026-08-16

AGENTS.md self-learning is the first standing rule.

- First `##` heading is Agent self-learning; sinks are `engineering/decisions.md` and `engineering/mistakes.md`
- Structure test locks placement and wording so a later rewrite cannot drop it
- Authorship omission recorded in `engineering/mistakes.md`
- Still no GitHub Actions
```

Do **not** write “2.0.7 remains Latest until a human last mile” into §2.0.8 (that sentence is the old 2.0.6 bug). Latest staying on v2.0.7 after a main-only push is expected and does not belong in product notes.

### Do not treat as 2.0.8 identity

| Path | Why |
| --- | --- |
| `QUICKSTART.md` | no version pin |
| `Makefile` | `package` / `deploy` / `verify` wrappers; no version |
| `engineering/runbooks/publish-v2.0.{4,5,6,7}.md` | historical. Leave frozen. |
| `tests/test_policy.py` / `tests/test_deploy.py` | `v2.0.4` strings are fixtures, not identity |
| `packages/adaptive-grok-build-pro-v2.0.7.zip*` | published artifact. Digest must stay `ec48d3174248e15e241519546b1414a7698857509cf97ac61e078dbd204de01c` |
| Historical `engineering/changes/**` 2.0.7 prose | do not rewrite |
| `pyproject.toml` / `requirements.txt` / `setup.py` | **must not exist**. `test_product_tree_has_no_packaging_markers` |

---

## 2. How `package_stack` + copy to `packages/` works

`scripts/package_stack.py` → `write_archive(root, output)`:

1. Reads `VERSION` via `_default_output` → `dist/adaptive-grok-build-pro-v{VERSION}.zip`.
2. `generate_manifest(root)` writes a temporary root `MANIFEST.sha256` of `included_files()`.
3. Zips those files plus the manifest as `adaptive-grok-build-pro/<rel>` with fixed zip time `(2026, 8, 14, 0, 0, 0)` and DEFLATE 9.
4. Writes sibling `{zip}.sha256` as `{digest}  {zipname}\n`.
5. **Unlinks** leftover root `MANIFEST.sha256` (the zip already embeds it). If a root `MANIFEST.sha256` remains, stop.

`included_files()` (`.grok-stack/adaptive_grok/manifest.py`):

- Walks the live filesystem (tracked **and** untracked).
- Drops: `.git`, `__pycache__`, `dist/`, `node_modules`, `vendor`, `.venv`, `htmlcov`, `.ruff_cache`, `MANIFEST.sha256` (as a listed file before it is force-added), `.env*`, `err.log`, `*.pem`/`*.key`/`*.p12`/`*.pfx`, `.grok-stack/runtime/**` except `.gitkeep`, `*.pyc`/`*.pyo`/`*.zip`/`*.sha256`.
- So prior `packages/*.zip` are **not** nested. `engineering/changes/**` markdown **is** packed.

Tracked copies live in `packages/`. Scratch rebuilds stay in gitignored `dist/`. Copy **both** siblings:

```bash
python3 scripts/package_stack.py
# stdout: /…/dist/adaptive-grok-build-pro-v2.0.8.zip
# stdout: <sha256>
test ! -f MANIFEST.sha256
cp dist/adaptive-grok-build-pro-v2.0.8.zip* packages/
( cd packages && sha256sum -c adaptive-grok-build-pro-v2.0.8.zip.sha256 )
```

Stop if the printed path still says `v2.0.7` (packed before the bump) or if `packages/adaptive-grok-build-pro-v2.0.7.zip.sha256` changed.

Residual (accepted, same class as 2.0.7): leftover on-disk change packages (`d55ce4`, post-commit `2929c0` reviews) are embedded in the new zip even if not `git add`ed. Do not expand packager excludes to “clean” that.

`.env` and private keys are never packaged.

---

## 3. What must not be committed

Architecture ruling: **stage only the 2.0.8 product files + this change package.**

### Do not `git add`

| Path | Why |
| --- | --- |
| `engineering/changes/20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4/**` | Other route. Ready-but-unpublished paperwork. Product bytes already live in `AGENTS.md` / test / `mistakes.md`. |
| `engineering/changes/20260816-publish-v2-0-7-github-release-2929c0/evidence/release-review.md` | Written **after** `02376cc`. Leftover 2.0.7 last-mile review. |
| `engineering/changes/20260816-publish-v2-0-7-github-release-2929c0/evidence/security-review.md` | Same. Committed 2929c0 evidence stops at analysis + `human-approval.md`. |
| Any other historical `engineering/changes/*` rewrite | Not this change. |

### Gitignored — never stage

- `.grok-stack/runtime/**` (approvals, receipts, `active-route.json`)
- `dist/**` including `RELEASE-NOTES.md`
- `err.log`
- root `MANIFEST.sha256`
- `__pycache__/`, `.coverage`, `.ruff_cache/`
- `.env`, `*.pem`, `*.key`

### Do not create / restore

- `.github/workflows/**`, `.github/dependabot.yml`, `.grok-stack/templates/ci/github-actions.yml`
- `pyproject.toml`, `requirements.txt`, `setup.py`
- rebuilt `packages/adaptive-grok-build-pro-v2.0.7.zip*`

### Do commit (this change)

```
VERSION
.grok-stack/adaptive_grok/__init__.py
README.md
CHANGELOG.md
packages/README.md
AGENTS.md
engineering/mistakes.md
engineering/decisions.md          # only if implementer appends a 2.0.8 self-learning / pin-after-bump entry
tests/test_structure.py
tests/test_manifest_package.py
engineering/runbooks/publish-v2.0.8.md
packages/adaptive-grok-build-pro-v2.0.8.zip
packages/adaptive-grok-build-pro-v2.0.8.zip.sha256
engineering/changes/20260816-user-query-пересобирай-себя-под-следущей-версией-37141f/
```

Use path-limited `git add` of that set. Do not `git add -A`.

---

## 4. How `grok_approve` + `git push` is supposed to work

Policy (`policy.py`):

- `git push` is a `PRODUCTION_INVOCATIONS` prefix (`('git', 'push')`).
- PreToolUse **denies** `git push …` unless `has_valid_approval(root, 'production')`.
- `python3 scripts/grok_approve.py production --reason "…"` is **not** a production invocation (`test_approve_script_is_not_blocked_by_scope_argument`).
- Default TTL is **15 minutes**. Scope must be `production` (or `*`).
- Current `approvals.json` rows expired 2026-08-16T20:12:24Z and say *publish v2.0.7 tag and GitHub Release*. Do **not** reuse them.

Required before the push:

```bash
python3 scripts/grok_approve.py production --reason "push v2.0.8 identity to origin/main"
git push origin main
```

Mint immediately before the push. Do not mint during identity work.

`AGENTS.md` still forbids “direct push to a protected/shared branch” and “production mutation without short-lived explicit approval.” The user prompt is the production **go** for **push only**. The approval row is the machine token that lifts the hook. No named `human_gates` on this route.

`scripts/grok_deploy.py` is prepare-only. It **prints** (never runs) tag / push / `gh release create`. `--record` also needs production approval and writes a `deploy`/`prepared` receipt. Dry-run is allowed without approval (`test_grok_deploy_cli_is_allowed_without_production_approval`). Do not treat `make deploy` / `grok_deploy` as “run these.”

Who does what:

- `general_implementer` owns identity, zip, path-limited commit.
- Controller (after last content write): official `grok_verify --mode pr`, dispatch `code_reviewer`, `grok_review.py code_review`, then approve + `git push origin main`.
- Implementer must not self-approve. Implementer must not push without a fresh production row.

Fingerprint: `tree_fingerprint` = `HEAD` + dirty/untracked (exclude-standard) file hashes. A `git commit` changes `HEAD` and stale-dates receipts. Official verify + `code_review` receipts for completion belong on the tree that will be pushed. Typical shape: commit the ship set, write `evidence/code-review.md`, run official verify **after** that last report, then `grok_review.py`. Leave the review report uncommitted **or** fold it into the ship commit **before** the official verify — do not commit after the completion receipts.

`required_evidence`: `verification`, `code_review`. Quality profile: `base` (`git-diff-check`, `secret-scan`) plus `--mode pr` always runs Ruff / Bandit / `coverage run -m unittest discover -s tests` / `coverage report` because this tree has `tests/test*.py` and no packaging marker.

---

## 5. Tag + `gh release` are **not** required for this prompt

User: «пересобирай себя под следующей версией … и гит пуш, если все ок».

| Action | This prompt |
| --- | --- |
| Identity 2.0.8 + zip on a new commit | **required** |
| `python3 scripts/grok_verify.py --mode pr` | **required** |
| Independent `code_reviewer` + `grok_review.py` | **required** (route evidence) |
| `git push origin main` if green | **required** (user; after approve) |
| `git tag -a v2.0.8` | **not** requested |
| `git push origin v2.0.8` | **not** requested |
| `gh release create v2.0.8 …` | **not** requested |

After a green main-only push:

- `origin/main` advertises 2.0.8.
- GitHub Latest **stays** Adaptive Grok Build Pro **v2.0.7** on `02376cc`.
- That is the same shape as `11da31a` sitting on main while Latest was still 2.0.6.

`grok_deploy` / the new runbook still **print** the full last mile for a later human:

```text
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.8.zip* packages/
git tag -a v2.0.8 -m "v2.0.8"
git push origin main
git push origin v2.0.8
gh release create v2.0.8 packages/adaptive-grok-build-pro-v2.0.8.zip packages/adaptive-grok-build-pro-v2.0.8.zip.sha256 --title "Adaptive Grok Build Pro v2.0.8" --notes-file dist/RELEASE-NOTES.md
```

Do **not** execute tag / tag-push / `gh release create` in this route. Those wait for an explicit “publish / GitHub release” prompt.

Rollback if the 2.0.8 commit is local only: `git reset --keep origin/main`. If it is already on origin: forward-fix as 2.0.9. Never `git push --force`. Never delete `v2.0.7`.

---

## Implementer checklist

1. Fail the pins first: change only the two hardcoded `'2.0.7'` asserts (and the `test_version_is_2_0_7_…` name) so `unittest` is red.
2. Set `VERSION` to `2.0.8` and `__version__ = "2.0.8"`.
3. README H1 → `v2.0.8`. Insert CHANGELOG `## 2.0.8` (leave `## 2.0.7`). Add `packages/README.md` 2.0.8 row.
4. Keep the dirty `AGENTS.md` self-learning section, `test_agents_md_starts_with_self_learning`, and the mistakes.md authorship entry. Do not revert them.
5. Create `engineering/runbooks/publish-v2.0.8.md` (print-only last mile). Do not edit `publish-v2.0.7.md`.
6. Overwrite scratch `dist/RELEASE-NOTES.md` with §2.0.8 only (not a commit).
7. **Then** pack: `python3 scripts/package_stack.py` → expect `dist/adaptive-grok-build-pro-v2.0.8.zip`. Confirm no root `MANIFEST.sha256`.
8. `cp dist/adaptive-grok-build-pro-v2.0.8.zip* packages/` and checksum. Confirm in-zip `VERSION` is `2.0.8`. Confirm 2.0.7 sidecar is still `ec48d317…`.
9. Optional: append a ≤3-sentence `engineering/decisions.md` entry if pin-after-bump + first-section lock paid for itself.
10. `python3 -m unittest tests.test_structure tests.test_manifest_package` green. No `pyproject.toml`. No `.github/`.
11. Path-limited `git add` of the §3 “Do commit” set (including this change package). **Do not** add `d55ce4/**`, 2929c0 post-commit reviews, `dist/`, or runtime.
12. Commit: `Release v2.0.8: AGENTS.md self-learning as first standing rule`.
13. Hand off. Controller runs official `python3 scripts/grok_verify.py --mode pr` **after the last remaining file**, dispatches `code_reviewer`, then `python3 scripts/grok_review.py code_review --status pass --report engineering/changes/20260816-user-query-пересобирай-себя-под-следущей-версией-37141f/evidence/code-review.md`.
14. If verify+review are green: `python3 scripts/grok_approve.py production --reason "push v2.0.8 identity to origin/main"` then `git push origin main`. Stop. No tag. No `gh release create`.
