# repo_explorer analysis

Route: `cec0c7622133`. Change: `20260824-configure-github-app-webhook-pull-request-https-cec0c7`.
Write owner: none. Skills loaded: adaptive-delivery (analysis only).

No PEM, `api.env`, or webhook secret values were read.

## 1. Repository webhooks

Command: `gh api repos/Dimkox/adaptive-grok-build-pro/hooks --jq 'length'`

- Result: **`0`** (empty list).
- Exit: `0`.
- No hook `config.secret` or other secret fields were printed.

A separate repository webhook is not present. App-level webhook is the intended path (cannot be listed via this repo hooks API).

## 2. User-token GitHub App APIs (HTTP status only)

Intended commands: `gh api /app` and `gh api /app/hook/config` with the existing user `gh` token. No App JWT was created.

- Control-plane **blocked** `gh api /app` (and the same class of `/app/hook/config`) as **direct external write** requiring a delegated grant for resource `github-api`.
- **HTTP status: not obtained** (blocked before the request). Do not infer 401/403/200.

Repo-scoped `GET .../hooks` was allowed; authenticated GitHub App owner APIs were not.

## 3. Public TLS and unsigned webhook POST

Environment: `NO_PROXY=*`. Target host: `trust-ci.ii-tonya.ru`. Python `urllib` + default vs unverified SSL context.

| Probe | TLS verify | Result |
| --- | --- | --- |
| GET `https://trust-ci.ii-tonya.ru/health/ready` | on | **SSL error**: `URLError` / `SSLCertVerificationError` (`CERTIFICATE_VERIFY_FAILED`; hostname/cert flags). Not an HTTP status. |
| GET same | off | **HTTP 200** |
| POST unsigned `https://trust-ci.ii-tonya.ru/webhooks/github` (body `{}`, no `X-Hub-Signature`) | on | **SSL error** (same class as ready) |
| POST unsigned same | off | **HTTP 405** (not 401) |

Interpretation:

- Public HTTPS is reachable if certificate verification is skipped; **public CA verification fails** from this environment (cert/hostname mismatch or untrusted chain — not diagnosed further).
- With verify off, unsigned POST is **405**, not **401**. That implies the listener answers on that path but does **not** treat missing signature as 401 in this probe (method/path policy or signature check not reached as 401). GitHub App “SSL verification Enabled” will still fail deliveries until the public cert is trusted by GitHub’s CAs.
- Desired GitHub App webhook URL remains `https://trust-ci.ii-tonya.ru/webhooks/github` (from the change brief). This explorer did not set App webhook config.

## 4. `TRUST_CI_PUBLIC_BASE_URL`

Grep key only in `trust-ci/env/common.env`:

- Key **exists**.
- Value (URL, not a secret): `http://127.0.0.1:18080`

That is **loopback HTTP**, not `https://trust-ci.ii-tonya.ru`. Public GitHub cannot deliver to `127.0.0.1`. App webhook URL must be the public HTTPS origin independently of this local compose URL.

`TRUST_CI_WEBHOOK_SECRET` was **not** grepped or opened (`api.env` not read).

## Impact for the change

- Empty repo hooks: consistent with “do not add a repo webhook; configure the GitHub App webhook.”
- App webhook URL/secret/events cannot be confirmed via `/app/hook/config` without a `github-api` grant (or GitHub App JWT + permissions, which this agent must not invent).
- Public TLS: **verify-on fails**; GitHub’s SSL-enabled deliveries will fail until the certificate presented by `trust-ci.ii-tonya.ru` chains to a public CA matching the hostname.
- Unsigned POST **405** vs **401**: endpoint exists behind TLS-off; signature/auth behavior not proven as 401.
- Local `TRUST_CI_PUBLIC_BASE_URL` is not the public webhook URL.

## Residual

- App hook active flag, subscribed events (`pull_request`), and secret equality to `TRUST_CI_WEBHOOK_SECRET` are **unverified**.
- Exact TLS failure (name mismatch vs untrusted issuer) not expanded (no cert dump).
