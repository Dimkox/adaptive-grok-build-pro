# Release review — M0.2 public TLS edge (DNS-blocked; HTTP vhost only)

Reviewer: `release_reviewer` (read-only except this report). Write owner: `frontend_implementer` (route; host Apache was applied by the parent after a stale lock).
Change: `engineering/changes/20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`
Route: `01096425a38d` · intent=`feature` · risk=`high` · complexity=`high-risk`
Skills: `/adaptive-delivery`, `release-readiness`, `feature-workflow`, `api-event-change`, `data-change`, `enterprise-integration`, `frontend-change`, `security-sensitive-change`.

Assigned: go/no-go of rollback, observability, and remaining risk for the Apache TLS-edge slice on `trust-ci.ii-tonya.ru`. **GO only for remaining local docs.** **NO-GO** for treating this as M0.2 complete or as a live public webhook. No merge, no tag, no GitHub webhook registration, no `main` protect.

Fetched: 2026-08-24T13:33Z on host `claw`. Did not read `.env`, PEM, webhook secret, App RSA, Let’s Encrypt keys, or production dumps. Did not push, merge, tag, deploy, register a GitHub hook, or protect `main`. Did not run `grok_review.py` (parent records receipts).

**PASS** as an honest **stop** (Apache HTTP ACME vhost on claw; Certbot/HTTPS/ProxyPass/env URL not applied). **GO** to keep writing operator-safe local docs that record that stop. **NO-GO** as a public TLS edge, as M0.2 exit, as a registered webhook, as merge/tag/protect.

| Check (assigned) | Result |
| --- | --- |
| TLS edge complete (DNS A = claw inbound, LE cert, HTTPS ProxyPass, public `/health/ready` 200) | **FAIL / NO-GO** — A `157.22.187.237` ≠ claw; public name is nginx, not this Apache |
| Unsigned `POST https://trust-ci.ii-tonya.ru/webhooks/github` → HTTP 401 + `TLS_VERIFY=0` | **FAIL / NO-GO** — TLS hostname mismatch; FastAPI never reached |
| Public GitHub webhook live / register hook | **NO-GO** — out of slice; `GET …/hooks` not this work; plan stays **not done** |
| Treat slice as M0.2 complete | **NO-GO** |
| Merge / tag / GitHub Release / VERSION / protect `main` | **NO-GO** |
| Rollback of what actually landed | **PASS** — `a2dissite trust-ci.conf` (+ reload); env/URL never changed |
| Observability of the *public* edge | **FAIL** — no public HTTPS SLI; loopback ready still 200 |
| Remaining local docs (honest DNS stop; webhook still not done; loopback URL until HTTPS exists) | **GO** |
| This reviewer push/merge/deploy/webhook/protect | **NO-GO** |

## Verdict

| Gate | Result |
| --- | --- |
| Identity surfaces | **PASS.** Product `VERSION` / README H1 / CHANGELOG top remain **2.0.12**. Trust CI `pyproject.toml` / `__version__` remain **2.1.0**. No identity, tag, or GitHub Release in this slice. |
| M0.2 live authority | **NO-GO.** Spec/plan still: no public HTTPS webhook; disposable Check Run is **local HMAC** only; `main` unprotected. Public HTTPS is not live. |
| Scope honesty | **PASS.** `evidence/implementation.md` lists LE cert, HTTPS vhost, public URL env, unsigned 401 as **not done**. Peer code/test/data reviews agree. |
| P0 acceptance (`requirements.md`) | **FAIL** against the *intended* TLS edge. DNS A, public ready 200, unsigned 401, `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru`, certbot dry-run are all unmet. Correct operational response is **stop**, not force Certbot. |
| Loopback API + catalog | **PASS.** `GET http://127.0.0.1:18080/health/ready` → 200 `status=ready`. Compose publish still `127.0.0.1:18080->8080/tcp`. Postgres container/volume not recreated. |
| Rollback | **PASS** for the landed HTTP vhost: `sudo a2dissite trust-ci.conf && sudo systemctl reload apache2`. Full-slice env revert + `api`/`worker` recreate are **not needed yet** (URL never switched). Never `compose down -v`. |
| Observability | **PASS** for loopback; **FAIL** for the public edge. Apache `trust-ci-*.log` only sees Host-header local probes. Public name answers on another host. |
| Remaining local docs | **GO.** Keep plan webhook **not done** / **no public HTTPS**. Keep activation-report `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080` until HTTPS is real. Do not commit `env/*.env` or LE keys. |
| Product mutation by this agent | **PASS / empty.** Wrote only this report. |

