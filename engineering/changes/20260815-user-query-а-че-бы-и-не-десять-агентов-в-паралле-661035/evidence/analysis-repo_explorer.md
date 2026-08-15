# Analysis — repo_explorer

Change: `20260815-user-query-а-че-бы-и-не-десять-агентов-в-паралле-661035`
Route: `661035fd084d`

Question: how this product currently selects and constrains parallel agents.

## 1. Agents under `.grok/agents/`

21 agents (21 `.toml` + 21 `.md`). Managed list matches: `.grok-stack/config/managed.json` lines 3–25. `tests/test_structure.py:76-80` only asserts `len(agents) >= 20` and TOML contract keys.

Classification is by `sandbox_mode` + instruction text in each `.toml`, not by a runtime registry.

### Analysis (8) — `sandbox_mode = "read-only"`, “Read-only analysis”

| Agent | File |
| --- | --- |
| `repo_explorer` | `.grok/agents/repo_explorer.toml` |
| `task_analyst` | `.grok/agents/task_analyst.toml` |
| `architect` | `.grok/agents/architect.toml` |
| `bitrix_architect` | `.grok/agents/bitrix_architect.toml` |
| `integration_architect` | `.grok/agents/integration_architect.toml` |
| `data_architect` | `.grok/agents/data_architect.toml` |
| `ai_architect` | `.grok/agents/ai_architect.toml` |
| `docs_researcher` | `.grok/agents/docs_researcher.toml` |

### Write (7) — `sandbox_mode = "workspace-write"`, “single write owner”

| Agent | File |
| --- | --- |
| `general_implementer` | `.grok/agents/general_implementer.toml` |
| `php_implementer` | `.grok/agents/php_implementer.toml` |
| `bitrix_implementer` | `.grok/agents/bitrix_implementer.toml` |
| `frontend_implementer` | `.grok/agents/frontend_implementer.toml` |
| `integration_implementer` | `.grok/agents/integration_implementer.toml` |
| `data_implementer` | `.grok/agents/data_implementer.toml` |
| `ai_implementer` | `.grok/agents/ai_implementer.toml` |

Same set as hardcoded `WRITE_ROLES` in `.grok-stack/adaptive_grok/policy.py:11-14` and as documentation list `.grok-stack/config/routing.json:11-19`.

### Review (6) — `sandbox_mode = "read-only"`, “Inspect the actual final diff”

| Agent | File |
| --- | --- |
| `code_reviewer` | `.grok/agents/code_reviewer.toml` |
| `test_reviewer` | `.grok/agents/test_reviewer.toml` |
| `bitrix_reviewer` | `.grok/agents/bitrix_reviewer.toml` |
| `security_reviewer` | `.grok/agents/security_reviewer.toml` |
| `data_reviewer` | `.grok/agents/data_reviewer.toml` |
| `release_reviewer` | `.grok/agents/release_reviewer.toml` |

8 + 7 + 6 = 21. No other agent files.

## 2. How `build_route` builds the four lists

Source: `.grok-stack/adaptive_grok/router.py` `build_route` at 202–361. `routing.json` is not read.

### `analysis_agents` (209–223)

Starts `['repo_explorer']`. Then appends, in this order:

1. `task_analyst` if `intent in {feature, architecture, refactor, research}` (210–211)
2. `architect` if `complexity != 'micro'` **or** `intent in {feature, architecture, refactor}` (212–213)
3. `bitrix_architect` if `'bitrix' in domains` (214–215)
4. `integration_architect` if any of `api`, `event`, `integration` (216–217)
5. `data_architect` if `'data' in domains` (218–219)
6. `ai_architect` if `'ai' in domains` (220–221)
7. `docs_researcher` if `intent in {research, architecture}` **or** `'bitrix' in domains` (222–223)

Deduped via `unique_ordered` (352). No size cap. Theoretical max analysis panel = 8 (all specialists fire).

### `write_agent` (225–246)

`None` when `intent in {review, research, release}` (225–227). Else first match:

- explicit task domain `ai` → `ai_implementer`
- explicit `frontend` and not explicit `bitrix` → `frontend_implementer`
- explicit `data` and not explicit `integration` → `data_implementer`
- explicit `integration`/`api`/`event` and not explicit `bitrix` → `integration_implementer`
- explicit or repo `bitrix` → `bitrix_implementer`
- explicit or repo `php` → `php_implementer`
- `'frontend' in domains` (repo+task) → `frontend_implementer`
- else → `general_implementer`

