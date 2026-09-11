# Code review — close M0.2 webhook stage (docs)

**Agent:** code_reviewer (read-only)  
**Change:** `engineering/changes/20260824-user-query-закрывай-ебана-блять-user-query-d80430`  
**Tree reviewed:** commit `873ab5034cc0813d7d7c42689afd7c89f7a654ac` (`docs: close M0.2 webhook stage on live GitHub delivery`) on `milestone/m0-live-trust-authority`  
**Verdict:** **PASS**

## Scope

Operator-doc + characterization-test slice. No product API/worker/compose behavior change. No PEM, JWT, webhook secret, human approval key, `branch-protect`, merge, or tag.

## Contracts vs diff

| Claim | Evidence in tree | Full M0.2? |
| --- | --- | --- |
| GitHub App `pull_request`/`synchronize` HTTP **200** | Plan M0.2 first box `[x]`; activation report inbound URL `https://claw.taild9f611.ts.net/webhooks/github`; `decisions.md` Funnel POST | Webhook **stage** only |
| Check Run `97524725228` on SHA `9d56734d9050fb3cb2543565084bcb83ded5c73b` App `4694114`, `external_id=0e147461-6de8-415f-b712-d06b2034c735`, `conclusion=action_required` (`needs_approval`) | Plan second box; activation-report identity cells updated from loopback `97390635614`/`1fc9420` | **Not** M0.2 complete (explicit) |
| Remaining M0.2 | Still `[ ]`: offline attestation, policy/holdout retitle, human Ed25519 same Check Run, source-mutation fail-closed, **Do not protect `main`** | Correctly **open** |
| M0.3 / protect `main` | Untouched `[ ]`; report `main` protected **false** | Correct |

`action_required` is publication + `needs_approval`, not a green policy-epoch pass. Brief, implementation note, plan, and decisions all refuse a full M0.2 claim.

## What is good

- Live identity is App webhook Funnel, not a repository webhook and not the voided ChatGPT hostname.
- Prior loopback Check Runs remain labeled **local HMAC**; GitHub-delivered id is distinct.
- `trust-ci/tests/test_m0_invariants.py` forbids `trust-ci.ii-tonya.ru` / `ii-tonya` in operator docs, requires Funnel URL on plan/report/decisions, and names `https://github.com/apps/adaptive-trust-ci`.
- Activation report still `N/A` for offline attestation (GET 404 / needs_approval).
- Diff does not mint keys, add `.github/workflows`, or protect `main`.

## Findings (non-blocking)

1. **Stale M0.1 checkbox** still reads “Public GitHub webhook still absent” as `[x]`. Historical for that slice; M0.2 now contradicts it. Does not claim M0.2 complete, but operators can misread the M0.1 line.
2. **Weak invariant** `test_activation_report_operator_safe` still accepts `"not done" in plan`, which is true because *remaining* items say **not done**, not because the webhook box is open.
3. Change-package `change-spec.yaml` / `architecture.md` / `tasks.md` remain templates; `state.json` still `draft`. Workflow paperwork only.

## Forbidden outcomes checked

- Full M0.2 claimed: **no**
- `main` protected: **no** (`false` / do-not-protect still open)
- Human approval keys / PEM: **not in diff**
- ChatGPT hostname as live webhook: **not in operator docs** (mistakes.md records the error only)

## Pass/fail

**PASS** for closing the **webhook stage** (GitHub `pull_request` 200 + Check Run `97524725228` `action_required` on `9d56734`) without claiming full M0.2.

Independent of implementer. Not merge authority. Remaining M0.2 (Ed25519 requeue, holdout/mutation, attestation, policy retitle, leave `main` unprotected) stays open.
