# Architect analysis — issue #156

## Verified failure and scope

`router._score()` currently tests `word in lowered`; `ui` therefore matches inside `distinguish`. `_task_domains()` feeds that false `frontend` domain to the write-owner priority, where `frontend` precedes `data` and `integration`. The same raw substring pattern appears in `is_development_prompt()`'s technical fallback. `state.set_active_route()` already persists the route dictionary to both active and per-ID JSON; the missing piece is matched-keyword data in that dictionary. The active route is a closed shape in `workflow_artifacts.RUNTIME_ROUTE_KEYS`, so adding a field requires updating that allowlist and bounded validation/tests.

## Bounded design

Use one domain-keyword matcher for `_task_domains()` and the technical fallback: for single word-shaped keywords of at most four characters, require Unicode word boundaries; preserve existing substring behavior for longer words and phrases. Preserve case-insensitive `UI`, `API`, `D7`, `SQL`, ASCII `1c`, and Cyrillic `1с`, including punctuation-separated `UI/API` and `D7/SQL`. Score from the matches and store a bounded, deterministic `matched_keywords` mapping from each *task-matched* domain to its winning keywords in the route record. Keep repository-inferred domains separate so the record does not imply a task match that never occurred. Avoid changing intent/release priority here; PR #140 owns that behavior.

Keep the current specialist precedence for genuinely matched task domains and Bitrix repository guarantees. The issue's literal fallback request conflicts with its own positive cases: a sole whole-word `UI` hit in “fix UI component” or `SQL` in “fix SQL migration” is valid explicit domain evidence; replacing its specialist with `general_implementer` would weaken existing behavior, and doing so for `D7` could bypass Bitrix ownership. The safe interpretation is to fall back to general only when no supported task or repository domain remains after boundary filtering. If broader ambiguity handling is wanted, it needs a separate policy decision with examples rather than silently downgrading all short terms.

## Regression checks and recovery

Test the exact #155 task wording for absence of `frontend` and its keyword evidence, plus genuine `React UI component`, `Cypress flow`, `D7`, `SQL`, `API`, and `1c/1с` tasks for retained owners, profiles, and review receipts. Assert durable route JSON contains only actual matched keywords and is accepted by the active-route closed-shape reader. A bad route can be recovered by re-routing the task; no receipt, policy, or production schema semantics need change.
