# task_analyst — M0.2 public TLS edge Apache trust-ci.ii-tonya.ru (route 01096425a38d)

**Verdict:** this turn is **one public HTTPS reverse-proxy on existing Apache** for `trust-ci.ii-tonya.ru` → loopback FastAPI `127.0.0.1:18080`. It is **not** GitHub webhook **registration**, **not** `branch-protect`, **not** merge, **not** PEM read, **not** M0.2 complete.

Write owner: **`frontend_implementer`** (route `write_agent`). Apache/ops does **not** authorize a second writer. This agent does not implement, push, merge, read PEM/`.env`, or deploy.

Skills: `/adaptive-delivery`, `feature-workflow`, `api-event-change`, `data-change`, `enterprise-integration`, `frontend-change`, `security-sensitive-change`. Allowed agents only. Analysis is read-only except this evidence file.

Route `human_gates`: `scope_and_design_approval`, `migration_or_external_write_approval`.

---

## 1. Outcome of THIS slice

**Observable result:** From the public Internet, `https://trust-ci.ii-tonya.ru` terminates TLS on **Apache :443** on host `claw` and proxies a bounded set of paths to the already-running Trust CI API on **loopback** `http://127.0.0.1:18080`. GitHub and a human workstation can **reach** `/webhooks/github` and `/approvals` over valid HTTPS. The API still publishes **only** `127.0.0.1:18080:8080`. Unsigned webhook POSTs still die at FastAPI HMAC with **HTTP 401**.

This is the public **TLS edge**. It is **not** GitHub App webhook **registration**.

Registration (`gh api …/hooks` / GitHub UI “Add webhook” / `hooks create`) is a **later** GitHub UI/API step. The user did **not** list `gh api hooks create`. Step 8 is an **unsigned** `POST https://trust-ci.ii-tonya.ru/webhooks/github` that must return **401** with `TLS_VERIFY=0`. That proves DNS + TLS + Apache proxy + FastAPI HMAC — it does **not** create a GitHub hook. `GET …/hooks` may stay empty after this slice. Plan checkbox “Register repo webhook `POST https://<ci>/webhooks/github`” stays **not done** until a later named order.

Live facts this analysis used (no secrets):

| Plane | State |
| --- | --- |
| Host | `claw` (named CI host; not a laptop). SearXNG owns host `:8080`. |
| Compose `adaptive-trust-ci` | API published `"127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"` (`trust-ci/compose.yaml`). Worker via untracked host-socket overlay. |
| Activation report | `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`; App `4694114`; Installation `156003193`; Check Run via **local HMAC**; **no public webhook**. |
| Public GitHub hook | absent (`GET …/hooks` empty at M0 freeze; later slices still “no public HTTPS”). |
| `main` protected | false |
| 80/443 | existing **Apache** on claw. Do **not** install Caddy on top. n8n/Caddy already share Docker. |

`CommonSettings` (`trust-ci/src/adaptive_trust_ci/settings.py`): `TRUST_CI_PUBLIC_BASE_URL` must start with `https://` **or** `http://localhost` / `http://127.0.0.1`. Changing the public URL to `https://trust-ci.ii-tonya.ru` is the legal non-localhost form. Do not leave it as public HTTP.

---

## 2. Do both human gates pass?

**Yes for this exact 8-step runbook. No for branch-protect, merge, PEM read, or GitHub hook create.**

Quoted user order (complete runbook, not a vibe):

> Не хватает только публичного TLS-edge:
>
> GitHub App → `https://trust-ci.ii-tonya.ru/webhooks/github` → Apache :443 → `http://127.0.0.1:18080/webhooks/github`
>
> human workstation → `https://trust-ci.ii-tonya.ru/approvals` → Apache → `http://127.0.0.1:18080/approvals`
>
> 1. Создай DNS … Type: A Name: trust-ci Value: \<публичный IPv4 сервера claw\>
> 2. Проверь, кто держит 80 и 443 … На claw уже был Apache, поэтому не ставим поверх него Caddy … `127.0.0.1:18080:8080` Не меняй его на `0.0.0.0:18080`. Внешним должен быть только Apache.
> 3. Поставь Certbot и модули Apache … `ufw allow 80/tcp` `ufw allow 443/tcp`
> 4. Создай временный HTTP-vhost для сертификата
> 5. Получи сертификат Let’s Encrypt … `EMAIL='ТВОЙ_EMAIL'`
> 6. Установи окончательный Apache reverse proxy
> 7. Замени loopback public URL … `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru` … `docker compose … up -d --force-recreate api worker`
> 8. Проверь TLS и HMAC gate … `HTTP=401` `TLS_VERIFY=0` … `sudo certbot renew --dry-run`

