# Architect ruling — M0.2 public TLS edge (Apache → loopback Trust CI)

Route `01096425a38d`. Change `engineering/changes/20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`. Write owner: `frontend_implementer`. This agent does not compose-up, register GitHub hooks, push, merge, read PEM/`.env`/webhook secrets, edit tracked `trust-ci/compose.yaml`, or deploy.

Sources (no secrets): user 8-step Apache runbook; `trust-ci/src/adaptive_trust_ci/settings.py` `CommonSettings`; `api.py` `/webhooks/github` + `/approvals`; `webhooks.py` HMAC-over-raw-body; `runner.py` `details_url`; tracked `trust-ci/compose.yaml` ports; spec Host `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`; README TLS reverse-proxy contract; `test_m0_invariants.py` loopback publish; live claw probe this turn plus sibling `analysis-repo_explorer.md`. Deployed `trust-ci/runtime/*.pem`, `trust-ci/env/*.env` contents, and Let’s Encrypt PEMs were **not** opened.

## Ruling (one paragraph)

**Execute the user’s Apache vhost as specified.** Do not invent Caddy, nginx, Cloudflare tunnel, or ngrok. Host `:80`/`:443` are **currently free** (host `apache2` package/service **absent**; n8n `caddy:alpine` publishes `3001`/`5678` only). The runbook’s “Apache already owns 80/443” is **false on this claw**; the conflict-avoidance rule still holds: **if at execution time any non-Apache process binds 80/443, stop**. Because the ports are free, install host `apache2` (the runbook’s `python3-certbot-apache` / `a2enmod` path assumes it), then apply the given vhost so **Apache is the only public TLS**. Keep the API publish at `127.0.0.1:18080:8080`. Point FirstVDS A `trust-ci` at claw’s public IPv4 (**today DNS `157.22.187.237` ≠ claw `91.197.106.11`** — fix DNS before Certbot). Recreate **api and worker** with the existing untracked overlay after `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru`. Unsigned public POST `/webhooks/github` **401** is the proof. **Do not register a GitHub webhook this slice.**

---

## Live facts (this host, this turn)

| Plane | Fact |
| --- | --- |
| Host | `claw`. SearXNG `127.0.0.1:8080`. Trust CI API `127.0.0.1:18080→8080/tcp` healthy. |
| Compose | Project `adaptive-trust-ci` files: tracked `trust-ci/compose.yaml` **+** `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` (mode `0600`, untracked). Containers: api + postgres + worker. |
| Tracked publish | `"127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"` (`compose.yaml:52`). Invariant forbids `0.0.0.0` and host `:8080`. |
| Host Apache | **Not installed.** `apache2.service` not-found; no `/etc/apache2`; `apache2ctl` absent. |
| `:80` / `:443` | **Not listening.** Docker PHP-Apache `pulsengineering-dev-web-1` is container-internal 80 only. Caddy `n8n-proxy` does **not** publish 80/443. |
| Overlay | Existing path above. Do not copy into git. Do not edit tracked compose. |
| Public URL env | Sibling grep of the **key only**: `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080` (legal loopback HTTP; not the public form). |
| DNS | A `trust-ci.ii-tonya.ru` = `157.22.187.237`. Claw egress IPv4 = `91.197.106.11`. **Mismatch.** AAAA empty. No global IPv6 on `enp6s0`. |

---

## 1. Loopback publish must stay `127.0.0.1:18080`. Apache is the only public TLS

**Confirm.** Spec Host: published mapping is `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`; Trust CI **must not** publish host 8080. Tracked compose already matches. `test_m0_invariants.py` asserts that exact string and forbids `0.0.0.0:8080` / `127.0.0.1:8080:8080`.

Implementer **must not**:

- change the publish to `0.0.0.0:18080`;
- steal SearXNG `:8080`;
- edit tracked `trust-ci/compose.yaml`;
- put a Trust CI site on `n8n-proxy` Caddy or any other container edge;
- install a second terminator on 80/443.

Public Internet → Apache `:443` → `http://127.0.0.1:18080/…` only. After Apache is installed and enabled, `ss` must show Apache on 80/443 and the API still on `127.0.0.1:18080`.

