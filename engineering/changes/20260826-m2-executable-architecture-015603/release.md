# Release plan — M2-A Executable Architecture

## Delivery

M2-A is a local branch/change package only until separately authorized push/PR delivery. It contains no deployment and does not activate independent enforcement.

Local verification and receipts remain preflight evidence. Merge authority remains the App-owned policy-epoch check on the exact pull-request head plus every separately required signed approval.

Installer planning is read-only for existing repositories and reports managed-file metadata plus dependency advice without executing it. `--materialize-new` publishes a verified complete payload only to an absent target and is supported only on Linux with descriptor-relative `O_NOFOLLOW`/`O_DIRECTORY` operations and libc/filesystem support for `renameat2(RENAME_NOREPLACE)`. An unavailable primitive or unsupported filesystem fails closed without publication, with no fallback to replacement, merge, or in-place copying. The supported alternative is `--plan` plus a normal reviewed source-change. `--force` is rejected. Every plan and payload excludes the target-owned marker, model, and rules.

## Go/no-go criteria

- Gate-valid red typed spec and exact completed-M1 adoption baseline.
- Root tests, compileall, deterministic diagram check, and PR verification pass.
- All route-selected code/test/security/data/release reviews pass on the final fingerprint.
- Exact M2-A diff contains no `trust-ci/**` path.
- M2-B dependency and external policy-epoch rollout remain explicit open items.

The authoritative current workflow status is recorded in `state.json` as `implementing`. Coordinator-owned exact-head verification plus code, test, security, data, and release review receipts remain required, and this note does not claim the package is `ready`.

The approved final safety pivot replaced order-dependent queue-name propagation with a package-aware bounded abstract interpreter and removed all mutation of existing installer targets. Current source repairs are implemented, but coordinator-owned final verification and all five independent route reviews and receipts remain pending on one immutable fingerprint. No final route review or receipt is claimed here, so AC-007 remains open.

## Rollout and observability

M2-A adoption is source-only and manual: review target model/rules, validate them, then commit the exact canonical marker. Existing consumer updates are ordinary reviewed source changes prepared from `--plan`; absent-target materialization has no in-place rollback path. Observe stable architecture/evidence digests, drift/fitness result counts, risk triggers, plan digests, publication failures, and receipt staleness. M2-B and deployment use a separate route/package/authorization.

Diagram rendering is stdout-only and checked-in projections change only through normal reviewed source edits. No migration, database, service, queue/runtime capability, provider, external write, `trust-ci/**` mutation, deployment, push, pull request, merge, tag, or release occurred in M2-A implementation.