| Gate | Satisfied? | Bound to |
| --- | --- | --- |
| `scope_and_design_approval` | **Yes** | The 8 steps **are** the design: DNS A `trust-ci.ii-tonya.ru` → claw IPv4; keep Apache; Certbot webroot; vhost with ProxyPass to loopback; public URL HTTPS; unsigned POST 401. No alternate Caddy/cloudflare/ngrok design is in scope. |
| `migration_or_external_write_approval` | **Yes** | Named host writes: FirstVDS DNS A, `apt-get`, Apache site/modules/reload, Certbot ACME, `ufw allow 80/443`, `sed` of gitignored `env/common.env` `TRUST_CI_PUBLIC_BASE_URL`, `docker compose … up -d --force-recreate api worker` with the **existing** host-socket overlay. |

Controller may treat both named gates as granted **only** for that runbook. Adaptive-delivery “stop before implementation” is **satisfied by this quote**, not waived.

**Not granted** (searched user text + change package; **not found**):

| Action | In the 8 steps? |
| --- | --- |
| `gh api …/hooks` / `hooks create` / GitHub UI register webhook | **No.** Step 8 is unsigned POST 401. |
| `adaptive-trust-ci branch-protect` / protect `main` | **No.** Plan: only after M0.2 is unambiguous. |
| Merge / mark PR ready / push `main` | **No.** |
| Read PEM / `.env` dump / App private key / webhook secret print / human approval private key | **No.** Step 5 only `ls -l` the live cert **directory**. Do not `cat` `privkey.pem`. |
| Policy / holdout / trust-store / image pin edit | **No.** |
| `compose down -v` | **No.** Recreate **api** and **worker** only. |
| Publish API on `0.0.0.0:18080` or host `:8080` | **Explicitly forbidden** by step 2. |

Mint any `grok_approve.py` grant only for the named host operations in steps 1–7 (DNS/apt/apache/certbot/ufw/env-url/`compose … api worker`), bound to current repo/route/change/HEAD/fingerprint/TTL. Wildcard forbidden. Local grants never create Trust CI checks or substitute human Ed25519.

---

## 3. Certbot EMAIL

User wrote a placeholder:

```text
EMAIL='ТВОЙ_EMAIL'
sudo certbot certonly --webroot -w /var/www/trust-ci-acme -d trust-ci.ii-tonya.ru --agree-tos --non-interactive -m "$EMAIL"
```

**Bound fallback (not invented):** `git log -1 --format=%ae` → **`bpall@mail.ru`**. Same address is the author of the last five commits (498 occurrences in this repo). Implementer must set `EMAIL=bpall@mail.ru` for `--non-interactive -m`. Do not invent another mailbox. Do not prompt. If `git log -1 --format=%ae` had been empty, **STOP** for email; it is not empty.

Let’s Encrypt ToS is accepted by the user’s `--agree-tos` in step 5.

---

## 4. In scope / out of scope

### In scope (the 8 steps)

