# Analysis — architect (identity 2.0.7 then last mile)

Change: `20260816-publish-v2-0-7-github-release-2929c0`  
Route: `2929c09b96b5` · intent=`release` · risk=`high` · write=`null` · reviews=`security_reviewer`+`release_reviewer` · gates=`scope_and_design_approval`,`production_action_approval` · evidence=`verification`,`security_review`,`release_review`  
User: «делай новый релиз и ПУБЛИКУЙ НАХУЙ ЗАЕБАЛ». Session ruling: controller does identity 2.0.7 (VERSION, `__version__`, CHANGELOG, README H1, packages/README, zip via `package_stack`, runbook) then last-mile tag / push / `gh release create --title`. No GHA. No retag 2.0.6. No `pyproject.toml`. User prompt is both gates.

Read-only design. No application-code edits from this agent. No `.env`. No push / tag / merge / `gh release`.

Narrow question: exact identity bytes and last-mile commands so GitHub Latest becomes Adaptive Grok Build Pro v2.0.7, and who executes.

---

## Ruling (one screen)

**Do not tag `11da31a`. Do not retag `v2.0.6`. Controller bumps identity to 2.0.7, rebuilds the zip, commits that ship, then tags / pushes / `gh release create --title`. Architect does not execute. No GitHub Actions. No `pyproject.toml`.**

`write_agent` is null → adaptive-delivery step 4 has no implementer. Parent controller is the only actor who may edit product files and run last mile.

| In | Out |
| --- | --- |
| New identity **2.0.7** on a **new** commit after `11da31a` | Tag `11da31a` as `v2.0.7` (VERSION still 2.0.6) |
| `package_stack` **after** identity edits | Rebuild / retag `v2.0.6` zip `55406ff2…` |
| Annotated `v2.0.7` on the 2.0.7 ship SHA | `git tag -f v2.0.6`; touch `v2.0.5` |
| `gh release create v2.0.7 … --title "Adaptive Grok Build Pro v2.0.7"` | `gh release create v2.0.6`; `gh release edit`; MCP `create_release` |
| `--notes-file dist/RELEASE-NOTES.md` = CHANGELOG `## 2.0.7` | Notes = leftover `## 2.0.6` scratch |
| Controller executes | Architect / analysis / review agents; a spawned write owner |
| Local `grok_verify --mode pr` | `.github/workflows/`; `pyproject.toml` / `requirements.txt` / `setup.py` |

This report is design. It is not authorization for the architect to mutate git or GitHub.

---

## 1. Current facts (inspected this wave)

| Item | Value |
| --- | --- |
| Local `HEAD` / `refs/heads/main` / `origin/main` | `11da31a3f3e60a0463233cb96c576da8517ddabd` — *Fix 2.0.6 leftovers: installer configs, deploy title, stale notes* |
| GitHub `main` | same tip (`/commits/main`) |
| Ancestry | linear: `e75f3a1` → `11da31a` (`.git/logs/HEAD`) |
| Local tags | `v2.0.0`–`v2.0.6`. **No** `refs/tags/v2.0.7` |
| Tag `v2.0.6` | annotated object `8e7c5b67a1f9e51cc2f15586b72e0dceff7f8ee1`, peels to `e75f3a1` |
| Tag `v2.0.5` | annotated object `7f85f7be43fd8008f6af522a967ebc5268a481d1`, peels to `7c0ae75` |
| GitHub Latest | **Adaptive Grok Build Pro v2.0.6** on `e75f3a1` (16 Aug 18:29). `/releases/latest` = `/releases/tag/v2.0.6` |
| GitHub `v2.0.6...main` | **1 commit / 24 files** = `11da31a`. Already on origin; **not** a Release |
| GitHub `/releases/tag/v2.0.7` | **404** |
| Remote | `origin` = `https://github.com/Dimkox/adaptive-grok-build-pro.git` |
| `VERSION` / `__version__` / README H1 | **2.0.6** (also `raw.githubusercontent.com/.../main/VERSION`) |
| CHANGELOG top | `## 2.0.6 — 2026-08-16`. No `## 2.0.7` |
| packages/README | rows through `v2.0.6.zip` only |
| Tracked 2.0.6 zip | `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d` |
| Tracked 2.0.5 zip | `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` |
| 2.0.7 zip | **absent** (`packages/` and `dist/`) |
| `dist/RELEASE-NOTES.md` | CHANGELOG `## 2.0.6` (gitignored scratch; **stale for this ship**) |
| `deploy.py:33` | already prints `--title "Adaptive Grok Build Pro v{version}"` (from `11da31a`) |
| GHA | **none**. `.github/` missing; no Dependabot; no `templates/ci/github-actions.yml` |
| Packaging markers | **absent** — no `pyproject.toml` / `requirements.txt` / `setup.py` |
| `approvals.json` | two rows `2026-08-16T19:26:43Z` expire `19:41:43Z`, reason “push 2.0.6 leftover bugfixes…”. **Wrong reason. Do not reuse.** |
| This change | `draft`. Active change pointer is this `2929c0` package |
| This-route receipts | empty (`2929c09b96b5/`) |
| Prior leftover ship | `3c1039` status `ready` on `11da31a` (identity stayed 2.0.6; no tag) |
| Human gates | already recorded in `evidence/human-approval.md` from the user prompt |
| `repo_explorer` | agrees: next identity is 2.0.7; do not retag 2.0.6 |

