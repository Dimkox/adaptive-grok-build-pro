# Integration analysis — GitHub App, webhook, Checks, branch-protect

Agent: `integration_architect` (read-only). Route `3722694830f7`. Change `20260824-user-query-read-agents-md-decisions-md-mistakes-372269`.
No `.env`/PEM/keys read. No push/merge/deploy. No GitHub Actions.

## Verdict

Adapters are implemented in `trust-ci/` and must stay on the **Trust plane**. The local Grok stack and any future `factory/` (absent today) stay on the **factory plane**: they may open PRs; they must not hold webhook HMAC, App RSA, installation tokens, CI signing keys, or publish `adaptive-trust-ci/verified@*`. Activation is operator work on an isolated CI host, not a factory grant.

Live: **M0 is not operational.** `origin/main` `48cb9737` is unprotected. No repo webhooks. Zero check runs on that SHA. PRs #2/#3/#4 only have GitGuardian. No Trust CI containers. `127.0.0.1:8080` is SearXNG, not the API. A gitignored leftover PEM is **not** an installation. Stale Actions catalog `trusted-ci.yml` exists but the file is gone from `main` — do not revive it.

## Plane split (do not mix)

| Secret / actuator | Owner | Forbidden |
| --- | --- | --- |
| `TRUST_CI_WEBHOOK_SECRET` | API only (`env/api.env`) | worker, factory, `common.env`, repo |
| App RSA + `APP_ID` + `INSTALLATION_ID` | worker only | API, factory, `grok_approve.py` |
| Installation token (`checks:write`,`contents:read`,`pull_requests:read`) | worker JWT mint | API, runner, laptop PAT |
| `TRUST_CI_GITHUB_ADMIN_TOKEN` | one-shot human CLI `branch-protect` | App, factory, long-lived |
| CI Ed25519 + trust-store | worker / API respectively | factory, PR checkout |

Holdout and compose tests enforce: `api.py` has no `GitHubClient`/`GitHubAppAuth`; PEM mount is worker-only; runner argv has no `TRUST_CI_GITHUB`. `grok_approve.py` sets `external_trust_ci_authority=false`. Do not enqueue factory tasks into `trust_ci_jobs`.

## Activation order (strict)

1. Dedicated CI host + pinned images/holdout. Do **not** bind compose `127.0.0.1:8080:8080` on this laptop (SearXNG collision). Terminate **TLS** on a reverse proxy; set `TRUST_CI_PUBLIC_BASE_URL=https://…`. GitHub will not deliver to HTTP except localhost, which is not a public webhook.
2. API+Postgres+worker up. Health on a **free** loopback port behind the proxy; expose `/webhooks/github` and `/approvals` only.
3. Register a **repository** webhook (not an App webhook): `https://<ci>/webhooks/github`, `application/json`, secret=`TRUST_CI_WEBHOOK_SECRET`, events=`pull_request`. HMAC is SHA-256 of the raw body (`X-Hub-Signature-256`). API verifies before parse; 401 on mismatch.
4. Disposable docs PR (drafts **do** enqueue). Worker mints App JWT (RS256, iat−60s, exp 9m) → reduced installation token → Checks API. Name = `adaptive-trust-ci/verified@<policy.digest[:12]>`. `external_id` = durable `job_id`. Reuse by `(name, external_id)` on retry; API never publishes.
5. Duplicate GitHub deliveries: idempotency key = sha256(repo, pr, head_sha, pipeline, policy_digest), `ON CONFLICT DO NOTHING` → same `job_id`, `created=false`. Do not close/reopen the same SHA expecting a new job (cancelled row is reused). New SHA supersedes.
6. Offline-verify attestation. Only then `branch-protect` with a **temporary human admin token**, App ID, and deployed policy check name. Payload uses `checks[{context, app_id}]` (no legacy `contexts`). Same text from GitGuardian/GHA/PAT cannot satisfy. Revoke the admin token after the PUT.
7. Never grant the App `Administration`. Never call Checks API from factory.

## Prove installation ID without private material

Do this on the operator machine, not in the agent workspace.

- GitHub UI: repo → Settings → GitHub Apps → `adaptive-trust-ci`; copy numeric **App ID** and **installation ID** from the URL (`/installations/<id>`).
- Or mint a short-lived App JWT **from the worker-mounted key in place** and `GET /repos/Dimkox/adaptive-grok-build-pro/installation`; record only `{app_id, id, app_slug, account}`.
- Put IDs in untracked `env/worker.env`. Operator-safe evidence may list the two integers + slug. Never commit PEM, JWT, installation token, webhook secret, or admin token. This session’s `user/installations` 403 and empty `/hooks` mean **ID is still unproven**.

## Rollback if protection is applied too early

Early protection on a missing App-owned check locks `main`.

1. Kill switch on (blocks new jobs; does not forge success).
2. Human admin token: remove **only** the exact `adaptive-trust-ci/verified@<epoch>` required check (keep PR/linear/no-force rules if already wanted).
3. Restore previous reviewed API/worker/holdout/policy. Epoch change requires a fresh disposable-PR check, then re-PUT protection with the new name + App ID.
4. Never substitute local receipts, delegated grants, GitGuardian, or the stale `trusted-ci` Actions workflow.

## Live evidence still missing

- Installed App + recorded installation ID (worker-provisioned, untracked).
- HTTPS webhook endpoint and at least one HMAC-verified delivery.
- Deployed worker Check Run `adaptive-trust-ci/verified@<policy-sha12>` owned by `adaptive-trust-ci`, `external_id=job_id`, exact head SHA.
- Signed attestation verified with the published CI public key.
- `main.protected=true` with that check + App ID (currently `protected:false`).
- Isolated host (not SearXNG `:8080`), backup/restore, kill-switch, and protected-path approval drills.

Until those exist, factory work must not call `branch-protect` or treat GitGuardian as merge authority.
