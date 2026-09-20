# Test plan — issue #158

| P | Scenario | Evidence |
| --- | --- | --- |
| P0 | adopted orphan reaped at lease boundary; control keeps the zombie | `test_lease_boundary_reaps_adopted_child`, `test_control_without_a_reaping_boundary_keeps_the_zombie` |
| P0 | no status theft (the dangerous mutation) | `test_drain_preserves_the_return_code_of_a_tracked_child`, `test_naive_unbounded_sweep_does_steal_the_status`, `test_sweep_declines_entirely_while_any_spawn_is_in_progress` |
| P0 | classification intact (timeout / heartbeat / missing runtime) | `test_timeout_path_still_classifies_as_timeout_and_releases_its_guard`, `test_heartbeat_failure_still_raises_after_reaping`, `test_missing_runtime_classification_is_unchanged` |
| P1 | guard coverage by AST + real decorator | `test_every_spawn_call_site_is_inside_a_guarded_region`, `test_guarded_sites_are_exactly_the_worker_spawn_helpers`, `test_run_is_really_wrapped_by_the_spawn_guard` |
| P1 | real PID-1 pair in a disposable container (red `[8]` → green `[]`) | recorded in `evidence/reaping-arms.md` |
| P2 | `ContainerExecutor.run` coverage added (previously zero) | `test_missing_runtime_classification_is_unchanged` + guard-balance arms |

Automated: `make trust-ci-test` (canonical: `PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests`) →
**257 OK (skipped=10)** vs baseline **243 OK**; `make trust-ci-compile`; `git diff --check`; `ruff check` on touched
files (repo `ruff.toml` applies — `trust-ci/pyproject.toml` defines no `[tool.ruff]`);
`GROK_VERIFY_CAPABILITY=repository-sandbox UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr`.

Manual: confirm no `.grok-stack/**` or `factory/**` edit; confirm the live worker was not restarted and existing
pre-deploy zombies are reported as operator-cleared, not claimed as fixed.

Note for runners: a bare `python3 -m unittest discover -s trust-ci/tests -t trust-ci` without `PYTHONPATH` yields 25
loader `ImportError`s — that was my own false alarm today, not a product defect; use the Makefile target.