`11da31a` is unpublished product: installer copies `ruff.toml` / `bandit.yaml` / `.coveragerc`; printer `--title`; `__version__` matched to 2.0.6; packager unlinks leftover `MANIFEST.sha256`; CHANGELOG §2.0.6 no longer claims 2.0.5 is Latest. That work is already on `main`. It is **not** GitHub Latest.

---

## 2. Why this is a new 2.0.7, not a 2.0.6 retag

`v2.0.6` is a published annotated tag on `e75f3a1` with a live Latest card and zip `55406ff2…`. Moving that tag to `11da31a` is a retag. User forbade it.

Tagging `11da31a` as `v2.0.7` is also wrong: every identity surface on that commit still says **2.0.6**. A 2.0.7 tag that unpacks `VERSION=2.0.6` is a lie.

Correct shape: **one new commit** after `11da31a` that advertises 2.0.7, carries a new zip, then tag **that** SHA.

Do not invent extra product work. `11da31a` already landed the leftover fixes. 2.0.7 is the advertisement + package of that tree.

---

## 3. Who executes, and which gates

| Action | Who |
| --- | --- |
| This design | `architect` (done; stop) |
| Parallel facts | `repo_explorer` (done), `docs_researcher` (read-only) |
| Identity edits + `package_stack` + ship commit | **Controller** |
| `grok_approve.py production` + tag + push + `gh release create` | **Controller**, after the token |
| Human terminal running the same bytes | Also valid; then skip `grok_approve` |
| Spawn `general_implementer` / any write role | **Nobody** — hook blocks (`write_agent` is null) |
| `security_reviewer` + `release_reviewer` | After last mile + `grok_verify --mode pr`, observational |
| This architect running identity or last mile | **Forbidden** |

Gates:

1. **scope_and_design_approval** — this report is the design. Already recorded from the user prompt. Controller does not wait for a second prompt unless preconditions fail.
2. **production_action_approval** — same utterance; same `human-approval.md`. Covers tag, `git push`, and `gh release create`.
3. **PreToolUse `PRODUCTION_INVOCATIONS`** — `git push` and `gh release create` only (`policy.py:48-54`). Identity edits, `package_stack`, `git commit`, and `git tag` are **not** hook-gated. Last mile still needs a **live** `grok_approve.py production` row. The 19:26 leftover-push tokens are the wrong reason and may already be expired; ignore them.

Adaptive-delivery close (`SKILL.md:103`) still forbids treating publish as paperwork. The named production gate plus user ruling authorize **this** last mile, not a 2.0.6 retag.

Default runbook `publish-v2.0.6.md` is print-only and names the wrong version. `grok_deploy.py` will **fail** while this change is `draft` and receipts are empty (`deploy.py:55-63`). That failure is not a publish blocker. Do not run it as the publisher.

---

## 4. Phase A — identity (controller; not a production invocation)

Order is load-bearing: **tests pin first (they fail), then identity files, then packager, then verify, then one ship commit.**

Packager reads `VERSION` and walks the working tree (`included_files` does not exclude `engineering/changes/`). Pack **after** identity bytes exist. A pack now would still emit `v2.0.6.zip` and fold this session’s dirt into the wrong name.

