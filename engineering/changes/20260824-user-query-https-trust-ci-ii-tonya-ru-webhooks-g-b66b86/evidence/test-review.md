# Test review — retract ChatGPT webhook URL

**Verdict: PASS**

Route `b66b867ba5ab`. Change `20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86`. Read-only; no product edits, no HTTP probe of `https://trust-ci.ii-tonya.ru/webhooks/github`.

## Characterization

`trust-ci/tests/test_m0_invariants.py` `test_operator_docs_do_not_present_chatgpt_webhook_as_live` scans the five operator docs (SPEC, PLAN, REPORT, README, DECISIONS) for both:

- `CHATGPT_WEBHOOK_URL` = `https://trust-ci.ii-tonya.ru/webhooks/github`
- `CHATGPT_WEBHOOK_HOST` = `trust-ci.ii-tonya.ru`

That matches the architect requirement: a URL-only `assertNotIn` would have been green before retraction because the five files never held the full path; the live leak was the hostname in `decisions.md`. Scanning both strings is the right red-to-green contract.

The test is a **string scan of tracked files**, not a live HTTP GET/POST. Constants live in the test module so the forbidden strings may appear there without failing. HMAC tests (`test_webhooks_github.py` / `test_api.py`) were not rewritten — correct; this slice does not change FastAPI intake.

## Coverage vs test-plan

| ID | Case | Evidence |
| --- | --- | --- |
| P0 | Operator docs do not present ChatGPT URL/host as live | Test exists; `decisions.md` now uses “voided hostname” / Apache leftover without naming `trust-ci.ii-tonya.ru`. SPEC/PLAN/README/REPORT remain placeholder or loopback. |
| P0 | Existing M0 invariants stay green | Implementation: `python3 -m unittest trust-ci.tests.test_m0_invariants` → **9 tests OK**. |
| P0 | HMAC contract unchanged | No edits to webhook/API tests; `grok_verify --mode pr` reported PASS on the atomic batch. |
| P1 | No live probe | Characterization is file `read_text` + `assertNotIn` only. |

Atomic batch (test + `decisions.md` retraction) is the only way to land a red-first invariant without a failing CI snapshot; pre-change `decisions.md` would fail the new test. That is documented and accepted.

## Intentional gaps (not fail)

- `mistakes.md` and sibling change briefs (`cec0c7`, `010964`) still name the URL. The invariant **must not** scan those paths, or the root-cause log and historical evidence would fail. Design, not a hole in P0.
- No unit test of host Apache leftovers (user: `не трогаем`).
- No GitHub App hook-config test (PEM/JWT forbidden).
- M0.2 public webhook remains **not done**; loopback HMAC is still the proven path.

## Residual test risk

If a later author puts the hostname back into one of the five operator docs, this test fails. If they put it only in `mistakes.md` or `engineering/changes/**`, it will not. That is the intended scope.

**PASS** — characterization is adequate for the retraction; HMAC suite untouched; no required live probe.
