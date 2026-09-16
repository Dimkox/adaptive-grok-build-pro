# Capability-selected test engine (defect 33 re-take)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Why the original died

PR #33 shipped a real sharding runner but hard-bound the parallel path to pinned pytest/xdist/cov being *importable*: on the Trust CI image (no pytest) its own suite asserted parallel-only properties, so the mandatory `root-unittest` command exited 1 (7 failures, one stating "pytest missing"). Closed unmerged on 2026-09-16 with the condition recorded: select the engine from what the interpreter provides; tests satisfiable without importable pytest.

## What this wave does

Ports the preserved head (runner + suite + pin file + `_python`/`_command_check` wiring) and pivots the contract: `select_engine()` decides **before** execution — xdist only when `pytest`, `xdist` (+`pytest_cov` when measuring) are importable, otherwise exactly one sequential unittest/coverage pass, labeled `unittest-degraded` in the check details. With the engine importable the old strict pin contract stands (missing/mismatched versions fail; no silent serial retry). Degraded-observable assertions in the suite are engine-conditional, not deleted.

## Verified

19 tests OK on this pytest-free host — the same condition as the Trust CI runner. External exact-head check completes the proof for the real image.