## 1. What actually landed (this host, this turn)

`HEAD` `92ddbd9f69c5c560f257fd61fa9c902f43f67e50` (`milestone/m0-live-trust-authority`, message `ops: record M0.2 backup restore restart drill on claw`). Tracked product code for Trust CI compose/API is unchanged in this working tree. Host Apache is **not** in git (expected).

| Plane | Live fact |
| --- | --- |
| Host | `claw`, LAN `192.168.0.229` via `192.168.0.1` |
| Egress IPv4 (`ifconfig.me`) | `91.197.106.11` (implementation.md also saw `45.85.105.28` earlier — NAT/egress is not a stable inbound target by itself) |
| DNS A `trust-ci.ii-tonya.ru` | **`157.22.187.237`** (apex `ii-tonya.ru` answers HTTP 200) |
| DNS AAAA | empty (correct; do not create AAAA) |
| Apache | `active` `enabled`. Sites: `000-default.conf`, `trust-ci.conf`. Modules include `ssl proxy proxy_http headers rewrite` **and** `deflate`. |
| `trust-ci.conf` | HTTP `*:80` ACME DocumentRoot only. **No** `*:443` vhost, **no** ProxyPass. |
| Listeners | `*:80`, `*:443`, `127.0.0.1:18080` (API), `127.0.0.1:8080` (SearXNG) |
| Local `Host: trust-ci.ii-tonya.ru` `GET /` | **403** (empty indexes; runbook-acceptable) |
| Local `GET /health/ready` on that vhost | **404** (no proxy yet) |
| Local `https://127.0.0.1/` | `SSL: WRONG_VERSION_NUMBER` — 443 is open because `ssl` is loaded / `Listen 443`, but no SSLEngine site |
| Default site `GET http://127.0.0.1/` Host `localhost` | **200** `Apache/2.4.58` |
| Let’s Encrypt live dir | **absent** |
| `TRUST_CI_PUBLIC_BASE_URL` (key only) | `http://127.0.0.1:18080` |
| Compose | `api` healthy `127.0.0.1:18080->8080/tcp`; `worker` Up ~4h; `postgres` healthy; overlay untouched |
| Loopback ready | `{"status":"ready",...,"status_publisher":"worker-github-app"}` |

Public name does **not** reach this Apache:

| Probe | Result |
| --- | --- |
| `curl -I http://trust-ci.ii-tonya.ru/` | **301** `Server: nginx/1.24.0 (Ubuntu)` → `https://trust-ci.ii-tonya.ru/` |
| `https://trust-ci.ii-tonya.ru/health/ready` | `CERTIFICATE_VERIFY_FAILED` hostname mismatch (cert not valid for `trust-ci.ii-tonya.ru`) |
| Unsigned `POST https://…/webhooks/github` | same TLS error — **not** FastAPI 401 |

That is the release blocker. HTTP-01 / GitHub deliveries would hit the FirstVDS nginx at `157.22.187.237`, not claw. `requirements.md` stop rule (“DNS A still not this host → do not force certbot”) was followed. Correct.

## 2. Why this is not M0.2 and not a live webhook

Plan `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` M0.2:

- `[ ] Register repo webhook …` — **not done** (no public HTTPS)
- Disposable Check Run — **partial:** local HMAC only. **Not M0.2 complete.**
- `[ ] Do not protect main`

Activation report still: `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`; first Check Run = loopback HMAC, not a GitHub-registered hook; `main` protected = false.

`test_m0_invariants.test_activation_report_operator_safe` requires `"local HMAC"` and (`"no public HTTPS"` **or** `"not done"`). **Do not** tick the webhook box or drop both phrases to make docs look greener.

Public HTTPS ≠ registered webhook even *after* Certbot. This slice never included `gh api …/hooks`. Today there is not even public HTTPS.

## 3. Rollback — adequate for the landed vhost

Authority: change-package `rollback.md` + architect §6. Trigger: abort, wrong site, or operator wants 80/443 free again.

### Now (HTTP vhost only; this is the live rollback)

