# Release review — Configure GitHub App webhook `pull_request` HTTPS

Reviewer: `release_reviewer` (read-only except this report). Write owner: **none**.
Change: `engineering/changes/20260824-configure-github-app-webhook-pull-request-https-cec0c7`
Route: `cec0c7622133` · intent=`review` · risk=`high` · complexity=`high-risk`
Skills: `/adaptive-delivery`, `release-readiness`, `verification-evidence`, `api-event-change`, `security-sensitive-change`.

Assigned: go/no-go of rollback, observability, and remaining risk. **NO-GO** for claiming the GitHub App webhook is live. **GO** for the operator App-settings UI as the only configuration path. **NO-GO** merge, tag, GitHub Release, protect `main`, repository webhook, App JWT/`PATCH /app/hook/config`.

Fetched: 2026-08-24T13:50Z on host `claw`. Did not read `.env`, `trust-ci/env/api.env`, PEM, webhook secret, JWT, or production dumps. Did not mint a JWT. Did not `GET`/`PATCH /app/hook/config`. Did not `POST /repos/.../hooks`. Did not push, merge, tag, deploy, or protect `main`. Did not run `grok_review.py` (parent records receipts).

**PASS** as an honest **stop** on live delivery. **GO** to the operator UI path. **NO-GO** as a live App webhook, as M0.2 complete, as merge/tag.

| Check (assigned) | Result |
| --- | --- |
| Claim App webhook live / GitHub delivers signed `pull_request` to FastAPI | **NO-GO** — TLS hostname mismatch; public POST is nginx **405**, not FastAPI **401** |
| Operator UI path (`https://github.com/settings/apps/adaptive-trust-ci`) | **GO** — JWT/PEM forbidden; user token cannot PATCH `/app/hook/config`; do not substitute a repo hook |
| Repository webhook | **NO-GO** — `GET …/hooks` length **0**; keep empty |
| `insecure_ssl=1` / SSL verification Disabled | **NO-GO** |
| Merge / tag / GitHub Release / VERSION bump / protect `main` | **NO-GO** |
| Rollback of this slice | **PASS** — nothing GitHub-side was mutated by this route; UI deactivate is the rollback if the operator later saves |
| Observability of *live* App deliveries | **FAIL** — no GitHub Recent Delivery proof; public edge is not Trust CI |
| Observability plan for the operator UI path | **PASS** — unsigned FastAPI 401 + signed ping 200 `ignored-event` + disposable `pull_request` 200 `accepted` |
| This reviewer push/merge/deploy/hook/protect | **NO-GO** |

## Verdict

| Gate | Result |
| --- | --- |
| Identity surfaces | **PASS.** Product `VERSION` / README H1 remain **2.0.12**. Trust CI `__version__` remains **2.1.0**. No identity, tag, or GitHub Release in this slice. |
| Product tree | **PASS / empty.** `git diff --stat HEAD -- trust-ci README.md VERSION CHANGELOG.md` is empty. This package is untracked paperwork only. `HEAD` `92ddbd9f69c5c560f257fd61fa9c902f43f67e50` (`milestone/m0-live-trust-authority`). `tag --points-at HEAD` empty. |
| M0.2 live authority | **NO-GO.** Plan still: register webhook **not done** (no public HTTPS). Disposable Check Run is **local HMAC**. `main` unprotected. Activation report `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`. |
| App webhook live | **NO-GO.** App hook Active / URL / secret / `pull_request` **unverified**. Public name does not reach FastAPI. |
| Operator UI path | **GO.** Exclusive allowed config surface. Fields: Active; URL `https://trust-ci.ii-tonya.ru/webhooks/github` (no trailing slash); secret = host `TRUST_CI_WEBHOOK_SECRET` (operator pastes; agent never prints); SSL Enabled; Subscribe **Pull request**. |
| Saving the App form *now* and treating Recent Deliveries as success | **NO-GO** until unsigned public POST is FastAPI **401** and the cert SAN includes `trust-ci.ii-tonya.ru`. Saving earlier yields SSL error and/or nginx 405. UI Active ≠ delivery. |
| Loopback API | **PASS.** `GET http://127.0.0.1:18080/health/ready` → 200 uvicorn `status=ready`, `policy_digest=6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5`, `status_publisher=worker-github-app`. Compose still `127.0.0.1:18080:8080`. |
| Rollback | **PASS** for this slice (no GitHub mutation). If the operator later saves the form: uncheck **Active** (optional clear URL). Do not add a repo hook. Do not `compose down -v`. Do not force-push. |
| Named human gate | **Open.** `scope_and_design_approval` is on the route. This report is not that gate. Operator owns the App form and TLS/vhost. |
| Product mutation by this agent | **PASS / empty.** Wrote only this report. |

