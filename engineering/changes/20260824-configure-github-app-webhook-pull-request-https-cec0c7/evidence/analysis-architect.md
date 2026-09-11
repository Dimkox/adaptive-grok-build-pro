# Architect ruling — GitHub App webhook without App PEM

Route: `cec0c7622133`. Change: `20260824-configure-github-app-webhook-pull-request-https-cec0c7`. Write owner: none. This agent is read-only except this report.

Did not read `.env`, `trust-ci/env/api.env`, `trust-ci/runtime/github-app-private-key.pem`, webhook secret values, JWTs, or installation tokens. Did not mint a JWT. Did not PATCH `/app/hook/config`. Did not POST `/repos/{owner}/{repo}/hooks`. Did not push, merge, or deploy.

Sources: GitHub REST `PATCH /app/hook/config` contract, GitHub App webhook UI docs, `trust-ci/src/adaptive_trust_ci/{api,webhooks,github_app,settings}.py`, `trust-ci/tests/test_webhooks_github.py`, sibling `analysis-repo_explorer.md` / `analysis-docs_researcher.md`, live public TLS probe of `trust-ci.ii-tonya.ru` (certificate SANs only).

## Ruling

**The agent cannot configure the GitHub App webhook via API.** `PATCH /app/hook/config` requires a GitHub App JWT signed with the App RSA private key. `AGENTS.md` forbids reading that PEM. A user token cannot call `/app/hook/config`. An installation token (what the worker mints) also cannot. Do not mint a JWT. Do not create a repository webhook as a substitute. The operator sets URL, secret, SSL verification, and `pull_request` on the App registration page: `https://github.com/settings/apps/adaptive-trust-ci` (or the org-owned equivalent). Live TLS for `trust-ci.ii-tonya.ru` currently presents a certificate for `ii-tonya.ru` / `www.ii-tonya.ru`; GitHub “SSL verification: Enabled” will fail deliveries until that hostname is on the cert.

---

## 1. Repository webhook vs App webhook

The user is correct. App `adaptive-trust-ci` is already registered and installed (activation report: App ID `4694114`, Installation ID `156003193`, slug `adaptive-trust-ci`). GitHub Apps have **one** webhook on the App registration. Deliveries for every installation, including this repository, go to that URL. A separate repository hook is the wrong channel.

| Channel | Config surface | Auth to mutate | Status this slice |
| --- | --- | --- | --- |
| **GitHub App webhook** | App registration: Active, Webhook URL, secret, SSL, Subscribe to events | App JWT **or** App owner UI | Intended. Current values unverified (JWT forbidden; user token cannot GET `/app/hook/config`) |
| Repository webhook | `POST /repos/{owner}/{repo}/hooks` or repo Settings → Webhooks | User admin / PAT | **Do not create.** `GET repos/Dimkox/adaptive-grok-build-pro/hooks` length **0** |

Product intake is channel-agnostic: `POST /webhooks/github` verifies HMAC then parses `X-GitHub-Event: pull_request`. App deliveries also carry `installation` on the payload; Trust CI ignores that field and keys jobs on `repository.full_name` + PR + SHAs.

**Do not create repo hooks** even though a user admin token *can* (`POST /repos/.../hooks`). That would:

- duplicate the intended App channel once the App webhook is Active;
- leave M0.2 docs saying “repository webhook” as if that were still the design;
- still fail GitHub SSL verification against the current public cert.

Tracked `trust-ci/` has **no** client for `/app/hook/*` or `/repos/.../hooks`. Worker `GitHubAppAuth` only `POST`s `/app/installations/{id}/access_tokens`. Webhook registration is operator configuration, not product code.

README/spec/plan still say “register repository webhook”. After a **successful GitHub delivery** (not merely UI Active), reword those lines to **App webhook**. Keep M0.2 incomplete until GitHub actually POSTs a signed `pull_request` to `/webhooks/github`. UI Active ≠ delivery. Loopback HMAC Check Runs already exist; they are not this slice.

---

## 2. Auth: App JWT is the API path — forbidden for the agent

GitHub contract (`docs.github.com/en/rest/apps/webhooks`):

```text
GET    /app/hook/config
PATCH  /app/hook/config
GET    /app/hook/deliveries
GET    /app/hook/deliveries/{id}
POST   /app/hook/deliveries/{id}/attempts
```

Each page states: **You must use a JWT to access this endpoint.**

