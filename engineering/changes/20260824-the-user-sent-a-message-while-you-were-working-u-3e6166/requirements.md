# Requirements

## Acceptance (P0)

1. `GET http://127.0.0.1:18080/health/ready` remains 200. Host `:8080` is SearXNG. Host `:1080` is proxy-gateway.
2. Compose project `adaptive-trust-ci` shows `worker` **running**. `docker-engine` is not restart-looping and is not required.
3. Overlay is **not** in tracked `trust-ci/compose.yaml`. `test_ops` still forbids `/var/run/docker.sock` in that file.
4. HMAC `POST http://127.0.0.1:18080/webhooks/github` returns 200 with `job_id`.
5. GitHub Check Run on the exact POST SHA: name `adaptive-trust-ci/verified@6737355947c2`, `app.id=4694114`, `external_id=job_id`.
6. No secrets in git, chat, or activation report. `main` unprotected. Repo hooks empty.

Honest terminals after P0: `failure` / `dead` / `action_required` (`needs_approval` expected for PR #5 because `decisions.md` is a governance glob). Do not forge human approval.

## Non-goals

Protect `main`, merge PR #5, register GitHub webhook, read PEM, GitHub Actions, M1–M9, `network_mode: host`, Trust CI on host 8080.
