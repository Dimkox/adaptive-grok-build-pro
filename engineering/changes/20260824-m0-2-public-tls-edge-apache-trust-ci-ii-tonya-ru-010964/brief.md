# M0.2 public TLS edge Apache trust-ci.ii-tonya.ru

**RETRACTED 2026-08-24:** `https://trust-ci.ii-tonya.ru/webhooks/github` is a ChatGPT error. Do not configure, probe, or complete TLS for it. Host Apache leftovers stay untouched. See `20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86`.

Change ID: `20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`
Route: `01096425a38d`
Write owner: `frontend_implementer` (route; do not spawn a second writer)

## Problem

Trust CI is live on loopback `127.0.0.1:18080` with App-owned Check Runs via HMAC. GitHub cannot POST to loopback. User ordered Apache TLS on `trust-ci.ii-tonya.ru` proxying `/webhooks/github` and `/approvals`.

## Outcome

`https://trust-ci.ii-tonya.ru/health/ready` returns 200. Unsigned POST `/webhooks/github` returns **401** with TLS verify 0. API stays `127.0.0.1:18080`. GitHub webhook is **not** registered this slice.

## Live deviations from the runbook (analysis)

- Host Apache is **not** installed; **80/443 are free**. Install `apache2` (do not put Caddy on 80/443; n8n Caddy is 3001/5678).
- DNS A `trust-ci.ii-tonya.ru` = `157.22.187.237` **≠** claw egress (probed `91.197.106.11` / NAT `192.168.0.229`). Re-measure public IPv4 at execution. **Fix A to claw inbound IPv4 before certbot.** AAAA stays empty.
- `TRUST_CI_PUBLIC_BASE_URL` still `http://127.0.0.1:18080`.
- Overlay: `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` mode 0600.
- Certbot email fallback: `bpall@mail.ru` (`git log -1 --format=%ae`). User placeholder was `ТВОЙ_EMAIL`.

## Gates

User runbook **is** `scope_and_design_approval` and `migration_or_external_write_approval` for this exact 8-step host work (DNS, apt, Apache, certbot, ufw, compose recreate **api worker only**, public URL). Not for GitHub hook create, branch-protect, merge, PEM read, `compose down -v`.

## Out of scope

GitHub `hooks` create, Caddy on 80/443, bind API `0.0.0.0:18080`, host 8080, tracked `compose.yaml` edit, policy/holdout/PEM, protect `main`, M0.2 complete claim.