**Install gap:** user step 3 runs `a2enmod` / Certbot Apache plugin but does not `apt-get install apache2`. On this claw that package is missing. Add `apache2` to the install line (or confirm `python3-certbot-apache` pulls it) **before** `a2enmod`. Then re-run the port inventory. If Caddy or anything else has taken 80/443 in the meantime, **stop** — do not fight.

---

## 2. ProxyPass of `/webhooks/github` and `/approvals` preserves raw body + GitHub headers

HMAC contract (`webhooks.py`):

```text
expected = hmac.new(secret, raw_body_bytes, sha256)
header  = X-Hub-Signature-256: sha256=<64 hex>
```

`api.py` `github_webhook` does `body = await request.body()` **then** `verify_webhook_signature(...)` **then** JSON parse. Missing/malformed signature → `WebhookError` → **HTTP 401**. Event name is `X-GitHub-Event` (`Header`). `/approvals` is `POST` + JSON envelope + Ed25519 (not raw-body HMAC) and still needs an unmodified JSON body.

**User vhost is HMAC-safe** for this FastAPI contract:

| Vhost knob | HMAC effect |
| --- | --- |
| `ProxyPass` / `ProxyPassReverse` to `http://127.0.0.1:18080/webhooks/github` (and `/approvals`) | Prefix proxy. `mod_proxy_http` forwards dechunked payload bytes. HMAC is over payload, not HTTP framing. FastAPI also dechunks. **OK.** |
| No `SetInputFilter`, `mod_substitute`, `mod_proxy_html`, `mod_sed`, request `INFLATE` | No body rewrite/re-encode. **OK.** |
| `RequestHeader unset Proxy early` | httpoxy only. Does **not** drop `X-Hub-Signature-256` or `X-GitHub-Event`. **OK.** |
| `RequestHeader set X-Forwarded-Proto/Port` | Additive. FastAPI HMAC does not use them. **OK.** |
| `ProxyPreserveHost On` | Host header only. **OK.** |
| `ProxyRequests Off` | Not an open forward proxy. **Required.** |
| `retry=0` | No POST replay on backend error. **Required** for webhook/approvals. |
| `ProxyTimeout 25` / `timeout=25` | Under GitHub’s 30s response budget. HMAC runs before JSON/enqueue. **OK.** |
| `LimitRequestBody 10485760` | 10 MiB. PR webhooks are small; oversized → Apache 413, not a silent HMAC mismatch. **OK.** |
| `<Location>` POST-only on `/webhooks/github` and `/approvals` | GET/HEAD die at Apache (403), not FastAPI. Proof curl is POST. **OK.** |
| Rewrite only on `:80` ACME exception | `:443` does not rewrite those paths. **OK.** |
| `Header always set` HSTS/nosniff/referrer | Response headers. **OK.** |
| LogFormat `X-GitHub-Delivery` / `X-GitHub-Event` | Logs copies; does not consume. **OK.** |

Hop-by-hop headers (`Connection`, `Transfer-Encoding`, …) are stripped by proxies; `X-Hub-*` / `X-GitHub-*` are not hop-by-hop. FastAPI `Header()` is case-insensitive.

**Do not add** any of: `RequestHeader unset X-Hub-Signature-256`, `RequestHeader unset X-GitHub-Event`, `SetInputFilter`, `Substitute`, `mod_security` body processors, `mod_deflate` **request** inflate, `mod_proxy_html`. After `apache2ctl -M`, if `security2`, `substitute`, or `proxy_html` are loaded globally from another site, isolate this vhost or **stop** — those can rewrite bytes and fail HMAC with 401-on-valid-GitHub.

Unsigned proof (`X-GitHub-Event: ping`, body `{}`, no signature) hits `missing or malformed webhook signature` **before** `parse_pull_request_event`. That is **401**, not ignored-event 200. Intended.

---

## 3. `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru` — recreate api **and** worker; never edit tracked compose

`CommonSettings.load` (`settings.py:62-64`):

- required `TRUST_CI_PUBLIC_BASE_URL`, rstrip `/`;
- must start with `https://` **or** `http://localhost` / `http://127.0.0.1`;
- else `SettingsError('TRUST_CI_PUBLIC_BASE_URL must be HTTPS outside localhost')`.

