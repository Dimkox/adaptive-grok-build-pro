# Implementation — GitHub App is the application

Route `0db5b77a9bf3`. Change `20260824-user-query-забудь-вообще-нахуй-про-ii-tonya-прил-0db5b7`. Write owner: `general_implementer`.

## What landed

- Expanded `test_operator_docs_do_not_present_chatgpt_webhook_as_live` so SPEC, PLAN, REPORT, README, and DECISIONS also `assertNotIn("ii-tonya", text)`. URL/host constants remain scan needles.
- Added `test_decisions_name_github_app_as_the_application` (`https://github.com/apps/adaptive-trust-ci` in `decisions.md`).
- Added `test_mistakes_do_not_call_nginx_the_application` (no `nginx for the existing app`).
- New `decisions.md` 2026-08-24 entry: «приложуха» is GitHub App `https://github.com/apps/adaptive-trust-ci`; webhook config lives on that App; no invented public webhook URL; loopback HMAC remains proven intake. File has no `ii-tonya`.
- Rewrote ChatGPT-hostname root cause; prepended overloaded-«приложение» mistakes entry.

## Unchanged

FastAPI, compose, env, plan, spec, activation report, README. No GitHub App hook PATCH, no repo webhook, no PEM read. M0.2 not claimed complete.

## Verify

```bash
python3 -m unittest trust-ci.tests.test_m0_invariants
```
