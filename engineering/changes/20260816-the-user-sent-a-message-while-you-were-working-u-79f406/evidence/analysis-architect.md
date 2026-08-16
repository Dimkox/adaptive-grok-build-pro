# Analysis — architect

Change: `20260816-the-user-sent-a-message-while-you-were-working-u-79f406`  
Route: `79f406e449de` · write owner: `ai_implementer` · reviews: `code_reviewer` + `test_reviewer` + `security_reviewer`  
Question: section outline for a complete README. Keep one complete mermaid graph. Expand to K14 (`Changes`, `Receipts`, `Doctor`, `Deploy`; \(C(14,2)=91\) undirected `---` edges) **or** keep K10 and add a second link-map table — pick one and be explicit. Structure tests must lock version `2.0.8`, `decisions.md` / `mistakes.md`, `AGENTS.md`, complete-graph pairwise edges, and links to `QUICKSTART` / `CHANGELOG` / `AGENTS`.

Read-only. No application-code edits. No `.env`. No push / merge / deploy.

Facts from this package, live `README.md`, `tests/test_structure.py`, `AGENTS.md`, `QUICKSTART.md`, `CHANGELOG.md`, `decisions.md`, `VERSION` (`2.0.8`), and the a13da8 K10 ship.

---

## Ruling

**Keep the existing K10 mermaid. Do not expand to K14. Add a second markdown link-map table that names Changes, Receipts, Doctor, and Deploy (and restates the ten stack nodes as paths).**

One mermaid fence. Same `graph TD`. Same ten IDs. Same 45 undirected `---` pairs. Same caption: every **core stack** piece is linked to every other. The four operational surfaces are first-class **navigation** targets, not a new complete clique.

Do **not** bump `VERSION`. It stays `2.0.8`. Do **not** rebuild the zip, tag, or cut a GitHub Release. Do **not** add a second mermaid. Do **not** touch `install_into.py`.

---

## Why K10 + link-map, not K14

| Option | What it is | Why rejected / kept |
| --- | --- | --- |
| **K14 mermaid** (`C(14,2)=91`) | Add `Changes`, `Receipts`, `Doctor`, `Deploy` as mermaid nodes and emit every pair | Rejected. 91 `---` lines is a hairball. `Doctor --- Mistakes` and `Deploy --- Skills` are not stack-coupling. It rewrites the locked a13da8 invariant (`decisions.md`: enumerate all 45 pairs) for four invoke/read surfaces that already exist as scripts and directories. |
| **K10 mermaid + link-map table** | Keep the complete stack graph; add one path table of 14 product surfaces | **Picked.** Satisfies “one complete mermaid graph” and “all links so a human or LLM can pick up current state.” Tables are the onboarding artifact; the clique is the coupling invariant. |

`Changes` / `Receipts` / `Doctor` / `Deploy` are operational surfaces:

| Surface | Kind | Already visible today |
| --- | --- | --- |
| Changes | durable packages under `engineering/changes/` | mentioned in “What this is”; created by `grok_change.py` |
| Receipts | fingerprint-bound evidence | “Verify + receipts” in the node table; `grok_review.py` in Scripts |
| Doctor | health / toolchain | Scripts row + Requirements offer-install |
| Deploy | prepare-only last mile | Scripts row + loop sentence |

They belong in a **path map**, not in the stack clique. Expanding the clique would make the caption a lie *or* force 91 edges. Keep the caption honest: the ten nodes are the core stack; the table is how you walk the product.

Forbidden substitutes (same as a13da8, still in force):

- Star, path, cycle, hub-and-spoke, “key links only”
- Second mermaid fence
- Directed `-->` mixed into the fence
- Extra 11th mermaid node
- `flowchart LR` rewrite
- `click` / `classDef` / subgraphs / `linkStyle`

---

## Gap vs the user ask

Live README is a thin product card, not a pickup document. An agent or a new human cannot get full current-state context from it alone.

| Need | Live README |
| --- | --- |
| Version identity | Title says v2.0.8. No `VERSION` file pointer. |
| `QUICKSTART.md` | **Zero hits.** |
| `CHANGELOG.md` | **Zero hits.** |
| `AGENTS.md` as a clickable contract | Backticks only; no markdown link. |
| Current-state snapshot | Missing (no GHA, local-only gate, published zips 2.0.0–2.0.8). |
| Agent 60-second read order | Missing. |
| Changes / Receipts / Doctor / Deploy as named surfaces | Doctor/Deploy are script rows; Changes/Receipts are not mapped. |
| Skills / agents / profiles catalog | Missing. |
| Directory map | Install copy list only. |
| Standing prohibitions | Scattered (MIT stanza, no EULA). |

