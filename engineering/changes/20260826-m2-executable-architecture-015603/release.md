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

Task 5 left the package in its historical `implementing` phase. The authoritative current workflow status is recorded in `state.json`; verification plus code, test, security, data, and release review receipts remain required, and this note does not claim the package is `ready`.

The final route review found seven source defects across queue provenance, installer containment, durable adoption, code-budget metrics, bounded process cleanup, added-contract comparison, and repository ownership. Their source repairs and focused regression coverage are present in the current candidate, but independent rereview and final receipts are still pending.

## Rollout and observability

M2-A adoption is source-only and manual: review target model/rules, validate them, then commit the exact canonical marker. Observe stable architecture/evidence digests, drift/fitness result counts, risk triggers, and receipt staleness. M2-B and deployment use a separate route/package/authorization.

Diagram rendering is stdout-only and checked-in projections change only through normal reviewed source edits. No migration, database, service, queue/runtime capability, provider, external write, `trust-ci/**` mutation, deployment, push, pull request, merge, tag, or release occurred in M2-A implementation.
