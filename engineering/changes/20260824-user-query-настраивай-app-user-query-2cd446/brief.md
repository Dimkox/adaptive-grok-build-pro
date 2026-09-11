# Configure GitHub App webhook (UI; no PEM)

Change ID: `20260824-user-query-настраивай-app-user-query-2cd446`
Route: `2cd446440734`
Write owner: `general_implementer`

## Problem

User: настраивай app. GitHub App is `adaptive-trust-ci`. Public path `https://claw.taild9f611.ts.net/webhooks/github` already returns unsigned HMAC 401. `PATCH /app/hook/config` requires an App JWT. Current `gh` token is 401. PEM read is forbidden. Repo hooks are empty and must stay empty.

## Outcome

Operator saves App webhook settings. Agent does not PATCH, does not mint JWT, does not print `TRUST_CI_WEBHOOK_SECRET`. Docs name the Funnel URL as the App webhook URL. M0.2 stays **not done** until Recent Deliveries show GitHub POSTed.

## Scope

### In scope

- Stop on GitHub API: no PATCH, no PEM, no repo hook.
- Exact UI card for `https://github.com/settings/apps/adaptive-trust-ci`.
- Operator docs + characterization: Funnel URL is the App webhook URL; checkbox stays unchecked.

### Out of scope

- FastAPI, Funnel reset, compose, `TRUST_CI_PUBLIC_BASE_URL`.
- Claiming M0.2 complete; protecting `main`.
