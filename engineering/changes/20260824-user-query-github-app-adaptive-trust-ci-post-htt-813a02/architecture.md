# Architecture — Funnel edge

No FastAPI contract change.

```
GitHub App adaptive-trust-ci   (registration later)
        │  POST HTTPS
        ▼
https://claw.taild9f611.ts.net/webhooks/github
        │  Tailscale Funnel :443  (strips mount /webhooks/github)
        ▼
http://127.0.0.1:18080/webhooks/github   ← target must include the path
        ▼
api.py POST /webhooks/github
  HMAC X-Hub-Signature-256 on raw body  → 401 if missing
  parse_pull_request_event              → ping/other = ignored-event
```

`TRUST_CI_PUBLIC_BASE_URL` stays loopback (Check Run `details_url`, not webhook routing).
