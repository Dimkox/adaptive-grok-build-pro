# Implementation

- Streamed PATCH script into `adaptive-trust-ci-worker-1:/tmp`.
- Loaded `TRUST_CI_WEBHOOK_SECRET` via `--env-file trust-ci/env/api.env` (not printed).
- Minted App JWT in-process from mounted PEM.
- PATCH `/app/hook/config` → 200, URL Funnel, SSL on, secret set.
- Ping redelivery → 200 OK.
- GET `/app` `events: []`; PATCH `/app` events 404.
- Plan/activation-report wording updated; checkbox stays `[ ]`.
