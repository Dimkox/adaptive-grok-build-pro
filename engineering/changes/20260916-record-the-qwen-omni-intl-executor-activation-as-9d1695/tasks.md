# Tasks

- [x] Live facts re-collected read-only (systemctl all three units, socket /health, provider probe, profile model cross-check in the installed release).
- [x] Dossier + third service entry recorded; qualification flags untouched; 120 coupled tests OK; secret sweep clean.
- [x] Round 1: code review FAIL (10 carried-forward claims) closed by making each claim true, not by
      deleting it; test review PASS with a mutation map.
- [x] Round 2: re-review FAIL on the residue (7/8/9 untouched, 4/6 partly, N1 introduced by round 1)
      closed — verbatim 10-field three-unit capture, `production_verified:false` recorded, real
      `active_enter_timestamp` on all three services, `observed_at` aligned to the re-capture,
      README/START_HERE reconciled to three executors, SIG-001 re-grounded on
      `Result`/`ExecMainStatus`/single start, a first per-unit capture pin added to
      `test_project_state`, capture windows and `source_trail` scope disclosed.
- [x] Round 3 (on `3c379ca`): two fresh reviewers — code review FAIL (F1–F6), test review PASS with
      contingencies. Closed: F1 (README:11/18 and START_HERE:59 falsified by this wave's own
      re-dating), F2 (the capture pin checked presence, not attribution; per-unit blocks added and
      swap mutants killed), F3 (the document's top-level `observed_at` left older than the section the
      wave had re-dated, with the date pin making it load-bearing), F6 (INV-001 bound also to the
      `code_review` receipt, which is what can falsify it), plus the reviewer's own catch on the
      `db_row` source SQL, which did not run.
- [x] Round 4: the deferred state↔dossier omni equality implemented rather than deferred a fourth
      time — identity leaves, every `acceptance` leaf against `dossier.omni.activation`, probe≠pilot,
      and the pilot block against its `db_row` (job, `artifact_ready`, revision 3,
      `2026-09-17T00:21:16.151094Z`, usage 813/364).
- [x] Round 5: the author's round-4 dismissal of F5 was **wrong and is corrected**: `route.json`'s
      pre-rebase base drove the gate's own comparison basis, so a records wave was measured over another
      PR's production code (40 files from the stale base against 22 from the real merge-base); the base
      is re-pointed, `base_fingerprint` left untouched on stated grounds. Adds the first anti-relabelling
      guard. Both round-5 delta reviews returned PASS.
- [x] Round 6: closes what those reviews named as HIGH — identity and pilot-state **literals**, because
      agreement between two in-tree files cannot anchor either (`selected_profile == qwen-omni-intl`,
      `installed_sha == observed_main_sha == dossier.source_base`, `pilot.state == artifact_ready`);
      the five-word `TERMINAL_STATES` blacklist replaced by membership in `landing_observation.CATEGORIES`
      plus the recorded value; `observed_at` ordering asserted where it can be; the `factory/src`
      bootstrap hoisted to module scope so the method runs in isolation (a defect also present on
      `main`). AC-003 gains the `NRestarts` caveat whose absence the round-5 review proved
      programmatically.
- [x] Disclosed as limits rather than closed: a consistent move of all three observation stamps inside
      the pinned day is unfalsifiable in-tree; no test shells out to `systemctl`/`journalctl`/sockets, so
      liveness is never asserted; `route.json`'s committed base documents intent while the value the gate
      actually reads lives in the gitignored runtime copy; and the *live re-derivation* path for the
      provider probe leaves is a separate concern, tracked as #121.
- [ ] `grok_verify --mode pr` on this head, receipts, PR, exact-head App check; close #86 within the
      scope stated in the PR body (enablement half only; contract declaration stays in #104; per-media
      acceptance not claimed).
