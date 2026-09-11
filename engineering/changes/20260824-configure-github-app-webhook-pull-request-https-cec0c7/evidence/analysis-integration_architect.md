# Integration analysis — GitHub App webhook → `POST /webhooks/github`

Agent: `integration_architect` (read-only). Route `cec0c7622133`.
Change: `engineering/changes/20260824-configure-github-app-webhook-pull-request-https-cec0c7`.

Sources: `trust-ci/src/adaptive_trust_ci/{api.py,webhooks.py,models.py,store.py,settings.py,policy.py}`, `trust-ci/tests/{test_api.py,test_webhooks_github.py}`, `trust-ci/README.md`, GitHub webhook/App docs, sibling TLS-edge diagnosis. No `.env`, PEM, webhook secret, JWT, or production dumps were read. No push, merge, deploy, or GitHub hook create.

## Verdict

**Do not change FastAPI.** A GitHub App webhook POST is the same HMAC adapter as a repository webhook. Configure the App (`adaptive-trust-ci`) only: Active, `https://trust-ci.ii-tonya.ru/webhooks/github` (no trailing slash), secret = API-only `TRUST_CI_WEBHOOK_SECRET` (value never in git), SSL verification Enabled, subscribe **Pull request**.

**Do not create a repository webhook.** Installation ID already exists; a second hook on the same URL double-delivers.

**Ping after HMAC is HTTP 200 `ignored-event`, not 4xx.** The parser requires `X-GitHub-Event: pull_request` for enqueue, but `None` is accepted as ignored. Unsigned POST is **401** HMAC. Public **405 nginx** means the App URL never reached FastAPI.

---

## 1. App POST is the same HMAC path as a repo webhook; ping is 200 after HMAC

Handler (`trust-ci/src/adaptive_trust_ci/api.py` `POST /webhooks/github`):

```text
body = await request.body()                                   # raw bytes
verify_webhook_signature(secret, body, X-Hub-Signature-256)   # HMAC first
event = parse_pull_request_event(X-GitHub-Event, body)        # JSON only after HMAC
if event is None:
    return {"accepted": false, "reason": "ignored-event"}     # HTTP 200
```

HMAC (`webhooks.py` `verify_webhook_signature`): SHA-256 of the **raw body**, UTF-8 secret, header `sha256=` + 64 hex, `hmac.compare_digest`. GitHub App and repository hooks use the same `X-Hub-Signature-256` contract ([Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries); [Using webhooks with GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/using-webhooks-with-github-apps)). App deliveries add `installation` on the JSON and extra headers (`X-GitHub-Hook-Installation-Target-Type: integration`). The API binds only `X-Hub-Signature-256` and `X-GitHub-Event`; extra keys/headers are ignored.

`parse_pull_request_event` (`webhooks.py`):

| `X-GitHub-Event` / body | Result |
| --- | --- |
| anything other than `pull_request` (including `ping`) | `None` **before** `json.loads` |
| `pull_request` + invalid JSON / non-object | `WebhookError` → HTTP **401** |
| `pull_request` + action not in `{opened, synchronize, reopened, ready_for_review, closed}` | `None` |
| `pull_request` + missing `repository` / `pull_request` objects | `WebhookError` → HTTP **401** |
| `pull_request` + malformed SHAs/refs/number | `WebhookError` → HTTP **401** |
| `pull_request` + supported action | `PullRequestEvent` (`closed=True` iff action is `closed`) |

`draft` is unused. Tests: `test_other_events_are_ignored` (`push` → `None`); `test_draft_pull_request_is_enqueued`; `test_synchronize_is_supported`; `test_closed_pull_request_is_parsed_for_cancellation`.

### Ping: accepted after HMAC (200), not 4xx

