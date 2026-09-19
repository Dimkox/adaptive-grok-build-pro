# Test review — issue #95

Result: **PASS for the #95 regression coverage; full PR preflight is NOT green.**

The focused tests pass in the current worktree (`/tmp/adaptive-fix-95-verifier`):

```text
python3 -m unittest tests.test_structure.StructureTests.test_grok_verify_rejects_script_from_another_repository tests.test_structure.StructureTests.test_grok_verify_root_identity_accepts_same_checkout -v
Ran 2 tests in 0.392s
OK
```

`test_grok_verify_rejects_script_from_another_repository` is the cross-root subprocess regression: it runs a copied verifier from `source` with `target` as cwd, asserts nonzero exit and a diagnostic containing both resolved roots, and asserts the target `.grok-stack/runtime` was not created. The second test, `test_grok_verify_root_identity_accepts_same_checkout`, only tests the same-root predicate (`ROOT` and `ROOT/scripts/..`); it does **not** launch the verifier end-to-end. This distinction is important: the required cross-root CLI path is covered, while same-root end-to-end verifier behavior remains covered only by the broader preflight, which currently has an unrelated failure.

The recorded full PR preflight is not a green gate: the `factory-postgres-exit` check failed in `factory.tests.test_postgres_integration.PostgresIntegrationTests.test_http_intake_deduplicates_fresh_proof_and_conflicts_on_command_reuse` because the intake returned HTTP 422 where the test expected success. The test module binds `NOW = datetime.now(timezone.utc).replace(microsecond=0)` at import, and the authority contract (`M0AuthorityV1.from_dict`) rejects `observed_at` values older than 300 seconds (`stale_m0`). The test sets the refreshed proof to `NOW - timedelta(seconds=2)` and then performs substantial database/API work; by the failing request that proof can exceed the 300-second freshness bound. This is a separate pre-existing factory test timing issue, not evidence against or in favor of the #95 root-identity change. It must remain recorded as a failed preflight; no claim that `grok_verify --mode pr` passed is warranted.

Scope limitation: this review covers test adequacy and the supplied preflight failure evidence only. It does not certify the independent code review, external Trust CI, or merge eligibility.
