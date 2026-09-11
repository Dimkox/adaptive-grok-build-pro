# Test review — 20260824-user-query-че-бля-делай-нахуй-user-query-c36377

**Agent:** test_reviewer (read-only)  
**Route:** `8a3cd76134f5` / `allowed_agents` includes this agent  
**Verdict:** **PASS**

## Scope reviewed

Live slice: worker App-JWT `PATCH /app/hook/config` to Funnel URL; ping redelivery 200; `GET /app` `events: []`. Operator docs updated; M0.2 checkbox stays `[ ]`. Characterization remains `trust-ci/tests/test_m0_invariants.py` (12 tests). Product HMAC adapter / compose / FastAPI were not the write surface.

## M0 invariants vs this tree

| Invariant | Test | Tree |
| --- | --- | --- |
| Funnel URL named | `test_operator_docs_name_funnel_app_webhook_url` asserts `https://claw.taild9f611.ts.net/webhooks/github` in PLAN, REPORT, DECISIONS | Plan M0.2 webhook line, activation-report inbound cell, `decisions.md` App-webhook entry |
| M0.2 not complete / local HMAC | `test_activation_report_operator_safe` requires `"local HMAC"` in PLAN and (`"no public HTTPS"` **or** `"not done"`) | Plan: `- [ ]` Register … **not done**; Check Run via **local HMAC**; “Not M0.2 complete.” Report: ping 200, not a pull_request delivery |
| Void ChatGPT host | `test_operator_docs_do_not_present_chatgpt_webhook_as_live` | Unchanged |
| No PEM in spec/plan/report | `test_activation_report_operator_safe` / `PEM_MARKERS` | Package evidence redacts secrets |
| Loopback API publish | `test_compose_publishes_loopback_not_all_interfaces` | Unchanged; `TRUST_CI_PUBLIC_BASE_URL` still `http://127.0.0.1:18080` |
| API vs worker key split | `test_api_cannot_hold_github_app_or_client`, `test_worker_uses_github_app_auth` | Unchanged |

A regression that dropped the Funnel URL, claimed M0.2 done by deleting “not done”, or rewrote the Check Run as GitHub-origin instead of **local HMAC** would fail these 12 tests.

## Characterization vs live proof

Unittest is **docs/source invariant**, not GitHub HTTP. That is correct: CI must not mint JWT, read PEM, or POST signed Funnel traffic.

Live proof (out of band, recorded in `evidence/app-hook-patch.md`): PATCH 200, Funnel URL, SSL on, secret_set, ping redelivery 200, `events: []`. Tests do **not** encode ping id or `events: []`; residual gap is acceptable because claiming those in git would freeze live GitHub state and still would not prove HMAC on `pull_request`.

## Adequacy of the 12 tests

| # | Test | Adequacy |
| --- | --- | --- |
| 1 | `test_m0_spec_and_plan_exist` | Base freeze SHA / check-name presence |
| 2 | `test_activation_report_operator_safe` | **P0** not-done / local HMAC / no PEM |
| 3 | `test_operator_docs_do_not_present_chatgpt_webhook_as_live` | Forbidden host |
| 4 | `test_decisions_name_github_app_as_the_application` | App identity |
| 5 | `test_operator_docs_name_funnel_app_webhook_url` | **P0** Funnel URL |
| 6 | `test_mistakes_do_not_call_nginx_the_application` | Historical wording |
| 7 | `test_no_github_actions_workflows_tree` | Policy |
| 8–9 | API/worker key split | Trust boundary |
| 10 | compose loopback | Host publish |
| 11 | claw not laptop | Host naming |
| 12 | holdout example forbids Actions | Holdout contract |

Change-package `test-plan.md` is still empty placeholders. Coverage lives in `test_m0_invariants.py`, not the package stub.

## Gaps (do not fail this slice)

- No assert that M0.2 checkbox is literally `- [ ]` (only substring `not done`).
- No assert `GET /app` `events: []` or `GET /repos/.../hooks` `[]`.
- No unsigned Funnel 401 in this unittest (prior slice `813a02`).
- `test-plan.md` in this package was not filled.

These do not undermine the required Funnel + not-done/local-HMAC locks.

## Verification evidence (claimed, not re-executed here)

- `python3 -m unittest` on `trust-ci/tests/test_m0_invariants.py`: **12 OK** (implementer / task statement).
- `python3 scripts/grok_verify.py --mode pr`: **PASS** (task statement).

This review did not re-run those commands (read-only; avoid extra tree writes). If the tree moved after those runs, receipts are stale.

## Forbidden claims this review would **fail**

- Marking M0.2 complete.
- Treating ping 200 or loopback HMAC Check Runs as `pull_request` GitHub delivery.
- Dropping Funnel URL from PLAN/REPORT/DECISIONS.
- Adding a repository webhook as the intake.

## Result

**PASS.** M0 invariants still require the Funnel webhook URL and PLAN language of **not done** / **local HMAC**. Twelve characterization tests remain the right gate for this docs+live-config slice.