## 1. What this slice is (and is not)

User order: App `adaptive-trust-ci` is already registered and installed (activation report: App ID `4694114`, Installation ID `156003193`). Do **not** create a repository webhook. Configure the **GitHub App** webhook: Active, URL `https://trust-ci.ii-tonya.ru/webhooks/github`, secret = `TRUST_CI_WEBHOOK_SECRET`, SSL Enabled, event **Pull request**.

`write_agent: null`. No FastAPI, worker, compose, holdout, or test edits belong to this route. Intake contract is already channel-agnostic (`POST /webhooks/github` HMAC then `parse_pull_request_event`). Registration is GitHub-side operator configuration.

Architect ruling (this package): `PATCH /app/hook/config` requires a GitHub App JWT. Reading the App PEM is forbidden. A user token and an installation token cannot call `/app/hook/*`. Do not mint a JWT. Do not create a repo hook as a substitute.

This reviewer independently confirmed public-edge facts (proxy bypass, no secrets):

| Probe (2026-08-24T13:50Z, `claw`, `NO_PROXY=*`) | Result |
| --- | --- |
| DNS A `trust-ci.ii-tonya.ru` | `157.22.187.237` |
| Presented cert | Let’s Encrypt; **CN=`ii-tonya.ru`**; SAN=`ii-tonya.ru`, `www.ii-tonya.ru`. **Not** `trust-ci.ii-tonya.ru` |
| `GET https://trust-ci.ii-tonya.ru/health/ready` verify-on | **SSL hostname mismatch** |
| same, verify-off | **HTTP 200** `Server: nginx/1.24.0 (Ubuntu)` JSON `checks.postgres/migrations/workerLease/adapters` — **not** Trust CI (`policy_digest` absent) |
| Unsigned `POST https://…/webhooks/github` (`X-GitHub-Event: ping`, body `{}`, no signature) verify-on | **SSL hostname mismatch** |
| same, verify-off | **HTTP 405** nginx HTML «Not Allowed» — **not** FastAPI JSON **401** |
| Loopback `GET http://127.0.0.1:18080/health/ready` | **200** uvicorn Trust CI ready |

Public GitHub cannot TLS-verify this hostname, and even with verification skipped the path is nginx, not `127.0.0.1:18080`. Claiming the App webhook is live is false.

## 2. Why this is not a live webhook and not M0.2

Plan `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` M0.2:

- `[ ] Register repo webhook …` — **not done** (no public HTTPS). After a **successful GitHub delivery**, reword to **App webhook**. Do not tick it from UI Active.
- Disposable Check Run — **partial:** local HMAC only (`97390635614` / `97406973020`). Not M0.2 complete.
- `[ ] Do not protect main`

Activation report still: `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`; first Check Run = loopback HMAC, **not** a GitHub-registered hook; `main` protected = false.

`test_m0_invariants.test_activation_report_operator_safe` requires `"local HMAC"` and (`"no public HTTPS"` **or** `"not done"`). **Do not** drop those phrases or mark the webhook complete without GitHub delivery.

Go-live (all required; **none** currently true):

1. Public cert SAN includes `trust-ci.ii-tonya.ru`; verify-on `/health/ready` is Trust CI 200 (`policy_digest` present), not nginx app JSON.
2. Unsigned public `POST /webhooks/github` → FastAPI **401** `missing or malformed webhook signature` (JSON, not nginx HTML 405).
3. Operator has saved App webhook Active + URL + secret + SSL Enabled + **Pull request**.
4. GitHub Recent Deliveries: signed `ping` HTTP **200** `{"accepted":false,"reason":"ignored-event"}`.
5. Disposable `pull_request` (`opened`/`synchronize`, drafts included) → HTTP **200** `accepted: true` + `job_id` + App-owned Check Run on the exact head SHA.
6. `GET repos/Dimkox/adaptive-grok-build-pro/hooks` still length **0**.

