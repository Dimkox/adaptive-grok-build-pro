# Code review — repository-scoped immutable policy profiles

Status: **FAIL**

Reviewed exact head `a4cc6dcebca25979388f31cef70b2b4782b86af2` against base `1c06299894279a88b881defa3f19b004fa742223`, using the supplied review package and repository-local requirements/design.

## Findings

### High — catalog accepts arbitrary absolute daemon host paths

`trust-ci/src/adaptive_trust_ci/policy.py:363-366` validates only that a catalog profile's `holdout.host_path` is a non-empty absolute string. It does not validate that the path is beneath an approved Trust CI holdout root, nor reject `/`, parent traversal after normalization, or other host locations. The worker then passes this value directly to `JobRunner` at `trust-ci/src/adaptive_trust_ci/worker.py:48-53`, and the runner passes it to the container executor at `trust-ci/src/adaptive_trust_ci/runner.py:198-208`.

This violates the stated requirement that holdout roots be invalid when outside the trusted/profile-scoped area and the architecture risk mitigation to confine profile holdouts beneath validated trusted roots. A server-mounted catalog containing a typo or malicious absolute path could cause an arbitrary daemon-host directory to be mounted into the isolated execution container. Absolute-path validation alone is not a sufficient boundary. Startup validation should canonicalize the configured path and enforce containment under an independently configured immutable Trust CI holdout root (and reject the root itself and traversal outside it); the effective canonical path must remain digest-bound.

## Spec compliance

The reviewed code otherwise satisfies the main data-flow requirements: legacy policies remain represented by the original `Policy` and digest; catalog resolution is exact and case-sensitive; profile digests include commands, holdout definitions, and common effective fields; webhook enqueue stores the selected digest in the existing job field; idempotency includes that digest; and the worker resolves `(repository, policy_digest)` before constructing a runner. Unknown repositories are rejected before closed-event cancellation or enqueue. Binding failures are terminal and do not invoke repository checkout or commands.

The holdout-path finding prevents full compliance with the acceptance criteria and security invariants, so this review cannot pass until fixed and covered by a regression test.

## Residual risks

- The worker's binding-failure path records a terminal failed job but does not publish a GitHub failure check, so operators may see a terminal non-success in durable state without a corresponding check-run update. Confirm whether the deployed operational contract requires a visible failure check for retired/skewed bindings.
- Legacy input containing an extra `holdout.host_path` is accepted by the legacy parser and changes the legacy digest; if “legacy policies omit it” is intended as strict validation rather than a deployment convention, reject that field explicitly in legacy mode.

No deployment, external write, secret access, or product/test/documentation modification was performed.
