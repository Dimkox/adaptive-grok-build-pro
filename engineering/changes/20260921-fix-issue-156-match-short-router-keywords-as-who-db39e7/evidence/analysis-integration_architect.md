# Integration architect analysis — issue #156

## Route producer and readers

`router._score()` currently applies substring matching to all domain keywords. `_task_domains()` uses its scores to populate `task_domains`; `build_route()` then derives `domains`, risk, complexity, analysis/review roles, quality profiles, required receipts, and the sole writer from those domains. In the shipped #155 task text (`engineering/changes/20260920-fix-issue-155-guards-inside-the-semantic-bind-re-c4e47e/route.json`), `ui` is embedded in `distinguish`, so the unrelated `frontend` domain can select `frontend_implementer` before data/integration ownership. `is_development_prompt()` also has an independent raw-substring technical scan; if domain matching changes, align this scan so recognition and route classification use the same short-term semantics.

The durable record is `Route.to_dict()` through `state.set_active_route()` into both `active-route.json` and `runtime/routes/<id>.json`; `change.start_change()` copies it to `<change>/route.json`. Add the actual winning keywords per task domain to that record, distinct from `repo.signals` and repository-inferred domains. `workflow_artifacts.load_runtime_authority()` rejects unknown route fields via `RUNTIME_ROUTE_KEYS`, so any added `matched_keywords` field must be admitted there and bounded/validated. Preserve readers of older route records where this optional field is absent. A key-only map of domain to matched keywords is enough for diagnosis; offsets or snippets of the full prompt are unnecessary.

## Bounded behavior

Use Unicode-aware whole-word matching for word-shaped domain terms of at most four characters (`ui`, `api`, `d7`, `sql`, `1c`, Cyrillic `1с`), with current substring behavior for longer terms and phrases. Keep scoring and match evidence derived from the same match operation. Short-only hits should not promote an otherwise unsupported specialist as the sole writer; preserve an explicit long domain hit and the existing repository Bitrix owner precedence. Genuine `React UI component`, `Cypress flow`, `SQL migration`, `Bitrix D7`, and `1С` integration wording still needs the corresponding domain, profiles, review receipts, and owner.

Open PR #140 (`remotes/pr/140`, `e51a0d15`) only changes review-versus-release intent priority and removes `pull request`/` pr ` as review triggers. This issue should leave `_best_intent()` and `INTENT_KEYWORDS` untouched. Rebase/merge interaction is limited to nearby router lines and tests; a release prompt mentioning a PR must still route as `release` after integration.

## Acceptance checks

1. Feed the exact #155 task string to `build_route()`: no `frontend` task domain/profile/reviewer/owner; `data` and `integration` remain visible with matching keywords recorded in the durable route. The keyword map explains every task-derived domain and omits repository-derived ones.
2. Exercise negative embedded forms (`distinguish`/`ui`, longer words containing `api`, `sql`, `d7`) and positive standalone or punctuation-delimited forms in Latin and Cyrillic. Check `is_development_prompt()` for the same short-term distinction.
3. Serialize, load, and copy a new route through `load_runtime_authority()` and `start_change()`, and load an older route without the optional field. Assert closed-shape rejection of unrecognized fields still holds.
4. Keep existing Bitrix and genuine frontend/data/integration routing tests green, plus the PR #140 release-priority case. Required evidence and profile checks remain tied to legitimately matched domains.

Source inspection only; no product code or gate was changed or run for this analysis.