Until then: **NO-GO** live. Loopback HMAC is not this slice.

## 3. GO — operator UI path (not agent API)

The correct configuration surface is the App registration page, not a repository hook and not this agent.

| Field | Required value |
| --- | --- |
| Webhooks | Active |
| Webhook URL | `https://trust-ci.ii-tonya.ru/webhooks/github` (no trailing slash; FastAPI `redirect_slashes` can 307 and drop POST body) |
| Webhook secret | exact bytes of API `TRUST_CI_WEBHOOK_SECRET` from gitignored `trust-ci/env/api.env` (operator reads on host; **never** paste into git, chat, or this package) |
| SSL verification | **Enabled** / API `insecure_ssl="0"` |
| Content type | `application/json` |
| Subscribe to events | **Pull request** only (`PATCH /app/hook/config` does not subscribe events) |

Operator URL: `https://github.com/settings/apps/adaptive-trust-ci` (or the org-owned equivalent). Sidebar **Permissions & events** for the subscription; Webhook section for URL/secret/SSL.

**Allowed:** human fills that form after (or in parallel with, accepting failed pings) TLS SAN + ProxyPass so unsigned POST is FastAPI 401.

**Forbidden (still):**

- Agent reads PEM / mints JWT / calls `/app/hook/config` or `/app/hook/deliveries*`.
- `POST /repos/.../hooks` (double-delivers; two secrets; contradicts user order).
- `insecure_ssl=1` to paper over the parent-domain cert.
- Print/log/commit `TRUST_CI_WEBHOOK_SECRET`.
- Claim M0.2 complete from UI Active or from loopback HMAC.
- Protect `main`, merge, tag, or GitHub Release.

README/spec/plan still say “Create a **repository** webhook”. That is a **docs gap after successful delivery**, not a reason to install a second hook now.

## 4. Rollback

Package `rollback.md` is still a template (empty headings). Adequacy for this slice does **not** depend on filling it: this route mutated no GitHub hook, no env URL, no compose, no TLS.

### Now (no App hook mutation by this route)

1. Do nothing on GitHub. Repo hooks stay empty. App form is operator-owned and unverified.
2. Do **not** sed `TRUST_CI_PUBLIC_BASE_URL` — still loopback HTTP (correct).
3. Do **not** `compose down -v` / recreate postgres.
4. Do **not** `a2dissite` as *this* rollback (that belongs to the TLS-edge slice `010964`).
5. Verify: loopback `/health/ready` 200; `GET …/hooks` length 0.

### If the operator later saves the App form

Trigger: abort, wrong URL/secret, SSL disabled, accidental extra events, or deliveries failing while the public edge is still nginx.

1. GitHub App settings → Webhook → uncheck **Active** → Save. Optional: clear URL if abandoning the hostname.
2. Do **not** set SSL verification Disabled.
3. Do **not** create a repository webhook “to recover”.
4. If the secret was rotated in the UI only: GitHub 401s until API `TRUST_CI_WEBHOOK_SECRET` matches. Operator restores both sides in one window. Agent does not retrieve the value.
5. Failed Recent Deliveries may retry until Active is off; deactivating stops new attempts.
6. Product code unchanged — no application rollback, no data recovery, no forward-fix in-tree.
7. Verify after rollback: no new Check Runs from GitHub deliveries; loopback ready still 200; local HMAC path (if used) still independent.

Rollback does **not** unprotect `main` (unprotected). It does **not** revert a tag (none). It does **not** unregister a repo hook (none).

## 5. Observability

FastAPI `/metrics` (`adaptive_trust_ci_jobs{status=…}`, queue age, kill switch, policy epoch) is **job-queue** telemetry. There is **no** webhook-delivery / HMAC-401 / ignored-event Prometheus series. Public `/metrics` is not on the internet (no ProxyPass). Bearer-gated even on loopback. Do not treat `/metrics` as GitHub delivery proof.

