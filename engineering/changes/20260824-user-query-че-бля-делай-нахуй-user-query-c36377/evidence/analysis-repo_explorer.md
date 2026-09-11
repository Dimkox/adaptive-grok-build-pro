# repo_explorer — worker App ID env names + Tailscale funnel

Route: `c36377792135`. Change: `20260824-user-query-че-бля-делай-нахуй-user-query-c36377`.

Read-only. Did not read PEM, did not `printenv` secrets, did not dump `worker.env`.

## Worker GitHub App environment variable names

Authoritative sources: `trust-ci/env/worker.env.example`, `WorkerSettings` in `trust-ci/src/adaptive_trust_ci/settings.py`, CLI fallback in `trust-ci/src/adaptive_trust_ci/cli.py`.

| Role | Env var name (not value) |
| --- | --- |
| GitHub App ID | **`TRUST_CI_GITHUB_APP_ID`** |
| GitHub App installation ID | `TRUST_CI_GITHUB_INSTALLATION_ID` |
| GitHub App RSA private key path | `TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH` |

`WorkerSettings` loads App ID via `_int('TRUST_CI_GITHUB_APP_ID')`. CLI `app_id = args.app_id or _required_int_env('TRUST_CI_GITHUB_APP_ID')`. API must not receive App ID, installation ID, or the PEM.

Example file still uses placeholder `REPLACE_WITH_APP_ID` (not a live secret). PEM path in the example is `/run/secrets/github-app-private-key.pem` (unread).

## Funnel status

Command: `sudo -n tailscale funnel status` (exit 0).

**Funnel is up.**

- Public: `https://claw.taild9f611.ts.net`
- Path: `/webhooks/github` → `http://10.200.200.1:18080/webhooks/github`

## Impact surface (this question)

Confirm names + live funnel only. No product tree change required by this analysis.

## Return for parent

- App ID env var name: `TRUST_CI_GITHUB_APP_ID`
- Funnel: still up (`https://claw.taild9f611.ts.net` → `/webhooks/github` proxy to `10.200.200.1:18080`)
