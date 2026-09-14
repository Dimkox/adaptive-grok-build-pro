# Docs/issue research — offline test execution & L5 coverage floors (agent docs_researcher)

## (a) Offline execution of factory tests without web/db deps

1. #57 requires the offline case be distinguishable: without pinned deps the documented commands give
   33/1/5 fake failures — 22 `psycopg`, 10 `fastapi`, 1 `uvicorn`. Its proposals: `grok_doctor` must emit
   `FAIL test-deps:<pkg>` instead of letting them surface as test errors, and `unittest.loader._FailedTest`
   must be reported as "N suites not collected", never counted as test failures. Pin set named there:
   fastapi==0.128.2 httpx==0.28.1 uvicorn==0.48.0 psycopg[binary]==3.3.4 pypdf==6.18.1 — same list as
   `factory/pyproject.toml:9`.
2. #51 proposal 1 requires exactly the split this change serves: "Run factory discovery in the gate
   without a database. Split `factory/tests` into DB-dependent and DB-free" and add `factory-unittest-all`;
   the DB-free set "already written to skip cleanly (skipped=139)". Proposal 5: stop pretending
   `factory-unit` is the factory suite; drive the list from a manifest asserted to cover every
   `factory/tests/test_*.py`.
3. mistakes.md:592-595 ("Relied on an undeclared host-only test dependency") is the durable precedent: a
   test imported a third-party package the gated env does not declare, host verification masked it, pinned
   runner failed. Prevention: keep tests dependency-free where practical and verify import parity in the
   exact pinned runner.
4. decisions.md:544-546 ("Exercise host ownership with real offline resources") blesses real FastAPI import
   **for the host fixture**: private temp sibling roots + synthetic actors give real FastAPI/SQLite/
   writer-exclusion/lifespan tests without provider or PostgreSQL. Constraint for this change: decoupling
   must not weaken the host tests — the offline module must stop inheriting, the host module must keep
   executing.
5. decisions.md:484 precedent: offline fixture executor is injected "without importing httpx into the API
   module" — same boundary direction.
6. The coupling is real and self-contradicting in-tree: `factory/tests/test_landing_backup.py:36-65` spawns
   a subprocess with an `importlib.abc.MetaPathFinder` guard blocking `adaptive_factory.api/.server/
   .landing_host/.landing_server/.landing_live_executors/psycopg/httpx/uvicorn/fastapi` — yet
   `factory/tests/test_landing_backup.py:18` does `from factory.tests.test_landing_host import HostFixture`,
   and `factory/tests/test_landing_host.py:17` is a module-level `from fastapi.testclient import TestClient`.
   Without fastapi the offline backup/restore boundaries are not skipped — they are uncollectable (loader
   ERROR), i.e. the offline guarantee is only observable in an environment that already has the web stack.

## (b) Coverage floors / per-module execution evidence for L5

7. The only threshold is `.coveragerc:15` -> `fail_under = 74`, and it cannot apply to L5: `.coveragerc:3-5`
   measures only `.grok-stack/adaptive_grok` + `scripts`; `factory/src` is not in scope at all. No coverage
   config exists in `factory/`.
8. #63 requirement 2 names the missing mechanism: "Per-module coverage floor for the landing path … add a
   coverage measurement over `factory/src/adaptive_factory/landing_*.py` to the verification matrix, so 0%
   on a module that writes to a production disk path is a failing check rather than an invisible statistic."
   `landing_backup.py` is listed there at 244 stmts / 0%.
9. #63 requirement 3 bullet 1 is this change's acceptance content: `landing_backup` restore must not
   overwrite at the same path, recovery must not replay the provider, the single lifetime SQLite writer
   lock must survive a killed predecessor.
10. #63 requirement 1 currently *holds* slice 4 (`landing_publication_cli`/`landing_backup`/
    `landing_pdf_worker`) until tests execute failure/recovery paths — this change is the precondition, not
    a violation. #63 requirement 4 still blocks slice 4 on governance-module imports in the publication CLI
    (`production_import` fitness) and `urllib.parse` in delivery.
11. Gate mechanics to cite: `.grok-stack/adaptive_grok/verification.py:882-896` runs `factory-unit` over
    hardcoded `('contracts','state','migrations','service')`; `:897-915` self-skips `factory-postgres-exit`
    under `GROK_VERIFY_CAPABILITY=repository-sandbox`.
12. #60 is a counter-example to respect: an exact literal (`len(records) == 39`) made two green PRs merge
    red; prefer derived/floor assertions over pinned counts when adding coverage checks.
13. #80 is unrelated to this change (10 MB tracked-binary diff analysis, local-route-only red).
14. `engineering/adr/` contains only `.gitkeep`; no ADR and no runbook states a coverage floor or an
    offline-import rule. `engineering/contracts/` does not exist. `QUICKSTART.md:108` documents coverage
    `fail_under 74` as optional local tooling only.

## Verdict
- Satisfies: #63 req 3 (`landing_backup` destructive boundaries), #51 proposal 1 (DB-free/web-free
  collectability), mistakes.md:595 prevention rule, #57 spirit (fake red -> real signal).
- Contradicts: nothing. Tension only with #63 req 1 (slice 4 held) — this change pays it down.
- **No existing issue covers the coupling defect as stated** ("an offline test module must not import a
  web-stack-bound test fixture"). Searches `HostFixture`, `fixture coupling`, `fastapi test import`,
  `offline test suite` over all 200 issues return #57/#56/#63 only, and none of them describes the
  test-source import graph: #57 is env gap + doctor classification, #51 is gate execution breadth, #63 is
  0%-coverage and slice ordering. Worth filing as new.
