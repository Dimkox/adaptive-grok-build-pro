# Docs research: after App webhook PATCH/Save to Funnel URL

Read-only. No invented APIs. No secrets. Did not PATCH GitHub.

## Fact after operator Save (not M0.2 complete)

Hook URL is set to Funnel `https://claw.taild9f611.ts.net/webhooks/github` (SSL Enabled, `pull_request`, secret = host `TRUST_CI_WEBHOOK_SECRET` unpublished). Agent `PATCH /app/hook/config` remains 401 without App JWT; PEM unread. **Do not add a repository webhook.** M0.2 stays **not fully complete** until GitHub Recent Deliveries show a signed POST. Loopback HMAC Check Runs on PR #5 are not that proof. `TRUST_CI_PUBLIC_BASE_URL` **stays** `http://127.0.0.1:18080`.

## Docs to update (wording only; do not check M0.2 done)

| File | Change |
| --- | --- |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | M0.2 first item: **GitHub App** webhook (not repo). Keep `[ ]` / **not done** until delivery observed. Funnel URL already named; say hook **URL is set**, GitHub delivery still absent. Keep `local HMAC` / `not done` phrases for `test_m0_invariants`. M0.1 “public webhook still absent” → “App hook URL set; no GitHub delivery yet”. |
| `engineering/runbooks/trust-ci-activation-report.md` | Inbound URL row already Funnel. Keep `TRUST_CI_PUBLIC_BASE_URL` loopback. Intro: hook **configured on App**, **no GitHub delivery yet**; Check Runs still **loopback HMAC**. |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | Rollout step “Register **repository** webhook” → **App** webhook `POST …/webhooks/github`. M0.2 still incomplete until GitHub POSTs. Do not set public base URL to Funnel. |
| `decisions.md` | Already: Funnel URL + operator UI Save + M0.2 not done until deliveries. Append only if PATCH actually succeeded vs UI Save. |
| `trust-ci/README.md`, `QUICKSTART.md`, `GROK_BUILD_HANDOFF.md`, `DARK_FACTORY_ROADMAP.md` | Generic “repository webhook” → **GitHub App webhook** on `adaptive-trust-ci` (same path `/webhooks/github`). Not live-status docs; do not claim M0.2 complete. |

## Do not change

- `TRUST_CI_PUBLIC_BASE_URL` in report, compose, or settings examples (loopback until a named public HTTPS path is the **API** public base, not just Funnel inbound).
- Marking M0.2 boxes complete, `main` protection, or claiming GitHub delivery.
- Pasting webhook secret, PEM, JWT.

## Invariant test

`trust-ci/tests/test_m0_invariants.py` requires plan/report to keep **`local HMAC`** and **`not done`** (or no public HTTPS). Funnel URL in the report is already allowed; dropping those phrases fails the test.
