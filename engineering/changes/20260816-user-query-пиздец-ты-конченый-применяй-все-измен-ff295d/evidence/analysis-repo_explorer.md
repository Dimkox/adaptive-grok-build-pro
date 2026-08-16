# Analysis — repo_explorer

Change: `20260816-user-query-пиздец-ты-конченый-применяй-все-измен-ff295d`  
Route: `ff295dada3ef` · HEAD / `origin/main`: `7152b75b610bada0ecc7468752900ab1515324f1`  
Question: for every dirty or untracked `engineering/changes/*` package **except this `ff295d` package**, KEEP (commit remaining files) or DELETE (rm -rf untracked leftover / restore committed files to HEAD).

Product is already shipped. This is paperwork cleanup only. No product files, tags, or GitHub Releases in this ruling.

## How dirt was established

This agent has no shell. Dirt vs `7152b75` is from:

1. GitHub tree of `engineering/changes` at `7152b75` (same SHA as local `.git/refs/heads/main` and `.git/refs/remotes/origin/main`).
2. Per-package GitHub file lists vs local `list_dir`.
3. Raw HEAD `state.json` / `requirements.md` vs the working copies.
4. `grok_verify` `changed_files` at `.grok-stack/runtime/receipts/2f9f5d5bc202/verification.json` (`2026-08-16T22:51:44Z`). That list is the union of `git diff <route-base>...HEAD` **and** unstaged **and** untracked, so committed `7152b75` paths also appear. File-list compare against the GitHub tree is what separates “in HEAD” from leftover dirt.

`ff295d` is the active package and is excluded from the table.

## Rule of action

| Ruling | Implementer action |
| --- | --- |
| **KEEP extras** | Path-limited `git add` of the listed untracked files and dirty tracked files. Leave the already-committed HEAD copy of the package. |
| **KEEP whole dir** | Path-limited `git add` of the entire untracked package. |
| **DELETE whole dir** | `rm -rf` the untracked directory. None of the DELETE rows have tracked files on `7152b75`. |
| **CLEAN** | No action. Listed only so “ba1615 if dirty” is answered. |

Do not `git add -A`. Do not restore tracked files on KEEP rows. Do not touch product paths (`AGENTS.md`, `README.md`, `VERSION`, `packages/`, tests).

## KEEP / DELETE table

