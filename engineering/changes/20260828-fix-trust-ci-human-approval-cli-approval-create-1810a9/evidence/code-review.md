# Code review — human approval CLI import repair

Verdict: **PASS**

Route: `1810a99eee3c`
Role: `code_reviewer`
Base commit: `1c06299894279a88b881defa3f19b004fa742223`
Reviewed final pre-report fingerprint: `94a15e670d843cc6f4ab7f9d8bc9d2d11f6ea0d2e5b0e2272da84d9dbeecc258`

The prior code-review report reviewed the earlier
`d869b1f770034816c0ad487613e13e02022451b52c54df9b8c25f2720cf51395`
tree, and any prior code-review receipt necessarily predates the test-only update.
The branch-smoke addition made both stale; neither was reused for this verdict. This
report is based on a complete fresh inspection of the
`94a15e...cc258` tree, whose current verification receipt is also bound to that
exact fingerprint.

## Findings

No critical or important findings.

## Independent review evidence

- Reinspected the complete actual diff and untracked additions against the assigned
  base, including the updated 517-line CLI regression suite and surrounding CLI,
  API, model, policy, signing, store, and operational documentation.
- The new branch-execution smoke contains 17 cases covering every relocated
  non-human command: API, worker, migration apply/status, policy/holdout digest,
  doctor, keygen, trust-store validation, approval/attestation verification, branch
  protection, backup create/verify/prune, restore drill, and kill-switch status.
  Each case replaces command dependencies with tracking modules, calls the real
  parser and dispatch function, asserts the exact command-local import slice, and
  requires a branch-specific safe effect. The two human commands remain covered by
  the separate create/submit subprocess tests, so all 19 CLI commands are exercised.
- The smoke harness avoids product mutations: files, PostgreSQL, GitHub, Uvicorn,
  backup, restore, key, and worker effects are faked; paths live in a temporary
  directory; the token and database URL are disposable non-credentials; and the test
  confirms keygen did not write the placeholder key paths.
- The production change remains import routing only. Removing imports from the base
  and current CLI ASTs produces identical trees, which confirms command bodies,
  argument handling, outputs, return codes, and side-effect ordering were not
  otherwise altered.
- `approval-submit` remains standard-library-only and sends byte-identical envelope
  bytes. `approval-create` loads only models, policy, signing, and cryptography,
  creates a mode-0600 envelope, and the regression verifies it through the unchanged
  production verifier.
- `api.py`, `models.py`, `policy.py`, `signing.py`, `store.py`, and packaged SQL are
  unchanged from the base. The schema-v1 envelope, canonical Ed25519 signature,
  exact repository/PR/base/head/policy binding, actor/key/scope authorization, key
  lifecycle, TTL, replay, API response, and durable-state contracts are not weakened.
- The runbook continues to match implementation: pinned minimal operator dependency,
  reviewed source-checkout `PYTHONPATH`, canonical deployed-policy digest comparison,
  one fresh envelope per scope, actual response/error semantics, and final App-owned
  exact-SHA Check Run verification. It keeps human keys, policies, venvs, and signed
  envelopes outside agent and service workspaces and does not treat HTTP acceptance
  as merge authority.

## Fresh commands and results

```text
PYTHONPATH=.grok-stack python3 -c '<tree_fingerprint>'
=> 94a15e670d843cc6f4ab7f9d8bc9d2d11f6ea0d2e5b0e2272da84d9dbeecc258

git diff --check
=> PASS

python3 -m compileall -q trust-ci/src trust-ci/tests
=> PASS

ruff check trust-ci/src/adaptive_trust_ci/cli.py trust-ci/tests/test_cli.py
=> All checks passed

PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest -v trust-ci/tests/test_cli.py
=> Ran 4 tests; OK, including all 17 non-human branch cases

uv run --no-project --with pinned service/test dependencies --env-file /dev/null -- \
  python3 -m unittest discover -s trust-ci/tests -v
=> Ran 150 tests; OK (skipped=8 PostgreSQL integration tests because
   TRUST_CI_TEST_DATABASE_URL is not configured)

base/current non-import AST comparison
=> identical

base/current frozen contract file comparison
=> API, models, policy, signing, store, and packaged SQL unchanged
```

A broad `ruff check trust-ci/src trust-ci/tests` also reported two pre-existing F401
findings in unchanged `lookup.py` and `store.py`. The changed CLI and regression file
pass Ruff, and neither unrelated finding was introduced or affected by this patch.

## Residual risk

The eight live PostgreSQL integration cases were not executed without a configured
disposable database. This is non-blocking for this import/test-only delta: no SQL,
store, schema, API, model, policy, or signing file changed, while the full in-memory
API, signing, replay, store, runner, and new command-dispatch suites passed. The
previously documented approval-insert/requeue transaction gap and same-head multi-PR
lookup edge remain out of scope and are not worsened by this patch.

Any repository change after the stated pre-report fingerprint makes this review
stale and requires fresh verification and review evidence.
