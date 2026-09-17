# Tasks

- [x] Live facts re-collected read-only (systemctl all three units, socket /health, provider probe, profile model cross-check in the installed release).
- [x] Dossier + third service entry recorded; qualification flags untouched; 120 coupled tests OK; secret sweep clean.
- [x] Round 1: code review FAIL (10 carried-forward claims) closed by making each claim true, not by
      deleting it; test review PASS with a mutation map.
- [x] Round 2: re-review FAIL on the residue (7/8/9 untouched, 4/6 partly, N1 introduced by round 1)
      closed — verbatim 10-field three-unit capture, `production_verified:false` recorded, real
      `active_enter_timestamp` on all three services, `observed_at` aligned to the re-capture,
      README/START_HERE reconciled to three executors, SIG-001/AC-003 re-grounded on
      `Result`/`ExecMainStatus`/single start, third-unit pin added to `test_project_state`, capture
      windows and `source_trail` scope disclosed.
- [x] Round 3: two fresh reviewers on `3c379ca` — code review FAIL (F1–F6), test review PASS with
      contingencies. Closed: F1 (README:11/18 and START_HERE:59 falsified by this wave's own
      re-dating), F2 (boot-stamp attribution now per-unit and per-property, swap mutants killed),
      F3 (top-level `observed_at` re-capture alignment, now asserted and falsifiable two ways),
      F6 (INV-001 bound to the `code_review` receipt, which is what can falsify it) and the
      reviewer's own catch on the `db_row` source SQL, which did not run. Disclosed with
      measurements: F4 (six surfaces share one instant; what the pins do not assert) and F5
      (`route.json` keeps its routing-time base — 2 of 3 recently merged packages differ from
      their merge parent the same way).
- [x] Deferred state↔dossier omni equality implemented here instead of deferred again: identity
      leaves, every `acceptance` leaf against `dossier.omni.activation`, probe≠pilot, and the pilot
      block against its `db_row` (job, state, revision 3, `2026-09-17T00:21:16.151094Z`, 813/364).
      Remaining open item is a *live re-derivation* path for the provider leaves, tracked separately.
- [ ] `grok_verify --mode pr` on this head, receipts, PR, exact-head App check; close #86 with the merged record.
