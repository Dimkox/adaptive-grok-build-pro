# Integration analysis — freeze webhook contract (ChatGPT URL is not a target)

Agent: `integration_architect` (read-only). Route `b66b867ba5ab`.
Change: `engineering/changes/20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86`.

User correction (verbatim): `https://trust-ci.ii-tonya.ru/webhooks/github нет , не трогаем, это ошибка chatgpt`

Sources cited: `trust-ci/src/adaptive_trust_ci/{api,webhooks,settings}.py`, `trust-ci/src/adaptive_trust_ci/{github,github_app,store,models}.py`, `trust-ci/tests/{test_api,test_webhooks_github,test_m0_invariants,test_github_app}.py`, `trust-ci/compose.yaml`, `trust-ci/holdout.example/validate.py`, activation report, sibling `010964` `github-delivery-diagnosis.md`, sibling `cec0c7` (superseded). No `.env`, PEM, webhook secret, JWT, or production dumps were read. No GitHub App hook API was called. The ChatGPT URL was **not** re-probed.

## Verdict

**FastAPI unchanged; App webhook URL forbidden; repo webhook forbidden.**

1. FastAPI path remains `POST /webhooks/github` with HMAC `X-Hub-Signature-256`. No FastAPI, adapter, settings, or test change is required for this slice.
2. GitHub App webhook URL must **not** be set to `https://trust-ci.ii-tonya.ru/webhooks/github`. That hostname is a ChatGPT error. Do not PATCH `/app/hook/config`. Do not open the App settings form to paste that URL.
3. A repository webhook must **not** be created as a substitute (`POST /repos/{owner}/{repo}/hooks` forbidden). Empty repo-hooks list from sibling `010964` stays the last recorded GitHub-side fact.
4. Public unsigned POST recorded as **405 nginx** on both `trust-ci.ii-tonya.ru` and `ii-tonya.ru` is **historical probe evidence**. Do not re-probe the ChatGPT URL.
5. Loopback HMAC `POST http://127.0.0.1:18080/webhooks/github` remains the **only proven GitHub delivery path** (Check Runs exist; GitHub never POSTed).
6. Frozen producer / adapter / consumer / outbox are listed in §6. Sibling `cec0c7` operator mapping that named the ChatGPT URL is **superseded** by this user correction.

---

## 1. FastAPI path stays `POST /webhooks/github` + HMAC — no FastAPI change

Handler (`trust-ci/src/adaptive_trust_ci/api.py` lines 75–109):

```text
@app.post('/webhooks/github')
async def github_webhook(request, x_hub_signature_256=Header, x_github_event=Header):
    body = await request.body()                                 # raw bytes
    verify_webhook_signature(settings.webhook_secret, body, x_hub_signature_256)
    event = parse_pull_request_event(x_github_event, body)
    # WebhookError → HTTP 401
    # event is None → HTTP 200 {"accepted": false, "reason": "ignored-event"}
    # policy deny → 403; closed → cancel_pr; stopped → 503; else enqueue
```

HMAC adapter (`trust-ci/src/adaptive_trust_ci/webhooks.py` `verify_webhook_signature`):

| Rule | Frozen value |
| --- | --- |
| Header | `X-Hub-Signature-256` (FastAPI binds `x_hub_signature_256`) |
| Format | `sha256=` + exactly 64 hex |
| Algorithm | HMAC-SHA256 of **raw body**, secret UTF-8 |
| Compare | `hmac.compare_digest` |
| Empty secret | `WebhookError("webhook secret is not configured")` |
| Missing / not `sha256=` | `WebhookError("missing or malformed webhook signature")` |
| Wrong length | `WebhookError("malformed webhook signature")` |
| Mismatch | `WebhookError("invalid webhook signature")` |
| API mapping | all `WebhookError` → **HTTP 401** |

Secret source (`trust-ci/src/adaptive_trust_ci/settings.py` `ApiSettings`): `_required('TRUST_CI_WEBHOOK_SECRET')`. API-only. Worker settings do not load this variable. Example placeholder lives in `trust-ci/env/api.env.example`; the live value is gitignored and was not read.