JWT mint (`docs.github.com` “Generating a JWT for a GitHub App”): RS256, claims `iat`/`exp`/`iss` (App ID or client ID), signed with the App private key. That is exactly `generate_app_jwt` in `trust-ci/src/adaptive_trust_ci/github_app.py`, which `read_bytes()`s `private_key_path`.

| Credential | Can PATCH `/app/hook/config`? | Agent may use? |
| --- | --- | --- |
| App JWT from `github-app-private-key.pem` | Yes (the documented path) | **No.** Reading the PEM is forbidden. Do not mint JWT. |
| User PAT / `gh` user token | **No.** Endpoint is App-auth only. | Irrelevant even if a `github-api` grant existed. |
| Installation token (worker) | **No.** Installation tokens are repo-scoped (`checks`/`contents`/`pull_requests`), not App-admin. | Worker-only; API must not hold it (holdout). |
| Fine-grained / classic PAT | **No** for `/app/hook/config`. | Must not be used to create a **repo** hook instead. |

Repo explorer’s `gh api /app` and `gh api /app/hook/config` were blocked as `github-api` writes. Even if unblocked, they would not succeed with a user token. Do not request a grant to work around the PEM rule.

**Operator path (approved):**

1. Open `https://github.com/settings/apps/adaptive-trust-ci` (personal-account owner) **or** `https://github.com/organizations/<org>/settings/apps/adaptive-trust-ci` if the App is org-owned.
2. Developer settings → GitHub Apps → Edit `adaptive-trust-ci`.
3. Under **Webhook**: Active, URL, secret, SSL verification.
4. Save changes.
5. Sidebar **Permissions & events** → **Subscribe to events** → **Pull request** → Save.

`PATCH /app/hook/config` body is only `url`, `content_type`, `secret`, `insecure_ssl`. It does **not** subscribe events. Events are a separate App-registration field (UI Permissions & events, or App manifest `default_events`). The operator UI covers both.

---

## 3. Events: `pull_request` required; drafts enqueue; `ping` is default

Required subscription: **Pull request** (`pull_request`). That is the only event Trust CI parses into a job.

`parse_pull_request_event` (`webhooks.py`):

- Non-`pull_request` → `None` → HTTP **200** `{accepted: false, reason: "ignored-event"}` after HMAC.
- Actions `opened` / `synchronize` / `reopened` / `ready_for_review` enqueue.
- `closed` cancels active jobs for that repo/PR.
- Other actions return `None` (ignored).
- **`draft` is not a filter.** `test_draft_pull_request_is_enqueued` already asserts draft `opened` becomes a `JobRequest`. Disposable PR #5 is a draft; that contract must stay.

`ping` is sent when a webhook is created or its URL is saved. Availability includes `app`. Trust CI does not special-case `ping`; a signed ping is ignored-event **200**. That is a successful GitHub delivery. Do not subscribe extra events to “catch ping”; GitHub sends it by default.

Do not subscribe `push`, `check_run`, or “all events”. HMAC still runs first; extra events only add ignored 200s.

---

## 4. SSL verification Enabled requires a cert for `trust-ci.ii-tonya.ru`

Intended App fields (operator UI; map to `PATCH /app/hook/config` where applicable):

| UI | API field | Required value |
| --- | --- | --- |
| Webhooks: Active | (App registration, not `/app/hook/config`) | Active |
| Webhook URL | `url` | `https://trust-ci.ii-tonya.ru/webhooks/github` |
| Webhook secret | `secret` | same bytes as API `TRUST_CI_WEBHOOK_SECRET` (not printed here) |
| SSL verification | `insecure_ssl` | **Enabled** / `"0"` |
| Content type | `content_type` | `json` (`application/json`) |
| Subscribe to events | not this endpoint | **Pull request** |

GitHub: `insecure_ssl` `0` = verify the host cert; `1` = skip. User asked Enabled. Do **not** set `insecure_ssl=1` to paper over the current cert.

**Live TLS (this analysis, public cert only):**

| Probe | Result |
| --- | --- |
| DNS `trust-ci.ii-tonya.ru` | `157.22.187.237` A only |
| Verify-on HTTPS | `SSLCertVerificationError` **62 Hostname mismatch**, certificate is not valid for `trust-ci.ii-tonya.ru` |
| Presented cert | Let’s Encrypt; **CN=`ii-tonya.ru`**; SAN=`DNS:ii-tonya.ru`, `DNS:www.ii-tonya.ru` |
| Not on cert | `trust-ci.ii-tonya.ru` |

