# Tasks — Fix Trust CI human approval CLI: approval-create and approval-submit must run from a source checkout on a human-controlled host without importing API, worker, PostgreSQL, or other server-only dependencies; add regression tests and reproducible operator setup documentation without weakening signature verification or exposing private keys

- [x] Freeze contracts and expected behavior.
- [x] Add failing test or characterization test.
  - Fail-first command: `PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest -v trust-ci/tests/test_cli.py`
  - Pre-fix result: exit `1`; both subprocess regressions failed before dispatch with
    `ImportError: blocked server-only import: adaptive_trust_ci.api`.
- [x] Implement the smallest vertical change.
- [x] Close test-review blocker with deterministic execution of every relocated
  non-human command branch, exact import-slice assertions and fake terminal effects.
- [x] Run selected quality profile.
- [x] Complete independent reviews.
- [x] Bind evidence to the final tree fingerprint.
