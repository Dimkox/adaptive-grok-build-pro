# GitHub delivery diagnosis (2026-08-24)

Operator-safe. No webhook secret, PEM, or JWT.

Repo hooks: **empty** (`gh api .../hooks` has no rows). GitHub is not POSTing yet.

Public name `trust-ci.ii-tonya.ru` A = `157.22.187.237` (same as `ii-tonya.ru`). That host is **nginx/1.24.0**, not claw Apache. Claw API remains `127.0.0.1:18080` (`status_publisher=worker-github-app`).

| Probe | Result | Table row |
| --- | --- | --- |
| `https://trust-ci.ii-tonya.ru/health/ready` (verify on) | SSL hostname mismatch | **SSL error** — cert is not valid for `trust-ci.ii-tonya.ru` |
| same URL, verify off | HTTP **200** JSON `checks.postgres/migrations/workerLease/adapters` | Not Trust CI `/health/ready` (no `policy_digest`) — the **app** nginx, not FastAPI |
| `POST https://trust-ci.ii-tonya.ru/webhooks/github` unsigned ping | HTTP **405** nginx «Not Allowed» | Not 401. Path is not ProxyPass to `127.0.0.1:18080`; POST is rejected by nginx |
| `https://ii-tonya.ru/health/ready` | HTTP 200 same **app** JSON | Apex TLS is valid for `ii-tonya.ru` |
| `POST https://ii-tonya.ru/webhooks/github` | HTTP **405** nginx | Same: not FastAPI HMAC |
| claw `GET http://127.0.0.1:18080/health/ready` | 200 Trust CI ready | Local API is fine (not 502/503) |
| claw Apache Host `trust-ci.ii-tonya.ru` on :80 | 403 empty docroot | Local HTTP vhost only; public DNS does not hit it |

Unsigned FastAPI 401 is **not** observable on the public name until nginx (or DNS A to claw) forwards POST to loopback 18080 **and** the cert SAN includes `trust-ci.ii-tonya.ru`.
