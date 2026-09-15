# Focused baseline

Before implementation the 62 existing live-executor/SSE tests passed in 2.605s using the installed release virtualenv interpreter with local factory/src:delivery/src on PYTHONPATH and PYTHONDONTWRITEBYTECODE=1. Installed source and dependencies were not edited.

Command:
```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=factory/src:delivery/src /opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/venv/bin/python -m unittest factory.tests.test_landing_live_executors factory.tests.test_landing_sse
```

An earlier run with system python executed the same62 tests but one fixture import failed because uvicorn was absent. This was an interpreter/dependency mismatch, not a source regression.

Full verification will set UV_FROZEN=1 because the existing disposable PostgreSQL runner invokes uv run; this prevents the verifier from re-resolving the tracked lock during its source-stability window. No dependency changes are part of this repair.