K10 graph and root-log names are already correct (a13da8). This change **fills the README**, it does not redo the graph.

---

## Section outline (implement this, in this order)

Keep existing facts. Expand. Do not invent a new product.

### 1. Title + identity

Keep:

```markdown
# Adaptive Grok Build Pro v2.0.8

A commercial-grade product for **Grok Build** — free of charge, public, and MIT-licensed.
```

One extra line under the title, no new heading: identity pins.

```markdown
Version source of truth: [`VERSION`](VERSION) (`2.0.8`). License: [MIT](LICENSE). No EULA, no paid tier, no GitHub Actions.
```

### 2. Start here (NEW)

Heading: `## Start here`

Two short lists, then the three required markdown links (tests lock these exact targets).

**Human**

1. [`QUICKSTART.md`](QUICKSTART.md) — install Grok, copy the stack, first prompt.
2. This README — graph, surfaces, current state.
3. [`CHANGELOG.md`](CHANGELOG.md) — what each shipped version did.

**LLM / Grok agent**

1. [`AGENTS.md`](AGENTS.md) — contract. First rule is self-learning into [`decisions.md`](decisions.md) / [`mistakes.md`](mistakes.md).
2. `.grok-stack/runtime/active-route.json` — `allowed_agents`, one `write_agent`, evidence kinds.
3. `/adaptive-delivery` — controller. Do not invent a generic workflow.
4. Active change package under `engineering/changes/<change-id>/`.
5. This README § Current state + § Product link map.

Required markdown links (must appear in this section, clickable):

- `[QUICKSTART.md](QUICKSTART.md)` or `[QUICKSTART](QUICKSTART.md)`
- `[CHANGELOG.md](CHANGELOG.md)` or `[CHANGELOG](CHANGELOG.md)`
- `[AGENTS.md](AGENTS.md)`

Also name `decisions.md` and `mistakes.md` here (root paths, not `engineering/`).

### 3. Current state (NEW)

Heading: `## Current state`

A short table. Facts only, as of this tree:

| Fact | Value |
| --- | --- |
| Product version | `2.0.8` (`VERSION`, `.grok-stack/adaptive_grok/__init__.py`) |
| License | MIT, public, free. No EULA, no paid tier |
| Quality gate | Local only: `make verify` / `python3 scripts/grok_verify.py --mode pr` |
| GitHub Actions | Absent. Do not add `.github/workflows/` or Dependabot |
| Coverage ratchet | 74 in `pr` / `release` |
| Published zips | `packages/adaptive-grok-build-pro-v2.0.0.zip` … `v2.0.8.zip` + `.sha256` |
| Self-learning logs | Root `decisions.md` / `mistakes.md`. Stubs at `engineering/decisions.md` / `engineering/mistakes.md` |
| Stack graph | K10 complete mermaid, 45 undirected `---` edges |
| Agents / skills / profiles | ≥21 agents, ≥15 skills, 9 quality profiles |
| Last mile | `python3 scripts/grok_deploy.py` prints commands. Humans own tag / push / `gh release` |

Do not claim `origin/main` or GitHub Release freshness. Do not write a live git SHA (it goes stale).

### 4. What this is (KEEP + one pointer)

Keep the five existing bullets (routing, change packages, receipts, multi-agent, self-learning). Add one bullet that points at § Start here / § Product link map. Do not drop `self-learning`, `decisions.md`, or `mistakes.md`.

### 5. Stack graph (KEEP the K10 mermaid)

Heading stays `## Stack graph`. Keep the one-line intro.

**Exactly one** ` ```mermaid ` fence in the whole README. Parser in `test_readme_stack_graph_is_complete` takes the **first** fence.

Keep this node tuple and these display labels:

```text
Route, Skills, Agents, Hooks, Policy, Verify, Packages, Contract, Decisions, Mistakes

