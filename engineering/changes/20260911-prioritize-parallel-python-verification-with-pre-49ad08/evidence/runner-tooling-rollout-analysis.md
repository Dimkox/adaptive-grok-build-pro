# Runner tooling: delivery boundary and smallest compatible rollout

2026-09-11; route `49ad08e34053`; worktree `adaptive-grok-build-pro-test-parallel`. Source-only analysis of the frozen priority implementation. No product changes, installs, tests, container operations, credentials or deployed-state reads by this agent.

## Conclusion

Keep the real parallel conformance tests and mandatory coverage gate. The smallest source adjustment is to add the three missing pinned packages to the existing runner image recipe, then have its owner build and approve a new immutable image and policy epoch. Editing the recipe does not update the external image. A serial compatibility mode cannot make the current complete test suite pass on an image without pytest/xdist/pytest-cov.

Current deployment identity is unknown. Do not diagnose the running service from local cached images or from an August activation record. The rollout prerequisite is conditional: if the active external runner already has all exact dependencies, no image change is needed; otherwise the external owner must provision them before the feature can receive a valid full check.

## Observed source and cached-image evidence

| Evidence | Bound conclusion |
| --- | --- |
| `trust-ci/runner.Dockerfile:19` | Installs service `[test]`, coverage 7.15.4, Ruff 0.16.2, Bandit 1.9.4, tomli 2.4.1. No explicit pytest, pytest-xdist or pytest-cov installation. |
| Root-produced `.grok-stack/runtime/cached-runner-tooling.json` | Two locally cached images reported all three distributions absent and coverage 7.15.4 present. Both entries explicitly set `deployment_identity_verified=false`. This analysis only read that nonsecret package report. |
| `.grok-stack/adaptive_grok/python_test_runner.py:149` | A requested parallel run requires exact pytest 9.1.1 / xdist 3.8.0 / pytest-cov 7.1.0 / coverage 7.15.4; missing/mismatched dependency fails before launch. Serial measured run requires coverage 7.15.4. |
| `trust-ci/config/policy.example.json:24` | Example policy runs mandatory root unittest discovery and repository `grok_verify --mode pr`, in addition to Trust CI tests and compileall. This file is not the observed deployed policy. |
| `trust-ci/src/adaptive_trust_ci/policy.py:31` | Policy parser rejects optional commands. Removing/ignoring a required test lane is not a compatibility mechanism. |

## Why serial fallback does not preserve this suite

`tests/test_python_test_runner.py:19` creates an opted-in fixture with `workers=2` and explicitly removes inherited `GROK_TEST_WORKERS` and `_GROK_TEST_CHILD`. Thus running the outer suite with unittest or `GROK_TEST_WORKERS=0` does not remove its real parallel dependency.

- `test_opted_in_verifier_shards_each_method_once` requires all four fixture methods and exactly two actual process IDs.
- `test_parallel_coverage_preserves_parent_and_existing_data` runs measured parallel execution and requires successful tests/coverage while protecting existing data.
- `test_coverage_below_threshold_and_worker_data_loss_fail` exercises the real pytest-cov worker-data path.
- `test_missing_parallel_dependency_fails_without_serial_retry` explicitly requires missing tooling to fail without producing fixture output.

Automatic serial fallback inside the fixture would fail those assertions. Skipping them on missing dependencies, replacing their assertions with mocked worker success, or excluding their file would remove the new feature's proof. An explicit outer serial mode remains useful for debugging/resource control once the test dependencies are installed; it is not an old-image delivery solution.

## Smallest source change and reproducible image preparation

1. Product writer adds `pytest==9.1.1`, `pytest-xdist==3.8.0` and `pytest-cov==7.1.0` to the existing `RUN python -m pip install` in `trust-ci/runner.Dockerfile`; preserve coverage and other existing pins, user, filesystem and no-runtime-install behavior.
2. Extend the existing stdlib recipe-pin check in `trust-ci/tests/test_ops.py:128` to keep these versions aligned with `.grok-stack/config/python-test-requirements.txt`. No changes to API, database contracts, policy commands or holdout are needed for installing the tools.
3. `trust-ci/compose.build.yaml:23` builds with context `trust-ci/`, so `COPY ../.grok-stack/...` is invalid. Inline exact pins plus a parity check is smaller than changing all build contexts or adding another packaging system.
4. The image owner builds from the reviewed recipe and an approved immutable Python base, records the exact resulting registry `name@sha256` and actual package versions, and validates the complete changed root suite plus coverage in an isolated runner environment. Same checkout, dependencies, resource limits and no-network execution matter; local host success alone is insufficient image evidence.
5. Keep package installation in image build/setup. Repository verification must not pip-install from the network, mount a host environment into CI, or modify the running cached container.

These are proposed follow-up actions, not actions performed during the frozen verifier. A source recipe change invalidates the earlier source fingerprint and needs normal verification/review before completion.

## External rollout remains independently owned

`trust-ci/src/adaptive_trust_ci/worker.py:27` requires configured runner image to equal `policy.sandbox.image` exactly. The source policy validates immutable digests, and its canonical policy digest includes sandbox configuration. `trust-ci/README.md:90` and `engineering/runbooks/trust-ci-rollout.md` document build/pin, policy-epoch proof and App-bound protection.

The external owner must install the approved immutable image and corresponding policy through its own deployment process, prove the new App-owned policy-epoch check, and bind branch protection to that exact check and App. The source PR and a local delegated grant cannot perform or substitute this authority transition. Existing checks/approvals from the old epoch cannot qualify a changed image/policy; the final feature head requires fresh exact-head verification and any externally required signed scopes.

The example approval rules match `trust-ci/**` as governance and `**/*.Dockerfile` as production. Therefore the proposed recipe edit also falls within those **example** scopes; actual required scopes must come from deployed authority, not inferred as already satisfied. No human private keys are requested or read.

For a bootstrap dependency cycle, split a small recipe-only PR from the feature: the old image can run the old suite plus a stdlib pin-parity test, then the owner rolls out the approved image before checking the feature PR. Alternatively an operator can independently approve/build the reviewed candidate recipe before the combined PR is checked. The source agent cannot silently choose a candidate image as trusted. Either sequence preserves tests and the App gate; neither treats the recipe merge or local tests as deployment evidence.

Keep rollback records for the previous immutable image/policy. A rollback is another authority/currentness transition requiring fresh jobs/protection binding as documented; it cannot leave the accelerated feature claiming compatibility with an image that lacks its tested dependencies.

## Public tracked immutable identity found

The historical [activation report at the source base](https://github.com/Dimkox/adaptive-grok-build-pro/blob/64378d28c7b78cace463d96470c1898294b8f196/engineering/runbooks/trust-ci-activation-report.md) is dated **2026-08-24** and records:

```text
ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2
```

This is a documented historical runner identity only. No concrete immutable Python **base image** identity was found in the inspected tracked runbooks. `runner.Dockerfile` and `compose.build.yaml` require a supplied `PYTHON_BASE_IMAGE` / `TRUST_CI_PYTHON_BASE_IMAGE`; neither establishes its deployed value. Do not manufacture a base digest or promote the cached-image package probe into a current deployment claim.

Memory fact: source recipe pinning plus independently approved immutable-image rollout is the honest delivery path if active CI lacks the packages. Serial fallback cannot satisfy this branch's actual two-worker and worker-coverage conformance tests without installing the same dependencies.
