# code_review: PASS

Reviewer: `code_reviewer` (read-only). Write owner: `general_implementer`.
Route: `661035fd084d`
Change: `engineering/changes/20260815-user-query-а-че-бы-и-не-десять-агентов-в-паралле-661035`
Date: 2026-08-15

Independent review of the final tree against the change package and the floor/cap/write-owner contract. No application files were edited for this review.

## Verdict

**PASS.** Inspected the change package, `routing.json`, `router.py`, `policy.py`, both adaptive-delivery skill copies, and the new/existing router and policy tests. No blocking defect: the generic panel is four names (not ten), the cap slices and never pads, missing/invalid `routing.json` falls back, domain architects stay match-only, and `write_agent` remains a single scalar with policy still serializing writes.

## What was inspected

Change package:

- `brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`
- `evidence/analysis-architect.md` (approved assembly order)
- `tasks.md`, `rollback.md`

Implementation:

- `.grok-stack/config/routing.json`
- `.grok-stack/adaptive_grok/router.py` (`DEFAULT_ROUTING`, `load_routing_config`, `_analysis_cap`, `build_route` analysis/review/write assembly, `route_context`)
- `.grok-stack/adaptive_grok/policy.py` (`write_roles()`, `WRITE_ROLES`, Agent spawn checks)
- `.grok-stack/adaptive_grok/util.py` (`load_json` swallows `FileNotFoundError` / `JSONDecodeError`; `unique_ordered`)
- `.grok/skills/adaptive-delivery/SKILL.md` and `.agents/skills/adaptive-delivery/SKILL.md`
- `CHANGELOG.md` 2.0.5 bullet

Tests:

- `tests/test_repo_router.py` new floor / micro / cap / fallback cases plus keep-green Bitrix / frontend / integration / data / AI / docs
- `tests/test_policy.py` `write_roles` fallback and second-writer deny

## Contract checks

| Contract | Final tree | Result |
| --- | --- | --- |
| Generic standard feature = 4 analysis names, not 10 | `analysis_floors.always` + `feature_like` + `standard` → `repo_explorer`, `task_analyst`, `architect`, `docs_researcher`. No padding loop. Test locks exact list and `len != 10`. | Hold |
| No unmatched domain architects on generic prompts | Domain names come only from `analysis_domain_agents[domain]` for domains already on the route. Generic `'Добавить функцию'` has none of those keys. | Hold |
| Micro = no architect / no `docs_researcher` | Standard floor is skipped when `complexity == 'micro'`. Micro PHP bugfix is not feature-like, so the leftover `architect` branch does not fire. | Hold |
| Cap truncates, never pads | `analysis = unique_ordered(analysis)[:cap]`. Slice cannot grow the list. Cap=2 on a multi-domain prompt is the first two floor names only. | Hold |
| Missing / invalid `routing.json` falls back | `load_json(..., None)` then `copy.deepcopy(DEFAULT_ROUTING)`. Unlink and `'{'` both rebuild the four-name floor. No raise. | Hold |
| Exactly one write owner | Write ladder is still a single if/elif assignment; `write_agent` is `str \| None`. Not placed on the analysis list. | Hold |
| Policy still serializes writes | `write_roles(root)` from the same file, `WRITE_ROLES` fallback. Allow-list + owner match + `active_write_agents` still deny a second implementer. No analysis semaphore added. | Hold |
| Bitrix / frontend / data / AI / docs review assertions | Existing tests unchanged and still express the old predicates with config-sourced names. Docs still `code_reviewer` in / `test_reviewer` out. | Hold |

## Assembly review

`build_route` follows the approved order: always → feature-like → standard (non-micro) → hard-coded `architect` only on the dead micro+feature-like path → domain map → `unique_ordered` then cap. `docs_researcher` is the only floor widening. Review names moved into `review_floors` / `review_domain_agents` / `review_risk_agents`; the if-ladder (docs vs delivery, review-intent, bitrix, high-risk vs domain security/ai/integration, data, release) is equivalent to the previous hardcoded lists after `unique_ordered`.

`load_routing_config` merges known dict keys, ignores unknown top-level keys, rejects non-int / `< 1` / `bool` caps, and keeps default sub-lists when a file value is not a list. `DEFAULT_ROUTING` matches the live file for every key the router reads.

`route_context` and both skill copies state the cap is a ceiling, not a quota, and keep exactly one write owner.

## Non-blocking residuals

- The micro+feature-like `analysis.append('architect')` is hardcoded and unreachable under current `_complexity` (only bugfix/docs/test can be micro). Harmless preservation of the old comment; not a second writer and not a pad.
- Policy loads `write_roles` with its own `load_json` path instead of `load_routing_config`. Fallback behavior matches; spawn classification is unchanged for the shipped list.
- Unknown agent names in `routing.json` are still emitted (architect ruling: no catalog validator). Policy still denies names off `allowed_agents`.
- This session’s leftover `active-route.json` still lists three analysis agents. Expected until a non-follow-up rematch; not a `build_route` defect.

None of these are FAIL reasons. FAIL would require a selectable second writer, a generic panel padded to 10, unmatched domain architects on a generic prompt, a crash on missing/invalid `routing.json`, or a cap that pads.