1. **DNS FirstVDS:** A `trust-ci` → claw public IPv4, TTL 300. No AAAA unless IPv6 is already configured on claw.
2. **Port inventory:** `ss` / `apache2ctl -S` / `systemctl status apache2`. Keep existing Apache. Enable `ssl proxy proxy_http headers rewrite`.
3. **Certbot + ufw:** install `certbot python3-certbot-apache`; `ufw allow 80/tcp` and `443/tcp`; operator reminder if FirstVDS has a separate panel firewall.
4. **Temporary HTTP vhost** `trust-ci.conf` for ACME webroot; `a2ensite`; `configtest`; reload; `curl -I http://trust-ci.ii-tonya.ru/` may be 200/403/404 as long as it hits claw.
5. **`certbot certonly --webroot`** for `trust-ci.ii-tonya.ru` with `EMAIL=bpall@mail.ru`. Prove files exist via `ls -l /etc/letsencrypt/live/trust-ci.ii-tonya.ru/` — **do not read PEM contents**.
6. **Final vhost:** HTTP→HTTPS 308 except ACME; TLS; `ProxyRequests Off`; ProxyPass of `/webhooks/github`, `/approvals`, `/jobs/`, `/attestations/`, `/metrics`, `/health/` to `http://127.0.0.1:18080…` with `timeout=25` (health 10); POST-only on webhook and approvals; empty DocumentRoot denied; HSTS/nosniff/no-referrer.
7. **Public URL:** `sed` **only** the `TRUST_CI_PUBLIC_BASE_URL=` line in gitignored `trust-ci/env/common.env` to `https://trust-ci.ii-tonya.ru`. Recreate **api** and **worker** with the **same** untracked `compose.host-socket.yaml` overlay already in use. Do not recreate postgres. Do not `down -v`.
8. **Proof:** public `/health/ready` 200; loopback `/health/ready` still 200; unsigned POST `/webhooks/github` HTTP 401 and `TLS_VERIFY=0`; `certbot renew --dry-run`.

Repo paperwork that **belongs** with this slice (write owner after host proof): fill this change package (brief/AC/architecture/test/rollback), operator-safe activation-report cell `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru`, plan note that **TLS edge exists** but **GitHub hook is still unregistered**. Do not claim M0.2 complete.

### Out of scope (explicit)

- **Caddy** (or nginx, Cloudflare tunnel, ngrok) on :80/:443. Apache already holds the ports.
- Publishing API on **`0.0.0.0:18080`** or host **`:8080`**. Tracked compose stays `"127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"`. SearXNG keeps 8080.
- **`compose down -v`**, postgres recreate, named-volume destroy, restore into live DSN.
- **Policy / holdout / trust-store / image digest** edits. Epoch name stays `adaptive-trust-ci/verified@6737355947c2`.
- **PEM / `.env` / webhook secret / App RSA / human approval private key** read, print, or commit. `ls` of Let’s Encrypt live dir is enough.
- **GitHub webhook create** (`gh api repos/…/hooks`, UI, `hooks create`). Step 8 is unsigned POST 401. Registration is a later slice.
- **`branch-protect`**, protect `main`, disable leftover Actions workflow `340420982`.
- Merge, mark ready, push `main`, tag, GitHub Release, VERSION bump.
- Human Ed25519 `approval-create` / requeue of Check Runs.
- Policy/holdout retitle, live source-mutation, forging `adaptive-trust-ci/verified@*`.
- Adding `.github/workflows/**`.
- Changing ProxyPass to a non-loopback upstream.
- Enabling Apache `ProxyRequests On` (forward proxy). User vhost sets `ProxyRequests Off`.

---

## 5. Acceptance criteria (observable)

**P0 — public TLS edge, loopback still private**

1. **Given** FirstVDS A `trust-ci` TTL 300, **when** `dig +short A trust-ci.ii-tonya.ru` from claw, **then** it equals claw’s public IPv4. `dig +short AAAA trust-ci.ii-tonya.ru` is empty unless IPv6 was already in use (do not create AAAA in this slice).
2. **Given** Let’s Encrypt webroot cert, **when** `curl -fsS https://trust-ci.ii-tonya.ru/health/ready`, **then** HTTP **200** and `status: ready`. Certificate verifies (`ssl_verify_result=0` on public curls).
3. **Given** an **unsigned** `POST https://trust-ci.ii-tonya.ru/webhooks/github` with `Content-Type: application/json`, `X-GitHub-Event: ping`, body `{}`, **then** `HTTP=401` and `TLS_VERIFY=0`. Not 404, 502, 503, or timeout. Body may be FastAPI HMAC error JSON; do not print secrets.
4. **Given** the same host, **when** `curl -fsS http://127.0.0.1:18080/health/ready`, **then** HTTP **200** `status: ready` (loopback listener unchanged).
5. **Given** `docker compose` publish mapping, **then** it is still **`127.0.0.1:18080→8080`**, not `0.0.0.0:18080` and not host `:8080`.
6. **Given** `grep '^TRUST_CI_PUBLIC_BASE_URL=' env/common.env`, **then** exactly `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru`. Do not dump the rest of the env file into chat or git.

