# Operational verification: FAIL for the requested two-service target

The source deployed for acceptance was the already merged 26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960, whose tree matches the independently attested PR150 head. No application source was edited. The full local product verifier was intentionally not rerun under AGENTS.md's no-op rule; this record is not a claim that grok_verify executed.

Passed before cutover: installed source comparison (62 factory and 10 delivery files), unchanged dependency inventory, pip check and 19 targeted backup/migration/recovery tests (1.258 s, exit 0). The exact named test commands and output are in focused-verification.txt. Independent security, data and release reviews inspected the actual cutover/acceptance scripts; three further bounded reviews covered Qwen rollback.

Both backups completed before offline v1→v2 startup. Original counts were preserved. Each service received one fixed acceptance POST. Grok passed exact-profile, same-job sealed receipt/artifact checks, then an observe-only replay of the GET returned the same artifact. Qwen's executor reported usage 761/195, but draft decoding failed; no artifact exists. AC-001 and AC-003 remain unmet. Its complete failed v2 state is retained, and its prior schema1 snapshot and original unit are restored. A GET-only historical-artifact check passed with the original digest and no provider call.

After writing the handoff, ran these two existing tests with the target installed interpreter (exit 0, 2 tests, 0.072 s):

```
python -m unittest tests.test_project_state.ProjectStateTests.test_current_epoch_and_app_are_consistent_in_handoff_documents tests.test_project_state.ProjectStateTests.test_runtime_observations_are_source_bound_without_promoting_qualification
```

A bounded structural check parsed each new operational script and JSON file, verified the newest PROJECT_STATE service facts equal final-runtime.json, checked acceptance/observation artifact equality, retained Qwen's failed exit and absent artifact, and checked zero POSTs in recovery. git diff --check passed. These checks validate the operational handoff; they do not convert Qwen failure into acceptance. No route-ready or release-complete claim is made.
