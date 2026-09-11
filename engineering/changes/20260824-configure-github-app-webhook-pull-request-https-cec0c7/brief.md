# Configure GitHub App webhook (no repo hook)

**RETRACTED 2026-08-24:** `https://trust-ci.ii-tonya.ru/webhooks/github` is a ChatGPT error. Do not configure, probe, or complete TLS for it. See `20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86`.

Route `cec0c7622133`. **write_agent: none.** High-risk review.

## User order

App `adaptive-trust-ci`: Active, URL `https://trust-ci.ii-tonya.ru/webhooks/github`, secret = `TRUST_CI_WEBHOOK_SECRET`, SSL Enabled, event Pull request. No repository webhook.

## Ruling

`PATCH /app/hook/config` **requires a GitHub App JWT**. `gh api /app` with the user token returns **401** «JWT could not be decoded». `AGENTS.md` forbids reading the App PEM, so this agent cannot set the hook. Do not substitute a repository webhook.

Operator UI: https://github.com/settings/apps/adaptive-trust-ci

TLS: GitHub SSL verification will fail until the cert includes `trust-ci.ii-tonya.ru`. Public unsigned POST is currently **405 nginx**, not FastAPI **401**.
