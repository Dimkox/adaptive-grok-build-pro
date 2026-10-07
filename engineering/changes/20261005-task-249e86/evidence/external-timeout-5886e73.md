# External timeout and bounded recovery

PR247 exact head5886e734b170307c6026f98c026f5e1a0e6ae834, App4694114, CheckRun111634695218, adaptive-trust-ci/verified@06ecf1c875bc: failure. Started2026-10-05T05:56:04Z, completed06:11:26Z. Public output: holdout-bundle-integrity PASSexit0, external-holdoutPASSexit0, root-unittestFAILexit124; attestation2a29b810-2083-45e0-9a2d-092e0c327d32. No assertion log/annotations were exposed. This is an authoritative failure at that head, not a pass inferred from local qualifier39340.

Measured fixture overhead justified source-only test optimization4471707; its focused pass and five independent affected reviews do not prove the external timeout resolved. No deployed timeout, policy, holdout, App, protection, runner image or GitHub Actions was changed. One fresh final full local run and exact-new-head App check are still pending at this workflow-record freeze.

Reviewer scratch relocation: after the data reviewer stopped, its exact owned0700 data-review.2JOlz8 directory was moved recoverably from the private home scratch to <project-root>/.review-scratch/data-review.2JOlz8, outside the candidate. No files were deleted; historical original report paths are retained as projected private-review-scratch references. Future reviewer scratch must use an explicit project-root absolute path.

Complete affected reports refer to4471707/d6232a5eb10c276f47a02b1d53c7b668de41d25e473b0d1eab25ee9b967bcd7d. Subsequent coordinator changes are workflow/prose evidence only; report identities remain historical and are never relabelled as reviewed at the later commit.
