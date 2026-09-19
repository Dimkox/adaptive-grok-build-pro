# Requirements — Fix #118: on non-POSIX hosts when pytest extras are installed and workers is an explicit integer, capability-selected grok_verify must degrade to sequential test execution instead of failing; add a Windows-emulated regression test.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given a non-POSIX host with explicit `workers > 0` and importable pytest/xdist modules, when Core tests are selected, then the selector chooses `workers=0` and `unittest-degraded` before dependency pinning or process launch.
- [ ] Given the same host/configuration, when Trust CI tests are selected, then they use the sequential unittest path and report the actual engine without raising the POSIX cleanup error.
- [ ] Given a POSIX host with explicit positive workers, when the parallel engine is importable, then xdist selection and strict version-pin validation remain unchanged.
- [ ] Given any host with workers set to `auto` or `0`, when engine selection runs, then existing behavior is preserved.

## Failure and edge cases

- Selection is deterministic and occurs before launching child processes.
- Non-POSIX fallback reports actual execution mode; it must not claim parallelism.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none identified by read-only analysis; routing/verification governance is unchanged.
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security:
- Reliability:
- Performance:
- Observability:
