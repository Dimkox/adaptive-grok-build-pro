# Test plan

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Loopback ready 200 | curl 127.0.0.1:18080 |
| P0 | Public https ready 200 | curl trust-ci.ii-tonya.ru |
| P0 | Unsigned webhook 401 + TLS ok | curl -w http_code ssl_verify_result |
| P0 | compose publish still 127.0.0.1:18080 | docker compose ps / inspect |
| P0 | test_m0_invariants (local HMAC, webhook not done, no PEM) | unittest |
| P1 | certbot renew --dry-run | command |
| P1 | postgres volume still present after recreate | docker volume |

Automated: `python3 scripts/grok_verify.py --mode pr`
