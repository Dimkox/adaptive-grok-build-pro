# Architecture

Authority: user runbook + `evidence/analysis-architect.md`.

Apache on host :443 is the only public TLS. FastAPI stays loopback. HMAC is verified on raw body inside FastAPI; Apache must not rewrite webhook body. `/approvals` is Ed25519 POST. Recreate api+worker with overlay; named volume postgres untouched.

Public URL https://trust-ci.ii-tonya.ru is Check Run `details_url`. Residual: `/metrics` `/jobs/` `/attestations/` become internet-reachable; FastAPI still requires read bearer.

## Rollback

`a2dissite trust-ci`; reload Apache; revert `TRUST_CI_PUBLIC_BASE_URL` to `http://127.0.0.1:18080`; `up -d --force-recreate api worker` with overlay; leave postgres.
