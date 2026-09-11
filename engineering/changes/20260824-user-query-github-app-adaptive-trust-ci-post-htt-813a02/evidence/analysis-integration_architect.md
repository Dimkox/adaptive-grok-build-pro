# Integration analysis — Funnel edge to existing FastAPI HMAC

Agent: `integration_architect` (read-only). Route `813a02b06dfc`.
Change: `engineering/changes/20260824-user-query-github-app-adaptive-trust-ci-post-htt-813a02`.

Sources: `trust-ci/src/adaptive_trust_ci/{api.py,webhooks.py,settings.py,models.py,store.py,github.py,github_app.py,cli.py}`, `trust-ci/tests/{test_api.py,test_webhooks_github.py}`, `trust-ci/compose.yaml`, `trust-ci/README.md`, `mistakes.md`, `decisions.md`. No `.env`, `api.env`, PEM, webhook secret, JWT, or production dumps were read. No Funnel mutation, no GitHub API call, no `/app/hook/config`, no push/merge/deploy.

## Verdict

**FastAPI unchanged.** `POST /webhooks/github` already verifies `X-Hub-Signature-256` on the **raw body** before JSON, consumes only `pull_request`, and returns HTTP 200 `ignored-event` for a correctly signed `ping`. Do not edit `api.py`, `webhooks.py`, settings, compose, or OpenAPI.

**Unsigned public 401 is success for this slice.** Operator `POST https://claw.taild9f611.ts.net/webhooks/github` with `X-GitHub-Event: ping`, body `{}`, **no** signature must be FastAPI **HTTP 401** `missing or malformed webhook signature`. That is the go-signal that Tailscale Funnel reached loopback FastAPI. It is **not** a parser bug and **not** a GitHub delivery.

**GitHub App webhook registration is not this slice.** Do not PATCH/GET `/app/hook/config`. Do not mint App JWT. Do not read PEM. Do not create a repository webhook. Do not write the Funnel URL into the App until a later, explicitly delegated slice after the unsigned-401 go-signal.

---

## Frozen inbound contract (already implemented)

Public edge this slice is meant to expose (Funnel, not FastAPI):

```text
GitHub (later slice) or operator curl
  POST https://claw.taild9f611.ts.net/webhooks/github
    ↓ Tailscale Funnel (--set-path=/webhooks/github)
  POST http://127.0.0.1:18080/webhooks/github
    ↓ compose publish 127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080
  FastAPI POST /webhooks/github
```

Payload URL must have **no trailing slash**. FastAPI default `redirect_slashes` can 307 `POST /webhooks/github/` and drop the body.

Path is doubled on purpose. Funnel strips the public mount before proxying; the **target** must keep `/webhooks/github` so FastAPI sees its route, not `POST /` (404, not HMAC 401). Existing n8n mount is `/webhook` (no `s`). Add beside it. **Never** `tailscale funnel reset`.

### Headers and body

| Item | Frozen value |
| --- | --- |
| Method / path | `POST /webhooks/github` only (`GET` is FastAPI 405) |
| Content-Type | `application/json` (GitHub). Handler does not gate on it; HMAC is over raw bytes. |
| Auth | `X-Hub-Signature-256: sha256=<64 lowercase hex>` HMAC-SHA256(raw body, UTF-8 `TRUST_CI_WEBHOOK_SECRET`) |
| Event | `X-GitHub-Event` |
| Consumed event | `pull_request` only |
| Ignored after HMAC | `ping`, `push`, `installation`, `check_run`, any other name → 200 `ignored-event` |
| Extra App headers / JSON keys | Ignored (`X-GitHub-Delivery`, `X-GitHub-Hook-Installation-Target-Type`, `installation`, `sender`) |

No OpenAPI: `create_app` sets `openapi_url=None`. `engineering/contracts/openapi/` is empty. Freeze here, not as a new schema file this slice.

### HMAC before JSON (cite)

`trust-ci/src/adaptive_trust_ci/api.py` `github_webhook` (lines 75–88):

```text
body = await request.body()                                   # raw bytes, not request.json()
verify_webhook_signature(settings.webhook_secret, body, x_hub_signature_256)
event = parse_pull_request_event(x_github_event, body)        # JSON only after HMAC
if event is None:
    return {"accepted": False, "reason": "ignored-event"}     # HTTP 200
```

Both HMAC and parse failures become **HTTP 401** (`HTTPException(status_code=401, detail=str(exc))`). FastAPI wraps that as JSON `{"detail":"<message>"}`.

`trust-ci/src/adaptive_trust_ci/webhooks.py` `verify_webhook_signature` (lines 25–35):

| Input | `WebhookError` | HTTP |
| --- | --- | --- |
| empty secret | `webhook secret is not configured` | 401 |
| missing header, or not `sha256=` prefix | `missing or malformed webhook signature` | 401 |
| hex after prefix not length 64 | `malformed webhook signature` | 401 |
| 64 hex that does not match HMAC | `invalid webhook signature` | 401 |

