# Tasks — M0 consolidate git and continue live authority proof

- [x] Probe attestation GET from **inside** the API container; print HTTP status only; never print bearer/env.
- [x] Mint exact `external-write` for this change/route/fingerprint if compose/kill-switch needs it. Kill-switch on → prove block → off → ready 200.
- [x] Update activation report (kill-switch pass, attestation N/A 404). Check off plan M0.0 false negatives; mark kill-switch if the drill passed. Annotate spec live-gap as freeze snapshot. Do not claim M0.2 complete.
- [x] Characterization: extend `trust-ci/tests/test_m0_invariants.py` (activation report Check Run id not UNKNOWN; no PEM in report; plan still says local HMAC / webhook not registered).
- [x] Mint `protected-path-write` for `decisions.md` and `trust-ci/tests/test_m0_invariants.py` **after last non-protected write or in one batch** against then-current fingerprint. Add ≤3-sentence no-push / next-slice SHA-change note.
- [ ] `git add --` in-scope paths only. Commit. Do not push.
- [ ] `python3 -m unittest trust-ci.tests.test_m0_invariants` and `python3 scripts/grok_verify.py --mode pr`.
- [x] Write `evidence/implementation.md`. Stop.
