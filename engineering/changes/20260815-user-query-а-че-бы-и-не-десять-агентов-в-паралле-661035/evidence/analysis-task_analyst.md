# Analysis — task_analyst

Change: `20260815-user-query-а-че-бы-и-не-десять-агентов-в-паралле-661035`
Route: `661035fd084d`
Role: `task_analyst` (read-only). This report does not implement.

## User ask

«а че бы и не десять агентов в параллель пускать М?» — why not just launch ten agents in parallel.

## Product outcome

A developer who asks that question gets a **wider read-only fan-out**, still **exactly one write owner**.

Observable result:

- A standard feature on a generic repo still starts a **small** analysis panel (today: 3). It is **not** padded to ten.
- A high-risk, domain-rich task can put **more independent read-only specialists** on the analysis wave, up to a documented cap of **10**.
- Review still runs **after** implementation, in its own parallel wave, still ≤ 10.
- The hook still refuses a second writer and any name outside `allowed_agents`.
- “Ten” is a **ceiling**, not a staffing target and not ten implementers.

## Baseline (facts, not design)

Aligned with `evidence/analysis-repo_explorer.md` and `adaptive_grok.router.build_route`.

| Situation | Analysis (one wave) | Write | Review (later wave) | Allowed |
| --- | ---: | ---: | ---: | ---: |
| This repo, this prompt (generic feature) | 3 (`repo_explorer`, `task_analyst`, `architect`) | 1 (`general_implementer`) | 2 (`code_reviewer`, `test_reviewer`) | 6 |
| Theoretical max today | 8 | 0 or 1 | 6 | 15 |
| Numeric target / cap today | none | 1 | none | none |

`routing.json` is documentation only. Runtime never loads it. Policy already blocks off-route agents and a second write role. Adaptive-delivery already says: parallelize analysis, one write owner, parallelize review after verification.

Domain gaps on the current 21-agent roster: `security`, `frontend`, `php`, and `infra` have no analysis specialist. That is why one analysis wave cannot reach 10 today.

## Rulings

Recorded so architect / implementer do not re-litigate them. This route has no named human gate.

1. **“10” is a per-wave concurrent read-only cap, not a default.** Do not fill unused slots. Do not spawn ten copies of one role.
2. **Write owner stays 0 or 1.** Ten implementers is out of scope. Policy must keep denying a second writer even if someone stuffs extra write names into `allowed_agents`.
3. **Waves stay sequential.** Analysis → one write owner → verification → review. Do not merge analysis and review into one 10-pack just to hit the number.
4. **Specialists stay signal-driven.** `bitrix_architect` / `bitrix_reviewer` only when `bitrix` is a domain. A Python-only or generic-only task must not grow Bitrix, 1C, or AI agents.
5. **Widen without padding.** Add at most the minimum extra *read-only* specialists needed so a documented high-risk multi-domain fixture can reach the analysis cap. Prefer existing domain gaps (`security_architect`, `frontend_architect`) over invented generic “worker-4…10” roles. If a new name is added, it needs a `.grok/agents/*.toml` contract and `sandbox_mode = "read-only"`.
6. **Across phases, more than 10 unique read-only is allowed** because they are not concurrent. Today that is already 8 + 6 = 14. After widening, analysis(≤10) + review(≤10) may exceed 10 unique names on the route.
7. **Missing / invalid `routing.json` falls back to built-in defaults** (current `build_route` behavior). Route construction must not crash. Unknown names never enter `analysis_agents`, `review_agents`, `write_agent`, or `allowed_agents`.
8. **This change is router / policy / routing-config / tests.** Not a release, not packaging, not VERSION bump, not hook fail-closed, not a new orchestrator.

## In scope

- Declare and enforce `10` as the read-only per-wave cap (analysis list and review list each ≤ 10).
- Keep default generic-feature analysis at the current small panel (3), not 10.
- Widen the high-risk / multi-domain analysis panel so ~10 independent read-only agents is *reachable* when domains justify it.
- Keep `write_agent` cardinality 0 or 1; keep `WRITE_ROLES` enforcement.
- Safe handling of missing/invalid `routing.json` and unknown agent names.
- Characterization tests for the two flows below plus the empty/error cases.
- Sync any live catalog with `WRITE_ROLES` / `.grok/agents` so docs and runtime cannot drift the way `routing.json` `write_roles` already does.

## Out of scope / non-goals