Exactly one or none.

### `review_agents` (248–262)

- if write owner: `code_reviewer`; plus `test_reviewer` unless `intent == 'docs'`
- elif `intent == 'review'`: `code_reviewer` + `test_reviewer`
- plus `bitrix_reviewer` if bitrix domain
- plus `security_reviewer` if `risk == 'high'` or domain in `{security, ai, integration}`
- plus `data_reviewer` if data domain
- plus `release_reviewer` if `intent == 'release'` or `risk == 'high'`

### `allowed_agents` (327)

```
unique_ordered([*analysis, *(review or []), *([write_agent] if write_agent else [])])
```

`.grok-stack/adaptive_grok/util.py:209-216` — first-seen order, no max.

Persisted by UserPromptSubmit (`.grok/hooks/user_prompt_submit.py:17-18`) calling `build_route` then `set_active_route`.

## 3. `routing.json` is documentation only

`.grok-stack/config/routing.json:3`: “Runtime defaults live in adaptive_grok.router and can be overridden here in future versions.”

Runtime Python never `load_json`s it. Only uses:

- existence check in `.grok-stack/adaptive_grok/doctor.py:27`
- hash in `MANIFEST.sha256`

`write_roles` in that file is unused. Policy uses its own `WRITE_ROLES` set (`policy.py:11-14`).

## 4. PreToolUse agent constraints

Hook: `.grok/hooks.json:27-37` → `.grok/hooks/pre_tool_use.py` → `evaluate_pre_tool` (`policy.py:146`).

Agent gate is only `policy.py:190-202`, and only when `tool` is `Agent` / `spawn_agent` / `agent` **and** a route exists **and** `_agent_type` extracts a non-empty string from `agent_type`/`type`/`name`/`role` (`policy.py:136-143`):

1. Outside `route['allowed_agents']` → deny: `Agent {type} is outside active route {id}` (193–195). Test: `tests/test_policy.py:195-201`.
2. Type is in `WRITE_ROLES` but not `route['write_agent']` → deny: `Route permits only write owner {expected}` (196–199).
3. Another write role already in `agent-state.json` active set (`state.py:133-139`) and this type is not that active one → deny: `Another write agent is already active` (200–202). Test: `tests/test_policy.py:210-218` (adds extra write to `allowed_agents` first; still blocked).

Selected write owner is allowed (`test_policy.py:203-208`).

Not gated: missing route; missing/unparseable agent type; analysis/review agents that *are* in `allowed_agents` (any number in parallel). Hook is fail-open (`pre_tool_use.py:67-75`).

## 5. Default panel for this repo / this route

This repo profile is `kind=generic`, empty domains/languages (live `active-route.json` `repo` + `detect_repo`). Prompt with no intent keywords defaults to `intent='feature'` (`router.py:99-103`). `_complexity` for `risk=low` + `intent=feature` is `'standard'` (not micro; micro requires bugfix/docs/test) (`router.py:169-174`).

Therefore:

| List | Contents | Size |
| --- | --- | --- |
| `analysis_agents` | `repo_explorer`, `task_analyst`, `architect` | **3** |
| `write_agent` | `general_implementer` | 1 |
| `review_agents` | `code_reviewer`, `test_reviewer` | 2 |
| `allowed_agents` | those 6, unique-ordered | **6** |

Live route `661035fd084d` matches that exactly. Adaptive-delivery treats analysis as the parallel panel (`SKILL.md` §2; `route_context` at `router.py:376`). There is no “10 agents” path and no numeric panel target.

## 6. Tests vs generic-feature analysis panel

**No test asserts the generic-feature analysis panel contents.**

`rg` over `tests/`:

- no `repo_explorer` mention
- no `assertEqual(route.analysis_agents, …)` / `assertListEqual` on analysis
- only two `analysis_agents` assertions, both specialist `assertIn`:
  - `tests/test_repo_router.py:47` — Bitrix bug includes `bitrix_architect`
  - `tests/test_repo_router.py:70` — REST/event/1C includes `integration_architect`

Closest generic-feature prompt is `'Добавить функцию'` (`test_change_receipts.py:47,55,102`, `test_hooks.py`, `test_deploy.py`) — used for change/receipt/hook flow, not panel membership.

`test_docs_can_have_write_owner_without_test_reviewer` (`test_repo_router.py:101-109`) asserts review composition for docs, not analysis.

`test_micro_bug` (`test_repo_router.py:111-114`) asserts `complexity == 'micro'` only.