### 4.1 Companion test pins (required or `grok_verify` fails)

Hardcoded 2.0.6 locks:

| File | Today | After |
| --- | --- | --- |
| `tests/test_structure.py` `test_version_is_2_0_6_and_github_actions_are_absent` | `VERSION == '2.0.6'` | `'2.0.7'`; keep GHA-absent asserts |
| `tests/test_manifest_package.py` `test_included_files_and_shipped_zip_have_no_github_actions` | `version == '2.0.6'` and zip `VERSION` == `2.0.6` | both `2.0.7` |
| `test_changelog_2_0_6_does_not_claim_stale_latest` | historical lock on `## 2.0.6` | **leave** |
| `test_package_version_matches_version_file` | `__version__ == VERSION` | **leave** (dynamic) |
| `test_product_tree_has_no_packaging_markers` | no `pyproject.toml` | **leave** |
| `test_deploy.py` `--title` | already version-dynamic | **leave**; do not edit `deploy.py` |

Rename `test_version_is_2_0_6_…` → `test_version_is_2_0_7_and_github_actions_are_absent` if the controller wants the name honest. Not required for green.

Optional one-liner next to the CHANGELOG 2.0.6 lock: `self.assertIn('## 2.0.7', text)`. Useful, not a new product behavior.

Bump the two hardcoded pins **before** editing `VERSION` so they fail first, then go green.

### 4.2 Exact identity bytes

**`VERSION`** — entire file:

```
2.0.7
```

**`.grok-stack/adaptive_grok/__init__.py`** — only the version line:

```python
__version__ = "2.0.7"
```

**`README.md` line 1:**

```markdown
# Adaptive Grok Build Pro v2.0.7
```

Leave the rest of README alone.

**`packages/README.md`** — insert one table row **above** the 2.0.6 row (keep every older row):

```markdown
| `adaptive-grok-build-pro-v2.0.7.zip` | 2.0.7 |
| `adaptive-grok-build-pro-v2.0.6.zip` | 2.0.6 |
```

**`CHANGELOG.md`** — insert this section at the top, **before** `## 2.0.6`. Do not rewrite §2.0.6.

```markdown
## 2.0.7 — 2026-08-16

Leftover 2.0.6 product fixes from `11da31a`, now a tagged release.

- Default `install_into` copies `ruff.toml`, `bandit.yaml`, and `.coveragerc`
- `gh release create` printer and runbook pass `--title "Adaptive Grok Build Pro v{version}"`
- `__version__` matches `VERSION`
- Packager unlinks leftover root `MANIFEST.sha256` after embedding it
- CHANGELOG §2.0.6 no longer claims 2.0.5 remains Latest until last mile
- Stop hook wording: warn, do not block
```

Do **not** put “2.0.6 remains Latest until a human last mile” in §2.0.7. That sentence is the 2.0.6 bug.

**`engineering/runbooks/publish-v2.0.7.md`** — new file (do not rewrite `publish-v2.0.6.md`):

```markdown
# Publish v2.0.7

Print-only last mile. Assemble the zip first; humans own tag / push / GitHub Release.

Last mile is the GitHub CLI (`gh release create`), not GitHub Actions. Do not add `.github/workflows/`.

Agents must not run `git push`, `git tag`, or `gh release`; humans own those commands.

## Checks

```bash
python3 scripts/grok_status.py
python3 scripts/grok_verify.py --mode pr
python3 scripts/grok_deploy.py
```

Only when a human is ready to publish: `python3 scripts/grok_approve.py production --reason "publish v2.0.7"`

## Commands

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.7.zip* packages/
git tag -a v2.0.7 -m "v2.0.7"
git push origin main
git push origin v2.0.7
gh release create v2.0.7 packages/adaptive-grok-build-pro-v2.0.7.zip packages/adaptive-grok-build-pro-v2.0.7.zip.sha256 --title "Adaptive Grok Build Pro v2.0.7" --notes-file dist/RELEASE-NOTES.md
```

## Rollback

