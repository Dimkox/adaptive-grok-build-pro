# repo_explorer — Tailscale Funnel / loopback / FastAPI facts

Change: `20260824-user-query-github-app-adaptive-trust-ci-post-htt-813a02`  
Route: `813a02b06dfc`  
Collected: 2026-08-24 (read-only).  
Not done: `tailscale funnel reset`, `--set-path=/webhooks/github`, GitHub App hook PATCH, PEM/secret reads, POST to `https://claw.taild9f611.ts.net/webhooks/github`.

## 1. Funnel status (read-only)

`sudo -n tailscale funnel status --json` succeeded (passwordless sudo). Exit 0.

JSON:

```json
{}
```

Human `sudo -n tailscale funnel status`:

```
No serve config
```

`sudo -n tailscale serve status --json` also `{}`.

**Current Funnel paths: none.** Expected n8n `/webhook` is **not** present in this host’s Tailscale serve/funnel config right now. Path `/webhooks/github` is **not** mounted.

MagicDNS name from the task (not re-verified here): `claw.taild9f611.ts.net`. Intended public URL once a path exists: `https://claw.taild9f611.ts.net/webhooks/github`.

## 2. Loopback health (127.0.0.1:18080 only)

| URL | HTTP code |
| --- | --- |
| `http://127.0.0.1:18080/health/live` | **200** |
| `http://127.0.0.1:18080/health/ready` | **200** |

API process is up and ready on the published loopback port.

## 3. FastAPI routes (source)

File: `trust-ci/src/adaptive_trust_ci/api.py`

- `GET /health/live` — `create_app` `@app.get('/health/live')` (lines 51–53).
- `GET /health/ready` — `@app.get('/health/ready')` (lines 55–73).
- `POST /webhooks/github` — `@app.post('/webhooks/github')` (lines 75–109). Verifies `X-Hub-Signature-256` via `verify_webhook_signature` before `parse_pull_request_event`. `WebhookError` → HTTP 401. `event is None` (unsupported event such as signed ping) → `{'accepted': False, 'reason': 'ignored-event'}`.

Tests: `trust-ci/tests/test_api.py` posts `/webhooks/github` with HMAC headers.

## 4. Compose publish

`trust-ci/compose.yaml` service `api` ports:

```yaml
ports:
  - "127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"
```

Default host bind remains loopback **18080** → container 8080. `trust-ci/.env` sets `TRUST_CI_API_HOST_PORT=18080` (port only, not a secret). `trust-ci/env/common.env` has `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`.

## 5. Public Funnel POST

Skipped on purpose: Funnel has **no** `/webhooks/github` (and no `/webhook`) path. A public POST would not prove the FastAPI route.

## Verdict

Loopback Trust CI is healthy (`/health/live` 200, `/health/ready` 200). Compose still publishes `127.0.0.1:18080`. `POST /webhooks/github` and `GET /health/live` exist in `trust-ci/src/adaptive_trust_ci/api.py`. **Tailscale Funnel current paths: empty (`{}` / “No serve config”).** n8n `/webhook` is not visible on this host’s funnel/serve config. Write owner may add `/webhooks/github` later; do not `funnel reset`.
