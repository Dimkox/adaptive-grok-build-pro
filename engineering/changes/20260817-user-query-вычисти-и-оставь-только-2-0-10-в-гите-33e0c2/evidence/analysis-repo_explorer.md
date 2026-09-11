# Analysis — repo_explorer

Change: `20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2`  
Route: `33e0c2404a15` · write owner: `general_implementer` · reviews: `code_reviewer` + `test_reviewer`

Narrow question: exact `git restore` paths and exact untracked sibling evidence paths to delete. Confirm no product pin needs the dirt. Confirm deleting remote tags or old zips is **not** this cleanup.

---

## Ruling

**Confirm the controller ruling.** Clean the working tree to committed `v2.0.10` (`975ccb20dfc5fb9e925602d177069abe7e5ccfbc`). Restore 3 tracked `state.json` files. Delete 22 untracked sibling evidence files. Do not delete tags, GitHub Releases, historical zips, CHANGELOG sections, or tracked change packages. Do not force-push. Do not bump `VERSION`. Do not commit. Do not `git clean -fd` at repo root.

After this cleanup, `HEAD` stays `975ccb2`. `git status` may still show **this** change package (`…-33e0c2/`) as untracked. That is required: committing it would leave `main` off the published tag.

---

## Facts inspected

| Item | Value |
| --- | --- |
| `refs/heads/main` | `975ccb20dfc5fb9e925602d177069abe7e5ccfbc` |
| `refs/remotes/origin/main` | same SHA |
| Annotated tag `v2.0.10` | object `8bf2b63e…` peels to `975ccb2` |
| Annotated tag `v2.0.9` | object `020921e7…` peels to `f72c0fc2bb27de5dee67f799517f71cd678eb068` |
| Annotated tag `v2.0.8` | object `695ee791…` peels to `02842413509dc98eaaf104e27f212888f9449826` |
| Local tags | `v2.0.0`–`v2.0.10` present |
| GitHub Release `v2.0.10` | Latest; published `2026-08-16T23:58:16Z`; zip `1b2ae2a3…` |
| GitHub Releases | `v2.0.0`–`v2.0.10` all exist |
| `VERSION` | `2.0.10` |
| Product tests | `tests/test_structure.py` and `tests/test_manifest_package.py` lock `2.0.10` |
| Tracked change packages at HEAD | 39 (this `33e0c2` dir is **not** on `975ccb2`; GitHub contents 404) |
| Tracked zips | `packages/adaptive-grok-build-pro-v2.0.0.zip` … `v2.0.10.zip` + `.sha256` |

Compared local `engineering/changes/**/evidence` and the three dirty `state.json` files against the GitHub tree at `975ccb2`.

---

## Restore (`git restore --`)

Exactly these 3 tracked files. Local copies drifted after the tag:

| Path | HEAD (`975ccb2`) | Working tree |
| --- | --- | --- |
| `engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/state.json` | `status=ready`, `updated_at=2026-08-16T23:56:47+00:00` | `status=released` + extra history at `23:58:33` |
| `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/state.json` | `status=implementing`, `updated_at=2026-08-16T23:14:30+00:00` | `status=ready` + verifying/reviewing/ready rows |
| `engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/state.json` | `status=implementing`, `updated_at=2026-08-16T23:29:27+00:00` | `status=verifying` + extra row at `23:29:38` |

Checked and **not** dirty (do not restore):

- `…-06a59f/state.json` matches HEAD (`implementing`)
- `…-e4afbb/state.json` matches HEAD (`draft`)
- `…-f1bdb9/state.json` matches HEAD (`implementing`)

```bash
git restore -- \
  engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/state.json \
  engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/state.json \
  engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/state.json
```

---

## Delete (untracked sibling evidence only)

22 files. Present locally, absent from tree `975ccb2`. Path-limited `rm -f` only. Do not delete tracked evidence (including all 8 files under `70b284/evidence/`).

### `…-e61f9d/` (HEAD has only `README.md` + `analysis-repo_explorer.md`) — 6

- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/analysis-architect.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/analysis-docs_researcher.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/analysis-task_analyst.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/code-review.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/implementation.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/evidence/test-review.md`

### `…-8fe260/` (HEAD has only `README.md` + `human-approval.md`) — 5

- `engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/analysis-architect.md`
- `engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/analysis-docs_researcher.md`
- `engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/analysis-repo_explorer.md`
- `engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/release-review.md`
- `engineering/changes/20260816-user-query-так-пуш-и-новая-версия-релиза-сука-да-8fe260/evidence/security-review.md`

### `…-06a59f/` (HEAD has only `README.md` + `human-approval.md`) — 5

- `engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/analysis-architect.md`
- `engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/analysis-docs_researcher.md`
- `engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/analysis-repo_explorer.md`
- `engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/release-review.md`
- `engineering/changes/20260816-user-query-релиз-сделай-user-query-06a59f/evidence/security-review.md`

### `…-f1bdb9/` (HEAD has `README.md` + `analysis-repo_explorer.md` + `implementation.md`) — 3

- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-f1bdb9/evidence/analysis-architect.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-f1bdb9/evidence/analysis-docs_researcher.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-f1bdb9/evidence/analysis-task_analyst.md`

### `…-e4afbb/` (HEAD has only `README.md` + `human-approval.md`) — 3

- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e4afbb/evidence/analysis-architect.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e4afbb/evidence/analysis-docs_researcher.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e4afbb/evidence/analysis-repo_explorer.md`

Total: **22**. Matches the controller’s “~22 untracked evidence files.”

Do **not** delete:

- Any file under `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/` (this package; leave uncommitted)
- Tracked evidence under `70b284`, `2f9f5d`, `a13da8`, `79f406`, `37141f`, `ff295d`, `ba1615`, `d55ce4`, or older packages (local listings match `975ccb2`)

---

## No product pin requires the dirty files

- `tests/`, `scripts/`, and `.grok-stack/adaptive_grok/` have **zero** hits for `70b284`, `e61f9d74d5c2`, or `8fe260c5f5c5`.
- Product identity is `VERSION` + README H1 + `test_version_is_2_0_10_and_github_actions_are_absent`. Those files are clean and already `2.0.10`.
- `managed.json` / installer do not consume sibling change-package `state.json` or leftover analysis markdown.
- `packages/README.md` documents historical zips as **tracked published artifacts**, not as this session’s dirt.
- Restoring `70b284/state.json` from `released` back to committed `ready` does not unpublish GitHub Release `v2.0.10`. The release already exists on tag `v2.0.10`.

---

## What must stay (this cleanup is **not** history rewrite)

Deleting any of the following would **not** be this cleanup:

- Local or remote tags `v2.0.0`–`v2.0.10` (`git tag -d`, `git push origin :refs/tags/…`)
- GitHub Releases (`gh release delete`)
- Tracked zips `packages/adaptive-grok-build-pro-v2.0.0.zip*` through `v2.0.9.zip*` (and `v2.0.10.zip*`)
- `dist/` scratch (gitignored; not the dirt)
- CHANGELOG sections `## 2.0.0`–`## 2.0.10`
- The 39 tracked change packages under `engineering/changes/`
- `VERSION` (`2.0.10`)
- `HEAD` / `origin/main` at `975ccb2`
- This uncommitted `33e0c2` package
- `.gitignore`d runtime (`.grok-stack/runtime/*`), `err.log`, `__pycache__/`

A `git clean -fd` at repo root would wipe this package and other ignored/untracked work. Path-limited `rm -f` of the 22 files only.

---

## Implementer sequence

1. `git restore` the 3 paths above.
2. `rm -f` the 22 paths above.
3. Do not add, commit, tag, push, or bump `VERSION`.
4. Expect: `git rev-parse HEAD` still `975ccb2`; `git describe --tags --exact-match` still `v2.0.10`; porcelain dirty only for `…-33e0c2/` (and ignored runtime).

This report is design. It is not a verification or review receipt.
