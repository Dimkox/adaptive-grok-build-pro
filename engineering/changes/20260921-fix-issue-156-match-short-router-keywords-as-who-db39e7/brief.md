# Issue #156 — explain and bound task keyword matches

Typed authority: [change-spec.yaml](change-spec.yaml).

User requested all issue work in parallel on 2026-09-21. Route db39e73f3dee has no named human gate. All selected analysis reports are complete under evidence/.

## Outcome and scope

Short word-shaped domain keywords match standalone words; every task-derived domain is explained by a persisted keyword map.

Use shared Unicode-aware matching for short (at most four characters) single-word domain keywords in route scoring and development-prompt detection; preserve longer keyword/phrase behavior, intent precedence and genuinely selected specialist owners. Persist optional bounded matched_keywords in new route records and admit/validate it in the closed reader while older records remain valid.

Allowed product/test surface: .grok-stack/adaptive_grok/router.py, .grok-stack/adaptive_grok/workflow_artifacts.py, tests/test_repo_router.py, tests/test_workflow_artifacts.py. Sole write role: general_implementer.

## Bounded ruling

The issue requests a general-owner fallback for short-only matches while also preserving genuine short-keyword specialist tasks. Apply fallback only when boundary filtering leaves no supported domain; do not demote valid SQL, UI or Bitrix D7 work. This bounded compatibility ruling is supported by independent architecture analysis. PR #140 owns release/review intent precedence and stays separate.

## Delivery dependency

Base is frozen PR #170 head 1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48, including issue164 clock correction. This independent branch is a successor; retain #170 unchanged. External push/PR/merge requires applicable exact authority; no deployment or provider operation is in scope.
