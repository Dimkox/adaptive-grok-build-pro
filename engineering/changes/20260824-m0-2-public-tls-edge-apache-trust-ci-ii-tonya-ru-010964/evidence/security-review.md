# Security review — M0.2 public TLS edge (HTTP vhost only)

**Agent:** `security_reviewer` (read-only except this report)  
**Route:** `01096425a38d`  
**Change:** `20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`  
**Verdict:** **pass**

Inspected the change package, tracked `trust-ci/compose.yaml` ports, `.gitignore`, live `ss` / `docker inspect` / `apache2ctl -S` / vhost files, loopback `/health/ready`, local Host-header probe, DNS A, and git index for env/PEM. Did **not** read `.env`, `env/*.env` bodies, webhook secret, App PEM, signing keys, Let’s Encrypt private keys, or dumps. Did not push, merge, deploy, or register a GitHub webhook.

This slice is host Apache HTTP-01 staging only. Public HTTPS, ProxyPass, certbot, and `TRUST_CI_PUBLIC_BASE_URL` HTTPS switch are **not done**.

---

## Pass gates (this review)

| Gate | Result |
| --- | --- |
| No secret leak in git | **PASS.** No `*.pem` / `*.key` / `trust-ci/env/*.env` / runtime secrets tracked. Gitignore covers them. Change-package evidence has no private-key blocks. |
| API not published on `0.0.0.0:18080` | **PASS.** Live bind is `127.0.0.1:18080`. Tracked compose still `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`. No compose edit. |
| `:443` listener residual | **NOTED** (not a fail). `ssl_module` is enabled → `ports.conf` `Listen 443`. No `*:443` vhost, no LE cert, `default-ssl` not enabled. |

---

## 1. Secrets

| Surface | Finding |
| --- | --- |
| Git index | `git ls-files '*.pem' '*.key' 'trust-ci/env/*.env' 'trust-ci/runtime/*'` → only `trust-ci/runtime/.gitkeep`. |
| `.gitignore` | `.env`, `*.pem`/`*.key`, `trust-ci/env/*.env`, `trust-ci/runtime/*` ignored (examples/` .gitkeep` kept). |
| `TRUST_CI_PUBLIC_BASE_URL` (key only) | Still `http://127.0.0.1:18080`. Not switched to the public HTTPS origin (correct until a real cert exists). File body not dumped. |
| Overlay | `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` mode `0600`, untracked. Contents not read. |
| Let’s Encrypt | `/etc/letsencrypt/live` **absent**. No `privkey.pem` to leak. Implementation `ls` only; this review did not `cat` PEMs. |
| Host vhost script | `evidence/host-http-vhost.sh` is the runbook HTTP ACME vhost. No secrets. |
| Product tree | Tracked compose/API/policy/holdout/trust-store **not** edited this slice. |

App ID `4694114` and installation ID `156003193` appear in the user runbook / activation report already; they are identifiers, not private keys. Certbot mailbox `bpall@mail.ru` in the change package is a contact address, not a credential.

---

## 2. Authz and exposure

**API remains loopback.** Live:

```text
LISTEN 127.0.0.1:18080  docker-proxy
HostIp=127.0.0.1 HostPort=18080  (adaptive-trust-ci-api-1 → 8080/tcp)
```

`NO_PROXY` GET `http://127.0.0.1:18080/health/ready` → **HTTP 200** `status=ready`. HMAC (`POST /webhooks/github`) and Ed25519 (`POST /approvals`) still terminate in FastAPI. Apache does **not** ProxyPass those paths yet.

**HTTP vhost only** (`/etc/apache2/sites-available/trust-ci.conf`, enabled): `VirtualHost *:80`, `ServerName trust-ci.ii-tonya.ru`, DocumentRoot ACME webroot, `Options -Indexes`, `Require all granted`. Local probe `GET http://127.0.0.1/` with that Host → **403 Forbidden** (empty indexes; runbook-acceptable). No reverse proxy, no `ProxyRequests`.

`apache2ctl -S` namevhosts on **`:80` only**: Debian `000-default` + `trust-ci`. Default site still serves `/var/www/html` as the catch-all; that is stock Apache, not Trust CI.

**DNS limits public reach of this vhost.** A `trust-ci.ii-tonya.ru` = `157.22.187.237` (not this claw’s inbound NAT `192.168.0.229` / probed egress). `getent` shows no native AAAA (IPv4-mapped only). Internet Host `trust-ci.ii-tonya.ru` does not land on this Apache until the operator fixes A (and any port-forward). LAN `:80`/`:443` on claw remain reachable; `ufw` was inactive.

Future residual (not installed): the runbook `:443` vhost would ProxyPass `/metrics`, `/jobs/`, `/attestations/`, `/health/` as well as webhook/approvals. FastAPI still requires bearer on jobs/metrics/attestations (`_bearer_authorizer`). That internet surface is **out of this slice**.

---

## 3. Residual: `:443` open with ssl module default

Enabling `ssl` for later Certbot/HTTPS also activated Debian `ports.conf`:

```apache
<IfModule ssl_module>
    Listen 443
</IfModule>
```

Live `ss`: Apache `*:443` **and** `*:80`. `mods-enabled` has `ssl.load` / `ssl.conf`. `sites-enabled` does **not** include `default-ssl.conf`. `apache2ctl -S` lists **no** `*:443` namevhost. There is no Trust CI TLS vhost and no Let’s Encrypt cert.

So TCP 443 is open under the **ssl module default** (listener only; snakeoil default-ssl site not enabled). Handshake/cert identity is undefined until the runbook HTTPS vhost exists. This is **not** a secret leak and **not** a publish of `18080`.

Mitigations already in place: DNS A mismatch, no ProxyPass to the API, API still `127.0.0.1:18080`. When DNS is corrected, close this residual by installing the specified `VirtualHost *:443` (or stop `Listen 443` until that vhost exists). Do not `a2ensite default-ssl` as a workaround.

---

## 4. PII, tenant isolation, irreversible actions

| Area | Finding |
| --- | --- |
| PII | Operator email in package/docs for a future certbot `-m`. No customer data, dumps, or approval private keys. Health JSON on loopback includes `policy_digest` (already the live loopback contract). |
| Tenant isolation | Single-tenant Trust CI. Postgres catalog not recreated; sibling data review confirms volume identity preserved. No `compose down -v`. Overlay untouched. |
| Irreversible | Host `apache2`/`certbot`/modules installed; HTTP vhost enabled; `ufw allow 80/443` recorded while ufw inactive; `a2enmod ssl` opened `:443`. **Not** done: certbot issue, HTTPS ProxyPass, env URL sed, api/worker recreate, GitHub hook create, `0.0.0.0` publish, PEM commit. Rollback remains `a2dissite trust-ci.conf` + reload; leave API on loopback. |

No production write to GitHub, 1C, Bitrix24, or deployed Trust CI policy/holdout/keys.

---

## 5. What would fail this review

- Publishing `"0.0.0.0:18080"` or host `:8080`.
- Committing `env/*.env`, PEM, webhook secret, App RSA, or LE `privkey.pem`.
- Claiming public HTTPS / unsigned POST 401 while there is no cert and no `:443` vhost.
- ProxyPass of the API from the HTTP ACME vhost (not present).

None of those happened.

**pass** — no secret leak; API stays `127.0.0.1:18080`; note Apache `:443` ssl-module default listener until DNS + Let’s Encrypt + the runbook TLS vhost.
