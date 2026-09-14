# test(l5): execute offline backup/restore boundaries without web-stack fixture coupling

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260914-test-l5-execute-offline-backup-restore-boundarie-962a9c`
Created: 2026-09-14T02:33:56+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

`factory/tests/test_landing_backup.py` is the offline backup/restore boundary suite for the L5 production
runtime. Its own first test spawns a subprocess with an `importlib.abc.MetaPathFinder` guard that fails if
importing `adaptive_factory.landing_backup` reaches `adaptive_factory.api`, `.server`, `.landing_host`,
`.landing_server`, `.landing_live_executors`, `psycopg`, `httpx`, `uvicorn` or `fastapi`
(`test_landing_backup.py:36-65`).

Yet the module cannot be collected at all without that web stack, because `test_landing_backup.py:18` is
`from factory.tests.test_landing_host import HostFixture` and `test_landing_host.py:17` is a module-level
`from fastapi.testclient import TestClient` (plus `:19` → `landing_host` → `uvicorn`, `:29` →
`adaptive_factory.server` → `uvicorn`). Measured on this host (no fastapi/uvicorn/psycopg installed):

```
python3 -m unittest factory.tests.test_landing_backup
→ ImportError: Failed to import test module: test_landing_backup ... No module named 'fastapi'
→ Ran 1 test ... FAILED (errors=1)
```

So the offline guarantee is observable only on a machine that already has the web stack, and the entire
destructive-boundary suite (non-overwriting restore, copy-budget reservation before any root is created,
committed-WAL snapshot, manifest/content tamper detection, symlink/hardlink rejection, concurrent-writer
exclusion) never executes offline. In the executed factory suite `landing_backup.py` measures **12%** and
`landing_host_config.py` **22%** for exactly this reason.

The coupling is incidental: the backup suite uses only `HostFixture.setUp`, `write_config` and
`reopen_store`, never `build_app` — the single member that touches `landing_host`/`TestClient`.

## Outcome

The L5 offline backup/restore boundaries execute on a machine with no web or database packages installed,
and the offline contract is enforced by a test that itself does not need the web stack. Reviewers get real
execution evidence for the code that writes production disk paths instead of a loader error that hides it.

## Scope

### In scope

- New `factory/tests/landing_host_fixture.py`: offline-only fixture subset (`ROOT_FIELDS`, `PATH_FIELDS`,
  `setUp`, `write_config`, `reopen_store`).
- `factory/tests/test_landing_host.py`: imports the subset and keeps `HostFixture` as a subclass adding
  `build_app`; every web-stack import stays where it is functionally used; test bodies untouched.
- `factory/tests/test_landing_backup.py`: one import line changes; adds
  `test_offline_test_support_imports_no_web_stack`, the guard test that is collectable offline.
- `evidence/coverage-before-after.md`: measured per-module coverage before and after.

### Out of scope

- Any `factory/src/**` or `delivery/src/**` behavior change.
- The second incidental coupling found (`test_semantic_repair_lifecycle.py:16-17` and
  `test_semantic_store_runtime.py:13-14` → `test_semantic_persistence.py:5` fastapi) — follow-up change.
- Adding a coverage **floor** or a `factory-unittest-all` gate check (#63 req 2, #51) — needs its own change;
  enforcing it now would turn the matrix red for environment reasons.
- L5 host runtime tests (`test_landing_host`, `test_landing_api`, `test_api`, `test_server`, `test_workspace`,
  PostgreSQL suites) which legitimately require the pinned dependencies (#57).

## Constraints

- Backward compatibility: `HostFixture` must remain importable from `factory.tests.test_landing_host` with
  identical behavior; no test renamed, skipped, deleted or relaxed.
- Data/privacy: fixture keeps synthetic actors, private 0700 roots, 0600 config; no real credential, actor
  or key file is read.
- Performance: no new dependency, no install step, no network; suite runtime stays within the existing
  ~8 s observed for the 5 landing runtime modules.
- Operational: `.coveragerc` (`fail_under = 74`) and the verification matrix stay unchanged; rollback is a
  single forward-fix revert of test-infrastructure files.
