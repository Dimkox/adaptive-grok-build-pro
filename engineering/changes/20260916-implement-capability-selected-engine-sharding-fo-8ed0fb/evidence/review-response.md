# Review response — #33 re-take (capability engine selection)

Code review PASS (2 Important, 5 Minor) and test review PASS (Important F1/F2, Minor F3/F7, honest mutant list) on `275b804`; all closed in one round.

| Source | Finding | Disposition |
| --- | --- | --- |
| code #1 Important | trust CLI printed the **requested** workers for a degraded run (`workers=8` over a serial pass) and recorded no engine | **Fixed**: `main()` now selects the engine itself and prints `requested_workers=…; workers=<effective>; engine=…`; the run carries the disclosure. |
| code #2 Important / test F3 | xdist-only arms only mock-proven while docs claimed executed coverage; `continue` made the worker-loss subtest silently assertion-free | **Fixed both**: `skipTest` (reports `skipped=1`), and architecture/test-plan/brief/AC-004 now state exactly which arms run here (serial/degrade) versus where xdist arms execute (the App check's image). |
| test F1 | no test exercised the repo's own default path (AC-003 parity was fixture-only) | **Fixed**: `test_repo_root_without_optin_keeps_legacy_verifier_path` asserts no config at repo root, `selected_workers(root) is None`, and the emitted commands are the legacy serial ones with `pytest` never appearing. |
| test F2 | strict-pin test only covered missing-dependency; version equality untested (mutant H survived) | **Fixed**: two arms now — missing (`python-test-requirements.txt`) and wrong-version (`requires tested version`); mutant H dies. |
| test config survivors (P/Q/S) | workers 65/-1/1.5/True, `schema_version` 2, extra key, `GROK_TEST_WORKERS='65'/'invalid'` unasserted | **Fixed**: subTest arms added to the invalid-worker test plus direct `selected_workers` raises. |
| test F7 | `/proc`-based descendant checks are vacuous off Linux | **Fixed**: `skipTest` when platform is not linux. |
| code Minor | requested workers vanished from Core details (FORBID-002 says both recorded) | **Fixed**: `requested_workers` kept in check details alongside the used engine. |
| code Minor | `wait(timeout=10)` in `_stop` could escape as non-RunnerError | **Fixed**: bounded double-SIGKILL then `RunnerError('owned process refused to exit after SIGKILL')`. |
| code Minor | opt-in config untracked-visible; INV-002 wording | **Fixed**: `.grok-test-runner.json` gitignored (local opt-in stays local); wording adjusted; `find_spec` ≠ runtime-importable noted in architecture as by-design strict-pin failure for declared-but-broken installs. |
| code Minor | SIG-001 durations only on xdist arm | Accepted — durations are line-reported by both paths; metric wording kept (no claim of per-engine durations). |
| both | pre-existing `minimum/maximum` huge-int OverflowError | Out of scope (base behavior, unrelated keyword); left untouched and disclosed. |

## Limits

The xdist distribution/combine properties execute only where pytest exists (dev venv, App image); on this no-pytest host the degrade path, disclosure, parity and strict-pin arms are what actually run — that split is now stated in every document rather than blurred.
