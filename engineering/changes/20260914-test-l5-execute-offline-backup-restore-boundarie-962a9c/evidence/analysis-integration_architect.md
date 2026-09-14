# Integration-architect: what `grok_verify.py --mode pr` executes for factory tests
Route 20260914-test-l5-execute-offline-backup-restore-boundarie-962a9c, profiles base,contracts.

## 1. Factory test modules actually executed
- `factory-unit` — `.grok-stack/adaptive_grok/verification.py:882-897`: hardcoded allow-list
  `('contracts','state','migrations','service')` (`verification.py:883-887`), run as
  `[sys.executable, '-m', 'unittest', factory.tests.test_*]`, cwd=root, 300s.
  Verified on host: `python3 -m unittest factory.tests.test_contracts ...test_service` -> Ran 51 tests OK.
- `factory-postgres-exit` — `verification.py:897-915`: pr/release only, runs
  `factory/tests/run_disposable_exit.py` (spawns Docker+Postgres; imports `adaptive_factory.server`,
  uv inside container). Self-skips iff `GROK_VERIFY_CAPABILITY=repository-sandbox`
  (`verification.py:899`; decisions.md:20).
- Env: gate `run()` merely copies os.environ (`util.py:76-86`) — no PYTHONPATH set, no uv/pip install
  inside the gate. Offline imports work only because `factory/tests/__init__.py` prepends `factory/src`,
  `delivery/src`, `.grok-stack` to sys.path. Third-party deps (fastapi) are NOT installed in the host python.
- Adjacent (not factory): `pilot-unittest` `unittest discover -s pilot/tests -t .`
  (`verification.py:833-841`); `python-unittest` `coverage run --rcfile=.coveragerc -m unittest discover
  -s tests` (`verification.py:854-860`) — host has no `pytest` binary (`verification.py:845` branch not
  taken), so this path is live in pr mode.

## 2. Is the missing-fastapi defect invisible? YES
- No check imports/discovers `factory/tests` beyond the 4 allow-listed modules; there is NO
  `unittest discover -s factory/tests` anywhere (Makefile discover targets cover trust-ci only).
- `factory/tests/test_landing_backup.py:18` `from factory.tests.test_landing_host import HostFixture`;
  `test_landing_host.py:17` `from fastapi.testclient import TestClient`. Reproduced:
  `python3 -m unittest factory.tests.test_landing_backup` -> ModuleNotFoundError: fastapi, FAILED (errors=1).
- Static gates cannot see it: ruff/bandit scan `QUALITY_PY_PATHS` (`verification.py:727-742`) which includes
  `factory/src/adaptive_factory` but NOT `factory/tests`, and ruff does not resolve imports.
- `tests/test_landing_architecture_boundaries.py:17-24` references landing_backup.py only as path strings —
  passes without importing.

## 3. Coverage threshold location
- `.coveragerc`: `[run] source = .grok-stack/adaptive_grok, scripts`; `[report] fail_under = 74`.
- Enforced by the `coverage` check `coverage report --rcfile=.coveragerc` (`verification.py:862-867`),
  pr/release only, and only on the non-pytest (unittest) path. It measures top-level `tests/` only;
  factory is neither a coverage source nor executed by that discover — new factory tests cannot raise or
  satisfy the 74% gate.

## 4. Cheapest evidence command for "the backup/restore boundary tests really execute"
- `python3 -m unittest factory.tests.test_landing_backup -v` from repo root. Currently FAILS on the fastapi
  import, which is exactly the defect; after the split this same command is the reviewer artifact.
- Note: the file currently defines 15 `def test_` methods (not 16) — reconcile the spec count.
- If real third-party deps must stay: `uv` (`~/.local/bin`) + `factory/uv.lock` allow
  `uv run --project factory python -m unittest factory.tests.test_landing_backup` from repo root
  (untested here; slower, network-install — prefer the offline path).

## Conclusion
A change confined to `factory/tests/test_landing_backup.py` / `test_landing_host.py` / a new factory
test-support file is covered by NO executed pr-mode check (factory-unit allow-list, no discover, no ruff,
no coverage). Verification for this slice must therefore be an explicit recorded command, not a gate signal.
