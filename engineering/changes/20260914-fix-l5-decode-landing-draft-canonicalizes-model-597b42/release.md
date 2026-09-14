# Release

This continues the review repair in existing PR #82 after v2.0.16. Published README/version/source identity remains unchanged. A later release train may include the merged bugfix; local focused tests do not establish external merge eligibility or runtime activation.

Stage 1: complete frozen-tree verification and independent reviews, then update the PR only with the exact delegated operation. Require fresh external Trust CI and required approvals for the resulting head before merge.

Stage 2: under separate exact operational delegation, stage the exact merged commit using the existing immutable-release procedure, record its identity and the prior release, and verify readiness. Do not alter the tested tree after approval or reuse approval for another SHA.

Stage 3: perform one authorized bounded synthetic normalization, expecting a valid mixed-language unsorted draft to normalize and malformed sections to return the controlled needs-human reason with evidence. Inspect the job reason and provider evidence digest; if a later stage builds an artifact, `artifact_ready` is distinct from normalization success. A ready health endpoint alone proves neither behavior. Stop on a regression and use [rollback.md](rollback.md).

Recovery observation supplied by the parent: the running service is ready but still uses `969c4f65f54ef9230f3f94587e228098d1c2ecb9`, with normalizer SHA-256 `9efc109b97d8769f5ea347752edbe6ccc632c63521275f95bb3a54893c6c2e96`. This implementation has not changed that service or verified any live repair.