```bash
gh release delete v2.0.7 --yes
git push origin :refs/tags/v2.0.7
git tag -d v2.0.7
```
```

This session’s last mile is the SHA-pinned sequence in §5, not a blind re-run of the packager line after the ship already exists.

**Scratch notes** (gitignored; not a commit): overwrite `dist/RELEASE-NOTES.md` with CHANGELOG `## 2.0.7` **only** (heading + lead + six bullets). Do not append §2.0.6. That file is `--notes-file` for `gh`.

### 4.3 Packager

```bash
python3 scripts/package_stack.py
cp dist/adaptive-grok-build-pro-v2.0.7.zip* packages/
```

Expect stdout path `dist/adaptive-grok-build-pro-v2.0.7.zip` and a fresh sha256. Copy both siblings into `packages/`.

Stop if the output name is still `v2.0.6` (VERSION not bumped) or if root `MANIFEST.sha256` remains (`11da31a` unlink must still work).

Residual: `included_files()` walks `engineering/changes/`, so the zip will contain this `2929c0` analysis and sibling change-package markdown that happens to be on disk. Same class as `11da31a` shipping `3c1039`. Do not add an exclude list. Do not add `pyproject.toml` to “clean” packaging.

Do **not** rebuild `packages/adaptive-grok-build-pro-v2.0.6.zip*`. Digest must stay `55406ff2…`. Leave `v2.0.5` at `b80e6310…`.

### 4.4 Verify before commit

```bash
python3 scripts/grok_verify.py --mode pr
```

Hard no-go if this fails. Quality profile is `base` (secret-scan + git-diff-check; ruff/bandit/coverage optional-but-fail-closed when installed). Do not pass `--with-ci`.

### 4.5 One ship commit — explicit add only

Subject:

```
Release v2.0.7: leftover installer/title/manifest fixes
```

```bash
git add -- \
  VERSION \
  .grok-stack/adaptive_grok/__init__.py \
  CHANGELOG.md \
  README.md \
  packages/README.md \
  engineering/runbooks/publish-v2.0.7.md \
  tests/test_structure.py \
  tests/test_manifest_package.py \
  packages/adaptive-grok-build-pro-v2.0.7.zip \
  packages/adaptive-grok-build-pro-v2.0.7.zip.sha256
git commit -m "Release v2.0.7: leftover installer/title/manifest fixes"
```

Do **not** `git add -A` / `git add .`. Stay out of:

| Path | Why |
| --- | --- |
| this `2929c0` package | session paperwork; optional hygiene **after** the tag |
| leftover `3c1039` review files not already on `11da31a` | already-ready leftover route |
| `dist/` | gitignored scratch |
| `.grok-stack/runtime/` | gitignored |
| `.env` / `.env.*` / `*.pem` / `*.key` | secrets |
| `packages/…v2.0.6.zip*` / `…v2.0.5.zip*` | published artifacts |
| `.github/` | must stay absent |

Record the new SHA. That is the only legal `v2.0.7` peel. Call it `<SHIP>` below.

---

## 5. Phase B — last mile (controller; production token required)

### 5.1 Machine token (controller Bash only)

```bash
python3 scripts/grok_approve.py production --reason "publish v2.0.7 tag and GitHub Release"
```

- TTL default **15 minutes**. Finish tag + both pushes + `gh` inside that window.
- `grok_approve.py production` itself is allowed without a prior token.
- Human terminal: PreToolUse does not apply; the token may be skipped. Outcome and command bytes stay the same.
- Do not mint `external-write` unless someone is about to call MCP. MCP is forbidden anyway.
- Do not reuse the leftover-bugfix rows.

### 5.2 Preconditions — stop if any fail

```bash
git fetch origin

git rev-parse HEAD
# expect <SHIP> (the 2.0.7 identity commit; not 11da31a, not e75f3a1)

test "$(tr -d '[:space:]' < VERSION)" = 2.0.7

git rev-parse 'v2.0.6^{}'
# expect e75f3a1b92e247279fbb6210d46715a90cf7895c

git rev-parse 'v2.0.5^{}'
# expect 7c0ae7573535ddd0cfe3800f81278991ced81584

git show-ref --verify --quiet refs/tags/v2.0.7; echo $?
# expect 1 (local tag missing)

git ls-remote --tags origin 'refs/tags/v2.0.7'
# expect empty

test -f packages/adaptive-grok-build-pro-v2.0.7.zip
test -f packages/adaptive-grok-build-pro-v2.0.7.zip.sha256
# sidecar must start with the digest printed by package_stack in §4.3
# 2.0.6 sidecar must still start with
# 55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d

test ! -e pyproject.toml
test ! -e .github/workflows
test -f dist/RELEASE-NOTES.md
# first heading must be ## 2.0.7

gh auth status
gh api repos/Dimkox/adaptive-grok-build-pro/releases/latest --jq .tag_name
# expect v2.0.6 before we publish
```

