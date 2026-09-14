# Rollback

Before activation, keep the current runner unchanged if verification, review, external Trust CI, or approval is incomplete. This source-only repair introduces no migration or persisted-data conversion.

If an authorized rollout regresses, an operator restores the previously recorded immutable release through the existing installer/service procedure, under the exact required operational delegation, then verifies source identity and readiness. The parent observed that the current runner is ready on source `969c4f65f54ef9230f3f94587e228098d1c2ecb9`; its normalizer SHA-256 `9efc109b97d8769f5ea347752edbe6ccc632c63521275f95bb3a54893c6c2e96` matches that release's Git blob. This is the recorded recovery baseline, not evidence that normalization succeeds there.

For repository recovery, submit a scoped forward-fix/revert PR and subject its exact head to the same verification, independent review, and external Trust CI. Reverting the eventual merged repair may reintroduce rejection of noncanonical model items; it is not a claim that the original defect is cured. Runtime recovery and source recovery are separate operations, and no agent uses a local receipt as merge or deployment authority.