`https://trust-ci.ii-tonya.ru` is the legal public form. `http://trust-ci.ii-tonya.ru` would **crash** api/worker on boot. Do not use it.

Worker injects `settings.common.public_base_url` into `JobRunner`. Check Run `details_url` is `{public_base_url}/jobs/{job_id}` (`runner.py` start path and `publish_dead_job`). Recreating **only** api leaves worker Check Runs pointing at loopback HTTP. Recreate **both**.

Commands (user step 7), with the **known** overlay — do not `find` a different file and do not track it:

```bash
cd /home/pall/grok-projects/adaptive-grok-build-pro/trust-ci
# sed ONLY the TRUST_CI_PUBLIC_BASE_URL= line in gitignored env/common.env
# grep '^TRUST_CI_PUBLIC_BASE_URL=' only; never dump the file
docker compose \
  -f compose.yaml \
  -f /home/pall/adaptive-trust-ci-host/compose.host-socket.yaml \
  up -d --force-recreate api worker
```

**Do not** recreate postgres. **Do not** `compose down -v`. **Do not** start `docker-engine`. **Do not** edit `trust-ci/compose.yaml`. Overlay stays outside the git tree, mode `0600`.

Both `api` and `worker` `env_file` include `./env/common.env`; compose reads it at container create. `force-recreate` is required after the sed.

---

## 4. Do not register a GitHub webhook this slice. Unsigned 401 is the proof

User runbook has **no** `gh api …/hooks`, UI “Add webhook”, or `hooks create`. Spec rollout step 2 (register webhook) is **later**. Plan checkbox “Register repo webhook” stays **unchecked** (`test_m0_invariants` still needs `"no public HTTPS"` **or** `"not done"` on the plan).

Proof:

```text
POST https://trust-ci.ii-tonya.ru/webhooks/github
  Content-Type: application/json
  X-GitHub-Event: ping
  body {}
→ HTTP=401  TLS_VERIFY=0
```

That proves DNS + valid public cert + Apache proxy + FastAPI HMAC gate. It is **not** a registered hook. `GET …/hooks` may stay empty. Do not claim M0.2 complete. Do not protect `main`.

---

## 5. DNS: A to claw public IPv4; no AAAA if IPv6 unused

User: FirstVDS A `trust-ci` TTL 300 → claw public IPv4. **Do not create AAAA.**

Live: AAAA already empty (good). A currently **`157.22.187.237`**, claw public **`91.197.106.11`**. Certbot `--webroot` for `trust-ci.ii-tonya.ru` will fail or issue for the wrong host until A matches claw. Fix DNS first; `dig +short A trust-ci.ii-tonya.ru` from claw must equal claw’s public IPv4; `dig +short AAAA` must stay empty. Do not Certbot until that matches. Do not invent another hostname.

---

## 6. Rollback

Trigger: bad cert, Apache 502, API crash after URL change, HMAC-valid GitHub traffic not intended, or user abort.

1. `sudo a2dissite trust-ci.conf && sudo apache2ctl configtest && sudo systemctl reload apache2`. If this Apache install exists only for Trust CI, `systemctl stop apache2` is allowed so 80/443 return to free; do not uninstall in panic.
2. Leave the API published on **`127.0.0.1:18080`**. Do not bind `0.0.0.0`.
3. Revert **only** `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080` in gitignored `env/common.env`.
4. `docker compose -f compose.yaml -f /home/pall/adaptive-trust-ci-host/compose.host-socket.yaml up -d --force-recreate api worker`.
5. Leave postgres volume. No `down -v`. No overlay delete.
6. Leave Let’s Encrypt files on disk (unused if the site is off). Do not `cat` PEMs. DNS A may stay.
7. Verify: `curl -fsS http://127.0.0.1:18080/health/ready` → 200; public HTTPS either fails closed or is gone; compose publish still loopback.

---

## 7. Residual: `/metrics`, `/jobs/`, `/attestations/` publicly proxied

User vhost ProxyPasses those paths to loopback. FastAPI still enforces bearer `TRUST_CI_READ_TOKEN` (`api.py` `_bearer_authorizer`; tests 401 without/with wrong token). Command tails are stripped from the public job DTO (`_public_result`).

**Residual internet exposure (accepted this slice, not a blocker):**

