# Requirements

## Acceptance

- [ ] `dig +short A trust-ci.ii-tonya.ru` equals claw inbound/public IPv4 used for ACME. AAAA empty.
- [ ] Host Apache is the only public TLS on 80/443. API publish remains `127.0.0.1:18080:8080`.
- [ ] `curl -fsS http://127.0.0.1:18080/health/ready` and `curl -fsS https://trust-ci.ii-tonya.ru/health/ready` both 200 `status=ready`.
- [ ] Unsigned POST `https://trust-ci.ii-tonya.ru/webhooks/github` with `X-GitHub-Event: ping` → HTTP 401, `TLS_VERIFY=0`.
- [ ] `TRUST_CI_PUBLIC_BASE_URL=https://trust-ci.ii-tonya.ru` (gitignored env). Recreate **api** and **worker** only, with host-socket overlay. Postgres not recreated. No `down -v`.
- [ ] Activation report public URL updated. Plan webhook line stays **not done**. `test_m0_invariants` still has `local HMAC` and (`no public HTTPS` OR `not done`). No LE keys or `env/common.env` in git.
- [ ] `certbot renew --dry-run` pass after cert exists.

## Stops

- DNS A still not this host → do not force certbot; leave HTTP vhost; report required A.
- Something other than Apache binds 80/443 after start → stop.
- Recreate includes postgres or down -v → abort.
