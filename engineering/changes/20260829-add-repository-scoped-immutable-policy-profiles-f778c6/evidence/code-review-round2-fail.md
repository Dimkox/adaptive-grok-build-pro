# Code review — repository-scoped immutable policy profiles

Status: **FAIL**

Reviewed exact head `898f76bbf23b5080904d618dbf744bf4b5bad2a4` against base `1c06299894279a88b881defa3f19b004fa742223`. Review scope was trusted-boundary correctness, canonicalization, immutable digest/check binding, API/worker selection, legacy compatibility, and approval/external-check semantics. The review was read-only apart from this report.

## Findings

### High — configured trusted roots are not themselves validated as safe roots

`trust-ci/src/adaptive_trust_ci/worker.py:62-79` canonicalizes `settings.holdout_path` and `settings.holdout_host_path` and only checks that each catalog path is a strict descendant of those values. `trust-ci/src/adaptive_trust_ci/settings.py:112-116` checks only that the environment values are absolute. Therefore a deployment with `TRUST_CI_HOLDOUT_HOST_PATH=/` (or another broad daemon path) accepts any absolute profile `holdout.host_path` below it, and the worker passes that profile path to the container runner at `trust-ci/src/adaptive_trust_ci/worker.py:44-55` / `trust-ci/src/adaptive_trust_ci/runner.py:198-208`. The same issue exists for the local trusted root.

This makes the new confinement boundary depend on an unchecked broad-root configuration and does not satisfy the requirement that invalid holdout roots fail closed. Startup must validate the configured roots themselves (canonical absolute non-root, deployment-approved holdout roots, with the host root independently trusted) before constructing `PostgresStore`, signing, or GitHub dependencies, and tests must cover `/`, empty/relative, and broad-root configurations. A catalog descendant check alone cannot establish the intended trusted boundary.

## Reviewed controls

- `PolicyCatalog.from_dict` requires exact profile keys and exact, case-sensitive `owner/name` repositories; unknown repositories are rejected by the API before cancellation or enqueue.
- Profile-local and host holdout paths are canonicalized before `Policy.from_dict`, and the effective profile digest includes the canonical holdout values, commands, and common execution envelope.
- `Worker.build` validates catalog path pairs before external dependency construction; profile paths must be strict descendants of configured roots with equal non-empty relative suffixes. The worker resolves jobs by `(repository, policy_digest)` and does not fall back to the current profile.
- API enqueue stores the selected effective digest, idempotency includes that digest, and approval lookup verifies the job-bound repository, SHAs, scope, and digest. Legacy mode continues through `Policy.from_dict` and `PolicyCatalog.from_policy`, retaining the legacy policy digest/check-name path.

## Residual risks

- A policy-binding failure is durably marked failed by the worker but does not publish a corresponding GitHub failure check (`trust-ci/src/adaptive_trust_ci/worker.py:100-121`). If the operational contract requires every terminal job to have a visible App-owned check, this remains a separate reliability/observability gap.
- The available local test run could not import `fastapi` in this environment; the focused non-FastAPI tests ran, but the full suite was not independently reproduced here. The implementation agent reported `167 passed, 8 skipped` and `grok_verify --mode pr` passed; those claims were not treated as review authority.

No production writes, external writes, secret access, or code fixes were performed.
