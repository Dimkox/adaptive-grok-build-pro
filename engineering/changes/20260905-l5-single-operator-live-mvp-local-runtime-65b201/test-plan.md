# Test plan — L5 single-operator live MVP local runtime

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | PDF/audio and unavailable profile terminate before executor or network | `test_landing_normalizer.py` |
| P0 | SQLite exact submit/cancel replay, isolation, terminal persistence, and bounded interrupted-state recovery | `test_landing_sqlite_store.py` |
| P0 | Existing coordinator and packager produce one fully bound deterministic artifact | `test_landing_runtime.py` |
| P1 | Existing in-memory API behavior, frozen identities, and `live_url=null` remain compatible | focused existing landing tests |
| P1 | Optional reversible port performs only deterministic fake effects and is absent from composition | focused delivery test if implemented |

## Automated checks

- Unit: normalizer validation/outcome matrix and SQLite path/schema/replay/recovery.
- Integration: injected provider -> existing coordinator -> existing artifact
  packager; no live process, network, or target mutation.
- Contract: typed change spec and existing landing contracts; frozen OpenAPI bytes
  are not edited.
- E2E: none during implementation. The final route verifier is run once only
  after the complete product tree is frozen.
- Static analysis: targeted Ruff and Bandit on changed Python, JSON/spec syntax,
  architecture checks when the new modules are registered, and `git diff --check`.

## Manual checks

- Confirm package ZIP/sidecar, landing OpenAPI, migrations `001`-`018`, and exact
  landing source identity are unchanged from predecessor `f3f8d737...`.
- Confirm no live model/network/publisher configuration or non-null live URL is
  introduced.
