# Test review — PASS

Route: `1810a99eee3c`
Role: `test_reviewer`
Reviewed base: `1c06299894279a88b881defa3f19b004fa742223`
Reviewed pre-report fingerprint: `94a15e670d843cc6f4ab7f9d8bc9d2d11f6ea0d2e5b0e2272da84d9dbeecc258`

## Verdict

**PASS.** The prior test-review blocker is fixed. The final test tree covers the
human import boundary and every non-human command branch affected by relocating CLI
imports. No critical or important test gap remains for this change.

## Prior blocker resolution

`CommandBranchImportTests` in `trust-ci/tests/test_cli.py:67-340` parameterizes all
17 relocated non-human branches:

- `api`, `worker`, `migrate`, `migration-status`, `policy-digest`,
  `holdout-digest`, and `doctor`;
- `keygen`, `trust-store-validate`, `approval-verify`, and
  `attestation-verify`;
- `branch-protect`, `backup-create`, `backup-verify`, `backup-prune`,
  `restore-drill`, and `kill-switch`.

Each case calls the real `cli.main(arguments)` dispatcher, injects tracking modules
for the relocated dependencies, asserts equality with the command's exact expected
module slice, and requires a command-specific terminal effect. Thus missing or
misspelled symbols fail execution, wrongly placed or unrelated `from` imports change
the observed slice, and a branch that stops before its intended operation fails its
effect assertion.

The fakes keep execution safe: API/worker/database/GitHub/backup/signing operations
only append in-memory events; restore uses a disposable-invalid URL only as an
argument to a fake; `kill-switch` uses `status`; `keygen` asserts no key files were
created. The test performs no network call, database access, backup deletion,
kill-switch mutation, GitHub write, or real key access.

The exact expected slices match the actual relocated imports in
`trust-ci/src/adaptive_trust_ci/cli.py:103-359`. All 19 CLI commands are covered when
the 17 branch cases are combined with the two real human command regressions.

## Human-path evidence preserved

- **Fail-first validity:** the final human regression file run against base commit
  `1c0629…` fails before dispatch at the eager
  `adaptive_trust_ci.api` import. This reproduces the original root cause.
- **Fresh-process guards:** top-level help and both human help paths run in new
  subprocesses with server modules and `cryptography` blocked. `approval-create`
  blocks API, worker, PostgreSQL, settings, backup, GitHub, holdout, migration,
  FastAPI and Uvicorn; `approval-submit` additionally blocks `cryptography`.
- **Disposable real signing:** `approval-create` uses an ephemeral test-only
  Ed25519 key, asserts mode 0600, parses the envelope, and verifies the unchanged
  production signature plus exact repository, PR, base/head SHA, policy digest,
  actor-authorized scope, and TTL limit.
- **Exact-byte submission and proxy isolation:** the submit test posts to a
  loopback standard-library server, asserts `/approvals`, content type, user agent,
  and byte-for-byte body equality, while removing upper/lower-case HTTP, HTTPS and
  ALL proxy variables and forcing loopback `NO_PROXY`.

## Independent executions

```text
PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest -v \
  trust-ci/tests/test_cli.py trust-ci/tests/test_signing.py trust-ci/tests/test_store.py
Ran 25 tests in 1.389s
OK
```

```text
PYTHONPATH=trust-ci/src:trust-ci/tests uv run --no-project \
  --with cryptography==46.0.4 --with fastapi==0.128.2 \
  --with 'psycopg[binary]==3.3.4' --with uvicorn==0.48.0 \
  --with httpx==0.28.1 \
  python3 -m unittest discover -s trust-ci/tests
Ran 150 tests in 2.002s
OK (skipped=8)
```

The eight skips are the unchanged PostgreSQL integration cases gated by
`TRUST_CI_TEST_DATABASE_URL`. No database, migration, store, API, model, policy, or
signing source changed, so the missing disposable-database environment is a residual
integration limitation rather than a blocker for this import-routing repair.

The `grok_verify --mode pr` receipt is PASS and is bound to the reviewed pre-report
fingerprint `94a15e…`; its recorded git-diff, secret, contract, SQL-safety, Ruff,
Bandit, root-unit and coverage checks all passed. The exact pinned Trust CI command
is now recorded in implementation evidence and was independently reproduced above.

## Residual risk

The branch test uses deterministic fakes, so it verifies dispatch, symbol resolution,
exact dependency slices and safe effects rather than live server infrastructure.
The full module suites cover the underlying components, and the unchanged PostgreSQL
integration tests remain environment-gated. Final controller verification and review
receipts must be rebound after evidence reports change the repository fingerprint.

No test-review blocker remains. This local review is workflow evidence only and is
not merge authority.
