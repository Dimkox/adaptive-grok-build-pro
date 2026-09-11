# «Приложуха» is the GitHub App, not a public website

Change ID: `20260824-user-query-забудь-вообще-нахуй-про-ii-tonya-прил-0db5b7`
Route: `0db5b77a9bf3`
Write owner: `general_implementer`

## Problem

User (verbatim): forget that public domain; the application is the GitHub App `https://github.com/apps/adaptive-trust-ci`.

Prior agents misread «приложуха» / «эндпойнт на самой приложухе» as a public website. Sibling `b66b86` voided the ChatGPT hostname but `mistakes.md` still says that hostname is «nginx for the existing app», and `decisions.md` never names the GitHub App as the application.

## Outcome

Later agents treat the application as GitHub App `adaptive-trust-ci` (page `https://github.com/apps/adaptive-trust-ci`, App ID `4694114`, Installation `156003193`). They do not treat a public website as the app, webhook target, or pending TLS edge. No public webhook URL is invented. Loopback HMAC stays the proven intake. M0.2 stays **not done**.

## Scope

### In scope

- `decisions.md`: «приложуха» = GitHub App; webhook config lives on that App.
- `mistakes.md`: drop «nginx for the existing app»; log overloaded «приложение».
- `trust-ci/tests/test_m0_invariants.py`: five operator docs must not contain `ii-tonya`; `decisions.md` must contain the App URL; `mistakes.md` must not say nginx-as-app.

### Out of scope

- FastAPI / compose / env.
- `PATCH /app/hook/config`, App JWT/PEM, repository webhook.
- TLS, certbot, Apache, DNS, probing that public domain.
- Inventing a public webhook URL.
- Rewriting historical change-package evidence.
- Claiming M0.2 complete; protecting `main`.

## Constraints

- Backward compatibility: no API contract change.
- Operational: API stays `127.0.0.1:18080`.
- Five operator docs (plan, spec, activation report, README, `decisions.md`) must not contain substring `ii-tonya`.
