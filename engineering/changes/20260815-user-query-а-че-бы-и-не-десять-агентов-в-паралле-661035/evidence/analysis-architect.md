# Analysis — architect

Change: `20260815-user-query-а-че-бы-и-не-десять-агентов-в-паралле-661035`
Route: `661035fd084d` · write owner: `general_implementer`
Risk: low · complexity: standard · domains: generic

Bounded design so the router can fan out more **read-only** analysis agents (ceiling 10) in one wave, while keeping **exactly one write owner**. Do not invent unused specialists to pad to ten. Not a release.

Facts recovered from the tree and from `evidence/analysis-repo_explorer.md`. No new services, agents, hooks, or schema bump.

## Problem (observed)

The parallel analysis wave is already a first-class controller step (`.grok/skills/adaptive-delivery/SKILL.md` §2, `route_context` in `router.py`). The limiter is **who `build_route` puts on the list**, not the dispatcher.

Today, for this generic standard feature, the live route is:

| List | Contents | Size |
| --- | --- | --- |
| `analysis_agents` | `repo_explorer`, `task_analyst`, `architect` | 3 |
| `write_agent` | `general_implementer` | 1 |
| `review_agents` | `code_reviewer`, `test_reviewer` | 2 |

`docs_researcher` already exists (read-only, managed) but is only appended for `research` / `architecture` or a Bitrix domain (`router.py:222-223`). Domain architects already append only on domain match. There is no numeric cap and no padding — theoretical max analysis panel is **8**, the entire read-only analysis catalog.

`.grok-stack/config/routing.json` is documentation only. Its own description says runtime defaults live in `adaptive_grok.router`. Python never `load_json`s it. `write_roles` there is unused; `policy.py` has a duplicate `WRITE_ROLES` set.

Policy spawn rules (`policy.py:190-202`) already serialize writes:

1. agent must be in `route['allowed_agents']`;
2. a write role must equal `route['write_agent']`;
3. a second distinct write role already recorded in `agent-state.json` is denied.

Analysis and review agents that are on the allow-list may already spawn in parallel. There is no analysis semaphore. That is the correct split: **cap at route construction**, **singleton at write spawn**.

Existing router tests use `assertIn` for specialists and never `assertEqual` the generic analysis panel, so a floor widening plus a cap will not break Bitrix / frontend / data / AI / docs routes if write-owner and review conditions stay as they are.

## Proposed behavior

### 1. `routing.json` becomes the runtime source of floors and the analysis cap

`build_route(root, …)` loads `.grok-stack/config/routing.json` via existing `load_json`. Missing file, invalid JSON, or missing keys fall back to an in-module `DEFAULT_ROUTING` that matches the file (same pattern as `policy.py` `DEFAULT_PROTECTED`).

The file supplies:

- `max_parallel_analysis` (default **10**);
- analysis floors and domain-architect map;
- review floors and domain/risk reviewer maps;
- `write_roles` (already listed; make it live).

It does **not** become a rules engine. Intent / complexity / domain / risk predicates stay in `router.py`. The JSON only names the agent sets those predicates apply.

Keep `schema_version: 1`. Adding keys is backward compatible if the reader treats absence as defaults.

### 2. Widen the standard analysis floor — do not pad to 10

Selection order after unique-preserving concat, then slice:

1. `analysis_floors.always` — `repo_explorer`
2. `analysis_floors.feature_like` — `task_analyst`, when `intent in {feature, architecture, refactor, research}`
3. `analysis_floors.standard` — `architect`, `docs_researcher`, when `complexity != 'micro'`
4. `architect` only, when `complexity == 'micro'` **and** `intent in {feature, architecture, refactor}` (preserves `router.py:212-213`; feature is never micro today)
5. `analysis_domain_agents[domain]` for each matched domain, in existing domain order
6. `unique_ordered(analysis)[:max_parallel_analysis]`

`docs_researcher` therefore moves from `(research | architecture | bitrix)` to **every non-micro wave**. That is the only floor widening.

Do **not** append `bitrix_architect`, `integration_architect`, `data_architect`, or `ai_architect` unless that domain is already on the route. Do **not** create new agents. Do **not** move review or write roles into the analysis wave to fill the cap.

Expected panels (this is the new contract):