Compare is `hmac.compare_digest` over SHA-256 of **raw body**. GitHub App and repository hooks share this header ([Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)).

`parse_pull_request_event` returns `None` **before** `json.loads` when `event_name != "pull_request"`. Signed `ping` therefore never parses JSON.

### Response matrix (frozen)

| Probe | Status | Body (semantic) |
| --- | --- | --- |
| Unsigned POST, no `X-Hub-Signature-256`, event `ping`, body `{}` | **401** | `missing or malformed webhook signature` |
| Header present but not `sha256=` / short hex | **401** | missing/malformed |
| `sha256=` + 64 wrong hex | **401** | `invalid webhook signature` |
| Valid HMAC + `X-GitHub-Event: ping` (or any non-`pull_request`) | **200** | `{"accepted":false,"reason":"ignored-event"}` |
| Valid HMAC + `pull_request` + action `opened`/`synchronize`/`reopened`/`ready_for_review` + allowlisted repo | **200** | `accepted: true`, `created`, `job_id`, `status`, `status_publisher: worker-github-app` |
| Same identity twice | **200** | same `job_id`, `created: false` |
| Valid HMAC + `pull_request` + `closed` | **200** | `accepted: true`, `cancelled_jobs` |
| Valid HMAC + `pull_request` + unsupported action (`edited`, `labeled`, …) | **200** | `ignored-event` |
| Valid HMAC + `pull_request` + invalid JSON / missing objects / bad SHAs | **401** | parse `WebhookError` |
| Allowlisted HMAC + repo not in policy | **403** | `repository is not allowed by server policy` |
| Kill switch + new enqueue (not `closed`) | **503** | `global kill switch is active` |
| Loopback `GET /health/live` | **200** | `{"status":"live",...}` — local liveness only, not Funnel proof |

GitHub treats 2xx as successful delivery. A signed `ping` **must stay 200**. Do not add a ping route. Do not turn unsigned 401 into 200.

### Canonical `pull_request` fields (after HMAC)

```text
repository.full_name
pull_request.number
pull_request.head.sha / .ref
pull_request.base.sha / .ref
action ∈ {opened, synchronize, reopened, ready_for_review} → enqueue
action == closed → cancel_pr
```

`draft` is unused; drafts enqueue (`decisions.md` 2026-08-23). SHAs must be lowercase 40-hex (`JobRequest.require_sha`). Extra App `installation` is ignored.

---

## Tests that already freeze this (cite; do not rewrite product)

`trust-ci/tests/test_webhooks_github.py`:

- `test_valid_signature_verifies` — HMAC-SHA256 over raw body + `sha256=` hex.
- `test_invalid_signature_is_rejected` — 64-zero hex → `WebhookError` `/invalid/`.
- `test_pull_request_opened_becomes_job_request`, `test_synchronize_is_supported`, `test_draft_pull_request_is_enqueued`, `test_closed_pull_request_is_parsed_for_cancellation`.
- `test_other_events_are_ignored` — `parse_pull_request_event('push', b'{}')` is `None` (same path as `ping`).

`trust-ci/tests/test_api.py`:

- `headers()` builds `X-Hub-Signature-256` + `X-GitHub-Event: pull_request`.
- `test_signed_webhook_only_enqueues_for_worker_publisher` — HMAC then enqueue 200.
- `test_duplicate_webhook_reuses_idempotent_job` — duplicate delivery is the outbox.
- `test_invalid_webhook_signature_is_rejected` — wrong HMAC → **401**.
- `test_disallowed_repository_is_rejected` — 403 after HMAC.
- `test_kill_switch_blocks_new_jobs_without_needing_github_credentials` — 503.
- `test_closed_pull_request_cancels_active_job` — 200 `cancelled_jobs`.

Characterization gaps (tests of **existing** behavior only; still no FastAPI edit):

- API POST with **omitted** `X-Hub-Signature-256` and `X-GitHub-Event: ping` → 401 `missing or malformed webhook signature` (operator Funnel probe).
- API POST with valid HMAC + `X-GitHub-Event: ping` → 200 `ignored-event`.

Those tests belong to `integration_implementer` if the write wave needs a failing/characterization test. They must not change handler order, status codes, or messages.

---

## Adapter, outbox, reconciliation (no new machinery)

```text
Funnel HTTPS
  → loopback FastAPI
  → HMAC adapter (raw body + X-Hub-Signature-256)     # webhooks.py
  → parse_pull_request_event (pull_request only)
  → policy.allows_repository
  → PostgreSQL enqueue / cancel_pr                    # store.py
       idempotency_key = sha256(canonical_json(
         repository, pr_number, head_sha, pipeline, policy_digest))
       ON CONFLICT (idempotency_key) DO NOTHING
       other in-flight heads on same PR → cancelled superseded-head
  → HTTP 200
  → worker claim / Check Run / holdout / runner       # not this slice
```

