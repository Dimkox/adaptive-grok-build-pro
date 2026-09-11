# Test review — M0.2 public TLS edge (HTTP vhost only)

**Agent:** test_reviewer (read-only except this report)  
**Route:** `01096425a38d`  
**Change:** `20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`  
**Verdict:** **PASS**

## Adequacy for this slice

This package stopped before Let’s Encrypt and HTTPS ProxyPass. Product characterization is still `trust-ci/tests/test_m0_invariants.py`. Public TLS is **not** a unit-test surface (host Apache + DNS + certbot). Live HTTP vhost **403** on Host `trust-ci.ii-tonya.ru` is sufficient operational evidence for the ACME-empty DocumentRoot.

No new unittest is required until HTTPS is in tree or `TRUST_CI_PUBLIC_BASE_URL` becomes a documented in-repo contract.

## Characterization (`test_m0_invariants`)

Live: `python3 -m unittest trust-ci.tests.test_m0_invariants` → **8 tests, OK** (0.001s).

| Invariant | Result |
| --- | --- |
| Spec/plan exist; check name + base SHA; M0.0–M0.3; no PEM in spec/plan | ok |
| Activation report: no PEM markers; Check Run id not UNKNOWN; **local HMAC**; plan **not done** / **no public HTTPS** | ok |
| No `.github/workflows` | ok |
| API has no `GitHubClient` / `GitHubAppAuth` | ok |
| Worker uses `GitHubAppAuth` | ok |
| Compose: project `adaptive-trust-ci`, `127.0.0.1:…18080:8080`, not `0.0.0.0:8080` | ok |
| Docs name claw, not laptop | ok |
| Holdout forbids GHA and webhook-held App key | ok |

PEM blobs are still absent from spec/plan/report (`PEM_MARKERS`). Tests do not open `.env`, certs, or `privkey.pem`.

## Live edge (not unit-tested)

`evidence/probe-local-vhost.py`: `GET http://127.0.0.1/` Host `trust-ci.ii-tonya.ru` → **HTTP 403 Forbidden**. Matches runbook (“200, 403 or 404”). Unsigned HTTPS POST 401 and public `/health/ready` are **out of scope** until cert + ProxyPass.

## Gaps (accepted)

- `test-plan.md` P0 public HTTPS 200 and unsigned webhook 401 + TLS_VERIFY=0 are **not** claimed. This review does not treat them as failing unit tests.
- Certbot dry-run and compose recreate are P1 ops, not characterization.
- Unittest does not prove Apache config syntax; host evidence lives in `implementation.md`.

## Residual risk

When HTTPS lands, do **not** encode Let’s Encrypt PEM paths into `test_m0_invariants`. Keep asserting loopback compose publish and “no PEM in docs.” Add live curl evidence, not unit tests against `/etc/letsencrypt`.

## Status

**pass** — `test_m0_invariants` green (8/8); local HMAC / webhook not done / no public HTTPS still encoded; no PEM; HTTP vhost 403 is enough; public TLS not unit-tested.
