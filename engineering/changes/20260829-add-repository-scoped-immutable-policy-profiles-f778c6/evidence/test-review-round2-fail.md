# Test review — repository-scoped immutable policy profiles

## Scope and verdict

- Base: `1c06299894279a88b881defa3f19b004fa742223`
- Head: `898f76bbf23b5080904d618dbf744bf4b5bad2a4`
- Verdict: **FAIL**

The new tests materially improve coverage, including execution-boundary assertions for two profiles and a trusted-root matrix. They do not yet adequately prove all requested immutable-binding, replay/idempotency, and removed-profile behaviors for the exact head SHA.

## Findings ordered by severity

### High — catalog replay/idempotency after a changed profile digest is not tested

The required scenario is that the same repository/head submitted against a changed catalog/profile digest produces a distinct idempotency identity/check epoch, while an existing job and replay remain bound to the original digest. `trust-ci/tests/test_api.py:128-134` only repeats one unchanged webhook and asserts reuse; `trust-ci/tests/test_runner.py:312-333` tests replay only with the legacy `self.policy`. The catalog tests at `trust-ci/tests/test_api.py:149-158` only assert initial job binding. No test changes the catalog digest and asserts distinct jobs, preserved original digest, distinct check name, or replay without re-execution under the original binding. This leaves `INV-002` and the plan’s changed-digest replay/idempotency acceptance criterion unproved.

### High — the purported removed-profile approval test does not remove the profile

`trust-ci/tests/test_api.py:183-201` is named `test_catalog_approval_fails_closed_when_bound_profile_is_removed`, but `self.catalog(changed=True)` still contains both repository profiles and only changes the first profile’s command name (`:108-110`). The 409 therefore proves stale digest rejection for a changed profile, not behavior when the repository profile is absent from the active catalog. There is no test that removes the bound repository, posts a matching signed approval, and verifies fail-closed behavior without requeue or execution.

### Medium — approval binding is only partially covered for catalog mode

The catalog approval test does verify a stale profile digest returns 409, which is useful. However, there is no positive catalog approval/requeue test proving the valid profile-specific approval scope/TTL is accepted for the job-bound digest, nor a retry/replay test proving a catalog job cannot use current profile approval rules after a profile change. The only positive requeue test remains legacy at `trust-ci/tests/test_api.py:218-253`.

### Medium — trusted-root coverage is good but not a complete independent matrix

`trust-ci/tests/test_worker.py:99-113` covers a valid paired descendant, root itself, parent traversal, and a host path outside the trusted root. This is adequate for the principal regression, and `Worker.build` invokes validation before store/signing/GitHub construction (`trust-ci/src/adaptive_trust_ci/worker.py:25-31`). However, the test uses `assertRaisesRegex(Exception, ...)` rather than the concrete configuration error and does not separately exercise missing/null host path or local path outside the root. The parser-level tests in `trust-ci/tests/test_policy.py:91-100` cover malformed host-path shape, but not the full runtime root containment matrix.

### Medium — closed/unknown event isolation is covered only on legacy API setup

`trust-ci/tests/test_api.py:175-181` proves an unknown and case-variant closed event cannot cancel a configured legacy job. There is no equivalent catalog-mode test with a configured profile and a closed event for an unknown/case-variant repository. Since catalog lookup is a central change boundary, that path should be exercised explicitly.

## Verified coverage

- Two catalog profiles reach the runner execution boundary with distinct command lists, local holdout paths, host mount paths, epoch check names, and attestation policy digests: `trust-ci/tests/test_runner.py:201-246`.
- Worker dispatch selects the job-bound profile and stale binding avoids runner construction: `trust-ci/tests/test_worker.py:61-88`.
- Catalog profile digest scoping, order independence, exact case-sensitive lookup, duplicate/wildcard rejection, and canonicalized path digest behavior: `trust-ci/tests/test_policy.py:48-136`.
- Legacy catalog adapter preserves the legacy digest/check name: `trust-ci/tests/test_policy.py:40-46,138-143`.
- Repository-specific initial webhook binding and case-variant open rejection: `trust-ci/tests/test_api.py:149-181`.

## TDD/evidence assessment

The supplied implementation reports may pass, but passing tests do not compensate for the missing acceptance cases above. The exact head was reviewed directly; no code was changed by this review.