| Prompt class | `analysis_agents` | Notes |
| --- | --- | --- |
| Generic standard feature (this repo / this change) | `repo_explorer`, `task_analyst`, `architect`, `docs_researcher` | 4, not 10 |
| Micro PHP bug / micro docs | `repo_explorer` | floor does **not** apply |
| Bitrix bug (existing test) | includes `bitrix_architect` (and `docs_researcher` because non-micro Bitrix already had it) | write stays `bitrix_implementer` |
| REST + event + 1C (existing test) | includes `integration_architect`; now also `docs_researcher` | write stays `integration_implementer` |
| SQL / ES backfill | includes `data_architect` + `docs_researcher`; no Bitrix/AI architects | write stays `data_implementer` |
| RAG + prompt injection | includes `ai_architect` + `docs_researcher` | write stays `ai_implementer` |
| All four specialist domains at once | 8 names: floor 4 + four domain architects | still ≤ 10; catalog max is 8 |

Cap 10 is a ceiling for a future architect (e.g. `security_architect`), not a quota.

### 3. Review floors move to the same file; predicates stay

Keep today's review if-ladder; only the agent names come from config:

- write owner + not docs → `review_floors.delivery` (`code_reviewer`, `test_reviewer`)
- write owner + docs → `review_floors.docs` (`code_reviewer` only) — **`test_docs_can_have_write_owner_without_test_reviewer` must stay green**
- no write + `intent == 'review'` → `review_floors.review_intent`
- `bitrix` / `data` domains → `review_domain_agents`
- `risk == 'high'` or domain in `{security, ai, integration}` → `security_reviewer` via domain map + `review_risk_agents.high`
- `intent == 'release'` or `risk == 'high'` → `release_reviewer` via `review_floors.release` and/or `review_risk_agents.high`

No `max_parallel_review`. Current review catalog max is 6.

### 4. Write roles stay singular — do not parallelize them

Do not change write-owner selection (`router.py:225-246`). `write_agent` remains one name or `None`.

Policy spawn rules stay the three checks above. Do **not** add an analysis concurrency counter or new `agent-state` fields. The route list is the allow-list; the cap is applied when the list is built.

Make `routing.json` `write_roles` live: `evaluate_pre_tool` loads that list from the same file, falls back to the current `WRITE_ROLES` constant if missing/empty. Tests already copy `.grok-stack` via `project_copy`, so behavior is unchanged unless a test rewrites the file.

### 5. Adaptive-delivery does not invent extras

One sentence in both skill copies (§2): dispatch every `analysis_agents` entry (the route is already capped, default 10); do not spawn names that are not on the route to fill the cap; keep exactly one write owner.

`route_context` already says “Parallel read-only analysis agents”. Optional extra rationale line on the route: `analysis-wave={n}/{cap}`. Do not add a `Route` field.

## Data shape for `routing.json`

```json
{
  "schema_version": 1,
  "description": "Runtime routing floors and analysis-wave cap. Router and policy load this file; missing keys fall back to adaptive_grok.router / policy defaults.",
  "principles": [
    "parallelize read-heavy analysis and review",
    "use exactly one write owner",
    "add Bitrix specialist whenever repository or task has Bitrix signals",
    "add security review for auth, PII, AI, production, and external writes",
    "bind evidence to the current repository fingerprint",
    "do not pad the analysis wave with unmatched domain specialists"
  ],
  "max_parallel_analysis": 10,
  "write_roles": [
    "ai_implementer",
    "bitrix_implementer",
    "data_implementer",
    "frontend_implementer",
    "general_implementer",
    "integration_implementer",
    "php_implementer"
  ],
  "analysis_floors": {
    "always": ["repo_explorer"],
    "feature_like": ["task_analyst"],
    "standard": ["architect", "docs_researcher"]
  },
  "analysis_domain_agents": {
    "bitrix": ["bitrix_architect"],
    "api": ["integration_architect"],
    "event": ["integration_architect"],
    "integration": ["integration_architect"],
    "data": ["data_architect"],
    "ai": ["ai_architect"]
  },
  "review_floors": {
    "delivery": ["code_reviewer", "test_reviewer"],
    "docs": ["code_reviewer"],
    "review_intent": ["code_reviewer", "test_reviewer"],
    "release": ["release_reviewer"]
  },
  "review_domain_agents": {
    "bitrix": ["bitrix_reviewer"],
    "data": ["data_reviewer"],
    "security": ["security_reviewer"],
    "ai": ["security_reviewer"],
    "integration": ["security_reviewer"]
  },
  "review_risk_agents": {
    "high": ["security_reviewer", "release_reviewer"]
  }
}
```