Contract["AGENTS.md"]
Decisions["decisions.md"]
Mistakes["mistakes.md"]
```

Keep all 45 undirected edges (do not re-derive, do not reverse-duplicate):

```text
Route --- Skills
Route --- Agents
Route --- Hooks
Route --- Policy
Route --- Verify
Route --- Packages
Route --- Contract
Route --- Decisions
Route --- Mistakes
Skills --- Agents
Skills --- Hooks
Skills --- Policy
Skills --- Verify
Skills --- Packages
Skills --- Contract
Skills --- Decisions
Skills --- Mistakes
Agents --- Hooks
Agents --- Policy
Agents --- Verify
Agents --- Packages
Agents --- Contract
Agents --- Decisions
Agents --- Mistakes
Hooks --- Policy
Hooks --- Verify
Hooks --- Packages
Hooks --- Contract
Hooks --- Decisions
Hooks --- Mistakes
Policy --- Verify
Policy --- Packages
Policy --- Contract
Policy --- Decisions
Policy --- Mistakes
Verify --- Packages
Verify --- Contract
Verify --- Decisions
Verify --- Mistakes
Packages --- Contract
Packages --- Decisions
Packages --- Mistakes
Contract --- Decisions
Contract --- Mistakes
Decisions --- Mistakes
```

Math (do not change): \(C(10,2)=45=10\times9/2\).

Keep the existing 10-row node-role table immediately under the fence (mermaid legend). Role cells already name the files; leave them.

### 6. Product link map (NEW — the second table)

Heading: `## Product link map`

This is the **second table**, not a second graph. Fourteen rows. Four new surfaces plus the ten stack nodes restated as paths so an agent has one lookup.

| Surface | Path | Role |
| --- | --- | --- |
| Route | `scripts/grok_route.py`, `.grok-stack/runtime/active-route.json` | Classify / show the live route |
| Skills | `.grok/skills/`, `.agents/skills/` | Domain skills (`SKILL.md`) |
| Agents | `.grok/agents/` | Routed agents (exactly one write owner) |
| Hooks | `.grok/hooks/`, `.grok/hooks.json`, `.grok/hooks/adaptive.json` | Lifecycle adapters |
| Policy | `.grok-stack/adaptive_grok/policy.py` | Deny / allow (invocations, not path words) |
| Verify | `scripts/grok_verify.py` | Local quality gate |
| Packages | `packages/`, `scripts/package_stack.py` | Tracked release zips |
| Contract | [`AGENTS.md`](AGENTS.md) | Engineering contract + self-learning first rule |
| Decisions | [`decisions.md`](decisions.md) | Patterns that paid for themselves |
| Mistakes | [`mistakes.md`](mistakes.md) | Root causes, not symptoms |
| Changes | `engineering/changes/`, `scripts/grok_change.py` | Durable change packages |
| Receipts | `.grok-stack/runtime/receipts/`, `scripts/grok_review.py` | Fingerprint-bound review / verify evidence |
| Doctor | `scripts/grok_doctor.py` | Health check + toolchain install offers |
| Deploy | `scripts/grok_deploy.py` | Prepare-only last mile; never tags / pushes / releases |

Column 1 must use those exact English surface names so tests can lock `Changes`, `Receipts`, `Doctor`, `Deploy`. Paths in column 2 must contain:

- `engineering/changes/`
- `.grok-stack/runtime/receipts/`
- `scripts/grok_doctor.py`
- `scripts/grok_deploy.py`

A one-line note under the table: this map is navigation; the mermaid above is the stack complete graph. Do not draw these fourteen as mermaid nodes.

### 7. How work flows (NEW, short)

Heading: `## How work flows`

One paragraph + the existing loop sentence, tightened:

```text
route → change package → verify → independent reviews → ready
      → python3 scripts/grok_deploy.py (prepare-only)
      → humans run the printed tag / push / GitHub Release commands
```

Point at `/adaptive-delivery` and `scripts/grok_change.py start`. Mention source-of-truth order by reference to `AGENTS.md` (do not paste the whole contract).

### 8. Requirements (KEEP)

Keep the toolchain table and `python3 scripts/grok_doctor.py --offer-install`. Keep the pointer at `.grok-stack/config/toolchain.json`.

### 9. Install (KEEP)

Keep `install_into.py` commands and the manual copy list (already includes root `decisions.md` / `mistakes.md`). Add one line: step-by-step is [`QUICKSTART.md`](QUICKSTART.md). Do **not** claim the installer copies the two logs.

### 10. Scripts + Make (KEEP, small add)

Keep the Scripts table. Add a Make row or a one-liner:

```text
make doctor | verify | status | package | deploy
```

Doctor and Deploy stay in this table **and** in the link map. Do not delete script rows.

### 11. Hooks (KEEP)

Keep the existing Hooks section. No new mermaid.

### 12. Skills, agents, profiles (NEW, compact)

Heading: `## Skills, agents, profiles`

Three compact inventories. Names only, not skill bodies.

**Skills** (15 under `.agents/skills/` and `.grok/skills/`):

