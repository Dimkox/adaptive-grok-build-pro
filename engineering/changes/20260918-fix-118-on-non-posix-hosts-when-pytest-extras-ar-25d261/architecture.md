# Architecture — Fix #118: on non-POSIX hosts when pytest extras are installed and workers is an explicit integer, capability-selected grok_verify must degrade to sequential test execution instead of failing; add a Windows-emulated regression test.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`parallel_engine_ready()` checks importability only. `select_engine()` consequently returns positive workers and `pytest-xdist`; `_pytest_command()` later raises on non-POSIX because process-group cleanup is POSIX-only. `workers="auto"` avoids the defect because `selected_workers()` already maps it to zero on non-POSIX. Core and Trust CI share `select_engine()`, so one early capability decision can fix both paths.

## Proposed behavior

Add a narrow `_parallel_process_cleanup_supported()` capability predicate (or equivalent) and require it alongside dependency importability in `select_engine()`. If explicit positive workers are requested where safe parallel process cleanup is unavailable, return `(0, "unittest-degraded")` before pin checks and execution. Keep `_pytest_command()`'s refusal as a defensive invariant. Do not change POSIX dependency pinning or coverage qualification.

## Components and boundaries

Only `.grok-stack/adaptive_grok/python_test_runner.py` selection and its focused tests change. Verification owns check reporting; runner output continues to disclose actual workers/engine. No API or data contract changes.

## Data flow

## API and event contracts

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Platform process cleanup is part of backend capability, not a late command-construction precondition.
- Windows stays sequential; cross-platform process-tree management is outside this fix.

## Risks and mitigations

- Risk: an overbroad fallback could hide broken/mismatched dependencies. Mitigation: degrade only for unsupported process-cleanup platform; keep strict pin failures when xdist remains selectable.
- Risk: tests that globally patch `os.name` affect pathlib. Mitigation: isolate the platform predicate in a narrow patchable seam.