Loader rules (keep in `router.py`, reuse from policy only for `write_roles` / `max_parallel_analysis` if convenient):

- unknown extra keys: ignore;
- unknown agent names: still emit (Grok spawn will fail later; do not invent a catalog validator here);
- `max_parallel_analysis` not an `int >= 1`: use `10`;
- lists that are not lists: use the matching `DEFAULT_ROUTING` entry;
- slice **after** `unique_ordered`, never pad.

`DEFAULT_ROUTING` in `router.py` must be byte-equivalent in meaning to the file so a deleted `routing.json` still produces the new floors (including `docs_researcher` on standard).

## Recommended file list

| File | Change |
| --- | --- |
| `.grok-stack/config/routing.json` | Replace the docs-only stub with the shape above. Keep existing principles + `write_roles`. |
| `.grok-stack/adaptive_grok/router.py` | `DEFAULT_ROUTING`, `load_routing_config(root)`, drive analysis/review assembly from it, slice analysis to the cap. Do not touch intent/domain/risk/complexity/write-owner predicates. |
| `.grok-stack/adaptive_grok/policy.py` | Load `write_roles` from the same file with `WRITE_ROLES` fallback. Keep the three spawn checks. No analysis semaphore. |
| `tests/test_repo_router.py` | New cases below. Keep every existing Bitrix / frontend / data / AI / docs assertion. |
| `tests/test_policy.py` | Only if write-role loading is added: one override/fallback case. Existing second-write-agent test must stay green. |
| `.grok/skills/adaptive-delivery/SKILL.md` | One sentence in §2 (cap is a ceiling; do not invent agents). |
| `.agents/skills/adaptive-delivery/SKILL.md` | Same sentence (mirror). |
| `CHANGELOG.md` | One 2.0.5 bullet. |

Optional, not required: `README.md` one-liner that `routing.json` is now loaded. Skip `AGENTS.md`, agent TOMLs, hooks, `Route` dataclass, installer, `VERSION`, packaging.

`MANIFEST.sha256` will go stale if the implementer regenerates it; this change is not a package/release. Do not treat manifest regen as part of the vertical slice unless a required check already fails on checksum.

## Test cases (fail first on the current tree)

Add against current `build_route` **before** the router edit. Existing specialist tests stay as they are.

1. **Standard generic feature includes the widened floor, not domain architects.** `build_route(root, 'Добавить функцию', …)` → `analysis_agents == ['repo_explorer', 'task_analyst', 'architect', 'docs_researcher']`. Write owner `general_implementer`. No `bitrix_architect` / `data_architect` / `ai_architect` / `integration_architect`. `write_agent not in analysis_agents`. `len(analysis_agents) <= 10`.

2. **Micro stays micro.** `'Исправь баг в одной функции PHP'` → `complexity == 'micro'`, `docs_researcher not in analysis_agents`, `architect not in analysis_agents`.

3. **Docs review contract unchanged.** `'Обнови README и документацию запуска'` → `write_agent == 'general_implementer'`, `code_reviewer` in review, `test_reviewer` not in review.

4. **Domain specialists still only on match** (existing tests, keep): Bitrix bug has `bitrix_architect` + `bitrix_implementer`; frontend-in-Bitrix stays `frontend_implementer` + `bitrix_reviewer`; explicit Bitrix+JS stays `bitrix_implementer`; REST/event/1C has `integration_architect` + `integration_implementer` + `security_reviewer`; SQL/ES has `data_implementer` + `data_reviewer`; RAG has `ai_implementer` + high risk + `security_reviewer`.

5. **Cap is honored and does not pad.** In `project_copy`, rewrite `routing.json` `max_parallel_analysis` to `2`, then a multi-domain feature prompt → `len(analysis_agents) == 2` and the two names are the first floor entries (`repo_explorer`, `task_analyst`). A second copy with the default file and a generic feature still has length 4, not 10.

