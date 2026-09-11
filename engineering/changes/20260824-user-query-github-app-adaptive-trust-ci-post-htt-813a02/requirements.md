# Requirements — Funnel webhook path

## Acceptance criteria

- [ ] Given current Funnel config, when status is read, then it is not reset.
- [ ] Given `sudo tailscale funnel --bg --https=443 --set-path=/webhooks/github http://127.0.0.1:18080/webhooks/github`, when status is listed, then `/webhooks/github` is present.
- [ ] Given `GET http://127.0.0.1:18080/health/live`, then HTTP 200.
- [ ] Given unsigned `POST https://claw.taild9f611.ts.net/webhooks/github` with `X-GitHub-Event: ping` and body `{}`, then HTTP 401 and body mentions missing or malformed webhook signature.
- [ ] Operator docs name that Funnel URL; M0.2 checkbox remains **not done**; `TRUST_CI_PUBLIC_BASE_URL` cell stays loopback.
- [ ] FastAPI, compose, gitignored env, GitHub App hook config unchanged.

## Failure and edge cases

- Funnel config is currently empty; do not treat missing n8n `/webhook` as a reason to reset or to skip adding GitHub path.
- HTTP 404/405/502 on the public POST means Funnel did not reach FastAPI HMAC.
- Signed ping is 200 `ignored-event` (not this slice’s public probe).

## Non-functional

- Security: HMAC fail-closed; no PEM; no secret in evidence.
- Rollback: remove only `/webhooks/github` funnel path.
