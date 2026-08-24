# docs_researcher — Trust CI GitHub App env, webhooks, health

Sources: `trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`, `trust-ci/env/worker.env.example` (env names only; no `.env`/secrets). User values App ID `4694114` / Installation ID `156003193` are not in those docs; they belong in worker-only env, never in the API.

Worker-only GitHub App env (`README` + `worker.env.example`; API must not receive them):
- `TRUST_CI_GITHUB_APP_ID`
- `TRUST_CI_GITHUB_INSTALLATION_ID`
- `TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH` (RSA PEM, worker-only)
- App permissions: Checks read/write, Contents read, Pull requests read. Worker mint token is `checks:write`, `contents:read`, `pull_requests:read`.

Webhook (`README` GitHub configuration; rollout: HTTPS `/webhooks/github`, API-only HMAC secret):
- Event: GitHub **Pull requests** (`pull_request`). Payload URL `…/webhooks/github`, `application/json`, secret `TRUST_CI_WEBHOOK_SECRET`.
- HMAC header: `X-Hub-Signature-256` (`sha256=` hex); FastAPI binds `x_hub_signature_256`.
- Drafts: parser does not skip `draft: true` (`tests/test_webhooks_github.py` `test_draft_pull_request_is_enqueued`); opened/synchronize/reopened/ready_for_review enqueue; `closed` cancels.

Health stays host **18080**: `curl -fsS http://127.0.0.1:18080/health/ready` after `docker compose up -d postgres migrate api worker`. Compose maps `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`. Rollout order: deploy API/Postgres/worker → webhook → disposable PR proving App-owned `adaptive-trust-ci/verified@<policy-sha12>` → then branch protection (`TRUST_CI_GITHUB_ADMIN_TOKEN` + `TRUST_CI_GITHUB_APP_ID`, not the long-lived App).