6. **Missing / invalid config falls back.** Delete or overwrite `routing.json` with `{` → same panel as (1). Do not crash.

7. **Write singleton unchanged.** Existing `test_policy.py` second-write-agent case stays green. Do not add a path that puts two implementers on `allowed_agents` as equals.

Cases 1, 2, and 5 (cap=2) **fail on the current tree**. Cases 3, 4, and 7 **pass now** and must still pass after.

## What NOT to change

- Write-owner ladder, `INTENT_KEYWORDS`, `DOMAIN_KEYWORDS`, `HIGH_RISK` / `MEDIUM_RISK`, `_complexity`.
- New agents, new skills, new hooks, new `Route` fields, new runtime state.
- Review-phase agents in the analysis wave; write roles in the analysis wave.
- Padding unmatched specialists, or a “launch 10 no matter what” dispatcher.
- An analysis spawn semaphore in `policy.py` / `agent-state.json`.
- `stop_gate.py`, rematch helpers, quality profiles, installer, packages, `VERSION`.
- Bitrix core, protected-path rules, secret-read, MCP side-effect approval.

## Decisions (bounded rulings)

1. **Cap is a ceiling at `build_route`, default 10.** The user asked why not ten in parallel. The catalog has eight analysis agents. Filling to ten would require unused or invented names. Raise the ceiling; select only relevant readers.
2. **`docs_researcher` on every non-micro wave** is the smallest useful widening. It already exists, is read-only, and is the only generalist not on the current standard feature panel.
3. **`routing.json` names sets; Python keeps predicates.** A JSON rules engine is out of scope and would churn every existing route test.
4. **Policy does not grow a parallel-analysis counter.** Writes stay serialized by the existing three checks. Analysis parallelism is “whatever the route listed.”
5. **Keep `schema_version: 1` and in-module defaults.** A deleted or broken `routing.json` must not collapse routing.

## Rollout

- Library + config + tests + one skill sentence. No migration, no feature flag, no human gate.
- Next `UserPromptSubmit` that rematches a route picks up the new floor. Leftover `active-route.json` for this session stays at 3 until rematch; do not hand-edit runtime.
- Installed consumer copies get the new `routing.json` on the next install/update of this stack, not by editing their live route.
- Do not package, tag, merge, or publish as part of this change.

## Rollback

- Revert the files in the table. No data repair.
- Reverting only `routing.json` while leaving the new loader in place still works: defaults embed the new floor. To restore the 3-agent generic panel, revert `router.py` (and `DEFAULT_ROUTING`) as well.
- Reverting policy write-role loading restores the hardcoded set; spawn behavior is identical if the JSON list was unchanged.
- After rollback: `python3 -m unittest tests.test_repo_router tests.test_policy` and `python3 scripts/grok_verify.py --mode pr`.

## Residual risks

- A future `routing.json` edit that lists a write role under `analysis_floors` would put a writer on the parallel wave. Mitigate with test (1) (`write_agent not in analysis_agents`) and by not validating a full catalog here. Policy would still allow that writer only if it is also `write_agent`.
- Cap truncation drops **later** names (domain architects) first. A `max_parallel_analysis: 3` site loses `docs_researcher` and specialists on a feature wave. Acceptable: operators who lower the cap choose a smaller floor.
- Dual skill copies (`.grok/skills` vs `.agents/skills`) can drift if only one is edited.
- `HIGH_RISK` / domain keyword false positives are unchanged and out of scope.
- This session’s live route will not show four analysis agents until a non-follow-up rematch. Evidence reports for *this* change may still have been produced by the 3-agent panel; that is expected.

## Implementation order for `general_implementer`

1. Land failing tests 1, 2, and 5 (and keep 3, 4, 7 as characterization).
2. Write `routing.json` + `DEFAULT_ROUTING` + `load_routing_config`.
3. Switch `build_route` analysis/review assembly to the loader; apply the cap; add `docs_researcher` via the standard floor only.
4. Point policy `write_roles` at the same file with fallback.
5. Confirm existing Bitrix / frontend / data / AI / docs tests and the second-write-agent test still pass.
6. Skill one-liner in both copies; CHANGELOG last.
7. Do not spawn a second write agent. Do not regenerate packages.
