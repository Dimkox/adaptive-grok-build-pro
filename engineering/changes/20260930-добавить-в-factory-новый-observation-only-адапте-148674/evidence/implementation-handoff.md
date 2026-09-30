# Implementation handoff

Initial source commit: `6e170318`; review repairs are recorded by the later branch head.

## Delivered

- closed versioned Qwen/OpenRouter candidate registry with exact upstream provenance;
- default-off deterministic selection and cooldown advice;
- bounded caller-owned transport attempts with retry only before response start;
- fatal authentication, payment, daily-limit and policy outcomes;
- tenant/repository/task/run/attempt/fence/budget/registry binding on evidence;
- incomplete usage remains unknown and forces `needs_human`;
- no endpoint, credential, header/body, home-directory or settings interface.

The source repository `Dimkox/qwen-model-rotator@f91ead60dfab81912e8224f9eab503e8cbc09976`
had no observed license. Its code was not copied; the independent implementation uses only
the explicitly authorized behavioral idea and records provenance.

## Verification observations

- RED: `PYTHONPATH=factory/src python3 -m unittest factory/tests/test_model_rotator.py`
  failed because `adaptive_factory.model_rotator` did not exist.
- Focused GREEN: the same command passed 7 tests.
- Related GREEN: model rotator, landing failover and prediction contracts passed 17 tests.
- Factory discovery GREEN: `PYTHONPATH=factory/src taskset -c 0-27 python3 -m unittest discover -s factory/tests -t factory -p 'test_*.py'`
  passed 956 tests with 166 conditional skips in 74.015 seconds.
- An exploratory full `grok_verify --mode pr` reached repository coverage and was cancelled
  on coordinator request to avoid contending with the authoritative integrated run. It is
  `NOT_RUN` for completion purposes; no verification receipt was recorded.

Live provider calls and qualification are `NOT_RUN`. Independent route reviews and the
authoritative integrated full verifier remain coordinator-owned.

## Review repairs

- Runtime execution now requires a store-authorized exact binding; PostgreSQL migration
  027 validates current task/run/fence/lease/reservation and atomically persists unique
  operation claims, replay evidence, cooldowns and cursor. It intentionally depends on
  the integrated branch's migration 026, so standalone full migration discovery remains
  `NOT_RUN` until integration.
- The closed transport result rejects inconsistent status/category/digest/usage facts.
  Unknown and over-limit usage stop as `needs_human`; active/all-model cooldowns prevent
  dispatch. Evidence stores only digests of opaque identities.
- Upstream advanced to `f91ead60dfab81912e8224f9eab503e8cbc09976`; its own suite passed
  53 tests. The exact archive/file hashes and clean-room exclusions are recorded in
  `upstream-inventory.json`.
- Focused repaired suite: 14 tests pass. Live providers and integrated PostgreSQL remain
  `NOT_RUN`; no verification or review receipt is claimed here.

Second-review repair replaces descriptive authority with independently admitted grant facts
and a leased/CAS state machine. Canonical wire digests are recomputed in SQL; task, run,
attempt, repository-derived tenant, fence, live lease and reservation-derived budget digest
are checked under row locks. Dispatch capacity is held before calls, settled cumulatively on
completion, and held through ambiguity until explicit `settle` or `release` reconciliation.
Focused concurrency, crash/quarantine, request-quota and canonical SQL assertions now total
17 passing tests. PostgreSQL execution still awaits integration immediately after migration 026.

Third-review repair removes all runtime table mutation grants. Runtime receives only narrow
`SECURITY DEFINER` claim/reserve/finish/quarantine functions and a safe pseudonymous status
view; only the independent migrator/reconciliation authority may settle or release quarantine.
Every reserve and finish rechecks task/run/attempt/fence/live lease/reservation and the
server-derived budget digest. Capacity accounting is reservation-scoped, binding limits are
persisted, claims are leased, and expired same-operation claims atomically quarantine before
independent reconciliation. The enabled-only cursor is covered against the bundled registry.
Focused suite: 18 passing tests; integrated PostgreSQL remains conditional on migration 026.