This `gh` may lack `isLatest` (cd8a96). Use `GET /releases/latest`, not `gh release view --latest`.

No-go if `VERSION` is not 2.0.7, `HEAD` is still `11da31a`, `v2.0.6` no longer peels to `e75f3a1`, origin already has `v2.0.7`, zip name/digest is wrong, `.github/workflows` exists, or `pyproject.toml` appeared. Then stop. Reassess. No `-f`.

### 5.3 Last mile — controller executes

```bash
git tag -a v2.0.7 <SHIP> -m "v2.0.7"
git push origin <SHIP>:refs/heads/main
git push origin v2.0.7
gh release create v2.0.7 \
  packages/adaptive-grok-build-pro-v2.0.7.zip \
  packages/adaptive-grok-build-pro-v2.0.7.zip.sha256 \
  --title "Adaptive Grok Build Pro v2.0.7" \
  --notes-file dist/RELEASE-NOTES.md \
  --verify-tag
```

Order is load-bearing:

1. Tag the ship SHA so `gh` cannot mint a different object.
2. Push `main` before the tag so default-branch `VERSION` and Latest move together.
3. Push the annotated tag before `gh release create`.
4. `--verify-tag` refuses a missing remote tag. Do **not** pass `--target` (that is how `gh` creates a tag when the ref is missing).

SHA-pin is intentional. `git push origin main` is equivalent **iff** `HEAD` is still `<SHIP>`. A later paperwork commit must not ride the publish.

`--title` is required. Empty-name cards (v2.0.5, first v2.0.6) were the `11da31a` bug; do not regress.

May be four Bash calls or one `&&` chain. Any chunk whose leading argv is `git push` or `gh release create` needs the live production token.

### 5.4 Confirm

```bash
git rev-parse 'v2.0.7^{}'
# expect <SHIP>

git rev-parse 'v2.0.6^{}'
# still e75f3a1b92e247279fbb6210d46715a90cf7895c

git ls-remote origin refs/heads/main 'refs/tags/v2.0.7'
# main and peeled tag both <SHIP>

gh release view v2.0.7 --json tagName,name,isDraft,isPrerelease
# tagName=v2.0.7
# name=Adaptive Grok Build Pro v2.0.7
# isDraft=false; isPrerelease=false

gh api repos/Dimkox/adaptive-grok-build-pro/releases/latest --jq .tag_name
# expect v2.0.7

gh release view v2.0.6 --json tagName
# still exists
```

Asset digest on the published zip must equal the `package_stack` digest from §4.3.

### 5.5 Skip (already done / would make things worse)

| Command | Why skip |
| --- | --- |
| Second `package_stack` after the ship commit | New digest; would fold post-ship paperwork |
| `git tag -a v2.0.7` without `<SHIP>` after `HEAD` moved | Would pin paperwork, not the ship |
| `git tag -a v2.0.6` / `-f` / `-d v2.0.6` | Published Latest until this ship lands |
| `git tag -a v2.0.7 11da31a` | Identity on that SHA is still 2.0.6 |
| `gh release create v2.0.6` / `gh release edit v2.0.6` | Wrong release |
| `git push --force` / `git reset --hard` | `policy.py` `DESTRUCTIVE_COMMANDS` |
| `python3 scripts/grok_deploy.py` | Fails on `draft` + missing receipts; packager line is already done |
| MCP GitHub `create_release` / `create_or_update_ref` | Second publisher |
| Adding `.github/workflows/` or `pyproject.toml` | Banned |

---

## 6. Frozen surfaces

