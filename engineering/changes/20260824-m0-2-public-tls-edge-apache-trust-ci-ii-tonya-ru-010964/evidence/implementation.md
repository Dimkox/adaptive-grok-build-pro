# Implementation — TLS edge (partial: Apache HTTP vhost)

Write owner: parent controller after `frontend_implementer` spawn was denied (stale `general_implementer` lock in `agent-state.json`).

## Done on claw

- Installed `apache2`, `certbot`, `python3-certbot-apache`.
- Enabled modules: `ssl proxy proxy_http headers rewrite`.
- `ufw allow 80/tcp` and `443/tcp` (ufw was inactive; rules still added).
- HTTP vhost `trust-ci.conf` for `ServerName trust-ci.ii-tonya.ru`, DocumentRoot ACME webroot.
- `a2ensite trust-ci.conf`; `apache2ctl configtest` Syntax OK; apache2 **active**.
- Listens `*:80` and `*:443` (ssl module). Loopback GET with Host `trust-ci.ii-tonya.ru` → **403** (empty indexes; runbook-acceptable).
- API still `127.0.0.1:18080` `/health/ready` 200. Overlay untouched. postgres not recreated.

## Stopped before certbot (DNS)

| Probe | Value |
| --- | --- |
| DNS A `trust-ci.ii-tonya.ru` | `157.22.187.237` (same as `ii-tonya.ru` apex) |
| claw LAN | `192.168.0.229` behind `192.168.0.1` |
| claw egress `ifconfig.me` | `45.85.105.28` (earlier probe also saw `91.197.106.11`) |
| AAAA | empty (correct) |

No FirstVDS DNS API in this environment. HTTP-01 cannot succeed until A points at the IPv4 that **inbound** 80/443 reaches this Apache.

Required record (operator, FirstVDS):

```text
Type: A
Name: trust-ci
Value: <IPv4 that port-forwards 80/443 to 192.168.0.229:80/443>
TTL: 300
```

Do **not** create AAAA. After A matches, rerun certbot with `-m bpall@mail.ru`, then the HTTPS vhost from the user runbook, then `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru` and recreate **api worker** only with the host-socket overlay.

## Not done

- Let’s Encrypt cert
- HTTPS ProxyPass vhost
- public URL env change
- GitHub webhook registration
- unsigned POST 401 on https://trust-ci.ii-tonya.ru

`TRUST_CI_PUBLIC_BASE_URL` remains `http://127.0.0.1:18080` until HTTPS is real.