Parser (`webhooks.py` `parse_pull_request_event`): only `X-GitHub-Event: pull_request` is consumed. Other events (including GitHub `ping`) return `None` **before** `json.loads`. Supported actions: `opened`, `synchronize`, `reopened`, `ready_for_review` (enqueue) and `closed` (cancel). Canonical fields: `repository.full_name`, `pull_request.number`, `head.sha` / `head.ref`, `base.sha` / `base.ref`. Extra App keys (`installation`, `sender`) are ignored. `draft` is unused (drafts enqueue).

`openapi_url=None`. Empty `engineering/contracts/openapi/`. Holdout (`trust-ci/holdout.example/validate.py`) and `test_m0_invariants.py` `test_api_cannot_hold_github_app_or_client` forbid `GitHubClient` / `GitHubAppAuth` in `api.py`. That split stays frozen.

### Tests that already freeze this contract (do not rewrite for this slice)

`trust-ci/tests/test_webhooks_github.py`:

- `test_valid_signature_verifies`
- `test_invalid_signature_is_rejected`
- `test_pull_request_opened_becomes_job_request`
- `test_synchronize_is_supported`
- `test_draft_pull_request_is_enqueued`
- `test_closed_pull_request_is_parsed_for_cancellation`
- `test_other_events_are_ignored` (`push` → `None`)

`trust-ci/tests/test_api.py`:

- `headers()` builds `X-Hub-Signature-256: sha256=<hex>` + `X-GitHub-Event: pull_request`
- `test_signed_webhook_only_enqueues_for_worker_publisher` → 200, `created: true`, `status_publisher: worker-github-app`
- `test_duplicate_webhook_reuses_idempotent_job` → same `job_id`, `created: false`
- `test_invalid_webhook_signature_is_rejected` → **401**
- `test_disallowed_repository_is_rejected` → **403**
- `test_kill_switch_blocks_new_jobs_without_needing_github_credentials` → **503**, no row
- `test_closed_pull_request_cancels_active_job` → `cancelled_jobs: 1`

No product test, handler, or HMAC rule needs to change because a ChatGPT public URL is withdrawn. Characterization of loopback HMAC already exists.

---

## 2. GitHub App webhook URL must not be `https://trust-ci.ii-tonya.ru/webhooks/github`

User: that URL **does not exist as a Trust CI target**; **do not touch it**; it is a ChatGPT error.

This supersedes sibling change `20260824-configure-github-app-webhook-pull-request-https-cec0c7`, whose brief and `analysis-integration_architect.md` told the operator to set App Webhook URL to exactly that hostname. That operator mapping is **void**.

Reasons the URL is not a delivery target (historical, not re-probed):

- Public name is nginx on `157.22.187.237` (apex `ii-tonya.ru`), not claw Apache → `127.0.0.1:18080`.
- Cert SAN does not include `trust-ci.ii-tonya.ru` (SSL hostname mismatch under verify-on).
- Unsigned POST there was **405 nginx**, not FastAPI **401**. GitHub SSL-enabled deliveries would never reach HMAC.
- `TRUST_CI_PUBLIC_BASE_URL` remains `http://127.0.0.1:18080` (activation report; `CommonSettings` allows loopback HTTP). Compose publish is `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080` (`trust-ci/compose.yaml`, `test_compose_publishes_loopback_not_all_interfaces`).

Forbidden this slice:

- Set, change, or “fix” GitHub App webhook URL to `https://trust-ci.ii-tonya.ru/webhooks/github`.
- Call `GET`/`PATCH /app/hook/config` (App JWT / PEM required; `AGENTS.md` forbids reading the App private key; this agent did not call it).
- Mint an App JWT to configure hooks (`github_app.py` `generate_app_jwt` exists only for **installation tokens** on the worker).
- Disable SSL verification (`insecure_ssl`) to paper over the parent-domain cert.
- Point the App URL at loopback (`http://127.0.0.1:18080/webhooks/github`) — GitHub cannot POST there.

`GitHubAppAuth` (`trust-ci/src/adaptive_trust_ci/github_app.py`) POSTs only `/app/installations/{id}/access_tokens` with `checks:write`, `contents:read`, `pull_requests:read`. Tests in `test_github_app.py` cover JWT/token cache, not hook config. That surface stays frozen.

