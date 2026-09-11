# Analysis — architect

Change: `20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2`  
Route: `33e0c2404a15` · write owner: `general_implementer` only  
Question: sequence of path-limited commands; how to avoid deleting this new change package; residual risk if the user actually wanted old zips/tags gone.

Read-only design. No product-code edits. No `.env`. Architect does **not** restore, `rm`, commit, push, merge, or deploy.

## Ruling

Working-tree cleanup only. Stay published **2.0.10**.

| Stay | Meaning |
| --- | --- |
| `HEAD` | `975ccb20dfc5fb9e925602d177069abe7e5ccfbc` |
| Tag | annotated `v2.0.10` peels to that commit (tag object `8bf2b63eba8d62b2dc36ac442f055ac627406f1d`) |
| `VERSION` | `2.0.10` |
| GitHub Release | `v2.0.10` remains Latest |
| History | tags `v2.0.0`–`v2.0.9`, GitHub Releases, tracked `packages/*v2.0.0`–`v2.0.9.zip*`, CHANGELOG `## 2.0.0`–`## 2.0.9`, tracked change packages |

Do **not** create a commit. Do **not** `git clean -fd` at repo root. Do **not** delete this package (`33e0c2`).

Interpretation of «оставь только 2.0.10 в гите» **for this route**: porcelain is clean except this active untracked package. It does **not** mean rewrite history so older tags/zips disappear.

## Inventory vs `975ccb2`

Compared local files to the GitHub tree of `975ccb20dfc5fb9e925602d177069abe7e5ccfbc`. Only one whole untracked change dir exists: **this** `33e0c2` package. Keep it.

### Restore — 3 dirty tracked `state.json`

| Path | HEAD | Working tree |
| --- | --- | --- |
| `engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/state.json` | `ready` @ `2026-08-16T23:56:47Z` | `released` @ `2026-08-16T23:58:33Z` (extra GitHub Release step) |
| `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/state.json` | `implementing` @ `2026-08-16T23:14:30Z` | `ready` @ `2026-08-16T23:22:24Z` |
| `engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/state.json` | `implementing` @ `2026-08-16T23:29:27Z` | `verifying` @ `2026-08-16T23:29:38Z` |

`06a59f/state.json` already matches HEAD (`implementing`). Do not restore that file.

`70b284/evidence/*` is already on HEAD (8 files). Do **not** delete any file in that evidence dir.

### Delete — untracked sibling evidence only

HEAD evidence vs disk:

**`e61f9d/evidence/`** — HEAD has `README.md`, `analysis-repo_explorer.md`. Untracked:

- `analysis-architect.md`
- `analysis-docs_researcher.md`
- `analysis-task_analyst.md`
- `code-review.md`
- `implementation.md`
- `test-review.md`

**`8fe260/evidence/`** — HEAD has `README.md`, `human-approval.md`. Untracked:

- `analysis-architect.md`
- `analysis-docs_researcher.md`
- `analysis-repo_explorer.md`
- `release-review.md`
- `security-review.md`

**`06a59f/evidence/`** — HEAD has `README.md`, `human-approval.md`. `state.json` clean. Untracked leftover from the superseded 2.0.9 last-mile:

- `analysis-architect.md`
- `analysis-docs_researcher.md`
- `analysis-repo_explorer.md`
- `release-review.md`
- `security-review.md`

Keep the tracked evidence files in those three dirs. Delete only the untracked names above.

## How to avoid deleting this new change package

The danger is `git clean` / a glob, not `git restore`. This whole tree is untracked:

`engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/`

| Safe | Unsafe (would wipe `33e0c2`) |
| --- | --- |
| `git restore --` of the 3 named `state.json` only | `git clean -fd`, `git clean -fd .`, `git clean -fdx` |
| `rm --` of the 16 named sibling evidence files | `git clean -fd -- engineering/changes` |
| Discover leftover `??` then `rm` only if path is sibling `…/evidence/…` **and** does not start with `KEEP` | `rm -rf engineering/changes/*` or `rm -rf engineering/changes/20260817*` |
| After every step: `test -d "$KEEP"` | `git restore .` / `git checkout -- .` / `git reset --hard` (too broad; hard reset also is not needed) |

Define once and never pass `KEEP` to `rm` or `git clean`:

```bash
KEEP="engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2"
```

That dir will still be `??` in `git status` when cleanup finishes. That is required. Committing it would leave `HEAD` ≠ `975ccb2` and stop being “only 2.0.10”.

## Hard forbids

Write owner must not run or touch:

