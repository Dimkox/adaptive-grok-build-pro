# Test review — close M0.2 webhook stage

**Verdict: fail**

Route: `test_reviewer` (read-only). Package: `engineering/changes/20260824-user-query-закрывай-ебана-блять-user-query-d80430`. `grok_verify --mode pr` reported PASS; 12 `M0InvariantTests` methods run green. That is execution evidence only. Characterization of this slice is not adequate.

## What this slice claims

Webhook + GitHub-delivered Check Run on SHA `9d56734` / Check Run `97524725228` is done. Full M0.2 is not: offline attestation, policy/holdout retitle, human Ed25519 requeue, source-mutation fail-closed, `main` protect remain open.

## Automated coverage that exists

| Check | Result | Adequacy |
| --- | --- | --- |
| `test_m0_spec_and_plan_exist` | PASS | Does not lock webhook-done vs remainder-open. |
| `test_activation_report_operator_safe` | PASS | `assertTrue("no public HTTPS" in plan or "not done" in plan)` is an OR. Live plan has **not done** for remaining M0.2, so the branch still passes even though public Funnel HTTPS exists. It does not fail if docs still say “no public HTTPS webhook” (spec still does). |
| `test_operator_docs_do_not_present_chatgpt_webhook_as_live` | PASS | Correct negative: no `ii-tonya`. |
| `test_operator_docs_name_funnel_app_webhook_url` | PASS | Still requires `https://claw.taild9f611.ts.net/webhooks/github` in **plan, report, decisions**. That matches live App webhook intake for this slice, not a leftover Funnel-only proof. Tests do not assert the URL is described as GitHub-delivered 200 vs unsigned 401 characterization. |
| `test_decisions_name_github_app_as_the_application` | PASS | Unrelated to M0.2 remainder. |
| Other M0 invariants (API/worker/compose/holdout/claw host) | PASS | Regression, not this stage. |

Package `test-plan.md` is empty (no P0 rows). No new test was added for: webhook checkbox `[x]`, Check Run id `97524725228`, “not M0.2 complete”, unchecked remaining M0.2 items, spec line still claiming “no public HTTPS webhook”.

## Characterization gaps (why fail)

1. **Funnel URL still required in plan/report/decisions** — acceptable as the live inbound URL, but the suite never distinguishes “Funnel path exists” from “GitHub App delivery 200”. A docs-only Funnel leftover would still pass.
2. **Plan still has “not done” for remaining M0.2** — intended, but the only automated lock is a substring `"not done"` anywhere in the plan (or the obsolete `"no public HTTPS"`). That does not pin attestation / Ed25519 / mutation / retitle / `Do not protect main` as open, nor webhook/Check Run as closed.
3. **Spec drift untested:** `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` still says M0.2 incomplete with **no public HTTPS webhook**, contradicting the plan’s `[x]` Funnel+GitHub 200 line. Invariants do not fail this.
4. **No characterization of Check Run `97524725228` / SHA `9d56734` / `action_required`** in tests (only prose in report/decisions).
5. **Change-package test plan and tasks remain unchecked stubs**; they are not verification.

## What would make this pass

- Assert webhook + GitHub Check Run lines are marked done without claiming M0.2 complete.
- Assert remaining M0.2 checkboxes (attestation, retitle, Ed25519, mutation, main) stay unchecked.
- Drop or replace the `"no public HTTPS" or "not done"` OR; fail if spec still denies public HTTPS while plan records GitHub 200.
- Keep Funnel URL as the named live App webhook URL (that assertion can stay).
- Fill package `test-plan.md` P0 rows to match the above.

## Verification evidence (execution)

- Local: `python3 scripts/grok_verify.py --mode pr` PASS (caller).
- `python3 -m unittest` M0 suite: 12 tests OK (caller).
- No new failing test was written before the doc change; green run does not prove the closed-stage contract.

**fail**
