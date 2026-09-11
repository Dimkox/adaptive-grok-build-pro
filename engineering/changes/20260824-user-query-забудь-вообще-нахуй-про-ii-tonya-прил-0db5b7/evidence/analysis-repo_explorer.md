# repo_explorer — `ii-tonya` in tracked operator-facing files

Route `0db5b77a9bf3`. Change `20260824-user-query-забудь-вообще-нахуй-про-ii-tonya-прил-0db5b7`.

Did **not** probe any `ii-tonya` hostname. Did **not** call GitHub App hook APIs. Did **not** read PEM/secrets.

User (verbatim): forget `ii-tonya`; the app is GitHub `https://github.com/apps/adaptive-trust-ci`.

## Verdict

**Operator live-target docs are already clean of `ii-tonya`.** Remaining mentions are a **named mistake** (`mistakes.md`) and **negative-test constants** (`test_m0_invariants.py`) that forbid the ChatGPT host/URL in plan/spec/activation/README/`decisions.md`. Activation report already records App slug `adaptive-trust-ci`, App ID `4694114`, Installation ID `156003193`. It does **not** spell the HTTPS GitHub App URL `https://github.com/apps/adaptive-trust-ci`; identity is slug + numeric IDs + loopback public base.

## Scan table (requested files only)

| File | `ii-tonya` present? | Presentation |
| --- | --- | --- |
| `decisions.md` | **No** | 2026-08-24 entries void the ChatGPT hostname without naming it; public base stays loopback until a named HTTPS path hits FastAPI HMAC. |
| `mistakes.md` | **Yes, once** | **Named mistake**, not a live target. Symptom quotes `https://trust-ci.ii-tonya.ru/webhooks/github`. Root cause: ChatGPT-invented hostname copied as operator truth; do not configure/probe/TLS. |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | **No** | (no `ii-tonya` substring) |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | **No** | (no `ii-tonya` substring) |
| `engineering/runbooks/trust-ci-activation-report.md` | **No** | Public base `http://127.0.0.1:18080`. App identity as below. |
| `README.md` | **No** | (no `ii-tonya` substring) |
| `trust-ci/tests/test_m0_invariants.py` | **Yes, as forbidden strings** | `CHATGPT_WEBHOOK_URL` / `CHATGPT_WEBHOOK_HOST` used only in `test_operator_docs_do_not_present_chatgpt_webhook_as_live` (`assertNotIn` on SPEC, PLAN, REPORT, README, DECISIONS). **Not** a live webhook/TLS target. `mistakes.md` is **not** in that scan set (intentional: the log must name the URL). |

## GitHub App identity already on the activation report

From `engineering/runbooks/trust-ci-activation-report.md` (lines 5, 13–17):

| Field | Recorded value |
| --- | --- |
| GitHub App slug | `adaptive-trust-ci` |
| App ID | `4694114` |
| Installation ID | `156003193` |
| `TRUST_CI_PUBLIC_BASE_URL` | `http://127.0.0.1:18080` |
| Webhook | Loopback HMAC POST; **not** a GitHub-registered public webhook |

Literal URL `https://github.com/apps/adaptive-trust-ci` is **absent** from the activation report. The slug is the GitHub App slug that that URL denotes. Worker env IDs are described as gitignored; this explorer did not open env/PEM.

## Out of scan (context only)

Historical change packages (`cec0c7`, `010964`, `b66b86`) still contain `ii-tonya` as retracted briefs/evidence. `test_operator_docs_do_not_present_chatgpt_webhook_as_live` does not scan `engineering/changes/**`. Current change-package stubs echo the user query (includes `ii-tonya` as the thing to forget).

## Implication for this slice

No live operator-doc leak of `ii-tonya` as webhook/TLS target. If the write owner’s job is “forget ii-tonya / the app is github.com/apps/adaptive-trust-ci”, remaining work is **docs identity** (optional explicit App URL on the report) vs **historical packages** (leave as retraction history). Do not probe the hostname. Do not PATCH `/app/hook/config`.
