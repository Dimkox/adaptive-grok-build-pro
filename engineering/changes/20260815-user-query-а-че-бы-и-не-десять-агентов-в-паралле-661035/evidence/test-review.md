# test_review: PASS

Reviewer: `test_reviewer` (read-only). Write owner: `general_implementer`.
Route: `661035fd084d`
Change: `engineering/changes/20260815-user-query-а-че-бы-и-не-десять-агентов-в-паралле-661035`
Date: 2026-08-15

**PASS.** All six required characterizations exist in the tests that were read. Parent verification recorded `python3 -m unittest discover -s tests` as **155 tests, OK**.

## What was inspected

Change package: `brief.md`, `requirements.md`, `architecture.md`, `tasks.md`, `test-plan.md`.

Tests (read in full):

- `tests/test_repo_router.py` — new floor / micro / cap / fallback cases plus the existing Bitrix, frontend, data, AI, docs, integration routes
- `tests/test_policy.py` — second-writer deny and `write_roles` fallback

Implementation they claim to cover (read, not edited):

- `.grok-stack/adaptive_grok/router.py` — `DEFAULT_ROUTING`, `load_routing_config`, `_analysis_cap`, `unique_ordered(analysis)[:cap]`
- `.grok-stack/config/routing.json` — live floors and `max_parallel_analysis: 10`
- `.grok-stack/adaptive_grok/policy.py` — `write_roles()` fallback to `WRITE_ROLES`; second write-owner deny

## Required characterizations

| # | Required case | Test | Verdict |
| --- | --- | --- | --- |
| 1 | Generic feature `analysis_agents == ['repo_explorer', 'task_analyst', 'architect', 'docs_researcher']`; no domain architects; write not in analysis; `len <= 10` | `RouterTests.test_generic_feature_uses_widened_analysis_floor` (`Добавить функцию`) | **Present.** Exact four-name equality; `write_agent == general_implementer` and `assertNotIn(write_agent, analysis_agents)`; `assertLessEqual(..., 10)`; loops `bitrix_architect` / `data_architect` / `ai_architect` / `integration_architect` out. |
| 2 | Micro PHP bug: no `docs_researcher`, no `architect` | `RouterTests.test_micro_bug_skips_standard_analysis_floor` (`Исправь баг в одной функции PHP`) | **Present.** Asserts `complexity == micro` and both names absent. Older `test_micro_bug` only locks complexity; the skip test is the required characterization. |
| 3 | Cap=2 truncates to first two floor names; default generic still length 4 not 10 | `RouterTests.test_analysis_cap_truncates_and_does_not_pad` | **Present.** Mutates `routing.json` `max_parallel_analysis = 2` on a multi-domain REST/RabbitMQ/1C/SQL prompt and asserts `['repo_explorer', 'task_analyst']`. Fresh copy of the same generic prompt asserts `len == 4` and `len != 10`. |
| 4 | Missing and invalid `routing.json` fall back to the four-name floor | `RouterTests.test_missing_or_invalid_routing_json_uses_defaults` | **Present.** `unlink()` and `'{'` each rebuild `Добавить функцию` and assert the same four names as (1). |
| 5 | Existing Bitrix / frontend / data / AI / docs cases remain | `test_bitrix_bug_routes_specialists`, `test_frontend_focus_wins_inside_bitrix_repo`, `test_explicit_bitrix_frontend_stays_bitrix_owned`, `test_data_migration_route`, `test_clickhouse_event_migration_uses_data_implementer`, `test_ai_security_route`, `test_prompt_injection_and_tenant_isolation_are_high_risk`, `test_docs_can_have_write_owner_without_test_reviewer` | **Present.** Integration keep-green also remains (`test_event_integration_route`). Docs still has `code_reviewer` in and `test_reviewer` out. |
| 6 | Second write agent still denied; `write_roles` fallback | `PolicyTests.test_blocks_second_different_write_agent`; `PolicyTests.test_routing_write_roles_match_constant_and_fallback` | **Present.** Extra `general_implementer` stuffed into `allowed_agents` after the PHP write owner is already started → deny (`write owner` / `already active`). Missing and invalid `routing.json` both return `set(WRITE_ROLES)`. |

## Plan extras (not on the PASS/FAIL bar)

Test-plan item 3 (docs README → `code_reviewer` in, `test_reviewer` out) is the existing `test_docs_can_have_write_owner_without_test_reviewer`. Item 7 (second writer) is the policy test above.

## Characterization quality

These tests would fail on the regressions this change is meant to lock:

- Padding a generic feature to ten names, or dropping `docs_researcher` from the standard floor, breaks (1) and the default half of (3).
- Putting `architect` / `docs_researcher` on a micro PHP bugfix breaks (2).
- Ignoring `max_parallel_analysis` (or padding to the cap) breaks the cap=2 half of (3).
- Crashing or using an empty panel when `routing.json` is gone / `{` breaks (4).
- Domain routing drift breaks the keep-green set (5).
- Allowing a second writer, or `write_roles()` returning empty on a missing file, breaks (6).

`project_copy()` isolates the mutated / deleted `routing.json` cases.

## Non-blocking residuals

Not fail reasons. The required cases exist.

- Micro skip does not `assertEqual(analysis_agents, ['repo_explorer'])`. Requirements say “repo_explorer only”; the test only forbids `architect` and `docs_researcher`. PHP has no `analysis_domain_agents` entry, so the exact list is implied, not locked.
- `_analysis_cap` fallback for `0` / negative / `true` is untested. Missing/invalid file is tested; a present file with a bad cap is not.
- `write_roles` fallback is not asserted for an empty list or non-list `write_roles` value (implementation treats both as fallback).
- Cap=2 uses a multi-domain prompt rather than the generic feature. That is the stronger truncate case (floor + domain names exist before the slice). First two names after `unique_ordered` are still the floor prefix.

## Verification evidence

`.grok-stack/runtime/receipts/661035fd084d/verification.json`: `python-unittest` **pass**, `Ran 155 tests in 20.953s`, `OK`. Mode `pr`, profile `base`.

## Recommendation

**PASS.** Required floor, micro skip, cap-without-pad, missing/invalid fallback, keep-green domain/docs, and second-writer / `write_roles` fallback characterizations are in the suite and match the router/policy contract that landed.