1. `sudo a2dissite trust-ci.conf && sudo apache2ctl configtest && sudo systemctl reload apache2`
2. Do **not** sed `TRUST_CI_PUBLIC_BASE_URL` — it is still loopback HTTP.
3. Do **not** `docker compose … --force-recreate api worker` for rollback — those containers were not recreated for a public URL.
4. Leave postgres volume. **Never** `compose down -v`.
5. No Let’s Encrypt files to delete (none exist). Do not `cat` PEMs if they appear later.
6. Optional: if this Apache install exists only for Trust CI and the operator wants ports free, `sudo systemctl stop apache2` is allowed. Do not uninstall in panic. `000-default` currently serves Ubuntu’s default page on `*:80`.
7. Verify: `curl -fsS http://127.0.0.1:18080/health/ready` → 200; compose publish still `127.0.0.1:18080`; `apache2ctl -S` no longer lists `trust-ci.ii-tonya.ru`.

### Later (only after DNS + cert + ProxyPass + env URL — not now)

Then the full `rollback.md` applies: `a2dissite`, revert `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`, `docker compose -f compose.yaml -f /home/pall/adaptive-trust-ci-host/compose.host-socket.yaml up -d --force-recreate api worker`. Leave LE files on disk unless abandoning the hostname.

Rollback does **not** unregister a GitHub hook (none). It does **not** unprotect `main` (unprotected). It does **not** revert a tag (none).

## 4. Observability

No public TLS SLI exists. Do not alert on `https://trust-ci.ii-tonya.ru/health/ready` until DNS A is claw inbound **and** a verified cert + ProxyPass exist.

| Signal | Expected for a complete edge | Observed now |
| --- | --- | --- |
| Loopback `/health/ready` | 200 `ready` | **200** |
| Public `/health/ready` | 200, `ssl_verify_result=0` | **TLS hostname mismatch** / nginx 301 on HTTP |
| Unsigned POST webhook | HTTP **401** | **TLS error** (HMAC gate untested on the public name) |
| Apache `trust-ci-access.log` / `trust-ci-error.log` | GitHub `X-GitHub-Delivery` after registration | Local 403/404 only |
| `TRUST_CI_PUBLIC_BASE_URL` | `https://trust-ci.ii-tonya.ru` | loopback HTTP (legal; Check Run `details_url` still loopback) |
| `certbot renew --dry-run` | exit 0 | **N/A** — no cert |
| Compose publish | `127.0.0.1:18080` | **held** |
| Plan webhook line | still not done | **held** |
| `main` protected | false until M0.3 | **false** |
| App-owned check on a *public* delivery | absent | absent (local HMAC only) |

Support visibility for this stop is `evidence/implementation.md` plus this report. FastAPI `/metrics` is **not** internet-reachable yet (no ProxyPass). After a future HTTPS vhost it will be reachable + bearer-gated (accepted residual in architect §7).

`mod_deflate` is globally enabled. Architect HMAC preflight: flag request-body processors. Not a blocker while there is no proxy, but **stop and isolate** before the HTTPS vhost if `deflate`/`substitute`/`security2`/`proxy_html` would rewrite webhook bytes.

## 5. Remaining risk (do not expand scope)

1. **DNS A is the wrong host.** `157.22.187.237` serves nginx for `ii-tonya.ru`. Operator must set FirstVDS A `trust-ci` TTL 300 to the IPv4 that **port-forwards 80/443 to `192.168.0.229`**. Egress `91.197.106.11` is a hint, not proof of inbound. Re-measure inbound before Certbot.
2. **Do not Certbot against the current A.** HTTP-01 would talk to nginx, or issue a cert for the wrong machine. Leave the HTTP vhost; report the required A.
3. **NAT / FirstVDS firewall.** Even a correct A fails ACME if 80/443 are not forwarded to this Apache. ufw was inactive with rules added; external panel firewall was not proven.
4. **New host listeners.** Apache now binds `*:80` and `*:443` on all interfaces. Default site returns 200. 443 speaks non-TLS. That is extra surface vs the pre-slice “ports free” state, even while DNS points elsewhere. Rollback is `a2dissite` / optional stop.
5. **Public URL must not be switched yet.** `CommonSettings` would accept `https://trust-ci.ii-tonya.ru`, but Check Run `details_url` would then point at a hostname whose cert does not match. Leave gitignored env on loopback until public ready 200 + unsigned 401.
6. **M0.2 remaining work is still the rest of the plan:** register webhook, public delivery Check Run, offline attestation, policy/holdout retitle, Ed25519 requeue, source-mutation. Local HMAC Check Runs (`97390635614`, `97406973020`) do not substitute.
7. **No merge / tag / protect.** `main` is unprotected. A merge would skip the still-absent App-owned public check. Do not reuse bootstrap exceptions.
8. **Security review not on disk** at write time. This report does not substitute `security_reviewer`. Stop if that review finds a blocker in the vhost script or leaked secrets.
9. **Untracked leftovers.** Other change packages (`20260817-…`, `20260824-да-user-query-37bf04`, dirty `9d97f8` state). Fail-closed on `git add -A`. Never commit `trust-ci/env/*.env`, `runtime/*.pem`, LE material.
10. **Egress IP drift** (`45.85.105.28` vs `91.197.106.11`) means “public IPv4 of claw” must be the **inbound** mapping, not `ifconfig.me` alone.
11. **change-spec.yaml** in this package is still a template. Route evidence only; not a product contract. Not a no-go for a docs-and-stop slice.
12. **Local receipts are not merge authority.** Parent may record `release_review` after this file; that does not create `adaptive-trust-ci/verified@6737355947c2`.

