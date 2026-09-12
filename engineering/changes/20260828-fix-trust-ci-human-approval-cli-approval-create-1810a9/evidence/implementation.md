# Implementation evidence — human approval CLI import repair

Route: `1810a99eee3c`
Write owner: `data_implementer`

## Fail-first reproduction

After adding fresh-process import guards and before changing production code:

```text
$ PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest -v trust-ci/tests/test_cli.py
test_approval_create_runs_without_server_imports_and_preserves_envelope_contract ... FAIL
test_approval_submit_posts_exact_bytes_without_server_or_crypto_imports ... FAIL

ImportError: blocked server-only import: adaptive_trust_ci.api
Ran 2 tests in 0.653s
FAILED (failures=2)
```

This is the expected failure: both real human commands import the API dependency
graph before argument dispatch. The create regression uses only an ephemeral
test-only Ed25519 key in a temporary directory; the submit regression targets only a
loopback standard-library HTTP server. No operational key, approval or deployed API
is accessed.

## Implemented slice

- `cli.py` now keeps only standard-library imports at module scope and imports each
  product dependency inside its selected command branch. `approval-submit` has no
  package-local dependency; `approval-create` loads only model, policy and signing.
- The regression executes top-level help, both human help paths, a real disposable
  approval creation and an exact-byte loopback submission in fresh subprocesses.
- The operator runbook now defines a minimal `cryptography==46.0.4` environment,
  canonical policy-digest comparison, exact review context, distinct envelopes for
  every missing scope, response handling and final App-owned Check Run verification.
- No root README change was needed: its Trust CI node, identity and connections are
  unchanged, and it already links the detailed Trust CI runbook.

## Focused and compatibility evidence

```text
$ PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest -v \
    trust-ci/tests/test_cli.py trust-ci/tests/test_signing.py trust-ci/tests/test_store.py
Ran 24 tests in 1.304s
OK

$ PYTHONPATH=trust-ci/src:trust-ci/tests uv run --no-project \
    --with 'cryptography==46.0.4' --with 'fastapi==0.128.2' \
    --with 'psycopg[binary]==3.3.4' --with 'uvicorn==0.48.0' \
    --with 'httpx==0.28.1' \
    python3 -m unittest discover -s trust-ci/tests -v
Ran 149 tests in 2.227s
OK (skipped=8)
```

The eight skips are the pre-existing PostgreSQL integration cases because
`TRUST_CI_TEST_DATABASE_URL` is not configured in the isolated test environment.
Focused API acceptance and tamper-rejection tests passed separately. A fresh venv
containing only pinned `cryptography` ran both documented help paths and all three
new CLI regressions successfully. Ruff, compileall and `git diff --check` passed.

The analysis-captured SHA-256 values for packaged SQL, `store.py`, `api.py`,
`models.py` and `signing.py` are unchanged on this implementation tree. There is no
schema, endpoint, envelope, signature, policy, trust-store or durable-state change.

## Residual risk

The existing approval insert/requeue transaction gap and same-head multi-PR lookup
edge remain unchanged and require separate API/data work. Route-level
`grok_verify --mode pr`, configured PostgreSQL integration, independent reviews and
fingerprint-bound receipts remain controller-owned completion steps; no deployment,
approval submission or operational-key access occurred here.

## Test-review repair

The first independent test review correctly identified that human-path coverage did
not execute the other command branches whose imports moved. A parameterized test now
executes all 17 affected non-human branches through `cli.main`, injects deterministic
fake modules for every server/operator dependency, asserts the exact imported module
set for each command, and verifies a command-specific safe terminal effect. This
catches omitted, misspelled, wrongly located and unrelated command-local imports
without network, PostgreSQL, backup deletion, kill-switch mutation, GitHub writes or
key access.

Evidence after this test-only repair:

```text
$ PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest -v trust-ci/tests/test_cli.py
Ran 4 tests in 1.348s
OK

$ PYTHONPATH=trust-ci/src:trust-ci/tests uv run --no-project \
    --with 'cryptography==46.0.4' --with 'fastapi==0.128.2' \
    --with 'psycopg[binary]==3.3.4' --with 'uvicorn==0.48.0' \
    --with 'httpx==0.28.1' \
    python3 -m unittest discover -s trust-ci/tests -v
Ran 150 tests in 2.306s
OK (skipped=8)
```

The same eight environment-gated PostgreSQL integration tests remain skipped; no
database or migration source changed. This repair changes only tests and change
evidence, not the lazy-import implementation or any trust/data contract.