| Suffix | Package | On `7152b75`? | Dirt | Ruling | Why |
| --- | --- | --- | --- | --- | --- |
| `5be23b` | `20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b` | yes | extras | **KEEP extras** | Shipped 2.0.6 ban commit `e75f3a1`. Local reviews + ready `state.json` are the missing ship evidence. |
| `2929c0` | `20260816-publish-v2-0-7-github-release-2929c0` | yes | extras | **KEEP extras** | Shipped 2.0.7 identity `02376cc`. Local release/security reviews + ready `state.json` are the missing ship evidence. |
| `3c1039` | `20260816-self-scan-and-fix-emerging-product-bugs-3c1039` | yes | extras | **KEEP extras** | Shipped leftover fixes `11da31a`. Local reviews + ready `state.json` are the missing ship evidence. |
| `ec0388` | `20260816-ship-working-v2-0-6-quality-contour-ec0388` | yes | extras | **KEEP extras** | Shipped 2.0.6 contour `549f29d`. Local reviews + ready `state.json` are the missing ship evidence. |
| `37141f` | `20260816-user-query-пересобирай-себя-под-следущей-версией-37141f` | yes | extras | **KEEP extras** | Shipped 2.0.8 rebuild `22762a77`. Local code-review + ready `state.json` are the missing ship evidence. |
| `a13da8` | `20260816-the-user-sent-a-message-while-you-were-working-u-a13da8` | yes | extras | **KEEP extras** | This is the `7152b75` README/K10 commit. Local reviews + verifying `state.json` are the missing ship evidence. |
| `ad4090` | `20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090` | yes | extras | **KEEP extras** | Real 2.0.5 publish package. Local merge/review/implementation files plus released `state.json` and filled `requirements.md` are the missing ship evidence. |
| `2f9f5d` | `20260816-the-user-sent-a-message-while-you-were-working-u-2f9f5d` | **no** | whole dir untracked | **KEEP whole dir** | Last-mile that authorized the CLI push of `7152b75`. `origin/main` is now that SHA. Status `ready`; has analysis + human-approval + release/security reviews. |
| `d55ce4` | `20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4` | **no** | whole dir untracked | **KEEP whole dir** | Investigation that found the self-learning bullets were never in any committed `AGENTS.md`, then restored them. Product landed in `22762a77`; the package itself was never committed. Status `ready`; has analysis + implementation + reviews. |
| `ba1615` | `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615` | yes | **none** | **CLEAN — no action** | On HEAD. Local evidence names match the `7152b75` tree. Local `state.json` is byte-identical to HEAD (`ready` @ `22:19:03`). It only appears in verify lists because those lists include `base...HEAD`. |
| `39b13f` | `20260816-ban-github-actions-publish-2-0-6-without-them-39b13f` | **no** | whole dir untracked | **DELETE whole dir** | Abandoned first GHA-ban attempt. Status still `draft`; evidence is analysis stubs only. Superseded by shipped `5be23b` / `9fd274`. |
| `864726` | `20260816-publish-v2-0-6-github-release-864726` | **no** | whole dir untracked | **DELETE whole dir** | Abandoned first 2.0.6 GitHub Release attempt. Status still `draft`; no implementation. Superseded by shipped `5be23b` then `2929c0`. |
| `b625b4` | `20260816-edit-github-release-v2-0-6-title-and-notes-b625b4` | **no** | whole dir untracked | **DELETE whole dir** | Last-mile note edit for the now-superseded 2.0.6 GitHub Release object. Product identity moved on to 2.0.7 / 2.0.8. Durable record is GitHub, not this leftover dir. |
| `0f3d94` | `20260816-the-user-sent-a-message-while-you-were-working-u-0f3d94` | **no** | whole dir untracked | **DELETE whole dir** | Interrupted “did you update README?” route. Status `draft`; analysis stubs only. Superseded by shipped `a13da8` (`7152b75`). |
| `2a31f5` | `20260816-the-user-sent-a-message-while-you-were-working-u-2a31f5` | **no** | whole dir untracked | **DELETE whole dir** | Interrupted Bitvise-GUI rant. Status `approved`, no implementation. Superseded by `2f9f5d` (CLI last mile; Bitvise called a false alarm). |
| `04ae05` | `20260816-user-query-гони-user-query-04ae05` | **no** | whole dir untracked | **DELETE whole dir** | Abandoned “гони” push of the ba1615 tree. Status `approved`; analysis stubs only; never pushed. Superseded by `a13da8` + `2f9f5d` (`7152b75` is already on `origin/main`). |

## Exact KEEP paths

Path-limited add. Do not add DELETE dirs. Do not add `ff295d`.

### `5be23b` extras

Untracked:

- `engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b/evidence/code-review.md`
- `engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b/evidence/implementation.md`
- `engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b/evidence/test-review.md`

Dirty vs HEAD (`implementing` → `ready`):

- `engineering/changes/20260816-finish-2-0-6-commit-ban-verify-github-release-5be23b/state.json`

HEAD already has the analysis files and `human-approval.md`.

### `2929c0` extras

Untracked:

- `engineering/changes/20260816-publish-v2-0-7-github-release-2929c0/evidence/release-review.md`
- `engineering/changes/20260816-publish-v2-0-7-github-release-2929c0/evidence/security-review.md`

Dirty vs HEAD (`implementing` → `ready`):

- `engineering/changes/20260816-publish-v2-0-7-github-release-2929c0/state.json`

### `3c1039` extras

Untracked:

- `engineering/changes/20260816-self-scan-and-fix-emerging-product-bugs-3c1039/evidence/code-review.md`
- `engineering/changes/20260816-self-scan-and-fix-emerging-product-bugs-3c1039/evidence/test-review.md`

Dirty vs HEAD (`implementing` → `ready`):

- `engineering/changes/20260816-self-scan-and-fix-emerging-product-bugs-3c1039/state.json`

HEAD already has `implementation.md` and `analysis-repo_explorer.md`.

### `ec0388` extras

Untracked:

