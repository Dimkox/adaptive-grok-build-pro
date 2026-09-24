# Tasks — Fix issue #167: select focused static SEO landing verification for landing-only changes while retaining full PR verification for runtime, contract, Trust CI, package, architecture, or workflow changes, with regression tests.

- [x] Freeze exact landing-only scope, non-goals, fail-closed behavior, and Trust CI authority.
- [x] Add selector and focused-mode regression tests, including multiple landing directories, status provenance, PR no-downgrade, and rejected-scope subprocess suppression.
- [x] Implement the explicit focused mode and exact workflow allowlist; preserve full `--mode pr`.
- [x] Audit default-to-contract wording and document focused mode as the safe default only after positive classification.
- [x] Rerun targeted verifier/workflow/status tests on 2026-09-23: 17 focused verifier tests, 2 Git-status tests, and 1 workflow allowlist test passed (`Ran 20 tests in 6.529s`, exit `0`).
- [x] Rerun the requested focused verifier on the real mixed tree; exit `1` as expected with `out-of-scope-or-invalid-paths`, source stability PASS, and no landing-contract or broad-suite subprocess dispatched. See `evidence/focused-verification-20260923.md`.
- [x] Run full PR verification against this repaired product tree; the final candidate run passed all route-selected checks.
- [x] Complete the repaired-tree `code_reviewer` and `test_reviewer` review wave; both reports PASS with no valid surviving mutants and `reviewed-tree-modified: no`.
- [x] Bind final full-PR verification and review receipts to one final tree fingerprint after persisting the reports.
