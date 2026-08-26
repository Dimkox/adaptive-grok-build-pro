# Release plan — M2-A Executable Architecture

## Delivery

M2-A is a local branch/change package only until separately authorized push/PR delivery. It contains no deployment and does not activate independent enforcement.

Installer delivery includes local architecture modules, CLI, both strict schemas, and non-authoritative examples. It excludes the target-owned marker, model, and rules under normal and forced installation.

## Go/no-go criteria

- Gate-valid red typed spec and exact completed-M1 adoption baseline.
- Root tests, compileall, deterministic diagram check, and PR verification pass.
- All route-selected code/test/security/data/release reviews pass on the final fingerprint.
- Exact M2-A diff contains no `trust-ci/**` path.
- M2-B dependency and external policy-epoch rollout remain explicit open items.

Current package state remains `implementing`. Verification plus code, test, security, data, and release review receipts are deliberately pending until the coordinator reviews the exact final M2-A tree; the package must not transition to `ready` in Task 5.

## Rollout and observability

M2-A adoption is source-only and manual: review target model/rules, validate them, then commit the exact canonical marker. Observe stable architecture/evidence digests, drift/fitness result counts, risk triggers, and receipt staleness. M2-B and deployment use a separate route/package/authorization.

No migration, database, service, queue, provider, external write, `trust-ci/**` mutation, deployment, push, pull request, merge, tag, or release occurred in M2-A implementation.
