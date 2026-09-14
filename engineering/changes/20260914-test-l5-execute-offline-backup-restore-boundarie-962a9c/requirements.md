# Requirements — test(l5): execute offline backup/restore boundaries without web-stack fixture coupling

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] **AC-001** Given an interpreter without `fastapi`, `uvicorn`, `httpx` or `psycopg`, when
      `python3 -m unittest factory.tests.test_landing_backup -v` runs, then the whole suite is collected and
      executed with **0** loader errors (today: 1 loader error, 0 real tests executed).
      Measured: `Ran 16 tests … OK`, 0 loader errors, 0 skips.
- [x] **AC-002** Given the new offline support module, when a subprocess guard blocks `adaptive_factory.api`,
      `.server`, `.landing_host`, `.landing_server`, `.landing_live_executors`, `psycopg`, `httpx`, `uvicorn`
      and `fastapi`, then importing `factory.tests.landing_host_fixture` and building its fixture reaches
      none of them — and the guard test is itself collectable without those packages.
      Measured, and proven non-vacuous by the eleven mutation checks M0–M10 in
      `evidence/coverage-before-after.md` §4.
- [x] **AC-003** `factory/tests/test_landing_host.py` keeps identical scaffolding (path fields, 0700 roots,
      0600 config, synthetic actors bound to `TARGET_REPOSITORY_ID`, `live_enabled=false`) and keeps
      `build_app`; no host test body is weakened, skipped or deleted.
      Measured by execution on a deps-complete interpreter: 36 host tests `OK` on the base tree and `OK` on
      this tree with identical test-name sets (§7), plus the byte-faithful-move check.
- [x] **AC-004** `evidence/coverage-before-after.md` records measured per-module coverage for the modules
      this suite reaches, before and after, so executed boundaries are visible rather than inferred.
      Recorded on three explicit bases; every number re-derived independently in review round 2.
- [ ] **AC-005** `python3 scripts/grok_verify.py --mode pr` passes for the committed tree and no
      architecture-fitness or inventory rule is newly violated by the added test-support file.
      Fitness and inventory are green here (`tests.test_architecture_fitness` 101 `OK`, contracts 34 `OK`);
      the gate itself can only bind a fingerprint after this tree is committed, so its result is recorded as
      the `verification` receipt under `.grok-stack/runtime/receipts/` and reported in the pull request
      rather than pre-checked here.

## Failure and edge cases

- The `sys.path` bootstrap lives in `factory/tests/__init__.py`; the support module must be reachable as
  `factory.tests.landing_host_fixture` without any package installation.
- `reopen_store()` registers `addCleanup(store.close)` and several backup tests also call `.close()`
  explicitly — the double-close path must stay byte-equivalent.
- `unittest discover -s factory/tests` must keep ignoring the support file (name must not start with
  `test_`) while the backup module imports it as a module, not as a test.
- `HostFixture` must stay resolvable from `test_landing_host.py` so its ~20 host tests need no body edits and
  any external reference keeps working.
- Environment gaps that must not be reported as product defects (#57): `test_landing_host`, `test_landing_api`,
  `test_api`, `test_server`, `test_workspace` and the PostgreSQL suites still need the pinned deps; the
  pdf-worker suite still skips without `pypdf` 6.18.1 and reports 0% because it runs in a child interpreter.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt,
or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: `FIT-BOUNDED-FACTORY-TEST-CHANGE`, `FIT-BOUNDED-FACTORY-CHANGE`
  (`architecture/rules.yaml:76-114`) — `FIT-BOUNDED-FACTORY-SOURCE-CHANGE` does not apply because
  `factory/src/**` is untouched.
- Canonical-example deviations and evidence: none; the change follows the existing flat-helper precedent
  (`factory/tests/postgres_restart_probe.py`, `factory/tests/run_disposable_exit.py`).
- Intentional debt created, repaid, or accepted: repays part of #63 (backup boundaries never executed) and
  #51 proposal 1 (web-free collectability); accepts as follow-up the `test_semantic_persistence` fastapi
  coupling and the missing per-module coverage floor.

## Non-functional requirements

- Security: no new dependency, no install step, no network, no secret or credential file access; private
  root modes preserved.
- Reliability: the offline boundary must fail loudly (loader error) if the coupling regresses; guard test is
  the tripwire.
- Performance: no measurable change; the suite already ran in ~8 s where deps existed.
- Observability: recorded test count and per-module coverage percentages before/after (SIG-001, SIG-002).
