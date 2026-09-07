# Write evidence — general_implementer

Change: `20260906-inert-control-flow-shells-must-not-become-ambigu-f88955`
Route: `f88955abe6a5`
HEAD at implementation: `5fb36e5f9cbaf3983ced6965646c7250ac79241e`

## Changed files

- `.grok/hooks/_lib.py` — `is_proven_inert_read_shell` after `_command_directory_aliases`; `proven_units == 0` fail-closed
- `.grok/hooks/pre_tool_use.py` — promotion exemption; catch-all `authority_shape` on objective material only
- `tests/test_hooks.py` — extended inert-read allow list; `;;;` / `;` deny; `true; ; true` allow
- `tests/test_pre_tool_circuit_breaker.py` — distinct/same catch-all shapes and classified coarseness
- Change-package brief/requirements/architecture/test-plan/tasks/change-spec.yaml
- `mistakes.md`, `decisions.md`

## Commands

```
python3 -m unittest tests.test_hooks tests.test_pre_tool_circuit_breaker tests.test_policy tests.test_protected_write_hook tests.test_policy_shell_targets -v
```

Result: 64 tests, OK.

Review repair: separator-only shells (`;;;`, `;`) no longer prove inert. `is_proven_inert_read_shell` counts allowlisted reads and proven `cd`/`pushd` skips; `proven_units == 0` returns False so promotion still assigns `ambiguous-sensitive-shell`. `true; ; true` still allows.

```
python3 -m unittest tests.test_hooks tests.test_pre_tool_circuit_breaker -v
```

Result: 36 tests, OK.

`python3 scripts/grok_verify.py --mode pr` was started after the focused suite; it did not finish within 300s in this session. Reviews should treat the focused unittest command as the implemented verification evidence and re-run `grok_verify --mode pr` if the full profile is required.

Classified coarseness is proven with two curl POSTs that share the deny-reason string (same resource, different bodies). Distinct URLs still hash separately because classified objectives include the full policy `reason` and were not reshaped.

## Residual risk

- Nested `bash -lc` with `;` and `git --no-pager log` remain unproven over-denies.
- Unknown unproven shells with an empty authority shape still share one catch-all objective.
- Quoted `;` inside a non-allowlisted command (`python3 … --reason "a; b"`) still hits the raw control-flow regex and is unproven, so it still promotes.
- Separator-only `;;;` / `;` now fail closed (`proven_units == 0`) and deny as `ambiguous-sensitive-shell`.