- `git commit`, `git commit --amend`, `git add` of anything
- `git push`, `git push --force`, `git push origin :refs/tags/*`
- `git tag -d`, `git tag -a`, retag of `v2.0.10` or older
- `gh release delete`, `gh release create`, `gh release edit`
- `git clean` in any form (`-f`, `-fd`, `-fdx`, path-limited clean of `engineering/changes`)
- `git reset --hard`, `git reset --merge`, `git checkout -- .`, `git restore .`, `git restore -- engineering/changes`
- `rm` of `$KEEP` or any path under it (including this report and sibling analysis files landing now)
- `rm` of tracked evidence (`70b284/evidence/*`, `e61f9d/evidence/{README.md,analysis-repo_explorer.md}`, `8fe260/evidence/{README.md,human-approval.md}`, `06a59f/evidence/{README.md,human-approval.md}`)
- Product / identity: `VERSION`, `README.md`, `CHANGELOG.md`, `AGENTS.md`, `QUICKSTART.md`, `decisions.md`, `mistakes.md`, `packages/**`, `dist/**`, `engineering/runbooks/**`
- Tracked change-package markdown/json except the 3 restore targets
- `.env`, keys, credential stores
- `.github/`, `pyproject.toml`, `requirements.txt`, `setup.py`
- `python3 scripts/package_stack.py`, `python3 scripts/grok_deploy.py`

## Exact implementer commands

Stop if any precondition fails. Repo root. Owner is `general_implementer` only. Quote every Cyrillic path.

### 0. Identity

```bash
KEEP="engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2"

test "$(cat VERSION)" = "2.0.10"
test "$(git rev-parse HEAD)" = "975ccb20dfc5fb9e925602d177069abe7e5ccfbc"
test "$(git rev-parse --verify 'v2.0.10^{commit}')" = "975ccb20dfc5fb9e925602d177069abe7e5ccfbc"
test "$(git rev-parse --verify 'v2.0.9^{commit}')" = "f72c0fc2bb27de5dee67f799517f71cd678eb068"
test "$(git rev-parse --verify 'v2.0.8^{commit}')" = "02842413509dc98eaaf104e27f212888f9449826"
test "$(git symbolic-ref --short HEAD)" = "main"
test -z "$(git diff --cached --name-only)"
test -d "$KEEP"
test ! -e pyproject.toml
test ! -d .github/workflows
test -f packages/adaptive-grok-build-pro-v2.0.10.zip
test -f packages/adaptive-grok-build-pro-v2.0.9.zip
test -f packages/adaptive-grok-build-pro-v2.0.0.zip
```

If `git diff --name-only -- . ':!engineering/changes'` is non-empty: **stop**. Do not restore product files. Report the paths.

### 1. Restore the 3 dirty `state.json`

```bash
git restore --source=HEAD --worktree -- \
  "engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/state.json" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/state.json" \
  "engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/state.json"

test -d "$KEEP"
test -z "$(git diff --name-only -- \
  "engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/state.json" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/state.json" \
  "engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/state.json")"
```

Do not `git restore` those package directories. Untracked evidence would remain anyway; restoring extra tracked files is out of scope.

### 2. Delete named untracked sibling evidence

```bash
rm -f -- \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/analysis-architect.md" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/analysis-docs_researcher.md" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/analysis-task_analyst.md" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/code-review.md" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/implementation.md" \
  "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/test-review.md" \
  "engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/analysis-architect.md" \
  "engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/analysis-docs_researcher.md" \
  "engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/analysis-repo_explorer.md" \
  "engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/release-review.md" \
  "engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/security-review.md" \
  "engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/analysis-architect.md" \
  "engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/analysis-docs_researcher.md" \
  "engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/analysis-repo_explorer.md" \
  "engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/release-review.md" \
  "engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/security-review.md"

test -d "$KEEP"
test -f "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/README.md"
test -f "engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/analysis-repo_explorer.md"
test -f "engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/README.md"
test -f "engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/human-approval.md"
test -f "engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/README.md"
test -f "engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/human-approval.md"
test -f "engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/evidence/release-review.md"
```

`-f` is only so a race-deleted name does not abort the rest of this fixed list. Never turn that into a glob.

### 3. Sweep leftover sibling `??` evidence (exclude `KEEP`)

```bash
python3 - <<'PY'
import subprocess
from pathlib import Path

keep = Path("engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2")
out = subprocess.check_output(
    ["git", "status", "--porcelain", "--untracked-files=all", "--", "engineering/changes"],
    text=True,
)
leftover_evidence = []
other = []
for line in out.splitlines():
    if not line.startswith("??"):
        # modified tracked leftovers after restore should be empty
        if line[3:] and not line[3:].startswith(str(keep)):
            other.append(line)
        continue
    path = Path(line[3:])
    if path == keep or keep in path.parents or str(path).startswith(str(keep)):
        continue
    if path.parent.name == "evidence":
        leftover_evidence.append(str(path))
    else:
        other.append(line)

print("LEFTOVER_EVIDENCE")
for p in leftover_evidence:
    print(p)
print("OTHER")
for p in other:
    print(p)
if leftover_evidence:
    raise SystemExit(2)
if other:
    raise SystemExit(3)
PY
```

