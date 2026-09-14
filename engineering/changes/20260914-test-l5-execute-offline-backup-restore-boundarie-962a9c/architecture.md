# Architecture — offline landing backup/restore boundaries without web-stack fixture coupling

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`factory/tests/test_landing_host.py` owns both halves of one fixture: the offline host-configuration
scaffolding (`ROOT_FIELDS`/`PATH_FIELDS`, `setUp` private roots + synthetic actors, `write_config`,
`reopen_store`) and the web-stack half (`build_app`, which imports `adaptive_factory.landing_host` and
`fastapi.testclient`). `test_landing_backup.py:18` inherits the whole class to reuse the offline half, so it
inherits the web-stack imports at module level. On a host without the pinned deps the offline boundary suite
is a loader **error**, not a skip — it never collects, so the destructive boundaries cannot be exercised
where the web stack is absent (this host, and the gate: `factory-unit` runs only
`contracts/state/migrations/service`, `.grok-stack/adaptive_grok/verification.py:882-897`).

## Proposed behavior

A dependency-free test-support module owns the offline half; the host test module keeps the web half and
re-exports the fixture under the same name for its own tests.

```
factory/tests/landing_host_fixture.py     ROOT_FIELDS, PATH_FIELDS, HostFixture (setUp/write_config/reopen_store)
        ↑ import                                ↑ subclass HostFixture(+build_app)
factory/tests/test_landing_backup.py      factory/tests/test_landing_host.py
```

`test_landing_host.py` declares `class HostFixture(landing_host_fixture.HostFixture)` containing only
`build_app`, so its ~20 tests resolve the same name with the same members and need no body edits.
`test_landing_backup.py` imports the support module directly and gains a guard test proving the offline
boundary.

## Components and boundaries

- Added: `factory/tests/landing_host_fixture.py` (test infrastructure, not product code, not a
  `test_*.py`, so `unittest discover` ignores it).
- Modified: `factory/tests/test_landing_host.py` (imports + fixture subclass), `factory/tests/test_landing_backup.py`
  (one import line + one new guard test).
- Unchanged: every `factory/src/adaptive_factory/landing_*.py` module, `.coveragerc`,
  `architecture/rules.yaml`, `architecture/system.yaml`, `scripts/**`.

## Data flow

Test process → `landing_host_fixture.HostFixture.setUp` creates a private temp root, writes `host.json`
(0600) and 0700 sibling roots, builds synthetic `Actor` set for `TARGET_REPOSITORY_ID` → `reopen_store()`
opens `SQLiteLandingJobStore` against the state path → product code under test (`landing_backup`) performs
its own filesystem/SQLite work. No HTTP, no provider, no PostgreSQL, no real credential file.

## API and event contracts

None. No HTTP route, event schema, or stored-data contract changes; the change is confined to test
infrastructure and evidence.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt,
or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: `FIT-BOUNDED-FACTORY-TEST-CHANGE` (7500 lines / 775000 bytes / AST 600,
  `architecture/rules.yaml:106-114`), `FIT-BOUNDED-FACTORY-CHANGE` (`:76-83`).
  `FIT-BOUNDED-FACTORY-SOURCE-CHANGE` (`:86-93`) is scoped to `factory/src` and stays untouched.
- Applicable canonical example IDs/versions: flat test-helper precedent
  `factory/tests/postgres_restart_probe.py`, `factory/tests/run_disposable_exit.py`
  (imported as `from factory.tests import ...`, `factory/tests/test_migrations.py:7`).
- Open or overdue debt IDs: #63 (0%-executed L5 runtime boundaries — paid down for `landing_backup`),
  #51 proposal 1 (web-free collectability), #57 (env-fake red), new: `test_semantic_persistence.py:5`
  fastapi coupling for two offline-looking suites.
- Expected governance handoff or receipt impact: `verification`, `code_review`, `test_review` receipts bound
  to the final tree fingerprint; no governance JSON change.

## Bitrix-specific impact

- Not applicable: no Bitrix module, component, agent, event or core path is involved; the route selected no
  Bitrix domain.

## Decisions

1. Subclass-and-re-export instead of renaming `HostFixture`: keeps `test_landing_host.py` bodies and any
   external reference valid, minimizing the diff to the reviewed host suite (see
   `evidence/analysis-architect.md` §3).
2. No `sys.modules` stubbing, no `try/except ImportError` + skip: a skip would re-hide the boundary the change
   exists to expose, and FORBID-002 forbids making tests "pass" by skipping.
3. The offline guard moves from a property of the product import to a property of the test support module too
   (AC-002), so the coupling cannot silently return.
4. Coverage stays measured, not enforced, in this change (FORBID-003): a floor would go red for environment
   reasons until #51 lands `factory-unittest-all`.

## Risks and mitigations

- Risk: weakening the host suite's isolation while splitting. Mitigation: `test_landing_host.py` keeps real
  FastAPI per decisions.md:544-546; AC-003 requires identical scaffolding and `build_app`; review inspects the
  full diff.
- Risk: double `store.close()` behavior drift. Mitigation: `reopen_store` moves verbatim; backup tests keep
  their explicit closes (INV-002).
- Risk: invisible to the gate, so a future regression goes unnoticed. Mitigation: the new guard test is itself
  offline-collectable, so any reintroduced web-stack import turns into a loud loader error on any host.
- Risk: helper picked up by discovery or by an inventory check. Mitigation: filename not `test_*`; no
  registration is required (architect §4); discovery shape asserted in the test plan.