---

## 3. Repository webhook must not be created as a substitute

Last recorded GitHub-side fact (sibling `010964` `github-delivery-diagnosis.md`, not re-listed here): `GET /repos/.../hooks` was **empty**. GitHub is not POSTing.

Creating a repo hook would not repair the ChatGPT URL. It would:

- Invent a second producer the user did not order.
- Still need a public HTTPS path that FastAPI actually serves (does not exist).
- Risk double-delivery later if a real App URL is ever configured on a working edge (idempotency would collapse duplicates to `created: false`, but two secrets and two Recent-Deliveries UIs would remain).

`GitHubClient` (`trust-ci/src/adaptive_trust_ci/github.py`) methods: `ensure_check_run`, `complete_check_run`, `configure_branch_protection`. **No** `hooks` create/list/edit. Do not add one. Do not `gh api repos/.../hooks`. README still says “Create a repository webhook” with example `https://ci.example.com/webhooks/github` — that is a **docs gap**, not a license to install a hook this slice. M0.2 plan checkbox stays **not done** (`docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`).

---

## 4. 405 nginx is historical — do not re-probe the ChatGPT URL

Recorded once in `engineering/changes/20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964/evidence/github-delivery-diagnosis.md` (and restated, not re-probed, by `cec0c7`):

| Historical probe | Result |
| --- | --- |
| Unsigned `POST https://trust-ci.ii-tonya.ru/webhooks/github` | HTTP **405** nginx «Not Allowed» — not FastAPI 401 |
| Unsigned `POST https://ii-tonya.ru/webhooks/github` | HTTP **405** nginx — same class |
| `https://trust-ci.ii-tonya.ru/health/ready` verify-on | SSL hostname mismatch |
| same, verify-off | HTTP 200 **app** JSON (not Trust CI `policy_digest`) |
| claw `GET http://127.0.0.1:18080/health/ready` | 200 Trust CI ready |

This slice **must not** curl, urllib, or otherwise re-hit `https://trust-ci.ii-tonya.ru/webhooks/github`. User said do not touch it. Treat 405 as frozen evidence that the public name is the wrong HTTP stack.

Diagnostic meanings remain (for a **future named** public-edge slice, not now):

| If a **legitimate** public POST ever happens | Meaning |
| --- | --- |
| Unsigned POST → FastAPI **401** JSON `missing or malformed webhook signature` | Request reached HMAC |
| Unsigned POST → **405 nginx** HTML | Never reached FastAPI |
| FastAPI GET `/webhooks/github` | FastAPI **405** (POST-only); distinguish via `Server` + JSON vs HTML |
| Signed `ping` after HMAC | **200** `ignored-event` (parser returns `None`; do not add a ping route) |

None of those public probes are in scope here.

---

## 5. Loopback HMAC is the only proven delivery path

Proven (activation report + `decisions.md`):

- Compose API bind: `127.0.0.1:18080` → container `8080`.
- `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`.
- Operator/agent HMAC `POST http://127.0.0.1:18080/webhooks/github` for draft PR **#5** produced App-owned Check Run `adaptive-trust-ci/verified@6737355947c2` id `97390635614` on SHA `1fc942065a124ce75659bd082519d8ebc37774e8`, `external_id` = durable `job_id` `1b63d10b-90c1-498a-97b8-7b5e0ea76aec`, App `4694114`. Later local HMAC bound `97406973020` to `ce03c87`.
- Activation report: “First App-owned Check Run was published by a loopback HMAC POST (**not** a GitHub-registered webhook).”
- M0.2 checkbox: Register repo webhook — **not done** (no public HTTPS). Partial Check Run via **local HMAC**.

Loopback HMAC is a **characterization** of the frozen FastAPI contract. It is not GitHub delivery, not M0.2 complete, not merge authority, and not a reason to register any public URL.

---

## 6. Producer / consumer / adapter that must stay frozen