| Signal | Expected for live App webhook | Observed now |
| --- | --- | --- |
| Loopback `/health/ready` | 200 Trust CI `ready` | **200** |
| Public `/health/ready` verify-on | 200 Trust CI, cert SAN match | **SSL hostname mismatch** |
| Public `/health/ready` verify-off | Trust CI JSON (`policy_digest`) | **nginx 200** other app JSON |
| Unsigned public POST webhook | FastAPI **401** | nginx **405** HTML |
| GitHub App Recent Deliveries | signed `ping` 200 `ignored-event`; `pull_request` 200 `accepted` | **Unverified** (JWT forbidden; public edge would fail SSL or 405) |
| Repo `/hooks` | empty | **empty** (peer security review + analysis) |
| App-owned Check Run from *public* delivery | present on disposable PR head | **absent** (local HMAC only) |
| `TRUST_CI_PUBLIC_BASE_URL` | `https://trust-ci.ii-tonya.ru` only after public ready 200 | loopback HTTP |
| Plan webhook line | still **not done** / **no public HTTPS** | **held** |
| `main` protected | false until M0.3 | **false** |
| Compose publish | `127.0.0.1:18080` | **held** |

Operator UI observability after a future valid edge:

1. Save App webhook → GitHub sends HMAC-signed `ping`. FastAPI returns 200 `ignored-event` (not 4xx — a 4xx ping would show as failed delivery and retry).
2. Open/synchronize disposable PR #5 (drafts enqueue; do not filter `draft`).
3. Confirm 200 `accepted` + `job_id` + worker Check Run `adaptive-trust-ci/verified@6737355947c2` on the exact head SHA, `external_id=job_id`.
4. Mismatch secret → GitHub 401; SSL still wrong → GitHub SSL error, no FastAPI log; nginx still in front → 405.

Support visibility for this stop is analysis reports + this review. Apache `trust-ci-*.log` (sibling TLS slice) only sees Host-header local probes; public name never hits claw Apache.

## 6. Remaining risk (do not expand scope)

1. **Public edge is the wrong stack.** A `157.22.187.237` nginx serves a different `/health/ready`. GitHub SSL-enabled POSTs will not reach FastAPI until DNS/inbound 80/443 + cert SAN `trust-ci.ii-tonya.ru` + ProxyPass to `127.0.0.1:18080`. That is the TLS-edge slice (`010964`), not this GO.
2. **Saving the App form against today’s edge** produces failed Recent Deliveries (SSL error, then 405). Allowed only if the operator accepts that as noise. **Not** proof of live. Do not lower SSL verification to make the log green.
3. **Secret equality unverified.** Agent must not open `api.env`. Operator pastes. Rotate both sides together if needed.
4. **App hook state unverified.** No JWT → no `GET /app/hook/config`. Do not infer Active/events from Installation ID.
5. **Docs still say repository webhook.** Reword only after GitHub actually delivers. Keep `test_m0_invariants` phrases until then.
6. **Double-producer risk** if anyone later adds a repo hook to the same URL. Idempotency prevents a second job; it still splits secrets and confuses Check Run provenance. Keep `/hooks` empty.
7. **No merge / tag / protect.** `main` is unprotected. A merge would skip the still-absent public App-owned check. Do not reuse bootstrap exceptions.
8. **Package templates.** `change-spec.yaml`, `release.md`, `rollback.md`, `test-plan.md` are stubs. Acceptable for no-code operator-config; not a product contract. Not a no-go for the UI-path GO.
9. **`scope_and_design_approval` still named.** Analysis is the design, not execution. Operator owns cert + App form.
10. **No webhook-specific metrics/alerts.** Go-live relies on GitHub Recent Deliveries + unsigned 401 + job enqueue. Residual: silent 405/SSL if nobody watches the App delivery log.
11. **Trailing slash / body processors.** Register URL without `/`. Before a future HTTPS vhost, isolate Apache `deflate`/`substitute` if they would rewrite HMAC bytes (sibling architect residual).
12. **Local receipts are not merge authority.** Parent may record `release_review` after this file; that does not create `adaptive-trust-ci/verified@6737355947c2`.
13. **Untracked leftovers.** Other change packages. Fail-closed on `git add -A`. Never commit `trust-ci/env/*.env` or PEMs.
14. **Extra subscribed events** (`push`, `check_run`, all events) would HMAC-pass and 200 ignore. Harmless but noisy. Subscribe **Pull request** only.

