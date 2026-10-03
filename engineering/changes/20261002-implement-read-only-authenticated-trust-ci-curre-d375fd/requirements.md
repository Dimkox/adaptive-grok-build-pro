# Acceptance criteria

Reconstruct approved authenticated read-only GET/authority/{job_id} snapshot with exact repository/PR/base/head, current server policy/holdout/public trust, verified approvals and cryptographically verified attestation, bounded enumeration and validity<=60seconds and applicable cutoffs. Synthetic public fixtures only. No deployment or deployed trust changes.

trust-ci/tests/test_authority.py, test_api.py and test_store.py; bounded matching PostgreSQL query test. Synthetic public signing/verification, auth, tuple mismatch, invalid attestation, rotation/revocation/expiry/read failure, concurrent source change, bounds/order and output secret absence.

The new source must be owned by its existing architecture node. tests/test_architecture_model.py::ArchitectureModelTests::test_seed_architecture_models_current_boundaries_and_real_contracts and mandatory architecture drift/fitness checks must pass without reducing the source inventory or changing fitness rules.

Source rollback uses a PR revert; additive database recovery retains durable rows and forward migration. Local evidence never authorizes protected merge or live rollout.
