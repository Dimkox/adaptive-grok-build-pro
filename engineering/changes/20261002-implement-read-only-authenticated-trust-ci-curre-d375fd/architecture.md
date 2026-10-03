# Bounded design

trust-ci/src/adaptive_trust_ci/authority.py; api.py; narrow store.py protocol/query; engineering/contracts/openapi/trust-ci.v1.json authority schema; focused API/store/authority and disposable PostgreSQL tests. Exclude unrelated policy/CLI/settings/worker/example changes.

Required source binding repair: declare authority.py as a source of the existing Trust CI architecture node in architecture/system.yaml and regenerate only views actually affected by that declaration. This does not add a service, trust boundary, dependency, rule waiver or deployed policy change. Full verification refused the previously undeclared module and the binding regression failed; source registration is necessary to deliver the already approved endpoint.

The existing store.py is already a Python PostgreSQL client, not the PostgreSQL server. Move only its source ownership from NODE-TRUST-CI-POSTGRES to existing NODE-TRUST-CI-API, which already has the PostgreSQL edge and matching network policy. Preserve every node/edge/runtime/trust/secret attribute and architecture/rules.yaml. This resolves a baseline ownership error exposed by the approved store query change, without introducing network behavior. Extend the real-contract binding test for the new endpoint and adapter ownership. The timeout test may inspect exact SQLSTATE57014 instead of importing the driver solely for its exception class; it must retain the actual database lock, query and elapsed-time assertions.

Reconstruct approved authenticated read-only GET/authority/{job_id} snapshot with exact repository/PR/base/head, current server policy/holdout/public trust, verified approvals and cryptographically verified attestation, bounded enumeration and validity<=60seconds and applicable cutoffs. Synthetic public fixtures only. No deployment or deployed trust changes.

Use existing runtime/storage/API boundaries, no new service/framework/provider dependency. Each accepted identity is exact and validated using current authorized source/public material. Concurrent mutation, unavailable sources and corrupted binding fail closed; lookup never confers execution or merge authority.