GitHub deliveries with SSL verification Enabled will record an **SSL error** and will not reach FastAPI until a certificate (and vhost) is valid for `trust-ci.ii-tonya.ru`. `TRUST_CI_PUBLIC_BASE_URL` in gitignored `common.env` is still loopback `http://127.0.0.1:18080`; that is the compose bind, not the App webhook URL. Public GitHub cannot POST to `127.0.0.1`.

Sibling explorer: verify-off unsigned `POST /webhooks/github` returned **405**, not FastAPI’s **401** for missing `X-Hub-Signature-256`. That implies the public edge is not yet the Trust CI API (parent-site vhost). Residual after cert fix: Apache/proxy must `ProxyPass` POST `/webhooks/github` to `127.0.0.1:18080`. This architect does not register the App hook against a host GitHub cannot TLS-verify.

---

## 5. Secret must match `TRUST_CI_WEBHOOK_SECRET`; agent must not print it

API `ApiSettings.webhook_secret` is `_required('TRUST_CI_WEBHOOK_SECRET')` from gitignored `trust-ci/env/api.env` (example placeholder only in `api.env.example`). `verify_webhook_signature` HMAC-SHA256s the **raw body** and compares `X-Hub-Signature-256`. Mismatch → **401**. Worker must not receive this secret (role split / holdout).

**Operator paste in the GitHub App UI is the correct way to set the App secret.** The agent must not `cat`/`echo`/`grep` `api.env`, must not print the value, and must not put it in this change package, activation report, or chat.

If the operator cannot recall the value, they read it on the CI host themselves and paste it into the App form. Do not ask the agent to retrieve it. Do not rotate the secret in this slice unless the operator chooses to; if rotated, update **both** `api.env` (API restart) and the App UI in the same window or GitHub deliveries 401.

---

## 6. Forbidden and allowed actions

**Forbidden**

- Read `trust-ci/runtime/github-app-private-key.pem` or any PEM/`.env`.
- Mint or print a GitHub App JWT (`generate_app_jwt`, `jwt.encode`, `gh auth` with PEM).
- `GET`/`PATCH /app/hook/config` or `/app/hook/deliveries*` from this agent.
- `POST /repos/Dimkox/adaptive-grok-build-pro/hooks` (or org hooks) as a substitute.
- Set `insecure_ssl=1` / SSL verification Disabled.
- Print, log, or commit `TRUST_CI_WEBHOOK_SECRET`.
- Claim M0.2 complete from UI Active or from loopback HMAC.
- Protect `main` in this slice.

**Allowed (operator, not agent)**

- Edit `https://github.com/settings/apps/adaptive-trust-ci` (or org equivalent): Active, URL `https://trust-ci.ii-tonya.ru/webhooks/github`, secret pasted from host `TRUST_CI_WEBHOOK_SECRET`, SSL Enabled, event **Pull request**.
- After TLS hostname is valid: confirm GitHub delivery of `ping` (200 ignored-event) then a real `pull_request` (200 `accepted: true`, `job_id`).

**Blocked until TLS matches the webhook host**

App webhook save will trigger `ping`. With the current parent-domain cert, GitHub’s delivery log will show SSL failure. Fix cert/vhost first (or in parallel, accepting failed pings until the name matches). Do not lower SSL verification.

---

## Contract freeze (intake; registration is GitHub-side)

Unchanged product contract:

```text
POST /webhooks/github
Content-Type: application/json
X-GitHub-Event: pull_request | ping | (other → ignored-event)
X-Hub-Signature-256: sha256=<hex>
```

Success for `pull_request` enqueue: 200 `{accepted: true, created, job_id, status, status_publisher: worker-github-app}`. Drafts enqueue. Idempotent on `(repository, pr, head_sha, policy_digest)`. This change does **not** modify that code.

---

## Residual

- App hook Active / URL / events / secret equality: **unverified** (JWT forbidden).
- Public POST 405 vs API 401: edge is not Trust CI yet.
- `scope_and_design_approval` is a named human gate; this report is the design, not execution.
- Write owner is null: no implementer may PATCH GitHub or edit deployed TLS from this route.

Human gate: operator (or a later granted host-TLS slice) owns cert SAN `trust-ci.ii-tonya.ru` and the App settings form. Agents do not.