## 6. GO / NO-GO

| Act | Decision |
| --- | --- |
| Remaining **local docs** that honestly record: Apache HTTP vhost on claw; DNS A still `157.22.187.237` (nginx); no LE cert; public URL stays loopback; plan webhook **not done** / **no public HTTPS**; not M0.2 complete | **GO** |
| Update activation-report `TRUST_CI_PUBLIC_BASE_URL` to `https://trust-ci.ii-tonya.ru` **before** public TLS works | **NO-GO** |
| Tick M0.2 “Register repo webhook” / drop “no public HTTPS” without leaving “not done” | **NO-GO** |
| Claim public webhook live / GitHub can POST to this FastAPI | **NO-GO** |
| Treat this slice as M0.2 complete | **NO-GO** |
| `certbot certonly` while A ≠ claw inbound | **NO-GO** |
| `gh api …/hooks` / UI register webhook | **NO-GO** |
| Merge / mark PR ready / push `main` | **NO-GO** |
| Tag / GitHub Release / VERSION bump | **NO-GO** |
| Protect `main` / `adaptive-trust-ci branch-protect` | **NO-GO** |
| Publish API `0.0.0.0:18080` or host `:8080` | **NO-GO** |
| `compose down -v` / recreate postgres | **NO-GO** |
| Commit `env/common.env` or LE keys | **NO-GO** |
| Caddy/nginx/Cloudflare/ngrok as this edge | **NO-GO** |
| This reviewer executing host writes, push, or deploy | **NO-GO** |
| After operator fixes A **and** inbound 80/443: Certbot + HTTPS vhost + env URL + recreate **api worker** only + unsigned 401 proof | **deferred** — new evidence; not this GO |

Parent sequence after this review (controller/human; **not** this agent): keep the HTTP vhost or `a2dissite` if the operator wants ports free; write any remaining local docs under the GO row; wait for FirstVDS A + port-forward; then resume the runbook from step 5. Do not register a GitHub webhook and do not protect `main` in that resume until unsigned public 401 + ready 200 exist **and** a later named order covers hook create / M0.3.

## Peer reviews (same tree)

| Review | On disk | Verdict |
| --- | --- | --- |
| `evidence/code-review.md` | yes | **pass** — honest partial; no compose/secrets/HTTPS claim |
| `evidence/test-review.md` | yes | **pass** — `test_m0_invariants` 8 OK; public TLS not unit-tested |
| `evidence/data-review.md` | yes | **pass** — postgres not recreated; no `down -v` |
| `evidence/security-review.md` | **absent** | contingent |

## What this review is not

- Not merge authority and not a Trust CI Check Run.
- Not a security review.
- Not `grok_review.py` receipt recording.
- Not host DNS mutation, Certbot, webhook registration, branch-protect, tag, or GitHub Release.
- Did not read `.env` or PEM bodies. Did not push, merge, or deploy.

## Stop

**GO** only for remaining **local docs** that keep the DNS stop honest.

**NO-GO** for treating this as M0.2 complete, for treating the public webhook as live, for merge, tag, GitHub webhook registration, or `main` protection.

Rollback of what landed is `a2dissite trust-ci.conf`. Public TLS remains blocked on DNS (and inbound 80/443). Loopback Trust CI stays ready on `127.0.0.1:18080`.
