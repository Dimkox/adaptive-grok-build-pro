# Integration analysis — GitHub webhook contract vs Apache TLS edge

Agent: `integration_architect` (read-only). Route `01096425a38d`.
Change: `engineering/changes/20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`.
Sources: `trust-ci/src/adaptive_trust_ci/{api.py,webhooks.py,signing.py,store.py,settings.py,cli.py}`, tests, README, M0 spec/plan, sibling probes. No `.env`, PEM, webhook secret, Let’s Encrypt keys, or production dumps were read. No push, merge, deploy, or GitHub webhook registration.

## Verdict

Apache on `:443` is a byte-preserving reverse proxy in front of an already-correct adapter. **Do not change the FastAPI schema.** HMAC for `/webhooks/github` and Ed25519 for `/approvals` stay inside the API. The edge must forward GitHub headers and the raw body, keep `ProxyPreserveHost On`, answer in 25s (under GitHub’s 30s delivery wait), and POST-only the two mutating paths.

Unsigned `POST` with `X-GitHub-Event: ping` **must** be HTTP **401** from FastAPI (missing `X-Hub-Signature-256` fails before JSON). Apache `LimitExcept POST` denying GET is OK. After TLS exists, GitHub *can* POST `https://trust-ci.ii-tonya.ru/webhooks/github`; **registering** that hook is **not this slice**.

---

## 1. Unsigned ping → 401 (HMAC before JSON). GET deny is OK

Handler (`trust-ci/src/adaptive_trust_ci/api.py` `POST /webhooks/github`):

```text
body = await request.body()                          # raw bytes
verify_webhook_signature(secret, body, X-Hub-Signature-256)
parse_pull_request_event(X-GitHub-Event, body)      # JSON only after HMAC
```

`verify_webhook_signature` (`webhooks.py`):

| Input | Error (all become HTTP 401) |
| --- | --- |
| empty secret | `webhook secret is not configured` |
| missing header or no `sha256=` prefix | `missing or malformed webhook signature` |
| hex after prefix ≠ 64 chars | `malformed webhook signature` |
| `hmac.compare_digest` fail | `invalid webhook signature` |

HMAC is SHA-256 of the **raw body** with the UTF-8 secret. `json.loads` runs only inside `parse_pull_request_event`, after a valid MAC.

**Unsigned POST** (`Content-Type: application/json`, `X-GitHub-Event: ping`, body `{}`, no `X-Hub-Signature-256`):

1. Apache proxies POST to `127.0.0.1:18080`.
2. FastAPI reads the body.
3. Signature header is missing → `WebhookError` → **HTTP 401** `{"detail":"missing or malformed webhook signature"}`.
4. JSON is never parsed. `ping` is never interpreted.

That is the TLS-edge smoke test: HTTP 401 + TLS verify 0, **not** 404 / 502 / timeout. 401 proves DNS, cert, proxy, loopback API, and HMAC fail-closed.

**Signed ping** (later, after registration — not this slice): HMAC passes; `event_name != "pull_request"` → `parse_pull_request_event` returns `None` → **HTTP 200** `{"accepted":false,"reason":"ignored-event"}`. GitHub treats 2xx as success. Do not add a ping-specific route.

**`pull_request` vs `ping`:**

| `X-GitHub-Event` | After valid HMAC |
| --- | --- |
| `ping` | 200 ignored-event |
| `pull_request` + `opened`/`synchronize`/`reopened`/`ready_for_review` | enqueue (drafts enqueue; `draft` is unused) |
| `pull_request` + `closed` | `cancel_pr` |
| `pull_request` + other action | 200 ignored-event |
| `push` / anything else | 200 ignored-event |
| invalid JSON on `pull_request` | 401 (`webhook body is not valid JSON`) — still after HMAC |

Allowlist miss → 403. Kill switch → 503 (no enqueue). Duplicate identity → 200 same `job_id`, `created=false`.

**Apache `LimitExcept POST` denying GET is OK.** FastAPI declares only `POST` on `/webhooks/github` and `/approvals`; a GET at the app would be 405. The vhost:

```apache
<Location "/webhooks/github">
    Require all granted
    <LimitExcept POST>
        Require all denied
    </LimitExcept>
</Location>
```

non-POST (GET/HEAD/PUT/DELETE/OPTIONS/PATCH) is typically **403** at Apache and never hits HMAC. GitHub only POSTs. Do not add GET handlers to “match” the edge.

---

## 2. After TLS, GitHub can POST the public URL — registration is NOT this slice

Reachable path once DNS A = claw public IPv4, Apache `:443`, cert valid, API loopback healthy:

```text
GitHub App / repo hook
  → POST https://trust-ci.ii-tonya.ru/webhooks/github
  → Apache :443 (TLS terminate)
  → http://127.0.0.1:18080/webhooks/github
  → FastAPI HMAC + enqueue
```

`compose.yaml` stays `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`. Do **not** publish `0.0.0.0:18080`. Only Apache is external.

**This slice does not register a GitHub hook.** Public HTTPS ≠ installed webhook.

- Plan M0.2 checkbox **Register repo webhook** stays **unchecked / not done**.
- Activation report: first Check Run was a **loopback HMAC POST**, not a GitHub delivery.
- Freeze: `GET .../hooks` empty.
- README rollout: deploy → **then** install webhook → disposable PR → observe App-owned check → **then** branch protection.

HMAC contract is the same for a **repository** webhook and a **GitHub App** webhook URL (`X-Hub-Signature-256` over raw body, secret = `TRUST_CI_WEBHOOK_SECRET` on the API only). Which UI is used later is operator work. Do not call GitHub’s hook API, do not paste the secret, do not check the M0.2 webhook box after Certbot/Apache only.

Sibling `analysis-docs_researcher.md`: `test_m0_invariants` requires the plan to keep `"no public HTTPS"` **or** `"not done"` on the webhook line.

---

## 3. Headers to forward, Host, timeout

GitHub delivery headers (docs: webhook events and payloads): `X-GitHub-Event`, `X-GitHub-Delivery`, `X-Hub-Signature-256` (when a secret is set), `Content-Type`, plus optional `X-Hub-Signature` (SHA-1, unused), hook/installation IDs, `User-Agent`.

**Must reach FastAPI unchanged:**

| Header | Why |
| --- | --- |
| `X-Hub-Signature-256` | HMAC gate. FastAPI binds `Header` → `x_hub_signature_256`. Missing → 401. |
| `X-GitHub-Event` | Distinguishes `ping` vs `pull_request`. Bound as `x_github_event`. |
| `X-GitHub-Delivery` | GUID. API does **not** consume it (idempotency is repo+PR+SHA+pipeline+policy). Apache `trustci` log format uses `%{X-GitHub-Delivery}i`. Forward for correlation; do not strip. |
| `Content-Type` | GitHub `application/json`. Body HMAC is independent of this header; keep it. |

`mod_proxy_http` forwards these (not hop-by-hop). Do **not** `RequestHeader unset` them. GitHub names use hyphens, so Apache `underscores_in_headers` is irrelevant.

**Body:** HMAC is over exact bytes. Proxy must not transcode, pretty-print, or rewrite JSON. Default `mod_proxy_http` buffering is fine. `retry=0` on ProxyPass: do not retry POST (GitHub already retries failed deliveries; API enqueue is idempotent).

**`ProxyPreserveHost On`:** backend `Host` is `trust-ci.ii-tonya.ru`, not `127.0.0.1:18080`. HMAC does not include Host. `TRUST_CI_PUBLIC_BASE_URL` (env) builds Check Run `details_url`, not the Host header. After this slice that env becomes `https://trust-ci.ii-tonya.ru` (HTTPS outside localhost is already required by `CommonSettings`). Keep `ProxyPreserveHost On` as specified.

**Timeout 25 < GitHub 30s:**

| Layer | Budget |
| --- | --- |
| GitHub delivery wait (operator brief / GitHub “respond before 30s”) | 30s |
| Apache `ProxyTimeout` + `ProxyPass … timeout=25` | **25s** |
| `connectiontimeout=3` | fail fast if API is down (502, not hang) |
| Webhook handler | HMAC + parse + SQL enqueue; worker publishes Check Runs asynchronously |

If the handler exceeded 25s, Apache would 504 before GitHub’s 30s wait. GitHub troubleshooting also documents a **10s** “timed out” class; enqueue-only already returns in milliseconds, so both 10s and 30s are satisfied. Do not do Checks API work in the webhook process (already true: API has no `GitHubClient`).

Register the payload URL **without** a trailing slash. FastAPI `redirect_slashes` would 307 `POST /webhooks/github/` → `/webhooks/github` and can drop/alter the body. Proposed vhost paths have no trailing slash.

`LimitRequestBody 10485760` (10 MiB): GitHub allows larger payloads; PR events are small. 413 is fail-closed, not a schema change.

`RequestHeader unset Proxy early` (HTTPoxy), `X-Forwarded-Proto https`, `X-Forwarded-Port 443`, `ProxyRequests Off`: keep. Extra forwarded headers do not affect HMAC.

---

## 4. `/approvals` is Ed25519, not HMAC; still POST only

`POST /approvals` (`api.py`): **no** `X-Hub-Signature-256`. Human workstation → `https://trust-ci.ii-tonya.ru/approvals` → Apache → `http://127.0.0.1:18080/approvals`.