- Exit `2`: extra sibling evidence appeared (parallel writer, missed file). Print the list. `rm --` **only** those `…/evidence/…` paths. Re-run the sweep. Never `rm` a path under `KEEP`.
- Exit `3`: unexpected dirty/untracked path (package root, `packages/`, etc.). **Stop.** Do not guess.
- Exit `0`: only `KEEP` remains untracked under `engineering/changes/`. That is success.

### 4. Accept the leftover `33e0c2` package

```bash
test "$(git rev-parse HEAD)" = "975ccb20dfc5fb9e925602d177069abe7e5ccfbc"
test "$(cat VERSION)" = "2.0.10"
test -d "$KEEP"
test -f "$KEEP/state.json"
test -f "$KEEP/evidence/analysis-architect.md"

# porcelain excluding this package must be empty
test -z "$(git status --porcelain --untracked-files=all -- . \
  ":!engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2")"

git describe --tags --exact-match HEAD
# expect: v2.0.10
```

Do **not** `git add` `$KEEP`. Do **not** commit. Write `evidence/implementation.md` **inside `$KEEP` only** after the commands succeed.

No new product test. Cleanup has no behavior change; the characterization is the `test`/`git status` block above. Then `python3 scripts/grok_verify.py --mode pr`.

## Rollback

Nothing is committed. Recovery is local only.

| If this happened | Undo |
| --- | --- |
| Restored the 3 `state.json` | Already HEAD. No action. To re-dirty is out of scope. |
| `rm` of the 16 untracked evidence files | Git cannot restore them. They were not on `975ccb2`. Accept the loss. Do not copy from chat into sibling packages. |
| Accidentally `git restore` extra tracked files | `git restore --source=HEAD --worktree -- <that-path>` again (already HEAD). |
| Accidentally deleted `$KEEP` | **Stop.** Recreate from the change-package templates + this report if still in the session. Do not invent a new change id. |
| `git clean -fd` at root | May have deleted `$KEEP` and any other untracked work. Stop. Do not continue this route blindly. |
| Accidental commit | Do **not** force-push. Stop for a human. Soft-reset only if the commit exists only locally and a human says so. This design does not authorize that. |
| Accidental tag/release delete | Out of this route. Irreversible remote tag delete needs a later high-risk route + explicit approval. |

Do not force-push. Do not retag.

## Residual risk — if the user wanted old zips/tags gone

Literal reading of «оставь только 2.0.10» can mean “erase 2.0.0–2.0.9 from git.” **That is a later route**, not this one.

After this cleanup the user will still see:

- tags `v2.0.0` … `v2.0.9` (and their annotated objects)
- GitHub Releases for those tags (Latest stays `v2.0.10`)
- tracked `packages/adaptive-grok-build-pro-v2.0.{0..9}.zip*`
- CHANGELOG sections `## 2.0.0` … `## 2.0.9`
- `packages/README.md` table rows for those zips
- historical `engineering/changes/*` and `engineering/runbooks/publish-v2.0.{4..9}.md`

Why this route must not do that work:

1. Deleting remote tags / `gh release delete` is irreversible production mutation. This feature route has no `production_action_approval` gate.
2. Removing tracked old zips requires a **new commit**. Then `HEAD` ≠ `975ccb2` and `v2.0.10` no longer matches “current tree.” That violates “stay 2.0.10.”
3. History rewrite (`filter-repo`, orphan branch, force-push) is forbidden routine action.
4. Docs-researcher: product docs stay frozen; the zip table and CHANGELOG history are the published record of 2.0.10.

If the user repeats the request after a clean working tree, open a **new high-risk** route with explicit scope (which tags, which GitHub Releases, whether to keep the zips on `main`). Do not stretch this implementer sequence.

## Files the implementer may touch

| Action | Paths |
| --- | --- |
| `git restore` | the 3 `state.json` listed in §1 |
| `rm` | the 16 sibling evidence files listed in §2, plus any sweep hit from §3 that is sibling `…/evidence/…` and not under `KEEP` |
| write (after cleanup) | `$KEEP/evidence/implementation.md` and later review reports under `$KEEP/evidence/` only |

Everything else is forbidden to touch.

## Done when

- `HEAD` is still `975ccb20dfc5fb9e925602d177069abe7e5ccfbc` / `v2.0.10`
- `VERSION` is still `2.0.10`
- tags still peel to `02842413509dc98eaaf104e27f212888f9449826` / `f72c0fc2bb27de5dee67f799517f71cd678eb068` / `975ccb20dfc5fb9e925602d177069abe7e5ccfbc`
- no sibling dirty `state.json` or untracked sibling evidence
- `$KEEP` still exists and is the only porcelain leftover
- no commit, no tag change, no GitHub Release change
