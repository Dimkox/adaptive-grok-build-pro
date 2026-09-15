# Upstream format research: do the workflow-artifact adapters' documented native subsets still match latest upstream?

Change: `20260915-update-third-party-workflow-components-superpowe-1b0c02` · Research date: 2026-09-15
Role: analysis evidence (docs_researcher), read-only. No product file was modified by this report.

## 0. Provenance

**Code examined** (the only tree where the adapter exists):

- `/home/pall/grok-projects/adaptive-grok-build-pro-workflow-adapters/.grok-stack/adaptive_grok/workflow_artifacts.py` (1704 lines), on branch `feature/workflow-artifact-adapters` whose HEAD is `dccaeec2a6b79c73663765f5909243e468e4b070`.
  **Important provenance caveat:** the adapter is **not in that commit**. `git ls-files --error-unmatch .grok-stack/adaptive_grok/workflow_artifacts.py` → "did not match any file(s) known to git"; `git cat-file -e HEAD:…workflow_artifacts.py` → "exists on disk, but not in 'HEAD'". Same for `scripts/grok_artifacts.py`, `tests/test_workflow_artifacts*.py` (untracked) and the design doc `docs/superpowers/specs/2026-08-30-workflow-artifact-adapters-design.md`. The `README.md` / `CHANGELOG.md` / `QUICKSTART.md` lines quoted in §5.4 are **uncommitted modifications** (`git status` shows them as ` M`). Everything analysed in §1 is therefore dirty working-tree state with **no commit SHA of its own** — cite it as `workflow-adapters worktree @ working tree (2026-08-30 mtimes), parent HEAD dccaeec`, never as a released or even committed artifact.
- Design claim text: `docs/superpowers/specs/2026-08-30-workflow-artifact-adapters-design.md` line 29 (the "bounded documented native subset" sentence).
- Schemas: `schemas/workflow-source-v1.schema.json`, `schemas/workflow-task-graph-v1.schema.json`.
- Tests: `tests/test_workflow_artifacts.py`, `tests/test_workflow_artifacts_cli.py`, `tests/test_workflow_artifacts_adversarial.py`.
- **Merger status check:** `workflow_artifacts.py` does **not** exist in `/home/pall/grok-projects/adaptive-grok-build-pro` (main) nor in this `adaptive-grok-build-pro-third-party-sync` worktree (`git branch -a --contains dccaeec` → only `feature/workflow-artifact-adapters` and its remote). `grep -rn "workflow_artifacts"` in the sync worktree → **zero hits**. All three workflow schemas are likewise untracked (`?? schemas/workflow-source-v1.schema.json`, `?? schemas/workflow-task-graph-v1.schema.json`, `?? schemas/workflow-convergence-report-v1.schema.json`). So today no shipped release — and no commit on any branch — contains these adapters at all.
- **Branch freshness:** the adapters branch carries `VERSION` `2.0.12` while `origin/main` is `2.0.16`, and `git merge-base --is-ancestor origin/main HEAD` fails, i.e. the branch does **not** contain current `origin/main`. Any "we are current" statement made from that worktree is about a base that is itself behind the product by four patch versions.

**Upstream, fetched and pinned today (2026-09-15) via `gh api`:**