| Step | Result |
| --- | --- |
| kill switch | 503 |
| `request.json()` / `ApprovalEnvelope.from_dict` fail | 400 malformed envelope |
| scope not in policy | 400 |
| no job for exact SHA | 404 |
| `verify_approval` (Ed25519, actor/scope/TTL/exact SHAs/policy digest) | 403 |
| `record_approval` unique `(approval_id, nonce)` | 409 `ReplayError` |
| success | 200 `accepted`, `approval_id`, `requeued_jobs` |

Signature is Ed25519 over **canonical JSON** of the payload (`signing.py`), not HMAC of raw bytes. CLI `approval-submit` POSTs the envelope with `Content-Type: application/json` (urllib timeout 30s). Apache 25s is still the proxy cap.

Same `<LimitExcept POST>` as the webhook: GET denied at Apache; FastAPI has no GET. Do not put a webhook secret on this path. Trust store is API-only public keys; human private keys stay off claw.

---

## 5. Do not change the API schema

This slice is host Apache + DNS + cert + `TRUST_CI_PUBLIC_BASE_URL`. **No FastAPI/OpenAPI/event-schema edits.**

Leave unchanged:

- Paths and methods: `POST /webhooks/github`, `POST /approvals`, `GET /health/{live,ready}`, `GET /jobs/{id}`, `GET /attestations/{id}`, `GET /metrics`
- HMAC-before-JSON; 401 on bad/missing MAC (including unsigned ping)
- 200 `ignored-event` for non-`pull_request` after valid HMAC
- Enqueue / cancel / idempotency JSON (`accepted`, `created`, `job_id`, `status`, `status_publisher`)
- Approval JSON (`accepted`, `approval_id`, `scope`, `requeued_jobs`)
- Status mapping: 401 HMAC, 403 repo/signature, 409 replay, 400 envelope, 404 missing job, 503 kill switch
- `openapi_url=None`; empty `engineering/contracts/openapi/`
- No GET on webhook/approvals; no ping-specific success before HMAC; do not start consuming `X-GitHub-Delivery` in Python this slice

Apache may 403 GET; that is edge policy, not an API change.

---

## Adapter, outbox, reconciliation (no new machinery)

Existing anti-corruption layer is enough:

```text
GitHub event (untrusted)
  → HMAC adapter (raw body + X-Hub-Signature-256)
  → canonical JobRequest (exact 40-hex SHAs)
  → PostgreSQL enqueue (idempotency_key = sha256(repo, pr, head, pipeline, policy_digest))
  → HTTP 200
  → worker claim / Check Run / holdout / runner
```

That insert **is** the outbox. Duplicate GitHub deliveries reuse the row (`created=false`). New head SHA supersedes in-flight jobs. `closed` cancels. Approvals bind exact SHA + policy digest + nonce; replay is unique-constraint 409. Proxy `retry=0` avoids a second POST on timeout.

Reconciliation remains worker poll + lease expiry + `cancel_pr`. The TLS edge does not add a second queue.

Auth split (unchanged): API holds webhook secret + human **public** trust store; worker holds App RSA / installation token; runner holds none. Apache holds only the TLS private key (Let’s Encrypt, not in git).

---

## Edge contract checklist (implementer)

| Requirement | Action |
| --- | --- |
| Unsigned POST ping | Expect **401**, not 404/502/timeout |
| GET `/webhooks/github` or `/approvals` | Apache deny (`LimitExcept POST`) OK |
| Header forward | `X-Hub-Signature-256`, `X-GitHub-Event`, `X-GitHub-Delivery`, `Content-Type`; raw body |
| `ProxyPreserveHost` | **On** |
| Timeouts | 25s proxy < 30s GitHub; `connectiontimeout=3`; `retry=0` |
| API bind | keep `127.0.0.1:18080:8080` |
| Webhook registration | **out of scope** — leave M0.2 checkbox not done |
| `/approvals` | POST JSON Ed25519; no HMAC |
| Schema | **do not change** FastAPI routes, status codes, or bodies |
| Secrets | do not read/print webhook secret, PEM, LE privkey, read token |

## Residual (not schema)

- DNS A must point at claw public IPv4 before GitHub can connect (sibling repo_explorer: A currently ≠ claw). That is DNS, not hook registration.
- Signed GitHub ping after a later registration should 200 `ignored-event` so GitHub does not retry; the **unsigned** operator curl stays 401.
- `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru` after recreate; Check Run `details_url` then uses `/jobs/{id}` (bearer still required).

No production writes to GitHub, 1C, Bitrix24, or infra were performed. No API schema change is required or permitted in this slice.
