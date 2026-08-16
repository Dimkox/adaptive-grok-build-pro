# Code review — move agent-prompt logs to the repo root

Change: `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615`  
Route: `ba1615416da5` · reviewer: `code_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-16  
Base: `22762a77ea4133cc34398f9a70194daa427bd096` (`Release v2.0.8`, `HEAD` == `origin/main`)

**PASS.** I would not block.

The working tree relocates the live logs to the repo root, keeps every prior dated entry, retargets the first `AGENTS.md` section to the original prompt filenames, and leaves short pointers at the old `engineering/` paths. Structure tests now lock the root files, the exact phrases, and stub shortness. `VERSION` is still `2.0.8`. There is no GitHub Actions tree and no `pyproject.toml`.

---

## Verdict against acceptance

| # | Criterion | Result |
| --- | --- | --- |
| 1 | Root `decisions.md` and `mistakes.md` exist and keep prior dated entries | **PASS** (13 prior decision `##` bodies + 3 prior mistake `##` bodies byte-identical vs `22762a77` `engineering/` copies; one new dated entry prepended to each) |
| 2 | `AGENTS.md` first section uses `log it in decisions.md` / `record it in mistakes.md` (no `engineering/` prefix) | **PASS** (`AGENTS.md:5-6`; first `##` remains `## Agent self-learning`) |
| 3 | `engineering/` copies are short pointers only | **PASS** (3 lines each; no `## 20*` entries; “Do not append here”) |
| 4 | Structure tests lock root files + exact phrases + stub shortness | **PASS** (`test_agents_md_starts_with_self_learning` + sibling `test_engineering_self_learning_stubs_are_pointers`) |
| 5 | `VERSION` still `2.0.8`; no GHA; no `pyproject.toml` | **PASS** |

Would I block? **No.**

---

## What was actually inspected

