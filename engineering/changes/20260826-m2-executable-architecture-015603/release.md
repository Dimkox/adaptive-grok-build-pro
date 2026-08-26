# Release plan — M2-A Executable Architecture

## Delivery

M2-A is a local branch/change package only until separately authorized push/PR delivery. It contains no deployment and does not activate independent enforcement.

## Go/no-go criteria

- Gate-valid red typed spec and exact completed-M1 adoption baseline.
- Root tests, compileall, deterministic diagram check, and PR verification pass.
- All route-selected code/test/security/data/release reviews pass on the final fingerprint.
- Exact M2-A diff contains no `trust-ci/**` path.
- M2-B dependency and external policy-epoch rollout remain explicit open items.

## Rollout and observability

M2-A adoption is source-only. Observe stable architecture/evidence digests, drift/fitness result counts, risk triggers, and receipt staleness. M2-B and deployment use a separate route/package/authorization.