- Unauthenticated callers can **reach** `/metrics`, `/jobs/{id}`, `/attestations/{id}` and receive **401** (token oracle / brute-force surface; job ids are UUIDs).
- `/health/live` and `/health/ready` are **unauthenticated** by design and will be public; ready JSON includes `policy_digest` and `status_context`.
- README: expose jobs/attestations “only according to the repository privacy model.” This vhost chooses public TCP + app authz. Do **not** drop those ProxyPass lines unless a later gate says so — they are in the user vhost and needed for Check Run `details_url` (`https://trust-ci.ii-tonya.ru/jobs/<job_id>`).
- Do not log Authorization headers. Custom `trustci` logformat does not.

---

## HMAC / Apache preflight (implementer)

After modules are enabled, before production traffic:

1. `apache2ctl -M` — expect `ssl`, `proxy`, `proxy_http`, `headers`, `rewrite`. Flag `security2`, `substitute`, `proxy_html`.
2. `apache2ctl configtest` then reload.
3. `ls -l /etc/letsencrypt/live/trust-ci.ii-tonya.ru/` only — **never** `cat` `privkey.pem` / `fullchain.pem`.
4. Loopback and public `/health/ready` both 200.
5. Unsigned POST 401 with `TLS_VERIFY=0`.
6. `certbot renew --dry-run`.

Certbot email: user placeholder `ТВОЙ_EMAIL`. Sibling `task_analyst` bound fallback `git log -1 --format=%ae` → `bpall@mail.ru`. Use that; do not invent another mailbox.

---

## Conflicts resolved

| Source | Claim | Ruling |
| --- | --- | --- |
| User runbook | Apache already on claw; do not install Caddy | **Edge = Apache.** Caddy/ngrok/Cloudflare **out**. |
| Live probe / `repo_explorer` | Host apache2 **absent**; 80/443 **free**; DNS A wrong | **Wins on facts.** Install `apache2` on free ports; fix A to `91.197.106.11` before ACME. |
| `task_analyst` §1 “80/443 existing Apache” | Assumed user text | **Overruled by live ss/systemctl.** Conflict rule still: non-Apache owner of 80/443 → **stop**. |
| Spec Host | “n8n/Caddy share Docker”; TLS reverse proxy required | Caddy stays on 3001/5678. **Do not** steal it for Trust CI. |
| Spec/README rollout step 2 | Register GitHub webhook | **Out this slice.** Unsigned 401 only. |
| Prior M0.2 analyses | “needs Cloudflare/Caddy/ngrok” | **Superseded.** User named Apache + `trust-ci.ii-tonya.ru`. |
| `CommonSettings` | HTTPS outside localhost | Public URL **must** be `https://trust-ci.ii-tonya.ru`. Recreate api **and** worker. |
| `AGENTS.md` | Repo cannot change deployed policy/holdout/images/Postgres/keys | **Binding.** Overlay + gitignored URL line only. |

Human gates `scope_and_design_approval` and `migration_or_external_write_approval` cover **this 8-step runbook plus `apt-get install apache2` on free 80/443 and the DNS A correction**. They do **not** cover hook registration, `branch-protect`, merge, PEM read, `compose down -v`, or `0.0.0.0` publish.

---

## Out of scope (explicit)

- Caddy / nginx / ngrok / Cloudflare as the Trust CI TLS edge
- Editing tracked `trust-ci/compose.yaml` or tracking the host-socket overlay
- GitHub webhook **registration**
- `branch-protect`, merge, push `main`, tag, VERSION
- Reading or committing PEM, `.env`, webhook secret, App RSA, human approval private keys
- Policy / holdout / trust-store / image digest changes
- Publishing API on `0.0.0.0` or host `:8080`
- `compose down -v` / postgres recreate
- Claiming M0.2 complete

**Success metric:** A record = claw public IPv4; AAAA empty; Apache (not Caddy) on 80/443; API still `127.0.0.1:18080`; `https://trust-ci.ii-tonya.ru/health/ready` 200; unsigned POST `/webhooks/github` HTTP 401 `TLS_VERIFY=0`; `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru` in the gitignored key only; worker recreated so new Check Run `details_url` uses that HTTPS origin; no GitHub hook created; no PEM in git or evidence.
