# Analysis — architect

Change: `20260816-user-query-пиздец-ты-конченый-применяй-все-измен-ff295d`  
Route: `ff295dada3ef` · write owner: `general_implementer`  
Question: exact commands — `rm` abandoned untracked packages; `git add` only keeper change-package files + this `ff295d` package; commit; later controller pushes. Do not restore deleted product. Do not add leftover `state.json` from unrelated packages if those packages are DELETE.

Read-only. No application-code edits. No `.env`. Architect does **not** commit, push, merge, or deploy.

## Ruling

Paperwork-only. Product is already `7152b75` on both `HEAD` and `origin/main`. `VERSION` stays `2.0.8`. No tag, no zip, no GHA, no `pyproject.toml`.

One write owner (`general_implementer`) does a path-limited cleanup commit. Controller verifies, reviews, then pushes. `git add -A` / `git add .` / `git add engineering/changes` are forbidden.

Live inventory vs GitHub tree of `7152b75` (same SHA as local `refs/heads/main` and `refs/remotes/origin/main`):

| Class | On `7152b75`? | Local disk | Action |
| --- | --- | --- | --- |
| DELETE `39b13f` `864726` `b625b4` `0f3d94` `2a31f5` `04ae05` | **no** | full untracked dirs | `rm -rf` whole dir, including `state.json` |
| KEEP extras on HEAD (`5be23b` `2929c0` `3c1039` `ec0388` `37141f` `a13da8` `ad4090`) | yes | extras + dirtier `state.json` | `git add` that dir only |
| KEEP `ba1615` | yes | evidence already on HEAD | add only if still dirty |
| KEEP `d55ce4` `2f9f5d` | **no** | full untracked dirs | `git add` whole dir |
| This package `ff295d` | **no** | full untracked dir | `git add` whole dir after analysis reports land |
| Non-KEEP HEAD (`9fd274` `cd8a96` `ef7b14` and older) | yes | leave alone | **do not add** |

DELETE packages are entirely untracked. Architecture already says: if a DELETE path ever had tracked files, leave the HEAD copy. That case is not live here — `rm -rf` is correct.

## Hard forbids

- `git add -A`, `git add .`, `git add engineering/changes`, `git add engineering/changes/`
- `git add` of any DELETE path, including a leftover `state.json` after a partial `rm`
- `git restore`, `git checkout --`, `git reset --hard`, `git reset --merge`, `git clean -fdx`
- Staging or restoring product paths (`VERSION`, `AGENTS.md`, `README.md`, `CHANGELOG.md`, `decisions.md`, `mistakes.md`, `packages/`, `tests/`, `scripts/`, `.grok/`, `.grok-stack/adaptive_grok/`, `.grok-stack/config/`)
- `git add -u` (would stage product deletions if any exist)
- VERSION bump, tag, `gh release`, zip rebuild, `.github/workflows`, `pyproject.toml`
- Push / merge / deploy from the write agent

“Do not restore deleted product” means: do not resurrect product files from HEAD, from abandoned packages, or from the index. Product already lives on `origin/main` at `7152b75`. This commit must not rewrite it.

“Do not add leftover `state.json` from DELETE packages” means: after `rm -rf`, if a hook or `grok_change.py` recreates only `…/39b13f/state.json` (or any other DELETE `state.json`), delete that file again. Never stage it. KEEP `state.json` dirt is in scope; DELETE `state.json` is not.

## Exact implementer commands

Stop if any precondition fails. Run from the repo root. Write owner is `general_implementer` only.

### 0. Identity — product already published

```bash
test "$(cat VERSION)" = "2.0.8"
test "$(git rev-parse HEAD)" = "7152b75b610bada0ecc7468752900ab1515324f1"
test "$(git rev-parse origin/main)" = "7152b75b610bada0ecc7468752900ab1515324f1"
test "$(git symbolic-ref --short HEAD)" = "main"
test -z "$(git diff --cached --name-only)"
test ! -e pyproject.toml
test ! -d .github/workflows
```

