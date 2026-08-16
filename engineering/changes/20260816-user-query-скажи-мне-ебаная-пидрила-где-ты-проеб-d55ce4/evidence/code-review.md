# Code review — restore AGENTS.md self-learning as first section

Change: `20260816-user-query-скажи-мне-ебаная-пидрила-где-ты-проеб-d55ce4`  
Route: `d55ce4cd4015` · reviewer: `code_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-16  
Base: `02376cc097d7640d56dd308b98efe4e026f4c253` (`Release v2.0.7`, `HEAD` == `origin/main`)

**PASS.** I would not block.

The working-tree restore matches the change package. The first `##` heading in `AGENTS.md` is the self-learning rule, user wording is preserved with the real `engineering/` sinks, and `tests/test_structure.py` now fails if that placement or wording is dropped. No VERSION bump, no GitHub Actions, no `pyproject.toml`, no publish.

---

## Verdict against acceptance

| # | Criterion | Result |
| --- | --- | --- |
| 1 | First `##` heading in `AGENTS.md` is `Agent self-learning` | **PASS** (`AGENTS.md:3`) |
| 2 | Bullets name `engineering/decisions.md` and `engineering/mistakes.md` | **PASS** (`AGENTS.md:5-6`) |
| 3 | User wording preserved (`worth the effort` / `no more than 3 sentences` / `root cause (not the symptom)`) | **PASS** |
| 4 | Structure test locks first-heading placement and both paths/verbs | **PASS** (`tests/test_structure.py:22-36`) |
| 5 | Omission recorded in `engineering/mistakes.md` by root cause | **PASS** (new 2026-08-16 entry; prior entries untouched) |
| 6 | No VERSION bump, no GHA, no `pyproject.toml`, no publish | **PASS** |

Would I block? **No.**

---

## What was actually inspected

Did not trust `evidence/implementation.md` alone. Compared current files to GitHub raw of `02376cc` plus the change-package contracts and surrounding installer/copy path. This session has no shell, so there is no live `git diff` / `unittest` / `ruff`. Equivalents below.

```text
# refs
.git/HEAD                    → ref: refs/heads/main
.git/refs/heads/main         → 02376cc097d7640d56dd308b98efe4e026f4c253
.git/refs/remotes/origin/main→ 02376cc097d7640d56dd308b98efe4e026f4c253
.git/COMMIT_EDITMSG          → Release v2.0.7: leftover 2.0.6 fixes as a published identity

# contracts
engineering/changes/…-d55ce4/{brief,requirements,architecture,test-plan,tasks,release,rollback}.md
engineering/changes/…-d55ce4/{route,state}.json
engineering/changes/…-d55ce4/evidence/{analysis-repo_explorer,analysis-architect,analysis-docs_researcher,implementation}.md

# product delta vs 02376cc (GitHub raw)
AGENTS.md                    +6 lines after H1 (new ## Agent self-learning + two bullets)
tests/test_structure.py      +test_agents_md_starts_with_self_learning only
engineering/mistakes.md      +2026-08-16 authorship-omission entry; 2026-08-14 entries byte-identical

# unchanged on purpose
VERSION                      2.0.7
CHANGELOG.md                 still headed by ## 2.0.7
engineering/decisions.md     not rewritten
docs/bitrix-local-AGENTS.md  no self-learning (out of scope)
scripts/install_into.py      merge_agents still copies root AGENTS.md verbatim (lines 68-85)

# absences
.pyproject.toml / requirements.txt / setup.py   do not exist
.github/                                        directory missing
.github/dependabot.yml                          missing
.grok-stack/templates/ci/github-actions.yml     missing
```

---

## Diff reviewed

### `AGENTS.md` (additive insert only)

Base `02376cc` started:

```markdown
# Adaptive Grok Build Pro Engineering Contract

This repository uses an adaptive, task-routed Grok Build workflow. …
## Mandatory entrypoint
```

Working tree now:

```3:10:AGENTS.md
## Agent self-learning

- If you make a decision that turns out to be correct and worth the effort, log it in engineering/decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in engineering/mistakes.md.

This repository uses an adaptive, task-routed Grok Build workflow. The `UserPromptSubmit` hook classifies development tasks and writes `.grok-stack/runtime/active-route.json`. That route is the authority for which skills, agents, quality profiles, human gates, and evidence are required.

## Mandatory entrypoint
```

User quote named `decisions.md` / `mistakes.md`. The only wording change is the `engineering/` prefix, which `architecture.md` required so agents do not create root-level sinks. The rest is the quoted English:

- `worth the effort`
- `pattern + why it worked`
- `no more than 3 sentences`
- `root cause (not the symptom)`
- verbs `log it in` / `record it in`

The contract intro, `## Mandatory entrypoint`, source-of-truth “record it in the change package”, Bitrix/API/data/AI rules, verify/receipts, and prohibited actions are unchanged through `AGENTS.md:113`. The change-package conflict-resolution sentence is still a different loop; it was not deleted or merged into self-learning.

### `tests/test_structure.py:22-36`

New test only. Existing structure tests (including `test_product_tree_has_no_packaging_markers` and `test_version_is_2_0_7_and_github_actions_are_absent`) were not edited.

The lock matches `test-plan.md` and `architecture.md`:

- first `##` heading must be `## Agent self-learning`
- both paths must appear before `## Mandatory entrypoint`
- both verbs (`log it in`, `record it in`)
- user phrases (`worth the effort`, `no more than 3 sentences`, `root cause (not the symptom)`)

A later rewrite that drops the section, moves it after the entrypoint, or strips either sink/path will fail. Implementation.md’s red run (`'## Mandatory entrypoint' != '## Agent self-learning'`) is consistent with the base file.

### `engineering/mistakes.md:5-8`

```5:8:engineering/mistakes.md
## 2026-08-16 — Self-learning bullets never wired into AGENTS.md

**Symptom:** Agents had `engineering/decisions.md` and `engineering/mistakes.md` but no standing `AGENTS.md` order to write them.
**Root cause:** Authorship omission when `AGENTS.md` was first written as the Engineering Contract (`ca63b2d`); the log files were added later (`097f5c9`) without wiring the trigger. Not a later delete.
```

Root cause, not symptom. Agrees with repo_explorer / architect / docs_researcher (never present in committed `AGENTS.md`; not a later delete). Existing 2026-08-14 entries are unchanged.

---

## Out-of-scope / non-blocking

These are documented residuals, not blockers:

- `scripts/install_into.py` still does not seed consumer `engineering/decisions.md` / `engineering/mistakes.md`. Brief out-of-scope. `merge_agents` will ship the new bullets on next install because it copies root `AGENTS.md` verbatim.
- Skills / per-agent `.md` files were not updated. Brief out-of-scope.
- The structure test locks first `##` heading + prefix content, not “byte-immediately after H1 with no intervening paragraph.” That is what `test-plan.md` asked for.
- No CHANGELOG / VERSION / package / GitHub release work. `release.md`: docs-only, no publish.

---

## Contracts check

| Source | Required | Observed |
| --- | --- | --- |
| `brief.md` in-scope | First section after H1; real `engineering/` paths; structure-test lock | Done |
| `brief.md` out-of-scope | No version bump, publish, installer seed, rewrite of old log entries, per-agent copies | Honored |
| `requirements.md` | Four acceptance boxes | All met in the tree |
| `architecture.md` | Section before intro and before `## Mandatory entrypoint`; verbs + paths locked | Met |
| `tasks.md` | Failing test → insert section → record omission → focused unittest | Matches implementation.md |
| `release.md` / `rollback.md` | No publish; revert three files | Consistent |

No OpenAPI / AsyncAPI / schema / ADR / Bitrix-core change. No `.env` or credential read. No push / merge / deploy.

---

## Blocking findings

None.
