# code_reviewer — App hook URL via worker JWT (POST-implementation)

Route `allowed_agents` includes `code_reviewer`. Change: `20260824-user-query-че-бля-делай-нахуй-user-query-c36377`. Read-only. No `.env`/PEM. No push/merge/deploy.

**Verdict: pass**

Slice is operational GitHub App `hook/config` plus operator docs. M0.2 is not complete. FastAPI intake is unchanged.

## Contracts vs evidence

| Claim | Result |
| --- | --- |
| App webhook URL via worker JWT; PEM not in agent stdout | **pass** — `evidence/app-hook-patch.md`, `evidence/implementation.md`, `evidence/patch_app_hook_inner.py` mint JWT inside the worker from `TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH`; reports only status/url/content_type/insecure_ssl/secret_set |
| PATCH `/app/hook/config` 200 | **pass** — Funnel `https://claw.taild9f611.ts.net/webhooks/github`, `content_type=json`, `insecure_ssl=0`, `secret_set=true` |
| GitHub ping 200 | **pass** — first ping 502; redelivery `3838817352380579840` 200 OK (~0.8s) |
| `events: []` residual | **pass** — GET `/app` still `events: []`; PATCH `/app` events 404; no REST subscribe to `pull_request`; no repository webhook |
| Plan checkbox still `[ ]` | **pass** — `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` M0.2 register webhook remains `[ ]` with “App hook URL set; GitHub ping 200; `pull_request` event still unsubscribed; no pull_request delivery” |
| FastAPI unchanged | **pass** — `git diff` empty for `trust-ci/src/adaptive_trust_ci/api.py` and `webhooks.py` |

Activation report inbound URL cell matches Funnel + ping 200 + not a pull_request delivery. `decisions.md` states M0.2 stays incomplete until a `pull_request` delivery exists.

## Product delta (this working tree)

- Docs/tests only: plan wording, activation-report webhook cell, `decisions.md`, `mistakes.md`, `trust-ci/tests/test_m0_invariants.py` Funnel URL asserts and ChatGPT hostname exclusion.
- No API/worker runtime Python change for HMAC or Check Runs.
- Change-package `change-spec.yaml` / `tasks.md` / `requirements.md` remain templates (`{{OBJECTIVE_STATEMENT}}`, all task boxes `[ ]`). Paperwork debt, not a false M0.2 claim.

## Residual (not fail)

- App event subscription cannot be written via REST; operator UI still required for `pull_request`.
- Live Check Runs remain local HMAC (`97390635614` / `97406973020`), not webhook-driven.
- `TRUST_CI_PUBLIC_BASE_URL` still loopback `http://127.0.0.1:18080`.
- Untracked `patch_app_hook_inner.py` is one-shot worker helper; do not treat it as shipped API.

Independent of the implementer. Not merge authority. External Trust CI check still required for any merge.
