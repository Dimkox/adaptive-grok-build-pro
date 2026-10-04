# M0.1 listener on <ci-host>

Route `6346a398114f`. User approved the dark-factory roadmap and automatic continuation.

## Outcome

`GET http://<loopback-trust-ci>/health/ready` returns 200 from compose project `adaptive-trust-ci` on host `<ci-host>`. Webhook absent. `main` unprotected.

## In scope

- Untracked host env/policy/holdout/signing key (gitignored)
- `docker compose up` postgres+migrate+api (worker only if App IDs exist without printing PEM)
- Activation-report operator-safe fields

## Out of scope

- Webhook, branch-protect, merge PR #5, M2, GitHub Actions, host 8080, reading PEM into chat
