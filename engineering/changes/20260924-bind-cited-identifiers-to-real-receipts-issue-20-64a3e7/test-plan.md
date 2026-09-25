# Test plan — Bind cited identifiers to real receipts (issue 206)

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | A run that records nothing (governance fail with an unchanged tree) must not echo a previous run's `status=pass`, and a receipt invalidated in place must not echo at all | `ReceiptEchoTests.test_echo_refuses_a_receipt_this_run_never_recorded`, `test_echo_refuses_a_receipt_invalidated_in_place`, `EchoCliWiringTests.test_grok_review_echoes_a_pasteable_line_for_its_own_receipt`, `EchoCliWiringTests.test_grok_verify_echoes_a_pasteable_line_for_its_own_receipt`; out-of-tree reproduction in `/tmp/cite206-fix/echo_cases.py` cases A/A2 vs control M |
| P0 | A cited document that was never read must not produce a green check | `CitationsCliTests.test_a_document_that_was_never_read_is_an_error_not_a_pass`, `test_an_oversized_document_is_declined_and_the_stdin_ceiling_applies` (exit 2, `CITATION ERROR`, `NOT READ` on stdout) |
| P0 | A genuine identifier prefix with an invented tail (the issue 206 shape) must be unresolved even when the prefix stands alone in the corpus | `CorpusCorruptsItsOwnTrustTests.test_a_short_identifier_plus_an_invented_tail_is_unresolved`; confirmed mutation-catching: re-adding the deleted `extended-citation` branch turns this test red |
| P1 | Corrupt, foreign-route, foreign-kind or envelope-incomplete receipts must yield one well-formed refusal line, never a traceback and never an identifier | `ReceiptEchoTests.test_echo_validates_the_envelope_before_emitting_an_identifier`, `test_echo_line_grammar_stays_one_shell_safe_token_per_field` |
| P1 | A fabricated hex committed into hand-written machine state must not become authoritative | `CorpusCorruptsItsOwnTrustTests.test_prose_inside_machine_state_does_not_make_a_token_authoritative` |
| P1 | The corpus must not read outside the repository through a symlinked directory, nor an oversized file | `CorpusCorruptsItsOwnTrustTests.test_symlinked_and_oversized_corpus_entries_are_skipped` (creates both a symlinked file, a symlinked directory and a >4 MiB corpus file) |
| P1 | Hex the checker declines to judge must be visible, not silently absent | `IdentifierExtractionTests.test_a_hex_run_longer_than_the_ceiling_is_declined_for_a_name`, `test_declined_runs_are_surfaced_instead_of_silently_absent`, `CitationsCliTests.test_the_summary_shows_what_the_checker_declined_to_judge` |
| P1 | An echo fingerprint pasted into a report must re-resolve against the checker; a padded one must not | `ReceiptEchoTests.test_a_cited_echo_fingerprint_resolves_against_the_checker` |
| P2 | Two same-named documents must stay distinguishable in findings | `CitationsCliTests.test_cli_distinguishes_two_documents_with_the_same_name` |
| P2 | The Git object hatch and probe bound must only ever make the check stricter | `GitObjectResolutionTests.test_the_git_hatch_only_makes_the_check_stricter`, `test_a_real_commit_prefix_resolves_even_though_no_receipt_repeats_it` |

## Automated checks

- Unit: `python3 -m unittest tests.test_citation_identifiers -q` — 33 tests, covers extraction and decline reasons, corpus containment and key scoping, resolution rules, all echo states, and the CLI.
- Integration: `tests.test_change_receipts`, `tests.test_package_status`, `tests.test_hooks` and `tests.test_installer` exercise the receipt writers, the stop gate and the managed-file installation set that now ships `scripts/grok_citations.py`; all pass in the `-P 6` sweep of all 38 test modules.
- Contract: `tests.test_structure` requires `scripts/grok_citations.py` to exist; `install_into.MANAGED_FILES`, `.grok-stack/config/managed.json` and the verification-evidence skill text agree on it.
- E2E: out-of-tree probes in `/tmp/cite206-fix/` — `echo_cases.py` (14 receipt shapes including controls), `cite_cases.py` (resolution, decline, symlink escape, label collision), `e2e_governance_fail.py` (the governance-fail branch through the real `grok_verify.py` CLI, before-vs-after).
- Mutation-pinned: re-adding the deleted `extended-citation` branch turns `test_a_short_identifier_plus_an_invented_tail_is_unresolved` red, and dropping `not_before` from `grok_review.py` turns the review wiring test red — both were verified by applying the mutation, observing the failure, and restoring the file byte-identically.
- Static analysis: `python3 -m ruff check .grok-stack/adaptive_grok scripts tests` and `git diff --check origin/main..HEAD`, both clean; bandit runs inside `grok_verify --mode pr`.

## Manual checks

- No test fixture in this module contains a literal high-entropy hex run: identifier fixtures are computed by `_synthetic_hex()`, so a secret scanner has nothing to disposition. Verified by grepping the diff for `[0-9a-fA-F]{16,}` outside generated package state.
- The checker's own claims were checked against measured behaviour before README, AGENTS.md and `requirements.md` were worded: 488 identifiers in 436 machine-state files (~1.1 MB, ~200 ms single walk), real commit ids resolve, `extended-citation` accepts nothing.

## Rollback

Reverting the two source commits restores the pre-#206 state: no echo line, no citation checker. Nothing persists a new format — `RECEIPT` lines are output only, and the corpus is recomputed per run — so no data migration or cleanup is required.