If `git diff --name-only -- . ':!engineering/changes'` is non-empty, **stop**. Do not restore those product files. Do not stage them. Report the paths.

### 1. Delete superseded untracked packages (whole dirs)

```bash
rm -rf -- \
  "engineering/changes/20260816-ban-github-actions-publish-2-0-6-without-them-39b13f" \
  "engineering/changes/20260816-publish-v2-0-6-github-release-864726" \
  "engineering/changes/20260816-edit-github-release-v2-0-6-title-and-notes-b625b4" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-0f3d94" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-2a31f5" \
  "engineering/changes/20260816-user-query-гони-user-query-04ae05"
```

Confirm the dirs and any leftover `state.json` are gone:

```bash
test ! -e "engineering/changes/20260816-ban-github-actions-publish-2-0-6-without-them-39b13f"
test ! -e "engineering/changes/20260816-ban-github-actions-publish-2-0-6-without-them-39b13f/state.json"
test ! -e "engineering/changes/20260816-publish-v2-0-6-github-release-864726"
test ! -e "engineering/changes/20260816-publish-v2-0-6-github-release-864726/state.json"
test ! -e "engineering/changes/20260816-edit-github-release-v2-0-6-title-and-notes-b625b4"
test ! -e "engineering/changes/20260816-edit-github-release-v2-0-6-title-and-notes-b625b4/state.json"
test ! -e "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-0f3d94"
test ! -e "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-0f3d94/state.json"
test ! -e "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-2a31f5"
test ! -e "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-2a31f5/state.json"
test ! -e "engineering/changes/20260816-user-query-гони-user-query-04ae05"
test ! -e "engineering/changes/20260816-user-query-гони-user-query-04ae05/state.json"
```

If any of those `state.json` files reappear, `rm -f` that file. Do **not** `git add` it.

### 2. Stage keepers + this package only

Wait until this package has the analysis reports (`evidence/analysis-architect.md` and the sibling analysis files). Then add **named** KEEP dirs plus `ff295d`. Do not add `9fd274`, `cd8a96`, `ef7b14`, or any DELETE path.

```bash
git add -- \
  "engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b" \
  "engineering/changes/20260816-publish-v2-0-7-github-release-2929c0" \
  "engineering/changes/20260816-self-scan-and-fix-emerging-product-bugs-3c1039" \
  "engineering/changes/20260816-ship-working-v2-0-6-quality-contour-ec0388" \
  "engineering/changes/20260816-user-query-пересобирай-себя-под-следущей-версией-37141f" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-a13da8" \
  "engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090" \
  "engineering/changes/20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615" \
  "engineering/changes/20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-2f9f5d" \
  "engineering/changes/20260816-user-query-пиздец-ты-конченый-применяй-все-измен-ff295d"
```

`ba1615` evidence already matches `7152b75`. `git add` of that dir is a no-op unless `state.json` (or another file) is still dirty. That is the “if still dirty” case.

Expected extras this stages (confirmed local vs `7152b75` tree):

| Package | New / dirty vs HEAD |
| --- | --- |
| `5be23b` | `evidence/{code-review,implementation,test-review}.md`; `state.json` (`implementing` → `ready`) |
| `2929c0` | `evidence/{release-review,security-review}.md`; `state.json` if dirty |
| `3c1039` | `evidence/{code-review,test-review}.md`; `state.json` if dirty |
| `ec0388` | `evidence/{code-review,test-review}.md`; `state.json` if dirty |
| `37141f` | `evidence/code-review.md`; `state.json` (`implementing` → `ready`) |
| `a13da8` | `evidence/{code-review,test-review}.md`; `state.json` (`implementing` → `verifying`) |
| `ad4090` | `evidence/{implementation,code-review,test-review,*-merge}.md`; `state.json` (`implementing` → `released`) |
| `ba1615` | only if still dirty (evidence already on HEAD) |
| `d55ce4` | whole untracked package |
| `2f9f5d` | whole untracked last-mile package |
| `ff295d` | whole untracked package |

