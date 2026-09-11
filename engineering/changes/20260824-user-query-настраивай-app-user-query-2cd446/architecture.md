# Architecture

```
GitHub App adaptive-trust-ci  (operator UI Save)
        │  POST HTTPS  HMAC X-Hub-Signature-256
        ▼
https://claw.taild9f611.ts.net/webhooks/github
        │  Funnel
        ▼
http://10.200.200.1:18080/webhooks/github → 127.0.0.1:18080
        ▼
FastAPI HMAC-first POST /webhooks/github
```

`PATCH /app/hook/config` is App-JWT-only. This slice is UI Save + docs. FastAPI frozen.