GitHub sends `X-GitHub-Event: ping` when the App webhook is created or the URL is saved ([ping](https://docs.github.com/en/webhooks/webhook-events-and-payloads#ping); availability includes `app`). With a secret set, ping is HMAC-signed.

1. HMAC passes.
2. `event_name != "pull_request"` → `None` (no JSON parse).
3. Handler returns **HTTP 200** `{"accepted":false,"reason":"ignored-event"}`.

GitHub treats 2xx as a successful delivery. **Do not add a ping route.** A 4xx ping would show as a failed Recent Delivery and GitHub would retry.

Apps also auto-deliver `installation` / `installation_repositories` / `github_app_authorization`. Those are the same 200 ignored-event after HMAC. Harmless. Do not subscribe to Check run / Check suite (worker already publishes Checks; the parser would ignore them anyway).

Unsigned operator ping (no `X-Hub-Signature-256`) never reaches the parser: missing header → `WebhookError("missing or malformed webhook signature")` → **HTTP 401**. That is the HMAC smoke test, not a ping-parser test.

---

## 2. Subscribe only Pull request — enough for enqueue

GitHub App UI: **Subscribe to events → Pull request** (`pull_request`). That is the only event `parse_pull_request_event` consumes. Permissions already implied by the existing Installation ID; this slice is the webhook subscription, not a new App.

| GitHub `action` (under `pull_request`) | Adapter |
| --- | --- |
| `opened` | enqueue `JobRequest` (drafts included) |
| `synchronize` | enqueue (new head SHA; prior in-flight jobs on that PR cancelled `superseded-head`) |
| `reopened` | enqueue |
| `ready_for_review` | enqueue (same identity as a prior draft `opened` → `created: false`) |
| `closed` | `cancel_pr` (`cancelled_jobs`) |
| `edited`, `labeled`, `assigned`, `converted_to_draft`, … | 200 ignored-event |

No `push`, `pull_request_review`, or `check_run` subscription is required for enqueue.

Canonical fields (extra App `installation` / `sender` / top-level `number` ignored):

```text
repository.full_name
pull_request.number
pull_request.head.sha / .ref
pull_request.base.sha / .ref
```

SHAs must be lowercase 40-hex (`JobRequest.require_sha`). Policy `allows_repository` after parse; foreign repo → **403** (HMAC already passed). Kill switch → **503** (no enqueue). Duplicate identity → 200 same `job_id`, `created: false`.

Content type: `application/json`. FastAPI does not read `Content-Type` for this route; HMAC is over raw bytes.

---

## 3. Do not create a repository webhook

User intent: App is registered, Installation ID exists, **no repo hook**.

`GET /repos/{owner}/{repo}/hooks` was empty on the last sibling probe (TLS-edge diagnosis). Creating a repository webhook to the **same** URL would:

- Double-deliver every `pull_request` (`X-GitHub-Delivery` differs; identity `repo+pr+head_sha+pipeline+policy_digest` does not).
- Store `ON CONFLICT (idempotency_key) DO NOTHING` makes the second POST `created: false` (safe, not a second job).
- Still wastes GitHub retries/UI, two secrets to keep in sync, and confuses “which hook produced the Check Run”.
- README still says “Create a repository webhook” — that is a **docs gap**, not a reason to install a second hook. Sibling `analysis-docs_researcher.md`: reword to App webhook after GitHub actually delivers.

Idempotency is the outbox; it is not a license for duplicate producers.

Do not call `POST /repos/.../hooks`. Configure **GitHub App → Webhook** only.

---

## 4. Diagnostics: 401 HMAC vs 405 nginx

| Probe | Meaning |
| --- | --- |
| Unsigned `POST https://trust-ci.ii-tonya.ru/webhooks/github` with `X-GitHub-Event: ping`, body `{}`, **no** signature → **401** `{"detail":"missing or malformed webhook signature"}` | Request hit FastAPI. HMAC fail-closed. TLS + proxy + loopback API are on the path. |
| Same POST → **405** nginx “Not Allowed” | App URL **never** reached FastAPI. Public name is some other HTTP stack (last recorded: nginx/1.24.0 on `157.22.187.237`, not claw Apache → `127.0.0.1:18080`). GitHub Recent Deliveries will fail the same way. |
| GET `/webhooks/github` at FastAPI | FastAPI **405** (only `POST` is declared). Distinguish from nginx 405 by `Server` and JSON vs HTML. |
| Apache `LimitExcept POST` denying GET | Typically **403** at the edge; never HMAC. GitHub only POSTs. |
| Signed ping after a working edge | **200** `ignored-event` (section 1). |
| Signed `pull_request` `opened`/`synchronize` for an allowlisted repo | **200** `accepted`, `job_id`, `status_publisher: worker-github-app`. |
| SSL hostname mismatch with **SSL verification Enabled** | GitHub does not POST; no FastAPI log. Cert SAN must include `trust-ci.ii-tonya.ru` before the App URL is useful. |

Last recorded public-edge fact (sibling `010964` `github-delivery-diagnosis.md`, not re-probed here): unsigned public POST was **405 nginx**, cert not valid for `trust-ci.ii-tonya.ru`, loopback `GET http://127.0.0.1:18080/health/ready` was 200. Live confirmation of the public URL is `repo_explorer` for this change. **Do not save the App webhook as “working” on 405.** Unsigned 401 is the go signal that GitHub can later HMAC-POST.

Register the payload URL **without** a trailing slash. FastAPI `redirect_slashes` would 307 `POST /webhooks/github/` and can drop the body.

---

## Adapter, outbox, reconciliation (no new machinery)

```text
GitHub App (or repo) POST
  → TLS edge (must be FastAPI, not nginx 405)
  → HMAC adapter (raw body + X-Hub-Signature-256)
  → parse_pull_request_event (pull_request only; ping = ignored-event)
  → policy.allows_repository
  → PostgreSQL enqueue / cancel_pr
       idempotency_key = sha256(canonical_json(repo, pr, head_sha, pipeline, policy_digest))
  → HTTP 200
  → worker claim / Check Run / holdout / runner
```

That insert **is** the outbox. Duplicate App deliveries reuse the row. New head SHA supersedes in-flight jobs. `closed` cancels. API has no `GitHubClient`; Checks stay on the worker. Auth split unchanged: API holds webhook secret + human **public** trust store; worker holds App RSA / installation token.

No OpenAPI/event-schema change. `openapi_url=None`. Empty `engineering/contracts/openapi/`. Do not start consuming `X-GitHub-Delivery` or `installation.id` this slice.

---

## Operator mapping (this slice)

| GitHub App field | Value |
| --- | --- |
| Webhooks | Active |
| Webhook URL | `https://trust-ci.ii-tonya.ru/webhooks/github` (no trailing slash) |
| Webhook secret | exact `TRUST_CI_WEBHOOK_SECRET` from gitignored `trust-ci/env/api.env` (do not paste into git, chat, or evidence) |
| SSL verification | Enabled |
| Subscribe to events | **Pull request** only |

Preconditions (edge, not App UI): public POST unsigned must be FastAPI **401**, not nginx **405**; cert SAN must match; API stays `127.0.0.1:18080`. Then GitHub’s signed ping is 200 ignored-event; a disposable `pull_request` enqueue is the M0.2 delivery proof.

No production writes to GitHub, 1C, Bitrix24, or infra were performed. No API schema change is required or permitted.