- Ten implementers, ten write owners, or parallel writers of any count > 1.
- Launching `bitrix_architect` (or any Bitrix/1C/AI specialist) on a Python-only or generic-only task.
- Padding a standard generic feature to ten agents.
- Spawning ten identical `repo_explorer` / `architect` clones.
- Running review agents in the analysis wave (or analysis agents in the review wave) just to make the count look like 10.
- Changing hook fail-open semantics, Stop-gate softness, or production-invocation matching.
- Push, merge, deploy, tag, GitHub Release, VERSION/package bump.
- Reading `.env` or credentials.
- New queue, service, or dispatcher process. Stay inside `build_route` + policy + existing hooks.

## Acceptance criteria

Copy into `requirements.md`. Each row is a failing-test candidate.

### A. Primary flow — standard feature on a generic repo

- [ ] **Given** a generic repo (no Bitrix/PHP/frontend/data/AI signals) and prompt «а че бы и не десять агентов в параллель пускать М?» (or equivalent feature text with no domain keywords), **when** `build_route` runs, **then** `analysis_agents == ['repo_explorer', 'task_analyst', 'architect']`, `write_agent == 'general_implementer'`, `review_agents == ['code_reviewer', 'test_reviewer']`, `len(allowed_agents) == 6`, and every name is in the known catalog.
- [ ] **Given** that route, **when** adaptive-delivery dispatches analysis, **then** it may start those three read-only agents in parallel and must not start the other 18 roster names.
- [ ] **Given** that route, **when** PreToolUse sees `Agent`/`spawn_agent` for `bitrix_architect`, `ai_implementer`, or any write role other than `general_implementer`, **then** it denies with the existing outside-route / write-owner reasons.
- [ ] **Given** that route, **when** a second write role is appended to `allowed_agents` and the first write owner is already active, **then** spawning the second writer is still denied.

### B. High-risk / domain-rich flow — can we actually reach ~10?

Honest answer against current code: **not in one analysis wave (max 8). Yes across analysis + review (max 14 unique, sequential).** After this change, one analysis wave must be *able* to reach the cap when enough independent domain specialists apply; we still do not launch them as writers.

- [ ] **Given** a high-risk architecture-style prompt that combines Bitrix + API/event/integration + data + AI + security (and frontend if a frontend analysis role is added), **when** `build_route` runs, **then**:
  - `len(analysis_agents) <= 10`
  - `len(review_agents) <= 10`
  - `write_agent` is exactly one implementer (or `None` only for review/research/release intents)
  - `analysis_agents` contains only `sandbox_mode = "read-only"` analysis names
  - `review_agents` contains only review names
  - every selected specialist is justified by a domain or intent already on the route (no padding)
  - after widening, `len(analysis_agents)` on this fixture is **≥ 8 and, if two gap specialists exist, == 10**
- [ ] **Given** that same route, **when** counting unique read-only names across `analysis_agents + review_agents`, **then** the total may exceed 10 (sequential waves). The product does **not** treat that as a violation.
- [ ] **Given** that route, **when** analysis is in flight, **then** review agents are not required to start in the same wave. Reaching 10 by collapsing the two waves is a fail.
- [ ] **Given** a Python-only / generic prompt, **when** `build_route` runs, **then** `bitrix_architect`, `bitrix_reviewer`, `integration_architect`, `ai_architect` are absent even though the cap is 10.

### C. What “10” means — cap vs default

- [ ] **Given** the routing configuration (live `routing.json` if it becomes loaded, otherwise the router constant that `routing.json` must document), **when** a human reads it, **then** it states `read_only_wave_cap = 10` (name may vary) and `write_owner_cap = 1`, and it does **not** state a default panel size of 10.
- [ ] **Given** a route that would otherwise select 11+ analysis names, **when** `build_route` runs, **then** `len(analysis_agents) == 10`, extras are dropped in a documented priority (signal-driven specialists keep their place; padding / unknown / duplicate names go first), and `allowed_agents` does not smuggle the dropped names back in.
- [ ] **Given** a generic feature, **when** `build_route` runs, **then** `len(analysis_agents)` stays 3 (default), not 10 (cap unused).
- [ ] **Given** any route, **when** `write_agent` is set, **then** it is a single string from `WRITE_ROLES`, never a list of ten.

### D. Empty / error — missing `routing.json`, unknown names