`adaptive-delivery`, `task-triage`, `feature-workflow`, `bugfix-workflow`, `verification-evidence`, `release-readiness`, `bitrix-development`, `api-event-change`, `data-change`, `frontend-change`, `ai-rag-change`, `enterprise-integration`, `incident-response`, `legacy-modernization`, `security-sensitive-change`

**Write owners** (one per route): `ai_implementer`, `bitrix_implementer`, `data_implementer`, `frontend_implementer`, `general_implementer`, `integration_implementer`, `php_implementer`

**Analysis / review** (do not spawn off-route): `repo_explorer`, `task_analyst`, `architect`, `docs_researcher`, `ai_architect`, `bitrix_architect`, `data_architect`, `integration_architect`, `code_reviewer`, `test_reviewer`, `security_reviewer`, `bitrix_reviewer`, `data_reviewer`, `release_reviewer`

**Profiles** (`.grok-stack/config/quality-profiles/`): `base`, `ai`, `bitrix`, `contracts`, `data`, `frontend`, `infra`, `integration`, `php`

Floors live in `.grok-stack/config/routing.json`. `max_parallel_analysis` is a ceiling (10), not a quota.

### 13. Engineering tree (NEW, short)

Heading: `## Engineering tree`

| Path | Role |
| --- | --- |
| `engineering/changes/` | Durable packages: brief, requirements, architecture, tasks, test-plan, rollback, release, evidence |
| `engineering/contracts/` | OpenAPI / AsyncAPI / JSON Schema (empty scaffold until a consumer adds contracts) |
| `engineering/adr/` | ADRs (empty until a new service/queue/store is justified) |
| `engineering/runbooks/` | Human publish runbooks (`publish-v2.0.8.md`, …) |
| `engineering/decisions.md` | Stub. Canonical log is `/decisions.md` |
| `engineering/mistakes.md` | Stub. Canonical log is `/mistakes.md` |
| `engineering/reviews/` | Optional review-report sink named by `AGENTS.md` |

### 14. Package (KEEP)

Keep packager commands, `dist/` vs `packages/`, zip prefix. Point at [`packages/README.md`](packages/README.md).

### 15. Bitrix + examples (KEEP, one extra path)

Keep the Bitrix paragraph. Add `docs/bitrix-local-AGENTS.md` and `examples/bitrix-module/` as links. Example is a reference `local/modules` shape, not a marketplace module.

### 16. Standing prohibitions (NEW, short)

Heading: `## Standing prohibitions`

Bullet the existing product locks (already tested):

- No `.github/workflows/`, no Dependabot, no `install_into --with-ci`
- No `pyproject.toml` / `requirements.txt` / `setup.py` at repo root
- No Bitrix core edits (`bitrix/modules`, `bitrix/components`, `bitrix/js`)
- No reading `.env`, private keys, credential stores, production dumps
- No force-push, merge, publish, or production mutation without a fresh `scripts/grok_approve.py production`
- `grok_deploy.py` prepares; it does not execute tag / push / `gh release create`

### 17. License (KEEP)

Keep the MIT / commercial / free / no EULA / no paid tier stanza and the `make doctor` / `make verify` line.

---

## Tests (fail first, then implement)

Do **not** weaken existing methods. Add methods. Keep `test_readme_stack_graph_is_complete` on the ten IDs and 45 `combinations` pairs.

### Keep unchanged

| Method | Lock |
| --- | --- |
| `test_version_is_2_0_8_and_github_actions_are_absent` | `VERSION` is `2.0.8`; no GHA yml |
| `test_agents_md_starts_with_self_learning` | `AGENTS.md` first rule → root `decisions.md` / `mistakes.md` |
| `test_engineering_self_learning_stubs_are_pointers` | stubs only |
| `test_readme_names_root_self_learning_logs` | README names both logs + self-learning |
| `test_readme_stack_graph_is_complete` | first mermaid fence: exactly the 10 IDs, 45 unique `---`, pair set == `combinations` |
| `test_readme_is_free_mit_commercial_product` | MIT, commercial, free, public, no EULA, no paid tier |
| `test_package_version_matches_version_file` | `__version__ == VERSION` |

### Add

**`test_readme_links_quickstart_changelog_agents`**

README body contains markdown links to the three docs. Accept either label form:

```text
[QUICKSTART](QUICKSTART.md)     or  [QUICKSTART.md](QUICKSTART.md)
[CHANGELOG](CHANGELOG.md)       or  [CHANGELOG.md](CHANGELOG.md)
[AGENTS.md](AGENTS.md)
```

Also assert the strings `QUICKSTART.md`, `CHANGELOG.md`, and `AGENTS.md` appear outside the mermaid fence. Do not accept backticks-only for these three.

