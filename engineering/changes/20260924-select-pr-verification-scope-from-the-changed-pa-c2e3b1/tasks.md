# Tasks — Select PR verification scope from the changed-path inventory (issue 205)

- [x] Freeze contracts and expected behavior. `verification_scope.py` exposes
      `select_docs_state_scope(...) -> dict`, `focused_command(targets) -> list[str]` and the
      admitted-role constants; the report key is `docs_state_scope` with `evidence_kind`
      `verification:docs-state-focused` or `verification:full-pr-suite`. The landing lane's
      `verification_scope` key stays reserved and untouched.
- [x] Add failing test or characterization test. `tests/test_verification_scope.py` was written
      against the v2.0.19 release-sync and artifact-child inventories (the case issue 205 is
      about) plus the rename/copy/status shapes, before the classifier existed.
- [x] Implement the smallest vertical change. Classifier module plus two seams in
      `verification.py` (`_docs_state_status_inventory`, `_python`/`_focused_python`), one
      `rename_detection` flag in `util.changed_file_statuses`, and the `docs-state-scope` reported
      check. No new service, queue, dependency or storage.
- [x] Run selected quality profile. `python3 -m unittest tests.test_verification_scope -q`, the
      38-module parallel sweep at `-P 5`, `ruff` over `.grok-stack/adaptive_grok`, `scripts` and
      `tests`, `git diff --check origin/main..HEAD`, then one authoritative
      `python3 scripts/grok_verify.py --mode pr`.
- [x] Complete independent reviews. Independent code review of head `a08060c1` returned
      **fail** with one major-that-matters and one untested-wiring major; its findings are
      recorded at `evidence/code-review-205.md` and the repairs are the role-based admission, the
      `verify()` end-to-end arms, the declared skipped checks, and the status-domain arms.
- [x] Bind evidence to the final tree fingerprint. The receipt written by the authoritative
      `grok_verify --mode pr` run carries `docs_state_scope` plus every check result against the
      final fingerprint; review receipts are recorded with `python3 scripts/grok_review.py`.
- [x] Mutation-prove the new tests. Battery in `evidence/mutation-battery-205.md`: every mutant
      the review listed as surviving (mw1, mw2, mw3, mp1) is killed, and the widened battery kills
      the role-admission, status-domain and disclosure mutants too.
