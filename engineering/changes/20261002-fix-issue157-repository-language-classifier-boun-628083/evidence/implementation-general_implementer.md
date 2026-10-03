# C classifier implementation evidence

Route `6280839332b6`, sole selected `general_implementer`, isolated branch `fix/v211-repo-classifier`. Baseline HEAD `e5856acfd4bc7a186f40a740b54ec86459462db5`; the commands below test the current uncommitted classifier/test snapshot on that baseline, before integrating actual fetched main. These are focused implementation observations, not a full verifier receipt, independent review or external merge authority.

Product inventory: `.grok-stack/adaptive_grok/repo.py` and `tests/test_repo_language_disclosure.py`. Additional files belong only to this active workflow package. No dirty historical source tree, release/version/state aggregate, router precedence code, deployed trust material or external resource was edited.

## Root cause and repair

Baseline root manifests followed symlinks, PHP/contract rglob was unbounded, and source languages/Swift/incomplete inventories were undisclosed. One shared descriptor-rooted inventory now bounds regular file reads and source traversal, refuses symlink/nonregular proof, checks open/read identity, and derives the existing confirmed fields plus additive `detected_languages` and `language_scan` disclosure. Swift confirmation uses nonempty readable first-party source or recognizable bounded canonical package text; it explicitly emits `swift:profile=base-only` and adds no Apple/macOS/U4 qualification.

Global defaults: files 4000; read bytes 8 MiB; directory depth 16; directories 1024; listing entries 20000; per-directory entries 4000; manifest/source reads 64 KiB each. An overflowing directory is discarded entirely to avoid enumeration-order-dependent partial selection. Fixed canonical root probes share file/read budgets. All truncation/unreadability sets incomplete status and unknown=true; unknown source extensions, weak signals and case conflicts remain visible independently of confirmed languages.

## Executed focused evidence

- RED baseline: `taskset -c 0-1 python3 -m unittest tests.test_repo_language_disclosure -q` → 25 tests in 0.052 s, 22 assertion failures, zero errors. Failures reproduce missing Swift, symlink proof and absent disclosure; three legacy characterization fixtures pass. Earlier initial test construction had missing-field errors; those were rewritten to observable assertions before product edits.
- Additional RED: `taskset -c 6-7 python3 -m unittest tests.test_repo_language_disclosure.RepoLanguageDisclosureTests.test_non_contract_sources_in_contract_directory_do_not_add_api_domain -q` → 1 failure. An unrelated helper.py in an OpenAPI folder must not manufacture API evidence; the existing contract suffix predicate was retained.
- Additional RED: unreadable-directory scenario with an unknown assertion → 1 failure among 3 checks; corrected incomplete scans to unknown=true. JSON depth/invalid-Unicode characterization checks passed.
- Additional RED: `taskset -c 6-7 python3 -m unittest tests.test_repo_language_disclosure.RepoLanguageDisclosureTests.test_node_json_integer_conversion_limit_does_not_crash -q` → 1 assertion failure around real stdlib ValueError on 5000-digit metadata. Catch bounded parser ValueError/RecursionError without changing compatible Node confirmation or creating scripts.
- Final GREEN: `taskset -c 6-7 python3 -m unittest tests.test_repo_language_disclosure tests.test_repo_router -q` → 71 tests (36 dedicated classifier, 35 existing router) in 2.962 s, OK, exit 0.
- `python3 -m ruff check .grok-stack/adaptive_grok/repo.py tests/test_repo_language_disclosure.py` → All checks passed, exit 0.
- `git diff --check` → no output, exit 0.
- Typed `adaptive_grok.spec.validate_spec` against this package → `[]`, exit 0.

Final tested product SHA-256: repo.py `14891f328cfce532c6f77c2a3769461ade9913c252f2ab001fef2928378bbd7a`; classifier tests `9fcc1dcb25ddb0c3830d38e9e6e77a0b340ff157c974d54f1b866a45a4e3c135`.

## Limits and remaining gates

Source/compiler validation, Swift test execution and macOS qualification are not claimed. Extension-only non-Swift source stays advisory; unknown extensions conservatively include configuration candidates. Hostile filesystem fault injection is deterministic at the os.open/read boundary in real temporary fixtures. Complete enumeration does not imply all languages are confirmed. No reviewer mutation score or full-suite claim is made here.

The controller owns final full PR verification, independent code/test review and fresh fingerprint-bound receipts after integration and report persistence. Executable product inventory retains full PR scope; startup docs-only skipped checks are historical initial-inventory observations. PR delivery/merge still requires exact delegated actions, App-owned exact-head Trust CI and the required approvals. Rollback is a new PR reverting the classifier contour; no data migration or production mutation occurs.
