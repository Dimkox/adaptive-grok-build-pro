# Code review — bind cited identifiers to real receipts

reviewed-tree-modified: no

## Verdict

**FAIL.** Receipt echo binding and the JSON citation rules on this HEAD match the issue #206 contract, and `tests.test_citation_identifiers` is green (38 tests). YAML corpus authority does not. `_line_keyed_identifiers` is not a leaf parser: a continuation line or comment whose first key-like token is an identifier key authorizes every identifier-shaped run on that line, including prose that a real YAML parse would keep under `statement`. That is the laundering channel AC-004 says is closed.

## Identity

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-cite206`
- Branch: `fix/issue-206-receipt-identifier-citation`
- HEAD: `542949a98569a73af533b7c514f6cfcbfd8ec97a` (`git rev-parse HEAD`), subject `fix: make cited evidence identifiers pasteable and checkable (#206)`
- HEAD tree: `09203f1ad0c0ff508a22f7155cef22fd36249ceb` (`git rev-parse HEAD^{tree}`)
- Dirty-tree fingerprint from `tree_fingerprint`: unavailable. The read-only fingerprint command was denied by the shell circuit breaker and was not retried.
- Porcelain before the unit run: only untracked `engineering/changes/20260924-bind-cited-identifiers-to-real-receipts-issue-20-64a3e7/evidence/next-gap.md`
- Porcelain after the unit run and again after the scratch diff: that file plus untracked `evidence/review-test-542949a9.md`, which this review did not write. HEAD was unchanged. No tracked product path was staged or modified by this review.
- Scratch: `/tmp/cite206-cr-0700` and `/tmp/cite206-cr-0700/scratch`, both mode `0700`. `cp -a` of `.grok-stack`, `tests`, `scripts`, `.grok`, and `.agents` into `/tmp/cite206-cr-0700/scratch/repo`. `diff -q` of `citations.py`, `receipts.py`, `grok_citations.py`, `grok_verify.py`, and `grok_review.py` against the worktree was silent (identical). Mutation edits in that copy were denied by the same circuit breaker and were not retried, so no mutant was executed.

## What holds

Prior majors against head `9f1a2dac` are fixed in this tree, and the tests that name them passed.

- `grok_verify.py` and `grok_review.py` mint one `receipt_id` and pass that same value into `write_receipt` and `receipt_echo`. `verify()` still skips the write when governance fails or the tree moves (`verification.py` around the `governance_check.status != 'fail'` guard). The echo refuses a different id (`not-recorded-this-invocation`), a missing id (`invocation-unbound`), `stale is True` (`receipt-invalidated`), a bad envelope (`receipt-envelope-invalid`), and a different tree (`tree-fingerprint-mismatch`) before it prints `fingerprint=`. Unavailable lines do not carry that field.
- `scripts/grok_citations.py` turns an unread path, directory, symlink, or oversize input (stdin included) into `status=error`, prints `NOT READ` on stdout, and exits 2 unless `--warn-only`.
- There is no `extended-citation` branch. `_matches_corpus` accepts only an exact id or a corpus id that starts with the citation. A citation longer than the real id is unresolved. The bisect choice is the right one: if any sorted id starts with the token, the first id at or after the token does too.
- JSON authority is leaf-or-map. Nested `description` / `example` under `id`, `version`, or `policy` is not collected. Report prose is not a corpus glob. `scripts/grok_citations.py` is on `install_into.MANAGED_FILES` and in `.grok-stack/config/managed.json`.
- Decline accounting, symlink-directory containment, same-name document labels, and the git hatch are implemented and covered by passing tests.

Executed command, bytecode redirected out of the worktree:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/cite206-cr-0700/pyc python3 -m unittest tests.test_citation_identifiers -q
```

Observed: `Ran 38 tests in 16.811s` / `OK`, exit 0. That includes `EchoCliWiringTests.test_grok_verify_echoes_a_pasteable_line_for_its_own_receipt`, which compares the echo's status and fingerprint to the receipt file written by `grok_verify.py --mode fast`. This review did not run `scripts/grok_verify.py --mode pr`.

## Finding

**[major]** `.grok-stack/adaptive_grok/citations.py` `_line_keyed_identifiers` (about lines 249-260) and `_LINE_KEY` (line 108).

Change-spec files are the hand-edited YAML in `CORPUS_GLOBS`. JSON uses a real parse and `_key_is_identifier_bearing` on the actual path. YAML does not. The scanner takes the first `[A-Za-z0-9_.:-]+` token followed by a colon anywhere on the line. If that token is an identifier leaf (`commit`, `fingerprint`, `id`, and the other `IDENTIFIER_LEAF_KEYS` / suffixes), every identifier-shaped run on the line is ingested.

Two shapes therefore authorize a token that is not a typed leaf:

- A folded or literal `statement` (or `description`) whose continuation line is `commit:` plus the run. The parsed value belongs to `statement`. The continuation line's first key-like token is `commit`, so the run enters the corpus. A single-line `statement:` value does not, which is why the requirements text can say `statement:` / `reason:` lines stopped laundering. The block-scalar split reopens it.
- A comment line, or a trailing `#` on an `id:` line, whose first key-like token is `fingerprint` or `id`. The comment is not in the parsed document. The checker still treats the run as machine state.

AC-004 and `README.md` say a YAML token counts only at an explicitly typed leaf or identifier-value map, and that nested description/example prose does not. This path makes a fabricated run authoritative without putting it in a parsed leaf. `tests/test_citation_identifiers.py` never builds a `change-spec.yaml`, so the suite stays green. Dynamic execution of this case was not run: the probe command was denied and not retried. The conclusion is the straight-line match of `_LINE_KEY.search`, `_key_is_identifier_bearing`, and `_HEX_RUN` on those lines.

JSON is not the same hole. A `statement` string that merely contains the letters `commit:` stays under a non-identifier key, and the nested `id` / `version` / `policy` case is tested.

## Minors, not the verdict

- `requirements.md` says a git batch over the cap, or a short `git cat-file --batch-check` answer, must surface `git-probes-capped=true` rather than report an unprobed token as absent. `_resolves_as_git_objects` sets the flag and still leaves uncapped-out tokens unresolved, so they are printed `MISSING`. Fail-closed, but not the stated contract. A short stdout is still `zip`ped, and a success line whose first field is any 40- or 64-character hex object name resolves the paired token even when that name does not start with the token (`citations.py` about lines 341-356). Aligned git output does not need that second clause. It is a false-accept if a line is dropped or shifted. Not executed against a fake `git`.
- Both verification-evidence skill copies say to paste the `RECEIPT` line and that existence is not proof. They do not say what the checker declines (decimal-only, degenerate, longer than 64). `README.md` and `AGENTS.md` do. AC-006 is only partly met for the skill copies.
- `at=` is on the success echo and is not asserted. `reason=receipt-not-recorded` is implemented and does not appear in the test module. `test_grok_review_echoes_a_pasteable_line_for_its_own_receipt` does not read `code_review.json`; the verify CLI test does, and it passed. These are locks the tests do not hold. They are not missing product behavior.

## Mutants

| Probe | Result |
| --- | --- |
| Re-add extended-citation (citation longer than a real id it starts with) | inconclusive — scratch patch denied before execution. The current branch is absent; `test_a_short_identifier_plus_an_invented_tail_is_unresolved` asserts the incident shape and passed |
| Drop the receipt-id mismatch return | inconclusive — same denial. `test_echo_refuses_a_receipt_this_run_never_recorded` and `test_same_second_prior_receipt_does_not_prove_this_invocation_recorded_it` assert `reason=not-recorded-this-invocation` and passed |
| Ignore `stale is True` | inconclusive — same denial. `test_echo_refuses_a_receipt_invalidated_in_place` passed against the current guard |
| Treat unread documents as pass | inconclusive — same denial. `test_a_document_that_was_never_read_is_an_error_not_a_pass` passed against the current `status=error` path |
| YAML comment or block-scalar continuation authorizes a run | not executed (probe denied). Static result: the current function does authorize it. No test names this input, so a fix would be a new failure, not a killed mutant of an existing assertion |
| Drop `at=` from the success line | not executed. No assertion in this module reads `at=`, so that mutant would survive the suite. The field is present in `receipt_echo` |
| Report unprobed git candidates as absent while setting `git-probes-capped` | not executed. Static result: that is what the function does |

## Unexecuted claims

- Dirty-tree `tree_fingerprint` before and after, because that command was circuit-broken.
- Every source mutation above, because patching the scratch copy was denied and not retried. Scratch identity for the five compared files was established; mutant behavior was not.
- A live `git cat-file --batch-check` mis-alignment and a symlinked-directory escape beyond the test that already passed.
- `--json` versus stdout, `--no-record` silence, and FIFO cited input. The code routes the echo to stderr under `--json`, skips the echo under `--no-record`, and rejects non-regular files before read. No test in the passing module was inspected as covering `--json` or `--no-record`.
- Whether a real identifier was bound to the claim beside it. The tool still does not claim that, and the docs that were read say so.

VERDICT: FAIL
