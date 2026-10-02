# Implementation report

## Identity and transplant

- Old base: `fa49dc35fb77ecfc0172209ecafd3427c5ee3251`
- Old head: `5c06cc146896fb48668291455fcbd7e23d8770a9`
- New base: `01b089fcbf417d69f8a21407ea41941436ce74d4`
- Five old commits were replayed in order with `git rebase --onto`; `git range-diff`
  reports `=` for all five commits and stable patch IDs match.
- The original product contour remains the same 15 paths. The follow-up repair
  touches only its schema/tests/restart probe plus the authoritative release plan
  path correction and this active change package. PR1 tail verifier files were not
  reverted or modified.

## Red/green evidence

- Schema admission red: the new contract test failed with `KeyError: 'x-admission'`.
  Green: the dependency-free `SubsetValidator` now accepts the valid structural
  wire, kills missing/extra/nested-extra/enum/digest mutations, and demonstrates
  that secret text and self-supersession are deliberately rejected only by native
  semantic admission.
- Restart decision red: the new migration characterization failed because
  `_canonical_restart_decision` did not exist. Green: the actual PG17 probe creates
  one canonical state decision, binds it atomically to its phase transition, and
  checks the exact record digest and cardinality before and after both restarts and
  after exact replay at each restart.
- The first disposable PostgreSQL suite exposed an existing test-double mismatch:
  its `_audit` override did not accept the contour's `received_at` argument. The
  override now preserves and forwards that exact audit timestamp; the formerly
  failing test passes.
- Focused modules: 44 tests passed (`decision_contracts`, `context_contracts`, root
  v1.5 context schema, and migrations).
- Full disposable PG17 module suite: 819 tests passed, 2 skipped after the repair.
- Focused actual restart probe: passed with two real PostgreSQL restarts, exact
  runtime/attestor roles, exact decision digest/cardinality and idempotent replay.
- `git diff --check` and Python compilation of the restart probe passed.
- Full-harness regression red: the isolated restart preflight failed before database
  access because `postgres_restart_probe.py` imported the discovered contract test,
  which in turn required root-only `tests.json_schema_subset`. Green: the shared
  factual fixture now lives in dependency-free `factory/tests/decision_fixtures.py`;
  the exact disposable harness completed 820 tests with 2 skips, two PostgreSQL
  restarts, capability-role checks and restart/reconciliation PASS.

## Architecture-budget repair

The first repair moved 15 KB of Factory assertions to non-discovered root helpers
and incorrectly claimed fitness success. Independent review identified that as a
governance bypass: the helpers were outside both Factory ownership and
`FIT-BOUNDED-FACTORY-TEST-CHANGE`.

The corrected contour keeps all assertions under `factory/tests` and adds only
`tests/test_factory_v15_decisions.py` as a root-discovery shim; both prefixes are
one union budget. Exact accounting then failed at 793281/775000 bytes. Charged
inventory was: decision contract cases 7858, decision persistence cases 14472,
restart probe 63903, contract shim 225, PostgreSQL shim 833, execution PostgreSQL
278221, landing API 18184, migrations 45479, PostgreSQL integration 363785, and
root discovery shim 188 bytes.

Restoring any charged legacy PostgreSQL module byte-identical was rejected because
its original migration-22 expectations and TRUNCATE list fail after migration 023;
moving tests outside the union was the already-rejected bypass, and splitting the
change would separate required migration compatibility evidence from its contour.
The route-approved bounded recalibration is 800000 bytes: a 25000-byte (3.23%)
increase, leaving 6719 bytes (0.84%) at the measured 793281-byte contour. Line
limit 7500, AST-complexity limit 600, severity `error`, and both exact prefixes
remain fixed by regression coverage; executable tests prove union accounting plus
fail-closed rejection at 800001 bytes.

## Scope and residual risk

This is the bounded U2 decision-persistence foundation only. Generic decision
sources, non-empty evidence, registered context/profile sources, read/export API,
and durable cost/timing integration remain deferred. Migration 023 is append-only
and forward-only after application; rollback retains schema-23-capable code and
disables the optional decision seam, or restores a separate schema-22 database.

The coordinator must still run the exact-tree full PR verifier, persist independent
code/test reviews, record fresh receipts and perform any authorized transport.