```text
[producer — frozen]
  ONLY proven: loopback characterization
    operator/agent HMAC POST http://127.0.0.1:18080/webhooks/github
  FORBIDDEN this slice:
    GitHub App webhook URL = https://trust-ci.ii-tonya.ru/webhooks/github
    repository webhook POST /repos/.../hooks
    GitHub App hook API GET/PATCH /app/hook/config
    re-probe of the ChatGPT URL

        │  headers: X-Hub-Signature-256, X-GitHub-Event
        │  body: raw JSON bytes
        ▼
[adapter — frozen, no code change]
  api.py POST /webhooks/github
    → webhooks.py verify_webhook_signature (HMAC first)
    → webhooks.py parse_pull_request_event (pull_request only)
    → policy.allows_repository
        ▼
[consumer / outbox — frozen]
  PostgresStore.enqueue / cancel_pr
    idempotency_key = sha256(canonical_json(repository, pr_number, head_sha, pipeline, policy_digest))
    ON CONFLICT (idempotency_key) DO NOTHING
    new head SHA cancels in-flight jobs (superseded-head)
  HTTP 200 {accepted, created, job_id, status, status_publisher: worker-github-app}
        ▼
[downstream publisher — frozen, not this slice]
  worker GitHubAppAuth installation token
    → GitHubClient.ensure_check_run / complete_check_run
  API must not hold GitHubClient / GitHubAppAuth (holdout + test_m0_invariants)
```

| Role | Component | Freeze rule |
| --- | --- | --- |
| Producer (proven) | Loopback HMAC client → `127.0.0.1:18080` | Keep as the only live intake |
| Producer (ChatGPT) | App webhook URL `https://trust-ci.ii-tonya.ru/webhooks/github` | **Do not set, edit, or probe** |
| Producer (substitute) | Repository webhook | **Do not create** |
| Auth adapter | `verify_webhook_signature` + `TRUST_CI_WEBHOOK_SECRET` | HMAC-SHA256 raw body; 401 fail-closed |
| Event adapter | `parse_pull_request_event` | `pull_request` only; ping/other → 200 ignored-event |
| HTTP binding | `api.py` `POST /webhooks/github` | No new route, no FastAPI edit |
| Settings | `ApiSettings.webhook_secret`; `CommonSettings.public_base_url` | Secret API-only; public base stays loopback until a **named** TLS-edge slice actually works |
| Outbox | `store.enqueue` idempotency + `cancel_pr` | Transactional; no new queue |
| Check publisher | worker `GitHubClient` | Checks only; no hooks API |
| App auth | `GitHubAppAuth.installation_token` | Tokens for Checks; never hook config |
| Public edge | nginx on `157.22.187.237` | Historical 405; not Trust CI; do not ProxyPass-fix via this slice |

Compatibility: no OpenAPI/event-schema version bump. Payload meaning under the existing HMAC contract does not change. Duplicate delivery already safe via idempotency; that is not permission to add a second producer.

Retries / ordering: GitHub retries failed deliveries; consumers already tolerate duplicates. Ordering is “latest head SHA wins” via `superseded-head`, not webhook delivery order. Correlation is `job_id` / Check Run `external_id`. Dead-letter is GitHub Recent Deliveries (irrelevant while GitHub does not POST). PII: adapter keeps repo/PR/SHAs/refs only.

---

## 7. What this slice may still do (write owner, not this agent)

In scope for `integration_implementer` if the route requires a tree change at all:

- Durable change-package paperwork that records the freeze and **strikes** the ChatGPT URL as a target.
- Optional characterization test that documents “public ChatGPT URL is out of contract” **without** performing a live HTTP probe (fixture/comment only). Product FastAPI tests already cover HMAC.

Out of scope / forbidden:

- Any edit to `trust-ci/src/adaptive_trust_ci/{api,webhooks,settings,github,github_app}.py`.
- GitHub App or repo webhook registration.
- Re-probe of `https://trust-ci.ii-tonya.ru/webhooks/github` or `https://ii-tonya.ru/webhooks/github`.
- Reading secrets, PEM, JWT.
- Claiming M0.2 complete.
- Merge, push, deploy, branch-protect.

No production writes to GitHub, 1C, Bitrix24, or infra were performed. No API schema change is required or permitted.
