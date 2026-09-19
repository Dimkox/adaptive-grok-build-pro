# Fix #118: on non-POSIX hosts when pytest extras are installed and workers is an explicit integer, capability-selected grok_verify must degrade to sequential test execution instead of failing; add a Windows-emulated regression test.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260918-fix-118-on-non-posix-hosts-when-pytest-extras-ar-25d261`
Created: 2026-09-18T01:21:05+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

With explicit `workers > 0`, `select_engine()` currently selects pytest-xdist whenever its modules are importable. On Windows, `_pytest_command()` then rejects the run because process-group cleanup requires POSIX. The sequential unittest path already exists but is never selected for this platform case.

## Outcome

On non-POSIX hosts, PR/release verification with an explicit positive worker count runs the existing sequential unittest/coverage path and truthfully reports `unittest-degraded`. POSIX hosts retain current xdist behavior when dependencies meet their strict pins.

## Scope

### In scope

- Include process-cleanup platform capability in parallel-engine selection before launching either Core or Trust CI tests.
- Add Windows-emulated tests for Core and Trust engine selection and the resulting sequential path.
- Preserve strict dependency version failures when the host is POSIX and xdist is selected.

### Out of scope

- Implementing Windows process-tree cleanup or enabling parallel execution on Windows.
- Changing worker configuration syntax, dependency pins, or coverage qualification rules.
- Modifying Trust CI deployed images or policy.

## Constraints

- Backward compatibility: only the previously failing non-POSIX + positive-workers combination changes; `auto`, zero workers, POSIX xdist, and missing/mismatched pin behavior remain as defined.
- Data/privacy: no data or external service access.
- Performance: non-POSIX explicit parallel requests become serial; this is the safe supported backend there.
- Operational: output must disclose actual engine and selected worker count.