The insert **is** the outbox. Duplicate GitHub deliveries reuse the row. API has no `GitHubClient`; Checks stay on the worker. Auth split unchanged: API holds `TRUST_CI_WEBHOOK_SECRET` (name only; value never in git/chat/evidence) + human **public** trust store; worker holds App RSA / installation token. Do not move the webhook secret onto the worker.

Retries: GitHub retries non-2xx. HMAC 401 on an unsigned operator curl is expected. GitHub’s own deliveries are signed when the App secret is set, so they must land on the 200 rows above. Do not store `X-GitHub-Delivery` this slice.

Dead-letter: none at the HTTP edge. Failed HMAC is fail-closed 401 with no persist. Malformed `pull_request` after HMAC is also 401 (existing; freeze). Jobs that enqueue then fail in the worker stay in PostgreSQL — out of this Funnel slice.

---

## Funnel vs FastAPI vs App PATCH (scope cut)

| Action | This slice |
| --- | --- |
| Inspect current Funnel (`tailscale funnel status [--json]`) | operator / write agent host ops, **do not reset** |
| Add path `/webhooks/github` → `http://127.0.0.1:18080/webhooks/github` beside n8n `/webhook` | in scope as **edge**, not product code |
| Loopback `GET http://127.0.0.1:18080/health/live` → 200 | local liveness |
| Public unsigned POST ping → **401** HMAC | **go-signal** Funnel reached FastAPI |
| Edit `api.py` / `webhooks.py` / tests of new behavior / compose port | **forbidden** (FastAPI unchanged) |
| `PATCH`/`GET` `https://api.github.com/app/hook/config` | **forbidden** |
| Mint App JWT / read PEM / call GitHub App settings API | **forbidden** |
| Register App webhook URL / secret / Pull request subscription | **later slice**, after unsigned 401 |
| Create repository webhook | **forbidden** (App already has Installation ID; second hook double-delivers) |
| `tailscale funnel reset` / old `funnel --bg 443 on` | **forbidden** (destroys n8n/TikTok route / stale CLI) |
| Read `trust-ci/env/api.env` or print `TRUST_CI_WEBHOOK_SECRET` | **forbidden** |

`github.py` PATCH targets are `/repos/{repo}/check-runs/{id}` only (worker Check Runs). `github_app.py` POSTs `/app/installations/{id}/access_tokens` only. **No** `/app/hook/config` client exists. Do not add one. App hook config requires App JWT from the PEM; installation tokens cannot publish it. That is why App registration is a human UI (or a later delegated JWT slice), not this Funnel proof.

Public hostname `claw.taild9f611.ts.net` is the operator-named Tailscale Funnel MagicDNS name. Do not substitute the ChatGPT-invented `trust-ci.ii-tonya.ru` (`mistakes.md` / `decisions.md` 2026-08-24). Do not treat Funnel proof as GitHub App registration.

`TRUST_CI_PUBLIC_BASE_URL` is worker `details_url`, not the inbound webhook path. Leave it on loopback until a later slice that is explicitly about Check Run links. Funnel exposing `/webhooks/github` does not require changing that setting this slice.

---

## Operator probes (no secrets)

Local:

```bash
curl -i http://127.0.0.1:18080/health/live
# expect HTTP 200
```

Public unsigned (Funnel go-signal):

```bash
curl -i -X POST \
  -H 'Content-Type: application/json' \
  -H 'X-GitHub-Event: ping' \
  --data '{}' \
  https://claw.taild9f611.ts.net/webhooks/github
# expect HTTP 401
# missing or malformed webhook signature
```

Interpret:

| Result | Meaning |
| --- | --- |
| FastAPI **401** + that detail | Funnel stripped/re-added path correctly; HMAC fail-closed; **this slice succeeds** |
| 404 | Funnel target lost `/webhooks/github` after mount strip, or no handler |
| HTML/nginx/Caddy **405** | request never hit FastAPI |
| TLS / Funnel timeout | public HTTPS did not reach claw |
| **200** on unsigned POST | **fail** — HMAC not applied; do not proceed to App registration |

Signed ping **200** `ignored-event` is GitHub’s later delivery (or a loopback HMAC characterization). It is **not** required to declare Funnel success. Do not HMAC-sign a public probe in this analysis (would need the secret).

---

## Implementer constraints

Write owner is `integration_implementer`. Product intake is already channel-agnostic. This slice is Funnel path + contract freeze + unsigned-401 proof.

- Do not change FastAPI.
- Do not PATCH `/app/hook/config`.
- Do not read secrets.
- Optional: characterization tests of missing-signature 401 and signed-ping 200 `ignored-event` only.
- Optional: runbook/change-package notes for Funnel command, path doubling, and “unsigned 401 = go”.
- After unsigned 401: stop. App webhook Active/URL/secret/SSL/Pull request is the next named slice.

No production writes to GitHub, 1C, Bitrix24, Funnel reset, or infra were performed. No API schema change is required or permitted.
