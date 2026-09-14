# Release plan — test(l5): execute offline backup/restore boundaries without web-stack fixture coupling

## Deployment

Nothing is deployed. The change touches only test infrastructure (`factory/tests/`); `factory/src/**`,
`delivery/src/**`, the installed Claw release `/opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a`,
its unit, config, state and artifacts are all untouched. Landing is a `main` commit plus the ordinary
release-line consequences (next artifact carries the extra test file); no tag, no GitHub Release and no
runtime activation belongs to this change.

## Feature flags / staged rollout

No flag, no gate, no rollout ladder: there is no runtime behavior to stage. The effect is immediate and
host-dependent only in the sense that the repaired suite now collects wherever `fastapi`, `uvicorn` and
`psycopg` are absent — which is exactly the environment where it previously reported nothing.

## Metrics and alerts

- `offline_landing_backup_collected_test_count` (SIG-001): read from
  `python3 -m unittest factory.tests.test_landing_backup -v` — expected 16, 0 loader errors, 0 skips.
  A regression to a loader error is self-announcing: the suite stops reporting 16.
- `landing_backup_measured_coverage_percent` (SIG-002): read from
  `coverage run --source=factory/src/adaptive_factory -m unittest factory.tests.test_landing_backup` +
  `coverage report -m` — expected 84% for `landing_backup.py`, 80% for `landing_host_config.py`. Neither is
  enforced by any gate yet (FORBID-003); this is a measured signal a reviewer reads, not an alert.
- No product metric, log line, or alert rule changes.

## Go/no-go criteria

Go requires all of:

1. `python3 -m unittest factory.tests.test_landing_backup -v` → 16 tests, `OK`, zero loader errors, zero skips.
2. Adjacent and gating checks green on this tree: `factory.tests.test_landing_publication_cli
   factory.tests.test_landing_sse` (50 `OK`), `tests.test_architecture_fitness
   tests.test_landing_architecture_boundaries tests.test_change_spec` (135 `OK`),
   `discover -s factory/tests -t .` still 430 tests with the same 36 dependency-gated errors and 7 skips.
3. `python3 scripts/grok_verify.py --mode pr` passes on the committed tree, and `verification`,
   `code_review`, `test_review` receipts are bound to that fingerprint with zero evidence gaps.
4. No `factory/src/**` or `delivery/src/**` file in the diff; no test skipped, deleted or relaxed
   (FORBID-001…003).

No-go: any of the above red, or a reviewer finding left unresolved. Post-merge, the next full-suite run on
a deps-complete host is the outstanding confirmation for the real-FastAPI host suite (AC-003 limitation in
`evidence/coverage-before-after.md` §6); this change cannot certify it here.