| Project | Tag | Tag object | Peeled commit | Release/commit date |
|---|---|---|---|---|
| `github/spec-kit` | `v1.0.7` | `ccae868325e5baf531a3181d8a9b30138ce00ea0` | `fe1d00e3ccaf495880aaf90fb0e17679e82f065b` | 2026-09-15T13:44:46Z (published 13:45:03Z) |
| `bmad-code-org/BMAD-METHOD` | `v6.12.0` | `b28fef564f2c48ac20d969bcccaf2fc08d503afb` | `05bfbd46d00766ec88eb9b42e76be2c575d64d7b` | 2026-09-04T02:30:56Z (published 02:31:25Z) |
| `obra/superpowers` | `v6.3.0` | `86babb696875227929e85420f287d6309374b93f` | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` | 2026-08-12T16:53:21Z |

All three stated "latest" versions in the task brief are **correct**; each is also the newest tag *and* newest GitHub release on 2026-09-15 (`releases?per_page=…` and `tags?per_page=…` top entries). `obra/superpowers@main` has no commits after `v6.3.0`; `BMAD-METHOD@main` has commits after the tag but no newer release (see §6 NOT-VERIFIED).

**Method.** Every "reality" row below was obtained by fetching the upstream file at the exact tag SHA and then running the adapter's **own compiled regexes** against that byte content (probe script kept out of the tree, in `/tmp`). Counts in §3 are reproducible, not impressions.

---

## 1. What the adapter actually accepts (extracted from code, not docs)

### 1.1 Framework → role → candidate-kind (`ROLE_MAP`, lines 66–89; closed enum)

- `spec-kit` (line 67): `constitution`→governance-candidate, `spec`→requirements-candidate, `plan`→architecture-candidate, `tasks`→task-candidate, `checklist`→convergence-hint.
- `bmad` (line 74): `prd`, `spec`→requirements-candidate; `architecture`→architecture-candidate; `project-context`→governance-candidate; `epics`, `stories`→task-candidate; `sprint-status`→status-projection; `readiness`→convergence-hint.
- `superpowers` (line 84): `spec`→requirements-candidate, `plan`→architecture-candidate, `sdd-evidence`→runtime-evidence.

`source_type` is the only closed enum in `schemas/workflow-source-v1.schema.json` (`["spec-kit","bmad","superpowers"]`); **`role` there is an unbounded string** (`{"type":"string","minLength":1,"maxLength":32}`) — the role enum is enforced only in Python (`load_source_manifest` line 369, `validate_workflow_source` line 160).

### 1.2 Path allowlist (`PATH_PREFIXES`, lines 90–94, plus lines 375–380)

- `spec-kit`: `(".specify/", "specs/")`
- `bmad`: `("_bmad/", "_bmad-output/")`
- `superpowers`: `("docs/superpowers/", ".superpowers/sdd/")`, narrowed by hard asserts: role `sdd-evidence` must start `.superpowers/sdd/`; non-`sdd-evidence` superpowers must start `docs/superpowers/`.
- **No filename, directory-depth, or extension assertion anywhere** for any framework. Discovery is prefix-only.

### 1.3 `source_version` is inert

Grep of the whole module: lines 151, 158, 366, 396 — that is *only* `_bounded_text(..., maximum=32)` and echo into the identity dict. **No branch in the parser, status-hint, graph or convergence path reads `source_version`.** There is no version→behaviour mapping, and no allowed-version set.

### 1.4 Content literals accepted per framework

**Spec Kit** (`_native_framework_tasks`, lines 593–615) — the only task-producing spec-kit path is role `tasks`:

- Phase reset: `re.match(r"^#{2,6}\s+Phase\b", line, re.I)` (line 599).
- Task row: `SPEC_TASK` (line 113) = `^\s*-\s*\[([ xX])\]\s+(T[0-9]{1,6})\s+(?:(\[P\])\s+)?(?:\[US[0-9]+\]\s+)?(.+?)\s*$` → checkbox, `T`+1–6 digits, optional `[P]` **immediately after the ID**, optional `[US#]` **after `[P]`**, then title.
- Status from checkbox: `NATIVE_STATUS` (line 117) = `^\s*-\s*\[([ xX])\]\s+(T[0-9]{1,6})\b`.
- Dependencies are **invented positionally** (all of previous phase + previous task in phase when not `[P]`); upstream prose dependencies are not read.
- `covers` only from `CRITERION_TOKEN` (line 115) = `\b(?:AC|INV|FORBID)-[0-9]{3,6}\b` found **in the task title**.

**BMAD** (lines 617–641, role `stories` or `epics`) and status hints (lines 644–679):

- Story/epic heading: `re.match(r"^#\s+(Story|Epic)\s+([A-Za-z0-9.-]+)", line, re.I)` (line 624) — **exactly one `#`**, i.e. h1 only; ID charset `[A-Za-z0-9.-]+`.
- Task row: `BMAD_TASK` (line 114) = `^\s*-\s*\[([ xX])\]\s+(.+?)\s*$` (any checkbox, any indent).
- Key shape: `{story|epic}-<normalized-id>-{NNN}`, ordinal and dependency chain reset per heading.
- sprint-status hints (lines 663–671), role `sprint-status` only, `re.fullmatch` on the stripped line: `([a-z0-9][a-z0-9-]{0,127}):\s*(done|complete|completed|ready-for-review|review)` → prefix `story-<n1>-<n2>-` (or `story-<key>-`) and match by key prefix.
- Story status section (lines 674–677): `re.fullmatch(r"#{2,6}\s+Status", line, re.I)` — a **heading** named Status, whose next non-empty non-heading line lower-cased and space→dash-normalised is in `{done, complete, completed, ready-for-review, review}`.
- **No YAML front-matter parsing exists** for BMAD (or any framework).

**Superpowers** — `_native_framework_tasks` falls through to `return []` (line 642): **zero** content literals. No plan-task parsing, no `> **For agentic workers:**` header check, no `### Task N:` / `- [ ] **Step M:**` handling, no `.superpowers/sdd/` filename grammar. Only §1.2 prefixes. The design doc states this deliberately ("advisory projections", "runtime evidence metadata only"), so superpowers cannot drift in code — only in *documentation* claims.

**Content gate shared by all frameworks** — `FORBIDDEN_SOURCE` (line 95) = `(^|\s)(?:!!|<<:|[&*][A-Za-z0-9_-]+)`, applied to the whole document body at line 388. It is a YAML-anchor/alias guard, but it runs against **markdown**, where `*` opens an italic/emphasis run.

### 1.5 Which upstream version the test fixtures actually simulate — **none**

`source_version` is the only version handle in a fixture, and it is a placeholder, not a release:

- `tests/test_workflow_artifacts.py` lines 46, 89, 105, 124, 137, 153, 164, 166, 167, 189, 529 → **`"1"`**; line 165 → **`"6"`** (a BMAD *role*-rejection case, not a 6.x conformance case).
- `tests/test_workflow_artifacts_cli.py:71` → `"1"`.
- `tests/test_workflow_artifacts_adversarial.py` lines 86, 157, 161, 166, 168, 169, 180, 249, 283, 306, 354, 418, 456 → `"1"` (161 is a 33-char overflow bound test).

Fixture bodies are likewise partly synthetic rather than upstream-shaped:

| Fixture | Line | Upstream conformance |
|---|---|---|
| `.specify/specs/tasks.md` with `## Phase 1: Setup`, `- [ ] T001 [P] [US1] …` | 262–266 | Row syntax ✅ matches v1.0.7; **path ❌ never an upstream layout** (upstream artifacts root is `specs/`; `.specify/` is infra) |
| `# Story 1.2: Safe import` + `## Status` / `Draft` | 293–295 | h1 heading ✅ legacy BMAD; **`## Status` heading ❌** upstream emits bare `Status: ready-for-dev`; `Draft` ∉ recognised vocabulary |
| `development_status:\n  1-2-safe-import: done` | 305–308 | ✅ matches upstream `sprint-status.yaml` key/value shape |
| `# Epic 1: Loader` (role `epics`) | 336–339 | ❌ upstream epics.md is `## Epic 1:` (h2) with `### Story 1.1:` (h3), and has **no `- [ ]` rows at all** |
| `docs/superpowers/specs/design.md`, `docs/superpowers/plans/plan.md`, content `# Plan\n1. Write tests\n` | adv. 446–447 | Prefix ✅; body is not the upstream plan shape (irrelevant — superpowers body is unparsed) |
| `.superpowers/sdd/x/progress.md` | 216 | ✅ matches v6.2.0+ plan-scoped layout (`<plan-basename>/progress.md`) |
| `_bmad-output/readiness.md` = `# Readiness\nStatus: ready` | adv. 449 | ❌ upstream readiness is `implementation-readiness.md` with `PASS`/`CONCERNS`/`FAIL`; bare `Status:` line is unparsed and `ready` ∉ vocabulary |
| `- [x] T001 Implement … in src/core.py` | adv. 407 | ✅ |

**Conclusion for Step 1:** the suite proves the *synthetic* grammar, and three of its fixtures encode paths/headings that upstream has never emitted (`.specify/specs/`, h1 `# Epic`, `## Status`). Because `source_version` is inert, no test can fail if upstream changes shape.

---

## 2. Latest upstream reality (quoted)

### 2.1 github/spec-kit v1.0.7 (`fe1d00e3`)

`templates/commands/tasks.md`, "Checklist Format (REQUIRED)":

```
- [ ] [TaskID] [P?] [Story?] Description with file path
```

`templates/tasks-template.md` — phase headings and representative rows:

```
## Phase 1: Setup (Shared Infrastructure)
- [ ] T001 Create project structure per implementation plan
## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP
### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️
- [ ] T010 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T014 [US1] Implement [Service] in src/services/[service].py (depends on T012, T013)
## Phase N: Polish & Cross-Cutting Concerns
- [ ] TXXX [P] Documentation updates in docs/
```

- Artifact root is **`specs/` at repo root**, not `.specify/specs/`: `scripts/python/create_new_feature.py` → `specs_dir = repo_root / "specs"`; `.specify/` holds `templates/`, `scripts/`, `memory/constitution.md`, `feature.json`. Verified against the tag tree: `gh api repos/github/spec-kit/git/trees/v1.0.7?recursive=1 | grep '^\.specify/'` yields only `.specify/memory` + `.specify/memory/constitution.md`. Per-feature dir is `NNN-feature-slug` (3-digit default). Root `specs/` has been the layout since at least `v0.0.1` — **`.specify/specs/` has never existed upstream.**
- Constitution: unchanged `.specify/memory/constitution.md`; `templates/commands/constitution.md` @ v1.0.7 — "Write the completed constitution back to `.specify/memory/constitution.md` (overwrite)." New v1.0.6 wording (commit `00a47de4`, 2026-09-09): the Sync Impact Report is "temporary scratch material for human review … expected to be removed before the amended constitution file is committed" → a leading `<!-- -->` block may or may not be present.
- Checklist: feature-scoped `FEATURE_DIR/checklists/[domain].md` (e.g. `specs/003-user-auth/checklists/requirements.md`), item syntax `- [ ] CHK001 …`.
- **Format changes since 2026-08-25 are only three**, none of them breaking the task-row grammar:
  1. `af8f5a49` (2026-09-03, v1.0.5) — `fix(scripts): name setup-plan's feature directory key FEATURE_DIR (#4397)`: `SPECS_DIR:` → `FEATURE_DIR:` in `setup_plan.py` output and `templates/commands/plan.md`. Script-output rename, not a document shape.
  2. `072ab333` (2026-09-08, v1.0.5) — `fix(tasks): require field constraints from data-model.md in generated tasks (#4430)`: adds a generation rule "quote the constraint verbatim in the task description". Changes task **text**, not syntax.
  3. `00a47de4`/`#4432` (2026-09-09, v1.0.6) — constitution Sync Impact Report is transient.
- Across the whole v0→v1 boundary (`v0.16.5` → `v1.0.7`), `git diff` of `spec-template.md`, `plan-template.md`, `tasks-template.md`, `checklist-template.md`, `constitution-template.md` is **empty**. No `v1.0.0-rc*` tags exist (tag list goes `v0.16.5` → `v1.0.0`). **The premise that spec-kit v1.0.x changed the artifact formats is false.**
- `templates/tasks-template.md` does carry YAML front matter (`---\n\ndescription: "Task list template for feature implementation"\n---`) which `scripts/python/common.py:resolve_template_content()` never strips — so a generated `tasks.md` may legitimately begin with `---`. Whether real agents keep it: NOT-VERIFIED.
- `spec-template.md` ids are `FR-NNN` / `SC-NNN` and unresolved items are `[NEEDS CLARIFICATION: …]` — **no `AC-`/`INV-`/`FORBID-` tokens exist anywhere in spec-kit documents.**

### 2.2 bmad-code-org/BMAD-METHOD v6.12.0 (`05bfbd46`)

Legacy story file, `src/bmm-skills/v6-shims/bmad-create-story/template.md` (byte-identical to v6.10.0), lines 1–3 and 19–22:

```
# Story {{epic_num}}.{{story_num}}: {{story_title}}

Status: ready-for-dev
...
- [ ] Task 1 (AC: #)
  - [ ] Subtask 1.1
```

Canonical **current** implementation record, `src/bmm-skills/ship/bmad-build/spec-template.md` (was `bmad-quick-dev` until v6.11.0):

```yaml
---
title: '{title}'
type: 'feature' # feature | bugfix | refactor | chore
created: '{date}'
status: 'draft' # draft | ready-for-dev | in-progress | in-review | done
route: '' # oneshot | dispatch — set by step-02's route gate after design
review_loop_iteration: 0
context: []
---
```

with `## Intent`, `## Boundaries & Constraints`, `## I/O & Edge-Case Matrix`, `## Open Questions`, `## Code Map`, `## Tasks & Acceptance`, `## Implementation Notes`, `## Spec Change Log`, `## Review Triage Log`, `## Design Notes`, `## Verification`, and tasks as:

```
**Execution:**
- [ ] `FILE` -- ACTION -- RATIONALE
**Acceptance Criteria:**
- Given PRECONDITION, when ACTION, then EXPECTED_RESULT
```

Epics, `src/bmm-skills/plan/bmad-create-epics-and-stories/templates/epics-template.md` (byte-identical to v6.10.0), lines 40 / 46:

```
## Epic {{N}}: {{epic_title_N}}
### Story {{N}}.{{M}}: {{story_title_N_M}}
```

- Probe result on that file: **0 lines match `BMAD_TASK`** — upstream `epics.md` contains **no checkboxes**, only `As a / I want / So that` prose and `**Given** / **When** / **Then**` criteria.
- Upstream's own tolerant grammar, `src/bmm-skills/plan/bmad-sprint-planning/scripts/sprint_plan.py:44-47`, shows what real corpora look like:
  ```python
  EPIC_RE  = re.compile(r"^#{1,3}\s*Epic\s+(\d+)\s*:?\s*(.*?)\s*#*\s*$", re.IGNORECASE)
  STORY_RE = re.compile(r"^#{2,4}\s*Story\s+(\d+)\.(\d+[a-z]?)\s*:?\s*(.*?)\s*#*\s*$", re.IGNORECASE)
  ```
  (epic h1–h3, story h2–h4, story number may carry a letter suffix `1.2a`, fenced code skipped).
- `sprint-status.yaml` — **unchanged format**. `CHANGELOG.md` v6.11.0: "`sprint-status.yaml` format is unchanged, so Build's sprint sync is unaffected." Path `{implementation_artifacts}/sprint-status.yaml` → default `_bmad-output/implementation-artifacts/sprint-status.yaml`. Vocab (`sprint_plan.py:63-68`): `STORY_RANK = {"backlog":0,"ready-for-dev":1,"in-progress":2,"review":3,"done":4}`, `EPIC_RANK = {"backlog","in-progress","done"}`, `RETRO_RANK = {"optional","done"}`, `ACTION_STATUSES = ("open","in-progress","done")`, `LEGACY_STATUS = {"drafted":"ready-for-dev","contexted":"in-progress"}`; keys are kebab (`1-2-account-management`), never `1.2`.
- Status vocabulary now has **two spellings**: story *file* / sprint-status use `review`; Build-spec front matter uses `in-review`.
- **`project-context.md` generation is gone.** `src/bmm-skills/plan/bmad-project-context/SKILL.md:8`: "a conversation that produces a repository's agent instructions: a small verified block inside `AGENTS.md`." CHANGELOG v6.11.0: "The deliverable changes shape: no generated overview, source-tree, or deep-dive pages and no `project-context.md`, just one verified block in `AGENTS.md`. An existing `project-context.md` still loads as a source."
- Readiness renamed: v6.10 `{planning_artifacts}/implementation-readiness-report-{{date}}.md` → v6.12 `src/bmm-skills/plan/bmad-sprint-planning/references/readiness-gate.md:20` `{planning_artifacts}/implementation-readiness.md`, verdicts `PASS`/`CONCERNS`/`FAIL`. `bmad-check-implementation-readiness` and `bmad-sprint-status` (as skills) were removed/deprecated (v6.11.0).
- New tracking file: spec-backed epics use `{spec-folder}/stories.yaml` and "No sprint-status file is involved" (`docs/plan/break-work-into-stories-and-track-it.md`); `src/bmm-skills/plan/bmad-spec/assets/stories-schema.md` rule 3: **"No `status` field, ever."**
- v6.12.0 breaking notes touching docs: "`persistent_facts` ships empty. Re-add `project-context.md` to your override…", "`{diff_output}` is now `{diff_file}`", "Deprecated shims are opt-in on fresh installs. Pass `--shims` to keep them."
- Output dirs did **not** move: `_bmad/` (installed skills) and `_bmad-output/` (generated artifacts) remain, so `PATH_PREFIXES["bmad"]` is still correct. What moved is the *source repo* internal tree (`src/bmm-skills/{1-analysis,…}` → `{agents,plan,ship,v6-shims}`), irrelevant to a project-artifact reader.

### 2.3 obra/superpowers v6.3.0 (`b36e0829`)

`skills/writing-plans/SKILL.md:18` and `:56-70`:

```
**Save plans to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
```
```
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** … **Architecture:** … **Tech Stack:** …
**Spec:** [path to the spec/design doc this plan implements — …]
```

- The `For agentic workers:` header is **byte-identical v5.0.7 → v6.3.0**. Plan task syntax `### Task N:` + `- [ ] **Step 1: Write the failing test**` is unchanged v5.1.0 → v6.3.0; v6.0.0 added `## Global Constraints` and per-task `**Interfaces:**`; **v6.3.0 added only the `**Spec:**` header field** (confirmed by direct diff of `writing-plans/SKILL.md` v6.0.0→v6.3.0: added `**Spec:**`, deleted a redundant `## Remember` section).
- **No per-task `Status:` field exists in a plan.** Status is the `- [ ]`/`- [x]` checkbox only, and upstream never rewrites plan checkboxes to `[x]`. Upstream's own task extractor accepts *any* heading level: `skills/subagent-driven-development/scripts/task-brief` uses `/^#+[ \t]+Task[ \t]+[0-9]+/`.
- Specs: `skills/brainstorming/SKILL.md:100` — "save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`"; **no mandated heading structure**. 2 of 19 committed specs lack `-design` (so a `*-design.md` glob drops ~11% — the adapter globs nothing, so unaffected).
- SDD evidence: `skills/subagent-driven-development/scripts/sdd-workspace` → `base="$root/.superpowers/sdd"; dir="$base/$slug"` with `slug=$(basename "$plan" .md)`, i.e. **`.superpowers/sdd/<plan-basename>/`** since **v6.2.0** (2026-07-23); before that it was `.git/sdd/` up to v6.0.2, and flat `.superpowers/sdd/<file>` at v6.0.3–v6.1.1. File names: `task-<N>-brief.md`, `task-<N>-report.md`, `progress.md`, `review-<base7>..<head7>.diff`.
- Critical operational fact: the workspace is **self-ignoring and deleted on success** — `printf '*\n' > "$base/.gitignore"` and SKILL.md §Finish: "delete this plan's workspace (`rm -rf <workspace>`) — the git history is the record now." Nothing under `.superpowers/sdd/` exists in any upstream git tree.
- v6.3.0 also introduces batched dispatches: "Compose ONE dispatch brief listing every file and its change" — one `task-N-brief.md` can cover several plan tasks, so a task↔report 1:1 assumption is unsafe.
- v6.3.0 "Three Paths" in `brainstorming/SKILL.md`: **Spike** and **Bounded** produce *no spec file and no plan file* — only **Architectural** produces the two-document set.

---

## 3. Empirical probe: adapter regexes vs the real upstream files at their tags

Running the §1 literals against byte content fetched at the tags (rows = matched line count / candidate line count):

| Upstream file @ tag | `SPEC_TASK` | `BMAD_TASK` | `^#{2,6} Phase` | h1 `Story\|Epic` (line 624) | `#{2,6} Status` (line 674) | sprint key→done (line 663) | `FORBIDDEN_SOURCE` (line 95) |
|---|---|---|---|---|---|---|---|
| `github/spec-kit@v1.0.7` `templates/tasks-template.md` | **28 / 34** | 34 / 34 | 7 | 0 | 0 | 0 | none |
| `github/spec-kit@v1.0.7` `templates/spec-template.md` | 0 | 0 | 0 | 0 | 0 | 0 | **1 hit — line 96** |
| `github/spec-kit@v1.0.7` `templates/plan-template.md` | 0 | 0 | 0 | 0 | 0 | 0 | **1 hit — line 41** |
| `BMAD-METHOD@v6.12.0` `v6-shims/bmad-create-story/template.md` | 0 | 4 / 4 | 0 | **0** (mustache `{{epic_num}}` ∉ `[A-Za-z0-9.-]`) | 0 | 0 | none |
| `BMAD-METHOD@v6.12.0` `…/templates/epics-template.md` | 0 | **0 / 0** | 0 | **0** (h2/h3) | 0 | 0 | none |
| `BMAD-METHOD@v6.12.0` `bmad-build/spec-template.md` | 0 | 1 | 0 | 0 | 0 | 0 | none |
| `BMAD-METHOD@v6.12.0` `bmad-sprint-planning/sprint-status-template.yaml` | — | — | — | — | 0 | **1** (`1-1-user-authentication: done`) | none |
| `obra/superpowers@v6.3.0` `skills/writing-plans/SKILL.md` | — | 5 | — | 0 | 0 | 0 | none |

The 6 unmatched spec-kit rows are all template placeholders (`- [ ] TXXX …`), correctly ignored. Instantiated BMAD headings confirm the heading-level gap:

```
'# Story 1.2: Safe import'   -> ('Story', '1.2')     # legacy single-story file: OK
'## Epic 1: Loader'          -> None                 # upstream epics.md: NOT matched
'### Story 1.1: Auth'        -> None                 # upstream epics.md: NOT matched
'## Story 2.3a: Hotfix'      -> None                 # h2 + letter suffix: NOT matched
```

The `FORBIDDEN_SOURCE` hits are markdown emphasis, not YAML authority:

```
sk_spec.md:96   *Example of marking unclear requirements:*
sk_plan.md:41   *GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
```

`(^|\s)` matches start-of-line, `*` then `[A-Za-z0-9_-]+` matches `Example`/`GATE`. Both are verbatim lines from spec-kit's own v1.0.7 templates that agents copy into generated `spec.md`/`plan.md`, and `load_source_manifest` (line 388) **raises `WorkflowArtifactError` code `content` on the whole document**.

---

## 4. Compatibility table

| # | Adapter assumption (code line) | Upstream latest reality (file @ tag) | Verdict |
|---|---|---|---|
| 1 | spec-kit task row `- [ ] TNNN [P] [US#] title` (113) | `templates/commands/tasks.md` @ v1.0.7: `- [ ] [TaskID] [P?] [Story?] Description with file path`; 28/34 real rows match, non-matches are `TXXX` placeholders | **compatible** |
| 2 | spec-kit phase headings `^#{2,6}\s+Phase\b` (599) | `## Phase 1…5` + `## Phase N: Polish & Cross-Cutting Concerns` @ v1.0.7 | **compatible** |
| 3 | spec-kit artifact paths `.specify/` **or** `specs/` (91) | Root `specs/NNN-slug/{spec,plan,tasks}.md` + `checklists/`; `.specify/` = infra incl. `memory/constitution.md` | **compatible** (allowlist covers both); fixtures are wrong (§1.5) |
| 4 | spec-kit roles `constitution/spec/plan/tasks/checklist` (67–73) | Exactly the five `/speckit.*` artifact kinds at v1.0.7 | **compatible** |
| 5 | **No** spec-kit v0.x→v1.0 format break assumed by anyone | `diff v0.16.5→v1.0.7` of all five templates = empty; only `SPECS_DIR→FEATURE_DIR` script-output rename (#4397) | **compatible — premise false** |
| 6 | `FORBIDDEN_SOURCE` `(^|\s)[&*]\w+` on markdown bodies (95) | spec-kit's own templates contain `*Example …:*` (spec:96) and `*GATE: …*` (plan:41) | **DRIFTED / broken — rejects genuine upstream artifacts** |
| 7 | `CRITERION_TOKEN` `AC\|INV\|FORBID-\d{3,6}` from titles (115) | spec-kit emits `FR-001`/`SC-001`; BMAD emits `1. [Add acceptance criteria…]` and `(AC: #)`; neither uses `AC-NNN` | **drifted-by-absence — `covers` is always empty for native imports** |
| 8 | `PLACEHOLDER` = `UNKNOWN\|TBD\|TODO\|...` (112) | spec-kit's unresolved marker is `[NEEDS CLARIFICATION: …]` (spec-template v1.0.7, 2 occurrences) | **drifted-by-absence — upstream's own open-question marker passes silently** |
| 9 | spec-kit prose `(depends on T012, T013)` ignored; deps inferred positionally (611–613) | Upstream expresses deps only in prose + `## Dependencies & Execution Order` | **approximation (not drift) — but undocumented in README/QUICKSTART** |
| 10 | BMAD story h1 `# Story 1.2: …` (624) | Legacy shim template identical: `# Story {{epic_num}}.{{story_num}}: …` | **compatible** (legacy path only) |
| 11 | BMAD epic/story headings h1-only (624) | `epics-template.md`: `## Epic {{N}}:` and `### Story {{N}}.{{M}}:`; upstream grammar `EPIC_RE ^#{1,3}`, `STORY_RE ^#{2,4}` incl. `1.2a` | **DRIFTED — role `epics` never yields tasks from a real epics.md** |
| 12 | BMAD `- [ ]` task rows in `epics` docs (114 + 617) | v6.12.0 `epics-template.md` has **zero** checkboxes | **DRIFTED — dead code path for role `epics`** |
| 13 | BMAD story status via `## Status` **heading** + next line ∈ {done, complete, completed, ready-for-review, review} (674–676) | v6.12.0 story template: bare `Status: ready-for-dev` at line 3 (`Status:` key/value, no heading); dev-story also parses a `Status` section per `v6-shims/bmad-dev-story/SKILL.md:199` | **DRIFTED — status hint never fires for real BMAD stories** |
| 14 | No YAML front-matter reading | v6.12.0 canonical Build spec keeps `status:` in front matter: `draft \| ready-for-dev \| in-progress \| in-review \| done` | **new-optional (unhandled)** — role `spec`/`stories` status now lives where the parser cannot look |
| 15 | Status vocab `review` / `ready-for-review` (665, 676) | sprint-status uses `review`; Build-spec front matter uses **`in-review`** | **drifted — one token short** |
| 16 | sprint-status `key: <done…>` key/value (663–671) | `sprint-status-template.yaml` @ v6.12.0 unchanged; kebab story keys `1-1-user-authentication: done`; CHANGELOG v6.11.0 "format is unchanged" | **compatible** (probe matched exactly) |
| 17 | sprint-status values `backlog`/`in-progress`/`ready-for-dev` treated as non-terminal; legacy `drafted`/`contexted` unknown | `STORY_RANK` + `LEGACY_STATUS = {"drafted":"ready-for-dev","contexted":"in-progress"}` | **new-optional — legacy aliases normalize to real states upstream but are unrecognised here** |
| 18 | BMAD role `project-context` → governance-candidate (74–83) | v6.11.0+: no `project-context.md` is generated; content is a managed block inside root `AGENTS.md` (outside `PATH_PREFIXES`) | **DRIFTED — role has no upstream producer in the allowlist** (legacy files still load) |
| 19 | BMAD role `readiness`, path-agnostic (92) | v6.12.0 `{planning_artifacts}/implementation-readiness.md`, verdicts `PASS`/`CONCERNS`/`FAIL` (was `implementation-readiness-report-<date>.md`) | **compatible** (prefix-only) — doc text should name the new file |
| 20 | BMAD output roots `_bmad/`, `_bmad-output/` (92) | Defaults `output_folder=_bmad-output`, `planning_artifacts`, `implementation_artifacts`, spec folder `{output_folder}/specs` | **compatible** |
| 21 | Superpowers `spec`/`plan` under `docs/superpowers/` (93, 379) | `docs/superpowers/specs/YYYY-MM-DD-…-design.md`, `docs/superpowers/plans/YYYY-MM-DD-….md` @ v6.3.0 | **compatible** |
| 22 | Superpowers `sdd-evidence` under `.superpowers/sdd/` (93, 377) | v6.2.0+ `.superpowers/sdd/<plan-basename>/{task-N-brief,task-N-report,progress,review-base..head.diff}` | **compatible** — but see #23 |
| 23 | (implicit) SDD evidence is ingestible content | v6.3.0: `sdd-workspace` writes `.superpowers/sdd/.gitignore` containing `*`, and the workspace is `rm -rf`'d at finish — never in any git tree | **constraint, not drift — must be documented as "transient, only while a run is live"** |
| 24 | Superpowers `**Spec:**` plan header field (v6.3.0 addition) | `skills/writing-plans/SKILL.md:69` @ v6.3.0 | **new-optional — unparsed, therefore no code change needed** |
| 25 | `source_version` accepted as ≤32-char free text, never compared (158, 366) | Upstream ships real semvers: v6.3.0 / v6.12.0 / v1.0.7 | **DRIFTED-BY-DESIGN — the product has no version claim the code enforces** |
| 26 | `schemas/workflow-source-v1.schema.json`: `role` is a free string; no `source_version` enum | Roles are framework-vocabulary (BMAD adds `stories.yaml`, spec concepts `SPEC.md`/`stories/<id>-*.md`) | **new-optional — schema cannot express "which upstream dialect"** |

**Net:** Spec Kit's documented subset is genuinely still current at v1.0.7 (with the #6 content-gate defect). BMAD's story/task/status subset has materially drifted at v6.11–v6.12. Superpowers is path-compatible at v6.3.0 and unparsable by design.

---

## 5. Concrete UPDATE LIST for the product

Ordered so the honesty question is settled before the grammar work. Nothing here is a merge authority; each bullet names the exact artifact to touch.

### 5.0 Blocks the "components updated to latest versions" claim as stated

1. **There is no version pin to update.** `grep -rn "superpowers\|bmad\|spec-kit\|specify"` across `scripts/`, `.grok-stack/`, `README.md`, `QUICKSTART.md`, `CHANGELOG.md`, `PROJECT_STATE.json` in the third-party-sync tree at `VERSION` `2.0.16` finds only the route/task strings and `architecture.py:707 PurePosixPath(".superpowers")` (an architecture-analysis ignore entry). No `toolchain.json` entry, no vendored copy, no lockfile. → The truthful claim today is "the adapters accept upstream artifacts as of spec-kit v1.0.7 / BMAD v6.12.0 / superpowers v6.3.0", **not** "components updated to v…".
2. **The adapter code is not in the shipped product at all — it is not even committed** (§0 merger status: untracked working-tree files on a branch that is itself at `VERSION` 2.0.12 vs `origin/main` 2.0.16). Any CHANGELOG/README/`PROJECT_STATE.json` release text that reads as third-party component currency for these three must not be written from this change until `feature/workflow-artifact-adapters` is committed, rebased onto current main, delivered by PR and merged. If the intent is "our own `.superpowers/` + skill docs are current", that is a different, already-superpowers-native claim — keep it separate.
3. `docs/superpowers/specs/2026-08-30-workflow-artifact-adapters-design.md:29` is the *only* place the "documented native subset" is defined. It must be re-versioned (§5.4) because three of its five asserted shapes are now wrong.

### 5.1 Must change in code (`.grok-stack/adaptive_grok/workflow_artifacts.py`)

4. **Line 95 `FORBIDDEN_SOURCE`** — stop treating markdown emphasis as YAML authority. Minimum: require the `&`/`*` anchor forms to be YAML-context (e.g. apply only inside `role == "sprint-status"`/`.yaml` sources, or anchor to `^\s*&`/`^\s*\*` only when the token is a whole-line key). Add regression fixtures that load `*Example of marking unclear requirements:*` and `*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*` verbatim (both quoted from `github/spec-kit@v1.0.7` `templates/spec-template.md:96` and `templates/plan-template.md:41`) and assert they load today. Without this fix, roles `spec` and `plan` cannot ingest real Spec Kit output at any version, so no version claim is honest.
5. **Line 624 heading regex** — widen to upstream's own grammar and letter suffixes: `^#{1,4}\s+(Story|Epic)\s+([0-9]+(?:\.[0-9]+[a-z]?)|[A-Za-z0-9][A-Za-z0-9.-]*)`, mirroring `sprint_plan.py:44-47` @ `BMAD-METHOD@v6.12.0`. Otherwise role `epics` yields nothing (see also #6).
6. **Role `epics` semantics** — decide and document: upstream `epics-template.md` @ v6.12.0 contains **no `- [ ]` rows**, so `_native_framework_tasks` (617–641) returns `[]` for a faithful epics.md. Either (a) reclassify role `epics` to a *task-candidate that may legitimately produce zero tasks* plus a `structure-only` convergence finding, or (b) parse `### Story N.M:` blocks into one task per story with AC prose. Option (b) matches upstream intent better; today's code silently produces an empty graph, which reads as "no work imported".
7. **Lines 674–677 status detection** — additionally accept the upstream bare line form `^Status:\s*(.+)$` (BMAD story template line 3 `Status: ready-for-dev`), and keep the heading form for annotated files. Extend the accepted set (676) from `{done, complete, completed, ready-for-review, review}` with **`in-review`** (v6.12.0 `bmad-build/spec-template.md` front matter) and treat `draft` / `ready-for-dev` / `backlog` / `in-progress` / `optional` / `open` / `blocked` as explicitly non-terminal, so the vocabulary is total rather than accidental.
8. **New: a minimal front-matter reader** for BMAD `status:` / `route:` / `deferred:` (v6.12.0 canonical Build spec). Without it, the *current* BMAD implementation record reports no status at all. Scope it to a leading `---` block and only these keys; do not add a YAML engine (keep the existing closed-shape discipline).
9. **Line 112 `PLACEHOLDER`** — add `NEEDS CLARIFICATION` so an unresolved Spec Kit `spec.md` (`spec-template.md` @ v1.0.7 lines 98–99) is caught instead of silently converged.
10. **Line 115 `CRITERION_TOKEN`** — either (a) add upstream id families `FR`/`SC` for spec-kit and BMAD's numbered `## Acceptance Criteria` so `covers` is not structurally always-empty on native imports, or (b) keep it native-only **and say so in the design doc + README** (currently the design sentence implies coverage extraction). Option (b) is the smaller honest change; option (a) changes `covers` semantics and needs a `change-spec.yaml`-id mapping rule — pick one explicitly, don't leave it implicit.
11. **Lines 611–613 positional dependency inference** — document in the design doc that upstream Spec Kit dependencies are prose (`(depends on T012, T013)`, `## Dependencies & Execution Order`) and are *not* parsed, so the imported DAG is a heuristic. Optionally parse the `(depends on T…, T…)` suffix as a strict union on top of the positional chain.
12. **`source_version` (158, 366)** — make it semantically checked or make the doc stop implying it is checked. Minimum: an allowlist per `source_type` of observed upstream series (`spec-kit`: `0.16.*`/`1.0.*`; `bmad`: `6.10`–`6.12`; `superpowers`: `6.2`/`6.3`) plus an explicit `unknown-version` convergence **finding** (not a hard reject) when it doesn't match. This is the single change that turns "we support latest" into a verifiable statement.
13. **Line 93 + 377 superpowers evidence** — keep the prefix, but record the v6.2.0/v6.3.0 lifecycle (plan-scoped dir, git-ignored, `rm -rf` at finish, batched briefs breaking task↔report 1:1) in the module comment and in §5.4 docs, so a reader cannot infer that missing `.superpowers/sdd/**` means missing evidence.

### 5.2 Schemas

14. `schemas/workflow-source-v1.schema.json` — `role` must become the **closed enum per `source_type`** it already is in Python (spec-kit 5 roles; bmad 8; superpowers 3), and `source_version` should gain `pattern` for a semver-ish token (currently just `minLength:1`/`maxLength:32`). No new role is required for BMAD `stories.yaml`/`SPEC.md` if §5.1#8 is done inside existing `spec`/`stories` roles; if a dedicated `stories-index` role is added, add it here **and** to `ROLE_MAP` in the same commit (the code enum is `validate_workflow_source` line 160).
15. `schemas/workflow-task-graph-v1.schema.json` — no change needed for the above; only touch `source_status`/`enrichment_required` if a new terminal state (e.g. `blocked`) is introduced. Prefer mapping upstream `blocked` → existing `pending` + a finding, to avoid a schema-version bump.

### 5.3 Tests (`tests/test_workflow_artifacts*.py`)

16. Replace placeholder `source_version` `"1"`/`"6"` with real `"1.0.7"`, `"6.12.0"`, `"6.3.0"` once #12 exists — today **no fixture simulates any upstream version**, which is exactly why the drift in §4 went unnoticed. Exact current inventory across the three test files (27 `source_version` occurrences): **23 × `"1"`, 1 × `"6"`, plus 1 × `"x"*33` and 1 × `""`** — the last two are deliberate length-bound tests (`test_manifest_rejects_source_version_bounds_backslashes_and_casefold_collisions`) and must keep their invalid values.
17. Fix the three non-upstream fixture shapes: `.specify/specs/tasks.md` → `specs/001-x/tasks.md` (also add one `.specify/memory/constitution.md` case so both allowlist branches are covered); `# Epic 1: Loader` → real `## Epic 1: Loader` + `### Story 1.1: …` + `## … / - [ ]` legacy story mix; `## Status\nDraft` → upstream `Status: ready-for-dev` (and one `Status: review`, one front-matter `status: 'in-review'`).
18. Add characterization tests that feed **verbatim upstream template bodies** (quoted in §2) — Spec Kit `tasks-template.md` phase block, BMAD `epics-template.md`, BMAD v6-shim story template, `sprint-status-template.yaml`, superpowers `writing-plans` header block — and assert exact task counts equal the probe table in §3 (28 tasks from Spec Kit's template, 4 from the BMAD story template, 0 from epics, 1 `key:done` from sprint-status).
19. Add a regression test for §5.1#4: a Spec Kit `spec.md` containing `*Example of marking unclear requirements:*` must **load**, and one containing `[NEEDS CLARIFICATION: auth method not specified]` must produce a placeholder finding (via §5.1#9).
20. Adversarial tests must keep passing for the `FORBIDDEN_SOURCE` narrowing: `<<:`, `!!`, and real YAML anchors must still be rejected while markdown emphasis is allowed.

### 5.4 Docs/strings that currently overstate

21. `docs/superpowers/specs/2026-08-30-workflow-artifact-adapters-design.md:29` — the sentence "Adapters parse a bounded documented native subset … Spec Kit phase headings plus `- [ ] TNNN [P] [USN] ...` task rows, and BMAD story/epic headings, status sections, task checkboxes, and sprint-status key/value hints" must be re-cut: Spec Kit part ✅; "BMAD epic headings" ❌ (#5.1#5–6), "status sections" ❌ (#7). Add "verified against spec-kit v1.0.7 (`fe1d00e3`), BMAD v6.12.0 (`05bfbd46`), superpowers v6.3.0 (`b36e0829`)" and a per-framework "known-unparsed" list (prose deps, FR/SC ids, `NEEDS CLARIFICATION`, `stories.yaml`, front-matter status, `AGENTS.md`-embedded project context).
22. `README.md:15` and `README.md:98`, `CHANGELOG.md:5`, `QUICKSTART.md:90` — today they name the three frameworks with **no version and no subset boundary**; `QUICKSTART.md:90` ("listing allowlisted GitHub Spec Kit, BMAD, or Superpowers files") invites a reader to point it at a real `_bmad-output/` tree, which is precisely where #4/#11/#12 bite. Add: supported upstream version window, the accepted-shape list, and the "advisory only, unparsed fields marked `enrichment_required`" caveat. Do **not** write "updated to latest versions" for an unmerged branch (§5.0#2).
23. `scripts/grok_artifacts.py:42` `--framework` choices and any `--help` text — only needs changing if a role is added (#14); the `choices=("spec-kit","bmad","superpowers")` tuple itself is still accurate.
24. `decisions.md` / `mistakes.md` (shared memory per `AGENTS.md`): record the ruling "upstream-format currency is asserted per framework with pinned tag SHAs and regex-probe evidence, never by bumping a version string", and record the root cause of the miss — `source_version` was accepted but never consumed, and no fixture used an upstream-shaped document, so v6.11/v6.12 BMAD drift was invisible to CI.

### 5.5 Already fine — explicitly do **not** "modernise" these

- Spec Kit task-row grammar (`SPEC_TASK` 113) and phase-heading gate (599): identical at v1.0.7, and identical across v0.16.5→v1.0.7. No change.
- Spec Kit role set and path allowlist incl. root `specs/` (67–73, 91). No change (fix the *fixtures*, not the code).
- BMAD `sprint-status.yaml` key/value hint path (663–671): format unchanged in v6.11.0 by upstream's own release note; probe matched. No change beyond #7 vocabulary totalisation.
- BMAD output-root prefixes `_bmad/`, `_bmad-output/` (92). Unchanged upstream. No change.
- All Superpowers handling (93, 377–380) — prefix-only, body unparsed. Only comments/docs (#13, #21) change, not behaviour.

---

## 6. NOT-VERIFIED

- **Generated-in-practice documents.** Upstream *templates/scripts* were read at the exact tags; no real project was produced by running `/speckit.tasks`, a BMAD workflow, or a superpowers run on this host. Whether generated `tasks.md` keeps the template's YAML front matter, and whether agent output deviates from template, is unconfirmed. All §3 counts are template-level, not corpus-level.
- **BMAD `main` past the tag.** `bmad-code-org/BMAD-METHOD@main` was pushed `2026-09-15T09:07:41Z`, 11 days after `v6.12.0`; unreleased shape changes there were not diffed. Spec Kit `v1.0.7` commit is same-day; superpowers `main` == `v6.3.0`.
- **Installed-layout paths.** BMAD artifact paths derive from `src/*/module.yaml` defaults, `customize.toml` defaults and skill `## Paths` blocks, plus docs — not from an observed `npx bmad install` tree. Users can override `output_folder`, so `PATH_PREFIXES` sufficiency is configuration-dependent.
- **PyPI/npm currency vs git tags** (`specify-cli`, BMAD package, superpowers channel-resolver RC channel): not inspected; only GitHub releases/tags.
- **spec-kit preset/override stack.** `.specify/templates/overrides/`, `presets/lean`, `presets/constitution-sync` can replace core command text; their generated shapes were not enumerated, so a lean-preset `tasks.md` could differ from §2.1.
- **Whether the intended scope of this change is really the adapters.** The brief names "third-party workflow components"; this tree contains no such pins (§5.0#1) and the adapters live on an unmerged branch. If the intended target is the repo's *own* `.superpowers/` working docs or bundled skills, this analysis covers the adapter half and the other half needs a separate inventory.
- `source_version` values `"1"`/`"6"`: whether they were ever intended as upstream versions is not documented anywhere in the branch; treated here as placeholders based on the absence of any consumer.
