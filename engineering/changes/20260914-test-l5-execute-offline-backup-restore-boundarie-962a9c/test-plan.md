# Test plan — offline landing backup/restore boundaries without web-stack fixture coupling

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Offline collectability: suite imports and executes with no fastapi/uvicorn/httpx/psycopg installed | `python3 -m unittest factory.tests.test_landing_backup -v` (0 loader errors, 16 tests) |
| P0 | Offline support module never reaches the web stack (guard subprocess) | `test_offline_test_support_imports_no_web_stack` |
| P0 | Destructive boundaries really run: non-overwriting restore, copy-budget reservation before root creation, committed-WAL snapshot, manifest/content tamper rejection, symlink/hardlink rejection, concurrent-writer exclusion | existing 15 `test_landing_backup.py` methods, now executed |
| P1 | Host suite keeps real-FastAPI behavior | `test_landing_host` diff review + `python3 -c "import factory.tests.test_landing_host"` (deps-gated) |
| P1 | Discovery ignores the helper, test module count unchanged | `python3 -m unittest discover -s factory/tests -t . -v 2>&1 | grep -c '^test_'` shape check |
| P1 | No fitness/inventory regression | `python3 -m unittest tests.test_architecture_fitness` |
| P2 | Measured coverage delta recorded | `evidence/coverage-before-after.md` |

## Automated checks

- Unit: `python3 -m unittest factory.tests.test_landing_backup -v`;
  `python3 -m unittest factory.tests.test_landing_publication_cli factory.tests.test_landing_sse`
  (adjacent offline landing suites, no regression). There is no `test_landing_host_config` module: the
  host-config cases live inside `test_landing_host.py`, which is dependency-gated and cannot execute here.
- Integration: not applicable — no product source, no service, no database is touched.
- Contract: `python3 -m unittest tests.test_landing_architecture_boundaries tests.test_change_spec`.
- E2E: not applicable in this change; the L5 host E2E stays dependency-gated (#57).
- Static analysis: `ruff check .`, `bandit -c bandit.yaml -r scripts .grok-stack factory/src` per profile, plus
  `python3 scripts/grok_verify.py --mode pr`.

## Manual checks

- Read the `test_landing_host.py` diff and confirm only imports/fixture plumbing changed, no assertion lost.
- Confirm `factory/src/**` and `delivery/src/**` are untouched (`git diff --name-only`).
- Confirm no `skip`, `expectedFailure`, deleted test or relaxed assertion appears in the diff
  (`git diff | grep -n "skip\|expectedFailure\|- *def test"`).
