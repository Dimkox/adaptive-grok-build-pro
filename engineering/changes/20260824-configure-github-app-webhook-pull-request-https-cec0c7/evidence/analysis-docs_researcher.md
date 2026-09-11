# Docs research: GitHub App webhook vs repo hook (route cec0c7622133)

Read-only recovery from repository docs, ADRs, contracts, and tests. No APIs invented. No secrets copied.

## Sources

- `trust-ci/README.md` — GitHub configuration still says **Create a repository webhook** with `Payload URL: https://ci.example.com/webhooks/github`, content type JSON, secret named as env `TRUST_CI_WEBHOOK_SECRET` (value never in tree), events **Pull requests**. Rollout: deploy → install webhook → disposable PR → confirm App-owned Check Run → attestation → then branch protection.
- `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` — binding rollout step 2: **Register repository webhook** `POST https://<ci>/webhooks/github` (API-only HMAC, `pull_request`; drafts enqueue). GitHub App section: never commit PEM, JWT, installation token, **webhook secret**, or admin token. Host: `TRUST_CI_PUBLIC_BASE_URL` must still be HTTPS; published mapping is loopback `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`.
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` — M0.2 checkbox: **Register repo webhook** `POST https://<ci>/webhooks/github` — **not done** (no public HTTPS). Partial Check Run on PR #5 via **local HMAC**, not M0.2 complete. Historical STOP: no webhook until later slices; those remain host-local.
- `engineering/runbooks/trust-ci-activation-report.md` — `TRUST_CI_PUBLIC_BASE_URL` = `http://127.0.0.1:18080`. First App-owned Check Run from **loopback HMAC POST**, **not a GitHub-registered webhook**. App slug `adaptive-trust-ci`, App ID `4694114`, Installation ID `156003193`. Local HMAC / public webhook still not a registered GitHub hook.
- `trust-ci/tests/test_m0_invariants.py` — `test_activation_report_operator_safe` requires plan text to contain **`local HMAC`** and (`**no public HTTPS**` **or** `**not done**`). PEM markers forbidden in spec/plan/report.

Supporting: `decisions.md` (leave `TRUST_CI_PUBLIC_BASE_URL` on loopback until HTTPS exists; public webhook registration out of scope for that slice). `trust-ci/src/adaptive_trust_ci/settings.py` — `TRUST_CI_PUBLIC_BASE_URL` must be HTTPS outside localhost. `trust-ci/src/adaptive_trust_ci/api.py` — `POST /webhooks/github` HMAC then `parse_pull_request_event`. Contract path is App-or-repo agnostic once GitHub posts to that URL.

## Findings for this change

### 1. Reword “Register repo webhook”; keep “not done” until GitHub delivers

User intent (change brief): App `adaptive-trust-ci` already installed; **no separate repository webhook**. Configure **GitHub App** webhooks: Active, URL `https://trust-ci.ii-tonya.ru/webhooks/github`, same secret as `TRUST_CI_WEBHOOK_SECRET` in host env (not in git), SSL verification enabled, subscribe **Pull request**.

Docs today still say **repository webhook** (README, spec step 2, plan M0.2 checkbox). After the App webhook is marked Active with `pull_request`, that checkbox should be **reworded to App webhook**, not a repo hook. Status must stay **not done** until GitHub **actually delivers** a signed `pull_request` payload to `/webhooks/github` (activation report still records only loopback HMAC). UI “Active” ≠ delivery.

### 2. Do not commit webhook secret

Spec and activation report: never paste webhook secret. README names the **env var**, not the value. `api.env` is gitignored operator material. Docs and change evidence must keep that rule.

### 3. Activation report `TRUST_CI_PUBLIC_BASE_URL`

Current recorded value is `http://127.0.0.1:18080`. It **only becomes** `https://trust-ci.ii-tonya.ru` after TLS hostname **verifies** (proxy + certificate for that name). Spec still requires HTTPS for the public URL. Do not backfill the public HTTPS URL from intent alone.

### 4. `test_m0_invariants` HMAC phrases

The test **must keep** asserting **`local HMAC`** and **`no public HTTPS` / `not done`** until the plan is updated **carefully** (App-webhook wording plus an honest delivery state). If the plan is marked complete without GitHub delivery, or drops those phrases, `python3 -m unittest trust-ci.tests.test_m0_invariants` fails. Changing the test to match an unverified public URL would hide the M0.2 gap.

## Gaps (docs vs operator intent)

| Doc | Current fact | Intent |
| --- | --- | --- |
| README GitHub configuration | “Create a **repository** webhook” | App webhook on `adaptive-trust-ci` |
| Spec rollout #2 | Register **repository** webhook | Same path, App subscription |
| Plan M0.2 | Repo webhook **not done** (no public HTTPS) | Keep incomplete until delivery; rename to App webhook |
| Activation report | Loopback HTTP + local HMAC | Public HTTPS URL only after TLS verify |

## Non-goals recovered from docs

No branch-protect before live App-owned check. No GitHub Actions. No PEM/JWT/admin token in tree. API has HMAC only; worker has App auth. Installation ID present does not complete M0.2.