- [ ] **Given** `.grok-stack/config/routing.json` is missing, **when** `build_route` runs on a generic feature prompt, **then** it succeeds with the built-in default panel (3 analysis / 1 write / 2 review) and does not raise.
- [ ] **Given** `routing.json` is present but invalid JSON (or `{}` with no usable fields), **when** `build_route` runs, **then** the same built-in defaults apply.
- [ ] **Given** `routing.json` (or any catalog it feeds) lists unknown names such as `worker_7` or `bitrix_implementer_2`, **when** `build_route` runs, **then** those names do not appear in `analysis_agents`, `review_agents`, `write_agent`, or `allowed_agents`.
- [ ] **Given** an active route whose `allowed_agents` is the legitimate set, **when** PreToolUse sees `agent_type=worker_7` (or any unknown / off-route name), **then** it denies (`outside active route`).
- [ ] **Given** no active route, **when** PreToolUse sees an Agent spawn, **then** behavior stays as today (no new hard lockout). Do not fail-closed the hook in this change.

### E. Compatibility and evidence

- [ ] **Given** the existing router tests (Bitrix write owner, frontend-inside-Bitrix, integration/data/AI routes, review/release with no write owner, docs without `test_reviewer`, one-write-owner policy), **when** the new tests run, **then** those assertions stay green.
- [ ] **Given** the change is implemented, **when** `python3 -m unittest discover -s tests` and `python3 scripts/grok_verify.py --mode pr` run against the final tree, **then** they pass. Review receipts are recorded only after that last tree write.

## Failure and edge cases

| Case | Expected |
| --- | --- |
| User literally asks for “10 agents” on a generic repo | Still the 3+1+2 panel. The ask changes the *cap policy*, not the default roster. |
| Micro bugfix (`complexity=micro`, intent bugfix/docs/test) | Stays smaller than the standard feature panel. Do not promote it to 10. |
| `intent in {review, research, release}` | `write_agent is None`. Read-only fan-out may still widen; do not invent a writer to make the count nicer. |
| Duplicate name from two triggers | `unique_ordered` keeps one. Duplicates do not count toward the cap as extra seats. |
| Catalog / `WRITE_ROLES` / `routing.json` write_roles drift | Single source of write roles. A test fails if they disagree. |
| Analysis agent listed as write, or writer listed as analysis | Route builder rejects the misclassification. |
| 11th legitimate specialist | Dropped by cap; recorded in route `rationale` so it is visible, not silent. |

## Non-functional

- **Security:** no new production writes; secret-path and protected-path policy unchanged; unknown agents cannot be smuggled via config.
- **Reliability:** missing `routing.json` is a fallback, not an outage. Hook remains fail-open.
- **Performance:** default panel stays 3 concurrent analysis agents. Cap 10 is only for domain-rich routes. No extra process manager.
- **Observability:** `route_context` / `grok_route --json` show the selected lists and, after the change, the cap (and any dropped names in `rationale`).
- **Compatibility:** existing `allowed_agents` consumers keep seeing a flat unique list. `write_agent` stays a scalar.

## Constraints

- Backward compatibility: existing specialist routing and one-write-owner tests must remain valid.
- Data/privacy: do not read `.env`, keys, or dumps.
- Operational: no push / merge / deploy as part of this change.
- Contract: one `write_agent` per route; analysis and review are independent read-only sets; only `allowed_agents` may be spawned.
- Bitrix: none on this generic repo; Bitrix rules apply only when a future route actually has the `bitrix` domain.

## Suggested tests (for `test-plan.md`)

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Generic feature / this user prompt → analysis panel is 3, write is 1, review is 2 | new `test_repo_router` assertion |
| P0 | Multi-domain high-risk fixture → analysis ≤ 10, ≥ 8, write cardinality 0\|1, no padding | new router test |
| P0 | Second writer denied even if listed in `allowed_agents` | existing `test_blocks_second_different_write_agent` |
| P0 | Unknown / off-route name denied | existing `test_blocks_agent_outside_route` + new unknown-name case |
| P0 | Missing or invalid `routing.json` → built-in defaults, no exception | new test |
| P1 | Python-only prompt never selects `bitrix_architect` | new router test |
| P1 | Cap truncates a synthetic 11-name analysis list; dropped names in `rationale` | new router test |
| P1 | `WRITE_ROLES` matches `routing.json` write-role list and `sandbox_mode=workspace-write` agent files | new structure/policy test |
| P1 | Existing Bitrix / integration / data / AI / docs / release cases stay green | current `test_repo_router.py` |

## Handoff

Architect should decide *where* the cap lives (constant in `router.py` vs loaded `routing.json`) and *which* 1–2 read-only specialists fill the security/frontend gaps so a domain-rich analysis wave can actually reach 10. Do not invent writers. Do not pad the generic default.

Implementer is `general_implementer` only. Analysis and review stay inside this route’s `allowed_agents` until that implementation lands.

Success for the user ask: **we can run up to ten *read-only* specialists when the work is actually that wide; we still refuse ten writers; a normal feature on this repo still starts three analysts, not ten.**
