# Approved source reconstruction — g-authority

Change 20261002-implement-read-only-authenticated-trust-ci-curre-d375fd. Overall target2.1.1with heartbeat/watchdog. Owner-approved October1recovery design supplies this contour. Current explicit user instructions: full dirty-tree recovery and release2.1.1; source-only plan does not authorize production mutation.

## Scope

Reconstruct approved authenticated read-only GET/authority/{job_id} snapshot with exact repository/PR/base/head, current server policy/holdout/public trust, verified approvals and cryptographically verified attestation, bounded enumeration and validity<=60seconds and applicable cutoffs. Synthetic public fixtures only. No deployment or deployed trust changes.

## Product boundaries

trust-ci/src/adaptive_trust_ci/authority.py; api.py; narrow store.py protocol/query; engineering/contracts/openapi/trust-ci.v1.json authority schema; focused API/store/authority and disposable PostgreSQL tests. Exclude unrelated policy/CLI/settings/worker/example changes.

## Baseline and compatibility

Actual main/base e5856acfd4bc7a186f40a740b54ec86459462db5. Historical RC81cb7c21 is not its ancestor; reconstruct against current source without asserting tree equivalence. Preserve current callers/defaults and all old dirty source trees; import no aggregate/evidence/old receipt.