## 7. GO / NO-GO

| Act | Decision |
| --- | --- |
| Operator (human) configures GitHub App `adaptive-trust-ci` webhook via **settings UI** with Active, URL `https://trust-ci.ii-tonya.ru/webhooks/github`, secret from host `TRUST_CI_WEBHOOK_SECRET`, SSL Enabled, event **Pull request** | **GO** (path only; not a live claim) |
| Treat UI Active / loopback HMAC / this receipt as “App webhook live” or M0.2 complete | **NO-GO** |
| Update activation-report `TRUST_CI_PUBLIC_BASE_URL` to `https://trust-ci.ii-tonya.ru` before public TLS + unsigned 401 | **NO-GO** |
| Tick M0.2 “Register repo webhook” / drop “no public HTTPS” without leaving “not done” | **NO-GO** |
| `PATCH /app/hook/config` / mint App JWT / read PEM | **NO-GO** |
| `POST /repos/.../hooks` / UI repository webhook | **NO-GO** |
| SSL verification Disabled / `insecure_ssl=1` | **NO-GO** |
| Merge / mark PR ready / push `main` | **NO-GO** |
| Tag / GitHub Release / VERSION bump | **NO-GO** |
| Protect `main` / `adaptive-trust-ci branch-protect` | **NO-GO** |
| Publish API `0.0.0.0:18080` | **NO-GO** |
| `compose down -v` / recreate postgres | **NO-GO** |
| Commit `env/*.env` or PEMs / print webhook secret | **NO-GO** |
| This reviewer executing UI save, push, or deploy | **NO-GO** |
| After unsigned public **401** + cert SAN match: operator save → ping 200 `ignored-event` → disposable `pull_request` enqueue | **deferred** — live proof; not this GO |

Parent sequence after this review (controller/human; **not** this agent): keep repo hooks empty; do not merge/tag; operator may open the App settings UI; do not claim delivery until the go-live table in §2 is all true. TLS/ProxyPass remains the blocking host slice.

## Peer reviews (same tree)

| Review | On disk | Verdict |
| --- | --- | --- |
| `evidence/code-review.md` | yes | **pass** — no product edits; JWT/PEM refused; repo hooks empty |
| `evidence/test-review.md` | yes | **pass** — `test_m0_invariants` 8 OK; no new tests required (no code change); not live-webhook proof |
| `evidence/security-review.md` | yes | **pass** — secret/PEM unread; SSL stays Enabled; no repo hook; live delivery still residual |

This PASS is independent of those receipts. It does not substitute them. It is not merge authority.

## What this review is not

- Not merge authority and not a Trust CI Check Run.
- Not a security review (peer already wrote one).
- Not `grok_review.py` receipt recording.
- Not host DNS mutation, Certbot, App form save, branch-protect, tag, or GitHub Release.
- Did not read `.env` or PEM bodies. Did not push, merge, or deploy.

## Stop

**PASS** as an honest stop on live delivery.

- **GO:** operator UI path on `https://github.com/settings/apps/adaptive-trust-ci` (Active, HTTPS URL, secret from host env, SSL Enabled, Pull request). No repository webhook.
- **NO-GO:** claiming the App webhook is live, M0.2 complete, merge, tag, GitHub Release, protect `main`, JWT/PEM, `insecure_ssl=1`.
- Rollback: nothing GitHub-side landed this route; if the operator later saves, uncheck Active. Never force-push / `compose down -v` / add a repo hook.
- Observability: loopback ready 200; public name SSL mismatch + nginx 405; live proof remains unsigned FastAPI 401 then GitHub ping/`pull_request` Recent Deliveries.
