# Tasks — offline landing backup/restore boundaries without web-stack fixture coupling

- [x] Freeze contracts and expected behavior: change-spec `OBJ-001`, AC-001…AC-005, INV-001/002,
      FORBID-001…003; route `962a9cd9fe34` profiles `base,contracts`.
- [x] Record the analysis wave (`repo_explorer`, `architect`, `docs_researcher`, `integration_architect`)
      under `evidence/`.
- [x] Capture the red state as a fact: `python3 -m unittest factory.tests.test_landing_backup` → loader
      ImportError (no module named 'fastapi'), 0 of 15 boundary tests executed; executed-suite coverage
      `landing_backup.py` 12%, `landing_host_config.py` 22%.
- [x] Characterization/red test that is itself collectable offline:
      `factory/tests/test_landing_backup.py::LandingBackupTests::test_offline_test_support_imports_no_web_stack`.
      Non-vacuity proven by eleven scratch checks (M0–M10) in `evidence/coverage-before-after.md` §4.
- [x] Implement the smallest vertical change (single write owner): add `factory/tests/landing_host_fixture.py`,
      subclass it in `test_landing_host.py`, switch the `test_landing_backup.py` import. No product source,
      no new dependency, no test body touched.
- [x] Measure and record coverage before/after into `evidence/coverage-before-after.md` (SIG-001, SIG-002),
      on three explicitly labelled bases after review round 1 found the original "before" column wrong.
- [ ] Run selected quality profile: focused offline run `Ran 16 … OK`, adjacent `Ran 50 … OK`, contracts
      `Ran 34 … OK`, `tests.test_architecture_fitness` `Ran 101 … OK`, root suite `Ran 654 … OK`, `ruff`
      clean on all three files, factory discovery `Ran 430 … errors=36, skipped=7` (all 36 pre-existing
      dependency gaps) — done; then `GROK_VERIFY_CAPABILITY=repository-sandbox UV_LOCKED=1
      python3 scripts/grok_verify.py --mode pr` on the committed tree, which is the remaining step.
- [x] Complete independent reviews against the final tree: `evidence/code-review.md` (rounds 1–5:
      pass/3 Minor, pass/3 Minor, pass/1 Minor, pass/1 Minor, pass — all eight findings closed in code and
      each pinned by a reproduced mutation; round 5 additionally stress-tested relative `PYTHONPATH`) and
      `evidence/test-review.md` (round 1 **fail** on a real evidence defect, round 2 pass with all 12
      coverage numbers reproduced). Reviewer-stated policy for this change, recorded so a later contributor
      does not mistake it for the implementer's own waiver: a further latent, unreachable-by-construction
      nit in `foreign()`'s containment predicate may be booked as accepted debt here — with the predicate,
      its exact reachability precondition and the one-line fix shape — instead of opening another round.
      There is no open finding at the time of writing. `code_review` / `test_review` receipts are recorded
      only after the verification receipt on the same fingerprint.
- [ ] Bind evidence to the final tree fingerprint; transition the change to `ready`.
- [ ] Deliver: isolated branch → pull request; merge only on the App-owned exact-head Trust CI success with an
      exact delegated grant. Deployment of the merged SHA remains a separately delegated operation.
