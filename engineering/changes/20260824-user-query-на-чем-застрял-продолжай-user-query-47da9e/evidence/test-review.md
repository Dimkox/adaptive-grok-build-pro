# Test review — route 47da9efaec38

**Status:** PASS  
**Reviewer:** test_reviewer  
**Change:** `20260824-user-query-на-чем-застрял-продолжай-user-query-47da9e`  
**Scope inspected:** `trust-ci/tests/test_m0_invariants.py` vs `trust-ci/compose.yaml` and M0 spec/plan docs.  
**Verification:** `python3 scripts/grok_verify.py --mode pr` reported PASS (given by dispatch; not re-run here).

## Adequacy

`M0InvariantTests` is a source-tree characterization suite. It is appropriate for the host-name and compose-publish correction: it reads committed files rather than executing compose.

## Required assertions (gate)

| Requirement | Assertion | Result |
|---|---|---|
| Named host is `claw` | `test_m0_docs_name_claw_not_laptop`: `assertIn("claw", spec)` and `assertIn("claw", plan)` | Present |
| Not laptop | `assertNotIn("laptop", spec)` | Present |
| Compose project name | `test_compose_publishes_loopback_not_all_interfaces`: `assertIn("name: adaptive-trust-ci", text)` | Present; matches `compose.yaml` line 1 |
| 18080 interpolation | `assertIn("127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080", text)` | Present; matches compose ports mapping |
| No all-interfaces 8080 | `assertNotIn("0.0.0.0:8080", text)` | Present |
| No hardcoded host 8080 publish | `assertNotIn("127.0.0.1:8080:8080", text)` | Present |

Healthcheck still uses in-container `http://127.0.0.1:8080/health/ready` (container listen, not host publish). Tests require that string; that is correct and does not contradict the host-port interpolation.

## Characterization coverage

Also covered: spec/plan existence, check-run name `adaptive-trust-ci/verified@`, base SHA `48cb9737…`, M0.0/M0.3 plan markers, no RSA private keys in docs, no `.github/workflows`, API must not hold `GitHubClient`/`GitHubAppAuth`, worker must use `GitHubAppAuth`, holdout forbids GitHub Actions and webhook-held app keys.

## Gaps (non-blocking)

- `assertNotIn("laptop", plan)` is not asserted (only spec). Plan currently does not use "laptop"; adding the check would lock the invariant on both docs.
- Tests do not execute compose or bind-check the published port.
- String matching could miss a second publish mapping with different quoting.

These do not fail the assigned gate.

## Verdict

**PASS.** Tests assert claw, no laptop on spec, compose name `adaptive-trust-ci`, `18080` host-port interpolation, and no `0.0.0.0:8080`.
