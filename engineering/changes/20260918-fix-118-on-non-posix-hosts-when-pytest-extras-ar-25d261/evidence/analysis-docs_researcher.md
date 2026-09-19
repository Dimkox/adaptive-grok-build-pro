# Documentation and package analysis — issue #118

## Findings

- GitHub issue [#118](https://github.com/Dimkox/adaptive-grok-build-pro/issues/118) is narrowly about the opt-in local Python test runner: when pytest, pytest-xdist and pytest-cov are importable on Windows, an explicit positive integer worker request currently selects xdist and then `_pytest_command()` rejects the non-POSIX process-cleanup path. The already-existing sequential unittest/coverage path can satisfy the request. `workers: "auto"` and `workers: 0` already select sequential mode on non-POSIX.
- The user-facing contract for the runner is operationally documented in the prior #33 retake package (`engineering/changes/20260916-implement-capability-selected-engine-sharding-fo-8ed0fb/`). Its design explicitly records capability-based selection, pre-execution degradation, truthful `unittest-degraded` labeling and preservation of strict dependency pinning when parallel execution is available. #118 should extend this same decision with platform capability: xdist requires both its Python dependencies and the POSIX process-group cleanup capability. Otherwise select the sequential engine before execution and expose the actual backend in check details.
- This is local verification tooling, not a public application/API contract. `README.md`, `START_HERE.md`, architecture diagrams and release identity do not need a behavioral change for this fix. The active change package does need complete durable context: brief outcome/scope, architecture decision/data flow, acceptance criteria covering positive integer workers on emulated Windows with parallel extras available, test plan and the evidence limitation that the regression is emulated on POSIX unless a real Windows runner is supplied.

## Documentation and compatibility guidance

- Keep the prior rule that degradation happens before invoking pytest; do not catch `_pytest_command()` refusal and retry after partial execution. The selected backend and worker count must describe the backend actually used.
- Retain the configured worker count as input/intent, but use the existing sequential command and coverage instrumentation on unsupported platforms. Dependency-pin failures must remain strict when a platform-capable xdist engine is selected.
- A regression test should monkeypatch both `os.name` and parallel-module availability, then exercise the public `select_engine`/runner decision. A test only asserting `_pytest_command()` raises or only testing `workers=0` would not protect issue #118.
- No canonical governance or machine-readable API/event contract was found to be affected. The package is currently incomplete (`brief.md` has placeholder outcome/scope; requirements and change-spec acceptance criteria are empty), so those artifacts should be completed before implementation/verification evidence is treated as sufficient.

## Sources inspected

- `gh issue view 118 --json title,body,labels,url` (read-only): exact symptom, reproduction, suggested behavior, related issue #109.
- `.grok-stack/adaptive_grok/python_test_runner.py`: `selected_workers`, `parallel_engine_ready`, `select_engine`, `_pytest_command`, and core/trust test dispatch.
- `engineering/changes/20260916-implement-capability-selected-engine-sharding-fo-8ed0fb/{brief.md,architecture.md,requirements.md,test-plan.md,release.md}`: prior platform/engine contract and test evidence boundary.
- `PROJECT_STATE.json` and `START_HERE.md`: #33 retake delivered via PR #113; current runner contract is recorded as capability-selected, sequential degradation on pytest-free interpreter.
- `decisions.md` and `mistakes.md`: no decision that requires Windows xdist; prior records favor lazy capability selection and tests that make unsupported platform paths explicit.

## Assessment

The issue is consistent with the shipped contract rather than requiring a new product feature: “capability-selected” should include the runner's process-management platform requirement. No external documentation update is needed; complete the change package and add the platform rule to `decisions.md` only if the implementation confirms the single pre-execution selection point is the robust correction.