| Surface | Must remain |
| --- | --- |
| `refs/tags/v2.0.6` peeled | `e75f3a1b92e247279fbb6210d46715a90cf7895c` |
| `refs/tags/v2.0.5` peeled | `7c0ae7573535ddd0cfe3800f81278991ced81584` |
| 2.0.6 zip | `55406ff22f81ae05fc70eb9a5710b5c055c76a18f2ddbe60687c03b3e0b95c4d` |
| 2.0.5 zip | `b80e63103453db3161a4e4489216f654c04aec27e0821a1642ccc6c37027b4fd` |
| GitHub Release `v2.0.6` card | exists; stops being Latest only because 2.0.7 is newer |
| GitHub Release `v2.0.5` | exists |
| `.github/workflows/*` | still absent |
| `pyproject.toml` / `requirements.txt` / `setup.py` | still absent |
| `deploy.py` `--title` printer | already correct; do not edit |

---

## 7. Rollback (v2.0.7 only)

Already in `rollback.md`:

```bash
gh release delete v2.0.7 --yes
git push origin :refs/tags/v2.0.7
git tag -d v2.0.7
```

Do not touch `v2.0.6` / `v2.0.5`. No force-push.

| Must not | Why |
| --- | --- |
| `gh release delete v2.0.6` | Current Latest until 2.0.7 exists; previous artifact after |
| `git push origin :refs/tags/v2.0.6` / retag | Published peel `e75f3a1` |
| `git push --force` / `git reset --hard` | Destructive |
| Revert `<SHIP>` as part of a *failed tag/Release* | If `main` was not pushed, nothing to revert. If it was, revert is a **separate** production approval |
| Delete `packages/…v2.0.7.zip*` after a failed Release | Belongs on `main` even if the card is withdrawn |

`gh release delete` is **not** in `PRODUCTION_INVOCATIONS`. Rollback is still controller-or-human-owned so `v2.0.6` cannot be deleted by a sloppy extra argument.

Partial-failure matrix:

| After | Next |
| --- | --- |
| Identity edit / tests fail | Stop. Do not pack / tag |
| `package_stack` emits `v2.0.6` | VERSION not bumped. Fix identity. Do not tag |
| `grok_verify` fails | Stop. Do not commit / tag |
| Ship commit ok, `grok_approve` fails | Stop. Do not tag/push. Retry approve only |
| Tag create fails (name taken) | Stop. Do not `-f`. Inspect peel. If it already is `<SHIP>`, continue from push |
| Tag ok, `main` push fails | Stop. Do not `gh release create`. Fix auth / non-ff. Retry SHA-pin push only. No `-f` |
| `main` ok, tag push fails | Retry `git push origin v2.0.7` only. Do not retag |
| Tag on origin, `gh` fails | Retry `gh release create … --title … --verify-tag` only. Do not retag |
| Release created with empty title | `gh release edit v2.0.7 --title "Adaptive Grok Build Pro v2.0.7"` only. Do not recreate |
| Notes are still §2.0.6 | Rewrite scratch notes; `gh release edit v2.0.7 --notes-file dist/RELEASE-NOTES.md`. Do not retag |
| Zip wrong after publish | Rollback **v2.0.7 only**; new commit + **new** tag name. No `git tag -f v2.0.7` |
| Token expires mid-sequence | Re-run `grok_approve.py production` with the same reason. Resume the **next unfinished** command only |

---

## 8. Post-publish (not the last mile)

After Latest is `v2.0.7`:

1. Controller: `python3 scripts/grok_verify.py --mode pr` on the published tree (working tree may still contain this analysis; that is session paperwork, not a second ship). Required evidence kind `verification`.
2. Dispatch **only** `security_reviewer` and `release_reviewer`. They inspect the **live** name `Adaptive Grok Build Pro v2.0.7`, body = §2.0.7 (no last-mile sentence), tag peel `<SHIP>`, Latest badge, new zip digest, and that `v2.0.6` still peels to `e75f3a1`. They do not execute.
3. Record receipts **after** any last intended `state.json` write:

```bash
python scripts/grok_review.py security_review --status pass --report engineering/changes/20260816-publish-v2-0-7-github-release-2929c0/evidence/security-review.md
python scripts/grok_review.py release_review --status pass --report engineering/changes/20260816-publish-v2-0-7-github-release-2929c0/evidence/release-review.md
```

4. Optionally transition this change `draft` → `ready` / `released` and mark `3c1039` released. Do not fold that paperwork into a new tag.

Those receipts close route `2929c09b96b5`. They are not a second ship.

---

## 9. File ledger