Did not trust `evidence/implementation.md` alone. Compared the working tree to GitHub raw of `22762a77` plus this change package (`brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `rollback.md`, `evidence/analysis-architect.md`). This session has no shell, so there is no live `git diff` / `unittest` / `ruff`. Equivalents below.

```text
# refs
.git/HEAD                     → ref: refs/heads/main
.git/refs/heads/main          → 22762a77ea4133cc34398f9a70194daa427bd096
.git/refs/remotes/origin/main → 22762a77ea4133cc34398f9a70194daa427bd096
.git/COMMIT_EDITMSG           → Release v2.0.8: AGENTS.md self-learning first, rebuild zip

# contracts
engineering/changes/…-ba1615/{brief,requirements,architecture,test-plan,tasks,release,rollback}.md
engineering/changes/…-ba1615/{route,state}.json
engineering/changes/…-ba1615/evidence/{analysis-architect,analysis-task_analyst,analysis-repo_explorer,analysis-docs_researcher,implementation}.md

# product delta vs 22762a77 (GitHub raw + working tree)
decisions.md                  NEW at root = old engineering/decisions.md + one 2026-08-16 move entry
mistakes.md                   NEW at root = old engineering/mistakes.md + one 2026-08-16 hide-under-engineering/ entry
engineering/decisions.md      full log → 3-line pointer
engineering/mistakes.md       full log → 3-line pointer
AGENTS.md                     two bullets only: drop engineering/ prefix
tests/test_structure.py       retarget self-learning lock; add stub-pointer test

# unchanged on purpose
VERSION                       2.0.8
.grok-stack/adaptive_grok/__init__.py  __version__ = "2.0.8"
CHANGELOG.md                  §2.0.8 still names engineering/ (2.0.8 ship record; architect ruling)
scripts/install_into.py       MANAGED_FILES / ENSURE still do not seed either log
scripts/package_stack.py      no special-case (not touched)
.grok-stack/adaptive_grok/**  no decisions.md / mistakes.md strings

# absences
pyproject.toml / requirements.txt / setup.py   do not exist
.github/                                       directory missing
.github/dependabot.yml                         missing
.grok-stack/templates/ci/github-actions.yml    missing
```

---

## Diff reviewed

### `AGENTS.md` (two-bullet retarget only)

Base `22762a77` first section:

```markdown
- If you make a decision that turns out to be correct and worth the effort, log it in engineering/decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in engineering/mistakes.md.
```

Working tree:

```5:6:AGENTS.md
- If you make a decision that turns out to be correct and worth the effort, log it in decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in mistakes.md.
```

Prefix before `## Mandatory entrypoint` contains the required phrases and does **not** contain `engineering/decisions.md` or `engineering/mistakes.md`. Heading order is unchanged (`## Agent self-learning` first). The rest of the Engineering Contract matches `22762a77` line-for-line.

### Root logs keep prior entries

Compared working-tree `decisions.md` / `mistakes.md` to GitHub raw of `22762a77:engineering/decisions.md` and `22762a77:engineering/mistakes.md`.

`decisions.md` still has, in order, with the same bodies:

- `## 2026-08-16 — Pin tests after bump, pack after VERSION`
- `## 2026-08-16 — Never GitHub Actions`
- `## 2026-08-16 — Ruff lives in ruff.toml, not pyproject.toml`
- `## 2026-08-15 — Ten is a read-only ceiling`
- `## 2026-08-15 — Root hook shims fail-open after pull`
- `## 2026-08-15 — Commercial product, free, MIT`
- `## 2026-08-15 — MIT public, not a paid SKU`
- `## 2026-08-15 — SubagentStop must emit empty JSON`
- `## 2026-08-15 — Unwrap one `-c` layer; reuse follow-ups only if open and same session`
- `## 2026-08-14 — Match production side-effects as argv prefixes`
- `## 2026-08-14 — Rematch every non-follow-up; skip child briefs`
- `## 2026-08-14 — Run unittest from verify without a packaging marker`
- `## 2026-08-14 — Bind receipts after the last change-package write`

`mistakes.md` still has the three pre-move sections, including the historical symptom that names `engineering/…` (left alone, as architect required):

- `## 2026-08-16 — Self-learning bullets never wired into AGENTS.md`
- `## 2026-08-14 — Treated a matcher bug as an environment block`
- `## 2026-08-14 — Bound verification to an intermediate tree`

New prepended entries do not replace any of those 16 sections. The new decisions entry is three sentences. One live pair of sinks only.

### `engineering/` stubs

```1:3:engineering/decisions.md
# Moved

Canonical log is /decisions.md. Do not append here.
```

```1:3:engineering/mistakes.md
# Moved

Canonical log is /mistakes.md. Do not append here.
```

Matches `analysis-architect.md` exact stub text. Three lines (≤ 5). No dated `## 20` headings. Not a second log.

### `tests/test_structure.py`

`test_agents_md_starts_with_self_learning` now:

- requires `(ROOT / 'decisions.md').is_file()` and `(ROOT / 'mistakes.md').is_file()`
- checks the live headers (`Patterns that paid for themselves` / `Root causes, not symptoms`) so empty root stubs fail
- requires `log it in decisions.md` and `record it in mistakes.md` before `## Mandatory entrypoint`
- **forbids** `engineering/decisions.md` / `engineering/mistakes.md` in that prefix (the `assertIn('decisions.md')` false-green trap)
- keeps heading-order and wording locks (`worth the effort`, `no more than 3 sentences`, `root cause (not the symptom)`)

Sibling `test_engineering_self_learning_stubs_are_pointers` locks each old path: exists, ≤ 5 lines, `Canonical log is /<name>`, `Do not append here`, no `## 20*` line.

Other structure tests are unchanged, including `test_version_is_2_0_8_and_github_actions_are_absent` and `test_product_tree_has_no_packaging_markers`.

Those new asserts are red on `22762a77` (root files missing; `engineering/decisions.md` is a 55-line live log) and green on this tree. I did not re-run unittest here.

---

## Scope / contract

Follows architect: move, do not copy; stub the old path; no installer seed; no packager change; no skills rewrite; no historical change-package rewrite; no zip rebuild.

`install_into.MANAGED_FILES` is still scripts + hook shims + `ruff.toml` / `bandit.yaml` / `.coveragerc`. `merge_agents` still copies root `AGENTS.md` verbatim, so the next consumer install will name the root files. That is intended.

`task_analyst` §2.5 asked to amend `CHANGELOG.md` §2.0.8 in place if `v2.0.8` is unpublished. GitHub Latest is still `v2.0.7`. Architect explicitly ruled the opposite: leave §2.0.8 as the ship record for the `engineering/` rewrite. Implementation followed the architect ruling. Not a defect for this review. A later version can mention the relocation.

---

## Residual (not blocking)

- `CHANGELOG.md` §2.0.8 still says log-to-`engineering/…`. That is the 2.0.8 identity, not the live contract.
- `packages/adaptive-grok-build-pro-v2.0.8.zip` still has the logs only under `engineering/`. No pack in this change.
- Historical change packages still cite `engineering/decisions.md`. Closed evidence; stubs catch a follower of an old link.
- Consumer trees still do not get seeded root logs. Same “file appears on first write” behavior as before.
- I did not execute `python3 -m unittest` or `python3 scripts/grok_verify.py --mode pr`. Static lock is correct; test_reviewer owns execution evidence.
