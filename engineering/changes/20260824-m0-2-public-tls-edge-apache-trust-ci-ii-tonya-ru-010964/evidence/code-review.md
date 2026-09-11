# Code review — M0.2 public TLS edge (partial Apache HTTP vhost)

**Agent:** code_reviewer (read-only)  
**Route:** 01096425a38d  
**Verdict:** **pass**

## Scope checked

- Tracked `trust-ci/compose.yaml` still publishes `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`. Diff does **not** change compose, env, API, or overlay.
- `trust-ci/env/common.env` still has `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`. Implementation notes correctly refuse to switch this until HTTPS exists.
- Git working tree for product code: no compose edit. Untracked change package + `decisions.md` paperwork only. No `*.pem` / Let’s Encrypt material in the commit set.
- `evidence/implementation.md` and `host-http-vhost.sh` describe HTTP ACME vhost only. Certbot, HTTPS `ProxyPass`, GitHub webhook URL, and unsigned public POST 401 are listed as **not done**.
- DNS stop is consistent: A `trust-ci.ii-tonya.ru` = `157.22.187.237` ≠ claw inbound NAT (`192.168.0.229`, egress `45.85.105.28`). AAAA empty. No claim that public HTTPS is live.

## Fail conditions (not met)

| Condition | Result |
| --- | --- |
| Claimed public HTTPS / webhook / certbot success | Not claimed |
| Edited `compose.yaml` (including `0.0.0.0:18080`) | Not edited |
| Secrets / PEM in git | Not present in the product/docs commit |

## Residual risk (out of this review)

Public TLS remains blocked on operator DNS/port-forward. Host Apache HTTP vhost is host-local and not in git; that is expected. Full reverse-proxy vhost from the runbook is still pending after A matches inbound claw.

This slice is an honest partial: loopback API unchanged, no secrets committed, DNS halt documented.