**`test_readme_link_map_names_operational_surfaces`**

After the mermaid fence, a markdown table names all four:

```text
Changes, Receipts, Doctor, Deploy
```

and contains the four paths:

```text
engineering/changes/
.grok-stack/runtime/receipts/
scripts/grok_doctor.py
scripts/grok_deploy.py
```

Assert mermaid still does **not** contain those four IDs as node ids (`Changes`, `Receipts`, `Doctor`, `Deploy` must be absent from the first mermaid fence). That is the K10-not-K14 lock.

**`test_readme_declares_version_2_0_8`**

README title or first heading contains `2.0.8`. Complements the VERSION-file test; stops a title drift to `2.0.9` while `VERSION` stays `2.0.8`.

Red on the current tree:

- no `QUICKSTART.md` / `CHANGELOG.md` in README
- no markdown link to `AGENTS.md`
- no `Changes` / `Receipts` rows
- mermaid is already K10 (graph test stays green)

Write the new tests first. Confirm the two new link tests fail. Then edit README.

Do **not** parse `CHANGELOG.md` for log paths. §2.0.8 is the 2.0.8 ship record and still says `engineering/decisions.md`. Leave it.

---

## Installer / packager / identity

| Surface | Ruling |
| --- | --- |
| `VERSION` | **2.0.8.** Do not touch. |
| `CHANGELOG.md` | Do not add `## 2.0.9` or `## Unreleased`. Optional one-line under §2.0.8 is out of scope; this is a docs-complete change on the same version. |
| `QUICKSTART.md` | No mermaid. May add a single “full map: README” pointer if cheap; not required. |
| `AGENTS.md` | No edit. Already the contract. |
| `decisions.md` / `mistakes.md` | Implementer may append one decision: “README onboarding is a link map, not a K14 mermaid.” At most three sentences. |
| `scripts/install_into.py` | **No edit.** Do not add the logs to `MANAGED_FILES`. |
| `package_stack.py` / zips / `dist/` | **Out.** |
| `.github/`, `pyproject.toml`, `requirements.txt`, `setup.py` | Forbidden. |
| Skills / agents / hooks / policy | **No edit.** README inventories them; it does not change them. |

---

## Write-owner sequence

One owner: `ai_implementer`. Smallest vertical.

1. Add the two (or three) new `StructureTests` methods. Confirm link-map + QUICKSTART/CHANGELOG/AGENTS tests fail on the current README.
2. Edit only `README.md` to the outline above. Do not rewrite the mermaid; copy it forward unchanged.
3. Optional: one `decisions.md` entry (K10 + link-map, not K14).
4. Confirm `python3 -m unittest tests.test_structure -q` is green.
5. Path-limited commit: `README.md`, `tests/test_structure.py`, this change package, optional `decisions.md`. Not `git add -A`.
6. `python3 scripts/grok_verify.py --mode pr` on the **final** tree (after evidence files that will remain).
7. Dispatch `code_reviewer`, `test_reviewer`, `security_reviewer`. Record the exact route evidence kinds.

Architect does not implement and does not push. `release.md` in this package: docs only, no tag unless the user later asks.

---

## Risks

| Risk | Mitigation |
| --- | --- |
| Implementer “completes” the graph to K14 | New test: those four IDs are **absent** from the mermaid fence; pair count stays 45 |
| Second mermaid “for the 14 surfaces” | Existing parser uses the first fence; new test can assert `text.count('```mermaid') == 1` |
| Title bumped to 2.0.9 | `test_readme_declares_version_2_0_8` + existing VERSION test |
| Installer “helpfully” copies logs | Do not touch `install_into.py` |
| Pasting all of `AGENTS.md` into README | Outline forbids it; link + 60-second read order only |
| Catalog drift (rename a skill, forget README) | Inventory is informative; do not hard-lock all 15 names unless cheap. Lock the four operational surfaces and the three doc links. |
| Receipts recorded before the last README/test write | Verify + reviews only after the last file that will stay |

---

## Out of scope (explicit)

- K14 mermaid / 91 edges
- Second mermaid
- `VERSION` bump, zip, tag, GitHub Release
- Installer / packager / hook / policy / skill / agent code
- OpenAPI / AsyncAPI / schema / ADR content
- Bitrix core or example-module behavior
- Coverage ratchet, Ruff/Bandit config
- Rewriting `CHANGELOG.md` §2.0.8
- Push / merge / deploy from this agent

No named human gate. Complexity `standard`, risk `medium` (docs + structure-test contract on a published 2.0.8 tree). Proceed after this design.
