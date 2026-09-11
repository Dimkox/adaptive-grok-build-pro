# GitHub App webhook — operator Save

Page: https://github.com/settings/apps/adaptive-trust-ci

| Field | Value |
| --- | --- |
| Webhook Active | yes |
| Webhook URL | `https://claw.taild9f611.ts.net/webhooks/github` |
| Webhook secret | paste host `TRUST_CI_WEBHOOK_SECRET` (never commit or chat) |
| SSL verification | Enabled |
| Subscribe to events | **Pull request** |

Do not add a repository webhook. After Save: Advanced → Recent deliveries. A signed `ping` should be 200 `ignored-event`. `pull_request` enqueue is later M0.2 proof.

Agent cannot `PATCH /app/hook/config` (`gh api /app` 401 JWT).
