# test_reviewer — App webhook docs characterization (route `2cd446440734`)

**Verdict: PASS**

Change: operator docs + characterization only. No product runtime tests required. Local evidence cited by the route: `grok_verify --mode pr` PASS; `python3 -m unittest trust-ci.tests.test_m0_invariants` 12 OK. This review did not re-run those commands.

## P0 cases vs tests

| Plan ID | Intent | Evidence | Adequacy |
| --- | --- | --- | --- |
| P0 | Operator docs name Funnel App webhook URL | `M0InvariantTests.test_operator_docs_name_funnel_app_webhook_url` | **Adequate.** Asserts `https://claw.taild9f611.ts.net/webhooks/github` in plan, activation report, and `decisions.md`. Tree matches: plan M0.2 line, report inbound URL cell, decisions 2026-08-24 App-webhook entry. |
| P0 | M0.2 still not done | `test_activation_report_operator_safe`: `local HMAC` in plan; `"no public HTTPS" in plan or "not done" in plan` | **Adequate for this slice.** Plan webhook line is still `[ ]` with **not done** and “no GitHub delivery yet”. Partial Check Run line still says **local HMAC** / Not M0.2 complete. Backup drill `[x]` does not satisfy the webhook checkbox. |
| P1 | Repo hooks stay empty | Live `gh api` list only | **Correctly not a unit test.** Characterization cannot prove GitHub `GET …/hooks == []`. |

## Characterization coverage

`test_operator_docs_name_funnel_app_webhook_url` is substring presence, not HTTP. That is the right level: this slice does not register the hook and must not treat unsigned Funnel 401 as GitHub POST.

M0.2 incompleteness is still gated by existing wording (`not done` **or** `no public HTTPS`, plus `local HMAC`). Checking the webhook box to `[x]` or dropping both phrases would fail the suite. Ticking only the backup line would not.

Sibling invariants still hold ChatGPT hostname absence (`ii-tonya`), App slug in decisions, no `.github/workflows`, API without App auth, compose loopback.

## Gaps (non-blocking)

- Funnel URL is not required in SPEC/README (only PLAN/REPORT/DECISIONS). Acceptable: those three are the operator-facing records for this slice.
- The test does not pin the webhook checkbox itself to `[ ]`; a later `[x]` that still contains “not done” elsewhere could pass. Current plan text is honest.
- No test asserts “Recent Deliveries” or signed GitHub `pull_request`. By design: that remains live M0.2, not this characterization.

## What would fail this review

Marking M0.2 complete, dropping Funnel URL from plan/report/decisions, claiming a repository webhook, or treating loopback HMAC Check Runs as GitHub delivery.

**PASS** — characterization matches the test plan; M0.2 stays not done.