KEEP `state.json` is in scope. DELETE `state.json` is not.

### 3. Refuse a dirty index that escaped the allow-list

```bash
git diff --cached --name-only
git diff --cached --name-only | grep -E '39b13f|864726|b625b4|0f3d94|2a31f5|04ae05' && exit 1
git diff --cached --name-only | grep -v '^engineering/changes/' && exit 1
```

Every staged path must start with one of the eleven KEEP/`ff295d` directories above. If anything else is staged (`VERSION`, `packages/`, `9fd274/state.json`, a DELETE leftover, …): `git restore --staged -- <path>` for the offender only. Do **not** `git restore` the working tree of product files.

### 4. Commit

```bash
git commit -m "$(cat <<'EOF'
Record leftover keeper change-package evidence.

Drop superseded untracked drafts. Product stays 2.0.8 at 7152b75.
EOF
)"
```

Do not amend `7152b75`. Do not `--allow-empty`.

### 5. Confirm the commit is paperwork-only

```bash
test "$(cat VERSION)" = "2.0.8"
git show --name-only --pretty=format: HEAD | grep -v '^engineering/changes/' | grep -v '^$' && exit 1
git ls-tree -r --name-only HEAD | grep -E '39b13f|864726|b625b4|0f3d94|2a31f5|04ae05' && exit 1
test ! -e "engineering/changes/20260816-ban-github-actions-publish-2-0-6-without-them-39b13f"
test ! -e "engineering/changes/20260816-publish-v2-0-6-github-release-864726"
test ! -e "engineering/changes/20260816-edit-github-release-v2-0-6-title-and-notes-b625b4"
test ! -e "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-0f3d94"
test ! -e "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-2a31f5"
test ! -e "engineering/changes/20260816-user-query-гони-user-query-04ae05"
```

Working tree after this commit may still contain this package’s later review markdown. That is fine. It must not still list the DELETE dirs.

## What the write owner must not do

| Action | Why |
| --- | --- |
| Restore product files | Product is already on `origin/main` |
| `git add` DELETE leftover `state.json` | Those packages are DELETE |
| `git add` `9fd274` / `cd8a96` / `ef7b14` extras | Not KEEP |
| Push | Controller after verify + reviews + fresh production token |
| Tag / `gh release` / zip | Identity stays 2.0.8 |

## Controller last mile (not this agent)

After the implementer commit:

```bash
python3 scripts/grok_verify.py --mode pr
```

Then dispatch only `code_reviewer` and `test_reviewer`. Bind receipts:

```bash
python3 scripts/grok_review.py code_review --status pass --report engineering/changes/20260816-user-query-пиздец-ты-конченый-применяй-все-измен-ff295d/evidence/code-review.md
python3 scripts/grok_review.py test_review --status pass --report engineering/changes/20260816-user-query-пиздец-ты-конченый-применяй-все-измен-ff295d/evidence/test-review.md
python3 scripts/grok_status.py
python3 scripts/grok_change.py transition 20260816-user-query-пиздец-ты-конченый-применяй-все-измен-ff295d ready --reason "keeper evidence committed; DELETE drafts removed"
python3 scripts/grok_approve.py production --reason "user apply/delete/push: push keeper cleanup commit to origin/main; no tag no release"
GIT_TERMINAL_PROMPT=0 git -c credential.helper='!gh auth git-credential' push origin main
```

`git push` is a `PRODUCTION_INVOCATIONS` pair. Architect does not run it. Do not run `python3 scripts/grok_deploy.py` — its printer still offers `package_stack` / tag / `gh release create`.

Done when `origin/main` contains the cleanup commit, `VERSION` is still `2.0.8`, DELETE packages are absent, and no leftover DELETE `state.json` is tracked.

## Residual

- Review markdown written after the commit is not a second product commit. Receipts live under `.grok-stack/runtime/` (gitignored).
- `package_stack` still walks the live tree; this route does not rebuild the zip.
- Local git `user.name` has a trailing CR (`Dimkox\r`). Do not “fix” it in this commit.
