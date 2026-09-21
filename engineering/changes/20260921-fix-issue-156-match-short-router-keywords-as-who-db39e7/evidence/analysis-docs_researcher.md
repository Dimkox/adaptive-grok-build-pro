# Docs researcher analysis — issue #156

## Established behavior

`.grok-stack/adaptive_grok/router.py:180-187` scores every intent/domain keyword by substring in lowercased task text. `DOMAIN_KEYWORDS` contains `ui`, `api`, `d7`, `sql`, `1c`, and other short terms. The issue's `distinguish` → `ui` example follows directly from the code. `build_route()` uses task domains to select the sole `write_agent` (`router.py:325-344`), so the false frontend hit can supersede a database task. The risk matcher already has `_has_term()` at `router.py:232-243`, which demonstrates Unicode-aware word boundaries for one-word terms; domain scoring does not use it. The durable route is a dataclass serialized with `asdict()` and persisted by `state.py:94-118`; it has no matched-keyword field today.

## Acceptance criteria and negative controls

1. Test `distinguish`, `build`, `fluid`, and `guide` as embedded `ui` controls; test standalone `UI`, `React UI component`, and `Cypress flow` as positives. The exact #155 task wording cited by the issue should produce `data`/`integration` without `frontend`, and the chosen owner should be appropriate to those domains. Test `api` in `capillary`, `sql` inside a larger identifier, and genuine `API`, `SQL`, `D7`, `1C` tokens to prove the short-token rule is general and Unicode-aware.
2. Match short terms only at word boundaries (the issue threshold is length <= 4 after trimming). Preserve existing substring matching for longer words/phrases so Russian stems such as `миграц` and `интеграц` still recognize inflections. `_score()` feeds intent too, and `is_development_prompt()` has a separate raw-substring technical detector at `router.py:280-290`; test both entrypoints for false short-token positives if the helper is shared.
3. Persist the winning domain keywords in the `Route` dataclass so `to_dict()`, active route, and `runtime/routes/<id>.json` carry the same bounded, deterministic evidence. Include only matched configured terms, not arbitrary prompt snippets. Prove ordering is deterministic and a nonmatched domain has no keyword evidence.
4. A short-keyword-only owner fallback must be constrained to genuinely ambiguous evidence; broad suppression would demote real `UI`, `API`, `SQL`, or `D7` requests. Keep existing explicit specialist cases in `tests/test_repo_router.py` (Bitrix D7, React in Bitrix repo, REST API integration, SQL migration, AI) green, and add a short-only ambiguity control that expects `general_implementer` without removing real domain profiles/reviews.

`tests/test_repo_router.py` is the focused test home; `tests/test_hooks.py` covers route persistence and owner enforcement. This task is separate from release-intent priority in open PR #140. No code or tests were run or changed in this analysis.
