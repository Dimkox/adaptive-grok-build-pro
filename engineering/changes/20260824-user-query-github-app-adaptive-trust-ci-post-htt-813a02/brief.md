# Tailscale Funnel public webhook path

Change ID: `20260824-user-query-github-app-adaptive-trust-ci-post-htt-813a02`
Route: `813a02b06dfc`
Write owner: `integration_implementer`

## Problem

GitHub App `adaptive-trust-ci` cannot POST to loopback `127.0.0.1:18080`. User named the public webhook URL:

`https://claw.taild9f611.ts.net/webhooks/github`

via Tailscale Funnel to `http://127.0.0.1:18080/webhooks/github`. This slice proves that path with unsigned HMAC 401. GitHub App webhook registration is **after** this proof.

## Outcome

Unsigned `POST https://claw.taild9f611.ts.net/webhooks/github` with `X-GitHub-Event: ping` returns HTTP 401 `missing or malformed webhook signature`. Local `GET /health/live` is 200. Funnel is not reset. API stays loopback-only. App hook is not PATCHed. M0.2 stays incomplete.

## Scope

### In scope

- Read `sudo tailscale funnel status --json` (already empty / no serve config).
- Add `--set-path=/webhooks/github` → `http://127.0.0.1:18080/webhooks/github` (path doubled; Funnel strips the mount).
- Local live 200; public unsigned ping 401.
- After proof: operator docs + M0 characterization name the Funnel webhook URL; plan checkbox stays **not done**.

### Out of scope

- `tailscale funnel reset`; old `funnel --bg 443 on`; `funnel --https=443 off`.
- Recreating n8n `/webhook` (currently absent; do not invent its target).
- `TRUST_CI_PUBLIC_BASE_URL` / compose recreate.
- GitHub App form / `PATCH /app/hook/config` / repo webhook / PEM.
- FastAPI HMAC changes.
- Claiming M0.2 complete; protecting `main`.

## Constraints

- Dual path is required so FastAPI still sees `/webhooks/github`.
- Do not print `TRUST_CI_WEBHOOK_SECRET`.
- Rollback: `sudo tailscale funnel --https=443 --set-path=/webhooks/github off` only.
