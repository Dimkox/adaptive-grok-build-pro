# repo_explorer — Trust CI health / webhook hostname (claw)

Route `421a1ddd7770`. No secrets, no `.env` contents, no PEM.

## adaptive-trust-ci
- `adaptive-trust-ci-api-1`: running, **healthy**; `127.0.0.1:18080->8080/tcp`.
- `adaptive-trust-ci-postgres-1`: running, **healthy**; `5432/tcp` not published to host.
- `adaptive-trust-ci-migrate-1`: Exited 0 (~9m ago).
- Host listen: `127.0.0.1:18080` (ready bind). HTTP `/health` curl blocked by local grant hook; Docker health is the probe used.

## worker.env
- Filename exists: `trust-ci/env/worker.env` (not opened).

## Public HTTPS / GitHub webhooks
- Host `ss`: **no** `:443` TCP listen (`NO_HOST_443`).
- `n8n-proxy` (Caddy v2.11.4): healthy; published **only** `0.0.0.0:3001` and `0.0.0.0:5678`. Internal 80/443/2019 **not** mapped to host 443.
- Caddyfile site blocks (no env): `http://:5678`, `http://:18789`, `http://:3001` — **no public HTTPS hostname**.
- Host IPs: LAN `192.168.0.229` plus docker bridges; not a public webhook FQDN.

## Impact
GitHub App webhooks cannot reach claw on published 443 today. API is loopback-only on 18080.