| Path | Action |
| --- | --- |
| `VERSION` | **Edit** → `2.0.7` |
| `.grok-stack/adaptive_grok/__init__.py` | **Edit** `__version__` → `"2.0.7"` |
| `CHANGELOG.md` | **Insert** `## 2.0.7`; leave `## 2.0.6` |
| `README.md` | **Edit** H1 only |
| `packages/README.md` | **Add** 2.0.7 row |
| `tests/test_structure.py` | **Bump** VERSION pin to 2.0.7 |
| `tests/test_manifest_package.py` | **Bump** VERSION / zip pins to 2.0.7 |
| `engineering/runbooks/publish-v2.0.7.md` | **Create** |
| `dist/RELEASE-NOTES.md` | **Rewrite scratch** to §2.0.7 |
| `packages/adaptive-grok-build-pro-v2.0.7.zip*` | **Create** via packager + `cp` |
| GitHub Release `v2.0.7` | **Create** (controller last mile) |
| `packages/…v2.0.6.zip*` | **Leave** |
| `engineering/runbooks/publish-v2.0.6.md` | **Leave** (historical) |
| `.grok-stack/adaptive_grok/deploy.py` | **Leave** (already has `--title`) |
| `pyproject.toml` | **Must stay absent** |
| `.github/workflows/*` | **Must stay absent** |
| `refs/tags/v2.0.6` / Release `v2.0.6` | **Do not move / edit** |
| This analysis file | The only write from this agent |

---

## 10. Risks

| Risk | Mitigation |
| --- | --- |
| Tag `11da31a` because it is already on `main` | Preconditions: `VERSION` must be 2.0.7; peel must be `<SHIP>` |
| Muscle memory `gh release create v2.0.6` / runbook 2.0.6 | New runbook; argv tag is `v2.0.7`; skip table |
| Empty GitHub title again | Required `--title`; confirm `name` in §5.4 |
| `--notes-file` still §2.0.6 | Overwrite scratch **after** CHANGELOG insert; first heading check |
| Packager before identity bump | Emits `v2.0.6.zip` and would clobber the published digest if copied. Pack after VERSION=2.0.7 |
| Second pack after paperwork | New digest vs tagged zip. Pack once, then commit |
| Reusing 19:26 leftover-push token | Wrong reason; mint a 2.0.7 production row |
| Spawn write owner because identity is “implementation” | `write_agent` is null; hook will block |
| Adding `pyproject.toml` so tests “look packaged” | Flips `detect_repo` and can skip unittest. Forbidden |
| Restoring GHA “for the release” | Banned since `e75f3a1`. Local verify only |
| MCP `create_release` as a “safer” path | Second publisher; no |

Residual: the 2.0.7 zip will embed whatever `engineering/changes/**` is on disk at pack time, including this analysis. Acceptable; do not expand packager excludes in this route.

---

## 11. Acceptance

- [ ] `VERSION` and `__version__` are `2.0.7`
- [ ] CHANGELOG has `## 2.0.7`; README H1 is `v2.0.7`; packages/README has a 2.0.7 row
- [ ] `packages/adaptive-grok-build-pro-v2.0.7.zip` exists; in-zip `VERSION` is `2.0.7`; no GHA / Dependabot / `github-actions.yml` in the zip
- [ ] No `pyproject.toml`; no `.github/workflows/`
- [ ] `python3 scripts/grok_verify.py --mode pr` PASS
- [ ] `git rev-parse 'v2.0.7^{}'` == `<SHIP>` (child of `11da31a`, not `11da31a` itself)
- [ ] `origin/main` is `<SHIP>`
- [ ] `gh release view v2.0.7 --json name` is `Adaptive Grok Build Pro v2.0.7`
- [ ] Latest tag is `v2.0.7`
- [ ] `git rev-parse 'v2.0.6^{}'` == `e75f3a1b92e247279fbb6210d46715a90cf7895c`
- [ ] Release `v2.0.6` and `v2.0.5` still exist
- [ ] 2.0.6 zip digest still `55406ff2…`

---

## 12. What this agent did not do

No application edits. No VERSION bump. No package rebuild. No `git push` / `git tag` / `gh release`. No read of `.env`. Independent reviews wait for the live 2.0.7 card.

This report is design. It is not a verification or review receipt.