- `engineering/changes/20260816-ship-working-v2-0-6-quality-contour-ec0388/evidence/code-review.md`
- `engineering/changes/20260816-ship-working-v2-0-6-quality-contour-ec0388/evidence/test-review.md`

Dirty vs HEAD (`implementing` → `ready`):

- `engineering/changes/20260816-ship-working-v2-0-6-quality-contour-ec0388/state.json`

HEAD already has analysis, `implementation.md`, `coverage-baseline.md`, `ruff-first-run.md`.

### `37141f` extras

Untracked:

- `engineering/changes/20260816-user-query-пересобирай-себя-под-следущей-версией-37141f/evidence/code-review.md`

Dirty vs HEAD (`implementing` → `ready`):

- `engineering/changes/20260816-user-query-пересобирай-себя-под-следущей-версией-37141f/state.json`

HEAD already has `analysis-repo_explorer.md` and `implementation.md`.

### `a13da8` extras

Untracked:

- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-a13da8/evidence/code-review.md`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-a13da8/evidence/test-review.md`

Dirty vs HEAD (`implementing` @ `22:33:00` → `verifying` @ `22:38:01`):

- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-a13da8/state.json`

HEAD already has the analysis files and `implementation.md`. The rest of the package is the `7152b75` commit itself.

### `ad4090` extras

Untracked (not on the `7152b75` evidence tree):

- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/analysis-architect-merge.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/analysis-docs_researcher-merge.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/analysis-repo_explorer-merge.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/analysis-task_analyst-merge.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/code-review-merge.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/code-review.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/implementation.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/test-review-merge.md`
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/evidence/test-review.md`

Dirty vs HEAD:

- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/state.json` — HEAD `implementing` @ `02:40:00`; local `released` @ `2026-08-16T16:20:01` (“v2.0.5 tag pushed and GitHub Release published”).
- `engineering/changes/20260815-user-query-гит-пуш-пакет-релиз-user-query-ad4090/requirements.md` — HEAD has all boxes unchecked; local has zip / ignore boxes checked.

HEAD already has README, the non-`-merge` analysis files, the two `*-continue.md` files, and `human-approval.md`.

### Whole untracked KEEP dirs

Add the entire directories:

- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-2f9f5d/`
- `engineering/changes/20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4/`

## Exact DELETE paths

`rm -rf` only these untracked dirs (none exist on `7152b75`):

- `engineering/changes/20260816-ban-github-actions-publish-2-0-6-without-them-39b13f/`
- `engineering/changes/20260816-publish-v2-0-6-github-release-864726/`
- `engineering/changes/20260816-edit-github-release-v2-0-6-title-and-notes-b625b4/`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-0f3d94/`
- `engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-2a31f5/`
- `engineering/changes/20260816-user-query-гони-user-query-04ae05/`

No `git checkout --` is required for DELETE rows: there is no HEAD copy.

## Clean packages (not in the KEEP/DELETE work)

Present on `7152b75` and absent from leftover dirt (not in the 22:51 extras set; file lists were not showing extra local evidence):

`2eacdf`, `bf62a5`, `58e51e`, `6d15cb`, `b8b188`, `757a43`, `b082cf`, `e86e93`, `14464b`, `99b743`, `e1d4a6`, `8abd64`, `bb6ab3`, `19fc56`, `e584b3`, `3ac76c`, `aea9d4`, `661035`, `9fd274`, `cd8a96`, `ef7b14`, and `ba1615`.

Do not restage or delete those.

## Out of this ruling

- This `ff295d` package (write it last, after KEEP/DELETE is applied).
- `.grok-stack/runtime/**`, `dist/`, `err.log`, `.env`, coverage artifacts.
- Product tree. HEAD `7152b75` already is the shipped tree.

## Residual

- No live `git status`. If the implementer sees a dirty `engineering/changes/*` path not named above, treat it as unverified and stop rather than guessing.
- `b625b4` did run `gh release edit` on v2.0.6. DELETE still applies: the release object is the record, and later 2.0.7 / 2.0.8 identities superseded that paperwork.
- `2f9f5d` brief said `origin/main` was one commit behind at 22:43. Local `origin/main` is now `7152b75`, so that push already happened. KEEP the package as evidence, do not push again from this ruling.
