# Test review — repository-scoped immutable policy profiles

## Verdict: FAIL

The supplied verification reports establish that the repository is structurally valid and that the focused unit suite passes, but the test evidence does not cover the change’s stated P0 contract end-to-end. The implementation also has one directly observable fail-closed gap identified below.

## Findings

### High — catalog-mode runner isolation is not tested at the execution boundary

`trust-ci/tests/test_worker.py:60-73` only asserts that `Worker.runner_factory` receives two distinct `Policy` objects. The existing runner tests at `trust-ci/tests/test_runner.py:173-305` all use the legacy fixture and therefore do not prove that repository A and B execute different command lists, different holdout bundles/host mounts, different `TRUST_CI_HOLDOUT_DIGEST` values, epoch check names, or signed attestation `policy_digest` values. This leaves the principal P0 “isolated commands/holdouts/digests” claim vulnerable to wiring regressions between the worker factory and `JobRunner`. Add a catalog-backed runner integration test with recording executor/GitHub/store doubles and assert the full command, holdout path, check, environment, and attestation binding for both repositories.

### High — approval, retry, and replay binding is only exercised for legacy policy

`trust-ci/tests/test_api.py:187-224` tests approval requeue with `self.policy` (legacy), while `trust-ci/tests/test_runner.py:265-285` tests replay with a legacy runner. There is no catalog-mode test proving that profile-specific approval scopes/TTL are selected from the job-bound digest, nor that a retry/replay cannot use the current profile after a profile change. This is explicitly a P0 acceptance scenario and an invariant in `change-spec.yaml` (`INV-002`). Add tests that enqueue a catalog job, alter/select a catalog with changed or swapped profile content, and verify approval validation and replay remain bound to the original repository/digest or fail closed.

### High — idempotency epoch behavior is not demonstrated

`trust-ci/tests/test_api.py:126-131` proves duplicate delivery for one unchanged request only. There is no test for the required case where the same repository/head is enqueued with a changed profile digest and must create a distinct idempotency identity and epoch Check Run. The store key implementation is outside the changed API tests; relying on it without a regression assertion does not validate the stated P1 requirement. Add an API/store test that posts the same event against two catalog generations and asserts distinct jobs, preserved original digest, and distinct check epoch inputs.

### Medium — removed/unknown repository close events and startup rejection matrix are incomplete

The API tests cover an unknown open event (`trust-ci/tests/test_api.py:142-145`) and a case-variant enqueue rejection (`:158-166`), but do not cover an unknown/case-variant `closed` event and prove it cannot cancel an existing job. Policy tests cover some malformed host paths and unknown keys (`trust-ci/tests/test_policy.py:91-112`), but not duplicate repositories, wildcard/default profiles, missing catalog common fields, or the complete null/empty/relative/unknown-field matrix required by `test-plan.md`.

### Medium — absolute host-path traversal is accepted and has no regression test

Catalog validation at `trust-ci/src/adaptive_trust_ci/policy.py:363-365` checks only string shape and `Path.is_absolute()`. Values such as `/srv/holdouts/../other` pass; there is no containment/canonical-root validation and no test for traversal, despite the failure-edge requirement that holdout path traversal fail before checkout. Add the intended profile-root invariant (or explicitly define the allowed canonical path policy) and a test asserting rejection before any runner/workspace activity.

## Spec compliance

- Legacy digest/check-name characterization: covered by `trust-ci/tests/test_policy.py:40-46,114-117`; credible as a regression assertion, though no separately recorded pre-change fixture is shown.
- Exact case-sensitive lookup and basic API enqueue binding: covered at policy/API level.
- Worker stale binding before runner construction: covered by `trust-ci/tests/test_worker.py:75-87`.
- Holdout host path forwarding: only factory-level coverage at `trust-ci/tests/test_worker.py:89-96`; not actual runner/container execution in catalog mode.
- Approval/check/attestation/retry/replay catalog binding: not demonstrated.
- Docs/config contract: `trust-ci/tests/test_ops.py:140-153` checks example shape and holdout digests, but does not validate README claims or full catalog rejection/rollback contract.

## TDD evidence credibility

The commit sequence contains tests added before each implementation slice (`427bd4d`, `d854fc0`, `f0c6d85`) and the supplied verification reports claim the selected unittest/coverage checks passed. However, the review package does not include captured failing-test output for the red phases, and several plan-listed tests were never added. Therefore the TDD claim is credible for the narrow parser/API/worker slices, not for the complete acceptance criteria.

## Residual risks

Without the missing tests, a future change could cross-wire a profile only after `JobRunner` construction, reuse current profile approval limits during replay, collapse changed-digest jobs, or cancel jobs from a repository no longer configured. The traversal acceptance gap additionally permits a syntactically absolute but non-canonical holdout host path.