**P1 — proxy contract and renewal**

7. Apache `ProxyRequests Off`; webhook and `/approvals` POST-only at the vhost; ACME path still served on :80; `sudo certbot renew --dry-run` exits 0.
8. `ss` shows Apache (not Caddy) on :80 and :443. API still bound to 127.0.0.1:18080.
9. No PEM, JWT, webhook secret, installation token, or human approval private key appears in git, chat, or reports. Let’s Encrypt `privkey.pem` is never `cat`’d.

**P2 — M0.2 honesty**

10. Plan “Register repo webhook” remains **unchecked**. Activation report may update the public URL cell; public webhook still **absent** until a later GitHub registration slice. `main` stays unprotected. Do not claim M0.2 complete.

Non-criteria: signed GitHub `ping` 200; GitHub delivery logs; Check Run from a **public** hook; `/approvals` 200 (unsigned must fail at FastAPI, typically 4xx); IPv6; Caddy; host 8080.

---

## 6. Write owner

**`frontend_implementer` is the sole write owner** despite this being Apache/ops on claw.

Route `write_agent`: `frontend_implementer`. Adaptive-delivery: exactly one write agent; do not spawn `general_implementer`, `integration_implementer`, or a second ops writer. Review agents stay read-only **after** implementation and `python3 scripts/grok_verify.py --mode pr`.

Implementer sequence (host first, paperwork second):

1. Wait for this analysis wave. Treat both human gates as granted **for the 8 steps only**.
2. Execute steps 1–8 on `claw`. `EMAIL=bpall@mail.ru`. Overlay path from `find "$HOME" -name 'compose.host-socket.yaml' -type f` — do not invent; do not track the overlay.
3. Record operator-safe proof (dig, curl HTTP codes, `TLS_VERIFY`, compose publish, certbot dry-run). No PEM bytes.
4. Update change package + activation-report public URL cell. Do not check GitHub hook registration. Do not protect `main`.
5. `python3 scripts/grok_verify.py --mode pr` if product files changed. Then route review agents.

**Empty / error stops (do not improvise):**

| Signal | Action |
| --- | --- |
| `dig A` ≠ claw IPv4 or NXDOMAIN | Fix FirstVDS DNS. Do not point Certbot at the wrong host. |
| :80/:443 held by Caddy or a non-Apache process | **Stop.** Do not install a second TLS terminator. |
| Temptation to bind API `0.0.0.0:18080` or host 8080 | **Stop.** Out of scope. |
| Temptation to `compose down -v` | **Stop.** Recreate api/worker only. |
| Temptation to `cat` `privkey.pem` / App PEM / `.env` | **Stop.** `ls -l` only. |
| Temptation to `gh api hooks create` because “M0.2 webhook” | **Stop.** User did not order registration. Step 8 is 401. |
| Temptation to `branch-protect` / merge | **Stop.** Not granted. |
| Certbot email missing | Use `bpall@mail.ru` from `git log -1 --format=%ae`. Do not invent. |
| Public `/health/ready` not 200 or unsigned POST not 401 | Do not proceed to GitHub UI. Fix proxy. |

**Rollback:** disable `trust-ci.conf` (`a2dissite`), reload Apache, revert `TRUST_CI_PUBLIC_BASE_URL` to `http://127.0.0.1:18080`, recreate api/worker with the same overlay. Leave postgres volume. Do not delete Let’s Encrypt certs as a panic move; they are host-local and unused if the vhost is off. DNS A can stay (harmless) or be removed by the operator.

**Success metric:** `dig A` matches claw IPv4; `https://trust-ci.ii-tonya.ru/health/ready` 200; unsigned POST `/webhooks/github` HTTP 401 `TLS_VERIFY=0`; loopback 18080 still ready; compose publish still `127.0.0.1:18080`; no GitHub hook created; no PEM in evidence; write owner remains `frontend_implementer`.

**Next slice (not this one):** GitHub webhook **registration** to `https://trust-ci.ii-tonya.ru/webhooks/github` (HMAC secret already in API env — do not print it); then public `ping`/PR events. Human Ed25519 requeue, policy/holdout retitle, and M0.3 `branch-protect` remain separately gated.
